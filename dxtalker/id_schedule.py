"""Bounded local calendar schedules. This module never touches audio or PTT."""
from datetime import date, datetime, timedelta
import json
import re
import uuid

KINDS = ('Interval', 'Daily', 'Weekly', 'Monthly weekday', 'Monthly date', 'Once')
WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')


def new_entry():
    return dict(id=uuid.uuid4().hex, name='Voice ID', enabled=True, source='Speech',
                text='', wav='', kind='Interval', minutes=30, times=['12:00'],
                weekdays=[1], ordinal=1, day=1, date='', start_date='', end_date='',
                window_start='00:00', window_end='23:59', grace_minutes=5)


def minute(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
        raise ValueError('Use times in 24 hour HH:MM format')
    return int(value[:2]) * 60 + int(value[3:])


def entries(text):
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        raise ValueError('Invalid voice ID collection') from None
    if not isinstance(data, list) or len(data) > 20:
        raise ValueError('Use at most 20 scheduled voice IDs')
    seen = set()
    defaults = new_entry()
    for item in data:
        if not isinstance(item, dict) or set(item) != set(defaults):
            raise ValueError('Incomplete voice ID. Edit and save its schedule')
        if any(type(item[k]) is not type(v) for k, v in defaults.items()):
            raise ValueError('Invalid voice ID field type')
        for key in ('id', 'name', 'text', 'wav'):
            if len(item[key]) > (2048 if key in ('text', 'wav') else 80) or any(ord(c) < 32 for c in item[key]):
                raise ValueError('Use single line voice ID fields')
        if not re.fullmatch('[a-f0-9]{32}', item['id']) or item['id'] in seen:
            raise ValueError('Each voice ID must have a unique identifier')
        seen.add(item['id'])
        if not item['name'].strip() or item['source'] not in ('Speech', 'WAV') or item['kind'] not in KINDS:
            raise ValueError('Choose a voice ID name, source and schedule')
        if item['enabled'] and not item['text' if item['source'] == 'Speech' else 'wav'].strip():
            raise ValueError('Assign text or a WAV file to every enabled voice ID')
        for key in ('date', 'start_date', 'end_date'):
            if item[key]:
                try: datetime.strptime(item[key], '%Y-%m-%d').date()
                except ValueError: raise ValueError('Use dates in YYYY-MM-DD format') from None
        if item['start_date'] and item['end_date'] and item['start_date'] > item['end_date']:
            raise ValueError('End date must be on or after start date')
        if item['kind'] == 'Once' and not item['date']:
            raise ValueError('Choose the date for a one time voice ID')
        if not 1 <= item['minutes'] <= 10080 or not 1 <= item['grace_minutes'] <= 60:
            raise ValueError('Interval must be 1 to 10080 minutes. Grace must be 1 to 60 minutes')
        if item['ordinal'] not in (1, 2, 3, 4, 5, -1) or not 1 <= item['day'] <= 31:
            raise ValueError('Choose a valid monthly occurrence or day')
        days = item['weekdays']
        if not days or len(days) > 7 or any(type(d) is not int or not 0 <= d <= 6 for d in days) or len(set(days)) != len(days):
            raise ValueError('Choose at least one weekday')
        if item['kind'] == 'Monthly weekday' and len(days) != 1:
            raise ValueError('Choose one weekday for a monthly weekday schedule')
        if not 1 <= len(item['times']) <= 24 or any(not isinstance(t, str) for t in item['times']) or len(set(item['times'])) != len(item['times']):
            raise ValueError('Choose 1 to 24 distinct times')
        for value in item['times']: minute(value)
        if minute(item['window_start']) > minute(item['window_end']):
            raise ValueError('Daily window must end on the same day after it starts')
    return data


def day_matches(item, day):
    iso = day.isoformat()
    if item['start_date'] and iso < item['start_date'] or item['end_date'] and iso > item['end_date']:
        return False
    kind = item['kind']
    if kind == 'Weekly': return day.weekday() in item['weekdays']
    if kind == 'Monthly weekday':
        ordinal = (day.day - 1) // 7 + 1
        return day.weekday() in item['weekdays'] and (ordinal == item['ordinal'] or
               item['ordinal'] == -1 and (day + timedelta(days=7)).month != day.month)
    if kind == 'Monthly date': return day.day == item['day']
    if kind == 'Once': return iso == item['date']
    return True


def valid_local_time(value):
    # The OS resolves local daylight saving rules. A skipped spring minute
    # round trips to a different wall time and must not be announced late.
    return datetime.fromtimestamp(value.timestamp()) == value


def next_occurrence(item, now):
    """Calendar preview uses the computer's local wall time, as does dispatch."""
    if not item['enabled']: return None
    if item['kind'] == 'Interval': return now + timedelta(minutes=item['minutes'])
    first_day = now.date()
    for key in ('start_date', 'date') if item['kind'] == 'Once' else ('start_date',):
        if item[key]: first_day = max(first_day, datetime.strptime(item[key], '%Y-%m-%d').date())
    if item['end_date'] and first_day.isoformat() > item['end_date']: return None
    if item['kind'] == 'Once' and item['date'] < now.date().isoformat(): return None
    for offset in range(366 * 8):
        try: day = first_day + timedelta(days=offset)
        except OverflowError: return None
        if item['kind'] == 'Once' and day.isoformat() > item['date']: return None
        if item['end_date'] and day.isoformat() > item['end_date']: return None
        if day_matches(item, day):
            for value in sorted(item['times']):
                if not minute(item['window_start']) <= minute(value) <= minute(item['window_end']): continue
                candidate = datetime.combine(day, datetime.strptime(value, '%H:%M').time())
                if candidate > now and valid_local_time(candidate): return candidate
    return None


class ScheduleBook:
    """No backlog from disabled time. Calendar keys suppress clock rollback repeats.

    A due message gets one bounded grace period while the receiver is busy.
    Completion is recorded only after playback and PTT release succeed.
    Interval schedules use monotonic time and advance from completion.
    """
    def __init__(self, text='[]', now=None, clock=0):
        self.items = entries(text)
        self.last = now or datetime.now()
        self.intervals = {i['id']: clock + i['minutes'] * 60 for i in self.items}
        self.pending = {}
        self.completed = set()
        self.tick_second = None

    def tick(self, now, clock):
        second = now.replace(microsecond=0)
        if second == self.tick_second: return
        self.tick_second = second
        for item in self.items:
            key = item['id']
            if not item['enabled']: continue
            # Clock changes never create a large replay burst.
            lower = max(self.last, now - timedelta(minutes=item['grace_minutes']))
            current_minute = now.hour * 60 + now.minute
            if item['kind'] == 'Interval':
                if clock >= self.intervals[key] and day_matches(item, now.date()) and minute(item['window_start']) <= current_minute <= minute(item['window_end']):
                    self.pending.setdefault(key, (item, 'interval', now + timedelta(minutes=item['grace_minutes'])))
            else:
                for offset in range((now.date() - lower.date()).days + 1):
                    day = lower.date() + timedelta(days=offset)
                    if not day_matches(item, day): continue
                    for value in item['times']:
                        if not minute(item['window_start']) <= minute(value) <= minute(item['window_end']): continue
                        due = datetime.combine(day, datetime.strptime(value, '%H:%M').time())
                        occurrence = day.isoformat() + 'T' + value
                        if lower < due <= now and valid_local_time(due) and (key, occurrence) not in self.completed:
                            self.pending.setdefault(key, (item, occurrence, due + timedelta(minutes=item['grace_minutes'])))
        self.last = now
        for key, (item, occurrence, expiry) in list(self.pending.items()):
            if now > expiry:
                self.finish(key, now, clock)
                yield 'expired', item
        # Keep at most the recent eight days of rollback suppression.
        cutoff = (now.date() - timedelta(days=8)).isoformat()
        self.completed = {(k, v) for k, v in self.completed if v == 'interval' or v >= cutoff}

    def due(self):
        return next(iter(self.pending.values()))[0] if self.pending else None

    def finish(self, key, now, clock):
        value = self.pending.pop(key, None)
        if value:
            item, occurrence, _ = value
            self.completed.add((key, occurrence))
            self.intervals[key] = clock + item['minutes'] * 60
