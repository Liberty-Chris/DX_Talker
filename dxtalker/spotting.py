"""Explicit, reviewed submissions to the currently monitored cluster only."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import tkinter as tk
from tkinter import ttk
from .models import valid_call

@dataclass(frozen=True)
class SpotCommand:
    command: str


def command(call,frequency,unit='kHz',comment=''):
    call=call.strip().upper()
    if not valid_call(call):raise ValueError('Enter the station callsign')
    try:f=Decimal(frequency.strip())*(1000 if unit=='MHz' else 1)
    except (InvalidOperation,AttributeError):raise ValueError('Enter a numeric frequency') from None
    if unit not in ('kHz','MHz') or not f.is_finite() or not 1<=f<=10000000 or f.normalize().as_tuple().exponent < -4:
        raise ValueError('Choose kHz or MHz and a frequency with at most four decimal places in kHz')
    if len(comment)>100 or any(ord(c)<32 or ord(c)>126 for c in comment):
        raise ValueError('Use up to 100 printable characters in the optional comment')
    # Explicit fields only. No CR/LF, command separators or arbitrary commands.
    if any(c in comment for c in (';','|')):raise ValueError('Remove command separator characters from the comment')
    text=format(f,'f').rstrip('0').rstrip('.') if '.' in format(f,'f') else format(f,'f')
    return 'DX '+text+' '+call+(' '+comment.strip() if comment.strip() else '')


def open_spot_dialog(app,myself=False):
    source=app.source
    if source is None or source.settings.source_type!='TCP/Telnet' or not (source.ready.is_set() or source.signed_in.is_set()):
        app._show_notice('Sign in to a TCP/Telnet cluster before submitting a spot. HTTPS feeds are read only.');return
    window=tk.Toplevel(app.root);window.title('Spot myself' if myself else 'Spot a station');window.transient(app.root)
    frame=ttk.Frame(window,padding=16);frame.pack(fill='both',expand=True)
    call=tk.StringVar(value=source.settings.login if myself else '')
    frequency=tk.StringVar();unit=tk.StringVar(value=app.settings.frequency_unit);comment=tk.StringVar()
    for row,(title,var) in enumerate((('Station callsign',call),('Frequency',frequency),('Comment (optional)',comment))):
        ttk.Label(frame,text=title).grid(row=row,column=0,sticky='w',padx=(0,12),pady=6)
        ttk.Entry(frame,textvariable=var,width=38).grid(row=row,column=1,sticky='w')
    ttk.Combobox(frame,textvariable=unit,values=['kHz','MHz'],state='readonly',width=6).grid(row=1,column=2,padx=8)
    preview=tk.StringVar();app.spot_status=tk.StringVar()
    ttk.Label(frame,text='Only the current cluster receives this command. Cluster policy determines acceptance and propagation.',wraplength=520).grid(row=3,column=0,columnspan=3,sticky='w',pady=8)
    ttk.Label(frame,textvariable=preview,wraplength=520).grid(row=4,column=0,columnspan=3,sticky='w')
    ttk.Label(frame,textvariable=app.spot_status,wraplength=520).grid(row=5,column=0,columnspan=3,sticky='w',pady=8)
    reviewed=[None]
    send=ttk.Button(frame,text='Send reviewed spot',state='disabled')
    def review():
        try:
            reviewed[0]=command(call.get(),frequency.get(),unit.get(),comment.get());preview.set(reviewed[0]);send.configure(state='normal')
        except ValueError as exc:preview.set(str(exc));send.configure(state='disabled')
    def submit():
        if app.source is not source or not (source.ready.is_set() or source.signed_in.is_set()):app.spot_status.set('Cluster changed or disconnected. Close this form and review again.');return
        try:
            text=command(call.get(),frequency.get(),unit.get(),comment.get())
            if text!=reviewed[0]:raise ValueError('Review the changed spot before sending')
            source.submit_spot(text)
            send.configure(state='disabled');app.spot_status.set('Queued for this cluster. Waiting for socket delivery.')
        except ValueError as exc:app.spot_status.set(str(exc))
    def changed(*args):reviewed[0]=None;send.configure(state='disabled');preview.set('')
    for var in (call,frequency,unit,comment):var.trace_add('write',changed)
    ttk.Button(frame,text='Review spot',command=review).grid(row=6,column=0,pady=10)
    send.configure(command=submit);send.grid(row=6,column=1,sticky='w')
