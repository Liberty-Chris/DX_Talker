import unittest
from dxtalker.protocol import LineFramer, TelnetDecoder


class ProtocolTests(unittest.TestCase):
    def test_telnet_handles_every_split_point(self):
        data = b"DX\xff\xfb\x01 de\xff\xfd\x03 W4MR\xff\xfa\x01secret\xff\xf0:"
        for split in range(len(data) + 1):
            decoder = TelnetDecoder()
            a, ar = decoder.feed(data[:split])
            b, br = decoder.feed(data[split:])
            self.assertEqual(a+b, b"DX de W4MR:")
            self.assertEqual(ar+br, b"\xff\xfe\x01\xff\xfc\x03")

    def test_negotiation_refusals_do_not_loop(self):
        self.assertEqual(TelnetDecoder().feed(b"\xff\xfc\x01\xff\xfe\x03"), (b"", b""))

    def test_iac_escape(self):
        self.assertEqual(TelnetDecoder().feed(b"A\xff\xffB"), (b"A\xffB", b""))

    def test_fragmented_lines_and_crlf(self):
        f = LineFramer()
        self.assertEqual(f.feed(b"one\r"), ["one"])
        self.assertEqual(f.feed(b"\ntwo\r\0three\nfo"), ["two", "three"])
        self.assertEqual(f.partial, "fo")
        self.assertEqual(f.feed(b"ur\n"), ["four"])

    def test_oversized_line_is_dropped_entirely(self):
        f = LineFramer(limit=8)
        self.assertEqual(f.feed(b"x" * 100000), [])
        self.assertLessEqual(len(f.buffer), 8)
        self.assertEqual(f.feed(b"malice\nvalid\n"), ["valid"])

    def test_every_byte_can_arrive_separately(self):
        f = LineFramer()
        lines = []
        for byte in b"DX de N0CALL: 7074 KT4BN CQ 0000Z\r\n":
            lines += f.feed(bytes([byte]))
        self.assertEqual(len(lines), 1)
