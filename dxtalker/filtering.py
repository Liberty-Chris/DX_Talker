"""Local spot classification. Comments are metadata, never announcement text."""
import re
from decimal import Decimal, InvalidOperation

BANDS = {"160m": (1800, 2000), "80m": (3500, 4000), "60m": (5250, 5450),
         "40m": (7000, 7300), "30m": (10100, 10150), "20m": (14000, 14350),
         "17m": (18068, 18168), "15m": (21000, 21450), "12m": (24890, 24990),
         "10m": (28000, 29700), "6m": (50000, 54000), "4m": (70000, 70500),
         "2m": (144000, 148000), "1.25m": (222000, 225000), "70cm": (420000, 450000),
         "33cm": (902000, 928000), "23cm": (1240000, 1300000)}
MODES = ("CW", "SSB", "FT8", "FT4", "RTTY", "PSK", "FM", "AM", "Unknown")
ACTIVITIES = ("POTA", "SOTA", "FOTA", "General")
MODE_WORD = re.compile(r"(?<![A-Z0-9])(?:CW|SSB|USB|LSB|FT8|FT4|RTTY|PSK(?:31|63|125)?|FM|AM)(?![A-Z0-9])", re.I)
# US operating practice inference, separate from FCC license privileges.
# ARRL preferred ranges with documented digital overlaps left Unknown.
# Lower inclusive, upper exclusive, in kHz. Sources and limits: docs/mode_inference.md.
MODE_SEGMENTS = (
    (1810, 1836, 'CW'),
    (3500, 3570, 'CW'),
    (7000, 7040, 'CW'),
    (10100, 10130, 'CW'),
    (14000, 14070, 'CW'),
    (18068, 18095, 'CW'),
    (21000, 21070, 'CW'),
    (24890, 24915, 'CW'),
    (28000, 28070, 'CW'),
    (50000, 50100, 'CW'),
    (144000, 144100, 'CW'),
)
# Recognize unsupported modes as evidence against guessing CW from frequency.
OTHER_MODE_WORD = re.compile(r'(?<![A-Z0-9])(?:FT2|FT9|JT\d+[A-Z]*|JS8(?:CALL)?|WSPR|Q65|QRA64|MSK144|FSK441|OLIVIA|MFSK\d*|SSTV|FAX|DIGI(?:TAL)?|DATA|DMR|DSTAR|D-STAR|C4FM|FUSION|DV)(?![A-Z0-9])', re.I)


def clean_comment(value):
    return ''.join(c for c in value if 32 <= ord(c) <= 126)[:160] if isinstance(value, str) else ''


def mode_of(comment, explicit='', frequency_khz=None):
    def normalized(word):
        word = word.upper()
        return 'SSB' if word in ('USB', 'LSB') else 'PSK' if word.startswith('PSK') else word
    if explicit:
        return normalized(explicit) if MODE_WORD.fullmatch(explicit) else 'Unknown'
    found = {normalized(m.group()) for m in MODE_WORD.finditer(comment)}
    if OTHER_MODE_WORD.search(comment):
        return 'Unknown'
    if found:
        return next(iter(found)) if len(found) == 1 else 'Unknown'
    try:
        frequency = Decimal(str(frequency_khz))
        if frequency.is_finite():
            return next((mode for low, high, mode in MODE_SEGMENTS if low <= frequency < high), 'Unknown')
    except InvalidOperation:
        pass
    return 'Unknown'


def activities_of(comment):
    return {name for name in ACTIVITIES[:-1] if re.search(r'(?<![A-Z0-9])'+name+r'(?![A-Z0-9])', comment, re.I)} or {'General'}


def choices(value, allowed):
    if value == 'None':
        return {'None'}
    values = value.split(',') if value else []
    if len(values) != len(set(values)) or any(v not in allowed for v in values):
        raise ValueError('Invalid spot filter selection')
    return set(values)


def activity_tags(comment):
    return tuple(name for name in ("POTA", "FOTA", "SOTA") if name in activities_of(comment))


def activity_style(settings):
    selected=choices(settings.filter_activities,ACTIVITIES)
    return settings.activity_announcements or bool(selected) and selected <= {'POTA','FOTA','SOTA'}


def rejection(spot, settings):
    bands = choices(settings.filter_bands, (*BANDS, 'Other'))
    modes = choices(settings.filter_modes, MODES)
    activities = choices(settings.filter_activities, ACTIVITIES)
    band = next((name for name, (low, high) in BANDS.items() if low <= spot.frequency_khz < high), 'Other')
    if not settings.min_khz <= spot.frequency_khz <= settings.max_khz:return 'Frequency range'
    if bands and band not in bands:return 'Band'
    mode=mode_of(spot.comment, spot.mode, spot.frequency_khz)
    if mode=='Unknown' and 'Unknown' not in modes:return 'Mode unknown'
    if modes and mode not in modes:return 'Mode unknown' if mode=='Unknown' else 'Mode'
    if activities and not activities & activities_of(spot.comment):return 'Activity tag'
    from .privileges import eligibility
    eligible=eligibility(spot.frequency_khz,mode,settings.license_class,settings.license_region)
    if eligible=='outside':return 'Outside selected license segments'
    if eligible=='unknown' and not settings.license_unknown:return 'License eligibility unverified'
    from .geography import rejection as location_rejection
    return location_rejection(spot,settings)


def matches(spot,settings):return not rejection(spot,settings)


def mode_summary(value):
    selected=choices(value,MODES)
    if selected==set(MODES):return 'All modes, including unknown'
    if not selected or selected==set(MODES)-{'Unknown'}:return 'Known modes only'
    if selected=={'None'}:return 'No modes'
    return value.replace('Unknown','Include unknown')


def summary(settings):
    parts=['License filter: '+settings.license_class] if settings.license_class!='Off' else []
    for key,default in (('filter_bands','All bands'),('filter_modes','All known modes'),('filter_activities','All activities')):
        parts.append(mode_summary(settings.filter_modes) if key=='filter_modes' else getattr(settings,key).replace('General','No activity tag') or default)
    for key,title in (('filter_spotter_countries','Reported from'),('filter_spotter_continents','Reporting continents'),('filter_spotter_regions','Reporting regions'),('filter_dx_countries','DX countries'),('filter_dx_continents','DX continents')):
        if getattr(settings,key):parts.append(title+': '+getattr(settings,key))
    return ' · '.join(parts)
