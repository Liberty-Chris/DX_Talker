"""Rounded ttk surfaces retain native widget focus, keyboard and disabled behavior."""
from functools import lru_cache
import hashlib
import struct
import tkinter as tk
from tkinter import ttk
import zlib


@lru_cache(maxsize=8)
def _coverage(size, radius, thickness):
    def inside(x,y,inset):
        r=radius-inset
        cx=min(max(x,radius),size-radius);cy=min(max(y,radius),size-radius)
        return inset<=x<size-inset and inset<=y<size-inset and (x-cx)**2+(y-cy)**2<=r*r
    return tuple((sum(inside(x+sx,y+sy,0) for sy in (.125,.375,.625,.875) for sx in (.125,.375,.625,.875)),
                  sum(inside(x+sx,y+sy,thickness) for sy in (.125,.375,.625,.875) for sx in (.125,.375,.625,.875)))
                 for y in range(size) for x in range(size))


@lru_cache(maxsize=128)
def _surface(fill, edge, size=32, radius=9, thickness=1):
    def color(value):return tuple(int(value[i:i+2],16) for i in (1,3,5))
    fill,edge=color(fill),color(edge)
    pixels=bytearray()
    for outer,inner in _coverage(size,radius,thickness):
        rgb=tuple(round((inner*f+(outer-inner)*e)/outer) if outer else 0 for f,e in zip(fill,edge))
        pixels.extend((*rgb,round(255*outer/16)))
    # ttk tiles image elements rather than stretching them. A 12 pixel center
    # caused thousands of image draws for each large settings card. Widen the
    # solid strips while retaining identical corner pixels and widget minima.
    tile_size=max(256,size)
    rows=bytearray()
    half=size//2
    for y in range(tile_size):
        source_y=y if y<half else y-(tile_size-size) if y>=tile_size-half else half
        row=pixels[source_y*size*4:(source_y+1)*size*4]
        rows.append(0)
        rows.extend(row[:half*4]+row[half*4:half*4+4]*(tile_size-size)+row[half*4:])
    size=tile_size
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(rows)))+chunk(b'IEND',b'')


def _image(root, fill, edge):
    cache=getattr(root,'_rounded_surfaces',None)
    if cache is None:
        cache={};root._rounded_surfaces=cache
    key=(fill,edge)
    if key not in cache:
        cache[key]=tk.PhotoImage(master=root,data=_surface(fill,edge))
    return cache[key]


def button_style(root,palette,fill,edge,ink,name=None):
    key=hashlib.sha1((fill+edge+ink+str(palette)).encode()).hexdigest()[:16]
    element='Rounded'+key+'.border'
    style=ttk.Style(root)
    cache=getattr(root,'_rounded_images',None)
    if cache is None:cache={};root._rounded_images=cache
    if element not in cache:
        images=[_image(root,f,e) for f,e in
                ((fill,edge),(fill,edge if edge not in (palette['edge'],) else palette['accent']),(palette['selected'] if fill==palette['field'] else fill,edge),(palette['field'],palette['edge']))]
        cache[element]=images
        style.element_create(element,'image',images[0],('disabled',images[3]),('focus',images[1]),('active',images[2]),border=10,padding=0,width=32,height=32,sticky='nsew')
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
        image=_image(root,palette['bg'],palette['edge'])
        root._rounded_images[key]=[image]
        style.element_create(key,'image',image,border=10,padding=0,width=32,height=32,sticky='nsew')
    style.layout('TLabelframe',[(key,{'sticky':'nsew'})])
