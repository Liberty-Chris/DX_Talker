"""Verified TLS 1.2 using a bundled current CA file, never an HTTP fallback."""
from ssl import *
import os
import ssl as _native

PROTOCOL_TLS_CLIENT = getattr(_native, 'PROTOCOL_TLS_CLIENT', _native.PROTOCOL_SSLv23)
SSLCertVerificationError = getattr(_native, 'SSLCertVerificationError', _native.SSLError)

def create_default_context(purpose=Purpose.SERVER_AUTH, cafile=None, capath=None, cadata=None):
    if cafile is None and capath is None and cadata is None:
        cafile = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'certificates', 'cacert.pem')
        if not os.path.isfile(cafile): raise ValueError('The bundled HTTPS certificate file is missing. Reinstall DX Talker.')
    context = _native.create_default_context(purpose, cafile=cafile, capath=capath, cadata=cadata)
    context.options |= _native.OP_NO_TLSv1 | _native.OP_NO_TLSv1_1
    if purpose == Purpose.SERVER_AUTH:
        context.verify_mode = _native.CERT_REQUIRED
        context.check_hostname = True
    return context
