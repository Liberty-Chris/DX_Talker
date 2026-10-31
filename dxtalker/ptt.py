"""Serial line PTT and explicitly selected VOX. No CAT or HID guessing."""


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
            try:
                if self.serial.is_open:
                    self.set(False)
            finally:
                self.serial.close()
                self.serial = None


def create_ptt(settings):
    return VoxPTT() if settings.ptt_method == "VOX" else SerialPTT(settings.serial_port, settings.ptt_method, settings.active_high)


def serial_ports():
    from serial.tools.list_ports import comports
    return [p.device for p in comports()]
