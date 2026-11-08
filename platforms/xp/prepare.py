"""Stage official, hash-pinned XP runtimes without installing Python system-wide."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tarfile
import urllib.request
import zipfile
from build_app import ROOT, build

DOWNLOADS = json.loads((ROOT / 'platforms/xp/downloads.json').read_text())


def fetch(name, cache):
    item = DOWNLOADS[name]
    path = cache / item['url'].rsplit('/', 1)[1]
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']: return path
    temporary = path.with_suffix(path.suffix + '.partial')
    with urllib.request.urlopen(item['url'], timeout=30) as source, temporary.open('wb') as output:
        size = 0
        while True:
            block = source.read(1024 * 1024)
            if not block: break
            size += len(block)
            if size > 64 * 1024 * 1024: raise ValueError('Build dependency exceeds its size limit')
            output.write(block)
    if hashlib.sha256(temporary.read_bytes()).hexdigest() != item['sha256']:
        temporary.unlink(); raise ValueError('Dependency checksum mismatch: ' + name)
    temporary.replace(path)
    return path


def machine(path):
    data = Path(path).read_bytes()
    if data[:2] != b'MZ': raise ValueError('Not a Windows binary')
    offset = struct.unpack_from('<I', data, 60)[0]
    if data[offset:offset + 4] != b'PE\0\0': raise ValueError('Invalid PE signature')
    return struct.unpack_from('<H', data, offset + 4)[0]


def enable_private_crt(source, destination):
    # Administrative extraction otherwise omits both level-zero CRT features.
    # Change only a disposable copy's feature selection, never binary payloads
    # or the hash-pinned original MSI. No system-wide runtime is installed.
    import ctypes as C
    shutil.copy2(source, destination)
    msi = C.WinDLL('msi')
    msi.MsiOpenDatabaseW.argtypes=[C.c_wchar_p,C.c_void_p,C.POINTER(C.c_uint32)]
    msi.MsiDatabaseOpenViewW.argtypes=[C.c_uint32,C.c_wchar_p,C.POINTER(C.c_uint32)]
    msi.MsiViewExecute.argtypes=[C.c_uint32,C.c_uint32]
    msi.MsiDatabaseCommit.argtypes=[C.c_uint32]
    msi.MsiCloseHandle.argtypes=[C.c_uint32]
    database=C.c_uint32()
    if msi.MsiOpenDatabaseW(str(destination),C.c_void_p(1),C.byref(database)): raise ValueError('Cannot prepare the private CRT extraction')
    try:
        for sql in ("UPDATE `Feature` SET `Level`=1 WHERE `Feature`='PrivateCRT'",
                    "DELETE FROM `Condition` WHERE `Feature_`='PrivateCRT'"):
            view=C.c_uint32()
            result = msi.MsiDatabaseOpenViewW(database,sql,C.byref(view))
            if result: raise ValueError('Cannot select private CRT metadata (' + str(result) + '): ' + sql)
            try:
                if msi.MsiViewExecute(view,0): raise ValueError('Cannot apply the private CRT feature selection')
            finally: msi.MsiCloseHandle(view)
        if msi.MsiDatabaseCommit(database): raise ValueError('Cannot commit the private extraction metadata')
    finally: msi.MsiCloseHandle(database)


def prepare(architecture, output):
    if os.name != 'nt': raise ValueError('Runtime extraction requires a disposable Windows build runner')
    output = Path(output).resolve()
    if output.exists(): raise ValueError('Use a new build output folder')
    cache = ROOT / 'build/xp-downloads'; cache.mkdir(parents=True, exist_ok=True)
    installer = fetch('python_' + architecture, cache)
    image = output.parent / (output.name + '-msi-image')
    image.mkdir(parents=True, exist_ok=False)
    log = image.parent / (image.name + '.log')
    private_msi = image.parent / (image.name + '.msi')
    enable_private_crt(installer,private_msi)
    installer = private_msi
    subprocess.run(['msiexec.exe', '/a', str(installer), '/qn', 'TARGETDIR=' + str(image), '/L*v', str(log)], check=True, timeout=180)
    build(output, with_tests=True)
    runtime = output / 'runtime'; runtime.mkdir()
    for name in ('Lib', 'DLLs', 'tcl'):
        source = image / name
        if not source.is_dir(): raise ValueError('The official runtime is missing ' + name)
        shutil.copytree(source, runtime / name)
    for path in image.iterdir():
        if path.is_file() and (path.suffix.lower() == '.dll' or path.name.lower() in ('python.exe', 'pythonw.exe', 'license.txt')):
            shutil.copy2(path, runtime / path.name)
    for name in ('test', 'idlelib', 'turtledemo', 'ensurepip'):
        shutil.rmtree(runtime / 'Lib' / name, ignore_errors=True)
    expected = 0x14c if architecture == 'x86' else 0x8664
    for name in ('python.exe', 'pythonw.exe', 'python34.dll', 'msvcr100.dll', 'DLLs/_tkinter.pyd', 'DLLs/_ssl.pyd'):
        if machine(runtime / name) != expected: raise ValueError('Runtime architecture mismatch: ' + name)
    packages = runtime / 'Lib/site-packages'; packages.mkdir(exist_ok=True)
    for name in ('qrcode', 'six'):
        with zipfile.ZipFile(fetch(name, cache)) as wheel: wheel.extractall(packages)
    with zipfile.ZipFile(fetch('png', cache)) as wheel:
        wheel.extractall(packages)
    notices = output / 'assets/licenses'; notices.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fetch('qrcode_source', cache)) as archive:
        (notices / 'qrcode-5.3-LICENSE.txt').write_bytes(archive.extractfile('qrcode-5.3/LICENSE').read())
    shutil.rmtree(packages / 'qrcode/tests', ignore_errors=True)
    certificates = output / 'assets/certificates'; certificates.mkdir(parents=True)
    with zipfile.ZipFile(fetch('certificates', cache)) as wheel:
        (certificates / 'cacert.pem').write_bytes(wheel.read('certifi/cacert.pem'))
        license_name = next(name for name in wheel.namelist() if name.endswith('/LICENSE'))
        (certificates / 'LICENSE.txt').write_bytes(wheel.read(license_name))
    shutil.copy2(ROOT / 'LICENSE', output / 'LICENSE')
    icon_script = ROOT / 'platforms/xp/make_icon.ps1'
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(icon_script),'-Source',str(output/'assets/brand/icon.png'),'-Destination',str(output/'assets/brand/dxt.ico')],check=True,timeout=30)
    data = (output/'assets/brand/dxt.ico').read_bytes()
    bitmap = struct.unpack_from('<I',data,18)[0]
    if data[bitmap:bitmap+4] != b'\x28\0\0\0': raise ValueError('XP icon must use a bitmap resource')
    result = subprocess.run([str(runtime / 'python.exe'), '-I', '-c', 'import sys,struct,ssl,tkinter; print(sys.version); print(struct.calcsize("P")); print(ssl.OPENSSL_VERSION); assert sys.version_info[:3] == (3,4,4)'],check=True,capture_output=True,text=True,timeout=30)
    print(result.stdout)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--architecture', choices=('x86', 'x64'), required=True)
    parser.add_argument('--out', required=True)
    options = parser.parse_args()
    print(prepare(options.architecture, options.out))
