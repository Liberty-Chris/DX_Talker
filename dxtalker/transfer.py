"""Versioned, credential-free desktop/mobile transfer and curated directory records."""
import base64
import hashlib
import json
import zlib
from dataclasses import replace
from urllib.parse import urlsplit
from .models import Settings
from .profiles import SOURCE_FIELDS

from .listening import FIELDS
FILTER_FIELDS = (*FIELDS, 'listening_presets')
MAX_BYTES = 65536

def validate(data):
    if not isinstance(data, dict) or data.get('schema') != 'dxtalker-transfer' or type(data.get('version')) is not int or data.get('version') not in (1, 2, 3):
        raise ValueError('Unsupported DX Talker transfer')
    if set(data) != {'schema', 'version', 'profiles', 'filters'} or not isinstance(data['profiles'], list) or not data['profiles']:
        raise ValueError('Transfer must contain profiles and filters only')
    if not isinstance(data['filters'], dict) or set(data['filters']) - set(FILTER_FIELDS):
        raise ValueError('Unsupported filter fields')
    base = replace(Settings(), **data['filters']).validate()
    for item in data['profiles']:
        if not isinstance(item, dict) or set(item) != {'name', 'connection'}:
            raise ValueError('Credentials and unknown profile fields cannot be transferred')
        name = item['name']
        if not isinstance(name, str) or not name.strip() or len(name) > 80 or any(ord(c) < 32 for c in name):
            raise ValueError('Invalid transferred profile name')
        connection = item['connection']
        if not isinstance(connection, dict) or set(connection) != set(SOURCE_FIELDS):
            raise ValueError('Invalid connection fields')
        replace(base, **connection).validate_connection()
        if urlsplit(connection['feed_url']).query:
            raise ValueError('Remove query parameters from feed URLs before sharing; they may contain credentials')
    return data

def document(profiles, settings):
    return validate(dict(schema='dxtalker-transfer', version=3,
                         profiles=[dict(name=p['name'], connection=dict(p['connection'])) for p in profiles],
                         filters={k:getattr(settings,k) for k in FILTER_FIELDS}))

def encode(data, qr=False):
    raw = json.dumps(validate(data), separators=(',', ':'), ensure_ascii=True).encode()
    if len(raw) > MAX_BYTES: raise ValueError('Transfer exceeds 64 KiB; export fewer profiles')
    if not qr: return raw
    text = 'DXT1:' + base64.urlsafe_b64encode(zlib.compress(raw)).decode().rstrip('=')
    if len(text.encode()) > 1800: raise ValueError('Too much data for one readable QR. Select one profile or use a file.')
    return text

def qr_sequence(data):
    """One legacy QR when possible, otherwise bounded, independently numbered parts."""
    raw = encode(data)
    compressed = zlib.compress(raw)
    text = 'DXT1:' + base64.urlsafe_b64encode(compressed).decode().rstrip('=')
    if len(text) <= 1800:
        return [text]
    identity = hashlib.sha256(compressed).hexdigest()
    chunks = [compressed[i:i+1024] for i in range(0, len(compressed), 1024)]
    return [f'DXT2:{identity}:{i+1}:{len(chunks)}:' + base64.urlsafe_b64encode(chunk).decode().rstrip('=')
            for i, chunk in enumerate(chunks)]

def decode(value):
    raw = value.encode() if isinstance(value,str) else value
    if raw.startswith(b'DXT1:'):
        if len(raw) > 1800: raise ValueError('QR transfer is too large')
        try:
            encoded = raw[5:]
            compressed = base64.b64decode(encoded+b'='*((-len(encoded))%4), altchars=b'-_', validate=True)
            decoder = zlib.decompressobj()
            raw = decoder.decompress(compressed, MAX_BYTES+1)
            if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                raise ValueError('Incomplete or oversized QR transfer')
        except (zlib.error, ValueError) as exc:
            raise ValueError('Invalid QR transfer') from None
    if len(raw) > MAX_BYTES: raise ValueError('Transfer exceeds 64 KiB')
    try: return validate(json.loads(raw))
    except (TypeError, KeyError, UnicodeError, json.JSONDecodeError): raise ValueError('Invalid transfer document') from None

def catalog(data):
    if not isinstance(data,dict) or data.get('schema') != 'dxtalker-directory' or type(data.get('version')) is not int or data.get('version') not in (1, 2, 3):
        raise ValueError('Unsupported cluster directory')
    entries = data.get('entries')
    if not isinstance(entries,list): raise ValueError('Invalid cluster directory entries')
    ids=set()
    for item in entries:
        if not isinstance(item,dict) or set(item) != {'id','name','connection','status','checked','description'}:
            raise ValueError('Invalid cluster directory entry')
        if not isinstance(item['id'],str) or not item['id'] or item['id'] in ids: raise ValueError('Duplicate or missing directory ID')
        ids.add(item['id'])
        if item['status'] not in ('active','retired'): raise ValueError('Invalid directory status')
        if any(not isinstance(item[k],str) or len(item[k])>400 for k in ('checked','description')): raise ValueError('Invalid directory notes')
        validate(dict(schema='dxtalker-transfer',version=1,profiles=[dict(name=item['name'],connection=item['connection'])],filters={}))
    return entries
