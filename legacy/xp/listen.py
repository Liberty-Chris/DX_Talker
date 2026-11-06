"""Experimental XP source test client. Python 3.4, SAPI 5; listening only, no RF."""
from __future__ import print_function
import json, os, queue, re, socket, subprocess, threading, time
import tkinter as tk
from tkinter import messagebox

WORDS = 'Alpha Bravo Charlie Delta Echo Foxtrot Golf Hotel India Juliet Kilo Lima Mike November Oscar Papa Quebec Romeo Sierra Tango Uniform Victor Whiskey Xray Yankee Zulu'.split()
DIGITS = 'zero one two three four five six seven eight nine'.split()
PATTERN = re.compile(r'^DX de ([A-Z0-9/\-]+):\s+(\d{1,7}(?:\.\d{1,4})?)\s+([A-Z0-9/\-]{2,20})\s+.*?(\d{4})Z?\s*$',re.I)

def announcement(line):
    match=PATTERN.match(line)
    if not match:return None
    call=match.group(3).upper()
    if not any(c.isdigit() for c in call) or not any(c.isalpha() for c in call):return None
    frequency=match.group(2)
    if not 1<=float(frequency)<=10000000:return None
    callwords=[WORDS[ord(c)-65] if c.isalpha() else DIGITS[int(c)] if c.isdigit() else 'stroke' if c=='/' else 'dash' for c in call]
    numbers=[DIGITS[int(c)] if c.isdigit() else 'point' for c in frequency]
    return 'New DX on. '+ ' '.join(numbers)+' kilohertz. '+' '.join(callwords)+'.'

class Client:
    def __init__(self,root):
        self.root=root;root.title('DX Talker XP listening test kit')
        self.events=queue.Queue(maxsize=100);self.speech=queue.Queue(maxsize=100)
        self.stop=threading.Event();self.stop.set();self.sock=None;self.voice=None;self.epoch=0
        self.fields={}
        for row,(name,default) in enumerate([('Host',''),('Port','7373'),('Callsign',''),('Password','')]):
            tk.Label(root,text=name).grid(row=row,column=0,sticky='w')
            value=tk.StringVar(value=default);self.fields[name]=value
            tk.Entry(root,textvariable=value,show='*' if name=='Password' else '',width=40).grid(row=row,column=1,padx=8,pady=4)
        self.button=tk.Button(root,text='Start listening',command=self.toggle);self.button.grid(row=4,column=1,pady=8)
        self.status=tk.StringVar(value='Experimental TCP/SAPI test. No radio audio selection or PTT.')
        tk.Label(root,textvariable=self.status,wraplength=420).grid(row=5,column=0,columnspan=2,padx=8,pady=8)
        self.rows=tk.Text(root,height=10,width=65,state='disabled');self.rows.grid(row=6,column=0,columnspan=2)
        self.closed=False;root.protocol('WM_DELETE_WINDOW',self.close)
        threading.Thread(target=self.speak_loop,daemon=True).start();root.after(100,self.poll)
    def log(self,event,error=None):
        try:
            folder=os.path.join(os.environ.get('LOCALAPPDATA',os.path.expanduser('~')),'DXTalker-XP-test')
            if not os.path.isdir(folder):os.makedirs(folder)
            path=os.path.join(folder,'diagnostics.jsonl')
            if os.path.exists(path) and os.path.getsize(path)>512000:
                if os.path.exists(path+'.1'):os.remove(path+'.1')
                os.rename(path,path+'.1')
            with open(path,'a') as output:output.write(json.dumps(dict(time=time.time(),event=event,error_type=type(error).__name__ if error else None))+'\n')
        except Exception:pass
    def emit(self,text):
        try:self.events.put_nowait(text)
        except queue.Full:pass
    def toggle(self):
        if not self.stop.is_set():self.halt();return
        try:
            host=self.fields['Host'].get().strip();port=int(self.fields['Port'].get());call=self.fields['Callsign'].get().strip();password=self.fields['Password'].get()
            if not host or not 1<=port<=65535:raise ValueError()
            if any(ord(c)<32 or ord(c)>126 for c in call+password) or len(call)>20 or len(password)>512:raise ValueError()
        except ValueError:messagebox.showerror('Connection','Enter a host, valid port and single-line ASCII login.');return
        self.stop.clear();self.epoch+=1;epoch=self.epoch;self.button.config(text='Stop listening')
        self.status.set('Connecting. Listening is armed before the first spot.');self.log('start')
        threading.Thread(target=self.connect,args=(host,port,call,password,epoch),daemon=True).start()
    def halt(self):
        self.stop.set();self.epoch+=1
        try:
            if self.sock:self.sock.close()
            if self.voice:self.voice.terminate()
        except Exception:pass
        self.button.config(text='Start listening');self.status.set('Stopped');self.log('stop')
    def connect(self,host,port,call,password,epoch):
        try:
            sock=socket.create_connection((host,port),5);sock.settimeout(.5);self.sock=sock
            self.emit('Connected. Waiting for login or first spot.');line='';iac=0;neg=0;sentcall=False;sentpass=False
            while not self.stop.is_set() and epoch==self.epoch:
                try:data=sock.recv(4096)
                except socket.timeout:continue
                if not data:raise IOError('closed')
                for b in bytearray(data):
                    if iac==1:
                        if b in (251,252,253,254):neg=b;iac=2
                        else:iac=0
                        continue
                    if iac==2:sock.sendall(bytes(bytearray([255,252 if neg in (253,254) else 254,b])));iac=0;continue
                    if b==255:iac=1;continue
                    if b in (10,13):
                        clean=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',line);spoken=announcement(clean)
                        if spoken:
                            self.emit(clean)
                            try:self.speech.put_nowait((epoch,spoken))
                            except queue.Full:pass
                        line=''
                    elif b==27 or 32<=b<127:
                        line=(line+chr(b))[-2048:]
                        if not sentcall and re.search(r'(?:login|call\s*sign|call|username)\s*[:>]\s*$',line,re.I):
                            if call:sock.sendall((call+'\r\n').encode('ascii'));sentcall=True;line=''
                            else:self.emit('Callsign required. Stop and edit the login.')
                        if not sentpass and re.search(r'password\s*[:>]\s*$',line,re.I):
                            if password:sock.sendall((password+'\r\n').encode('ascii'));sentpass=True;line=''
                            else:self.emit('Password required. Stop and edit the login.')
        except Exception as error:
            if epoch==self.epoch:self.log('connection_failure',error);self.emit('Connection failed or closed. Check host, port, login and cluster availability.');self.stop.set()
        finally:
            try:sock.close()
            except Exception:pass
    def speak_loop(self):
        while not self.closed:
            try:epoch,text=self.speech.get(timeout=.2)
            except queue.Empty:continue
            if self.stop.is_set() or epoch!=self.epoch:continue
            try:
                self.voice=subprocess.Popen(['cscript.exe','//nologo',os.path.join(os.path.dirname(os.path.abspath(__file__)),'speak.vbs'),text],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if self.voice.wait()!=0:self.emit('SAPI speech failed. Check the installed voice.');self.log('speech_failure')
            except Exception as error:self.log('speech_failure',error);self.emit('Could not start SAPI speech.')
    def poll(self):
        for unused in range(100):
            try:text=self.events.get_nowait()
            except queue.Empty:break
            if text.startswith('DX de '):
                self.rows.config(state='normal');self.rows.insert('end',text+'\n');self.rows.delete('1.0','end-150l');self.rows.see('end');self.rows.config(state='disabled')
            else:self.status.set(text)
        if self.stop.is_set():self.button.config(text='Start listening')
        if not self.closed:self.root.after(100,self.poll)
    def close(self):self.halt();self.closed=True;self.root.destroy()

if __name__=='__main__':
    if '--self-test' in __import__('sys').argv:
        assert announcement('DX de N0CALL: 7074 WB4IUY CQ 1234Z')
        assert announcement('chat or login:') is None
        print('XP test client parser checks passed. This is not XP runtime acceptance.')
    else:
        root=tk.Tk();Client(root);root.mainloop()
