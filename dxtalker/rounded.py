"""Rounded ttk surfaces retain native widget focus, keyboard and disabled behavior."""
from functools import lru_cache
import hashlib
import struct
import tkinter as tk
from tkinter import ttk
import zlib


@lru_cache(maxsize=128)
def _surface(fill, edge, size=32, radius=9, thickness=1):
    def color(value):return tuple(int(value[i:i+2],16) for i in (1,3,5))
    fill,edge=color(fill),color(edge)
    def inside(x,y,inset):
        r=radius-inset
        cx=min(max(x,radius),size-radius);cy=min(max(y,radius),size-radius)
        return inset<=x<size-inset and inset<=y<size-inset and (x-cx)**2+(y-cy)**2<=r*r
    rows=bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            outer=inner=0
            for sy in (.125,.375,.625,.875):
                for sx in (.125,.375,.625,.875):
                    outer+=inside(x+sx,y+sy,0);inner+=inside(x+sx,y+sy,thickness)
            rgb=tuple(round((inner*f+(outer-inner)*e)/outer) if outer else 0 for f,e in zip(fill,edge))
            rows.extend((*rgb,round(255*outer/16)))
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(rows)))+chunk(b'IEND',b'')


def button_style(root,palette,fill,edge,ink,name=None):
    key=hashlib.sha1((fill+edge+ink+str(palette)).encode()).hexdigest()[:16]
    element='Rounded'+key+'.border'
    style=ttk.Style(root)
    cache=getattr(root,'_rounded_images',None)
    if cache is None:cache={};root._rounded_images=cache
    if element not in cache:
        images=[tk.PhotoImage(master=root,data=_surface(f,e)) for f,e in
                ((fill,edge),(fill,edge if edge=='#d63852' else palette['accent']),(palette['selected'] if fill==palette['field'] else fill,edge),(palette['field'],palette['edge']))]
        cache[element]=images
        style.element_create(element,'image',images[0],('disabled',images[3]),('focus',images[1]),('active',images[2]),border=10,padding=0,sticky='nsew')
    if name is None:
        name='Rounded'+key+'.TButton'
        if name in getattr(root,'_rounded_styles',set()):return name
        if not hasattr(root,'_rounded_styles'):root._rounded_styles=set()
        root._rounded_styles.add(name)
    style.layout(name,[(element,{'sticky':'nsew','children':[('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})]})])
    style.configure(name,foreground=ink,background=palette['bg'],padding=(10,7),bordercolor=edge)
    style.map(name,foreground=[('disabled',palette['muted']),('active',ink)])
    return name


def install(root,palette,theme):
    button_style(root,palette,palette['field'],palette['edge'],palette['ink'],'TButton')
    button_style(root,palette,palette['accent'],palette['accent'],'#ffffff' if theme in ('Light','High contrast') else '#071722','Accent.TButton')
    button_style(root,palette,'#b22b42','#b22b42','#ffffff','Stop.TButton')
    style=ttk.Style(root)
    key='RoundedCard'+hashlib.sha1(str(palette).encode()).hexdigest()[:12]
    if key not in root._rounded_images:
        image=tk.PhotoImage(master=root,data=_surface(palette['bg'],palette['edge']))
        root._rounded_images[key]=[image]
        style.element_create(key,'image',image,border=10,padding=0,sticky='nsew')
    style.layout('TLabelframe',[(key,{'sticky':'nsew'})])
