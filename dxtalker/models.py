"""Validated settings, DX records and speech formatting. No hardware dependencies."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
import math
import os
import sys
from pathlib import Path
import re
from urllib.parse import urlsplit

from . import __version__

UTC = timezone.utc
CALL = r"[A-Z0-9][A-Z0-9/\-]{1,19}"
SPOT = re.compile(rf"^DX de (?P<spotter>{CALL}):\s+(?P<freq>\d{{1,7}}(?:\.\d{{1,4}})?)\s+(?P<dx>{CALL})\s+(?P<rest>.*)$", re.I)
STAMP = re.compile(r"(?:^|\s)(\d{4})Z?\s*$", re.I)
PHONETIC = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "Alpha Bravo Charlie Delta Echo Foxtrot Golf Hotel India Juliet Kilo Lima Mike November Oscar Papa Quebec Romeo Sierra Tango Uniform Victor Whiskey Xray Yankee Zulu".split()))
DIGITS = dict(zip("0123456789", "zero one two three four five six seven eight nine".split()))


def valid_call(value: str) -> bool:
    return bool(re.fullmatch(CALL, value.upper()) and any(c.isdigit() for c in value)
                and any(c.isalpha() for c in value))


@dataclass(frozen=True)
class Spot:
    dx_call: str
    frequency_khz: Decimal
    spotter: str
    timestamp: datetime
    received: datetime
    source: str
    comment: str = ""
    mode: str = ""
    dx_country: str = ""
    dx_continent: str = ""
    spotter_country: str = ""
    spotter_continent: str = ""
    spotter_region: str = ""

    @property
    def key(self) -> tuple:
        return self.dx_call, self.frequency_khz

    def frequency_text(self, unit="kHz") -> str:
        if unit not in ("kHz", "MHz"):
            raise ValueError("Choose kHz or MHz")
        value = self.frequency_khz / Decimal("1000") if unit == "MHz" else self.frequency_khz
        text = format(value, "f")
        return text.rstrip("0").rstrip(".") if "." in text else text

    def spoken_groups(self, unit="kHz") -> tuple[str, str, str]:
        call = " ".join(PHONETIC.get(c, DIGITS.get(c, {"/": "stroke", "-": "dash"}.get(c, c))) for c in self.dx_call)
        spoken = " ".join("point" if c == "." else DIGITS[c] for c in self.frequency_text(unit))
        units = "megahertz" if unit == "MHz" else "kilohertz"
        return "New DX on", f"{spoken} {units}", call

    def announcement_groups(self, settings, phonetic=True):
        settings.validate_format()
        _, frequency, call = self.spoken_groups(settings.frequency_unit)
        if not phonetic:
            frequency = self.frequency_text(settings.frequency_unit)
            call = self.dx_call
            if settings.speak_units:
                frequency += " " + settings.frequency_unit
        elif not settings.speak_units:
            frequency = frequency.rsplit(" ", 1)[0]
        content = {"intro": settings.announcement_intro.strip(), "frequency": frequency, "callsign": call}
        included = {"intro": settings.include_intro, "frequency": settings.include_frequency,
                    "callsign": settings.include_callsign}
        return [(part, content[part]) for part in settings.announcement_order.split(",") if included[part]]

    def speech_in(self, unit="kHz") -> str:
        return ". ".join(self.spoken_groups(unit)) + "."

    @property
    def speech(self) -> str:
        return self.speech_in()


def make_spot(dx: str, freq: str, spotter: str, stamp: datetime,
              source: str, now: datetime, comment: str = "", mode: str = "", **location) -> Spot:
    dx, spotter = dx.upper(), spotter.upper()
    if not valid_call(dx) or not valid_call(spotter):
        raise ValueError("Invalid callsign")
    value = Decimal(str(freq))
    if not value.is_finite() or not Decimal("1") <= value <= Decimal("10000000"):
        raise ValueError("Invalid frequency")
    if stamp.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    stamp = stamp.astimezone(UTC)
    if stamp > now + timedelta(minutes=2):
        raise ValueError("Timestamp is in the future")
    from .filtering import clean_comment
    from .geography import clean_location
    return Spot(dx, value, spotter, stamp, now, source, clean_comment(comment), clean_comment(mode), **clean_location(location))


def parse_line(line: str, source: str, now: datetime | None = None) -> Spot | None:
    now = now or datetime.now(UTC)
    match = SPOT.fullmatch(line.strip())
    if not match:
        return None
    time_match = STAMP.search(match["rest"])
    if not time_match:
        return None
    try:
        hhmm = time_match[1]
        stamp = now.replace(hour=int(hhmm[:2]), minute=int(hhmm[2:]), second=0, microsecond=0)
        # Cluster HHMM fields do not carry dates. Pick the nearest UTC day,
        # then reject excessive future timestamps. The queue enforces freshness.
        stamp = min((stamp + timedelta(days=d) for d in (-1, 0, 1)), key=lambda t: abs((now-t).total_seconds()))
        return make_spot(match["dx"], match["freq"], match["spotter"], stamp, source, now, match["rest"][:time_match.start()])
    except (ValueError, InvalidOperation):
        return None


def parse_json_feed(payload: bytes, source: str, now: datetime | None = None) -> list[Spot]:
    now = now or datetime.now(UTC)
    items = json.loads(payload)
    if not isinstance(items, list) or len(items) > 2000:
        raise ValueError("Feed must be a JSON array of at most 2000 spots")
    result = []
    for item in items:
        try:
            if not isinstance(item, dict):
                continue
            result.append(make_spot(str(item["dx_call"]), str(item["frequency_khz"]), str(item["spotter"]),
                                    datetime.fromisoformat(str(item["time"]).replace("Z", "+00:00")), source, now, item.get("comment", ""), item.get("mode", ""),
                                    **{k:item.get(k, '') for k in ('dx_country','dx_continent','spotter_country','spotter_continent','spotter_region')}))
        except (KeyError, ValueError, InvalidOperation, TypeError, OverflowError):
            continue
    return result


@dataclass(frozen=True)
class Settings:
    source_type: str = "TCP/Telnet"
    host: str = "w4mr.ddns.net"
    port: int = 7373
    login: str = ""
    feed_url: str = ""
    poll_seconds: int = 30
    radio_device: str = ""
    preview_device: str = ""
    receive_guard: bool = False
    receive_device: str = ""
    receive_threshold_db: int = -40
    receive_quiet_seconds: int = 7
    ptt_method: str = "VOX"
    serial_port: str = ""
    active_high: bool = True
    lead_ms: int = 300
    tail_ms: int = 200
    max_tx_seconds: int = 60
    voice_text: str = ""
    cw_text: str = ""
    voice: str = ""
    speech_rate: int = 0
    voice_wav: str = ""
    voice_mode: str = "Speech"
    cw_wpm: int = 20
    cw_hz: int = 700
    id_mode: str = "CW"
    id_minutes: int = 10
    voice_id_minutes: int = 30
    max_age_seconds: int = 180
    repeat_seconds: int = 300
    spacing_seconds: int = 5
    filter_bands: str = ""
    filter_modes: str = ""
    filter_activities: str = ""
    license_class: str = "Off"
    license_region: str = "US Region 2"
    license_unknown: bool = False
    filter_dx_countries: str = ""
    filter_dx_continents: str = ""
    filter_spotter_countries: str = ""
    filter_spotter_continents: str = ""
    filter_spotter_regions: str = ""
    geography_unknown: bool = False
    location_overrides: str = ""
    listening_presets: str = "{}"
    min_khz: float = 1.0
    max_khz: float = 10000000.0
    volume_percent: int = 70
    cw_volume_percent: int = 45
    voice_id_volume_percent: int = 70
    local_volume_percent: int = 70
    character_pause_ms: int = 0
    group_pause_ms: int = 450
    voice_gender: str = "Any"
    speech_provider: str = "eSpeak NG" if sys.platform.startswith("linux") else "Windows"
    eleven_voice: str = ""
    frequency_unit: str = "kHz"
    announcement_order: str = "intro,frequency,callsign"
    announcement_intro: str = "New DX on"
    include_intro: bool = True
    include_callsign: bool = True
    include_frequency: bool = True
    speak_units: bool = True
    piper_executable: str = ""
    piper_model: str = ""
    voice_pack_root: str = ""
    voice_pack: str = ""
    supervised_ack: bool = False
    keep_awake: str = 'Off'
    display_limit: int = 500
    logging_enabled: bool = True
    diagnostics_enabled: bool = bool(re.search(r"(a|b|rc)\d+$", __version__))
    log_directory: str = ""
    log_max_mb: int = 5
    log_backups: int = 4
    check_updates: bool = True
    update_channel: str = "Pilot"
    text_size: int = 10

    def validate(self) -> Settings:
        for f in fields(self):
            value, default = getattr(self, f.name), getattr(Settings(), f.name)
            if type(value) is not type(default):
                # JSON integers are accepted for numeric frequency limits.
                if type(default) is float and type(value) in (float, int):
                    continue
                raise ValueError(f"Invalid value for {f.name}")
            if isinstance(value, str) and (len(value) > (32768 if f.name=="listening_presets" else 8192 if f.name=="location_overrides" else 2048) or any(ord(c) < 32 for c in value)):
                raise ValueError(f"Invalid text in {f.name}")
        bounds = {"port": (1, 65535), "poll_seconds": (15, 3600), "lead_ms": (0, 5000),
                  "tail_ms": (0, 5000), "max_tx_seconds": (5, 120), "speech_rate": (-10, 10),
                  "cw_wpm": (5, 50), "cw_hz": (300, 1500), "id_minutes": (1, 30), "voice_id_minutes": (1, 120),
                  "max_age_seconds": (30, 600), "repeat_seconds": (30, 3600),
                  "spacing_seconds": (0, 120), "volume_percent": (0, 100),
                  "cw_volume_percent": (0, 100), "voice_id_volume_percent": (0, 100),
                  "local_volume_percent": (0, 100), "character_pause_ms": (0, 1000),
                  "group_pause_ms": (0, 3000), "display_limit": (50, 5000),
                  "log_max_mb": (1, 100), "log_backups": (1, 30), "text_size": (10, 18), "receive_threshold_db": (-60, -5), "receive_quiet_seconds": (5, 10)}
        for name, (low, high) in bounds.items():
            if not low <= getattr(self, name) <= high:
                raise ValueError(f"{name.replace('_', ' ')} must be between {low} and {high}")
        for name, options in {"source_type": ("TCP/Telnet", "HTTPS JSON"),
                              "ptt_method": ("VOX", "RTS", "DTR", "RTS+DTR"),
                              "voice_mode": ("Speech", "WAV"),
                              "speech_provider": ("Windows", "eSpeak NG", "Piper", "Recorded", "ElevenLabs"),
                              "frequency_unit": ("kHz", "MHz"),
                              "update_channel": ("Pilot", "Stable"),
                              "keep_awake": ("Off", "Computer", "Computer and display"),
                              "voice_gender": ("Any", "Male", "Female"),
                              "id_mode": ("CW", "Voice", "Alternate", "Both", "Independent")}.items():
            if getattr(self, name) not in options:
                raise ValueError(f"Choose a valid {name.replace('_', ' ')}")
        if not all(math.isfinite(v) for v in (self.min_khz, self.max_khz)) or not 1 <= self.min_khz <= self.max_khz <= 10000000:
            raise ValueError("Frequency filter must be between 1 and 10000000 kHz")
        from .filtering import choices, BANDS, MODES, ACTIVITIES
        choices(self.filter_bands, (*BANDS, "Other"))
        choices(self.filter_modes, MODES)
        choices(self.filter_activities, ACTIVITIES)
        from .privileges import validate_license
        from .geography import validate_geography
        validate_license(self)
        validate_geography(self)
        from .listening import validate_presets
        validate_presets(self.listening_presets)
        self.validate_format()
        if self.log_directory and not Path(self.log_directory).is_absolute():
            raise ValueError("Choose an absolute history folder path")
        return self

    def validate_format(self):
        if (not isinstance(self.announcement_order, str) or
                sorted(self.announcement_order.split(",")) != ["callsign", "frequency", "intro"]):
            raise ValueError("Announcement order must contain Intro, Callsign and Frequency once each")
        for name in ("include_intro", "include_callsign", "include_frequency", "speak_units"):
            if type(getattr(self, name)) is not bool:
                raise ValueError("Choose whether to include each announcement section")
        if not isinstance(self.announcement_intro, str) or len(self.announcement_intro) > 80 or any(
                ord(c) < 32 for c in self.announcement_intro):
            raise ValueError("Use a single line intro of up to 80 characters")
        if self.include_intro and not self.announcement_intro.strip():
            raise ValueError("Enter intro text or uncheck Intro")
        if not (self.include_intro or self.include_callsign or self.include_frequency):
            raise ValueError("Include at least one announcement section")
        return self

    def validate_connection(self):
        self.validate()
        if self.source_type == "TCP/Telnet":
            if not self.host or re.search(r"[\s/:@]", self.host):
                raise ValueError("Enter a hostname without a URL prefix or port")
            if self.login and not valid_call(self.login):
                raise ValueError("Enter a callsign for cluster sign in")
        else:
            url = urlsplit(self.feed_url)
            if url.scheme != "https" or not url.hostname or url.username or url.password or url.fragment:
                raise ValueError("Enter an HTTPS feed URL without embedded credentials or a fragment")

    def validate_rf(self):
        self.validate()
        if self.receive_guard and not self.receive_device:
            raise ValueError("Choose a receive audio input or turn off receive monitoring")
        if not self.radio_device:
            raise ValueError("Choose a radio audio device")
        if self.ptt_method != "VOX":
            windows_port = re.fullmatch(r"COM[1-9]\d{0,2}", self.serial_port, re.I)
            linux_port = sys.platform.startswith('linux') and re.fullmatch(r'/dev/(?:tty(?:USB|ACM|S)\d+|rfcomm\d+|serial/by-id/[A-Za-z0-9_.:+-]+)', self.serial_port)
            if not (windows_port or linux_port): raise ValueError("Choose a serial port for PTT")
        if self.id_mode in ("CW", "Both", "Alternate", "Independent"):
            from .audio import validate_morse
            validate_morse(self.cw_text)
        if self.id_mode in ("Voice", "Both", "Alternate", "Independent"):
            if self.voice_mode == "Speech" and not self.voice_text.strip():
                raise ValueError("Enter voice ID text")
            if self.voice_mode == "WAV" and not Path(self.voice_wav).is_file():
                raise ValueError("Choose an existing WAV ID file")


def settings_path() -> Path:
    if sys.platform.startswith('linux') and not os.environ.get('LOCALAPPDATA'):
        return Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config')) / 'dxtalker/settings.json'
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "DXTalker" / "settings.json"


def load_settings(path: Path | None = None) -> Settings:
    path = path or settings_path()
    if not path.exists():
        return Settings()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported settings version. Move settings.json aside to use defaults.")
    names = {f.name for f in fields(Settings)}
    values = {k: v for k, v in data.items() if k in names}
    if sys.platform.startswith('linux') and values.get('speech_provider') == 'Windows': values['speech_provider'] = 'eSpeak NG'
    return Settings(**values).validate()


def save_settings(settings: Settings, path: Path | None = None):
    settings.validate()
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"schema_version": 1, **asdict(settings)}, indent=2), encoding="utf-8")
    temporary.replace(path)
