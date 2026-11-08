"""Compile a CRT-free XP launcher and the pinned XP-compatible setup engine."""
import argparse
import os
from pathlib import Path
import re
import struct
import shutil
import subprocess
import sys
from prepare import ROOT, fetch, machine


def development_environment(architecture):
    finder = Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'))/'Microsoft Visual Studio/Installer/vswhere.exe'
    installation = subprocess.check_output([str(finder),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True).strip()
    if not installation: raise ValueError('A Windows C toolchain is required')
    script = Path(installation)/'Common7/Tools/VsDevCmd.bat'
    command = '"' + str(script) + '" -no_logo -arch=' + architecture + ' >nul && set'
    # Capture rather than print the developer environment: it can contain build
    # secrets inherited from Actions. Compiler output never includes that data.
    output = subprocess.check_output('cmd.exe /d /s /c "' + command + '"',text=True)
    result = {name.upper(): value for name, value in os.environ.items()}
    for line in output.splitlines():
        name, equals, value = line.partition('=')
        if equals and name: result[name.upper()] = value
    return result


def imports(path):
    data=Path(path).read_bytes(); pe=struct.unpack_from('<I',data,60)[0]
    count=struct.unpack_from('<H',data,pe+6)[0]; optional=pe+24
    size=struct.unpack_from('<H',data,pe+20)[0]
    magic=struct.unpack_from('<H',data,optional)[0]
    directory=optional+(96 if magic==0x10b else 112)
    rva=struct.unpack_from('<I',data,directory+8)[0]
    sections=[]
    for index in range(count):
        start=optional+size+index*40
        virtual_size, address, raw_size, offset=struct.unpack_from('<IIII',data,start+8)
        sections.append((address,max(virtual_size,raw_size),offset))
    def at(address):
        for start,length,offset in sections:
            if start<=address<start+length:return offset+address-start
        raise ValueError('Invalid PE directory')
    result=[]; cursor=at(rva)
    while any(data[cursor:cursor+20]):
        address=struct.unpack_from('<I',data,cursor+12)[0]; start=at(address)
        end=data.index(b'\0',start)
        result.append(data[start:end].decode('ascii').lower());cursor+=20
        if len(result)>20:raise ValueError('Unexpected native import table')
    return result


def build(architecture, stage):
    if os.name!='nt': raise ValueError('Installer compilation requires Windows')
    stage=Path(stage).resolve()
    expected=0x14c if architecture=='x86' else 0x8664
    if machine(stage/'runtime/python.exe')!=expected:raise ValueError('The private runtime has the wrong architecture')
    version=re.search(r'__version__ = "([^"]+)"',(ROOT/'dxtalker/__init__.py').read_text()).group(1)
    match=re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(?:a|b|rc)?(\d*)',version)
    if not match:raise ValueError('Invalid application version')
    if not re.search(r'(a|b|rc)\d+$', version):
        sys.path.insert(0, str(ROOT/'scripts'))
        from check_stable_release import check
        check(ROOT)
        raise ValueError('Stable XP installer terms presentation must be reviewed before enabling stable packaging')
    numeric=','.join(str(int(value or 0)) for value in match.groups())
    bits='32' if architecture=='x86' else '64'
    resource=stage/'launcher.rc'
    icon=str(stage/'assets/brand/dxt.ico').replace('\\','\\\\')
    resource.write_text('1 ICON "'+icon+'"\n1 VERSIONINFO\n FILEVERSION '+numeric+'\n PRODUCTVERSION '+numeric+'\n FILEOS 0x40004L\n FILETYPE 0x1L\nBEGIN\n BLOCK "StringFileInfo"\n BEGIN\n  BLOCK "040904b0"\n  BEGIN\n   VALUE "FileDescription", "DX Talker for Windows XP"\n   VALUE "FileVersion", "'+version+'"\n   VALUE "ProductName", "DX Talker"\n   VALUE "ProductVersion", "'+version+'"\n  END\n END\n BLOCK "VarFileInfo"\n BEGIN\n  VALUE "Translation", 0x409, 1200\n END\nEND\n',encoding='utf-8')
    env=development_environment(architecture)
    def tool(name):
        path = shutil.which(name, path=env.get('PATH', ''))
        if not path: raise ValueError('Required build tool is missing: ' + name)
        return path
    subprocess.run([tool('cl.exe'),'/nologo','/c','/GS-','/Zl','/Od','/utf-8','/Fo'+str(stage/'launcher.obj'),str(ROOT/'platforms/xp/launcher.c')],env=env,check=True,timeout=60)
    subprocess.run([tool('rc.exe'),'/nologo','/fo',str(stage/'launcher.res'),str(resource)],env=env,check=True,timeout=60)
    minimum='5.01' if architecture=='x86' else '5.02'
    executable=stage/'DXTalkerXP.exe'
    subprocess.run([tool('link.exe'),'/nologo','/NODEFAULTLIB','/ENTRY:WinMainCRTStartup','/MANIFEST:NO','/SUBSYSTEM:WINDOWS,'+minimum,'/OSVERSION:'+minimum,'/MACHINE:'+architecture.upper(),'/OUT:'+str(executable),str(stage/'launcher.obj'),str(stage/'launcher.res'),'kernel32.lib','user32.lib'],env=env,check=True,timeout=60)
    if machine(executable)!=expected:raise ValueError('Launcher bitness mismatch')
    if set(imports(executable))-{'kernel32.dll','user32.dll'}:raise ValueError('The XP launcher must not depend on a modern C runtime')
    data=executable.read_bytes(); header=struct.unpack_from('<I',data,60)[0]+24
    if struct.unpack_from('<HH',data,header+48)>(5,1 if architecture=='x86' else 2):raise ValueError('The launcher has a newer subsystem requirement')
    cache=ROOT/'build/xp-downloads'
    engine=fetch('inno',cache)
    compiler=stage.parent/('inno-5-'+architecture)
    subprocess.run([str(engine),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/DIR='+str(compiler)],check=True,timeout=120)
    template=(ROOT/'platforms/xp/installer.iss').read_text()
    options={'VERSION':version,'STAGE':str(stage),'BITS':bits,'APPID':'{{B895D94A-A921-4A3D-A113-10A8C9508732}' if architecture=='x86' else '{{6D3E5BB7-240A-4B69-9B46-B0CC077A0164}',
             'ARCHFLAGS':'ArchitecturesAllowed=x86 x64' if architecture=='x86' else 'ArchitecturesAllowed=x64\nArchitecturesInstallIn64BitMode=x64',
             'MINVER':'0,5.1sp3' if architecture=='x86' else '0,5.2sp2','OUTPUT':str(ROOT/'dist')}
    for name,value in options.items():template=template.replace('@'+name+'@',value)
    script=stage/'installer.iss';script.write_text(template,encoding='utf-8-sig')
    subprocess.run([str(compiler/'ISCC.exe'),str(script)],check=True,timeout=180)
    output=ROOT/('dist/DXTalker-Setup-Windows-XP-'+bits+'bit.exe')
    if not output.is_file():raise ValueError('XP installer was not produced')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--architecture',choices=('x86','x64'),required=True);parser.add_argument('--stage',required=True)
    options=parser.parse_args();print(build(options.architecture,options.stage))
