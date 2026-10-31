"""Windows package smoke check. Does not play audio, open a serial port or connect."""
import json
import os
from pathlib import Path
import tempfile
import threading
import traceback


def run(report_path):
    report = {"ok": False}
    try:
        import tkinter as tk
        from dataclasses import fields
        from .app import Application
        from .audio import AudioOutput, WindowsSpeech
        from .models import Settings
        from .ptt import serial_ports

        speech = WindowsSpeech()
        voices = speech.voices(threading.Event())
        clip = speech.render("DX Talker. Kilo Foxtrot four Delta Bravo Xray.", "", 0, threading.Event())
        assert clip.duration > 0
        report.update(voices=voices, speech_seconds=clip.duration,
                      audio_outputs=AudioOutput.devices(), serial_ports=serial_ports())
        with tempfile.TemporaryDirectory() as folder:
            old_local = os.environ.get("LOCALAPPDATA")
            os.environ["LOCALAPPDATA"] = folder
            try:
                root = tk.Tk()
                app = Application(root)
                root.update()
                assert set(app.variables) == {f.name for f in fields(Settings)}
                assert not app.engine.enabled
                app._samples()
                assert len(app.spots) == 3
                assert app._read_settings() == Settings()
                app._apply()
                assert (Path(folder) / "DXTalker/settings.json").exists()
                root.after(500, app.close)
                root.mainloop()
            finally:
                if old_local is None:
                    os.environ.pop("LOCALAPPDATA", None)
                else:
                    os.environ["LOCALAPPDATA"] = old_local
        report["ok"] = True
    except Exception:
        report["error"] = traceback.format_exc()
    Path(report_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1
