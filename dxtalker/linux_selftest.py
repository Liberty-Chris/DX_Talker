"""Ubuntu package verification. Synthetic keyring data and WAV only; no audio/PTT."""
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import traceback

def run(destination):
    report = {'ok': False}
    app = None
    previous = os.environ.get('LOCALAPPDATA')
    temporary = tempfile.TemporaryDirectory(prefix='DXTalker_ubuntu_check_')
    try:
        import tkinter as tk
        from .linux_speech import EspeakSpeech
        from .linux_desktop import protect_secret, forget_secret
        from .models import Settings, save_settings
        from .app import Application
        from .performance import measure, violations, BUDGETS
        from .updates import INSTALLER, update_ssl_context
        speech = EspeakSpeech(); cancel = threading.Event()
        assert speech.voices(cancel)
        clip = speech.render('DX Talker. Kilo Foxtrot four Delta Bravo Xray.', '', 0, cancel)
        assert clip.duration > 0 and clip.channels == 1 and clip.rate == 22050
        from .speech import SpeechService
        service = SpeechService()
        try: assert service.render_configured('DX Talker [pause 500ms] test', Settings(), cancel).duration > 0
        finally: service.close()
        report['offline_speech'] = True
        reference = protect_secret('synthetic-keyring-test')
        try: assert protect_secret(reference, decrypt=True) == 'synthetic-keyring-test'
        finally: forget_secret(reference)
        report['desktop_keyring'] = True
        context = update_ssl_context()
        assert context.check_hostname
        assert INSTALLER == 'DXTalker-Ubuntu-amd64.deb'
        os.environ['LOCALAPPDATA'] = temporary.name
        save_settings(Settings(check_updates=False))
        start = time.perf_counter()
        root = tk.Tk(className='DXTalker'); app = Application(root); root.update()
        startup = (time.perf_counter() - start) * 1000
        assert not app.engine.enabled and not app.engine.local_enabled
        app._samples(); assert len(app.spots) == 3
        for index in range(8): app.notebook.select(index); root.update()
        import qrcode
        from qrcode.image.pure import PyPNGImage
        output = io.BytesIO(); qrcode.make('synthetic profile collection', image_factory=PyPNGImage).save(output)
        report['qr_png'] = output.getvalue().startswith(b'\x89PNG')
        report['performance'] = measure(app, startup)
        report['performance_budgets'] = BUDGETS
        report['performance_failures'] = violations(report['performance'])
        assert not report['performance_failures']
        app.close()
        if not app.diagnostics.closed.is_set(): root.after(5000, root.quit); root.mainloop()
        assert app.diagnostics.closed.is_set()
        app = None
        report['ok'] = True
    except Exception: report['error'] = traceback.format_exc()
    finally:
        if app:
            try:
                app.close()
                if not app.diagnostics.closed.is_set(): app.root.after(5000, app.root.quit); app.root.mainloop()
                app.diagnostics.close()
            except Exception: pass
        if previous is None: os.environ.pop('LOCALAPPDATA', None)
        else: os.environ['LOCALAPPDATA'] = previous
        temporary.cleanup()
        Path(destination).write_text(json.dumps(report, indent=2))
    return 0 if report['ok'] else 1
