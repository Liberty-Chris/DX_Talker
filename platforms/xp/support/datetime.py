from datetime import *
import datetime as _native
import re

class datetime(_native.datetime):
    @classmethod
    def fromisoformat(cls, value):
        pattern = r'^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?)?(Z|[+-]\d{2}:\d{2}(?::\d{2})?)?$'
        match = re.fullmatch(pattern, value)
        if match is None: raise ValueError('Invalid ISO datetime')
        groups = match.groups()
        values = [int(part or 0) for part in groups[:6]]
        fraction = int((groups[6] or '').ljust(6, '0')[:6] or 0)
        zone = groups[7]
        tz = None
        if zone == 'Z': tz = timezone.utc
        elif zone:
            pieces = [int(part) for part in zone[1:].split(':')]
            if pieces[0] > 23 or any(part > 59 for part in pieces[1:]): raise ValueError('Invalid ISO offset')
            offset = timedelta(hours=pieces[0], minutes=pieces[1], seconds=pieces[2] if len(pieces) > 2 else 0)
            tz = timezone(offset if zone[0] == '+' else -offset)
        return cls(*(values + [fraction]), tzinfo=tz)
