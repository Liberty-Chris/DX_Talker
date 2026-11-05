"""Public GitHub release discovery and verified, operator initiated installer downloads."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import socket
import ssl
import threading
from urllib import request, error
from urllib.parse import urlsplit

from . import __version__

REPOSITORY = "Liberty-Chris/DX_Talker"
API = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=30"
INSTALLER = "DXTalker-Setup-Windows-x64.exe"
CHECKSUMS = "SHA256SUMS.txt"
MAX_INSTALLER = 300 * 1024 * 1024


def version_key(value):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?", value)
    if not match:
        raise ValueError("Unrecognized release version")
    major, minor, patch, stage, number = match.groups()
    return int(major), int(minor), int(patch), {"a": 0, "b": 1, "rc": 2, None: 3}[stage], int(number or 0)


def trusted_url(url):
    p = urlsplit(url)
    return (p.scheme == "https" and p.netloc == "github.com" and
            p.path.startswith(f"/{REPOSITORY}/releases/download/") and not p.query and not p.fragment)


@dataclass(frozen=True)
class Release:
    version: str
    page: str
    notes: str
    installer_url: str
    checksum_url: str
    size: int


def select_release(releases, current=__version__, channel="Pilot"):
    candidates = []
    for item in releases:
        if not isinstance(item, dict):
            continue
        if item.get("draft") or (item.get("prerelease") and channel == "Stable"):
            continue
        try:
            version = item["tag_name"]
            key = version_key(version)
            if key <= version_key(current):
                continue
            assets = {a["name"]: a for a in item["assets"]}
            setup, checksum = assets[INSTALLER], assets[CHECKSUMS]
            if not all(trusted_url(a["browser_download_url"]) for a in (setup, checksum)):
                continue
            if not 0 < setup["size"] <= MAX_INSTALLER:
                continue
            page = f"https://github.com/{REPOSITORY}/releases/tag/{version}"
            candidates.append((key, Release(version, page, (item.get("body") or "")[:12000],
                                            setup["browser_download_url"], checksum["browser_download_url"], setup["size"])))
        except (KeyError, TypeError, ValueError):
            continue
    return max(candidates, key=lambda pair: pair[0])[1] if candidates else None


class HTTPSRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https":
            raise ValueError("Update redirects must stay on HTTPS")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_url(url):
    return request.build_opener(HTTPSRedirect()).open(request.Request(url, headers={"User-Agent": "DXTalker/" + __version__,
                                                       "Accept": "application/vnd.github+json", "Cache-Control": "no-cache"}), timeout=15)


def read_releases(opener=open_url):
    with opener(API) as response:
        body = response.read(1024 * 1024 + 1)
    if len(body) > 1024 * 1024:
        raise ValueError("Release response exceeds size limit")
    releases = json.loads(body)
    if not isinstance(releases, list):
        raise ValueError("Release service did not return a release list")
    return releases


def check(channel="Pilot", opener=open_url):
    return select_release(read_releases(opener), channel=channel)


@dataclass(frozen=True)
class CheckResult:
    release: Release | None
    status: str


def check_report(channel="Pilot", current=__version__, opener=open_url):
    releases = read_releases(opener)
    selected = select_release(releases, current=current, channel=channel)
    context = f"Installed {current}. Channel: {channel}. "
    if selected:
        return CheckResult(selected, context + "Update available: " + selected.version)
    preview = select_release(releases, current=current, channel="Pilot")
    if channel == "Stable" and preview:
        return CheckResult(None, context + f"Preview {preview.version} is available. Choose Pilot and Check now to see preview updates.")
    if not releases:
        return CheckResult(None, context + "No releases have been published yet.")
    return CheckResult(None, context + "No newer compatible release is available.")


def describe_error(exc):
    if isinstance(exc, error.HTTPError):
        if exc.code == 429 or (exc.code == 403 and (exc.headers or {}).get("X-RateLimit-Remaining") == "0"):
            return "GitHub's public update check limit was reached. Wait and retry, or open Release page to download manually."
        return f"Update service returned HTTP {exc.code}. Try again or open Release page."
    reason = exc.reason if isinstance(exc, error.URLError) else exc
    if isinstance(reason, ssl.SSLCertVerificationError):
        return "The secure update connection could not be verified. Check the Windows clock and HTTPS filtering, or open Release page."
    if isinstance(reason, socket.gaierror):
        return "The update service hostname could not be resolved. Check the internet connection or open Release page."
    if isinstance(reason, TimeoutError):
        return "The update check timed out. Try Check now again or open Release page."
    return "Could not check for updates. Check your connection and try Check now, or open Release page."


def checksum_for(data):
    for line in data.decode("ascii").splitlines():
        match = re.fullmatch(r"([a-fA-F0-9]{64})\s+\*?" + re.escape(INSTALLER), line)
        if match:
            return match[1].lower()
    raise ValueError("The release does not include an installer checksum")


def download(release, directory, cancel=None, progress=lambda value: None, opener=open_url):
    if not trusted_url(release.installer_url) or not trusted_url(release.checksum_url):
        raise ValueError("Untrusted update location")
    cancel = cancel or threading.Event()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / INSTALLER
    partial = final.with_suffix(".partial")
    try:
        with opener(release.checksum_url) as response:
            raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError("Checksum file exceeds size limit")
        expected = checksum_for(raw)
        digest, count = hashlib.sha256(), 0
        with opener(release.installer_url) as response, partial.open("wb") as target:
            while True:
                if cancel.is_set():
                    raise InterruptedError("Update download cancelled")
                chunk = response.read(128 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                if count > release.size or count > MAX_INSTALLER:
                    raise ValueError("Installer exceeds expected size")
                target.write(chunk)
                digest.update(chunk)
                progress(round(count * 100 / release.size))
        if count != release.size or digest.hexdigest() != expected:
            raise ValueError("Installer verification failed. Download it again.")
        partial.replace(final)
        return final, expected
    finally:
        partial.unlink(missing_ok=True)


def verify_download(path, expected):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
