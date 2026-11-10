"""Desktop interactions: scoped edits, nonmodal feedback and cancellable transitions."""
from dataclasses import replace
import json
import time
import tkinter as tk
from tkinter import ttk

from .appearance import PALETTES
from .models import Settings, save_settings, settings_path
from .preferences import (RADIO_FIELDS, PREFERENCE_FIELDS, FORMAT_FIELDS,
                          read_group, save_radio_draft, load_radio_draft)
from .profiles import SOURCE_FIELDS


class Usability:
    def _build_usability(self):
        self.undo_action = None
        self.system_voice_choice=tk.StringVar(value=self.settings.voice or 'System default')
        self.combos['voice'].configure(textvariable=self.system_voice_choice)
        self.combos['voice'].bind('<<ComboboxSelected>>',lambda e:self.variables['voice'].set('' if self.system_voice_choice.get()=='System default' else self.system_voice_choice.get()))
        self.undo_button = ttk.Button(self.error_frame, text='Undo', command=self.guard(self._undo))
        self.routing_hint = tk.StringVar()
        ttk.Label(self.tabs['Audio and PTT'], textvariable=self.routing_hint, wraplength=650).grid(row=6, column=0, sticky='w', pady=8)
        self.receive_level = tk.Canvas(self.tabs['Audio and PTT'], width=300, height=24, highlightthickness=0)
        self.receive_fill = self.receive_level.create_rectangle(0,0,0,24,fill=PALETTES[self.theme.get()]['positive'],outline='')
        self.receive_mark = self.receive_level.create_line(0,0,0,24,fill=PALETTES[self.theme.get()]['ink'],width=3)
        self.receive_level.grid(row=7, column=0, sticky='w', pady=4)
        self.receive_threshold = tk.StringVar()
        ttk.Label(self.tabs['Audio and PTT'], textvariable=self.receive_threshold).grid(row=8,column=0,sticky='w')
        self.empty_spots = tk.StringVar()
        self.empty_label = ttk.Label(self.tree.master, textvariable=self.empty_spots, wraplength=580, anchor='center', justify='center')
        self.quick_volume = tk.DoubleVar(value=self.settings.local_volume_percent)
        volume = ttk.Frame(self.tabs['Live spots'])
        volume.grid(row=0, column=0, sticky='e')
        # Keep the existing unit and profile controls; volume lives in the queue row.
        volume.grid_forget()
        queue_row = self.catch_up_button.master
        self.volume_label = ttk.Label(queue_row, text='Local volume')
        self.volume_label.pack(side='left', padx=(12,4))
        ttk.Scale(queue_row, from_=0, to=100, length=100, variable=self.quick_volume,
                  command=lambda v: self.variables['local_volume_percent'].set(str(round(float(v))))).pack(side='left')
        self.nav_frame = ttk.Frame(self.root, padding=(18,0,18,5))
        self.nav_choice = tk.StringVar(value='Live spots')
        self.nav_picker = ttk.Combobox(self.nav_frame, state='readonly', textvariable=self.nav_choice,
                                      values=list(self.tabs), width=28)
        self.nav_picker.pack(side='left')
        self.nav_picker.bind('<<ComboboxSelected>>', lambda e: self._select_page(self.nav_choice.get()))
        self.notebook.bind('<<NotebookTabChanged>>', self._page_changed, add='+')
        self._normal_tab_layout = ttk.Style(self.root).layout('TNotebook.Tab')
        self.root.bind('<Configure>', self._fit_navigation, add='+')
        # Diagnostics stay available without dominating daily operation.
        self.help_search = tk.StringVar()
        search = ttk.Entry(self.tabs['Help and Info'], textvariable=self.help_search)
        search.grid(row=3,column=0,sticky='ew',pady=4)
        search.bind('<Return>', lambda e: self._search_help())
        ttk.Button(self.tabs['Help and Info'], text='Search help', command=self._search_help).grid(row=3,column=1,padx=4)
        for name, target, label in [('Announcements','Speech and access','Voice and speech settings'),
                                    ('Speech and access','Announcements','Announcement format')]:
            ttk.Button(self.tabs[name],text=label,command=lambda t=target:self._select_page(t)).grid(row=20,column=0,sticky='w',pady=8)
        self.wav_status = tk.StringVar()
        ttk.Label(self.tabs['Identification'], textvariable=self.wav_status, wraplength=640).grid(row=4,column=0,sticky='w')
        self.variables['voice_wav'].trace_add('write', lambda *args: self._validate_wav_choice())
        self.profile_edit_key='new'
        self._load_profile_drafts()
        self._radio_dirty_state()
        self._fit_navigation()

    def _page_id(self,name):
        frame=self.tabs[name]
        return frame if frame.master is self.notebook else frame.master.master

    def _select_page(self,name):
        self.notebook.select(self._page_id(name))

    def _page_changed(self, event=None):
        if hasattr(self, 'nav_choice'):
            self.nav_choice.set(next((name for name, tab in self.tabs.items() if str(self._page_id(name))==self.notebook.select()),'Live spots'))

    def _fit_navigation(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        if not hasattr(self,'nav_frame'):
            return
        geometry=(self.root.winfo_width(),self.settings.text_size,self.theme.get())
        if not self.render_cache.changed('navigation_geometry',geometry):
            return
        import tkinter.font as font
        f = font.Font(root=self.root, font=('Segoe UI',self.settings.text_size))
        needed = sum(f.measure(self.notebook.tab(tab,'text'))+30 for tab in self.notebook.tabs())
        narrow = needed > self.root.winfo_width()-40 or (self.settings.text_size>=14 and self.root.winfo_width()<1250)
        if getattr(self,'_nav_narrow',None)==narrow:
            return
        self._nav_narrow=narrow
        style=ttk.Style(self.root)
        style.layout('TNotebook.Tab', [] if narrow else self._normal_tab_layout)
        if narrow:
            self.nav_frame.pack(fill='x',before=self.notebook)
        else:
            self.nav_frame.pack_forget()

    def _queue_preference(self, key):
        if key in RADIO_FIELDS:
            self._radio_dirty_state()
            names=('radio_draft',)
        elif key in SOURCE_FIELDS:
            if hasattr(self,'profile_status'):
                self.profile_status.set('Connection edits are not active. Connect uses these details; Save profile keeps them for later.')
            return
        else:
            names=FORMAT_FIELDS if key=='format' or key in FORMAT_FIELDS else (key,)
            if not set(names) <= set(PREFERENCE_FIELDS):
                return
        token=','.join(names)
        previous=self.preference_jobs.pop(token,None)
        if previous:
            self.root.after_cancel(previous)
        self.save_status.set('Radio draft preserved on leaving. Apply radio changes when ready.' if key in RADIO_FIELDS else 'Saving when you finish editing…')
        self.preference_jobs[token]=self.root.after(450,lambda:self._save_preference(token,names))

    def _save_preference(self, token, names):
        self.preference_jobs.pop(token,None)
        if names==('radio_draft',):
            self._save_radio_draft()
            return
        try:
            # Display labels do not become voice identifiers.
            if 'voice' in names and self.variables['voice'].get()=='System default':
                old=self.initializing;self.initializing=True
                self.variables['voice'].set('')
                self.initializing=old
            updated=read_group(self.settings,self.variables,names)
            save_settings(updated)
            self.settings=updated
            self.engine.update_preferences(updated,names)
            self.preference_errors.pop(token,None)
            for key in names:self._mark_field(key,False)
            if 'frequency_unit' in names:
                self._refresh_spot_units()
                self._sync_listening_editor(reset_filters=False)
            if set(names)&{'logging_enabled','log_directory','log_max_mb','log_backups'}:
                self._configure_history()
            if 'display_limit' in names:
                self._trim_spots()
            if 'text_size' in names:
                self._style();self._paint_widgets();self._nav_narrow=None;self._fit_navigation();self._responsive_layout()
            if 'local_volume_percent' in names:
                self.quick_volume.set(updated.local_volume_percent)
            self.save_status.set('Saved.' if not self.preference_errors else next(iter(self.preference_errors.values())))
        except (ValueError,tk.TclError,OSError) as exc:
            label = names[0].replace('_',' ')
            message='Not saved: '+label+'. '+str(exc)
            self.preference_errors[token]=message
            for key in names:self._mark_field(key,True)
            self.save_status.set(message)

    def _flush_preferences(self, names=None):
        for token,callback in list(self.preference_jobs.items()):
            fields=tuple(token.split(','))
            if names is not None and not set(fields)&set(names):
                continue
            self.root.after_cancel(callback)
            self._save_preference(token,fields)

    def _radio_dirty_state(self):
        changed=any(str(self.variables[k].get())!=str(getattr(self.settings,k)) for k in RADIO_FIELDS)
        if hasattr(self,'save_button'):
            self.save_button.configure(state='normal' if changed else 'disabled')
        return changed

    def _save_radio_draft(self):
        try:
            dirty=save_radio_draft(self.variables,self.settings)
            if dirty:
                self.save_status.set('Radio draft saved. Apply radio changes to use it. RF state unchanged.')
        except OSError:
            self._show_notice('Radio draft could not be saved. Check settings folder permissions.')

    def _restore_radio_draft(self):
        for key,value in load_radio_draft().items():
            self.variables[key].set(value)
        if self._radio_dirty_state():
            self.save_status.set('Restored radio draft. Apply radio changes when ready.')

    def _when_idle(self, action, stop=False):
        """One action owns one transition; Stop/disconnect invalidates pending actions."""
        self.transition_serial+=1
        serial=self.transition_serial
        deadline=time.monotonic()+30
        if stop and (self.engine.enabled or self.engine.local_enabled or self.engine.busy):
            self.engine.stop('Switching output. Waiting for audio and PTT cleanup.')
        def finish():
            if self.closing or serial!=self.transition_serial:
                return
            if self.engine.busy:
                if time.monotonic()>deadline:
                    self.pending_source=False
                    self._show_notice('Output is still stopping. Check the radio and try again when Idle.')
                    return
                self.save_status.set('Waiting for output to stop…')
                self.root.after(50,finish)
                return
            self.guard(action)()
            self._render_connections()
        finish()

    def _preview_settings(self, kind):
        self._flush_preferences(PREFERENCE_FIELDS)
        names=FORMAT_FIELDS+('preview_device','local_volume_percent','speech_provider','voice','voice_gender','speech_rate','character_pause_ms','group_pause_ms','piper_executable','piper_model','voice_pack_root','voice_pack','eleven_voice','frequency_unit')
        if kind=='cw':
            names=('preview_device','local_volume_percent','cw_text','cw_wpm','cw_hz','cw_volume_percent')
        elif kind=='voice':
            names=names+('voice_text','voice_mode','voice_wav','voice_id_volume_percent')
        return read_group(self.settings,self.variables,names)

    def _start_preview(self, kind, value=None, settings=None):
        settings=settings or self._preview_settings(kind)
        if not settings.preview_device:
            self._select_page('Audio and PTT')
            self.field_widgets['preview_device'].focus_set()
            raise ValueError('Choose Local listening speakers first. This choice saves automatically.')
        self._confirm_preview()
        if self.engine.local_enabled:
            self.engine.set_local_muted(True)
        self._when_idle(lambda:self.engine.preview(kind,value,settings=settings),stop=self.engine.enabled)

    def _stash_profile_draft(self):
        if self.profile_edit_key is not None:
            self.profile_drafts[self.profile_edit_key]=dict(
                name=self.profile_name.get(),connection={k:self.variables[k].get() for k in SOURCE_FIELDS},
                secret=self.secret.get(),remember=self.remember_secret.get())

    def _restore_profile_draft(self,key):
        self.profile_edit_key=key
        draft=self.profile_drafts.get(key)
        if draft:
            self.profile_name.set(draft['name'])
            for name,value in draft['connection'].items():
                self.variables[name].set(value)
            self.secret.set(draft['secret']);self.remember_secret.set(draft['remember'])
            self._source_type_changed()
            self.profile_status.set('Restored unfinished profile edits. The active connection is unchanged.')

    def _profile_credential_notice(self,message):
        self._show_notice(message)

    def _offer_undo(self,message,action,finalize=None):
        if getattr(self,'undo_finalize',None):self.undo_finalize()
        self.undo_finalize=finalize
        self.undo_action=action
        self._show_notice(message)
        self.undo_button.pack(side='right',padx=8)

    def _undo(self):
        action,self.undo_action=self.undo_action,None
        self.undo_finalize=None
        self.undo_button.pack_forget()
        if action:
            action()
            self._show_notice('Restored.')

    def _validate_wav_choice(self):
        if not hasattr(self,'wav_status'):
            return
        path=self.variables['voice_wav'].get()
        if not path:
            self.wav_status.set('Choose a WAV file to check its format.')
            return
        try:
            from .audio import wav_clip
            clip=wav_clip(path)
            if self.variables['id_mode'].get()=='Both' and (clip.rate!=22050 or clip.channels!=1):
                raise ValueError('Both requires mono 22050 Hz PCM16.')
            self.wav_status.set(f'WAV ready. {clip.duration:.1f} seconds. {clip.rate} Hz. {clip.channels} channel(s).')
        except Exception as exc:
            self.wav_status.set('WAV not ready. '+str(exc))

    def _visible_spots(self):
        if self.render_cache.changed('spot_visibility', self._spot_view_revision):
            self._visible_count=sum(not reason for reason in self.spot_reasons.values())
        return self._visible_count

    def _refresh_operating_ui(self,count,age):
        if not hasattr(self,'empty_label'):
            return
        cache=self.render_cache
        visible=self._visible_spots()
        empty_state=(bool(visible),self.source is None,bool(self.rejected_spots),self.source_ready)
        if cache.changed('empty_spots',empty_state):
            if not visible:
                if self.source is None:
                    message='Choose a cluster profile and Connect. Matching spots appear even with audio off.'
                elif self.rejected_spots:
                    message='Reports are arriving but do not match your current filters. Open Spot details or Filters.'
                elif self.source_ready:
                    message='Connected. Waiting for new matching spots.'
                else:
                    message='Connecting or signing in. Check Connection status for progress.'
                cache.set(self.empty_spots,message)
                self.empty_label.place(relx=.5,rely=.5,anchor='center')
            else:
                self.empty_label.place_forget()
        shared=self.settings.preview_device and self.settings.preview_device==self.settings.radio_device
        cache.set(self.routing_hint,'Local audio uses the radio output and may key VOX. Select separate speakers to monitor RF.' if shared else 'RF and local listening can run together. Local mute and volume affect speakers only.' if self.settings.preview_device else 'Choose Local listening speakers to enable local audio.')
        state,level,remaining=self.engine.monitor.snapshot()
        # One pixel of display precision; the receive detector retains full precision.
        meter=round(5*max(0,min(60,(level if level is not None else -60)+60)))
        cache.coords(self.receive_level,self.receive_fill,0,0,meter,24)
        threshold=self.settings.receive_threshold_db
        marker=5*(threshold+60)
        cache.coords(self.receive_level,self.receive_mark,marker,0,marker,24)
        cache.set(self.receive_threshold,f'Receive level: {level:.0f} dBFS. Threshold: {threshold} dBFS.' if level is not None and state!='off' else f'Receive threshold: {threshold} dBFS. Test receive input to see its level.')
        cache.configure(self.catch_up_button,state='normal' if count else 'disabled')
        selection=None
        for button,action in getattr(self,'capability_buttons',[]):
            available=True
            if action=='preview':
                if selection is None:selection=bool(self.tree.selection())
                available=selection
            elif action=='identify':available=self.engine.enabled
            elif action=='install':available=bool(self.update_download) and not self.update_busy
            elif action=='download':available=bool(self.update_release) and not self.update_busy
            elif action=='check':available=not self.update_busy
            cache.configure(button,state='normal' if available else 'disabled')

    def _search_help(self):
        term=self.help_search.get().strip()
        if not term:return
        for page in self.help_topics:
            from .app import resource_root
            text=(resource_root()/'docs/help'/page['path']).read_text(encoding='utf-8')
            if term.casefold() in text.casefold():
                self.help_topic.set(page['title']);self._show_help()
                index=self.help_text.search(term,'1.0',nocase=True)
                if index:
                    self.help_text.tag_remove('search','1.0','end')
                    self.help_text.tag_add('search',index,index+'+'+str(len(term))+'c')
                    self.help_text.tag_configure('search',background=PALETTES[self.theme.get()]['selected'])
                    self.help_text.see(index)
                return
        self._show_notice('No help topic contains '+term+'.')

    def _show_spot_details(self):
        """One destination for a selected receipt, exclusion counts and rejected rows."""
        from collections import Counter
        window=tk.Toplevel(self.root);window.title('Spot details');window.transient(self.root)
        panel=ttk.Frame(window,padding=16);panel.pack(fill='both',expand=True)
        selected=self.tree.selection()
        if selected and selected[0] in self.spots:
            row=selected[0];spot=self.spots[row]
            state,reason=self.spot_states.get(row,('display_only','Audio was off.'))
            ttk.Label(panel,text=spot.dx_call+' · '+spot.frequency_text(self.settings.frequency_unit)+' '+self.settings.frequency_unit).pack(anchor='w')
            ttk.Label(panel,text=state.replace('_',' ').capitalize()+'. '+reason,wraplength=600).pack(anchor='w',pady=8)
        counts=Counter(reason for _,reason in self.rejected_spots)
        ttk.Label(panel,text='Recent reports excluded by filtering or announcement rules',font=('Segoe UI',11,'bold')).pack(anchor='w',pady=8)
        if not counts:ttk.Label(panel,text='No recent exclusions. Select a live spot for its announcement result.').pack(anchor='w')
        for reason,count in counts.most_common():ttk.Label(panel,text=f'{count}: {reason}',wraplength=600).pack(anchor='w',pady=2)
        ttk.Button(panel,text='Review excluded spots',command=self._show_rejected_spots).pack(anchor='w',pady=8)
        ttk.Button(panel,text='Change filters',command=lambda:(window.destroy(),self._open_filters())).pack(anchor='w')
        ttk.Button(panel,text='Close',command=window.destroy).pack(anchor='e',pady=8)
        window.bind('<Escape>',lambda e:window.destroy())

    def _show_session_diagnostics(self):
        count,age,expired=self.engine.queue_status()
        window=tk.Toplevel(self.root);window.title('Announcement diagnostics');window.transient(self.root)
        ttk.Label(window,text=f'{count} queued. Oldest {age}s. Expired {expired}.\nLast audio preparation: {self.engine.preparation_seconds:.2f}s.',padding=16).pack()
        ttk.Button(window,text='Close',command=window.destroy).pack(pady=10)

    def _edit_locations(self, variable):
        from .geography import overrides, CONTINENTS
        window=tk.Toplevel(self.root);window.title('Known station locations');window.transient(self.root)
        panel=ttk.Frame(window,padding=16);panel.pack(fill='both',expand=True)
        values={name:tk.StringVar() for name in ('Callsign','Country code','Continent','Region')}
        for row,(name,var) in enumerate(values.items()):
            ttk.Label(panel,text=name).grid(row=row,column=0,sticky='w',padx=(0,12),pady=4)
            if name=='Continent':ttk.Combobox(panel,textvariable=var,values=CONTINENTS,state='readonly',width=18).grid(row=row,column=1,sticky='w')
            else:ttk.Entry(panel,textvariable=var,width=22).grid(row=row,column=1,sticky='w')
        listing=tk.Listbox(panel,width=54,height=7,exportselection=False);listing.grid(row=4,column=0,columnspan=2,pady=10)
        message=tk.StringVar();ttk.Label(panel,textvariable=message,wraplength=430).grid(row=5,column=0,columnspan=2)
        def refresh():
            listing.delete(0,'end')
            for call,item in overrides(variable.get()).items():listing.insert('end',call+'='+item['dx_country']+','+item['dx_continent']+(','+item['spotter_region'] if item['spotter_region'] else ''))
        def select(event=None):
            if listing.curselection():
                text=listing.get(listing.curselection()[0]);call,location=text.split('=');parts=location.split(',')
                for var,value in zip(values.values(),[call]+parts+['']):var.set(value)
        listing.bind('<<ListboxSelect>>',select)
        def save():
            try:
                raw=[v.get().strip().upper() for v in values.values()]
                entry=raw[0]+'='+raw[1]+','+raw[2]+(','+raw[3] if raw[3] else '')
                overrides(entry)
                entries=[listing.get(i) for i in range(listing.size()) if not listing.get(i).startswith(raw[0]+'=')]
                variable.set(';'.join(entries+[entry]));refresh();message.set('Location saved.')
            except ValueError as exc:message.set(str(exc))
        def remove():
            if not listing.curselection():return
            previous=variable.get();index=listing.curselection()[0]
            variable.set(';'.join(listing.get(i) for i in range(listing.size()) if i!=index));refresh()
            self._offer_undo('Location removed.',lambda:(variable.set(previous),refresh() if window.winfo_exists() else None))
        ttk.Button(panel,text='Add or update',command=save).grid(row=6,column=0,pady=8)
        ttk.Button(panel,text='Remove selected',command=remove).grid(row=6,column=1)
        ttk.Button(panel,text='Close',command=window.destroy).grid(row=7,column=1,pady=8)
        refresh()

    def _choose_locations(self, variable, title, continent=False):
        from .geography import CONTINENTS
        values=CONTINENTS if continent else ('US','CA','MX','GB','DE','FR','IT','ES','JP','AU','NZ','BR','ZA')
        window=tk.Toplevel(self.root);window.title(title);window.transient(self.root)
        ttk.Label(window,text='Choose common locations. Other country codes remain available in the text field.',wraplength=400).grid(row=0,column=0,columnspan=3,padx=12,pady=8)
        selected=set(variable.get().split(',')) if variable.get() else set()
        flags={value:tk.BooleanVar(value=value in selected) for value in values}
        def use():
            other=selected-set(values)
            variable.set(','.join(sorted(other|{v for v,f in flags.items() if f.get()})))
        for i,(value,flag) in enumerate(flags.items()):ttk.Checkbutton(window,text=value,variable=flag,command=use).grid(row=1+i//3,column=i%3,padx=12,pady=4,sticky='w')
        def clear():
            selected.clear()
            for flag in flags.values():flag.set(False)
            use()
        ttk.Button(window,text='All locations',command=clear).grid(row=8,column=0,pady=10)
        ttk.Button(window,text='Close',command=window.destroy).grid(row=8,column=2,pady=10)

    def _persist_profile_drafts(self):
        from urllib.parse import urlsplit
        self._stash_profile_draft()
        clean={}
        for key,draft in self.profile_drafts.items():
            connection=dict(draft['connection'])
            try:
                url=urlsplit(str(connection.get('feed_url','')))
                if url.username or url.password or url.query:connection['feed_url']=''
            except ValueError:connection['feed_url']=''
            clean[key]=dict(name=draft['name'],connection=connection)
        path=settings_path().with_name('profile-drafts.json')
        try:
            path.parent.mkdir(parents=True,exist_ok=True)
            temporary=path.with_suffix('.tmp')
            temporary.write_text(json.dumps(clean),encoding='utf-8');temporary.replace(path)
        except OSError:self._show_notice('Profile drafts could not be saved. Check settings folder permissions.')

    def _load_profile_drafts(self):
        path=settings_path().with_name('profile-drafts.json')
        try:
            if path.stat().st_size>131072:return
            saved=json.loads(path.read_text(encoding='utf-8'))
            for key,draft in saved.items():
                if type(key) is not str or not isinstance(draft,dict):continue
                if set(draft)!= {'name','connection'} or not isinstance(draft['name'],str):continue
                connection=draft['connection']
                if not isinstance(connection,dict) or set(connection)!=set(SOURCE_FIELDS):continue
                if any(type(value) not in (str,int) for value in connection.values()):continue
                self.profile_drafts[key]=dict(name=draft['name'],connection=connection,secret='',remember=False)
            self._restore_profile_draft('new')
        except (OSError,ValueError,TypeError,AttributeError):return

    def _mark_field(self,key,invalid):
        widget=self.field_widgets.get(key)
        if widget is None:return
        base=widget.winfo_class()
        style=ttk.Style(self.root)
        if invalid:
            style.configure('Invalid.'+base,bordercolor='#d63852',lightcolor='#d63852',darkcolor='#d63852')
            widget.configure(style='Invalid.'+base)
        else:widget.configure(style=base)

    def _has_source_edits(self):
        if self.source is None:return False
        active=getattr(self.source,'settings',self.settings)
        if not isinstance(active,Settings):active=self.settings
        return any(str(self.variables[k].get())!=str(getattr(active,k)) for k in SOURCE_FIELDS) or self.secret.get()!=getattr(self,'active_secret',self.secret.get())
