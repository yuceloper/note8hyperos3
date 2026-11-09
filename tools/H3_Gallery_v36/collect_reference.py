#!/usr/bin/env python3
"""Read-only Gallery code/manifest reference collection; no app data is pulled."""
import hashlib
import json
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

SERIAL='12da33e7'

def adb(*args):
    return subprocess.run(['adb','-s',SERIAL,*args],check=True,stdin=subprocess.DEVNULL,capture_output=True,timeout=180)

def main():
    root=Path.cwd()
    if not (root/'tools/H3_Gallery_v36').is_dir():raise SystemExit('Run from note8hyperos3 repository root')
    destination=root/'logs'/('gallery-v36-reference-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.zip')
    destination.parent.mkdir(exist_ok=True)
    if destination.exists():raise SystemExit('Output already exists')
    raw=adb('shell','pm','path','com.miui.gallery').stdout
    paths=[line.removeprefix('package:').strip() for line in raw.decode().splitlines() if line.startswith('package:')]
    if not paths or len(paths)!=len(set(paths)) or any(not p.startswith('/') or not p.endswith('.apk') for p in paths):
        raise RuntimeError('Unexpected Gallery package paths')
    manifest=[]
    with tempfile.TemporaryDirectory(prefix='ginkgo-gallery-reference-') as tmp:
        with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as output:
            output.writestr('package-path.txt',raw)
            for index,remote in enumerate(paths):
                local=Path(tmp)/f'apk-{index}.apk'
                print('GALERI APK OKUNUYOR:',index,flush=True)
                adb('pull',remote,str(local))
                with local.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
                with zipfile.ZipFile(local) as source:
                    if len(source.namelist())!=len(set(source.namelist())):raise RuntimeError('Duplicate APK entries')
                    selected=[]
                    for name in source.namelist():
                        if name in ('AndroidManifest.xml','resources.arsc') or ('/' not in name and name.startswith('classes') and name.endswith('.dex')):
                            output.writestr(f'apk-{index}/'+name,source.read(name));selected.append(name)
                    if 'AndroidManifest.xml' not in selected:raise RuntimeError('APK manifest missing')
                manifest.append(dict(remote_path=remote,apk_sha256=sha,apk_size=local.stat().st_size,entries=selected))
            output.writestr('gallery-package.txt',adb('shell','dumpsys','package','com.miui.gallery').stdout)
            output.writestr('camera-package.txt',adb('shell','dumpsys','package','com.android.camera').stdout)
            output.writestr('reference.json',json.dumps(dict(read_only=True,apk_references=manifest,app_private_data_collected=False),indent=2))
    with zipfile.ZipFile(destination) as z:
        if z.testzip() is not None:raise RuntimeError('Reference ZIP verification failed')
    print('PAKET HAZIR:',destination)
    print('UYGULAMA VERISI ALINMADI. TELEFONA YAZMA/REBOOT/KURULUM YAPILMADI.')
    subprocess.run(['open','-R',str(destination)],check=False,stdin=subprocess.DEVNULL)

if __name__=='__main__':main()
