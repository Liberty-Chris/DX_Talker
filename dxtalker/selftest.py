"""Windows package smoke check. Does not play audio, open a serial port or connect."""
import json
import os
from pathlib import Path
import tempfile
import threading
import traceback
import subprocess


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
                assert app.save_button.winfo_rooty() + app.save_button.winfo_height() <= root.winfo_rooty() + root.winfo_height()
                assert set(app.variables) == {f.name for f in fields(Settings)}
                assert not app.engine.enabled
                app._samples()
                assert len(app.spots) == 3
                assert app._read_settings() == Settings()
                app._apply()
                assert (Path(folder) / "DXTalker/settings.json").exists()
                root.lift()
                root.update()
                # Capture only the synthetic runner UI for layout review. No audio
                # endpoint or radio connection is opened by this operation.
                image = str(Path(report_path).resolve().with_suffix(".png"))
                script = r'''
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap ([int]$env:DX_WIDTH), ([int]$env:DX_HEIGHT)
$g = [System.Drawing.Graphics]::FromImage($bmp)
try {
  $g.CopyFromScreen([int]$env:DX_X, [int]$env:DX_Y, 0, 0, $bmp.Size)
  $bmp.Save($env:DX_IMAGE, [System.Drawing.Imaging.ImageFormat]::Png)
} finally { $g.Dispose(); $bmp.Dispose() }
'''
                env = {**os.environ, "DX_IMAGE": image, "DX_X": str(root.winfo_rootx()),
                       "DX_Y": str(root.winfo_rooty()), "DX_WIDTH": str(root.winfo_width()),
                       "DX_HEIGHT": str(root.winfo_height())}
                shell = str(Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe")
                capture = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-Command", script], env=env,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                report["screenshot"] = capture.returncode == 0 and Path(image).exists()
                app.notebook.select(3)
                root.update()
                env["DX_IMAGE"] = str(Path(image).with_name(Path(image).stem + "_identification.png"))
                capture = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-Command", script], env=env,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                report["identification_screenshot"] = capture.returncode == 0 and Path(env["DX_IMAGE"]).exists()
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
