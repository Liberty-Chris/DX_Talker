"""Shared desktop interface. All Tk calls stay on the main thread."""
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
from .linux_speech import EspeakSpeech
from .engine import Engine
from .models import UTC, Settings, load_settings, parse_line, save_settings, settings_path
from .ptt import serial_ports
from .source import SourceClient
from .profiles import ProfileStore, SOURCE_FIELDS
from .history import History
from . import updates
from .diagnostics import Diagnostics
from . import transfer
from .usability import Usability
from .rendering import RenderCache
from .preferences import RADIO_FIELDS, PREFERENCE_FIELDS, FORMAT_FIELDS, read_group, load_radio_draft, save_radio_draft


def resource_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


class Application(Usability):
    def __init__(self, root):
        self.root = root
        self.render_cache = RenderCache()
        self._spot_view_revision = 0
        root.title(f"DX Talker {__version__}")
        width = max(900, min(1160, root.winfo_screenwidth() - 60))
        height = max(600, min(830, root.winfo_screenheight() - 100))
        root.geometry(f"{width}x{height}+20+10")
        root.minsize(900, 600)
        self.events = queue.Queue(maxsize=1500)
        self.control_events = queue.SimpleQueue()
        self.raw_events = queue.Queue(maxsize=30)
        self.source = None
        self.connection_phase = "disconnected"
        self.connection_controls = []
        self.listening_controls = []
        self.rf_controls = []
        self.source_generation = 0
        self.source_ready = False
        self.spots = {}
        self.spot_reasons = {}
        self.spot_states = {}
        self.rejected_spots = []
        self.spot_serial = 0
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
        try:
            self.diagnostics = Diagnostics(enabled=self.settings.diagnostics_enabled)
        except OSError:
            self.diagnostics = Diagnostics(enabled=False)
            settings_error += " Diagnostic logs could not be opened. Check folder permissions."
        root.report_callback_exception = self._callback_exception
        self._previous_thread_hook = threading.excepthook
        def thread_failure(args):
            self.diagnostics.exception('thread_exception', args.exc_type, args.exc_traceback)
            self.engine.stop('A background task failed. Output stopped. See diagnostic logs.')
            self.emit('journal', 'A background task failed. Export diagnostic logs for investigation.')
        threading.excepthook = thread_failure
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
        self.engine.source_available = lambda: self.source is not None and self.source.connected.is_set()
        self.preference_jobs = {}
        self.preference_errors = {}
        self.transition_serial = 0
        self.profile_drafts = {}
        self.profile_edit_key = None
        self.variables = {}
        for f in fields(Settings):
            value=getattr(self.settings,f.name)
            self.variables[f.name]=tk.BooleanVar(value=value) if type(value) is bool else tk.StringVar(value=str(value))
        self.combos = {}
        self.field_widgets = {}
        self.theme = tk.StringVar(value=load_appearance())
        brand = resource_root() / "assets/brand"
        self.logos = {name: tk.PhotoImage(file=str(brand / f"logo-{'light' if name == 'Light' else 'dark'}.png")).subsample(2)
                      for name in PALETTES}
        self.compact_logos={name:logo.subsample(2) for name,logo in self.logos.items()}
        self.icon = tk.PhotoImage(file=str(brand / "icon.png"))
        root.iconphoto(True, self.icon)
        if sys.platform == "win32":
            root.iconbitmap(str(brand / "dxt.ico"))
        self._style()
        self._build()
        self._paint_widgets()
        self._build_usability()
        self._restore_radio_draft()
        self.initializing = False
        self._refresh_devices()
        self._refresh_spot_units()
        self._load_voices()
        self._configure_history()
        self.root.bind("<Escape>", lambda event: self._stop())
        self.root.bind("<F6>", lambda event: self.guard(self._preview_spot)())
        self.root.bind("<F8>", lambda event: self.guard(self._listen)())
        self.root.bind("<Alt-c>", lambda event: self._focus_command())
        self.notebook.enable_traversal()
        self.root.bind("<Configure>", self._responsive_layout, add="+")
        root.after_idle(self._responsive_layout)
        root.after(2500, self._startup_update_check)
        root.after(86400000, self._scheduled_update_check)
        if settings_error:
            self._show_notice(settings_error)
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
        from .rounded import install
        install(self.root,p,self.theme.get())

    def _paint_widgets(self):
        p = PALETTES[self.theme.get()]
        self.brand_label.configure(image=(self.compact_logos if getattr(self,"compact_mode",False) else self.logos)[self.theme.get()])
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
        self._render_connections()

    def _change_theme(self, event=None):
        # Appearance never applies radio settings, stops a transmission or rearms RF.
        self._style()
        self._paint_widgets()
        try:
            save_appearance(self.theme.get())
        except OSError:
            self._show_notice("The theme changed but could not be saved for next time.")

    def _build(self):
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(20, 14))
        header.pack(fill="x")
        self.brand_label = ttk.Label(header, image=self.logos[self.theme.get()], style="Brand.TLabel")
        self.brand_label.pack(side="left")
        identity = ttk.Frame(header, style="Header.TFrame")
        identity.pack(side="left", padx=16)
        ttk.Label(identity, text="DX TALKER", style="Header.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(identity, text="Beta  /  " + __version__, style="Header.TLabel").pack(anchor="w", pady=(4, 0))
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
                                                  ("AUDIO OUTPUT", self.output_status),
                                                  ("ACTIVITY", self.activity))):
            status.columnconfigure(column, weight=1, uniform="status")
            card = ttk.Frame(status, style="Status.TFrame", padding=(0, 8))
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 4, 0))
            ttk.Label(card, text=title, style="Eyebrow.TLabel", padding=(14, 0)).pack(anchor="w")
            ttk.Label(card, textvariable=variable, style="Status.TLabel", wraplength=280).pack(anchor="w")
        self.error_notice=tk.StringVar()
        self.error_frame=ttk.Frame(self.root,padding=(18,6))
        ttk.Label(self.error_frame,textvariable=self.error_notice,wraplength=850).pack(side='left')
        ttk.Button(self.error_frame,text='Dismiss',command=self.error_frame.pack_forget).pack(side='right')
        notebook = ttk.Notebook(self.root)
        self.notebook = notebook
        notebook.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.tabs = {}
        self.scroll_tabs = []
        for name in ("Live spots", "Source", "Audio and PTT", "Identification", "Announcements", "Speech and access", "History and updates", "Help and Info", "Listening filters"):
            if name in ("Live spots", "Help and Info"):
                frame = ttk.Frame(notebook, padding=16)
                notebook.add(frame, text={"Help and Info": "Help"}.get(name, name))
            else:
                container = ttk.Frame(notebook)
                notebook.add(container, text={"Audio and PTT": "Audio / PTT", "Identification": "IDs", "Speech and access": "Speech", "History and updates": "Maintenance", "Listening filters": "Filters"}.get(name, name))
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
        self._format_changed()
        self._history_tab()
        self._help_tab()
        footer = ttk.Frame(self.root, padding=(18, 5, 18, 12))
        footer.pack(side="bottom", fill="x", before=notebook)
        self.save_status = tk.StringVar(value="Preferences save automatically. RF starts disabled.")
        ttk.Label(footer, textvariable=self.save_status, wraplength=540).pack(side="left")
        self.save_button = ttk.Button(footer, text="Apply radio changes", style="Accent.TButton", command=self.guard(self._apply))
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

    def _callback_exception(self, exc_type, exc_value, tb):
        self.diagnostics.exception('ui_exception', exc_type, tb)
        self.engine.stop('An interface error stopped output. See diagnostic logs.')
        self._show_notice('An unexpected interface error stopped output. Export diagnostic logs from History / Updates.')

    def _export_diagnostics(self):
        path = filedialog.asksaveasfilename(title='Export diagnostic report', defaultextension='.zip', filetypes=[('ZIP report', '*.zip')])
        if path:
            self.diagnostics.export(path)
            self._show_notice("Diagnostic report saved. No report was uploaded.")

    def guard(self, action):
        def wrapped():
            try:
                action()
            except Exception as exc:
                if not isinstance(exc, ValueError):
                    self.diagnostics.exception('action_exception', type(exc), exc.__traceback__)
                self._show_notice(str(exc) if isinstance(exc, ValueError) else "The action failed. Export diagnostics from Maintenance.")
        return wrapped

    def _field(self, parent, row, label, name, choices=None, note=None, browse=False, compact=False):
        parent.columnconfigure(1, weight=0 if compact else 1)
        value = getattr(self.settings, name)
        var = self.variables.get(name)
        if var is None:
            var = tk.BooleanVar(value=value) if type(value) is bool else tk.StringVar(value=str(value))
        self.variables[name] = var
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 18), pady=3 if compact else 6)
        if type(value) is bool:
            widget = ttk.Checkbutton(parent, variable=var)
        elif choices is not None:
            widget = ttk.Combobox(parent, textvariable=var, values=choices, state="readonly", width=45)
            self.combos[name] = widget
        elif type(value) is int:
            limits = {"port": (1, 65535), "poll_seconds": (15, 3600), "lead_ms": (0, 5000), "tail_ms": (0, 5000), "max_tx_seconds": (5, 120), "cw_wpm": (5, 50), "cw_hz": (300, 1500), "id_minutes": (1, 30), "voice_id_minutes": (1,120), "speech_rate": (-10, 10), "character_pause_ms": (0, 1000), "group_pause_ms": (0, 3000),
                      "volume_percent": (0, 100), "cw_volume_percent": (0, 100), "voice_id_volume_percent": (0, 100),
                      "local_volume_percent": (0, 100), "text_size": (10, 18), "receive_threshold_db": (-60, -5), "receive_quiet_seconds": (5, 10)}
            low, high = limits.get(name, (0, 10000000))
            widget = ttk.Spinbox(parent, textvariable=var, from_=low, to=high, width=12)
        else:
            widget = ttk.Entry(parent, textvariable=var, width=48)
        if compact and type(value) is not bool:
            width = 36 if name == "voice" else 44 if name.startswith("piper_") else 18 if choices is not None else 10
            widget.configure(width=width)
        self.field_widgets[name] = widget
        widget.grid(row=row, column=1, sticky="w" if compact else "ew", pady=3 if compact else 6)
        if browse:
            ttk.Button(parent, text="Browse", command=self.guard(self._browse_wav)).grid(row=row, column=2, padx=6)
        elif note:
            ttk.Label(parent, text=note, wraplength=260).grid(row=row, column=2, padx=12, sticky="w")
        var.trace_add("write", lambda *args, key=name: self._setting_changed(key))

    def _show_notice(self,text):
        self.error_notice.set(text)
        self.error_frame.pack(fill='x',before=self.notebook)

    def _open_filters(self):
        self._select_page('Listening filters')
        self.filter_editor.focus()

    def _sync_listening_editor(self, reset_filters=True):
        from .listening import FIELDS
        previous=self.initializing;self.initializing=True
        try:
            for key in (*FIELDS,'listening_presets'):self.variables[key].set(getattr(self.settings,key))
        finally:self.initializing=previous
        if reset_filters and hasattr(self,'filter_editor'):self.filter_editor.reset()

    def _apply_listening(self,settings, sync_editor=True):
        from .listening import FIELDS
        updated=replace(self.settings,**{key:getattr(settings,key) for key in (*FIELDS,'listening_presets')}).validate()
        save_settings(updated)
        self.settings=updated
        self.engine.update_listening(updated)
        self._sync_listening_editor(reset_filters=sync_editor)
        self._refresh_filtered_view()
        self._journal('Listening filters applied. Source connection preserved.')

    def _refresh_filtered_view(self):
        self._spot_view_revision += 1
        from .filtering import rejection
        for item,spot in reversed(list(self.spots.items())):
            reason=rejection(spot,self.settings);self.spot_reasons[item]=reason
            if not reason:self.tree.move(item,'','end')
            else:self.tree.detach(item)

    def _why_hidden(self):
        from collections import Counter
        from .filtering import rejection
        counts=Counter(reason for spot,reason in self.rejected_spots)
        counts.update(rejection(v,self.settings) for v in self.spots.values() if rejection(v,self.settings))
        window=tk.Toplevel(self.root);window.title('Why spots are hidden');window.transient(self.root)
        ttk.Label(window,text='Recent rejections before announcement admission. Rejected spots are excluded from the main list. Retained admitted rows: '+str(sum(not reason for reason in self.spot_reasons.values())),wraplength=500).pack(padx=16,pady=12)
        for reason,count in counts.most_common():ttk.Label(window,text=f'{reason}: {count}').pack(anchor='w',padx=16,pady=4)
        ttk.Button(window,text='Close',command=window.destroy).pack(pady=12)

    def _spot_dialog(self,myself=False):
        from .spotting import open_spot_dialog
        open_spot_dialog(self,myself)

    def _setting_changed(self, key=None, *args):
        if self.initializing or not hasattr(self, 'save_status'):
            return
        self._queue_preference(key)

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
        self.variables["frequency_unit"] = tk.StringVar(value=self.settings.frequency_unit)
        self.variables["frequency_unit"].trace_add("write", lambda *args: self._setting_changed("frequency_unit"))
        units = ttk.Frame(quick)
        units.pack(side="right", padx=8)
        for unit in ("kHz", "MHz"):
            ttk.Radiobutton(units, text=unit, value=unit, variable=self.variables["frequency_unit"]).pack(side="left", padx=4)
        toolbar = ttk.Frame(frame)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self._connection_control(toolbar).grid(row=0,column=0,sticky='ew',padx=(0,6))
        self._listening_control(toolbar).grid(row=0,column=1,sticky='ew',padx=(0,6))
        self._state_control(toolbar,'rf').grid(row=0,column=2,sticky='ew',padx=(0,6))
        ttk.Button(toolbar,text='Filters',command=self._open_filters).grid(row=0,column=3,sticky='ew')
        for column in range(4):toolbar.columnconfigure(column,weight=1)
        filters=ttk.Frame(toolbar)
        filters.grid(row=1,column=0,columnspan=4,sticky='ew',pady=(6,0))
        self.capability_buttons=[]
        selected=ttk.Button(filters,text='Preview selected',command=self.guard(self._preview_spot))
        selected.pack(side='left',padx=(0,6));self.capability_buttons.append((selected,'preview'))
        self.rejected_button=ttk.Button(filters,text='Spot details',command=self._show_spot_details)
        self.rejected_button.pack(side='left',padx=(0,6))
        spot_actions=ttk.Frame(toolbar)
        spot_actions.grid(row=2,column=0,columnspan=4,sticky='ew',pady=(6,0))
        self.spot_station_button=ttk.Button(spot_actions,text='Spot a station',command=self.guard(lambda:self._spot_dialog(False)))
        self.spot_station_button.pack(side='left',padx=(0,6))
        self.spot_myself_button=ttk.Button(spot_actions,text='Spot myself',command=self.guard(lambda:self._spot_dialog(True)))
        self.spot_myself_button.pack(side='left',padx=(0,6))
        tools=ttk.Menubutton(filters,text='More actions')
        menu=tk.Menu(tools,tearoff=False)
        for label,action in [('Sample preview',self._sample_preview),('Clear view',self._clear_spots),
                             ('Send ID now',self.engine.identify),('Cluster commands',lambda:self._focus_command(source=True)),
                             ('Announcement diagnostics',self._show_session_diagnostics)]:
            menu.add_command(label=label,command=self.guard(action))
        tools.configure(menu=menu);tools.pack(side='left')
        self.filter_summary=tk.StringVar()
        self.live_hint = ttk.Label(frame, textvariable=self.filter_summary, text="Spots appear here before RF is enabled. Select one to preview it locally.")
        self.live_hint.configure(wraplength=900)
        self.live_hint.grid(row=2, column=0, sticky="w", pady=(0, 8))
        columns = ("time", "dx", "frequency", "spotter", "mode", "source")
        table = ttk.Frame(frame)
        table.grid(row=3, column=0, sticky="nsew")
        self.tree = ttk.Treeview(table, columns=columns, show="tree headings", height=10, selectmode="browse",
                                 displaycolumns=('dx','time','frequency','spotter','mode','source'))
        self.tree.heading('#0', text='State')
        self.tree.column('#0', width=44, minwidth=44, stretch=False)
        self.status_images = self._make_status_images()
        self.tree.bind('<ButtonRelease-1>', self._status_click)
        self.tree.bind('<Return>', lambda event:self._show_spot_status())
        for key, title, width in zip(columns, ("UTC", "DX callsign", "Frequency kHz", "Spotted by", "Mode", "Source"), (90, 150, 140, 140, 65, 100)):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=55 if key=="mode" else 80)
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.queue_summary=tk.StringVar()
        queue_row=ttk.Frame(frame);queue_row.grid(row=4,column=0,sticky='ew')
        ttk.Label(queue_row,textvariable=self.queue_summary).pack(side='left')
        self.catch_up_button=ttk.Button(queue_row,text='Catch up to live',command=self.engine.catch_up);self.catch_up_button.pack(side='right')
        self.compact_commands_button=ttk.Button(queue_row,text='Cluster commands',command=lambda:self._focus_command(source=True))
        self.live_command_bar=self._command_bar(frame, 5)
        # The activity journal contains application events, never raw cluster text.
        self.activity_label = ttk.Label(frame, text="Activity")
        self.activity_label.grid(row=6, column=0, sticky="w", pady=(8, 4))
        self.log = tk.Text(frame, height=3, wrap="word", state="disabled", font=("Consolas", 9), relief="flat")
        self.log.grid(row=7, column=0, sticky="ew")

    def _profile_qr(self):
        from .sharing_ui import show_profile_qr
        show_profile_qr(self)

    def _export_profiles(self):
        if not self.profile_store or not self.profile_store.profiles:
            raise ValueError('Save a cluster profile first')
        raw = transfer.encode(transfer.document(self.profile_store.profiles, self.settings))
        path = filedialog.asksaveasfilename(title='Export profiles and filters', defaultextension='.dxt.json', filetypes=[('DX Talker transfer','*.json')])
        if path: Path(path).write_bytes(raw)

    def _cluster_directory(self):
        window = tk.Toplevel(self.root)
        window.title('Curated cluster directory')
        items = []
        listing = tk.Listbox(window, width=72, height=12)
        listing.pack(padx=12,pady=12)
        note = tk.StringVar(value="Choose a recommended cluster and add it to your profiles. Use your own callsign when connecting. Review dates reflect the supplied operator list, not a live availability check.")
        ttk.Label(window,textvariable=note,wraplength=580).pack(padx=12,pady=8)
        def populate(path):
            if Path(path).stat().st_size > transfer.MAX_BYTES: raise ValueError('Directory exceeds 64 KiB')
            entries = transfer.catalog(json.loads(Path(path).read_text()))
            items[:] = entries
            listing.delete(0,'end')
            for entry in items:
                c=entry['connection']
                listing.insert('end', f"{entry['name']}  {c['host']}:{c['port']} ({entry['status']})")
        def load():
            path = filedialog.askopenfilename(title='Load curated cluster directory',filetypes=[('JSON directory','*.json')])
            if path: populate(path)
        def add():
            choice = listing.curselection()
            if not choice: raise ValueError('Choose a directory entry')
            item = items[choice[0]]
            if item['status'] != 'active': raise ValueError('This directory entry is retired')
            if any(p['connection'] == item['connection'] for p in self.profile_store.profiles):
                raise ValueError('This connection is already saved')
            connection=dict(item['connection'])
            connection['login']=connection['login'] or self.variables['login'].get().strip()
            self.profile_store.save(item['name'], replace(self.settings, **connection))
            self._refresh_profiles()
            note.set('Added. Select the profile to enter your callsign and any required password. Nothing connected automatically.')
        ttk.Button(window,text='Load directory file',command=self.guard(load)).pack(side='left',padx=12,pady=12)
        ttk.Button(window,text='Add selected cluster',command=self.guard(add)).pack(side='left',padx=12,pady=12)
        bundled = resource_root() / 'assets/catalog/clusters.json'
        if bundled.exists(): populate(bundled)

    def _source_tab(self):
        page=self.tabs['Source']
        frame=ttk.Frame(page)
        frame.grid(row=0,column=0,sticky='nw')
        self.source_connection_panel=frame
        profiles = ttk.LabelFrame(frame, text="Cluster profiles", padding=12)
        profiles.grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.profile_name = tk.StringVar()
        self.remember_secret = tk.BooleanVar(value=False)
        ttk.Label(profiles, text="Saved profile").grid(row=0, column=0, sticky="w", padx=(0, 18))
        self.profile_picker = ttk.Combobox(profiles, textvariable=self.profile_choice, state="readonly", width=36, height=12)
        self.profile_picker.grid(row=0, column=1, sticky="w", pady=3)
        self.profile_picker.bind("<<ComboboxSelected>>", lambda event: self.guard(self._select_profile)())
        ttk.Label(profiles, text="Profile name").grid(row=1, column=0, sticky="w")
        self.profile_name_entry = ttk.Entry(profiles, textvariable=self.profile_name, width=38)
        self.profile_name_entry.grid(row=1, column=1, sticky="w", pady=3)
        buttons = ttk.Frame(profiles)
        buttons.grid(row=2, column=0, columnspan=2, sticky="w", pady=8)
        ttk.Button(buttons, text="New profile", command=self.guard(self._new_profile)).pack(side="left", padx=(0, 8))
        self.save_profile_button = ttk.Button(buttons, text="Save new profile", command=self.guard(self._save_profile))
        self.save_profile_button.pack(side="left", padx=(0, 8))
        self.delete_profile_button = ttk.Button(buttons, text="Delete profile", command=self.guard(self._delete_profile))
        self.delete_profile_button.pack(side="left", padx=(0, 8))
        self._connection_control(buttons).pack(side="left")
        sharing = ttk.Frame(profiles)
        sharing.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8,0))
        for label, action in (("QR to phone", self._profile_qr), ("Export profiles", self._export_profiles), ("Cluster directory", self._cluster_directory)):
            ttk.Button(sharing, text=label, command=self.guard(action)).pack(side="left", padx=(0,8))
        self.profile_status = tk.StringVar()
        ttk.Label(profiles, textvariable=self.profile_status, wraplength=610).grid(row=3, column=0, columnspan=2, sticky="w")
        details = ttk.LabelFrame(frame, text="Connection details", padding=12)
        details.grid(row=1, column=0, sticky="w", pady=(0, 12))
        details.columnconfigure(0, minsize=190)
        details.columnconfigure(2, weight=1)
        self._field(details, 0, "Source type", "source_type", ["TCP/Telnet", "HTTPS JSON"], compact=True)
        self.tcp_source_fields = ttk.Frame(details)
        self.tcp_source_fields.grid(row=1, column=0, columnspan=3, sticky="w")
        self.tcp_source_fields.columnconfigure(0, minsize=190)
        self._field(self.tcp_source_fields, 0, "Hostname", "host", compact=True)
        self.field_widgets["host"].configure(width=34)
        self._field(self.tcp_source_fields, 1, "Port", "port", compact=True)
        self.tcp_source_fields.grid_slaves(row=1, column=0)[0].grid_configure(row=0, column=2, padx=(12, 8))
        self.field_widgets["port"].configure(width=7)
        self.field_widgets["port"].grid_configure(row=0, column=3)
        self._field(self.tcp_source_fields, 1, "Login callsign", "login", compact=True)
        self.field_widgets["login"].configure(width=18)
        self.https_source_fields = ttk.Frame(details)
        self.https_source_fields.grid(row=2, column=0, columnspan=3, sticky="w")
        self.https_source_fields.columnconfigure(0, minsize=190)
        self._field(self.https_source_fields, 0, "JSON feed URL", "feed_url", compact=True)
        self.field_widgets["feed_url"].configure(width=48)
        self._field(self.https_source_fields, 1, "Poll interval (s)", "poll_seconds", note="15 to 3600 seconds", compact=True)
        self.secret_label = ttk.Label(details, text="Cluster password (optional)")
        self.secret_label.grid(row=3, column=0, sticky="w", pady=3, padx=(0, 18))
        self.secret = tk.StringVar()
        self.secret_visible = False
        secret_field = ttk.Frame(details)
        secret_field.grid(row=3, column=1, columnspan=2, sticky="w")
        self.secret_entry = ttk.Entry(secret_field, textvariable=self.secret, show="*", width=30)
        self.secret_entry.grid(row=0, column=0, sticky="w")
        self.secret_toggle = ttk.Button(secret_field, text="Show", command=self._toggle_secret, width=7)
        self.secret_toggle.grid(row=0, column=1, padx=(8, 0))
        ttk.Checkbutton(details, text="Remember password or token on this PC", variable=self.remember_secret).grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Label(details, text="Optional. Save the profile to keep its password or token protected for this account. Unchecked means session only.",
                  wraplength=610).grid(row=5, column=0, columnspan=3, sticky="w", pady=(4, 8))
        self.source_hint = tk.StringVar()
        ttk.Label(details, textvariable=self.source_hint, wraplength=610).grid(row=6, column=0, columnspan=3, sticky="w")
        self._command_bar(frame, 2)
        console = ttk.LabelFrame(frame, text="Unfiltered diagnostic console", padding=8)
        console.grid(row=3, column=0, sticky="w", pady=8)
        self.console_visible=tk.BooleanVar(value=False)
        ttk.Checkbutton(console,text='Show raw cluster traffic. Bypasses listening filters; not an announcement list.',variable=self.console_visible,command=lambda:self.raw_console.grid() if self.console_visible.get() else self.raw_console.grid_remove()).grid(row=0,column=0,sticky='w')
        self.raw_console = tk.Text(console, height=5, width=76, wrap="word", state="disabled", font=("Consolas", 10))
        self.raw_console.grid(row=1, column=0, pady=(6, 0))
        self.raw_console.grid_remove()
        self.raw_lines = []
        self._refresh_profiles()
        self.combos["source_type"].bind("<<ComboboxSelected>>", lambda event: self._source_type_changed(clear_secret=True))
        self._source_type_changed()
        from .filter_ui import build_filters
        self.filter_editor=build_filters(self,self.tabs["Listening filters"])
        self.filter_editor.frame.pack(fill="x", anchor="nw")

    def _layout_source_columns(self,width):
        self.source_column_layout = 'separate'

    def _audio_tab(self):
        frame = self.tabs["Audio and PTT"]
        outputs = ttk.LabelFrame(frame, text="Audio outputs", padding=12)
        outputs.grid(row=0, column=0, sticky="w", pady=(0, 12))
        self._field(outputs, 0, "Local listening", "preview_device", [], compact=True)
        self._field(outputs, 1, "Radio output", "radio_device", [], compact=True)
        for name in ("preview_device", "radio_device"):
            self.field_widgets[name].configure(width=48)
        ttk.Button(outputs, text="Refresh devices", command=self._refresh_devices).grid(row=2, column=1, sticky="w", pady=(8, 0))
        ttk.Label(outputs, text="Choose exact output names. Keep local and radio outputs separate for listening tests.",
                  wraplength=610).grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ptt = ttk.LabelFrame(frame, text="Push to talk", padding=12)
        ptt.grid(row=1, column=0, sticky="w", pady=(0, 12))
        ptt.columnconfigure(0, minsize=120)
        ptt.columnconfigure(2, weight=1)
        self._field(ptt, 0, "Method", "ptt_method", ["VOX", "RTS", "DTR", "RTS+DTR"], compact=True)
        self.serial_ptt_fields = ttk.Frame(ptt)
        self.serial_ptt_fields.grid(row=1, column=0, columnspan=3, sticky="w")
        self.serial_ptt_fields.columnconfigure(0, minsize=120)
        self._field(self.serial_ptt_fields, 0, "Serial port", "serial_port", [], compact=True)
        self._field(self.serial_ptt_fields, 1, "Active high", "active_high", note="Unchecked means active low", compact=True)
        self.ptt_hint = tk.StringVar()
        ttk.Label(ptt, textvariable=self.ptt_hint, wraplength=610).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Button(ptt,text='Test PTT for 2 seconds',command=self.guard(self._test_ptt)).grid(row=3,column=0,columnspan=2,sticky='w',pady=8)
        timing = ttk.LabelFrame(frame, text="Transmit timing", padding=12)
        timing.grid(row=2, column=0, sticky="w", pady=(0, 12))
        self._field(timing, 0, "Lead time (ms)", "lead_ms", note="0 to 5000 ms", compact=True)
        self._field(timing, 1, "Tail time (ms)", "tail_ms", note="0 to 5000 ms", compact=True)
        self._field(timing, 2, "Maximum transmit (s)", "max_tx_seconds", note="5 to 120 seconds, including lead and tail", compact=True)
        levels = ttk.LabelFrame(frame, text="Audio levels", padding=12)
        levels.grid(row=3, column=0, sticky="w", pady=(0, 12))
        for row, (label, name) in enumerate((("Spot radio (%)", "volume_percent"), ("CW ID (%)", "cw_volume_percent"),
                                            ("Voice ID (%)", "voice_id_volume_percent"), ("Local listening (%)", "local_volume_percent"))):
            self._field(levels, row, label, name, note="0 to 100" if row == 0 else None, compact=True)
        ttk.Label(levels, text="Local listening also scales previews. Zero mutes the selected category.",
                  wraplength=610).grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))
        receive = ttk.LabelFrame(frame, text="Receive audio transmit hold", padding=12)
        receive.grid(row=4, column=0, sticky="w", pady=(0, 12))
        self._field(receive, 0, "Monitor radio receive audio", "receive_guard", compact=True)
        self._field(receive, 1, "Receive input", "receive_device", [], compact=True)
        self.field_widgets['receive_device'].configure(width=48)
        self._field(receive, 2, "Audio threshold (dBFS)", "receive_threshold_db", note="Minus 60 to minus 5. Lower detects quieter audio.", compact=True)
        self._field(receive, 3, "Quiet delay (s)", "receive_quiet_seconds", note="5 to 10 seconds after received audio ends", compact=True)
        self.receive_status = tk.StringVar(value='Receive monitor off')
        ttk.Label(receive, textvariable=self.receive_status, wraplength=610).grid(row=4, column=0, columnspan=3, sticky='w', pady=8)
        self.receive_test_button = ttk.Button(receive, text='Test receive input', command=self.guard(self._test_receive))
        self.receive_test_button.grid(row=5, column=1, sticky='w')
        ttk.Label(receive, text='Test with receiver audio before enabling RF. Use squelched receive audio, never a microphone or a mix containing DX Talker output. Input failure stops RF. Audio is measured locally and never recorded.', wraplength=610).grid(row=6, column=0, columnspan=3, sticky='w', pady=(8,0))
        self.variables["ptt_method"].trace_add("write", lambda *args: self._ptt_method_changed())
        self._ptt_method_changed()

        if sys.platform == 'win32':
            power = ttk.LabelFrame(frame, text='Power management', padding=12)
            power.grid(row=5, column=0, sticky='w', pady=(0,12))
            self._field(power, 0, 'Keep awake', 'keep_awake', ['Off', 'Computer', 'Computer and display'], compact=True)
            ttk.Label(power, text='Applies while listening, RF or a preview is active. Does not change Num Lock, screensaver or lock settings. Save and apply.', wraplength=610).grid(row=1,column=0,columnspan=3,sticky='w',pady=(8,0))

    def _test_ptt(self):
        keys=('ptt_method','serial_port','active_high','receive_guard','receive_device','receive_threshold_db','receive_quiet_seconds','max_tx_seconds')
        values={}
        for key in keys:
            try:values[key]=type(getattr(Settings(),key))(self.variables[key].get())
            except (ValueError,tk.TclError):raise ValueError('Check '+key.replace('_',' ')) from None
        self.engine.test_ptt(replace(self.settings,**values))

    def _test_receive(self):
        if self.engine.enabled or self.engine.local_enabled or self.engine.busy:
            raise ValueError('Stop output before testing the receive input')
        if self.engine.monitor.stream is not None:
            self.engine.monitor.close()
        else:
            settings = self._read_settings()
            if not settings.receive_device:
                raise ValueError('Choose a receive input first')
            self.engine.monitor.start(settings)

    def _receive_meter(self):
        monitor=self.engine.monitor
        state,level,remaining=monitor.snapshot()
        descriptions={'off':'Receive monitor off','fault':'Input unavailable. '+monitor.fault_message(),
                      'starting':'Waiting for the first input samples','busy':'Audio above threshold. RF waiting.',
                      'waiting':f'Quiet delay. {remaining:.1f} seconds remaining.','clear':'Channel clear.'}
        measured=f' Measured {level:.0f} dBFS.' if state not in ('off','starting','fault') and level is not None else ' No current measurement.' if state!='off' else ''
        self.render_cache.set(self.receive_status,descriptions[state]+measured)
        if state=='fault' and getattr(self,'last_receive_fault',None)!=monitor.fault_code:
            self.diagnostics.record('receive_input_fault',code=monitor.fault_code)
        self.last_receive_fault=monitor.fault_code if state=='fault' else None
        self.render_cache.configure(self.receive_test_button,state='disabled' if self.engine.enabled or self.engine.local_enabled or self.engine.busy else 'normal',text='Stop receive test' if state!='off' else 'Test receive input')

    def _ptt_method_changed(self):
        vox = self.variables["ptt_method"].get() == "VOX"
        self.serial_ptt_fields.grid_remove() if vox else self.serial_ptt_fields.grid()
        self.ptt_hint.set("VOX needs a radio or interface already set up for VOX; the app sends audio without controlling a PTT line." if vox else
                          "RTS/DTR control lines do not send CAT commands. No baud setting is needed for this method. Choose the compatible interface and polarity.")

    def _id_tab(self):
        frame = self.tabs["Identification"]
        cw = ttk.LabelFrame(frame, text="CW identification", padding=12)
        cw.grid(row=0, column=0, sticky="w", pady=(0, 12))
        cw.columnconfigure(0, minsize=120)
        self._field(cw, 0, "ID text", "cw_text", compact=True)
        self.field_widgets["cw_text"].configure(width=38)
        self._field(cw, 1, "Speed (WPM)", "cw_wpm", note="5 to 50 WPM", compact=True)
        self._field(cw, 2, "Tone (Hz)", "cw_hz", note="300 to 1500 Hz", compact=True)
        ttk.Button(cw, text="Preview CW locally", command=self.guard(lambda: self._preview("cw"))).grid(row=0, column=2, sticky="w", padx=12)
        voice = ttk.LabelFrame(frame, text="Voice identification", padding=12)
        voice.grid(row=1, column=0, sticky="w", pady=(0, 12))
        voice.columnconfigure(0, minsize=120)
        self._field(voice, 0, "Source", "voice_mode", ["Speech", "WAV"], compact=True)
        self.voice_id_speech_fields = ttk.Frame(voice)
        self.voice_id_speech_fields.grid(row=1, column=0, columnspan=3, sticky="w")
        self.voice_id_speech_fields.columnconfigure(0, minsize=120)
        self._field(self.voice_id_speech_fields, 0, "ID text", "voice_text", compact=True)
        self.field_widgets["voice_text"].configure(width=38)
        pause_controls=ttk.Frame(self.voice_id_speech_fields);pause_controls.grid(row=1,column=0,columnspan=3,sticky='w',pady=6)
        ttk.Label(pause_controls,text='Pause (seconds)').pack(side='left',padx=(0,8))
        pause_seconds=tk.IntVar(value=1)
        ttk.Spinbox(pause_controls,from_=1,to=10,width=4,textvariable=pause_seconds).pack(side='left')
        def insert_pause():
            seconds=pause_seconds.get()
            if not 1<=seconds<=10:raise ValueError('Choose a pause from one to ten seconds')
            entry=self.field_widgets['voice_text'];entry.insert(tk.INSERT,f' [pause {seconds}s] ');entry.focus_set()
        ttk.Button(pause_controls,text='Insert pause',command=self.guard(insert_pause)).pack(side='left',padx=8)
        self.voice_id_wav_fields = ttk.Frame(voice)
        self.voice_id_wav_fields.grid(row=2, column=0, columnspan=3, sticky="w")
        self.voice_id_wav_fields.columnconfigure(0, minsize=120)
        self._field(self.voice_id_wav_fields, 0, "WAV file", "voice_wav", browse=True, compact=True)
        self.field_widgets["voice_wav"].configure(width=38)
        ttk.Button(voice, text="Preview voice locally", command=self.guard(lambda: self._preview("voice"))).grid(row=0, column=2, sticky="w", padx=12)
        ttk.Label(voice, text="Voice and delivery settings are in Speech. Local previews do not assert serial PTT.",
                  wraplength=550).grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self.variables["voice_mode"].trace_add("write", lambda *args: self._voice_id_source_changed())
        self._voice_id_source_changed()
        schedule = ttk.LabelFrame(frame, text="ID schedule", padding=12)
        schedule.grid(row=2, column=0, sticky="w", pady=(0, 12))
        self._field(schedule, 0, "Policy", "id_mode", ["CW", "Voice", "Alternate", "Both", "Independent"], compact=True)
        self._field(schedule, 1, "CW / policy interval (minutes)", "id_minutes", note="1 to 30 minutes", compact=True)
        self._field(schedule,2,'Voice interval (minutes)','voice_id_minutes',note='Independent policy only. 1 to 120 minutes.',compact=True)
        self.independent_id_widgets=list(schedule.grid_slaves(row=2))
        def id_policy_changed(*args):
            for widget in self.independent_id_widgets:
                widget.grid() if self.variables['id_mode'].get()=='Independent' else widget.grid_remove()
        self.variables['id_mode'].trace_add('write',id_policy_changed);id_policy_changed()
        ttk.Label(frame, text="Independent gives CW and voice separate schedules. Audio never overlaps.\nRF starts with an ID. IDs take priority over spots. Both sends CW followed by voice.\nFor Both, a recorded voice ID must be mono 22050 Hz PCM16.",
                  wraplength=650).grid(row=3, column=0, sticky="w")

    def _voice_id_source_changed(self):
        recorded = self.variables["voice_mode"].get() == "WAV"
        self.voice_id_speech_fields.grid_remove() if recorded else self.voice_id_speech_fields.grid()
        self.voice_id_wav_fields.grid() if recorded else self.voice_id_wav_fields.grid_remove()

    def _policy_tab(self):
        page = self.tabs["Announcements"]
        frame = ttk.Frame(page)
        frame.grid(row=0,column=0,sticky='nw')
        self._format_editor(frame)
        timing = ttk.LabelFrame(frame, text="Timing and repeats", padding=12)
        timing.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self._field(timing, 0, "Maximum spot age (s)", "max_age_seconds", note="30 to 600 seconds", compact=True)
        self._field(timing, 1, "Repeat suppression (s)", "repeat_seconds", note="30 to 3600 seconds", compact=True)
        self._field(timing, 2, "Gap between spots (s)", "spacing_seconds", note="0 to 120 seconds. Zero adds no pause.", compact=True)
        supervision = ttk.LabelFrame(frame, text="RF supervision", padding=12)
        supervision.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        self.variables["supervised_ack"] = tk.BooleanVar(value=self.settings.supervised_ack)
        self.channel_ack = self.variables["supervised_ack"]
        # Retain the old saved value for settings compatibility; it no longer gates RF.
        ttk.Label(supervision, text="Optional receive audio monitoring in Audio / PTT can hold transmissions while audio is detected. Supervise operation on a clear or coordinated channel. RF Enable does not require an acknowledgement.",
                  wraplength=550).grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text="Only validated spots are spoken. Comments and cluster commands are excluded.\nQueue: up to 100 spots. Starting output does not replay displayed history.",
                  wraplength=650).grid(row=3, column=0, sticky="w")

    FORMAT_FIELDS = ("announcement_order", "announcement_intro", "include_intro",
                     "include_callsign", "include_frequency", "speak_units")
    FORMAT_PRESETS = {
        "Frequency first": ("intro,frequency,callsign", "New DX on", True),
        "Callsign first": ("intro,callsign,frequency", "New DX", True),
        "Callsign + frequency": ("callsign,frequency,intro", "New DX", False),
    }

    def _format_editor(self, parent, row=0):
        frame = ttk.LabelFrame(parent, text="Announcement format", padding=12)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        presets = ttk.Frame(frame)
        presets.grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(presets, text="Preset").pack(side="left", padx=(0, 12))
        self.format_preset = tk.StringVar()
        picker = ttk.Combobox(presets, textvariable=self.format_preset,
                              values=list(self.FORMAT_PRESETS) + ["Custom"], state="readonly", width=24)
        picker.pack(side="left")
        picker.bind("<<ComboboxSelected>>", lambda event: self._format_preset_selected())
        for name in self.FORMAT_FIELDS:
            value = getattr(self.settings, name)
            self.variables[name] = tk.BooleanVar(value=value) if type(value) is bool else tk.StringVar(value=value)
        rows = ttk.Frame(frame)
        rows.grid(row=1, column=0, sticky="w")
        self.format_rows = {}
        for part, label in (("intro", "Intro"), ("callsign", "Callsign"), ("frequency", "Frequency")):
            row = ttk.Frame(rows)
            include = ttk.Checkbutton(row, text=label, variable=self.variables["include_" + part], width=13)
            include.grid(row=0, column=0, sticky="w")
            if part == "intro":
                content = ttk.Combobox(row, textvariable=self.variables["announcement_intro"],
                                       values=["New DX", "New DX on"], width=28)
            elif part == "frequency":
                content = ttk.Checkbutton(row, text="Speak units (kHz / MHz)", variable=self.variables["speak_units"], width=30)
            else:
                content = ttk.Label(row, text="Phonetic callsign", width=30)
            content.grid(row=0, column=1, sticky="w", padx=(0, 12))
            up = ttk.Button(row, text="Up", width=5, command=lambda p=part: self._move_format(p, -1))
            down = ttk.Button(row, text="Down", width=6, command=lambda p=part: self._move_format(p, 1))
            up.grid(row=0, column=2, padx=(0, 4))
            down.grid(row=0, column=3)
            for button in (up, down):
                def activate(event, b=button):
                    b.invoke()
                    return "break"
                button.bind("<Return>", activate)
            self.format_rows[part] = {"row": row, "content": content, "up": up, "down": down}
        self.format_example = tk.StringVar()
        ttk.Label(frame, textvariable=self.format_example, wraplength=610).grid(row=2, column=0, sticky="w", pady=(10, 8))
        ttk.Button(frame, text="Listen to example", command=self.guard(self._preview_format)).grid(row=3, column=0, sticky="w")
        ttk.Label(frame, text="Uncheck a section to omit it. Units stay with frequency. Intro accepts your own text.",
                  wraplength=610).grid(row=4, column=0, sticky="w", pady=(8, 0))
        for name in self.FORMAT_FIELDS + ("frequency_unit",):
            self.variables[name].trace_add("write", self._format_changed)

    def _format_settings(self):
        values = {name: self.variables[name].get() for name in self.FORMAT_FIELDS + ("frequency_unit",)}
        return replace(self.settings, **values).validate_format()

    def _format_changed(self, *args):
        self._setting_changed("format")
        order = self.variables["announcement_order"].get().split(",")
        content_width = max(item["content"].winfo_reqwidth() for item in self.format_rows.values()) + 12
        for index, part in enumerate(order):
            item = self.format_rows[part]
            item["row"].columnconfigure(1, minsize=content_width)
            item["row"].grid(row=index, column=0, sticky="w", pady=3)
            item["up"].configure(state="disabled" if index == 0 else "normal")
            item["down"].configure(state="disabled" if index == 2 else "normal")
            item["content"].configure(state="normal" if self.variables["include_" + part].get() else "disabled")
        self.format_preset.set("Custom")
        try:
            settings = self._format_settings()
            now = datetime.now(UTC)
            spot = parse_line(f"DX de N0CALL: 14025.5 WB4IUY/P {now:%H%M}Z", "sample", now)
            self.format_example.set("Example: " + ". ".join(text for _, text in spot.announcement_groups(settings, phonetic=False)) + ".")
            for label, (order, intro, include) in self.FORMAT_PRESETS.items():
                if (settings.announcement_order == order and settings.announcement_intro == intro and
                        settings.include_intro == include and settings.include_callsign and
                        settings.include_frequency and settings.speak_units):
                    self.format_preset.set(label)
        except ValueError as exc:
            self.format_example.set(str(exc))

    def _move_format(self, part, direction):
        order = self.variables["announcement_order"].get().split(",")
        index = order.index(part)
        target = index + direction
        if 0 <= target < len(order):
            order[index], order[target] = order[target], order[index]
            self.variables["announcement_order"].set(",".join(order))

    def _format_preset_selected(self):
        preset = self.FORMAT_PRESETS.get(self.format_preset.get())
        if preset:
            order, intro, include = preset
            for name, value in (("announcement_order", order), ("announcement_intro", intro),
                                ("include_intro", include), ("include_callsign", True),
                                ("include_frequency", True), ("speak_units", True)):
                self.variables[name].set(value)

    def _preview_format(self):
        settings = self._preview_settings('spot')
        now = datetime.now(UTC)
        spot = parse_line(f"DX de N0CALL: 14025.5 WB4IUY/P {now:%H%M}Z", 'sample', now)
        self._start_preview('spot', spot, settings)

    def _connection_control(self, parent):
        return self._state_control(parent, "connection")

    def _listening_control(self, parent):
        return self._state_control(parent, "listening")

    def _state_control(self, parent, kind):
        action = {"connection": self._connection_action, "listening": self._listen, "rf": self._enable}[kind]
        shell = tk.Frame(parent)
        button = ttk.Button(shell, width=15,takefocus=True,command=self.guard(action))
        button.pack(fill="both", expand=True)
        item = {"shell": shell, "button": button, "hover": False, "focus": False, "kind": kind}
        {"connection": self.connection_controls, "listening": self.listening_controls, "rf": self.rf_controls}[kind].append(item)
        for event, key, value in (("<Enter>", "hover", True), ("<Leave>", "hover", False),
                                  ("<FocusIn>", "focus", True), ("<FocusOut>", "focus", False)):
            def changed(event, i=item, k=key, v=value):
                i[k] = v
                self._render_connections()
            button.bind(event, changed)
        button.bind("<Return>", lambda event: self.guard(action)())
        self._render_connections()
        return shell

    def _connection_action(self):
        if getattr(self,'pending_source',False):
            self.transition_serial+=1;self.pending_source=False
            self._render_connections()
            return
        if self.source is None or self._has_source_edits():
            self._connect()
        else:
            self._disconnect()

    def _render_connections(self):
        p = PALETTES[self.theme.get()]
        active = self.source is not None or getattr(self,'pending_source',False)
        connected = active and getattr(self.source, "connected", threading.Event()).is_set()
        for item in self.connection_controls + self.listening_controls + self.rf_controls:
            attention = item["hover"] or item["focus"]
            stopping = item["kind"] in ("listening", "rf") and self.engine.busy and self.engine.cancel.is_set()
            if item["kind"] == "rf":
                if self.engine.enabled:
                    text = "Disable RF" if attention else "RF enabled"
                    edge, background = ("#d63852", "#542334") if attention else (p["accent"], p["selected"])
                    ink = "#ffffff" if attention else p["ink"]
                else:
                    text = "Stopping..." if stopping else "Enable RF"
                    edge, background, ink = (p["accent"] if attention else p["edge"]), p["field"], p["ink"]
            elif item["kind"] == "listening":
                if self.engine.local_enabled:
                    text = "Muting..." if stopping else "Unmute" if self.engine.local_muted else "Volume zero" if self.settings.local_volume_percent == 0 else "Mute" if attention else "Listening"
                    if self.engine.enabled and not self.engine.local_muted and self.settings.local_volume_percent > 0:
                        text = 'Mute local' if attention else 'Monitoring RF'
                    if self.engine.local_muted:
                        edge,background,ink=(p["positive"],p["positive_bg"],p["positive_ink"]) if attention else (p["edge"],p["field"],p["ink"])
                    else:
                        edge, background = ("#d63852", "#542334") if attention else (p["accent"], p["selected"])
                        ink = "#ffffff" if attention else p["ink"]
                else:
                    text = "Stopping..." if stopping else "Monitor RF locally" if self.engine.enabled else "Listen locally"
                    edge, background, ink = (p["accent"] if attention else p["edge"]), p["field"], p["ink"]
            elif connected:
                if self._has_source_edits():
                    text='Switch cluster'
                    edge,background,ink=p['accent'],p['field'],p['ink']
                    rendered=(self.theme.get(),text,background,edge,ink,stopping)
                    if item.get('rendered')!=rendered:
                        from .rounded import button_style
                        item['button'].configure(text=text,style=button_style(self.root,p,background,edge,ink),state='normal')
                        item['rendered']=rendered
                    continue
                text = "Disconnect" if attention else "Connected"
                edge, background = ("#d63852", "#542334") if attention else (p["accent"], p["selected"])
                ink = "#ffffff" if attention else p["ink"]
            elif active:
                text = "Cancel" if attention else "Reconnecting..." if self.connection_phase == "retrying" else "Connecting..."
                edge, background = ("#d63852", "#542334") if attention else (p["edge"], p["field"])
                ink = "#ffffff" if attention else p["muted"]
            else:
                text = "Connect"
                edge, background, ink = (p["accent"] if attention else p["edge"]), p["field"], p["ink"]
            rendered=(self.theme.get(),text,background,edge,ink,stopping)
            if item.get("rendered") == rendered:
                continue
            from .rounded import button_style
            item["shell"].configure(background=p['bg'])
            style=button_style(self.root,p,background,edge,ink)
            item["button"].configure(text=text,style=style,state="disabled" if stopping else "normal")
            item["rendered"]=rendered

    def _refresh_spot_units(self):
        self.tree.heading("frequency", text="Frequency " + self.settings.frequency_unit)
        for item, spot in self.spots.items():
            values = list(self.tree.item(item, "values"))
            values[2] = spot.frequency_text(self.settings.frequency_unit)
            self.tree.item(item, values=values)

    def _focus_command(self,source=False):
        if not source and self.command_entries[0].winfo_ismapped():
            self.notebook.select(0);self.command_entries[0].focus_set();return
        self.notebook.select(1)
        def focus():
            self.root.update_idletasks()
            frame=self.tabs['Source'];canvas=next(c for f,c in self.scroll_tabs if f is frame)
            button=self.command_buttons[1]
            bottom=button.winfo_rooty()-frame.winfo_rooty()+button.winfo_height()+12
            canvas.yview_moveto(max(0,(bottom-canvas.winfo_height())/max(1,frame.winfo_height())))
            self.command_entries[1].focus_set()
        self.root.after_idle(focus)

    def _responsive_layout(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        compact = self.root.winfo_height() < 720 or self.settings.text_size>=14
        self.compact_mode=compact
        if not self.render_cache.changed('responsive', (compact,self.theme.get())):
            return
        self.brand_label.configure(image=(self.compact_logos if compact else self.logos)[self.theme.get()])
        for widget in (self.log, self.activity_label, self.live_command_bar):
            widget.grid_remove() if compact else widget.grid()
        if compact:self.compact_commands_button.pack(side='right',padx=8)
        else:self.compact_commands_button.pack_forget()

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
        return bar

    def _set_secret_visible(self, visible):
        self.secret_visible = visible
        self.secret_entry.configure(show="" if visible else "*")
        self.secret_toggle.configure(text="Hide" if visible else "Show")

    def _toggle_secret(self):
        self._set_secret_visible(not self.secret_visible)

    def _source_type_changed(self, clear_secret=False):
        tcp = self.variables["source_type"].get() == "TCP/Telnet"
        self.tcp_source_fields.grid() if tcp else self.tcp_source_fields.grid_remove()
        self.https_source_fields.grid_remove() if tcp else self.https_source_fields.grid()
        for name in ("host", "port", "login"):
            self.field_widgets[name].configure(state="normal" if tcp else "disabled")
        for name in ("feed_url", "poll_seconds"):
            self.field_widgets[name].configure(state="disabled" if tcp else "normal")
        self.secret_label.configure(text="Cluster password (optional)" if tcp else "HTTPS bearer token (optional)")
        label_width = max(190, self.secret_label.winfo_reqwidth() + 18)
        self.secret_label.master.columnconfigure(0, minsize=label_width)
        self.tcp_source_fields.columnconfigure(0, minsize=label_width)
        self.https_source_fields.columnconfigure(0, minsize=label_width)
        self.source_hint.set("Common login prompts are detected automatically. Use the visible command field below for other responses." if tcp else
                             "Enter an HTTPS JSON feed matching the Help contract. Ordinary website URLs are not feeds.")
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
        self._spot_view_revision += 1
        for row in list(self.spots):
            self.tree.delete(row)
        self.spots.clear()
        self.spot_reasons.clear()
        self.spot_states.clear()
        self.rejected_spots.clear()
        if hasattr(self,'rejected_button'):self.rejected_button.configure(text='Spot details')

    def _trim_spots(self):
        rows = list(self.spots)
        if len(rows)>self.settings.display_limit:self._spot_view_revision += 1
        for row in rows[:-self.settings.display_limit]:
            self.tree.delete(row)
            self.spots.pop(row, None)
            self.spot_reasons.pop(row,None)
            self.spot_states.pop(row,None)

    def _refresh_profiles(self):
        names = sorted((p["name"] for p in self.profile_store.profiles), key=str.casefold) if self.profile_store else []
        self.profile_picker.configure(values=names)
        self.live_profile_picker.configure(values=names)
        selected = self.selected_profile_id is not None
        self.save_profile_button.configure(text="Save changes" if selected else "Save new profile",
                                           state="normal" if self.profile_store else "disabled")
        self.delete_profile_button.configure(state="normal" if selected and self.profile_store else "disabled")
        if self.profile_store is None:
            self.profile_status.set("Saved profiles unavailable. Recover profiles.json before saving.")
        else:
            mode = "Editing selected profile. Save changes updates its name and connection details." if selected else "New profile. Enter a name and connection details, then save."
            self.profile_status.set(f"{len(names)} saved profile" + (". " if len(names) == 1 else "s. ") + mode)

    def _new_profile(self):
        login = self.variables["login"].get()
        previous_key=self.profile_edit_key
        self._stash_profile_draft()
        previous_draft=self.profile_drafts.pop('new',None) if previous_key=='new' else None
        self.selected_profile_id = None
        self.profile_choice.set("")
        self.profile_name.set("")
        defaults = replace(Settings(), login=login)
        for key in SOURCE_FIELDS:
            self.variables[key].set(getattr(defaults, key))
        self.secret.set("")
        self._set_secret_visible(False)
        self.remember_secret.set(False)
        self._source_type_changed()
        self._refresh_profiles()
        self._restore_profile_draft('new')
        if previous_draft and previous_draft['name']:
            self._offer_undo('New profile editor ready.',lambda:(self.profile_drafts.update({'new':previous_draft}),self._restore_profile_draft('new')))
        self.profile_name_entry.focus_set()

    def _select_profile(self):
        if not self.profile_store:
            raise ValueError("Recover profiles.json before using saved profiles")
        item = next(p for p in self.profile_store.profiles if p["name"] == self.profile_choice.get())
        credential_unavailable = False
        try:
            updated, secret = self.profile_store.load(item["id"], self.settings)
        except ValueError:
            # A credential tied to another Windows account must not make its
            # connection details impossible to edit or its profile undeletable.
            updated = replace(self.settings, **item["connection"])
            secret = ""
            credential_unavailable = True
        self._stash_profile_draft()
        self.selected_profile_id = item["id"]
        self.profile_name.set(item["name"])
        self.secret.set(secret)
        self.remember_secret.set(bool(item["secret"]) and not credential_unavailable)
        for key in SOURCE_FIELDS:
            self.variables[key].set(getattr(updated, key))
        self._source_type_changed()
        self._refresh_profiles()
        self._restore_profile_draft(item['id'])
        if credential_unavailable:
            self._profile_credential_notice(
                                   "The connection details were loaded, but This account could not unlock the saved password or token. "
                                   "Enter it again and choose whether to remember it before saving. "
                                   "Saving with Remember unchecked removes the stored credential. You can also delete this profile.")

    def _profile_settings(self):
        # Profile operations must not validate or apply unrelated pending radio edits.
        values = {}
        for key in SOURCE_FIELDS:
            value = self.variables[key].get()
            try:
                values[key] = int(value) if type(getattr(Settings(), key)) is int else value.strip()
            except (ValueError, tk.TclError):
                raise ValueError(f"Enter a valid number for {key.replace('_', ' ')}") from None
        return replace(self.settings, **values)

    def _save_profile(self):
        if not self.profile_store:
            raise ValueError("Recover profiles.json before saving profiles")
        item = self.profile_store.save(self.profile_name.get(), self._profile_settings(), self.secret.get(),
                                       self.remember_secret.get(), self.selected_profile_id)
        self.selected_profile_id = item["id"]
        self.profile_choice.set(item["name"])
        self.profile_drafts.pop(self.profile_edit_key, None)
        self.profile_edit_key = item['id']
        self._refresh_profiles()
        self._show_notice('Profile saved. The active connection is unchanged.')

    def _delete_profile(self):
        if self.selected_profile_id:
            item = next(p for p in self.profile_store.profiles if p['id'] == self.selected_profile_id)
            self.profile_store._write([p for p in self.profile_store.profiles if p['id'] != item['id']])
            self.profile_drafts.pop(item['id'], None)
            self.profile_edit_key = None
            self._new_profile()
            def restore():
                self.profile_store._write(self.profile_store.profiles + [item])
                self._refresh_profiles()
            self._offer_undo('Profile removed. The active session is unchanged.', restore, lambda:self.profile_store._forget(item['secret']))

    def _speech_tab(self):
        frame = self.tabs["Speech and access"]
        ttk.Label(frame, text="Set announcement format in Announcements.").grid(row=0, column=0, sticky="w", pady=(0, 10))
        delivery = ttk.LabelFrame(frame, text="Speech delivery", padding=12)
        delivery.grid(row=1, column=0, sticky="w", pady=(0, 12))
        self._field(delivery, 0, "Provider", "speech_provider", ["eSpeak NG" if sys.platform.startswith("linux") else "Windows", "Piper", "Recorded", "ElevenLabs"], compact=True)
        self._field(delivery, 1, "Frequency units", "frequency_unit", ["kHz", "MHz"],
                    note="Used by announcements and the live view.", compact=True)
        self._field(delivery, 2, "Speed", "speech_rate", note="Minus 10 to 10. Zero is normal.", compact=True)
        self._field(delivery, 3, "Character pause (ms)", "character_pause_ms", note="0 to 1000. Zero keeps natural spacing.", compact=True)
        self._field(delivery, 4, "Group pause (ms)", "group_pause_ms", note="0 to 3000. Intro, frequency and callsign.", compact=True)
        self.windows_speech_fields = ttk.LabelFrame(frame, text="System voice", padding=12)
        self.windows_speech_fields.grid(row=2, column=0, sticky="w", pady=(0, 12))
        self._field(self.windows_speech_fields, 0, "Voice", "voice", [""], compact=True)
        self.resolved_voice=tk.StringVar(value="System default voice. Preview to hear it.")
        ttk.Label(self.windows_speech_fields,textvariable=self.resolved_voice,wraplength=610).grid(row=2,column=0,columnspan=3,sticky="w",pady=8)
        self._field(self.windows_speech_fields, 1, "Gender preference", "voice_gender", ["Any", "Male", "Female"],
                    note="Used when Voice is blank. Installed voices determine availability.", compact=True)
        self.piper_speech_fields = ttk.LabelFrame(frame, text="Piper voice", padding=12)
        self.piper_speech_fields.grid(row=3, column=0, sticky="w", pady=(0, 12))
        self._field(self.piper_speech_fields, 0, "Executable", "piper_executable", compact=True)
        self._field(self.piper_speech_fields, 1, "ONNX model", "piper_model", compact=True)
        for row, name, title in ((0, "piper_executable", "Choose Piper executable"), (1, "piper_model", "Choose Piper ONNX model")):
            ttk.Button(self.piper_speech_fields, text="Browse", command=lambda n=name, t=title: self._browse_file(n, t)).grid(row=row, column=2, padx=8)
        ttk.Label(self.piper_speech_fields, text="Optional local runtime and model. The model chooses the voice.", wraplength=600).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self.recorded_speech_fields = ttk.LabelFrame(frame, text="Recorded voice", padding=12)
        self.recorded_speech_fields.grid(row=4,column=0,sticky="w",pady=(0,12))
        self._field(self.recorded_speech_fields,0,"Voice pack folder","voice_pack_root",compact=True)
        self.field_widgets['voice_pack_root'].configure(width=40)
        def choose_packs():
            value=filedialog.askdirectory(title='Choose folder containing voice packs')
            if value:self.variables['voice_pack_root'].set(value);self._refresh_voice_packs()
        ttk.Button(self.recorded_speech_fields,text='Browse',command=choose_packs).grid(row=0,column=2,padx=8)
        self._field(self.recorded_speech_fields,1,'Recorded voice','voice_pack',[],compact=True)
        self.pack_display = tk.StringVar()
        self.pack_ids = {}
        self.field_widgets['voice_pack'].configure(width=36, textvariable=self.pack_display)
        self.combos['voice_pack'].bind('<<ComboboxSelected>>', self._choose_recorded_pack)
        ttk.Label(self.recorded_speech_fields,text='Local pre-generated WAVs. No inference at playback. Custom intro words must exist in the chosen pack.',wraplength=600).grid(row=2,column=0,columnspan=3,pady=8)
        self.pack_storage_widgets=list(self.recorded_speech_fields.grid_slaves(row=0))
        for widget in self.pack_storage_widgets:widget.grid_remove()
        self.pack_storage_visible=tk.BooleanVar(value=False)
        ttk.Checkbutton(self.recorded_speech_fields,text='Advanced storage options',variable=self.pack_storage_visible,command=lambda:[w.grid() if self.pack_storage_visible.get() else w.grid_remove() for w in self.pack_storage_widgets]).grid(row=3,column=0,columnspan=3,sticky='w')
        self._refresh_voice_packs()
        ttk.Button(frame, text='Generate ElevenLabs recorded voice', command=self._elevenlabs_dialog).grid(row=5,column=0,sticky='w',pady=(0,12))
        self.eleven_speech_fields = ttk.LabelFrame(frame, text='ElevenLabs shared pilot voice', padding=12)
        self.eleven_speech_fields.grid(row=6, column=0, sticky='w', pady=(0,12))
        self._field(self.eleven_speech_fields,0,'Voice','eleven_voice',[],compact=True)
        self.eleven_display=tk.StringVar(value=self.settings.eleven_voice)
        self.eleven_voices={}
        self.field_widgets['eleven_voice'].configure(width=38,textvariable=self.eleven_display)
        self.combos['eleven_voice'].bind('<<ComboboxSelected>>',lambda event:self.variables['eleven_voice'].set(self.eleven_voices[self.eleven_display.get()]))
        ttk.Button(self.eleven_speech_fields,text='Refresh voices',command=self._load_shared_voices).grid(row=0,column=2,padx=8)
        self.eleven_status=tk.StringVar(value='Uses the DX Talker pilot account. No API key is required. Blank uses the service default voice.')
        ttk.Label(self.eleven_speech_fields,textvariable=self.eleven_status,wraplength=610).grid(row=1,column=0,columnspan=3,sticky='w',pady=(8,0))
        ttk.Label(self.eleven_speech_fields,text='Online synthesis sends announcement and voice ID text to our speech service and ElevenLabs. Testing limits apply. System speech, Piper and Recorded remain available. Speed is fixed; character and group pauses are retained.',wraplength=610).grid(row=2,column=0,columnspan=3,sticky='w',pady=(8,0))
        access = ttk.LabelFrame(frame, text="Interface", padding=12)
        access.grid(row=7, column=0, sticky="w", pady=(0, 12))
        self._field(access, 0, "Text size", "text_size", note="10 to 18 points. High contrast is in Appearance.", compact=True)
        controls = ttk.Frame(frame)
        controls.grid(row=0, column=0, sticky="e", pady=(0, 10))
        ttk.Button(controls, text="Preview sample speech", command=self.guard(self._preview_sample)).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Speech setup and shortcuts", command=self._speech_help).pack(side="left")
        self.combos["speech_provider"].bind("<<ComboboxSelected>>", lambda event: self._speech_provider_changed())
        self._speech_provider_changed()

    def _elevenlabs_dialog(self):
        from .elevenlabs_ui import ElevenLabsDialog
        ElevenLabsDialog(self)

    def _speech_provider_changed(self):
        windows = self.variables["speech_provider"].get() in ("Windows", "eSpeak NG")
        self.windows_speech_fields.grid() if windows else self.windows_speech_fields.grid_remove()
        piper = self.variables["speech_provider"].get() == "Piper"
        recorded = self.variables["speech_provider"].get() == "Recorded"
        self.piper_speech_fields.grid() if piper else self.piper_speech_fields.grid_remove()
        self.recorded_speech_fields.grid() if recorded else self.recorded_speech_fields.grid_remove()
        eleven = self.variables['speech_provider'].get() == 'ElevenLabs'
        self.eleven_speech_fields.grid() if eleven else self.eleven_speech_fields.grid_remove()
        self.field_widgets["speech_rate"].configure(state="disabled" if recorded or eleven else "normal")

    def _load_shared_voices(self):
        if getattr(self,'shared_voices_loading',False):return
        self.shared_voices_loading=True
        self.eleven_status.set('Loading shared pilot voices...')
        def task():
            from .cloud_speech import SharedSpeech
            try:self.emit('shared_voices',SharedSpeech().voices(self.background_cancel))
            except Exception as exc:self.emit('shared_voices_error',str(exc) if isinstance(exc,ValueError) else 'Shared voices are unavailable. Contact the pilot administrator.')
        threading.Thread(target=task,daemon=True,name='Shared speech voices').start()

    def _choose_recorded_pack(self,event=None):
        label=self.pack_display.get()
        if label in self.pack_ids:
            self.variables['voice_pack_root'].set(self.pack_roots[label])
            self.variables['voice_pack'].set(self.pack_ids[label])

    def _refresh_voice_packs(self):
        from .voicepacks import installed
        roots=[self.variables['voice_pack_root'].get(),str(settings_path().parent/'voices'),str(resource_root()/'assets/voices')]
        self.pack_ids={};self.pack_roots={}
        for root in dict.fromkeys(roots):
            for identity,label in installed(root).items():
                display=label
                if display in self.pack_ids:display+=' · '+Path(root).name
                self.pack_ids[display]=identity;self.pack_roots[display]=root
        self.combos['voice_pack'].configure(values=list(self.pack_ids))
        selected=self.variables['voice_pack'].get();root=self.variables['voice_pack_root'].get()
        self.pack_display.set(next((label for label,identity in self.pack_ids.items() if identity==selected and self.pack_roots[label]==root),''))

    def _speech_help(self):
        self._select_page("Help and Info")
        self.help_topic.set(next(page["title"] for page in self.help_topics if page["id"] == "speech"))
        self._show_help()

    def _browse_file(self, name, title):
        value = filedialog.askopenfilename(title=title)
        if value:
            self.variables[name].set(value)

    def _preview_sample(self):
        now = datetime.now(UTC)
        spot = parse_line(f"DX de N0CALL: 14025.5 WB4IUY/P {now:%H%M}Z", 'sample', now)
        self._start_preview('spot', spot)

    def _listen(self):
        self._flush_preferences(('preview_device','local_volume_percent'))
        if self.engine.local_enabled:
            muted = not self.engine.local_muted
            if not muted:
                if self.engine.enabled:
                    self.engine.set_local_muted(False)
                else:
                    self._when_idle(lambda: self.engine.set_local_muted(False))
            else:
                self.engine.set_local_muted(True)
        else:
            if not self.engine.settings.preview_device:
                self._select_page('Audio and PTT')
                self.field_widgets['preview_device'].focus_set()
                raise ValueError('Choose Local listening speakers in Audio / PTT. The choice saves automatically.')
            self._confirm_preview()
            if self.engine.enabled:
                self.engine.listen_locally()
            else:
                self._when_idle(self.engine.listen_locally, stop=True)
        self._render_connections()

    def _history_tab(self):
        groups=ttk.Notebook(self.tabs['History and updates'])
        groups.grid(row=0,column=0,sticky='nsew')
        history=ttk.Frame(groups,padding=12);updates_frame=ttk.Frame(groups,padding=12);diagnostics=ttk.Frame(groups,padding=12)
        for title,panel in [('Updates',updates_frame),('History',history),('Diagnostics',diagnostics)]:groups.add(panel,text=title)
        frame=history
        self._field(frame, 0, "Live view maximum spots", "display_limit", note="50 to 5000. Oldest rows leave the view.")
        self._field(frame, 1, "Keep spot and connection history", "logging_enabled")
        self._field(frame, 2, "History folder", "log_directory", note="Blank uses the DXTalker settings folder / logs.")
        ttk.Button(frame, text="Choose folder", command=self._choose_log_folder).grid(row=3, column=1, sticky="w")
        self._field(frame, 4, "History file size in MiB", "log_max_mb", note="1 to 100 MiB per file")
        self._field(frame, 5, "History backup files", "log_backups", note="1 to 30 plus the active file")
        ttk.Button(frame, text="Open history folder", command=self.guard(self._open_history)).grid(row=6, column=1, sticky="w", pady=8)
        frame=diagnostics
        self._field(frame, 0, "Keep local diagnostic logs", "diagnostics_enabled", note="No automatic upload. Restart to apply.")
        ttk.Button(frame, text="Export diagnostic report", command=self.guard(self._export_diagnostics)).grid(row=1, column=1, sticky="w", pady=8)
        frame=updates_frame
        self._field(frame, 7, "Check for updates automatically", "check_updates")
        self._field(frame, 8, "Update channel", "update_channel", ["Pilot", "Stable"])
        self.update_status = tk.StringVar(value="Installed version: " + __version__)
        ttk.Label(frame, textvariable=self.update_status, wraplength=800).grid(row=9, column=0, columnspan=3, sticky="w", pady=12)
        controls = ttk.Frame(frame)
        controls.grid(row=10, column=0, columnspan=3, sticky="w")
        for label, action in (("Check now", self._check_updates), ("Release page", self._release_page),
                              ("Download update", self._download_update), ("Install and restart", self._install_update)):
            button=ttk.Button(controls,text=label,command=self.guard(action))
            button.pack(side='left',padx=(0,8))
            if label in ('Check now','Download update','Install and restart'):
                self.capability_buttons.append((button,{'Check now':'check','Download update':'download','Install and restart':'install'}[label]))
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
            subprocess.Popen(["xdg-open", str(directory)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
                self.emit("update_result", updates.check_report(channel))
            except Exception as exc:
                self.emit("update_error", updates.describe_error(exc))
        threading.Thread(target=task, daemon=True, name="DX updates").start()

    def _release_page(self):
        webbrowser.open(self.update_release.page if self.update_release else "https://github.com/Liberty-Chris/DX_Talker/releases")

    def _download_update(self):
        if self.update_busy:
            raise ValueError("Wait for the current update operation")
        if not self.update_release:
            raise ValueError("Check for an available update first")
        if sys.platform != "win32" and not sys.platform.startswith("linux"):
            raise ValueError("Use the release page for this operating system.")
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
        if not self.update_download:
            raise ValueError("Download and verify an update first")
        if not getattr(sys, "frozen", False):
            raise ValueError("Install updates from the packaged app. Source checkouts use Git.")
        path, checksum = self.update_download
        if not updates.verify_download(path, checksum):
            self.update_download = None
            raise ValueError("The downloaded installer changed. Download it again.")
        self.engine.stop("Stopping output for update")
        self._disconnect()
        self._wait_install(path, checksum, time.monotonic() + 30)

    def _wait_install(self, path, checksum, deadline):
        if self.engine.busy:
            if time.monotonic() > deadline:
                self._show_notice("Output has not stopped. Verify the radio and try installing again after Idle.")
                return
            self.root.after(100, lambda: self._wait_install(path, checksum, deadline))
            return
        try:
            if not updates.verify_download(path, checksum):
                raise ValueError("Installer verification failed")
            if sys.platform.startswith('linux'):
                from .linux_desktop import install_update
                install_update(path)
            else:
                subprocess.Popen([str(path)], shell=False)
        except Exception:
            self._show_notice("Could not open the verified installer. Download it again or use the release page.")
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
        ttk.Label(frame, text=f"DX Talker {__version__}  |  Beta  |  All rights reserved\nSettings: {settings_path()}", wraplength=900).grid(row=2, column=0, sticky="w", pady=10)

    def _show_help(self):
        from .help_ui import render
        render(self)

    def _read_settings(self):
        values = {}
        for f in fields(Settings):
            default = getattr(Settings(), f.name)
            value = self.variables[f.name].get()
            try:
                values[f.name] = type(default)(value) if type(default) is not str else value.strip()
            except (ValueError, tk.TclError):
                raise ValueError(f"Enter a valid number for {f.name.replace('_', ' ')}") from None
        pending=Settings(**values)
        return self.filter_editor.current(pending) if hasattr(self,'filter_editor') else pending.validate()

    def _apply(self):
        self._flush_preferences()
        updated = read_group(self.settings, self.variables, RADIO_FIELDS)
        def apply_radio():
            current = replace(self.settings, **{k: getattr(updated, k) for k in RADIO_FIELDS})
            save_settings(current)
            self.engine.configure(current)
            self.settings = current
            save_radio_draft(self.variables, current)
            self.save_status.set('Radio changes applied. RF remains disabled.')
            self._radio_dirty_state()
        self._when_idle(apply_radio, stop=True)

    def _connect(self):
        updated = read_group(self.settings, self.variables, SOURCE_FIELDS)
        updated.validate_connection()
        secret = self.secret.get()
        if len(secret) > 512 or any(ord(c) < 32 or ord(c) > 126 for c in secret):
            raise ValueError('Use a single line ASCII password or token of at most 512 characters')
        keep_listening = self.engine.local_enabled
        keep_muted = self.engine.local_muted
        def connected():
            self.pending_source=False
            current = replace(self.settings, **{k: getattr(updated, k) for k in SOURCE_FIELDS})
            save_settings(current)
            self.settings = current
            with self.engine.lock:
                self.engine.settings = replace(self.engine.settings, **{k: getattr(current, k) for k in SOURCE_FIELDS})
            self._start_source(secret, keep_listening, keep_muted)
        self._disconnect()
        self.pending_source=True
        self._when_idle(connected)

    def _start_source(self, secret, keep_listening=False, keep_muted=False):
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
                self.transition_serial += 1
                self.engine.stop("Source lost. RF disabled.")
            self.emit("source_event", (generation, kind, value))

        self.active_secret=secret
        self.source = SourceClient(self.settings, source_event, secret)
        self.connection_phase = "connecting"
        if keep_listening:
            self.engine.listen_locally(muted=keep_muted)
        self._render_connections()
        self.source.start()

    def _disconnect(self):
        self.pending_source=False
        self.transition_serial += 1
        if self.source:
            self._history_record("disconnect", profile=self.connected_profile)
        self.source_generation += 1
        if self.source:
            self.source.stop()
            self.source = None
        self.source_ready = False
        self.connection_phase = "disconnected"
        self._render_connections()
        self.source_status.set("Source: disconnected")
        self.engine.stop("RF disabled. Source disconnected.")

    def _send(self):
        if not self.source:
            raise ValueError("Connect to a cluster first")
        self.source.send(self.command.get())
        self.command.set("")
        self.emit("journal", "Manual cluster response sent. Contents are not logged.")

    def _sample_preview(self):
        from .spot_status_ui import sample_preview
        return sample_preview(self)

    def _samples(self):
        now = datetime.now(UTC)
        for frequency, call, mode in (("14025.0", "WB4IUY", "CW"), ("7074.0", "KT4BN", "FT8"), ("50125.0", "KF4DBX", "SSB")):
            spot = parse_line(f"DX de N0CALL: {frequency} {call} {mode} Demo {now:%H%M}Z", "sample", now)
            self._add_spot(spot)
        self.emit("journal", "Three sample spots loaded. Samples can be previewed locally and never enter the RF queue.")

    def _make_status_images(self):
        from .spot_status_ui import images
        return images(self.root)

    def _status_click(self, event):
        if self.tree.identify_column(event.x)=='#0':
            row=self.tree.identify_row(event.y)
            if row:self._show_spot_status(row)

    def _show_spot_status(self, row=None):
        selected=self.tree.selection()
        row=row or (selected[0] if selected else None)
        if row not in self.spots:return
        from .spot_status_ui import details
        state,reason=self.spot_states.get(row,('sample','Sample for manual preview only'))
        return details(self,self.spots[row],state,reason)

    def _show_rejected_spots(self):
        from .spot_status_ui import rejected
        return rejected(self)

    def _receive_spot(self, spot):
        self.spot_serial+=1
        token='spot_'+str(self.source_generation)+'_'+str(self.spot_serial)
        reason=self.engine.admit(spot,token)
        if reason:
            self.rejected_spots.append((spot,reason))
            self.rejected_spots=self.rejected_spots[-self.settings.display_limit:]
            self.rejected_button.configure(text='Spot details ('+str(len(self.rejected_spots))+' excluded)')
            return reason
        self._add_spot(spot, token)
        return ''

    def _spot_status(self, receipt):
        row=receipt['token']
        if row not in self.spots:return
        self.spot_states[row]=(receipt['state'],receipt['reason'])
        image=self.status_images.get(receipt['state'],self.status_images['queued'])
        self.tree.item(row,image=image)

    def _add_spot(self, spot, token=None):
        self._spot_view_revision += 1
        from .filtering import mode_of
        mode=mode_of(spot.comment,spot.mode,spot.frequency_khz)
        options=dict(image=self.status_images['queued'])
        if token:options['iid']=token
        item = self.tree.insert("", 0, values=(spot.timestamp.strftime("%H:%MZ"), spot.dx_call,
                                                spot.frequency_text(self.settings.frequency_unit), spot.spotter, "" if mode=="Unknown" else mode, spot.source),
                                tags=("alternate",) if len(self.spots) % 2 else (), **options)
        self.spots[item] = spot
        self.spot_states[item]=('queued','Accepted into the announcement queue') if token else ('sample','Sample or manual preview. Not automatically queued')
        from .filtering import rejection
        self.spot_reasons[item]=rejection(spot,self.settings)
        if self.spot_reasons[item]:self.tree.detach(item)
        self._trim_spots()

    def _preview_spot(self):
        selected = self.tree.selection()
        if not selected:
            raise ValueError('Select a live spot or open Sample preview.')
        self._start_preview('spot', self.spots[selected[0]])

    def _preview(self, kind):
        self._start_preview(kind)

    def _confirm_preview(self):
        if self.settings.preview_device and self.settings.preview_device == self.settings.radio_device:
            self._show_notice('Local audio uses the radio device and may key VOX. Change Local listening in Audio / PTT to use speakers.')
        return True

    def _enable(self):
        local,muted=self.engine.local_enabled,self.engine.local_muted
        if self.engine.enabled:
            if local:
                self._when_idle(lambda:self.engine.listen_locally(muted=muted),stop=True)
            else:
                self._stop()
        else:
            self.engine.settings.validate_rf()
            if local and not muted:self.engine._validate_monitor()
            self._when_idle(lambda:self.engine.enable(local=local,muted=muted), stop=True)
        self._render_connections()

    def _stop(self):
        self.pending_source=False
        self.transition_serial += 1
        self.engine.stop()
        self._render_connections()

    def _browse_wav(self):
        filename = filedialog.askopenfilename(title="Choose voice ID", filetypes=[("WAV audio", "*.wav")])
        if filename:
            self.variables["voice_wav"].set(filename)

    def _refresh_devices(self):
        try:
            devices = AudioOutput.devices()
            for name in ("preview_device", "radio_device"):
                self.combos[name].configure(values=devices)
            from .receiver import ReceiveMonitor
            self.combos["receive_device"].configure(values=ReceiveMonitor.devices())
            self.combos["serial_port"].configure(values=serial_ports())
            self.emit("journal", f"Found {len(devices)} audio output names")
        except Exception as exc:
            self.emit("journal", f"Device discovery unavailable ({type(exc).__name__}). Check the installed audio and serial dependencies.")

    def _load_voices(self):
        def task():
            try:
                self.emit("voices", (EspeakSpeech() if sys.platform.startswith("linux") else WindowsSpeech()).voices(self.background_cancel))
            except Exception:
                self.emit("journal", "System voices could not be enumerated. Check the installed speech provider.")
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
        self.diagnostics.heartbeat()
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
                    if kind == "source_lost":
                        self.diagnostics.record("source_failure", code=str(value).split(". Retrying")[0])
                    if kind == 'spot_sent':
                        if hasattr(self,'spot_status'):self.spot_status.set(value)
                        self._journal(value)
                        continue
                    if kind == "raw":
                        self._append_raw(value)
                        continue
                    if kind == "spot":
                        self._history_spot(value)
                        self._receive_spot(value)
                        continue
                    if kind == "source_ready":
                        self.source_ready = True
                        self.connection_phase = "connected"
                    elif kind == "source_connected":
                        self.connection_phase = "connected"
                    elif kind == "source_lost":
                        self.source_ready = False
                        self.connection_phase = "retrying"
                    self.source_status.set("Source: " + value)
                elif kind == "diagnostic":
                    self.diagnostics.record('output_failure', **value)
                    continue
                elif kind == 'performance':
                    self.diagnostics.record('speech_timing',**value)
                    continue
                elif kind == 'audio_recovery':
                    self.diagnostics.record('audio_recovered', **value)
                    continue
                elif kind == 'power_event':
                    self.diagnostics.record('desktop_power', **value)
                    continue
                elif kind == 'speech_voice':
                    self.resolved_voice.set('Speaking voice: '+value)
                    continue
                elif kind == 'spot_status':
                    self._spot_status(value)
                    continue
                elif kind == "announcement":
                    self._history_record("announcement", profile=self.connected_profile, **value)
                    continue
                elif kind == "output":
                    self.output_status.set(value)
                elif kind == "activity":
                    self.diagnostics.record('activity', state=value)
                    self.activity.set(value)
                elif kind == 'shared_voices':
                    self.shared_voices_loading=False
                    self.eleven_voices=value
                    self.combos['eleven_voice'].configure(values=['']+list(value))
                    selected=self.variables['eleven_voice'].get()
                    self.eleven_display.set(next((label for label,identity in value.items() if identity==selected),''))
                    self.eleven_status.set('Shared voices ready. Choose a voice. The selection saves automatically; preview when ready.')
                    continue
                elif kind == 'shared_voices_error':
                    self.shared_voices_loading=False
                    self.eleven_status.set(value)
                    continue
                elif kind == "voices":
                    self.combos["voice"].configure(values=["System default"] + value)
                    continue
                elif kind == "update_result":
                    self.update_busy = False
                    self.update_release = value.release
                    self.update_download = None
                    self.update_status.set(value.status)
                    value = value.release
                    self.update_banner.set("Update available: " + value.version + ". Open History / Updates." if value else "")
                    self.release_notes.configure(state="normal")
                    self.release_notes.delete("1.0", "end")
                    if value:
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
                    self._show_notice("Output stopped. " + value)
                self._journal(str(value))
        self._render_connections()
        self._receive_meter()
        count,age,expired=self.engine.queue_status()
        self.render_cache.set(self.queue_summary,f'{count} waiting announcements. Oldest {age}s.')
        if self.render_cache.changed('filter_summary', (self.settings,self._spot_view_revision)):
            from .filtering import summary
            self.render_cache.set(self.filter_summary,summary(self.settings)+f" · {self._visible_spots()} live spots")
        self._refresh_operating_ui(count, age)
        self.root.after(75, self._poll)

    def _journal(self, text):
        # Fixed application categories only; freeform journal text is not diagnostic data.
        if text.startswith(('Source ', 'Cluster ', 'Feed ')):
            self.diagnostics.record('source_status', code=('retrying' if 'Retrying' in text else 'state_change'))
        self.log.configure(state="normal")
        self.log.insert("end", datetime.now().strftime("%H:%M:%S ") + text + "\n")
        self.log_lines += 1
        if self.log_lines > 200:
            self.log.delete("1.0", "2.0")
            self.log_lines = 200
        self.log.see("end")
        self.log.configure(state="disabled")

    def close(self):
        if hasattr(self,'filter_editor'):self.filter_editor.flush()
        self._flush_preferences()
        self._save_radio_draft()
        self._persist_profile_drafts()
        self.transition_serial += 1
        if getattr(self,'undo_finalize',None):self.undo_finalize()
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
                self._show_notice("Output is still stopping. Verify the radio is unkeyed. The application will remain open while cleanup finishes.")
            self.root.after(50, lambda: self._wait_close(count + 1))
        else:
            self.diagnostics.close()
            threading.excepthook = self._previous_thread_hook
            self.root.destroy()


def main():
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DXTalker.Desktop")
    app = None
    try:
        root = tk.Tk(className="DXTalker")
        app = Application(root)
        app.diagnostics.enable_native_faults()
        root.mainloop()
    except Exception as exc:
        try:
            diagnostic = app.diagnostics if app else Diagnostics()
            diagnostic.exception('unhandled_application_exception', type(exc), exc.__traceback__)
            if app: app.engine.shutdown()
            diagnostic.close(clean=False)
        except Exception:
            pass
        raise
