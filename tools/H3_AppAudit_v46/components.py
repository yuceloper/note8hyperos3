"""Read raw manifests and regional selection files; never install components."""
from pathlib import Path
import hashlib,json,re,subprocess,zipfile
ROOTS={'donor':Path('/linux/source/creek-tr-3.0.302.0'),
       'work_tree':Path('/linux/build/hyperos3-ginkgo-v1')}
OUT=Path('/out/components-v1')
TARGETS={'com.android.contacts','com.android.incallui','com.android.mms',
         'com.android.dialer','com.xiaomi.phone','com.google.android.dialer',
         'com.google.android.contacts','com.google.android.apps.messaging'}
PATTERN=re.compile(r'GoogleDialer|GoogleContacts|Messages_arm64|MiuiMms|MtkContacts|com\.android\.contacts|com\.android\.incallui|com\.android\.mms|com\.google\.android\.(?:dialer|contacts|apps\.messaging)|mi_ext|isGoogleCsp',re.I)
def main():
    if OUT.exists():raise RuntimeError('Output exists; nothing overwritten')
    if any(not p.is_dir() for p in ROOTS.values()):raise RuntimeError('Source roots unavailable')
    OUT.mkdir(parents=True);report={'status':'READ_ONLY_COMPONENT_REVIEW','roots':{},'source_modified':False}
    for label,root in ROOTS.items():
        rows=[];matches=[]
        for p in sorted(root.rglob('*.apk')):
            rel=str(p.relative_to(root));row={'path':rel,'size':p.lstat().st_size}
            if p.is_symlink():row['state']='SYMLINK';row['target']=str(p.readlink());rows.append(row);continue
            if not zipfile.is_zipfile(p):
                row['state']='NOT_ZIP';row['prefix_hex']=p.read_bytes()[:64].hex();rows.append(row);continue
            with zipfile.ZipFile(p) as z:
                if 'AndroidManifest.xml' not in z.namelist():row['state']='NO_MANIFEST';rows.append(row);continue
            try:
                r=subprocess.run(['aapt','dump','xmltree',str(p),'AndroidManifest.xml'],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=20)
                pkg=re.search(r'A: package="([^"]+)"',r.stdout)
                if not pkg:
                    row.update(state='MANIFEST_PARSE_FAILED',error=r.stderr[:600]);rows.append(row);continue
                row.update(state='MANIFEST_READ',package=pkg.group(1),tool_exit=r.returncode)
                if row['package'] in TARGETS or re.search('HyperPhone|Contacts/|Dialer/|InCall',rel,re.I):
                    row['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
                    folder=OUT/label;folder.mkdir(exist_ok=True)
                    name=re.sub(r'[^A-Za-z0-9_.-]','_',rel)
                    (folder/(name+'.manifest.txt')).write_text(r.stdout+'\n'+r.stderr)
            except Exception as e:row.update(state='READ_FAILED',error=str(e))
            rows.append(row)
        for p in sorted(root.rglob('*')):
            if p.is_symlink() or not p.is_file() or p.suffix not in {'.xml','.rc','.prop','.sh','.json','.txt'}:continue
            if p.stat().st_size>2*1024*1024:continue
            try:lines=p.read_text(errors='replace').splitlines()
            except OSError:continue
            hits=[i for i,l in enumerate(lines) if PATTERN.search(l)]
            if hits:
                selected=sorted({j for i in hits for j in range(max(0,i-2),min(len(lines),i+3))})
                matches.append({'path':str(p.relative_to(root)),
                                'lines':[{'line':j+1,'text':lines[j][:2000]} for j in selected[:250]]})
        report['roots'][label]={'apks':rows,'selection_config_matches':matches}
        print(label+': '+str(len(rows))+' APK, '+str(len(matches))+' yapilandirma dosyasi',flush=True)
    (OUT/'components.json').write_text(json.dumps(report,indent=2)+'\n')
    print('BILESEN INCELEMESI HAZIR. KAYNAKLAR VE TELEFON DEGISTIRILMEDI.',flush=True)
if __name__=='__main__':main()
