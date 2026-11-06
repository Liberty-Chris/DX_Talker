"""Keyless pilot generation into offline voice packs through the shared service."""
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, ttk
from .audio import Cancelled
from .elevenlabs import build_pack, CancelEither
from .cloud_speech import SharedSpeech
from .models import settings_path
from .voicepacks import vocabulary


class ElevenLabsDialog:
    def __init__(self, app):
        existing=getattr(app,'eleven_dialog',None)
        if existing and existing.window.winfo_exists():existing.window.lift();return
        self.app=app;app.eleven_dialog=self
        self.window=tk.Toplevel(app.root);self.window.title('Generate an ElevenLabs recorded voice');self.window.transient(app.root)
        self.cancel=threading.Event();self.events=queue.SimpleQueue();self.busy=False;self.closed=False
        frame=ttk.Frame(self.window,padding=16);frame.pack(fill='both',expand=True)
        self.values={}
        fields=[('Voice label','ElevenLabs pilot voice'),('Voice pack folder',app.variables['voice_pack_root'].get() or str(settings_path().parent/'voices')),
                ('Pack name','elevenlabs-voice'),('Custom intro',app.variables['announcement_intro'].get())]
        for row,(label,value) in enumerate(fields):
            ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',padx=(0,12),pady=4)
            var=tk.StringVar(value=value);self.values[label]=var
            ttk.Entry(frame,textvariable=var,width=42).grid(row=row,column=1,sticky='w',pady=4)
            if label=='Voice pack folder':
                def browse():
                    folder=filedialog.askdirectory(parent=self.window,title='Choose parent voice pack folder')
                    if folder:self.values['Voice pack folder'].set(folder)
                ttk.Button(frame,text='Browse',command=browse).grid(row=row,column=2,padx=8)
        self.voice_names={};self.voice_choice=tk.StringVar()
        self.voices=ttk.Combobox(frame,textvariable=self.voice_choice,state='readonly',width=42)
        self.voices.grid(row=4,column=1,sticky='w',pady=8)
        self.load=ttk.Button(frame,text='Refresh voices',command=lambda:self.begin('voices'));self.load.grid(row=4,column=0,sticky='w')
        ttk.Label(frame,text='Uses our shared DX Talker pilot account. No API key is needed. Refresh voices to choose one, or leave blank for the service default. Generation uses the shared testing allowance. Text is sent to our speech service and ElevenLabs; normal Recorded playback stays offline.',wraplength=600).grid(row=5,column=0,columnspan=3,sticky='w',pady=8)
        self.estimate=tk.StringVar();ttk.Label(frame,textvariable=self.estimate,wraplength=600).grid(row=6,column=0,columnspan=3,sticky='w')
        def estimate(*args):
            words=vocabulary(self.values['Custom intro'].get())
            self.estimate.set(f'Generate {len(words)} clips, about {sum(map(len,words.values()))} text characters. Interrupted jobs can resume with the same folder, name, voice and intro.')
        self.values['Custom intro'].trace_add('write',estimate);estimate()
        self.status=tk.StringVar(value='Choose a destination, then Generate voice pack.')
        ttk.Label(frame,textvariable=self.status,wraplength=600).grid(row=7,column=0,columnspan=3,sticky='w',pady=10)
        self.progress=ttk.Progressbar(frame,length=420,mode='determinate');self.progress.grid(row=8,column=0,columnspan=3,sticky='ew')
        self.generate=ttk.Button(frame,text='Generate voice pack',command=lambda:self.begin('generate'));self.generate.grid(row=9,column=1,sticky='w',pady=10)
        self.cancel_button=ttk.Button(frame,text='Close',command=self.close);self.cancel_button.grid(row=9,column=2,pady=10)
        self.use=ttk.Button(frame,text='Use this voice',command=self.use_pack);self.destination=None
        self.window.protocol('WM_DELETE_WINDOW',self.close);self.window.after(100,self.poll)

    def begin(self,action):
        if self.busy:return
        try:
            values={key:variable.get().strip() for key,variable in self.values.items()}
            client=SharedSpeech()
            voice_id=self.voice_names.get(self.voice_choice.get(),'')
            if action=='generate':
                import re
                if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',values['Pack name']):raise ValueError('Use a pack name containing letters, numbers or underscores')
                if not Path(values['Voice pack folder']).is_absolute():raise ValueError('Choose an absolute voice pack folder')
                if not values['Voice label'] or len(values['Voice label'])>100:raise ValueError('Enter a voice label up to 100 characters')
                if len(values['Custom intro'])>80:raise ValueError('Use an intro up to 80 characters')
                destination=Path(values['Voice pack folder'])/values['Pack name']
                if destination.exists():raise ValueError('Choose a new pack name. Completed packs are never overwritten.')
            self.cancel.clear();self.busy=True
            request_cancel=CancelEither(self.cancel,self.app.background_cancel)
            self.generate.configure(state='disabled');self.load.configure(state='disabled');self.use.grid_remove()
            self.cancel_button.configure(text='Cancel generation' if action=='generate' else 'Cancel request')
            self.status.set('Using shared pilot speech service...')
            def task():
                try:
                    catalog=client.catalog(request_cancel)
                    if action=='voices':self.events.put(('voices',{v['name']+' ('+v['id']+')':v['id'] for v in catalog['voices']}))
                    else:
                        selected=voice_id or catalog['voices'][0]['id']
                        if selected not in {v['id'] for v in catalog['voices']}:raise ValueError('This voice is no longer enabled. Refresh the voice list.')
                        path=build_pack(client,destination,values['Voice label'],selected,catalog['model_id'],values['Custom intro'],request_cancel,
                                        progress=lambda done,total:self.events.put(('progress',(done,total))))
                        self.events.put(('done',path))
                except Cancelled:self.events.put(('error','Cancelled. Completed clips are kept for resuming. The current service request may still use testing allowance.'))
                except Exception as exc:self.events.put(('error',str(exc) if isinstance(exc,ValueError) else 'Generation failed. Check folder permissions or contact the pilot administrator.'))
            threading.Thread(target=task,daemon=True,name='Shared ElevenLabs generation').start()
        except ValueError as exc:self.status.set(str(exc))

    def poll(self):
        if self.closed or self.app.closing:self.cancel.set();return
        while not self.events.empty():
            kind,value=self.events.get_nowait()
            if kind=='progress':
                done,total=value;self.progress.configure(maximum=total,value=done);self.status.set(f'Generated or verified {done} of {total} clips');continue
            self.busy=False;self.generate.configure(state='normal');self.load.configure(state='normal');self.cancel_button.configure(text='Close')
            if kind=='voices':self.voice_names=value;self.voices.configure(values=['']+list(value));self.status.set('Choose a voice or leave blank for the service default.')
            elif kind=='done':
                self.destination=Path(value);self.status.set('Voice pack ready. Choose Use this voice, then Save and apply and Preview sample speech.')
                self.use.grid(row=10,column=1,sticky='w',pady=8)
            else:self.status.set(value)
        self.window.after(100,self.poll)

    def use_pack(self):
        self.app.variables['voice_pack_root'].set(str(self.destination.parent));self.app.variables['voice_pack'].set(self.destination.name)
        self.app.variables['speech_provider'].set('Recorded');self.app._refresh_voice_packs();self.app._speech_provider_changed();self.close()

    def close(self):
        if self.busy:self.cancel.set();self.status.set('Cancelling. Completed clips will be kept.');return
        self.cancel.set();self.closed=True;self.window.destroy()
