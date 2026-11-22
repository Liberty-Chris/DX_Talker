from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from dxtalker.models import Settings
from dxtalker.ptt import CM108_METHOD, SerialPTT, cm108_devices, create_ptt


class Port:
    def __init__(self, **kwargs):
        self.is_open = False
        self.rts = self.dtr = None

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False


class PTTTests(unittest.TestCase):
    def test_cm108_selects_exact_path_and_keys_gpio3(self):
        hid = Mock()
        hid.enumerate.return_value = [
            {"path": b"first", "product_string": "USB Audio Device"},
            {"path": b"second", "product_string": "USB Audio Device"},
        ]
        port = hid.device.return_value
        port.write.side_effect = len
        idle = bytes((0, 0, 0, 4, 0))
        keyed = bytes((0, 0, 4, 4, 0))

        with patch.dict("sys.modules", {"hid": hid}), patch("dxtalker.ptt.cm108_supported", return_value=True):
            choices = cm108_devices()
            self.assertEqual(len(choices), 2)
            hid.enumerate.assert_called_once_with(0x0d8c, 0x0012)
            hid.device.assert_not_called()
            name = next(name for name, path in choices.items() if path == b"second")
            settings = Settings(ptt_method=CM108_METHOD, hid_ptt_device=name)
            settings.validate_ptt()
            ptt = create_ptt(settings)
            ptt.open()
            port.open_path.assert_called_once_with(b"second")
            ptt.set(True)
            ptt.close()
            self.assertEqual([call.args[0] for call in port.write.call_args_list], [idle, keyed, idle])
            port.close.assert_called_once_with()

            hid.device.reset_mock()
            hid.enumerate.return_value.pop()
            with self.assertRaisesRegex(ValueError, "unavailable"):
                create_ptt(settings).open()
            hid.device.assert_not_called()

    def test_cm108_short_write_still_attempts_release_and_closes(self):
        hid = Mock()
        port = hid.device.return_value
        port.write.side_effect = [5, 0, OSError("device unplugged")]
        settings = Settings(ptt_method=CM108_METHOD, hid_ptt_device="selected")

        with patch.dict("sys.modules", {"hid": hid}), patch("dxtalker.ptt.cm108_devices", return_value={"selected": b"path"}):
            ptt = create_ptt(settings)
            ptt.open()
            with self.assertRaisesRegex(ValueError, "incomplete"):
                ptt.set(True)
            with self.assertRaisesRegex(ValueError, "write failed"):
                ptt.close()
            port.write.assert_called_with(bytes((0, 0, 0, 4, 0)))
            port.close.assert_called_once_with()
            self.assertIsNone(ptt.device)

    def test_close_attempts_both_lines_even_if_one_release_fails(self):
        calls = []

        class FailingPort:
            is_open = True

            def __setattr__(self, name, value):
                calls.append(name)
                if name == "rts":
                    raise OSError("RTS failure")

            def close(self):
                calls.append("close")

        ptt = SerialPTT("COM4", "RTS+DTR")
        ptt.serial = FailingPort()
        with self.assertRaises(OSError):
            ptt.close()
        self.assertEqual(calls, ["rts", "dtr", "close"])
        self.assertIsNone(ptt.serial)

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
