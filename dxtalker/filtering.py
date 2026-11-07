"""Local spot classification. Comments are metadata, never announcement text."""
import re

BANDS = {"160m": (1800, 2000), "80m": (3500, 4000), "60m": (5250, 5450),
         "40m": (7000, 7300), "30m": (10100, 10150), "20m": (14000, 14350),
         "17m": (18068, 18168), "15m": (21000, 21450), "12m": (24890, 24990),
         "10m": (28000, 29700), "6m": (50000, 54000), "4m": (70000, 70500),
         "2m": (144000, 148000), "1.25m": (222000, 225000), "70cm": (420000, 450000),
         "33cm": (902000, 928000), "23cm": (1240000, 1300000)}
MODES = ("CW", "SSB", "FT8", "FT4", "RTTY", "PSK", "FM", "AM", "Unknown")
ACTIVITIES = ("POTA", "SOTA", "FOTA", "General")
MODE_WORD = re.compile(r"(?<![A-Z0-9])(?:CW|SSB|USB|LSB|FT8|FT4|RTTY|PSK(?:31|63|125)?|FM|AM)(?![A-Z0-9])", re.I)


def clean_comment(value):
    return ''.join(c for c in value if 32 <= ord(c) <= 126)[:160] if isinstance(value, str) else ''


def mode_of(comment, explicit=''):
    def normalized(word):
        word = word.upper()
        return 'SSB' if word in ('USB', 'LSB') else 'PSK' if word.startswith('PSK') else word
    if explicit:
        return normalized(explicit) if MODE_WORD.fullmatch(explicit) else 'Unknown'
    found = {normalized(m.group()) for m in MODE_WORD.finditer(comment)}
    return next(iter(found)) if len(found) == 1 else 'Unknown'


def activities_of(comment):
    return {name for name in ACTIVITIES[:-1] if re.search(r'(?<![A-Z0-9])'+name+r'(?![A-Z0-9])', comment, re.I)} or {'General'}


def choices(value, allowed):
    values = value.split(',') if value else []
    if len(values) != len(set(values)) or any(v not in allowed for v in values):
        raise ValueError('Invalid spot filter selection')
    return set(values)


def matches(spot, settings):
    bands = choices(settings.filter_bands, (*BANDS, 'Other'))
    modes = choices(settings.filter_modes, MODES)
    activities = choices(settings.filter_activities, ACTIVITIES)
    band = next((name for name, (low, high) in BANDS.items() if low <= spot.frequency_khz <= high), 'Other')
    return (not bands or band in bands) and (not modes or mode_of(spot.comment, spot.mode) in modes) and (not activities or bool(activities & activities_of(spot.comment)))
