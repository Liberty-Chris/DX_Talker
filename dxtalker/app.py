"""Windows desktop interface. All Tk calls stay on the main thread."""
from __future__ import annotations

from dataclasses import fields
from datetime import datetime
import json
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .audio import AudioOutput, WindowsSpeech
from .engine import Engine
from .models import UTC, Settings, load_settings, parse_line, save_settings, settings_path
from .ptt import serial_ports
from .source import SourceClient


def resource_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


class Application:
    def __init__(self, root):
        self.root = root
        root.title(f"DX Talker {__version__}")
        width = max(900, min(1160, root.winfo_screenwidth() - 60))
        height = max(600, min(830, root.winfo_screenheight() - 100))
        root.geometry(f"{width}x{height}+20+10")
        root.minsize(900, 600)
        self.events = queue.Queue(maxsize=1500)
        self.control_events = queue.SimpleQueue()
        self.source = None
        self.source_generation = 0
        self.source_ready = False
        self.spots = {}
        self.log_lines = 0
        self.closing = False
        self.initializing = True
        self.background_cancel = threading.Event()
        try:
            self.settings = load_settings()
            settings_error = ""
        except Exception:
            self.settings = Settings()
            settings_error = "Saved settings could not be loaded. Defaults are shown. Your settings file has not been replaced."
        self.engine = Engine(self.settings, self.emit)
        self.engine.rf_allowed = lambda: self.source is not None and self.source.ready.is_set()
        self.variables = {}
        self.combos = {}
        self._style()
        self._build()
        self.initializing = False
        self._refresh_devices()
        self._load_voices()
        if settings_error:
            messagebox.showwarning("Settings", settings_error)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(75, self._poll)

    def _style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background="#edf2f7")
        style.configure("TLabel", background="#edf2f7", foreground="#172a43")
        style.configure("Title.TLabel", font=("Segoe UI", 23, "bold"), background="#12243a", foreground="white")
        style.configure("Header.TLabel", background="#12243a", foreground="#c8d8e9")
        style.configure("Header.TFrame", background="#12243a")
        style.configure("TButton", padding=(12, 7))
        style.configure("Stop.TButton", background="#a52335", foreground="white", font=("Segoe UI", 11, "bold"))
        style.map("Stop.TButton", background=[("active", "#811a29")])
        style.configure("Treeview", rowheight=27, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("TNotebook.Tab", padding=(12, 9))

    def _build(self):
        header = ttk.Frame(self.root, style="Header.TFrame", padding=18)
        header.pack(fill="x")
        ttk.Label(header, text="DX Talker", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="WINDOWS PILOT  /  " + __version__, style="Header.TLabel").pack(side="left", padx=20)
        ttk.Button(header, text="STOP ALL OUTPUT", style="Stop.TButton", command=self._stop).pack(side="right")

        status = ttk.Frame(self.root, padding=(18, 12))
        status.pack(fill="x")
        self.source_status = tk.StringVar(value="Source: disconnected")
        self.output_status = tk.StringVar(value="RF disabled")
        self.activity = tk.StringVar(value="Idle")
        ttk.Label(status, textvariable=self.source_status).pack(anchor="w")
        ttk.Label(status, textvariable=self.output_status).pack(anchor="w", pady=(5, 0))
        ttk.Label(status, textvariable=self.activity).pack(anchor="w", pady=(5, 0))
        notebook = ttk.Notebook(self.root)
        self.notebook = notebook
        notebook.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.tabs = {}
        self.scroll_tabs = []
        for name in ("Live spots", "Source", "Audio and PTT", "Identification", "Announcements", "Help and Info"):
            if name in ("Live spots", "Help and Info"):
                frame = ttk.Frame(notebook, padding=16)
                notebook.add(frame, text=name)
            else:
                container = ttk.Frame(notebook)
                notebook.add(container, text=name)
                canvas = tk.Canvas(container, background="#edf2f7", highlightthickness=0)
                scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
                canvas.configure(yscrollcommand=scrollbar.set)
                scrollbar.pack(side="right", fill="y")
                canvas.pack(side="left", fill="both", expand=True)
                frame = ttk.Frame(canvas, padding=16)
                item = canvas.create_window(0, 0, window=frame, anchor="nw")
                frame.bind("<Configure>", lambda event, c=canvas: c.configure(scrollregion=c.bbox("all")))
                canvas.bind("<Configure>", lambda event, c=canvas, i=item: c.itemconfigure(i, width=event.width))
                self.scroll_tabs.append((frame, canvas))
            self.tabs[name] = frame
        self._live_tab()
        self._source_tab()
        self._audio_tab()
        self._id_tab()
        self._policy_tab()
        self._help_tab()
        footer = ttk.Frame(self.root, padding=(18, 5, 18, 12))
        footer.pack(side="bottom", fill="x", before=notebook)
        ttk.Label(footer, text="Settings apply only when saved. Passwords and tokens are never saved.").pack(side="left")
        self.save_button = ttk.Button(footer, text="Save and apply settings", command=self.guard(self._apply))
        self.save_button.pack(side="right")
        for index, (frame, canvas) in enumerate(self.scroll_tabs):
            tag = f"SettingsScroll{index}"

            def wheel(event, c=canvas):
                c.yview_scroll(-int(event.delta / 120), "units")
                return "break"

            self.root.bind_class(tag, "<MouseWheel>", wheel)

            def bind_children(widget):
                widget.bindtags((tag,) + widget.bindtags())
                for child in widget.winfo_children():
                    bind_children(child)

            bind_children(frame)

    def guard(self, action):
        def wrapped():
            try:
                action()
            except Exception as exc:
                messagebox.showerror("DX Talker", str(exc))
        return wrapped

    def _field(self, parent, row, label, name, choices=None, note=None, browse=False):
        parent.columnconfigure(1, weight=1)
        value = getattr(self.settings, name)
        var = tk.BooleanVar(value=value) if type(value) is bool else tk.StringVar(value=str(value))
        self.variables[name] = var
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 18), pady=6)
        if type(value) is bool:
            widget = ttk.Checkbutton(parent, variable=var)
        elif choices is not None:
            widget = ttk.Combobox(parent, textvariable=var, values=choices, state="readonly", width=45)
            self.combos[name] = widget
        else:
            widget = ttk.Entry(parent, textvariable=var, width=48)
        widget.grid(row=row, column=1, sticky="ew", pady=6)
        if browse:
            ttk.Button(parent, text="Browse", command=self.guard(self._browse_wav)).grid(row=row, column=2, padx=6)
        elif note:
            ttk.Label(parent, text=note, wraplength=260).grid(row=row, column=2, padx=12, sticky="w")
        var.trace_add("write", self._setting_changed)

    def _setting_changed(self, *args):
        if not self.initializing and self.engine.enabled:
            self.engine.stop("Settings changed. RF disabled. Save and apply before enabling again.")

    def _live_tab(self):
        frame = self.tabs["Live spots"]
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", pady=(0, 12))
        for text, action in (("Connect", self._connect), ("Disconnect", self._disconnect),
                             ("Load sample spots", self._samples), ("Preview selected", self._preview_spot),
                             ("Enable RF", self._enable), ("Send ID now", self.engine.identify)):
            ttk.Button(toolbar, text=text, command=self.guard(action)).pack(side="left", padx=(0, 6))
        ttk.Label(frame, text="Spots appear here before RF is enabled. Select one to preview it locally.").pack(anchor="w", pady=(0, 8))
        columns = ("time", "dx", "frequency", "spotter", "source")
        table = ttk.Frame(frame)
        table.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table, columns=columns, show="headings", height=10, selectmode="browse")
        for key, title, width in zip(columns, ("UTC", "DX callsign", "Frequency kHz", "Spotted by", "Source"), (100, 170, 170, 160, 100)):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=80)
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        # The activity journal contains application events, never raw cluster text.
        ttk.Label(frame, text="Activity").pack(anchor="w", pady=(12, 4))
        self.log = tk.Text(frame, height=5, wrap="word", state="disabled", font=("Consolas", 9), relief="flat")
        self.log.pack(fill="x")

    def _source_tab(self):
        frame = self.tabs["Source"]
        self._field(frame, 0, "Source type", "source_type", ["TCP/Telnet", "HTTPS JSON"])
        self._field(frame, 1, "Cluster hostname", "host", note="Example: w4mr.ddns.net")
        self._field(frame, 2, "Cluster port", "port", note="Example: 7373")
        self._field(frame, 3, "Cluster login callsign", "login")
        ttk.Label(frame, text="Password or HTTPS bearer token").grid(row=4, column=0, sticky="w", pady=6)
        self.secret = tk.StringVar()
        ttk.Entry(frame, textvariable=self.secret, show="*", width=48).grid(row=4, column=1, sticky="ew")
        ttk.Label(frame, text="Session only. Leave blank if not required.", wraplength=260).grid(row=4, column=2, padx=12)
        self._field(frame, 5, "HTTPS JSON feed URL", "feed_url")
        self._field(frame, 6, "HTTPS polling interval in seconds", "poll_seconds", note="Minimum 15 seconds")
        ttk.Label(frame, text="Cluster prompts are detected for callsign and password. For an unusual prompt, send a response below.\nFor HTTPS, see the documented JSON feed format in Help. Ordinary website URLs are not feeds.",
                  wraplength=900).grid(row=7, column=0, columnspan=3, sticky="w", pady=14)
        self.command = tk.StringVar()
        ttk.Label(frame, text="Manual response or cluster command").grid(row=8, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.command, show="*").grid(row=8, column=1, sticky="ew")
        ttk.Button(frame, text="Send", command=self.guard(self._send)).grid(row=8, column=2, padx=12)
        ttk.Button(frame, text="Connect using these settings", command=self.guard(self._connect)).grid(row=9, column=1, sticky="w", pady=14)

    def _audio_tab(self):
        frame = self.tabs["Audio and PTT"]
        self._field(frame, 0, "Local preview output", "preview_device", [])
        self._field(frame, 1, "Radio audio output", "radio_device", [])
        self._field(frame, 2, "PTT method", "ptt_method", ["VOX", "RTS", "DTR", "RTS+DTR"])
        self._field(frame, 3, "Serial PTT port", "serial_port", [])
        self._field(frame, 4, "PTT active high", "active_high", note="Unchecked means active low")
        self._field(frame, 5, "PTT lead time in milliseconds", "lead_ms")
        self._field(frame, 6, "PTT tail time in milliseconds", "tail_ms")
        self._field(frame, 7, "Maximum transmit seconds", "max_tx_seconds", note="Includes lead time, audio and tail time")
        self._field(frame, 8, "Audio level percent", "volume_percent", note="Applies to preview and radio audio")
        ttk.Button(frame, text="Refresh audio and serial devices", command=self._refresh_devices).grid(row=9, column=1, sticky="w", pady=12)
        ttk.Label(frame, text="Choose the exact output for each role. Prefer Windows WASAPI when your device offers it.\nVOX requires a radio or interface already configured for VOX. It cannot key a radio on its own.\nRTS and DTR need compatible serial PTT wiring. CM108 HID and CAT are not included in this pilot.",
                  wraplength=950).grid(row=10, column=0, columnspan=3, sticky="w", pady=12)

    def _id_tab(self):
        frame = self.tabs["Identification"]
        self._field(frame, 0, "CW ID text", "cw_text", note="Letters, digits, spaces and / . - ? =")
        self._field(frame, 1, "CW speed in words per minute", "cw_wpm")
        self._field(frame, 2, "CW tone in Hz", "cw_hz")
        self._field(frame, 3, "Voice ID text", "voice_text")
        self._field(frame, 4, "Voice ID source", "voice_mode", ["Speech", "WAV"])
        self._field(frame, 5, "Voice ID WAV file", "voice_wav", browse=True)
        self._field(frame, 6, "Windows speech voice", "voice", [""])
        self._field(frame, 7, "Speech rate", "speech_rate", note="From minus 10 to 10. Zero is normal.")
        self._field(frame, 8, "ID policy", "id_mode", ["CW", "Voice", "Alternate", "Both"])
        self._field(frame, 9, "ID interval in minutes", "id_minutes")
        controls = ttk.Frame(frame)
        controls.grid(row=10, column=1, sticky="w", pady=12)
        ttk.Button(controls, text="Preview CW locally", command=self.guard(lambda: self._preview("cw"))).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Preview voice locally", command=self.guard(lambda: self._preview("voice"))).pack(side="left")
        ttk.Label(frame, text="Blank voice uses the Windows default. IDs take priority over spots. RF starts with an ID.\nBoth sends CW then voice together. WAV files used with Both must be mono 22050 Hz PCM16.",
                  wraplength=900).grid(row=11, column=0, columnspan=3, sticky="w")

    def _policy_tab(self):
        frame = self.tabs["Announcements"]
        self._field(frame, 0, "Minimum frequency in kHz", "min_khz")
        self._field(frame, 1, "Maximum frequency in kHz", "max_khz")
        self._field(frame, 2, "Maximum spot age in seconds", "max_age_seconds")
        self._field(frame, 3, "Repeat suppression in seconds", "repeat_seconds")
        self._field(frame, 4, "Gap between spots in seconds", "spacing_seconds")
        ttk.Label(frame, text="Announcements spell the DX callsign using phonetics and read the frequency digit by digit in kilohertz.\nComments, chat, banners and cluster commands are never announced. The queue holds at most 100 spots.\nSpots received while RF is disabled are displayed but are not queued for later transmission.",
                  wraplength=900).grid(row=5, column=0, columnspan=3, sticky="w", pady=20)
        self.channel_ack = tk.BooleanVar(value=False)
        self.channel_ack.trace_add("write", lambda *args: self.engine.stop("Channel acknowledgement cleared. RF disabled.")
                                   if not self.channel_ack.get() else None)
        ttk.Checkbutton(frame, text="I am supervising operation on a clear or coordinated channel. This pilot does not detect a busy channel.",
                        variable=self.channel_ack).grid(row=6, column=0, columnspan=3, sticky="w")

    def _help_tab(self):
        frame = self.tabs["Help and Info"]
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)
        self.help_topic = tk.StringVar()
        self.help_topics = json.loads((resource_root() / "docs/help/manifest.json").read_text(encoding="utf-8"))["pages"]
        chooser = ttk.Combobox(frame, textvariable=self.help_topic, state="readonly", values=[p["title"] for p in self.help_topics])
        chooser.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        chooser.bind("<<ComboboxSelected>>", lambda event: self._show_help())
        self.help_text = tk.Text(frame, wrap="word", font=("Segoe UI", 11), padx=16, pady=12, state="disabled")
        self.help_text.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, command=self.help_text.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.help_text.configure(yscrollcommand=scrollbar.set)
        self.help_topic.set(self.help_topics[0]["title"])
        self._show_help()
        ttk.Label(frame, text=f"DX Talker {__version__}  |  Windows pilot  |  All rights reserved\nSettings: {settings_path()}", wraplength=900).grid(row=2, column=0, sticky="w", pady=10)

    def _show_help(self):
        topic = next(p for p in self.help_topics if p["title"] == self.help_topic.get())
        text = (resource_root() / "docs/help" / topic["path"]).read_text(encoding="utf-8")
        self.help_text.configure(state="normal")
        self.help_text.delete("1.0", "end")
        # The canonical Markdown is displayed locally. Topic navigation is provided
        # by the selector, avoiding any remote content or embedded browser dependency.
        self.help_text.insert("1.0", text)
        self.help_text.configure(state="disabled")

    def _read_settings(self):
        values = {}
        for f in fields(Settings):
            default = getattr(Settings(), f.name)
            value = self.variables[f.name].get()
            try:
                values[f.name] = type(default)(value) if type(default) is not str else value.strip()
            except (ValueError, tk.TclError):
                raise ValueError(f"Enter a valid number for {f.name.replace('_', ' ')}") from None
        return Settings(**values).validate()

    def _apply(self):
        updated = self._read_settings()
        if self.engine.enabled:
            self.engine.stop("Settings applied. RF disabled.")
        self.engine.configure(updated)
        source_fields = ("source_type", "host", "port", "login", "feed_url", "poll_seconds")
        if any(getattr(updated, k) != getattr(self.settings, k) for k in source_fields):
            self._disconnect()
        save_settings(updated)
        self.settings = updated
        self.emit("journal", "Settings saved")

    def _connect(self):
        self._apply()
        self.settings.validate_connection()
        secret = self.secret.get()
        if len(secret) > 512 or any(ord(c) < 32 or ord(c) > 126 for c in secret):
            raise ValueError("Use a single line ASCII password or token of at most 512 characters")
        self._disconnect()
        generation = self.source_generation

        def source_event(kind, value):
            if generation != self.source_generation:
                return
            if kind == "source_lost":
                self.engine.stop("Source lost. RF disabled.")
            self.emit("source_event", (generation, kind, value))

        self.source = SourceClient(self.settings, source_event, secret)
        self.source.start()

    def _disconnect(self):
        self.source_generation += 1
        if self.source:
            self.source.stop()
            self.source = None
        self.source_ready = False
        self.source_status.set("Source: disconnected")
        self.engine.stop("RF disabled. Source disconnected.")

    def _send(self):
        if not self.source:
            raise ValueError("Connect to a cluster first")
        self.source.send(self.command.get())
        self.command.set("")
        self.emit("journal", "Manual cluster response sent. Contents are not logged.")

    def _samples(self):
        now = datetime.now(UTC)
        for frequency, call in (("14025.0", "WB4IUY"), ("7074.0", "KT4BN"), ("50125.0", "KF4DBX")):
            spot = parse_line(f"DX de N0CALL: {frequency} {call} Demo {now:%H%M}Z", "sample", now)
            self._add_spot(spot)
        self.emit("journal", "Three sample spots loaded. Samples can be previewed locally and never enter the RF queue.")

    def _add_spot(self, spot):
        item = self.tree.insert("", 0, values=(spot.timestamp.strftime("%H:%MZ"), spot.dx_call,
                                                str(spot.frequency_khz), spot.spotter, spot.source))
        self.spots[item] = spot
        if len(self.spots) > 500:
            last = self.tree.get_children()[-1]
            self.tree.delete(last)
            self.spots.pop(last, None)

    def _preview_spot(self):
        selected = self.tree.selection()
        if not selected:
            raise ValueError("Select a spot first or load the sample spots")
        self._apply()
        if self._confirm_preview():
            self.engine.preview("spot", self.spots[selected[0]].speech)

    def _preview(self, kind):
        self._apply()
        if self._confirm_preview():
            self.engine.preview(kind)

    def _confirm_preview(self):
        if self.settings.preview_device and self.settings.preview_device == self.settings.radio_device:
            return messagebox.askyesno("Preview audio reaches radio output", "Preview and radio outputs are the same device. Preview audio may key a VOX radio. Play it on this device?")
        return True

    def _enable(self):
        self._apply()
        if not self.source_ready or not self.source or not self.source.ready.is_set():
            raise ValueError("Connect to a source and receive a valid feed before enabling RF. Use local previews for offline testing.")
        if not self.channel_ack.get():
            raise ValueError("Read and acknowledge supervised channel operation in Announcements")
        if self.settings.radio_device == self.settings.preview_device:
            if not messagebox.askyesno("Shared audio device", "The radio and local preview use the same device. A preview could reach the radio, especially with VOX. Continue?"):
                return
        self.engine.enable()

    def _stop(self):
        self.engine.stop()

    def _browse_wav(self):
        filename = filedialog.askopenfilename(title="Choose voice ID", filetypes=[("WAV audio", "*.wav")])
        if filename:
            self.variables["voice_wav"].set(filename)

    def _refresh_devices(self):
        if self.engine.enabled:
            self.engine.stop("Device refresh. RF disabled.")
        try:
            devices = AudioOutput.devices()
            for name in ("preview_device", "radio_device"):
                self.combos[name].configure(values=devices)
            self.combos["serial_port"].configure(values=serial_ports())
            self.emit("journal", f"Found {len(devices)} audio output names")
        except Exception as exc:
            self.emit("journal", f"Device discovery unavailable ({type(exc).__name__}). Install the runtime requirements on Windows.")

    def _load_voices(self):
        def task():
            try:
                self.emit("voices", WindowsSpeech().voices(self.background_cancel))
            except Exception:
                self.emit("journal", "Windows voices could not be enumerated. The default voice remains available on Windows.")
        threading.Thread(target=task, daemon=True).start()

    def emit(self, kind, value):
        # Never touch Tk variables from a worker. Control events bypass the bounded
        # spot queue, so a burst of spots cannot hide a disconnect or output fault.
        target = self.events if kind == "source_event" and value[1] == "spot" else self.control_events
        try:
            target.put_nowait((kind, value))
        except queue.Full:
            pass

    def _poll(self):
        if self.closing:
            return
        for target in (self.control_events, self.events):
            for _ in range(150):
                try:
                    kind, value = target.get_nowait()
                except queue.Empty:
                    break
                if kind == "source_event":
                    generation, kind, value = value
                    if generation != self.source_generation:
                        continue
                    if kind == "spot":
                        self._add_spot(value)
                        self.engine.offer(value)
                        continue
                    if kind == "source_ready":
                        self.source_ready = True
                    elif kind == "source_lost":
                        self.source_ready = False
                    self.source_status.set("Source: " + value)
                elif kind == "output":
                    self.output_status.set(value)
                elif kind == "activity":
                    self.activity.set(value)
                elif kind == "voices":
                    self.combos["voice"].configure(values=[""] + value)
                    continue
                elif kind == "error":
                    messagebox.showerror("Output stopped", value)
                self._journal(str(value))
        self.root.after(75, self._poll)

    def _journal(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", datetime.now().strftime("%H:%M:%S ") + text + "\n")
        self.log_lines += 1
        if self.log_lines > 200:
            self.log.delete("1.0", "2.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def close(self):
        self.closing = True
        self.background_cancel.set()
        self._disconnect()
        self.engine.shutdown()
        self._wait_close(0)

    def _wait_close(self, count):
        if self.engine.worker.is_alive():
            if count == 100:
                messagebox.showwarning("Waiting for output", "Output is still stopping. Verify the radio is unkeyed. The application will remain open while cleanup finishes.")
            self.root.after(50, lambda: self._wait_close(count + 1))
        else:
            self.root.destroy()


def main():
    root = tk.Tk()
    Application(root)
    root.mainloop()
