"""The receive monitor's small stream interface, backed by selected WinMM input."""
import threading
from . import winmm

_selection = threading.local()
query_hostapis = winmm.query_hostapis

def query_devices():
    devices = winmm.query_devices()
    _selection.devices = devices
    return devices

class RawInputStream(winmm.RawInputStream):
    def __init__(self, device, **options):
        devices = getattr(_selection, 'devices', None)
        if devices is None or not isinstance(device, int) or not 0 <= device < len(devices):
            raise ValueError('Refresh and select a unique receive input')
        # Retain the named selection across a fresh device enumeration rather
        # than treating a changing combined input/output index as an identity.
        winmm.RawInputStream.__init__(self, device=devices[device], **options)
