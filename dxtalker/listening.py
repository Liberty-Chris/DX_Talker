"""Named listening presets are independent of cluster credentials and radio settings."""
import json
from dataclasses import replace
FIELDS=('min_khz','max_khz','max_age_seconds','repeat_seconds','spacing_seconds','frequency_unit','filter_bands','filter_modes','filter_activities','license_class','license_region','license_unknown','filter_dx_countries','filter_dx_continents','filter_spotter_countries','filter_spotter_continents','filter_spotter_regions','geography_unknown','location_overrides')

def validate_presets(text):
    try:
        data=json.loads(text)
        if not isinstance(data,dict) or len(data)>30:raise ValueError()
        for name,values in data.items():
            if not isinstance(name,str) or not name.strip() or len(name)>60 or any(ord(c)<32 for c in name):raise ValueError()
            if not isinstance(values,dict) or set(values)-set(FIELDS):raise ValueError()
            from .models import Settings
            replace(Settings(),**values,listening_presets='{}').validate()
        return data
    except (TypeError,ValueError):raise ValueError('Invalid listening presets') from None

def snapshot(s):return {key:getattr(s,key) for key in FIELDS}
