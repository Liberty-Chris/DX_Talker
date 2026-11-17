"""App selection policy supplied by WB4IUY, separate from license authorizations."""
from collections import defaultdict
from decimal import Decimal
from .band_table_data import RULES

INDEX = defaultdict(list)
for cls, mode, low, high, reference, result in RULES:
    INDEX[cls, mode].append((Decimal(low), Decimal(high), reference == 'point', result))


def policy_eligibility(frequency, mode, license_class):
    if license_class == 'Off': return 'eligible'
    f = Decimal(str(frequency))
    results = {result for low, high, point, result in INDEX[license_class, mode]
               if (f == low if point else low <= f < high)}
    return 'eligible' if 'Eligible' in results else 'unknown' if 'Unverified' in results else 'outside'
