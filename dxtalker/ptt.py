"""Explicitly selected serial, CM108 GPIO3 and VOX PTT adapters."""

import hashlib
import sys
import threading


CM108_METHOD = "CM108 HID"
CM108_VENDOR = 0x0D8C
CM108B_PRODUCT = 0x0012
GPIO3 = 0x04


def cm108_supported():
    # The separate Windows XP build uses Python 3.4 and has no HIDAPI runtime.
    return sys.platform == "win32" and sys.version_info >= (3, 10)


def cm108_devices():
    """Return display names and HID paths without opening or keying devices."""
    if not cm108_supported():
        return {}
    try:
        import hid
        devices = hid.enumerate(CM108_VENDOR, CM108B_PRODUCT)
    except (ImportError, OSError) as exc:
        raise ValueError("CM108 USB discovery failed. Check the DX Talker installation.") from exc
    choices = {}
    for device in devices:
        path = device["path"]
        name = device["product_string"] or "USB Audio Device"
        # The chip typically has no serial number. Scope this choice to the
        # Windows HID path so identical names cannot select a different unit.
        identifier = hashlib.sha256(path.lower()).hexdigest()[:12]
        choices[f"{name} [{identifier}]"] = path
    return choices


class Cm108PTT:
    def __init__(self, name):
        self.name = name
        self.device = None
        self.lock = threading.Lock()

    def open(self):
        path = cm108_devices().get(self.name)
        if path is None:
            raise ValueError("Selected CM108 USB PTT device is unavailable. Refresh devices and select the DigiRig Lite.")
        import hid
        try:
            device = hid.device()
            device.open_path(path)
        except OSError as exc:
            raise ValueError("Could not open the selected CM108 USB PTT device. Check its USB connection and close other radio apps.") from exc
        self.device = device
        try:
            self.set(False)
        except Exception:
            self.close()
            raise

    def _write(self, keyed):
        # Unnumbered HID output report: operation, GPIO values, directions, SPDIF.
        report = bytes((0, 0, GPIO3 if keyed else 0, GPIO3, 0))
        try:
            written = self.device.write(report)
        except OSError as exc:
            raise ValueError("CM108 USB PTT write failed. Check the DigiRig Lite connection.") from exc
        if written != len(report):
            raise ValueError("CM108 USB PTT write was incomplete. Check the DigiRig Lite connection.")

    def set(self, keyed):
        with self.lock:
            if self.device is not None:
                self._write(keyed)

    def close(self):
        with self.lock:
            if self.device is not None:
                try:
                    self._write(False)
                finally:
                    device, self.device = self.device, None
                    device.close()


class VoxPTT:
    def open(self):
        pass

    def set(self, keyed):
        pass

    def close(self):
        pass


class SerialPTT:
    def __init__(self, port, method, active_high=True):
        self.port, self.method, self.active_high = port, method, active_high
        self.serial = None

    def open(self):
        import serial
        # Set initial idle line levels before opening. Some USB drivers can still
        # pulse lines during open; bench verification is required for each interface.
        self.serial = serial.Serial(port=None, baudrate=9600, timeout=0, write_timeout=0.5)
        self.serial.rts = not self.active_high if "RTS" in self.method else False
        self.serial.dtr = not self.active_high if "DTR" in self.method else False
        self.serial.port = self.port
        try:
            self.serial.open()
            self.set(False)
        except Exception:
            self.close()
            raise

    def set(self, keyed):
        level = self.active_high if keyed else not self.active_high
        if "RTS" in self.method:
            self.serial.rts = level
        if "DTR" in self.method:
            self.serial.dtr = level

    def close(self):
        if self.serial:
            port = self.serial
            failure = None
            try:
                if port.is_open:
                    for line in ("RTS", "DTR"):
                        if line in self.method:
                            try:
                                setattr(port, line.lower(), not self.active_high)
                            except Exception as exc:
                                failure = exc
            finally:
                self.serial = None
                port.close()
            if failure:
                raise failure


def create_ptt(settings):
    if settings.ptt_method == "VOX":
        return VoxPTT()
    if settings.ptt_method == CM108_METHOD:
        return Cm108PTT(settings.hid_ptt_device)
    return SerialPTT(settings.serial_port, settings.ptt_method, settings.active_high)


def serial_ports():
    from serial.tools.list_ports import comports
    return [p.device for p in comports()]
