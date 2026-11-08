"""One staged listening editor. Cluster credentials and radio settings stay separate."""
from collections import Counter
from dataclasses import replace
import json
import tkinter as tk
from tkinter import ttk, simpledialog
from .models import Settings
from .listening import FIELDS, snapshot, validate_presets
from .filtering import BANDS, MODES, ACTIVITIES, summary
from .privileges import CLASSES, REGIONS


def open_filters(app):
    old=getattr(app,'filter_window',None)
    if old and old.winfo_exists():old.lift();return
    window=tk.Toplevel(app.root);app.filter_window=window
    window.title('What do you want to hear?');window.transient(app.root)
    window.geometry('740x650');window.minsize(540,400)
    from .appearance import PALETTES
    window.configure(background=PALETTES[app.theme.get()]['bg'])
    canvas=tk.Canvas(window,highlightthickness=0,background=PALETTES[app.theme.get()]['bg'])
    scroll=ttk.Scrollbar(window,orient='vertical',command=canvas.yview)
    canvas.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');canvas.pack(fill='both',expand=True)
    frame=ttk.Frame(canvas,padding=16);item=canvas.create_window(0,0,window=frame,anchor='nw')
    frame.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
    staged={k:(tk.BooleanVar(value=getattr(app.settings,k)) if type(getattr(app.settings,k)) is bool else tk.StringVar(value=str(getattr(app.settings,k)))) for k in FIELDS}
    presets=validate_presets(app.settings.listening_presets)
    def current():
        defaults=Settings()
        return replace(app.settings,**{k:type(getattr(defaults,k))(v.get()) for k,v in staged.items()},listening_presets=json.dumps(presets,separators=(',',':'))).validate()
    note=tk.StringVar();status=tk.StringVar()
    def describe(*args):
        try:note.set(summary(current()))
        except ValueError:note.set('Complete the selected options below.')
    ttk.Label(frame,text='What do you want to hear?',font=('Segoe UI',16,'bold')).pack(anchor='w')
    ttk.Label(frame,textvariable=note,wraplength=650).pack(anchor='w',pady=8)
    saved=ttk.LabelFrame(frame,text='Listening presets',padding=10);saved.pack(fill='x',pady=6)
    name=tk.StringVar();picker=ttk.Combobox(saved,textvariable=name,values=list(presets),width=24);picker.pack(side='left',padx=(0,6))
    def load():
        for k,v in presets.get(name.get(),{}).items():staged[k].set(v)
        describe()
    def save():
        label=name.get().strip() or simpledialog.askstring('Save listening preset','Preset name',parent=window)
        if not label:return
        presets[label]=snapshot(current());validate_presets(json.dumps(presets))
        picker.configure(values=list(presets));name.set(label);status.set('Preset staged. Apply to save it.')
    def remove():
        presets.pop(name.get(),None);picker.configure(values=list(presets));name.set('');status.set('Preset removal staged. Apply to save it.')
    for label,action in (('Load',load),('Save',save),('Remove',remove)):ttk.Button(saved,text=label,command=app.guard(action)).pack(side='left',padx=3)
    filters=ttk.LabelFrame(frame,text='Choose your interests',padding=12);filters.pack(fill='x',pady=6)
    def choose(key,title,values):
        dialog=tk.Toplevel(window);dialog.title(title);dialog.transient(window);dialog.configure(background=PALETTES[app.theme.get()]['bg'])
        all_values=tk.BooleanVar(value=not staged[key].get());selected=set(staged[key].get().split(','))
        ttk.Checkbutton(dialog,text='All '+title.lower(),variable=all_values).grid(row=0,column=0,columnspan=3,sticky='w',padx=12,pady=10)
        flags={value:tk.BooleanVar(value=value in selected) for value in values}
        for i,(value,flag) in enumerate(flags.items()):
            label='No activity tag' if value=='General' else 'Unknown / not supplied' if value=='Unknown' else value
            ttk.Checkbutton(dialog,text=label,variable=flag,command=lambda:all_values.set(False)).grid(row=1+i//3,column=i%3,padx=12,pady=6,sticky='w')
        message=tk.StringVar();ttk.Label(dialog,textvariable=message).grid(row=2+(len(values)+2)//3,column=0,columnspan=3)
        def use():
            selected=[v for v,flag in flags.items() if flag.get()]
            if not all_values.get() and not selected:message.set('Select at least one option or choose All.');return
            staged[key].set('' if all_values.get() else ','.join(selected));dialog.destroy()
        ttk.Button(dialog,text='Use selection',command=use).grid(row=3+(len(values)+2)//3,column=0,columnspan=3,pady=12)
        dialog.bind('<Escape>',lambda e:dialog.destroy());dialog.grab_set()
    for key,title,values in (('filter_bands','Bands',(*BANDS,'Other')),('filter_modes','Modes',MODES),('filter_activities','Activities',ACTIVITIES)):
        row=ttk.Frame(filters);row.pack(fill='x',pady=3)
        ttk.Button(row,text='Choose '+title.lower(),command=lambda k=key,t=title,v=values:choose(k,t,v)).pack(side='left')
        label=tk.StringVar()
        def update_label(*args,k=key,t=title,var=label):var.set(staged[k].get().replace('General','No activity tag') or 'All '+t.lower())
        staged[key].trace_add('write',update_label);update_label()
        ttk.Label(row,textvariable=label,wraplength=430).pack(side='left',padx=12)
    ttk.Label(filters,text='Selections combine: POTA + 20m + SSB. Activity and mode tags must be present in the spot.',wraplength=620).pack(anchor='w',pady=8)
    license=ttk.LabelFrame(frame,text='My operating privileges (optional)',padding=12);license.pack(fill='x',pady=6)
    for row,(key,title,values) in enumerate((('license_class','FCC license class',CLASSES),('license_region','Operating region',REGIONS))):
        ttk.Label(license,text=title).grid(row=row,column=0,sticky='w',padx=(0,12),pady=3)
        ttk.Combobox(license,textvariable=staged[key],values=values,state='readonly',width=22).grid(row=row,column=1,sticky='w')
    ttk.Checkbutton(license,text='Include spots whose license eligibility cannot be verified',variable=staged['license_unknown']).grid(row=2,column=0,columnspan=2,sticky='w',pady=6)
    def advanced():geo.pack_forget() if geo.winfo_manager() else geo.pack(fill='x',pady=6)
    ttk.Button(frame,text='Location and advanced filters',command=advanced).pack(anchor='w',pady=6)
    geo=ttk.LabelFrame(frame,text='Location and advanced filters',padding=12)
    specs=(('filter_spotter_countries','Reporting station countries','Country codes, for example US,CA'),('filter_spotter_continents','Reporting station continents','AF, AN, AS, EU, NA, OC, SA'),('filter_spotter_regions','Reporting station regions','For example NC,SC,GA'),('filter_dx_countries','DX station countries','Country codes, for example US,JP'),('filter_dx_continents','DX station continents','AF, AN, AS, EU, NA, OC, SA'),('location_overrides','Known station locations','CALL=US,NA,NC;CALL=CA,NA,ON'),('min_khz','Minimum frequency (kHz)',''),('max_khz','Maximum frequency (kHz)',''))
    for row,(key,title,hint) in enumerate(specs):
        ttk.Label(geo,text=title).grid(row=row,column=0,sticky='w',pady=4)
        ttk.Entry(geo,textvariable=staged[key],width=30).grid(row=row,column=1,sticky='w',padx=8)
        if hint:ttk.Label(geo,text=hint,wraplength=200).grid(row=row,column=2,sticky='w')
    ttk.Checkbutton(geo,text='Include spots with unknown location',variable=staged['geography_unknown']).grid(row=8,column=0,columnspan=3,sticky='w',pady=6)
    ttk.Label(geo,text='Location comes from feed metadata or your known station list. A callsign alone does not establish current location. Leave a location field empty to accept all.',wraplength=620).grid(row=9,column=0,columnspan=3,sticky='w')
    for var in staged.values():var.trace_add('write',describe)
    describe()
    footer=ttk.Frame(window,padding=12);footer.pack(side='bottom',fill='x',before=canvas)
    ttk.Label(footer,textvariable=status,wraplength=650).pack(anchor='w')
    def apply():
        try:app._apply_listening(current());window.destroy()
        except ValueError as exc:status.set(str(exc))
    ttk.Button(footer,text='Apply listening filters',command=apply,style='Accent.TButton').pack(side='right',padx=6)
    ttk.Button(footer,text='Cancel',command=window.destroy).pack(side='right')
    window.bind('<Escape>',lambda e:window.destroy())
