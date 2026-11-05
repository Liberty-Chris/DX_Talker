"""Windows desktop interface. All Tk calls stay on the main thread."""
from __future__ import annotations

from dataclasses import fields, replace
from datetime import datetime
import json
from pathlib import Path
import queue
import os
import subprocess
import webbrowser
import time
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .appearance import PALETTES, load_appearance, save_appearance
from .audio import AudioOutput, WindowsSpeech
from .engine import Engine
from .models import UTC, Settings, load_settings, parse_line, save_settings, settings_path
from .ptt import serial_ports
from .source import SourceClient
from .profiles import ProfileStore, SOURCE_FIELDS
from .history import History
from . import updates


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
        self.raw_events = queue.Queue(maxsize=30)
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
        self.history = None
        self.history_error = False
        self.update_release = self.update_download = None
        self.update_busy = False
        self.connected_identity = None
        self.connected_profile = "Unsaved source"
        self.selected_profile_id = None
        try:
            self.profile_store = ProfileStore()
        except Exception:
            # Preserve a damaged file for recovery. A new save remains disabled.
            self.profile_store = None
            settings_error += " Cluster profiles could not be loaded. The existing file has been retained."
        self.engine = Engine(self.settings, self.emit)
        self.engine.rf_allowed = lambda: self.source is not None and self.source.ready.is_set()
        self.variables = {}
        self.combos = {}
        self.field_widgets = {}
        self.theme = tk.StringVar(value=load_appearance())
        brand = resource_root() / "assets/brand"
        self.logos = {name: tk.PhotoImage(file=str(brand / f"logo-{'light' if name == 'Light' else 'dark'}.png")).subsample(2)
                      for name in PALETTES}
        self.icon = tk.PhotoImage(file=str(brand / "icon.png"))
        root.iconphoto(True, self.icon)
        if sys.platform == "win32":
            root.iconbitmap(str(brand / "dxt.ico"))
        self._style()
        self._build()
        self._paint_widgets()
        self.initializing = False
        self._refresh_devices()
        self._load_voices()
        self._configure_history()
        self.root.bind("<Escape>", lambda event: self._stop())
        self.root.bind("<F6>", lambda event: self.guard(self._preview_spot)())
        self.root.bind("<F8>", lambda event: self.guard(self._listen)())
        self.root.bind("<Alt-c>", lambda event: self.command_entries[0].focus_set())
        self.notebook.enable_traversal()
        self.root.bind("<Configure>", self._responsive_layout, add="+")
        root.after_idle(self._responsive_layout)
        root.after(2500, self._startup_update_check)
        root.after(86400000, self._scheduled_update_check)
        if settings_error:
            messagebox.showwarning("Settings", settings_error)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(75, self._poll)

    def _style(self):
        p = PALETTES[self.theme.get()]
        style = ttk.Style(self.root)
        style.theme_use("clam")
        self.root.configure(background=p["bg"])
        style.configure(".", font=("Segoe UI", self.settings.text_size), background=p["bg"], foreground=p["ink"],
                        troughcolor=p["bg"], bordercolor=p["edge"], lightcolor=p["edge"], darkcolor=p["edge"])
        style.configure("TFrame", background=p["bg"])
        style.configure("TLabel", background=p["bg"], foreground=p["ink"])
        style.configure("Header.TFrame", background=p["panel"])
        style.configure("Header.TLabel", background=p["panel"], foreground=p["muted"])
        style.configure("Brand.TLabel", background=p["panel"])
        style.configure("Status.TFrame", background=p["panel"])
        style.configure("Status.TLabel", background=p["panel"], foreground=p["ink"], padding=(14, 4))
        style.configure("Eyebrow.TLabel", background=p["panel"], foreground=p["muted"], font=("Segoe UI", 9))
        style.configure("TButton", padding=(10, 7), background=p["field"], foreground=p["ink"], borderwidth=1)
        style.map("TButton", background=[("active", p["selected"]), ("pressed", p["selected"])],
                  foreground=[("disabled", p["muted"])])
        style.configure("Accent.TButton", background=p["accent"], foreground="#ffffff" if self.theme.get() in ("Light", "High contrast") else "#071722")
        style.map("Accent.TButton", background=[("active", "#36c9f4")], foreground=[("active", "#071722")])
        style.configure("Stop.TButton", background="#b22b42", foreground="white", font=("Segoe UI", 10, "bold"))
        style.map("Stop.TButton", background=[("active", "#d63852")], foreground=[("active", "white")])
        style.configure("TEntry", fieldbackground=p["field"], foreground=p["ink"], insertcolor=p["ink"], padding=6)
        style.configure("TSpinbox", fieldbackground=p["field"], foreground=p["ink"], arrowcolor=p["ink"], padding=6)
        style.configure("TCombobox", fieldbackground=p["field"], background=p["field"], foreground=p["ink"],
                        arrowcolor=p["ink"], padding=5)
        style.map("TCombobox", fieldbackground=[("readonly", p["field"])], foreground=[("readonly", p["ink"])],
                  selectbackground=[("readonly", p["selected"])], selectforeground=[("readonly", p["ink"])])
        self.root.option_add("*TCombobox*Listbox.background", p["field"])
        self.root.option_add("*TCombobox*Listbox.foreground", p["ink"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", p["selected"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", p["ink"])
        style.configure("TCheckbutton", background=p["bg"], foreground=p["ink"])
        style.map("TCheckbutton", background=[("active", p["bg"])], indicatorbackground=[("selected", p["accent"])])
        style.configure("Treeview", background=p["panel"], fieldbackground=p["panel"], foreground=p["ink"],
                        rowheight=max(32, self.settings.text_size * 2 + 10), font=("Segoe UI", self.settings.text_size), borderwidth=0)
        style.map("Treeview", background=[("selected", p["selected"])], foreground=[("selected", p["ink"])])
        style.configure("Treeview.Heading", background=p["field"], foreground=p["muted"],
                        font=("Segoe UI", 9, "bold"), padding=(8, 9))
        style.map("Treeview.Heading", background=[("active", p["selected"])])
        style.configure("TNotebook", background=p["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", padding=(12, 9), background=p["bg"], foreground=p["muted"])
        style.map("TNotebook.Tab", background=[("selected", p["panel"]), ("active", p["field"])],
                  foreground=[("selected", p["accent"]), ("active", p["ink"])])
        style.configure("Vertical.TScrollbar", background=p["field"], arrowcolor=p["muted"])

    def _paint_widgets(self):
        p = PALETTES[self.theme.get()]
        self.brand_label.configure(image=self.logos[self.theme.get()])
        self.accent_line.configure(background=p["accent"])
        for text in (self.log, self.help_text, self.raw_console, self.release_notes):
            text.configure(background=p["panel"], foreground=p["ink"], insertbackground=p["ink"],
                           selectbackground=p["selected"], selectforeground=p["ink"], highlightthickness=0)
        for _, canvas in self.scroll_tabs:
            canvas.configure(background=p["bg"])
        self.tree.tag_configure("alternate", background=p["field"])
        self.eye_icon = tk.PhotoImage(width=18, height=14)
        for x in range(2, 16):
            y = round(3 + 4 * ((x - 8.5) / 6.5) ** 2)
            self.eye_icon.put(p["ink"], (x, y))
            self.eye_icon.put(p["ink"], (x, 13 - y))
        for x in range(7, 11):
            for y in range(5, 9):
                self.eye_icon.put(p["ink"], (x, y))
        self.secret_toggle.configure(image=self.eye_icon, compound="left")

    def _change_theme(self, event=None):
        # Appearance never applies radio settings, stops a transmission or rearms RF.
        self._style()
        self._paint_widgets()
        try:
            save_appearance(self.theme.get())
        except OSError:
            messagebox.showwarning("Appearance", "The theme changed, but could not be saved for next time.")

    def _build(self):
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(20, 14))
        header.pack(fill="x")
        self.brand_label = ttk.Label(header, image=self.logos[self.theme.get()], style="Brand.TLabel")
        self.brand_label.pack(side="left")
        identity = ttk.Frame(header, style="Header.TFrame")
        identity.pack(side="left", padx=16)
        ttk.Label(identity, text="DX TALKER", style="Header.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(identity, text="Windows pilot  /  " + __version__, style="Header.TLabel").pack(anchor="w", pady=(4, 0))
        self.stop_button = ttk.Button(header, text="STOP ALL OUTPUT", style="Stop.TButton", command=self._stop)
        self.stop_button.pack(side="right")
        appearance = ttk.Frame(header, style="Header.TFrame")
        appearance.pack(side="right", padx=18)
        ttk.Label(appearance, text="APPEARANCE", style="Eyebrow.TLabel").pack(anchor="w", pady=(0, 4))
        self.theme_picker = ttk.Combobox(appearance, textvariable=self.theme, values=list(PALETTES),
                                         state="readonly", width=7)
        self.theme_picker.pack()
        self.theme_picker.bind("<<ComboboxSelected>>", self._change_theme)
        self.accent_line = tk.Frame(self.root, height=2, background=PALETTES[self.theme.get()]["accent"])
        self.accent_line.pack(fill="x")

        status = ttk.Frame(self.root, padding=(18, 10))
        status.pack(fill="x")
        self.source_status = tk.StringVar(value="Source: disconnected")
        self.output_status = tk.StringVar(value="RF disabled")
        self.activity = tk.StringVar(value="Idle")
        for column, (title, variable) in enumerate((("CONNECTION", self.source_status),
                                                  ("RADIO OUTPUT", self.output_status),
                                                  ("ACTIVITY", self.activity))):
            status.columnconfigure(column, weight=1, uniform="status")
            card = ttk.Frame(status, style="Status.TFrame", padding=(0, 8))
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 4, 0))
            ttk.Label(card, text=title, style="Eyebrow.TLabel", padding=(14, 0)).pack(anchor="w")
            ttk.Label(card, textvariable=variable, style="Status.TLabel", wraplength=280).pack(anchor="w")
        notebook = ttk.Notebook(self.root)
        self.notebook = notebook
        notebook.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.tabs = {}
        self.scroll_tabs = []
        for name in ("Live spots", "Source", "Audio and PTT", "Identification", "Announcements", "Speech and access", "History and updates", "Help and Info"):
            if name in ("Live spots", "Help and Info"):
                frame = ttk.Frame(notebook, padding=16)
                notebook.add(frame, text={"Help and Info": "Help"}.get(name, name))
            else:
                container = ttk.Frame(notebook)
                notebook.add(container, text={"Audio and PTT": "Audio / PTT", "Identification": "IDs", "Speech and access": "Speech", "History and updates": "History / Updates"}.get(name, name))
                canvas = tk.Canvas(container, background=PALETTES[self.theme.get()]["bg"], highlightthickness=0)
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
        self.command = tk.StringVar()
        self.command_entries = []
        self.command_buttons = []
        self._live_tab()
        self._source_tab()
        self._audio_tab()
        self._id_tab()
        self._policy_tab()
        self._speech_tab()
        self._history_tab()
        self._help_tab()
        footer = ttk.Frame(self.root, padding=(18, 5, 18, 12))
        footer.pack(side="bottom", fill="x", before=notebook)
        ttk.Label(footer, text="Save settings to apply. RF always starts disabled.").pack(side="left")
        self.save_button = ttk.Button(footer, text="Save and apply settings", style="Accent.TButton", command=self.guard(self._apply))
        self.save_button.pack(side="right")
        self.update_banner = tk.StringVar()
        ttk.Label(footer, textvariable=self.update_banner, wraplength=420).pack(side="left", padx=12)
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
        elif type(value) is int:
            limits = {"speech_rate": (-10, 10), "character_pause_ms": (0, 1000), "group_pause_ms": (0, 3000),
                      "volume_percent": (0, 100), "cw_volume_percent": (0, 100), "voice_id_volume_percent": (0, 100),
                      "local_volume_percent": (0, 100), "text_size": (10, 18)}
            low, high = limits.get(name, (0, 10000000))
            widget = ttk.Spinbox(parent, textvariable=var, from_=low, to=high, width=12)
        else:
            widget = ttk.Entry(parent, textvariable=var, width=48)
        self.field_widgets[name] = widget
        widget.grid(row=row, column=1, sticky="ew", pady=6)
        if browse:
            ttk.Button(parent, text="Browse", command=self.guard(self._browse_wav)).grid(row=row, column=2, padx=6)
        elif note:
            ttk.Label(parent, text=note, wraplength=260).grid(row=row, column=2, padx=12, sticky="w")
        var.trace_add("write", self._setting_changed)

    def _setting_changed(self, *args):
        if not self.initializing and (self.engine.enabled or self.engine.local_enabled):
            self.engine.stop("Settings changed. RF disabled. Save and apply before enabling again.")

    def _live_tab(self):
        frame = self.tabs["Live spots"]
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(3, weight=1, minsize=90)
        quick = ttk.Frame(frame)
        quick.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(quick, text="Cluster profile").pack(side="left", padx=(0, 8))
        self.profile_choice = tk.StringVar()
        self.live_profile_picker = ttk.Combobox(quick, textvariable=self.profile_choice, state="readonly", width=32)
        self.live_profile_picker.pack(side="left")
        self.live_profile_picker.bind("<<ComboboxSelected>>", lambda event: self.guard(self._select_profile)())
        ttk.Label(quick, text="Choose a saved profile, then Connect.").pack(side="left", padx=12)
        toolbar = ttk.Frame(frame)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        for index, (text, action) in enumerate((("Connect", self._connect), ("Disconnect", self._disconnect),
                             ("Load sample spots", self._samples), ("Preview selected", self._preview_spot),
                             ("Listen locally (F8)", self._listen), ("Clear view", self._clear_spots),
                             ("Enable RF", self._enable), ("Send ID now", self.engine.identify))):
            ttk.Button(toolbar, text=text, command=self.guard(action)).grid(
                row=index // 4, column=index % 4, sticky="ew", padx=(0, 6), pady=(0, 6))
        self.live_hint = ttk.Label(frame, text="Spots appear here before RF is enabled. Select one to preview it locally.")
        self.live_hint.grid(row=2, column=0, sticky="w", pady=(0, 8))
        columns = ("time", "dx", "frequency", "spotter", "source")
        table = ttk.Frame(frame)
        table.grid(row=3, column=0, sticky="nsew")
        self.tree = ttk.Treeview(table, columns=columns, show="headings", height=10, selectmode="browse")
        for key, title, width in zip(columns, ("UTC", "DX callsign", "Frequency kHz", "Spotted by", "Source"), (100, 170, 170, 160, 100)):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=80)
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self._command_bar(frame, 4)
        # The activity journal contains application events, never raw cluster text.
        self.activity_label = ttk.Label(frame, text="Activity")
        self.activity_label.grid(row=5, column=0, sticky="w", pady=(8, 4))
        self.log = tk.Text(frame, height=3, wrap="word", state="disabled", font=("Consolas", 9), relief="flat")
        self.log.grid(row=6, column=0, sticky="ew")

    def _source_tab(self):
        frame = self.tabs["Source"]
        self._field(frame, 0, "Source type", "source_type", ["TCP/Telnet", "HTTPS JSON"])
        self._field(frame, 1, "Cluster hostname", "host", note="Example: w4mr.ddns.net")
        self._field(frame, 2, "Cluster port", "port", note="Example: 7373")
        self._field(frame, 3, "Cluster login callsign", "login")
        self.secret_label = ttk.Label(frame, text="Cluster password (optional)")
        self.secret_label.grid(row=4, column=0, sticky="w", pady=6)
        self.secret = tk.StringVar()
        self.secret_visible = False
        secret_field = ttk.Frame(frame)
        secret_field.grid(row=4, column=1, sticky="ew")
        secret_field.columnconfigure(0, weight=1)
        self.secret_entry = ttk.Entry(secret_field, textvariable=self.secret, show="*", width=40)
        self.secret_entry.grid(row=0, column=0, sticky="ew")
        self.secret_toggle = ttk.Button(secret_field, text="Show", command=self._toggle_secret, width=8)
        self.secret_toggle.grid(row=0, column=1, padx=(8, 0))
        ttk.Label(frame, text="Session only unless remembered in a profile.", wraplength=260).grid(row=4, column=2, padx=12)
        self._field(frame, 5, "HTTPS JSON feed URL", "feed_url")
        self._field(frame, 6, "HTTPS polling interval in seconds", "poll_seconds", note="Minimum 15 seconds")
        ttk.Label(frame, text="Cluster prompts are detected for callsign and password. For an unusual prompt, send a response below.\nFor HTTPS, see the documented JSON feed format in Help. Ordinary website URLs are not feeds.",
                  wraplength=900).grid(row=7, column=0, columnspan=3, sticky="w", pady=14)
        self._command_bar(frame, 8)
        ttk.Label(frame, text="Cluster console. Latest 15 lines, session only. Never spoken or logged.").grid(row=10, column=0, columnspan=3, sticky="w")
        self.raw_console = tk.Text(frame, height=8, wrap="word", state="disabled", font=("Consolas", 10))
        self.raw_console.grid(row=11, column=0, columnspan=3, sticky="ew", pady=8)
        self.raw_lines = []
        profiles = ttk.LabelFrame(frame, text="Saved cluster profiles", padding=12)
        profiles.grid(row=12, column=0, columnspan=3, sticky="ew", pady=12)
        profiles.columnconfigure(1, weight=1)
        self.profile_name = tk.StringVar()
        self.remember_secret = tk.BooleanVar(value=False)
        ttk.Label(profiles, text="Saved profile").grid(row=0, column=0, sticky="w")
        self.profile_picker = ttk.Combobox(profiles, textvariable=self.profile_choice, state="readonly")
        self.profile_picker.grid(row=0, column=1, sticky="ew", padx=8)
        self.profile_picker.bind("<<ComboboxSelected>>", lambda event: self.guard(self._select_profile)())
        ttk.Label(profiles, text="Profile name").grid(row=1, column=0, sticky="w", pady=8)
        ttk.Entry(profiles, textvariable=self.profile_name).grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Checkbutton(profiles, text="Remember secret for this Windows account", variable=self.remember_secret).grid(row=2, column=0, columnspan=2, sticky="w")
        buttons = ttk.Frame(profiles)
        buttons.grid(row=3, column=0, columnspan=2, sticky="w", pady=8)
        for label, action in (("New", self._new_profile), ("Save profile", self._save_profile), ("Delete", self._delete_profile), ("Connect", self._connect), ("Disconnect", self._disconnect)):
            ttk.Button(buttons, text=label, command=self.guard(action)).pack(side="left", padx=(0, 8))
        ttk.Label(profiles, text="Selecting a profile loads its connection details and stops output. Connect when ready.", wraplength=800).grid(row=4, column=0, columnspan=2, sticky="w")
        # Profile selection belongs at the top of Source, before editable details.
        for child in frame.winfo_children():
            if child is not profiles:
                child.grid_configure(row=int(child.grid_info()["row"]) + 1)
        profiles.grid_configure(row=0)
        self._refresh_profiles()
        self.combos["source_type"].bind("<<ComboboxSelected>>", lambda event: self._source_type_changed(clear_secret=True))
        self._source_type_changed()

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
        self._field(frame, 8, "Spot radio level percent", "volume_percent")
        self._field(frame, 9, "CW ID level percent", "cw_volume_percent")
        self._field(frame, 10, "Voice ID level percent", "voice_id_volume_percent")
        self._field(frame, 11, "Local listening level percent", "local_volume_percent", note="Also scales local previews")
        ttk.Button(frame, text="Refresh audio and serial devices", command=self._refresh_devices).grid(row=12, column=1, sticky="w", pady=12)
        ttk.Label(frame, text="Choose the exact output for each role. Prefer Windows WASAPI when your device offers it.\nVOX requires a radio or interface already configured for VOX. It cannot key a radio on its own.\nRTS and DTR need compatible serial PTT wiring. CM108 HID and CAT are not included in this pilot.",
                  wraplength=950).grid(row=13, column=0, columnspan=3, sticky="w", pady=12)

    def _id_tab(self):
        frame = self.tabs["Identification"]
        self._field(frame, 0, "CW ID text", "cw_text", note="Letters, digits, spaces and / . - ? =")
        self._field(frame, 1, "CW speed in words per minute", "cw_wpm")
        self._field(frame, 2, "CW tone in Hz", "cw_hz")
        self._field(frame, 3, "Voice ID text", "voice_text")
        self._field(frame, 4, "Voice ID source", "voice_mode", ["Speech", "WAV"])
        self._field(frame, 5, "Voice ID WAV file", "voice_wav", browse=True)
        ttk.Label(frame, text="Voice, rate and pronunciation controls are in Speech.").grid(row=6, column=0, columnspan=3, sticky="w", pady=8)
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
        self.variables["supervised_ack"] = tk.BooleanVar(value=self.settings.supervised_ack)
        self.channel_ack = self.variables["supervised_ack"]
        self.channel_ack.trace_add("write", lambda *args: self.engine.stop("Channel acknowledgement cleared. RF disabled.")
                                   if not self.channel_ack.get() else None)
        ttk.Checkbutton(frame, text="I am supervising operation on a clear or coordinated channel. This pilot does not detect a busy channel.",
                        variable=self.channel_ack).grid(row=7, column=0, columnspan=3, sticky="w")

    def _responsive_layout(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        compact = self.root.winfo_height() < 720
        for widget in (self.log, self.activity_label, self.live_hint):
            widget.grid_remove() if compact else widget.grid()

    def _command_bar(self, frame, row):
        bar = ttk.LabelFrame(frame, text="Manual response or cluster command", padding=8)
        bar.grid(row=row, column=0, columnspan=3 if frame is self.tabs["Source"] else 1, sticky="ew", pady=8)
        bar.columnconfigure(0, weight=1)
        entry = ttk.Entry(bar, textvariable=self.command)
        entry.grid(row=0, column=0, sticky="ew")
        entry.bind("<Return>", lambda event: self.guard(self._send)())
        self.command_entries.append(entry)
        send = ttk.Button(bar, text="Send", command=self.guard(self._send))
        send.grid(row=0, column=1, padx=(8, 0))
        self.command_buttons.append(send)

    def _set_secret_visible(self, visible):
        self.secret_visible = visible
        self.secret_entry.configure(show="" if visible else "*")
        self.secret_toggle.configure(text="Hide" if visible else "Show")

    def _toggle_secret(self):
        self._set_secret_visible(not self.secret_visible)

    def _source_type_changed(self, clear_secret=False):
        tcp = self.variables["source_type"].get() == "TCP/Telnet"
        for name in ("host", "port", "login"):
            self.field_widgets[name].configure(state="normal" if tcp else "disabled")
        for name in ("feed_url", "poll_seconds"):
            self.field_widgets[name].configure(state="disabled" if tcp else "normal")
        self.secret_label.configure(text="Cluster password (optional)" if tcp else "HTTPS bearer token (optional)")
        for widget in self.command_entries + self.command_buttons:
            widget.configure(state="normal" if tcp else "disabled")
        self._set_secret_visible(False)
        if clear_secret:
            self.secret.set("")

    def _clear_console(self):
        self.raw_lines.clear()
        self.raw_console.configure(state="normal")
        self.raw_console.delete("1.0", "end")
        self.raw_console.configure(state="disabled")

    def _append_raw(self, value):
        self.raw_lines = (self.raw_lines + [value])[-15:]
        self.raw_console.configure(state="normal")
        self.raw_console.delete("1.0", "end")
        self.raw_console.insert("end", "\n".join(self.raw_lines))
        self.raw_console.see("end")
        self.raw_console.configure(state="disabled")

    def _clear_spots(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.spots.clear()

    def _trim_spots(self):
        rows = self.tree.get_children()
        for row in rows[self.settings.display_limit:]:
            self.tree.delete(row)
            self.spots.pop(row, None)

    def _refresh_profiles(self):
        names = sorted(p["name"] for p in self.profile_store.profiles) if self.profile_store else []
        self.profile_picker.configure(values=names)
        self.live_profile_picker.configure(values=names)

    def _new_profile(self):
        self._disconnect()
        self.selected_profile_id = None
        self.profile_choice.set("")
        self.profile_name.set("")
        self.secret.set("")
        self._set_secret_visible(False)
        self.remember_secret.set(False)

    def _select_profile(self):
        if not self.profile_store:
            raise ValueError("Recover profiles.json before using saved profiles")
        item = next(p for p in self.profile_store.profiles if p["name"] == self.profile_choice.get())
        updated, secret = self.profile_store.load(item["id"], self._read_settings())
        self._disconnect()
        self._clear_spots()
        self._clear_console()
        self.command.set("")
        self.selected_profile_id = item["id"]
        self.profile_name.set(item["name"])
        self.secret.set(secret)
        self.remember_secret.set(bool(item["secret"]))
        for key in SOURCE_FIELDS:
            self.variables[key].set(getattr(updated, key))
        self._source_type_changed()

    def _save_profile(self):
        if not self.profile_store:
            raise ValueError("Recover profiles.json before saving profiles")
        item = self.profile_store.save(self.profile_name.get(), self._read_settings(), self.secret.get(),
                                       self.remember_secret.get(), self.selected_profile_id)
        self.selected_profile_id = item["id"]
        self.profile_choice.set(item["name"])
        self._refresh_profiles()

    def _delete_profile(self):
        if self.selected_profile_id and messagebox.askyesno("Delete cluster profile", "Delete this saved profile and its remembered secret?"):
            self.profile_store.delete(self.selected_profile_id)
            self._new_profile()
            self._refresh_profiles()

    def _speech_tab(self):
        frame = self.tabs["Speech and access"]
        self._field(frame, 0, "Speech provider", "speech_provider", ["Windows", "Piper"])
        self._field(frame, 1, "Windows voice", "voice", [""])
        self._field(frame, 2, "Preferred Windows voice gender", "voice_gender", ["Any", "Male", "Female"],
                    note="Used with the default voice selection. Installed voices determine availability.")
        self._field(frame, 3, "Speech speed", "speech_rate", note="Minus 10 to 10. Zero is normal.")
        self._field(frame, 4, "Pause between letters and digits (ms)", "character_pause_ms", note="0 to 1000. Zero keeps natural spacing.")
        self._field(frame, 5, "Pause between announcement groups (ms)", "group_pause_ms", note="0 to 3000. Intro, callsign and frequency.")
        self._field(frame, 6, "Piper executable", "piper_executable")
        self._field(frame, 7, "Piper ONNX voice model", "piper_model")
        for row, name, title in ((6, "piper_executable", "Choose Piper executable"), (7, "piper_model", "Choose Piper ONNX model")):
            ttk.Button(frame, text="Browse", command=lambda n=name, t=title: self._browse_file(n, t)).grid(row=row, column=2, padx=8)
        self._field(frame, 8, "Interface text size", "text_size", note="10 to 18 points. Save to apply.")
        ttk.Button(frame, text="Preview sample speech", command=self.guard(self._preview_sample)).grid(row=9, column=1, sticky="w", pady=12)
        ttk.Label(frame, text="Windows speech is built in. Piper is an optional local neural voice provider. Install it and a matching voice separately.\nPiper voice character is chosen by its model. Windows voice and gender controls apply only to Windows.\nF6 previews the selected spot. F8 starts local listening. Escape stops all output. Alt+C focuses cluster commands.\nCtrl+Tab changes pages. High contrast is available in Appearance. See Listening and accessibility in Help.",
                  wraplength=800).grid(row=10, column=0, columnspan=3, sticky="w", pady=8)

    def _browse_file(self, name, title):
        value = filedialog.askopenfilename(title=title)
        if value:
            self.variables[name].set(value)

    def _preview_sample(self):
        self._apply()
        now = datetime.now(UTC)
        spot = parse_line(f"DX de N0CALL: 14025.5 WB4IUY/P {now:%H%M}Z", "sample", now)
        if self._confirm_preview():
            self.engine.preview("spot", spot)

    def _listen(self):
        self._apply()
        if not self._confirm_preview():
            return
        self.engine.listen_locally()

    def _history_tab(self):
        frame = self.tabs["History and updates"]
        self._field(frame, 0, "Live view maximum spots", "display_limit", note="50 to 5000. Oldest rows leave the view.")
        self._field(frame, 1, "Keep spot and connection history", "logging_enabled")
        self._field(frame, 2, "History folder", "log_directory", note="Blank uses the DXTalker settings folder / logs.")
        ttk.Button(frame, text="Choose folder", command=self._choose_log_folder).grid(row=3, column=1, sticky="w")
        self._field(frame, 4, "History file size in MiB", "log_max_mb", note="1 to 100 MiB per file")
        self._field(frame, 5, "History backup files", "log_backups", note="1 to 30 plus the active file")
        ttk.Button(frame, text="Open history folder", command=self.guard(self._open_history)).grid(row=6, column=1, sticky="w", pady=8)
        self._field(frame, 7, "Check for updates automatically", "check_updates")
        self._field(frame, 8, "Update channel", "update_channel", ["Pilot", "Stable"])
        self.update_status = tk.StringVar(value="Installed version: " + __version__)
        ttk.Label(frame, textvariable=self.update_status, wraplength=800).grid(row=9, column=0, columnspan=3, sticky="w", pady=12)
        controls = ttk.Frame(frame)
        controls.grid(row=10, column=0, columnspan=3, sticky="w")
        for label, action in (("Check now", self._check_updates), ("Release page", self._release_page),
                              ("Download update", self._download_update), ("Install update", self._install_update)):
            ttk.Button(controls, text=label, command=self.guard(action)).pack(side="left", padx=(0, 8))
        self.release_notes = tk.Text(frame, height=6, wrap="word", state="disabled", font=("Segoe UI", 10))
        self.release_notes.grid(row=11, column=0, columnspan=3, sticky="ew", pady=12)
        ttk.Label(frame, text="Pilot includes preview releases. Stable includes final releases only. Checks run at startup and daily.\nUpdates never install automatically. Download verification uses the release SHA256 checksum.\nInstallation stops output and closes DX Talker. Settings and cluster profiles are retained.",
                  wraplength=800).grid(row=12, column=0, columnspan=3, sticky="w")

    def _choose_log_folder(self):
        folder = filedialog.askdirectory(title="Choose history folder")
        if folder:
            self.variables["log_directory"].set(folder)

    def _configure_history(self):
        if self.history:
            self.history.close()
        self.history = None
        try:
            self.history = History(self.settings)
            self.history_error = False
        except OSError:
            self.history_error = True
            self.emit("journal", "History folder is unavailable. Choose a writable folder and save settings.")

    def _history_record(self, kind, **values):
        if self.history:
            try:
                self.history.record(kind, **values)
            except OSError:
                self.history.close()
                self.history = None
                self.emit("journal", "History writing failed. Choose a writable folder and save settings.")

    def _history_spot(self, spot):
        if self.history:
            try:
                self.history.spot(spot, self.connected_profile)
            except OSError:
                self.history.close()
                self.history = None
                self.emit("journal", "History writing failed. Choose a writable folder and save settings.")

    def _open_history(self):
        directory = Path(self.settings.log_directory) if self.settings.log_directory else settings_path().parent / "logs"
        directory.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(directory))
        else:
            webbrowser.open(directory.as_uri())

    def _startup_update_check(self):
        if self.settings.check_updates and not self.closing:
            self._check_updates()

    def _scheduled_update_check(self):
        if self.closing:
            return
        if self.settings.check_updates:
            self._check_updates()
        self.root.after(86400000, self._scheduled_update_check)

    def _check_updates(self):
        if self.update_busy or self.closing:
            return
        self.update_busy = True
        self.update_status.set("Checking GitHub Releases...")
        channel = self.variables["update_channel"].get()
        def task():
            try:
                self.emit("update_result", updates.check(channel))
            except Exception:
                self.emit("update_error", "Could not check for updates. Check your connection and try Check now.")
        threading.Thread(target=task, daemon=True, name="DX updates").start()

    def _release_page(self):
        webbrowser.open(self.update_release.page if self.update_release else "https://github.com/Liberty-Chris/DX_Talker/releases")

    def _download_update(self):
        if self.update_busy:
            raise ValueError("Wait for the current update operation")
        if not self.update_release:
            raise ValueError("Check for an available update first")
        if sys.platform != "win32":
            raise ValueError("This installer is for Windows x64. Use the release page on other systems.")
        self.update_busy = True
        self.update_download = None
        release = self.update_release
        def task():
            try:
                self.emit("update_download", updates.download(release, settings_path().parent / "updates",
                          self.background_cancel, lambda value: self.emit("update_progress", value)))
            except Exception:
                self.emit("update_error", "Download failed or was cancelled. Try again. The current installation is unchanged.")
        threading.Thread(target=task, daemon=True, name="DX update download").start()

    def _install_update(self):
        if sys.platform != "win32" or not self.update_download:
            raise ValueError("Download and verify an update first")
        if not getattr(sys, "frozen", False):
            raise ValueError("Install updates from the packaged Windows app. Source checkouts use Git.")
        path, checksum = self.update_download
        if not updates.verify_download(path, checksum):
            self.update_download = None
            raise ValueError("The downloaded installer changed. Download it again.")
        if not messagebox.askyesno("Install DX Talker update", "Stop output, close DX Talker and open the verified setup program? Your settings and profiles will be retained."):
            return
        self.engine.stop("Stopping output for update")
        self._disconnect()
        self._wait_install(path, checksum, time.monotonic() + 30)

    def _wait_install(self, path, checksum, deadline):
        if self.engine.busy:
            if time.monotonic() > deadline:
                messagebox.showerror("Update paused", "Output has not stopped. Verify the radio and try installing again after Idle.")
                return
            self.root.after(100, lambda: self._wait_install(path, checksum, deadline))
            return
        try:
            if not updates.verify_download(path, checksum):
                raise ValueError("Installer verification failed")
            subprocess.Popen([str(path)], shell=False)
        except Exception:
            messagebox.showerror("Update", "Could not open the verified installer. Download it again or use the release page.")
            return
        self.close()

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
        if self.engine.enabled or self.engine.local_enabled:
            self.engine.stop("Settings applied. RF disabled.")
        self.engine.configure(updated)
        source_fields = ("source_type", "host", "port", "login", "feed_url", "poll_seconds")
        if any(getattr(updated, k) != getattr(self.settings, k) for k in source_fields):
            self._disconnect()
            self._clear_spots()
            self._clear_console()
        save_settings(updated)
        history_changed = any(getattr(updated, key) != getattr(self.settings, key) for key in
                              ("logging_enabled", "log_directory", "log_max_mb", "log_backups"))
        self.settings = updated
        if history_changed or self.history is None:
            self._configure_history()
        self._trim_spots()
        self._style()
        self.help_text.configure(font=("Segoe UI", self.settings.text_size + 1))
        self._paint_widgets()
        self.emit("journal", "Settings saved")

    def _connect(self):
        self._apply()
        self.settings.validate_connection()
        secret = self.secret.get()
        if len(secret) > 512 or any(ord(c) < 32 or ord(c) > 126 for c in secret):
            raise ValueError("Use a single line ASCII password or token of at most 512 characters")
        self._disconnect()
        identity = tuple(getattr(self.settings, key) for key in SOURCE_FIELDS)
        if identity != self.connected_identity:
            self._clear_spots()
            self._clear_console()
        self.connected_identity = identity
        self.connected_profile = self.profile_name.get().strip() or "Unsaved source"
        self._history_record("connection", profile=self.connected_profile, source_type=self.settings.source_type)
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
        if self.source:
            self._history_record("disconnect", profile=self.connected_profile)
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
                                                str(spot.frequency_khz), spot.spotter, spot.source),
                                tags=("alternate",) if len(self.spots) % 2 else ())
        self.spots[item] = spot
        self._trim_spots()

    def _preview_spot(self):
        selected = self.tree.selection()
        if not selected:
            raise ValueError("Select a spot first or load the sample spots")
        spot = self.spots[selected[0]]
        self._apply()
        if self._confirm_preview():
            self.engine.preview("spot", spot)

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
        if self.engine.enabled or self.engine.local_enabled:
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
        target = self.control_events
        if kind == "source_event":
            if value[1] == "raw":
                target = self.raw_events
            elif value[1] == "spot":
                target = self.events
        try:
            target.put_nowait((kind, value))
        except queue.Full:
            pass

    def _poll(self):
        if self.closing:
            return
        for target in (self.control_events, self.events, self.raw_events):
            for _ in range(150):
                try:
                    kind, value = target.get_nowait()
                except queue.Empty:
                    break
                if kind == "source_event":
                    generation, kind, value = value
                    if generation != self.source_generation:
                        continue
                    if kind == "raw":
                        self._append_raw(value)
                        continue
                    if kind == "spot":
                        self._history_spot(value)
                        self._add_spot(value)
                        self.engine.offer(value)
                        continue
                    if kind == "source_ready":
                        self.source_ready = True
                    elif kind == "source_lost":
                        self.source_ready = False
                    self.source_status.set("Source: " + value)
                elif kind == "announcement":
                    self._history_record("announcement", profile=self.connected_profile, **value)
                    continue
                elif kind == "output":
                    self.output_status.set(value)
                elif kind == "activity":
                    self.activity.set(value)
                elif kind == "voices":
                    self.combos["voice"].configure(values=[""] + value)
                    continue
                elif kind == "update_result":
                    self.update_busy = False
                    self.update_release = value
                    self.update_download = None
                    self.update_status.set("Update available: " + value.version if value else "No newer compatible release found for this channel.")
                    self.update_banner.set("Update available: " + value.version + ". Open History / Updates." if value else "")
                    if value:
                        self.release_notes.configure(state="normal")
                        self.release_notes.delete("1.0", "end")
                        self.release_notes.insert("1.0", value.notes)
                        self.release_notes.configure(state="disabled")
                    continue
                elif kind == "update_error":
                    self.update_busy = False
                    self.update_status.set(value)
                    continue
                elif kind == "update_progress":
                    self.update_status.set(f"Downloading update: {value}%")
                    continue
                elif kind == "update_download":
                    self.update_busy = False
                    self.update_download = value
                    self.update_status.set("Download verified. Choose Install update when ready.")
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
            self.log_lines = 200
        self.log.see("end")
        self.log.configure(state="disabled")

    def close(self):
        self.closing = True
        for callback in self.root.tk.call("after", "info"):
            self.root.after_cancel(callback)
        self.background_cancel.set()
        self._disconnect()
        self.engine.shutdown()
        if self.history:
            self.history.close()
        self._wait_close(0)

    def _wait_close(self, count):
        if self.engine.worker.is_alive():
            if count == 100:
                messagebox.showwarning("Waiting for output", "Output is still stopping. Verify the radio is unkeyed. The application will remain open while cleanup finishes.")
            self.root.after(50, lambda: self._wait_close(count + 1))
        else:
            self.root.destroy()


def main():
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DXTalker.Desktop")
    root = tk.Tk()
    Application(root)
    root.mainloop()
