"""Named source profiles with optional Windows account protected credentials."""
from dataclasses import asdict, replace
import base64
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import uuid

from .models import Settings, settings_path

SOURCE_FIELDS = ("source_type", "host", "port", "login", "feed_url", "poll_seconds")


def protect_secret(value, decrypt=False):
    if sys.platform != "win32":
        raise ValueError("Remembering passwords requires Windows account protection. Leave Remember password or token unchecked.")

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    raw = base64.b64decode(value, validate=True) if decrypt else value.encode("utf-8")
    buffer = ctypes.create_string_buffer(raw)
    source = Blob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                   ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise ValueError("Windows could not unlock this profile secret. Reenter it for this account.")
    try:
        result = ctypes.string_at(output.data, output.size)
        return result.decode("utf-8") if decrypt else base64.b64encode(result).decode("ascii")
    finally:
        kernel.LocalFree(output.data)


class ProfileStore:
    def __init__(self, path=None, protector=protect_secret):
        self.path = path or settings_path().with_name("profiles.json")
        self.protector = protector
        self.profiles = []
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("schema_version") != 1 or not isinstance(data.get("profiles"), list):
                raise ValueError("Unsupported cluster profiles file")
            for item in data["profiles"]:
                self._validate_name(item["name"])
                if not isinstance(item["id"], str) or not item["id"]:
                    raise ValueError("Invalid profile ID")
                replace(Settings(), **item["connection"]).validate_connection()
                if set(item["connection"]) != set(SOURCE_FIELDS):
                    raise ValueError("Invalid profile fields")
            if len({p["id"] for p in data["profiles"]}) != len(data["profiles"]) or len({p["name"].casefold() for p in data["profiles"]}) != len(data["profiles"]):
                raise ValueError("Duplicate cluster profiles")
            self.profiles = data["profiles"]

    @staticmethod
    def _validate_name(name):
        if not isinstance(name, str) or not name.strip() or len(name) > 80 or any(ord(c) < 32 for c in name):
            raise ValueError("Enter a profile name of 1 to 80 characters")

    def _write(self, profiles):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps({"schema_version": 1, "profiles": profiles}, indent=2), encoding="utf-8")
        temp.replace(self.path)
        self.profiles = profiles

    def save(self, name, settings, secret="", remember=False, profile_id=None):
        name = name.strip()
        self._validate_name(name)
        settings.validate_connection()
        if any(p["name"].casefold() == name.casefold() and p["id"] != profile_id for p in self.profiles):
            raise ValueError("A cluster profile already uses that name")
        if profile_id is not None and not any(p["id"] == profile_id for p in self.profiles):
            raise ValueError("The selected cluster profile no longer exists")
        item = {"id": profile_id or uuid.uuid4().hex, "name": name,
                "connection": {k: asdict(settings)[k] for k in SOURCE_FIELDS},
                "secret": self.protector(secret) if remember and secret else ""}
        self._write([p for p in self.profiles if p["id"] != item["id"]] + [item])
        return item

    def load(self, profile_id, settings):
        item = next(p for p in self.profiles if p["id"] == profile_id)
        secret = self.protector(item["secret"], decrypt=True) if item["secret"] else ""
        return replace(settings, **item["connection"]), secret

    def delete(self, profile_id):
        self._write([p for p in self.profiles if p["id"] != profile_id])
