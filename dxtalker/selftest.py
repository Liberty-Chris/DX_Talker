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
        from . import updates
        import ssl
        context = updates.update_ssl_context()
        assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
        report["update_certificate_verification"] = True
        import tkinter as tk
        from dataclasses import fields
        from .app import Application
        from .audio import AudioOutput, WindowsSpeech
        from .models import Settings, save_settings, parse_line, UTC
        from .speech import SpeechService
        from .profiles import protect_secret
        from datetime import datetime
        from .appearance import load_appearance
        from .ptt import serial_ports

        speech = WindowsSpeech()
        voices = speech.voices(threading.Event())
        clip = speech.render("DX Talker. Kilo Foxtrot four Delta Bravo Xray.", "", 0, threading.Event())
        assert clip.duration > 0
        secret = protect_secret("synthetic-test-secret")
        assert "synthetic-test-secret" not in secret
        assert protect_secret(secret, decrypt=True) == "synthetic-test-secret"
        now = datetime.now(UTC)
        spot = parse_line(f"DX de N0CALL: 14025.5 WB4IUY/P {now:%H%M}Z", "test", now)
        paced = SpeechService().render_spot(spot, Settings(character_pause_ms=50, group_pause_ms=450), threading.Event())
        assert paced.duration > 0
        report["ssml_speech_seconds"] = paced.duration
        report["protected_secret_roundtrip"] = True
        report.update(voices=voices, speech_seconds=clip.duration,
                      audio_outputs=AudioOutput.devices(), serial_ports=serial_ports())
        with tempfile.TemporaryDirectory() as folder:
            old_local = os.environ.get("LOCALAPPDATA")
            os.environ["LOCALAPPDATA"] = folder
            try:
                save_settings(Settings(check_updates=False))
                root = tk.Tk()
                app = Application(root)
                root.update()
                assert app.save_button.winfo_rooty() + app.save_button.winfo_height() <= root.winfo_rooty() + root.winfo_height()
                assert set(app.variables) == {f.name for f in fields(Settings)}
                assert not app.engine.enabled
                app._samples()
                assert len(app.spots) == 3
                assert app._read_settings() == Settings(check_updates=False)
                app._apply()
                assert app.icon.width() == 256
                for theme in ("Light", "Dark", "High contrast"):
                    app.theme.set(theme)
                    app._change_theme()
                    root.update()
                    assert load_appearance() == theme
                    assert not app.engine.enabled
                    assert app.brand_label.cget("image")
                report["appearance"] = ["Light", "Dark", "High contrast"]
                normal_geometry = root.geometry()
                root.geometry("900x600")
                root.update()
                for index in range(len(app.notebook.tabs())):
                    app.notebook.select(index)
                    root.update()
                    for control in (app.save_button, app.stop_button, app.theme_picker):
                        assert control.winfo_ismapped()
                        assert control.winfo_rooty() + control.winfo_height() <= root.winfo_rooty() + root.winfo_height()
                        assert control.winfo_rootx() + control.winfo_width() <= root.winfo_rootx() + root.winfo_width()
                report["small_window_controls"] = True
                root.geometry(normal_geometry)
                app.notebook.select(0)
                root.update()
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
                app.notebook.select(0)
                app.theme.set("Light")
                app._change_theme()
                root.update()
                env["DX_IMAGE"] = str(Path(image).with_name(Path(image).stem + "_light.png"))
                capture = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-Command", script], env=env,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                report["light_screenshot"] = capture.returncode == 0 and Path(env["DX_IMAGE"]).exists()
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
