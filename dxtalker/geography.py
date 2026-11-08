"""Explicit location metadata. Never guesses a station's current QTH from its call."""
import re
from functools import lru_cache
CONTINENTS=('AF','AN','AS','EU','NA','OC','SA')
LOCATION_FIELDS=('dx_country','dx_continent','spotter_country','spotter_continent','spotter_region')
FILTER_LOCATIONS={'filter_'+name.replace('country','countries').replace('continent','continents').replace('region','regions'):name for name in LOCATION_FIELDS}

def tokens(value, pattern):
    if not value:return set()
    parts=value.split(',')
    if len(parts)!=len(set(parts)) or any(not re.fullmatch(pattern,p) for p in parts):
        raise ValueError('Use comma separated country codes, continent codes or region labels')
    return set(parts)

def clean_location(data):
    result={}
    for key in LOCATION_FIELDS:
        value=data.get(key,'')
        value=value.upper().strip() if isinstance(value,str) else ''
        pattern=r'[A-Z]{2}' if key.endswith('country') else r'AF|AN|AS|EU|NA|OC|SA' if key.endswith('continent') else r'[A-Z0-9 ]{1,30}'
        result[key]=value if re.fullmatch(pattern,value) else ''
    return result

@lru_cache(maxsize=8)
def overrides(text):
    result={}
    for row in text.split(';'):
        if not row.strip():continue
        try:
            call,location=row.strip().split('=')
            parts=location.split(',')
            if not 2<=len(parts)<=3:raise ValueError()
            country,continent,region=(parts+[''])[:3]
        except ValueError:raise ValueError('Locations use CALL=US,NA,NC;CALL=CA,NA,ON') from None
        from .models import valid_call
        if not valid_call(call) or call!=call.upper():raise ValueError('Use an uppercase station callsign for each known location')
        parsed=clean_location(dict(dx_country=country,dx_continent=continent,spotter_region=region))
        if country!=parsed['dx_country'] or continent!=parsed['dx_continent'] or region!=parsed['spotter_region']:
            raise ValueError('Check the country, continent and region in known station locations')
        result[call]=parsed
    return result

def validate_geography(s):
    for key,field in FILTER_LOCATIONS.items():
        selected=tokens(getattr(s,key),r'[A-Z]{2}' if field.endswith('country') else r'[A-Z0-9 ]{1,30}')
        if field.endswith('continent') and not selected<=set(CONTINENTS):raise ValueError('Choose valid continent codes')
    overrides(s.location_overrides)

def location(spot,s):
    data={field:getattr(spot,field,'') for field in LOCATION_FIELDS}
    known=overrides(s.location_overrides)
    for role,call in (('dx',spot.dx_call),('spotter',spot.spotter)):
        entry=known.get(call,{})
        for suffix,source in (('country','dx_country'),('continent','dx_continent'),('region','spotter_region')):
            key=role+'_'+suffix
            if key in data and not data[key]:data[key]=entry.get(source,'')
    return data

def rejection(spot,s):
    data=location(spot,s)
    for key,field in FILTER_LOCATIONS.items():
        selected=set(getattr(s,key).split(',')) if getattr(s,key) else set()
        if selected and (data[field] not in selected) and (data[field] or not s.geography_unknown):
            return 'Location unknown' if not data[field] else ('Reporting station location' if field.startswith('spotter') else 'DX station location')
    return ''
