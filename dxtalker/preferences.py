"""Preference boundaries shared by autosave, radio drafts and scoped actions."""
from dataclasses import fields, replace
import json
from .models import Settings, settings_path
from .profiles import SOURCE_FIELDS

RADIO_FIELDS = (
    'radio_device', 'receive_guard', 'receive_device', 'receive_threshold_db',
    'receive_quiet_seconds', 'ptt_method', 'serial_port', 'active_high', 'lead_ms',
    'tail_ms', 'max_tx_seconds', 'voice_text', 'cw_text', 'voice_wav', 'voice_mode',
    'cw_wpm', 'cw_hz', 'id_mode', 'id_minutes', 'voice_id_minutes',
    'volume_percent', 'cw_volume_percent', 'voice_id_volume_percent',
)
FORMAT_FIELDS = ('announcement_order', 'announcement_intro', 'include_intro',
                 'include_callsign', 'include_frequency', 'speak_units')
PREFERENCE_FIELDS = tuple(f.name for f in fields(Settings)
                          if f.name not in (*RADIO_FIELDS, *SOURCE_FIELDS, 'supervised_ack'))


def read_group(base, variables, names):
    values = {}
    for name in names:
        try:
            raw = variables[name].get()
            default = getattr(Settings(), name)
            values[name] = raw.strip() if type(default) is str else type(default)(raw)
        except Exception:
            # Tk variables can raise TclError; do not leak platform exceptions.
            raise ValueError('Check ' + name.replace('_', ' ')) from None
    return replace(base, **values).validate()


def save_radio_draft(variables, base):
    """Keep incomplete edits, never source addresses, credentials or enable state."""
    values = {}
    for name in RADIO_FIELDS:
        try:
            value = variables[name].get()
        except Exception:
            continue
        if str(value) != str(getattr(base, name)):
            values[name] = value
    path = settings_path().with_name('radio-draft.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(values), encoding='utf-8')
    temporary.replace(path)
    return bool(values)


def load_radio_draft():
    try:
        path = settings_path().with_name('radio-draft.json')
        if path.stat().st_size > 32768:
            return {}
        values = json.loads(path.read_text(encoding='utf-8'))
        return {key: value for key, value in values.items()
                if key in RADIO_FIELDS and type(value) in (str, bool, int, float)}
    except (OSError, ValueError, AttributeError):
        return {}
