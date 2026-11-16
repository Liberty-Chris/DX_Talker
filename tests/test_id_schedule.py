from dataclasses import replace
from datetime import datetime, timedelta
import json
import os
import threading
import time
import unittest
from unittest.mock import patch

from dxtalker.id_schedule import entries, new_entry, next_occurrence, ScheduleBook
from dxtalker.models import Settings
from dxtalker.engine import Engine
from test_engine import FakeAudio, FakeSpeech, FakePTT, wait_for


def entry(**changes):
    item = new_entry()
    item.update(text='This is a scheduled ID')
    item.update(changes)
    return item


class CalendarTests(unittest.TestCase):
    def test_first_tuesday_twice_and_fifth_or_last_weekday(self):
        item = entry(kind='Monthly weekday', weekdays=[1], ordinal=1, times=['12:00', '18:00'])
        self.assertEqual(next_occurrence(item, datetime(2026, 11, 15)), datetime(2026, 12, 1, 12))
        self.assertEqual(next_occurrence(item, datetime(2026, 12, 1, 12)), datetime(2026, 12, 1, 18))
        self.assertEqual(next_occurrence(item, datetime(2026, 12, 1, 18)), datetime(2027, 1, 5, 12))
        self.assertEqual(next_occurrence(dict(item, ordinal=-1), datetime(2026, 11, 15)), datetime(2026, 11, 24, 12))
        self.assertEqual(next_occurrence(dict(item, ordinal=5), datetime(2026, 11, 15)), datetime(2026, 12, 29, 12))

    def test_weekly_monthly_once_and_date_window(self):
        now = datetime(2026, 11, 15, 12)
        self.assertEqual(next_occurrence(entry(kind='Weekly', weekdays=[0, 4]), now), datetime(2026, 11, 16, 12))
        self.assertEqual(next_occurrence(entry(kind='Monthly date', day=31), now), datetime(2026, 12, 31, 12))
        self.assertEqual(next_occurrence(entry(kind='Once', date='2026-12-25'), now), datetime(2026, 12, 25, 12))
        self.assertIsNone(next_occurrence(entry(kind='Once', date='2026-01-01'), now))
        self.assertIsNone(next_occurrence(entry(kind='Daily', end_date='2026-11-14'), now))
        self.assertEqual(next_occurrence(entry(kind='Daily', start_date='2026-12-02'), now), datetime(2026, 12, 2, 12))

    def test_no_disabled_time_backlog_and_no_duplicates_after_clock_rollback(self):
        item = entry(kind='Daily', times=['12:00'])
        before = datetime(2026, 11, 15, 11, 59)
        book = ScheduleBook(json.dumps([item]), before, 0)
        list(book.tick(before + timedelta(minutes=1), 60))
        self.assertEqual(book.due(), item)
        book.finish(item['id'], before + timedelta(minutes=1), 60)
        list(book.tick(before, 120)); list(book.tick(before + timedelta(minutes=1), 180))
        self.assertIsNone(book.due())
        late = ScheduleBook(json.dumps([item]), datetime(2026, 11, 15, 12, 1), 0)
        list(late.tick(datetime(2026, 11, 15, 12, 2), 60))
        self.assertIsNone(late.due())

    def test_busy_message_expires_and_interval_advances_from_success(self):
        item = entry(kind='Interval', minutes=1, grace_minutes=2)
        now = datetime(2026, 11, 15, 12)
        book = ScheduleBook(json.dumps([item]), now, 0)
        list(book.tick(now + timedelta(seconds=60), 60))
        self.assertIsNotNone(book.due())
        book.finish(item['id'], now + timedelta(seconds=90), 90)
        list(book.tick(now + timedelta(seconds=149), 149)); self.assertIsNone(book.due())
        list(book.tick(now + timedelta(seconds=150), 150)); self.assertIsNotNone(book.due())
        expired = list(book.tick(now + timedelta(seconds=271), 271))
        self.assertEqual(expired, [('expired', item)])
        self.assertIsNone(book.due())

    @unittest.skipUnless(hasattr(time, 'tzset'), 'Local DST simulation needs tzset')
    def test_spring_gap_is_skipped_and_fall_repeated_hour_runs_once(self):
        old = os.environ.get('TZ')
        try:
            os.environ['TZ'] = 'America/Indiana/Indianapolis'; time.tzset()
            item = entry(kind='Daily', times=['02:58'])
            now = datetime(2026, 3, 8, 1, 59)
            self.assertEqual(next_occurrence(item, now), datetime(2026, 3, 9, 2, 58))
            book = ScheduleBook(json.dumps([item]), now, 0)
            list(book.tick(datetime(2026, 3, 8, 3), 60)); self.assertIsNone(book.due())
            item = entry(kind='Daily', times=['01:30'])
            book = ScheduleBook(json.dumps([item]), datetime(2026, 11, 1, 1, 29), 0)
            list(book.tick(datetime(2026, 11, 1, 1, 30), 60)); self.assertIsNotNone(book.due())
            book.finish(item['id'], datetime(2026, 11, 1, 1, 30), 60)
            list(book.tick(datetime(2026, 11, 1, 1), 1800))
            list(book.tick(datetime(2026, 11, 1, 1, 30), 3600)); self.assertIsNone(book.due())
        finally:
            if old is None: os.environ.pop('TZ', None)
            else: os.environ['TZ'] = old
            time.tzset()

    def test_collection_bounds_and_required_fields(self):
        self.assertEqual(len(entries(json.dumps([entry() for _ in range(20)]))), 20)
        for values in ([entry() for _ in range(21)], [entry(text='')], [entry(times=['25:00'])],
                       [entry(kind='Monthly weekday', weekdays=[0, 1])], [entry(minutes=True)],
                       [entry(start_date='2026-12-01', end_date='2026-11-01')]):
            with self.assertRaises(ValueError): entries(json.dumps(values))
        values = [entry()]; values.append(dict(values[0]))
        with self.assertRaises(ValueError): entries(json.dumps(values))
        self.assertEqual(Settings().voice_ids, '[]')


class ScheduledTransmissionTests(unittest.TestCase):
    def test_source_loss_cleanup_cannot_hold_the_source_callback(self):
        entered, release = threading.Event(), threading.Event()
        class Monitor:
            def close(self): entered.set(); release.wait(3)
        engine = Engine(Settings(), lambda *event: None, FakeAudio(), FakeSpeech(), monitor=Monitor())
        try:
            engine.stop('Source lost', defer_cleanup=True)
            self.assertTrue(entered.wait(1))
            # Another source event must finish while the driver remains blocked.
            callback = threading.Thread(target=lambda: engine.stop('Still lost', defer_cleanup=True))
            callback.start(); callback.join(1)
            self.assertFalse(callback.is_alive())
            self.assertFalse(engine.enabled)
            with self.assertRaises(ValueError): engine.enable()
        finally:
            release.set(); engine.quit.set(); engine.wake.set(); engine.worker.join(3)
            self.assertFalse(engine.worker.is_alive())

    def test_required_id_then_scheduled_voice_with_one_ptt_owner(self):
        item = entry(kind='Daily', times=['12:00'])
        now = [datetime(2026, 12, 1, 11, 59, 59)]
        tick = [0]
        audio, speech, ptts, events = FakeAudio(), FakeSpeech(), [], []
        def create(settings):
            ptt = FakePTT(); ptts.append(ptt); return ptt
        settings = Settings(radio_device='radio', preview_device='local', cw_text='E', lead_ms=0, tail_ms=0, voice_ids=json.dumps([item]))
        engine = Engine(settings, lambda *e: events.append(e), audio, speech, create, clock=lambda: tick[0], wall_clock=lambda: now[0])
        try:
            engine.enable()
            wait_for(lambda: len(audio.played) == 1 and not engine.busy)
            tick[0] = 1; now[0] = datetime(2026, 12, 1, 12)
            engine.wake.set()
            wait_for(lambda: any(k == 'schedule_event' and v['code'] == 'completed' for k, v in events))
            self.assertEqual(speech.texts, [item['text']])
            self.assertEqual(len(ptts), 2)
            self.assertTrue(all(p.calls == ['open', True, False, 'close'] for p in ptts))
            engine.stop(); self.assertFalse(engine.enabled)
            # Restarting output within this minute cannot replay a completed ID.
            wait_for(lambda: not engine.busy)
            engine.enable(); wait_for(lambda: len(audio.played) == 3 and not engine.busy)
            self.assertEqual(speech.texts, [item['text']])
        finally:
            engine.stop(); engine.quit.set(); engine.wake.set(); engine.worker.join(3)
            self.assertFalse(engine.worker.is_alive())

    def test_invalid_recorded_schedule_prevents_rf_enable(self):
        settings = Settings(radio_device='radio', cw_text='E', voice_ids=json.dumps([entry(source='WAV', wav='/missing/id.wav')]))
        with self.assertRaises((ValueError, FileNotFoundError)):
            settings.validate_rf()
