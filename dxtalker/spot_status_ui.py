"""Session only announcement receipts. No audio, source or radio ownership."""
import tkinter as tk
from tkinter import ttk


def images(root):
    result={}
    for state,color in [('announced','#239e59'),('rejected','#e04f5f'),('queued','#8899aa'),('muted','#8899aa'),('display_only','#8899aa')]:
        icon=tk.PhotoImage(master=root,width=18,height=18)
        if state=='queued':
            icon.put(color,to=(6,6,12,12))
        else:
            strokes=[(3,14,3,4),(3,4,8,10),(8,10,13,4),(13,4,13,14)] if state=='muted' else [(3,9,7,13),(7,13,15,4)]
            if state=='rejected':strokes=[(4,4,14,14),(14,4,4,14)]
            if state=='display_only':strokes=[(3,4,3,14),(3,4,9,4),(9,4,13,8),(13,8,13,10),(13,10,9,14),(9,14,3,14)]
            for x1,y1,x2,y2 in strokes:
                steps=max(abs(x2-x1),abs(y2-y1))
                for i in range(steps+1):
                    x=round(x1+(x2-x1)*i/steps);y=round(y1+(y2-y1)*i/steps)
                    icon.put(color,to=(x,y,x+2,y+2))
        result[state]=icon
    return result


def details(app, spot, state, reason):
    reason={
        'Mode unknown':'The mode could not be identified from a reported tag or the supported frequency inference ranges. Choose All modes, including unknown to remove this mode restriction.',
        'License eligibility unverified':'Your license filter could not verify eligibility for this spot. This is separate from the mode selection. Review Include spots whose license eligibility cannot be verified in Source.',
        'Outside selected license segments':'The spot is outside the operating segments selected by your license filter.',
    }.get(reason,reason)
    window=tk.Toplevel(app.root);window.title('Announcement details');window.transient(app.root)
    title={'announced':'Announced','muted':'Locally muted. Not announced','display_only':'Displayed. Audio off','rejected':'Not announced','queued':'Queued','announcing':'Preparing or playing','sample':'Sample for local preview'}[state]
    ttk.Label(window,text=spot.dx_call+' · '+spot.frequency_text(app.settings.frequency_unit)+' '+app.settings.frequency_unit,font=('Segoe UI',12,'bold')).pack(anchor='w',padx=16,pady=(14,6))
    ttk.Label(window,text=title+' · '+spot.timestamp.strftime('%H:%M:%SZ')+' · '+spot.source).pack(anchor='w',padx=16)
    ttk.Label(window,text=reason,wraplength=480).pack(anchor='w',padx=16,pady=12)
    ttk.Button(window,text='Close',command=window.destroy).pack(pady=(0,12))
    return window


def rejected(app):
    window=getattr(app,'rejected_window',None)
    if window is not None and window.winfo_exists():window.destroy()
    window=tk.Toplevel(app.root);app.rejected_window=window
    window.title('Rejected spots · not in announcement list');window.transient(app.root)
    ttk.Label(window,text='Recent incoming spots rejected before admission. These are not queued for speech. Select an exclusion and open its reason, or press Enter.',wraplength=650).pack(padx=12,pady=12)
    table=ttk.Treeview(window,columns=('call','frequency','reason'),show='tree headings',height=10,selectmode='browse')
    table.column('#0',width=38,stretch=False);table.heading('#0',text='State')
    for key,title,width in [('call','DX callsign',130),('frequency','Frequency',110),('reason','Rejected because',350)]:
        table.heading(key,text=title);table.column(key,width=width)
    rows={}
    for spot,reason in reversed(app.rejected_spots):
        row=table.insert('', 'end', image=app.status_images['rejected'],values=(spot.dx_call,spot.frequency_text(app.settings.frequency_unit)+' '+app.settings.frequency_unit,reason));rows[row]=(spot,reason)
    scroll=ttk.Scrollbar(window,orient='vertical',command=table.yview);table.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right',fill='y');table.pack(fill='both',expand=True,padx=12)
    def show(event=None):
        selected=table.selection()
        if selected:
            spot,reason=rows[selected[0]];details(app,spot,'rejected',reason)
    table.bind('<ButtonRelease-1>',lambda event:show() if table.identify_column(event.x)=='#0' else None)
    table.bind('<Return>',show)
    ttk.Button(window,text='Rejection details',command=show).pack(pady=10)
    ttk.Button(window,text='Close',command=window.destroy).pack(pady=(0,10))
    return window


def sample_preview(app):
    from datetime import datetime
    from .models import UTC, parse_line
    window=tk.Toplevel(app.root);window.title('Sample preview · separate from live announcements');window.transient(app.root)
    ttk.Label(window,text='Synthetic samples for manual local preview. No source connection or serial PTT. Stop active output and select local speakers before previewing.',wraplength=500).pack(padx=16,pady=12)
    table=ttk.Treeview(window,columns=('call','frequency','mode'),show='headings',height=3)
    for key in ('call','frequency','mode'):table.heading(key,text={'call':'DX callsign','frequency':'Frequency kHz','mode':'Mode'}[key]);table.column(key,width=150)
    samples={};now=datetime.now(UTC)
    for freq,call,mode in [('14025.0','WB4IUY','CW'),('7074.0','KT4BN','FT8'),('50125.0','KF4DBX','SSB')]:
        spot=parse_line('DX de N0CALL: '+freq+' '+call+' '+mode+' Demo '+now.strftime('%H%M')+'Z','sample',now)
        row=table.insert('','end',values=(call,freq,mode));samples[row]=spot
    table.pack(padx=16)
    def preview():
        selected=table.selection()
        if not selected:raise ValueError('Select a sample first')
        app._start_preview('spot',samples[selected[0]])
    ttk.Button(window,text='Preview selected sample',command=app.guard(preview)).pack(pady=12)
    ttk.Button(window,text='Close',command=window.destroy).pack(pady=(0,12))
    return window
