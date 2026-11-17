"""Named voice IDs and calendar editor. Changes use the existing radio draft."""
from dataclasses import replace
from datetime import datetime, timedelta
import json
import tkinter as tk
from tkinter import ttk, filedialog

from .id_schedule import KINDS, WEEKDAYS, entries, new_entry, next_occurrence


def build_scheduled_ids(app, parent, row):
    panel = ttk.LabelFrame(parent, text='Scheduled voice IDs', padding=12)
    panel.grid(row=row, column=0, sticky='ew', pady=12)
    ttk.Label(panel, text='Up to 20 additional voice IDs. Times use this computer’s local clock.\nRequired station identification stays active and takes priority.', wraplength=650).pack(anchor='w')
    tree = ttk.Treeview(panel, columns=('schedule', 'next'), show='tree headings', height=6, selectmode='browse')
    tree.heading('#0', text='Voice ID'); tree.column('#0', width=180)
    tree.heading('schedule', text='Schedule'); tree.column('schedule', width=150)
    tree.heading('next', text='Next planned time'); tree.column('next', width=175)
    tree.pack(fill='x', pady=8)
    note = tk.StringVar()
    ttk.Label(panel, textvariable=note, wraplength=650).pack(anchor='w')
    controls = ttk.Frame(panel); controls.pack(fill='x', pady=6)

    def refresh(*args):
        selected = tree.selection()
        tree.delete(*tree.get_children())
        values = entries(app.variables['voice_ids'].get())
        for item in values:
            due = next_occurrence(item, datetime.now())
            if item['kind'] == 'Interval' and app.engine.enabled and app.variables['voice_ids'].get() == app.settings.voice_ids:
                with app.engine.lock:
                    deadline = app.engine.schedule_book.intervals.get(item['id'])
                if deadline is not None: due = datetime.now() + timedelta(seconds=max(0, deadline - app.engine.clock()))
            tree.insert('', 'end', iid=item['id'], text=item['name'], values=(item['kind'] if item['enabled'] else 'Disabled', due.strftime('%Y-%m-%d %H:%M') if due else 'None'))
        if selected and tree.exists(selected[0]): tree.selection_set(selected)
        note.set(f'{len(values)} of 20 voice IDs. Apply radio changes to activate edits. Preview never keys PTT.')
        add.configure(state='normal' if len(values) < 20 else 'disabled')

    def selected():
        return next((i for i in entries(app.variables['voice_ids'].get()) if i['id'] in tree.selection()), None)

    def remove():
        item = selected()
        if item:
            app.variables['voice_ids'].set(json.dumps([i for i in entries(app.variables['voice_ids'].get()) if i['id'] != item['id']], separators=(',', ':')))

    def preview():
        item = selected()
        if not item: raise ValueError('Select a voice ID to preview')
        settings = replace(app._preview_settings('voice'), voice_mode=item['source'], voice_text=item['text'], voice_wav=item['wav'])
        app._start_preview('voice', settings=settings)

    def edit(adding=False):
        collection = entries(app.variables['voice_ids'].get())
        if adding and len(collection) >= 20: raise ValueError('Remove an ID before adding another')
        item = new_entry() if adding else selected()
        if item is None: raise ValueError('Select a voice ID to edit')
        window = tk.Toplevel(app.root); window.title('Voice ID and schedule'); window.transient(app.root)
        window.columnconfigure(1, weight=1)
        values = {key: tk.StringVar(window, value=str(item[key])) for key in ('name', 'source', 'text', 'wav', 'kind', 'minutes', 'ordinal', 'day', 'date', 'start_date', 'end_date', 'window_start', 'window_end', 'grace_minutes')}
        values['times'] = tk.StringVar(window, value=', '.join(item['times']))
        enabled = tk.BooleanVar(window, value=item['enabled'])
        days = [tk.BooleanVar(window, value=n in item['weekdays']) for n in range(7)]
        widgets = {}

        def field(n, key, title, options=None):
            label = ttk.Label(window, text=title)
            label.grid(row=n, column=0, sticky='w', padx=12, pady=4)
            widget = ttk.Combobox(window, textvariable=values[key], values=options, state='readonly', width=28) if options else ttk.Entry(window, textvariable=values[key], width=46)
            widget.grid(row=n, column=1, sticky='ew', padx=12, pady=4)
            widgets[key] = (label, widget)
        field(0, 'name', 'Name')
        ttk.Checkbutton(window, text='Enabled', variable=enabled).grid(row=0, column=2, padx=12)
        field(1, 'source', 'Voice source', ('Speech', 'WAV'))
        field(2, 'text', 'Text to speak')
        field(3, 'wav', 'WAV recording')
        browse = ttk.Button(window, text='Browse', command=lambda: values['wav'].set(filedialog.askopenfilename(parent=window, filetypes=[('WAV audio', '*.wav')]) or values['wav'].get()))
        browse.grid(row=3, column=2, padx=12)
        field(4, 'kind', 'Schedule', KINDS)
        field(5, 'minutes', 'Every N minutes (1 to 10080)')
        field(6, 'times', 'Times, separated by commas')
        weekdays = ttk.Frame(window); weekdays.grid(row=7, column=0, columnspan=3, padx=12, pady=6)
        for n, day in enumerate(WEEKDAYS): ttk.Checkbutton(weekdays, text=day[:3], variable=days[n]).pack(side='left', padx=4)
        field(8, 'ordinal', 'Occurrence (1 to 5, or -1 for last)', ('1', '2', '3', '4', '5', '-1'))
        field(9, 'day', 'Day of month (1 to 31)')
        field(10, 'date', 'One time date (YYYY-MM-DD)')
        field(11, 'start_date', 'Starting date (optional)')
        field(12, 'end_date', 'Ending date (optional)')
        field(13, 'window_start', 'Daily window starts (HH:MM)')
        field(14, 'window_end', 'Daily window ends (HH:MM)')
        field(15, 'grace_minutes', 'Wait for a clear channel (minutes)')
        feedback = tk.StringVar()
        ttk.Label(window, textvariable=feedback, wraplength=570).grid(row=16, column=0, columnspan=3, padx=12, pady=6, sticky='w')

        def visibility(*args):
            kind = values['kind'].get()
            for key, show in (('text', values['source'].get() == 'Speech'), ('wav', values['source'].get() == 'WAV'), ('minutes', kind == 'Interval'), ('times', kind != 'Interval'), ('ordinal', kind == 'Monthly weekday'), ('day', kind == 'Monthly date'), ('date', kind == 'Once')):
                for widget in widgets[key]: widget.grid() if show else widget.grid_remove()
            browse.grid() if values['source'].get() == 'WAV' else browse.grid_remove()
            weekdays.grid() if kind in ('Weekly', 'Monthly weekday') else weekdays.grid_remove()
        for key in ('source', 'kind'): values[key].trace_add('write', visibility)
        visibility()

        def save():
            try:
                updated = dict(item, enabled=enabled.get())
                for key, variable in values.items():
                    raw = variable.get().strip()
                    updated[key] = int(raw) if key in ('minutes', 'ordinal', 'day', 'grace_minutes') else [t.strip() for t in raw.split(',')] if key == 'times' else raw
                updated['weekdays'] = [n for n, flag in enumerate(days) if flag.get()]
                if updated['kind'] not in ('Weekly', 'Monthly weekday') and not updated['weekdays']: updated['weekdays'] = [1]
                updated_collection = [updated if i['id'] == item['id'] else i for i in collection]
                if adding: updated_collection.append(updated)
                text = json.dumps(updated_collection, separators=(',', ':'))
                entries(text)
                if updated['enabled'] and updated['source'] == 'WAV':
                    from .audio import wav_clip
                    clip = wav_clip(updated['wav'])
                    if clip.duration > app.settings.max_tx_seconds: raise ValueError('Recording exceeds maximum transmit duration')
                app.variables['voice_ids'].set(text)
                window.destroy()
            except (ValueError, OSError) as exc: feedback.set(str(exc))
        actions = ttk.Frame(window); actions.grid(row=17, column=0, columnspan=3, pady=10)
        ttk.Button(actions, text='Save voice ID', command=save).pack(side='left', padx=6)
        ttk.Button(actions, text='Cancel', command=window.destroy).pack(side='left', padx=6)
        window.bind('<Escape>', lambda event: window.destroy())
        window.grab_set()

    add = ttk.Button(controls, text='+ Add voice ID', command=app.guard(lambda: edit(True))); add.pack(side='left', padx=3)
    for title, action in (('Edit', edit), ('Remove', remove), ('Preview locally', preview)):
        ttk.Button(controls, text=title, command=app.guard(action)).pack(side='left', padx=3)
    tree.bind('<Double-1>', lambda event: app.guard(edit)())
    def changed(*args):
        refresh()
        app._setting_changed('voice_ids')
    app.variables['voice_ids'].trace_add('write', changed)
    refresh()
    def update_times():
        if not app.closing:
            refresh()
            app.root.after(30000, update_times)
    app.root.after(30000, update_times)
