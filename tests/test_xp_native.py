"""XP APIs are simulated here. No native audio endpoint or serial port is opened."""
import ctypes as C
import io
import tempfile
import threading
import time
import unittest
from platforms.xp.support import winmm, serial, sapi
from platforms.xp.support.pathlib import Path as XPPath
from dxtalker.audio import Clip, Cancelled

class MM:
    def __init__(self): self.calls=[]; self.headers=[]; self.finish=True; self.fail=set()
    def waveOutGetNumDevs(self): return 1
    def waveInGetNumDevs(self): return 1
    def caps(self, identifier, pointer, size):
        value=pointer._obj
        for index,char in enumerate('Synthetic device'): value.name[index]=ord(char)
        value.channels=2; value.formats=0x40
        return 0
    waveOutGetDevCapsW=caps
    waveInGetDevCapsW=caps
    def opened(self, pointer, *args): pointer._obj.value=42; self.calls.append('open'); return 0
    waveOutOpen=opened
    waveInOpen=opened
    def prepared(self, handle, pointer, size): self.calls.append('prepare'); self.headers.append(pointer._obj); return 0
    waveOutPrepareHeader=prepared
    waveInPrepareHeader=prepared
    def waveOutWrite(self, handle, pointer, size):
        self.calls.append('write')
        if self.finish: pointer._obj.flags |= 1
        return 0
    def waveInAddBuffer(self, handle, pointer, size): pointer._obj.flags &= ~1; return 0
    def waveInStart(self, handle):
        for header in self.headers:
            C.memset(header.data,0,header.length); header.recorded=header.length; header.flags |= 1
        return 0
    def reset(self, handle): self.calls.append('reset'); return 1 if 'reset' in self.fail else 0
    waveOutReset=reset
    waveInReset=reset
    def unprepare(self, *args): self.calls.append('unprepare'); return 1 if 'unprepare' in self.fail else 0
    waveOutUnprepareHeader=unprepare
    waveInUnprepareHeader=unprepare
    def close(self, handle): self.calls.append('close'); return 1 if 'close' in self.fail else 0
    waveOutClose=close
    waveInClose=close

class Kernel:
    def __init__(self): self.calls=[]; self.fail=None
    def CreateFileW(self,*args): self.calls.append('open'); return 42
    def GetCommState(self,handle,state): return 1
    def SetCommState(self,handle,state): self.flags=state._obj.flags; self.calls.append('configure'); return 1
    def EscapeCommFunction(self,handle,command):
        self.calls.append(command)
        return 0 if command==self.fail else 1
    def CloseHandle(self,handle): self.calls.append('close'); return 1

class XPNativeTests(unittest.TestCase):
    def test_path_string_normalization_and_atomic_file_replace(self):
        path = XPPath(r'C:\Users\Operator\DXTalker')
        self.assertEqual(path.replace('\\', '/'), 'C:/Users/Operator/DXTalker')
        self.assertEqual(path.replace('Operator', 'Dad', 1), str(path).replace('Operator', 'Dad', 1))
        with tempfile.TemporaryDirectory() as folder:
            source = XPPath(folder) / 'pending.json'
            destination = XPPath(folder) / 'settings.json'
            source.write_text('synthetic settings', encoding='utf-8')
            self.assertEqual(source.replace(destination), destination)
            self.assertFalse(source.exists())
            self.assertEqual(destination.read_text(encoding='utf-8'), 'synthetic settings')

    def test_qr_png_encoder_preserves_modules_scale_and_quiet_border(self):
        import qrcode
        import png
        from platforms.xp.support.qr_image import PyPNGImage
        qr = qrcode.QRCode(box_size=3, border=4, image_factory=PyPNGImage)
        qr.add_data('synthetic collection'); qr.make(fit=True)
        image = qr.make_image(); output = io.BytesIO(); image.save(output)
        width, height, rows, metadata = png.Reader(bytes=output.getvalue()).asDirect()
        pixels = list(rows)
        self.assertEqual(width, height)
        self.assertEqual(width, (qr.modules_count + 8) * 3)
        self.assertTrue(all(value == 1 for value in pixels[0]))
        for row in range(qr.modules_count):
            for column in range(qr.modules_count):
                self.assertEqual(pixels[(row + 4) * 3][(column + 4) * 3], 0 if qr.modules[row][column] else 1)

    def tearDown(self): winmm._quarantined[:]=[]
    def test_pcm_completion_cancellation_deadline_and_cleanup(self):
        for scenario in ('complete','cancel','deadline'):
            mm=MM(); cancel=threading.Event(); mm.finish=scenario=='complete'
            if scenario=='cancel': cancel.set()
            end=time.monotonic()+(.03 if scenario=='deadline' else 1)
            output=winmm.AudioOutput(mm)
            if scenario=='complete': output.play(Clip(b'\0\0'*1024),'Windows MME :: Synthetic device',70,cancel,end)
            else:
                with self.assertRaises(Cancelled if scenario=='cancel' else TimeoutError):
                    output.play(Clip(b'\0\0'*1024),'Windows MME :: Synthetic device',70,cancel,end)
            if scenario!='cancel': self.assertEqual(mm.calls[-3:],['reset','unprepare','close'])
            else: self.assertEqual(mm.calls,[])
    def test_failed_native_cleanup_retains_buffers_and_refuses_new_audio(self):
        mm=MM();mm.fail.add('unprepare');output=winmm.AudioOutput(mm)
        with self.assertRaises(ValueError):output.play(Clip(b'\0\0'*10),'Windows MME :: Synthetic device',70,threading.Event(),time.monotonic()+1)
        self.assertEqual(mm.calls[-3:],['reset','unprepare','close'])
        self.assertTrue(winmm._quarantined)
        before=list(mm.calls)
        with self.assertRaises(ValueError):output.play(Clip(b'\0\0'*10),'Windows MME :: Synthetic device',70,threading.Event(),time.monotonic()+1)
        self.assertEqual(mm.calls,before)
    def test_receive_buffers_deliver_then_reset_and_release(self):
        mm=MM();received=[];ready=threading.Event()
        def callback(data,frames,timing,status):received.append((len(data),frames,bool(status)));ready.set()
        stream=winmm.RawInputStream(1,22050,1,'int16',1024,callback,backend=mm)
        stream.start();self.assertTrue(ready.wait(2));stream.close()
        self.assertFalse(stream.active);self.assertFalse(stream.opened)
        self.assertEqual(received[0],(2048,1024,False))
        self.assertEqual(mm.calls.count('unprepare'),4);self.assertEqual(mm.calls[-1],'close')
    def test_serial_polarities_and_failure_release_attempt_every_selected_line(self):
        for active in (True,False):
            kernel=Kernel();ptt=serial.SerialPTT('COM4','RTS+DTR',active,backend=kernel)
            ptt.open();self.assertEqual(kernel.flags,1 if active else 1|(1<<4)|(1<<12));ptt.set(True);kernel.fail=4 if active else 3
            with self.assertRaises(OSError):ptt.close()
            self.assertIsNone(ptt.handle)
            self.assertEqual(kernel.calls[-3:],[4 if active else 3,6 if active else 5,'close'])
    def test_native_layout_and_speech_pause_translation(self):
        self.assertEqual(C.sizeof(winmm.Format),18)
        self.assertEqual(C.sizeof(winmm.Header),48 if C.sizeof(C.c_void_p)==8 else 32)
        self.assertEqual(C.sizeof(winmm.OutCaps),84);self.assertEqual(C.sizeof(winmm.InCaps),80)
        self.assertEqual(C.sizeof(serial.DCB),28)
        self.assertEqual(sapi.sapi_xml('<speak>A &amp; B<break time="450ms"/> C</speak>'),'A &amp; B<silence msec="450"/> C')
        with self.assertRaises(ValueError):sapi.sapi_xml('<speak><audio src="https://example.org/"/></speak>')
