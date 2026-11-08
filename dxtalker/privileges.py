"""Frequency/emission eligibility, not permission to transmit. FCC rules checked 2026-11-07.

All intervals are kHz, lower inclusive, upper exclusive. CW still requires its
occupied bandwidth to fit. 60 m discrete channels use mode-specific dial values.
Special geographic/power/bandwidth conditions remain in Help.
"""
from decimal import Decimal

CLASSES = ('Off', 'Novice', 'Technician', 'General', 'Advanced', 'Extra')
REGIONS = ('US Region 2', 'US Region 1', 'US Region 3')
RULES_VERSION = 'FCC-2026-02-13-reviewed-2026-11-07'
# Class frequency authorizations from 97.301; emission intersections from 97.305/307.
ALLOCATIONS = {
 'Extra': [(135.7,137.8),(472,479),(1800,2000),(3500,4000),(5351.5,5366.5),(7000,7300),(10100,10150),(14000,14350),(18068,18168),(21000,21450),(24890,24990),(28000,29700)],
 'Advanced': [(135.7,137.8),(472,479),(1800,2000),(3525,3600),(3700,4000),(5351.5,5366.5),(7025,7300),(10100,10150),(14025,14150),(14175,14350),(18068,18168),(21025,21200),(21225,21450),(24890,24990),(28000,29700)],
 'General': [(135.7,137.8),(472,479),(1800,2000),(3525,3600),(3800,4000),(5351.5,5366.5),(7025,7125),(7175,7300),(10100,10150),(14025,14150),(14225,14350),(18068,18168),(21025,21200),(21275,21450),(24890,24990),(28000,29700)],
 'Novice': [(3525,3600),(7025,7125),(21025,21200),(28000,28500),(222000,225000),(1270000,1295000)],
 'Technician': [(3525,3600),(7025,7125),(21025,21200),(28000,28500)],
}
VHF = [(50000,54000),(144000,148000),(222000,225000),(420000,450000),(902000,928000),(1240000,1300000)]
DATA = [(135.7,137.8),(472,479),(1800,2000),(3500,3600),(5351.5,5366.5),(7000,7125),(10100,10150),(14000,14150),(18068,18110),(21000,21200),(24890,24930),(28000,28300)]
PHONE = [(135.7,137.8),(472,479),(1800,2000),(3600,4000),(5351.5,5366.5),(7125,7300),(14150,14350),(18110,18168),(21200,21450),(24930,24990),(28300,29700)]

def inside(f, spans):
    return any(Decimal(str(lo)) <= f < Decimal(str(hi)) for lo,hi in spans)

def validate_license(s):
    if s.license_class not in CLASSES or s.license_region not in REGIONS:
        raise ValueError('Choose an FCC license class and operating region, or turn license filtering off')

def eligibility(frequency, mode, license_class, region='US Region 2'):
    """Return eligible, outside or unknown. Unknown never silently becomes legal."""
    if license_class == 'Off': return 'eligible'
    if license_class not in ALLOCATIONS or region not in REGIONS: return 'unknown'
    f=Decimal(str(frequency)); novice=license_class in ('Novice','Technician')
    allocations=list(ALLOCATIONS[license_class])
    if license_class != 'Novice': allocations += VHF
    if region != 'US Region 2':
        allocations=[(max(lo,1810) if lo==1800 and region=='US Region 1' else lo, min(hi,1850) if hi==2000 and region=='US Region 1' else min(hi,7200) if hi==7300 else min(hi,3900 if region=='US Region 3' else 3800) if hi==4000 else hi) for lo,hi in allocations]
        allocations=[(lo,hi) for lo,hi in allocations if lo!=222000 and lo!=902000 and not(region=='US Region 1' and lo==50000)]
        allocations=[(430000,440000) if lo==420000 else (lo,hi) for lo,hi in allocations]
    # Four retained 60 m channels. CW is at center, other authorized modes at dial.
    if 5250 <= f <= 5450:
        if novice: return 'outside'
        if mode == 'Unknown':
            return 'unknown' if inside(f,[(5351.5,5366.5)]) or f in map(Decimal,('5330.5','5332','5346.5','5348','5371.5','5373','5403.5','5405')) else 'outside'
        if mode not in ('CW','SSB','FT8','FT4','RTTY','PSK'): return 'outside'
        channels=('5332','5348','5373','5405') if mode=='CW' else ('5330.5','5346.5','5371.5','5403.5')
        return 'eligible' if inside(f,[(5351.5,5366.5)]) or f in map(Decimal,channels) else 'outside'
    if not inside(f,allocations): return 'outside'
    if mode=='Unknown': return 'unknown'
    if mode=='CW': return 'eligible'
    if novice and f < 28000: return 'outside'
    if f >= 50000:
        if f < 50100 or 144000 <= f < 144100: return 'outside'
        return 'eligible' if mode in ('SSB','AM','FM','FT8','FT4','RTTY','PSK') else 'unknown'
    if mode in ('FT8','FT4','RTTY','PSK'):
        return 'eligible' if inside(f,DATA) else 'outside'
    if mode in ('SSB','AM','FM'):
        phone=PHONE+([(7075,7100)] if region!='US Region 2' else [])
        if region=='US Region 2' and 7075<=f<7100:return 'unknown'
        if novice and mode!='SSB': return 'outside'
        # FM bandwidth below 29 MHz cannot be established from a mode label.
        if mode=='FM' and f<29000: return 'unknown' if inside(f,phone) else 'outside'
        return 'eligible' if inside(f,phone) else 'outside'
    return 'unknown'
