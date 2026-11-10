"""Automatically saved listening filters. Cluster credentials and radio settings stay separate."""
from types import SimpleNamespace
from dataclasses import replace
import json
import tkinter as tk
from tkinter import ttk, simpledialog
from .models import Settings
from .listening import FIELDS, snapshot, validate_presets
from .filtering import BANDS, MODES, ACTIVITIES, summary, mode_summary
from .privileges import CLASSES, REGIONS


def build_filters(app,parent):
    window=app.root
    from .appearance import PALETTES
    frame=ttk.Frame(parent)
    staged={k:(tk.BooleanVar(value=getattr(app.settings,k)) if type(getattr(app.settings,k)) is bool else tk.StringVar(value=str(getattr(app.settings,k)))) for k in FIELDS}
    dirty=set();resetting=[False];preset_dirty=[False]
    presets=validate_presets(app.settings.listening_presets)
    pending={}
    def current(base=None):
        defaults=Settings();base=base or app.settings
        changes={k:type(getattr(defaults,k))(staged[k].get()) for k in dirty}
        if preset_dirty[0]:changes['listening_presets']=json.dumps(presets,separators=(',',':'))
        return replace(base,**changes).validate()
    note=tk.StringVar();status=tk.StringVar()
    def describe(*args):
        try:note.set(summary(current()))
        except ValueError:note.set('Complete the selected options below.')
    ttk.Label(frame,text='What do you want to hear?',font=('Segoe UI',16,'bold')).pack(anchor='w')
    ttk.Label(frame,textvariable=note,wraplength=650).pack(anchor='w',pady=8)
    saved=ttk.LabelFrame(frame,text='Listening presets',padding=10);saved.pack(fill='x',pady=6)
    name=tk.StringVar();picker=ttk.Combobox(saved,textvariable=name,values=list(presets),width=24);picker.pack(side='left',padx=(0,6))
    def load():
        values=presets.get(name.get(),{})
        if values:app._apply_listening(replace(app.settings,**values))
        describe()
    def save():
        label=name.get().strip() or simpledialog.askstring('Save listening preset','Preset name',parent=window)
        if not label:return
        presets[label]=snapshot(current());validate_presets(json.dumps(presets));preset_dirty[0]=True
        app._apply_listening(current());picker.configure(values=list(presets));name.set(label);status.set('Preset saved.')
    def remove():
        presets.pop(name.get(),None);preset_dirty[0]=True;app._apply_listening(current());picker.configure(values=list(presets));name.set('');status.set('Preset removed.')
    for label,action in (('Load',load),('Save',save),('Remove',remove)):ttk.Button(saved,text=label,command=app.guard(action)).pack(side='left',padx=3)
    filters=ttk.LabelFrame(frame,text='Choose your interests',padding=12);filters.pack(fill='x',pady=6)
    def choose_modes():
        dialog=tk.Toplevel(window);dialog.title('Modes');dialog.transient(window)
        dialog.configure(background=PALETTES[app.theme.get()]['bg'])
        stored=staged['filter_modes'].get()
        selected=set(stored.split(',')) if stored else set(MODES)-{'Unknown'}
        flags={value:tk.BooleanVar(value=value in selected) for value in MODES}
        def use():
            staged['filter_modes'].set(','.join(value for value in MODES if flags[value].get()) or 'None')
        def select(values):
            for value,flag in flags.items():flag.set(value in values)
            use()
        ttk.Button(dialog,text='All modes, including unknown',command=lambda:select(MODES)).grid(row=0,column=0,columnspan=3,padx=12,pady=8,sticky='ew')
        ttk.Button(dialog,text='Known modes only',command=lambda:select(set(MODES)-{'Unknown'})).grid(row=1,column=0,columnspan=2,padx=12,pady=4,sticky='ew')
        ttk.Button(dialog,text='None',command=lambda:select(set())).grid(row=1,column=2,padx=12,pady=4)
        for i,(value,flag) in enumerate(flags.items()):
            ttk.Checkbutton(dialog,text='Include unknown' if value=='Unknown' else value,variable=flag,command=use).grid(row=2+i//3,column=i%3,padx=12,pady=6,sticky='w')
        ttk.Label(dialog,text='Saves immediately. Band, activity, location and license filters still apply.',wraplength=310).grid(row=5,column=0,columnspan=3,padx=12,pady=8)
        ttk.Button(dialog,text='Close',command=dialog.destroy).grid(row=6,column=0,columnspan=3,pady=12)

    def choose(key,title,values):
        if key=='filter_modes':return choose_modes()
        dialog=tk.Toplevel(window);dialog.title(title);dialog.transient(window);dialog.configure(background=PALETTES[app.theme.get()]['bg'])
        all_values=tk.BooleanVar(value=not staged[key].get());selected=set(staged[key].get().split(','))
        ttk.Checkbutton(dialog,text='All known modes' if key=='filter_modes' else 'All '+title.lower(),variable=all_values,command=lambda:use()).grid(row=0,column=0,columnspan=3,sticky='w',padx=12,pady=10)
        flags={value:tk.BooleanVar(value=value in selected) for value in values}
        for i,(value,flag) in enumerate(flags.items()):
            label='No activity tag' if value=='General' else 'Include unknown' if value=='Unknown' else value
            ttk.Checkbutton(dialog,text=label,variable=flag,command=lambda v=value:toggle(v)).grid(row=1+i//3,column=i%3,padx=12,pady=6,sticky='w')
        message=tk.StringVar();ttk.Label(dialog,textvariable=message).grid(row=2+(len(values)+2)//3,column=0,columnspan=3)
        def use():
            selected=[v for v,flag in flags.items() if flag.get()]
            if not all_values.get() and not selected:selected=['None']
            if all_values.get():
                selected=list(MODES) if key=='filter_modes' and flags['Unknown'].get() else []
            staged[key].set(','.join(selected))
        def toggle(value):
            if value!='Unknown':all_values.set(False)
            use()
        ttk.Button(dialog,text='Close',command=dialog.destroy).grid(row=3+(len(values)+2)//3,column=0,columnspan=3,pady=12)
        dialog.bind('<Escape>',lambda e:dialog.destroy());dialog.grab_set()
    for key,title,values in (('filter_bands','Bands',(*BANDS,'Other')),('filter_modes','Modes',MODES),('filter_activities','Activities',ACTIVITIES)):
        row=ttk.Frame(filters);row.pack(fill='x',pady=3)
        ttk.Button(row,text='Choose '+title.lower(),command=lambda k=key,t=title,v=values:choose(k,t,v)).pack(side='left')
        label=tk.StringVar()
        def update_label(*args,k=key,t=title,var=label):var.set(mode_summary(staged[k].get()) if k=='filter_modes' else staged[k].get().replace('General','No activity tag') or 'All '+t.lower())
        staged[key].trace_add('write',update_label);update_label()
        ttk.Label(row,textvariable=label,wraplength=430).pack(side='left',padx=12)
    ttk.Label(filters,text='The same filters select displayed and announced spots. Mode comes from a reported tag or a single mode band segment. Include unknown admits uncertain modes within your other selections.',wraplength=620).pack(anchor='w',pady=8)
    ttk.Checkbutton(filters,text='Use POTA / FOTA / SOTA wording during mixed listening',variable=staged['activity_announcements']).pack(anchor='w',pady=4)
    ttk.Label(filters,text='Activity-only selections use this wording automatically: activity, mode, frequency, callsign. Unknown modes are omitted. All listening filters still apply.',wraplength=620).pack(anchor='w',pady=4)
    license=ttk.LabelFrame(frame,text='My operating privileges (optional)',padding=12);license.pack(fill='x',pady=6)
    for row,(key,title,values) in enumerate((('license_class','FCC license class',CLASSES),('license_region','Operating region',REGIONS))):
        ttk.Label(license,text=title).grid(row=row,column=0,sticky='w',padx=(0,12),pady=3)
        ttk.Combobox(license,textvariable=staged[key],values=values,state='readonly',width=22).grid(row=row,column=1,sticky='w')
    ttk.Checkbutton(license,text='Include spots whose license eligibility cannot be verified',variable=staged['license_unknown']).grid(row=2,column=0,columnspan=2,sticky='w',pady=6)
    def advanced():geo.pack_forget() if geo.winfo_manager() else geo.pack(fill='x',pady=6,before=footer)
    ttk.Button(frame,text='Location and advanced filters',command=advanced).pack(anchor='w',pady=6)
    geo=ttk.LabelFrame(frame,text='Location and advanced filters',padding=12)
    specs=(('filter_spotter_countries','Reporting station countries','Country codes, for example US,CA'),('filter_spotter_continents','Reporting station continents','AF, AN, AS, EU, NA, OC, SA'),('filter_spotter_regions','Reporting station regions','For example NC,SC,GA'),('filter_dx_countries','DX station countries','Country codes, for example US,JP'),('filter_dx_continents','DX station continents','AF, AN, AS, EU, NA, OC, SA'),('location_overrides','Known station locations','CALL=US,NA,NC;CALL=CA,NA,ON'),('min_khz','Minimum frequency (kHz)',''),('max_khz','Maximum frequency (kHz)',''))
    for row,(key,title,hint) in enumerate(specs):
        ttk.Label(geo,text=title).grid(row=row,column=0,sticky='w',pady=4)
        ttk.Entry(geo,textvariable=staged[key],width=30).grid(row=row,column=1,sticky='w',padx=8)
        if hint:ttk.Label(geo,text=hint,wraplength=200).grid(row=row,column=2,sticky='w')
    ttk.Checkbutton(geo,text='Include spots with unknown location',variable=staged['geography_unknown']).grid(row=8,column=0,columnspan=3,sticky='w',pady=6)
    ttk.Label(geo,text='Location comes from feed metadata or your known station list. A callsign alone does not establish current location. Leave a location field empty to accept all.',wraplength=620).grid(row=9,column=0,columnspan=3,sticky='w')
    def commit(key):
        pending.pop(key,None)
        if key not in dirty:return
        keys=({'min_khz','max_khz'} & dirty) if key in ('min_khz','max_khz') else {key}
        try:
            changes={k:type(getattr(Settings(),k))(staged[k].get()) for k in keys}
            updated=replace(app.settings,**changes).validate()
            if updated!=app.settings:app._apply_listening(updated,sync_editor=False)
            dirty.difference_update(keys)
            status.set('Filters saved automatically.' if not dirty else 'Complete the unfinished fields. Other choices are saved.')
        except (ValueError,tk.TclError,OSError) as exc:status.set('Not saved: '+str(exc))
        describe()
    immediate={'activity_announcements','filter_bands','filter_modes','filter_activities','license_class','license_region','license_unknown','geography_unknown','frequency_unit'}
    def changed(key,*args):
        if resetting[0]:return
        dirty.add(key)
        if key in pending:window.after_cancel(pending.pop(key))
        if key in immediate:commit(key)
        else:
            status.set('Saving when you finish typing…')
            pending[key]=window.after(450,lambda:commit(key))
    for key,var in staged.items():var.trace_add('write',lambda *args,k=key:changed(k))
    describe()
    footer=ttk.Frame(frame,padding=(0,12));footer.pack(fill='x')
    status.set('Filter changes save automatically.')
    ttk.Label(footer,textvariable=status,wraplength=650).pack(anchor='w')
    def reset():
        resetting[0]=True
        try:
            for callback in pending.values():window.after_cancel(callback)
            pending.clear();dirty.clear();preset_dirty[0]=False
            for key,var in staged.items():var.set(getattr(app.settings,key))
            presets.clear();presets.update(validate_presets(app.settings.listening_presets))
            picker.configure(values=list(presets));status.set('Filter changes save automatically.');describe()
        finally:resetting[0]=False
    def flush():
        for key,callback in list(pending.items()):
            window.after_cancel(callback);commit(key)
    return SimpleNamespace(frame=frame,current=current,reset=reset,flush=flush,variables=staged,focus=picker.focus_set)
