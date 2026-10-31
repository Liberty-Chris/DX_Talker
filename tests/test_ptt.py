from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dxtalker.ptt import SerialPTT


class Port:
    def __init__(self, **kwargs):
        self.is_open = False
        self.rts = self.dtr = None

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False


class PTTTests(unittest.TestCase):
    def test_lines_and_polarities_return_to_idle(self):
        for method in ("RTS", "DTR", "RTS+DTR"):
            for polarity in (True, False):
                with self.subTest(method=method, polarity=polarity), patch.dict("sys.modules", {"serial": SimpleNamespace(Serial=Port)}):
                    ptt = SerialPTT("COM4", method, polarity)
                    ptt.open()
                    port = ptt.serial
                    for line in ("RTS", "DTR"):
                        self.assertEqual(getattr(port, line.lower()), not polarity if line in method else False)
                    ptt.set(True)
                    for line in ("RTS", "DTR"):
                        self.assertEqual(getattr(port, line.lower()), polarity if line in method else False)
                    ptt.close()
                    self.assertFalse(port.is_open)
                    for line in ("RTS", "DTR"):
                        self.assertEqual(getattr(port, line.lower()), not polarity if line in method else False)
