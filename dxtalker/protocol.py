"""Incremental bounded Telnet decoder and cluster line framing."""


class TelnetDecoder:
    def __init__(self):
        self.state = "data"
        self.command = 0

    def feed(self, data: bytes) -> tuple[bytes, bytes]:
        output, reply = bytearray(), bytearray()
        for byte in data:
            if self.state == "data":
                if byte == 255:
                    self.state = "iac"
                else:
                    output.append(byte)
            elif self.state == "iac":
                if byte == 255:
                    output.append(byte)
                    self.state = "data"
                elif byte in (251, 252, 253, 254):
                    self.command, self.state = byte, "option"
                elif byte == 250:
                    self.state = "sub"
                else:
                    self.state = "data"
            elif self.state == "option":
                # Decline WILL with DONT and DO with WONT. Never echo refusals.
                if self.command in (251, 253):
                    reply.extend((255, 254 if self.command == 251 else 252, byte))
                self.state = "data"
            elif self.state == "sub":
                if byte == 255:
                    self.state = "sub_iac"
            elif self.state == "sub_iac":
                self.state = "data" if byte == 240 else "sub"
        return bytes(output), bytes(reply)


class LineFramer:
    def __init__(self, limit=4096):
        self.buffer = bytearray()
        self.limit = limit
        self.discarding = False
        self.after_cr = False

    def feed(self, data: bytes) -> list[str]:
        lines = []
        for byte in data:
            if byte in (10, 13):
                if byte == 10 and self.after_cr:
                    self.after_cr = False
                    continue
                if not self.discarding and self.buffer:
                    lines.append(self.buffer.decode("ascii", errors="replace"))
                self.buffer.clear()
                self.discarding = False
                self.after_cr = byte == 13
            elif byte == 0 and self.after_cr:
                self.after_cr = False
            elif 32 <= byte <= 126 or byte == 9:
                self.after_cr = False
                if not self.discarding:
                    self.buffer.append(byte)
                    if len(self.buffer) > self.limit:
                        self.buffer.clear()
                        self.discarding = True
        return lines

    @property
    def partial(self):
        return self.buffer.decode("ascii", errors="replace")
