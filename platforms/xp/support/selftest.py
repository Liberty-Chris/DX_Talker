"""Full shared UI/core smoke test. SAPI writes a WAV; no playback or PTT."""
import base64
import io
import json
import os
import platform
import struct
import tempfile
import threading
import time
import traceback


def run(destination):
    report = {'ok': False, 'runtime': 'Python 3.4 XP compatibility', 'bits': struct.calcsize('P') * 8}
    report['os'] = platform.platform()
    old_local = os.environ.get('LOCALAPPDATA')
    app = None
    temporary = None
    try:
        from xp_support.ssl import create_default_context
        from xp_support.sapi import WindowsSpeech
        context = create_default_context()
        import ssl
        assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
        report['tls_validation_enabled'] = True
        from dxtalker.updates import INSTALLER
        expected_installer = 'DXTalker-Setup-Windows-XP-' + ('32bit' if struct.calcsize('P') == 4 else '64bit') + '.exe'
        assert INSTALLER == expected_installer
        report['update_installer'] = INSTALLER
        with WindowsSpeech() as speech:
            voices = speech.voices(threading.Event())
            assert voices
            clip = speech.render('DX Talker. Kilo Foxtrot four Delta Bravo Xray.', '', 0, threading.Event())
            assert clip.rate == 22050 and clip.channels == 1 and clip.duration > 0
            process = speech.process.pid
            assert speech.render('Second render.', '', 0, threading.Event()).duration > 0
            assert speech.process.pid == process
            report['persistent_sapi'] = True
        import tkinter as tk
        from xp_support.dataclasses import fields
        from dxtalker.app import Application
        from dxtalker.models import Settings, save_settings
        from dxtalker.profiles import protect_secret
        temporary = tempfile.TemporaryDirectory(prefix='DXTalker_XP_check_')
        folder = temporary.name
        os.environ['LOCALAPPDATA'] = folder
        save_settings(Settings(check_updates=False))
        started = time.monotonic()
        root = tk.Tk(); app = Application.__new__(Application); app.__init__(root); root.update()
        report['ui_startup_ms'] = (time.monotonic() - started) * 1000
        assert not app.engine.enabled and not app.engine.local_enabled
        assert set(app.variables) == {field.name for field in fields(Settings)}
        app._samples(); assert len(app.spots) == 3
        for index in range(8):
            app.notebook.select(index); root.update()
        secret = protect_secret('synthetic-test-secret')
        assert protect_secret(secret, decrypt=True) == 'synthetic-test-secret'
        report['account_secret_roundtrip'] = True
        import qrcode
        from xp_support.qr_image import PyPNGImage
        image = qrcode.make('DX Talker synthetic QR test', image_factory=PyPNGImage)
        output = io.BytesIO(); image.save(output)
        photo = tk.PhotoImage(data=base64.b64encode(output.getvalue()))
        assert photo.width() > 0
        report['qr_png'] = True
        report['settings_fields'] = len(fields(Settings))
        from dxtalker.performance import measure, violations, BUDGETS
        report['performance'] = measure(app, report['ui_startup_ms'])
        report['performance_budgets'] = BUDGETS
        report['performance_failures'] = violations(report['performance'])
        assert not report['performance_failures'], 'XP UI performance budget failed'
        app.close()
        if not app.diagnostics.closed.is_set():
            root.after(5000, root.quit); root.mainloop()
        assert app.diagnostics.closed.is_set()
        app = None
        report['ok'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if app:
            try:
                app.close()
                if not app.diagnostics.closed.is_set():
                    app.root.after(5000, app.root.quit); app.root.mainloop()
            except Exception:
                try:
                    if hasattr(app, 'engine'):
                        app.engine.shutdown(); app.engine.worker.join(3)
                    if hasattr(app, 'diagnostics'): app.diagnostics.close()
                    app.root.destroy()
                except Exception: pass
        if temporary is not None:
            try: temporary.cleanup()
            except OSError:
                report['temporary_cleanup_failed'] = True
                report['ok'] = False
        if old_local is None: os.environ.pop('LOCALAPPDATA', None)
        else: os.environ['LOCALAPPDATA'] = old_local
    with open(destination, 'w', encoding='utf-8') as output: json.dump(report, output, indent=2)
    return 0 if report['ok'] else 1
