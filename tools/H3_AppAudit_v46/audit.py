"""Compare donor and offline ROM APK identities without modifying either."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
PREFIXES=('com.google.android.dialer','com.google.android.contacts',
          'com.google.android.apps.messaging','com.android.contacts',
          'com.android.dialer','com.android.incallui','com.android.mms',
          'com.android.messaging','com.android.server.telecom','com.android.phone',
          'com.xiaomi.phone','com.miui.contacts','com.miui.mms')
def hashfile(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def scan(root):
    if not root.is_dir():raise RuntimeError('Source directory missing: '+str(root))
    rows=[];errors=[]
    for p in sorted(root.rglob('*.apk')):
        if p.is_symlink():
            errors.append(dict(path=str(p.relative_to(root)),error='symlink not followed'));continue
        try:
            r=subprocess.run(['aapt','dump','badging',str(p)],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=20)
            match=re.search(r"^package: name='([^']+)'(?: versionCode='([^']*)')?(?: versionName='([^']*)')?",r.stdout,re.M)
            if r.returncode or not match:raise RuntimeError((r.stderr or 'Missing package identity')[:500])
            pkg,code,version=match.groups()
            item=dict(path=str(p.relative_to(root)),package=pkg,version_code=code,version_name=version,size=p.stat().st_size)
            item['communication_scope']=any(pkg==x or pkg.startswith(x+'.') for x in PREFIXES)
            if item['communication_scope']:item['sha256']=hashfile(p)
            rows.append(item)
        except Exception as e:errors.append(dict(path=str(p.relative_to(root)),error=str(e)))
    if not rows:raise RuntimeError('No APK identities read: '+str(root))
    return dict(root=str(root),apk_count=len(rows),apk_errors=errors,all_apks=rows,
                communication_apks=[r for r in rows if r['communication_scope']])
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--donor',default='/linux/source/creek-tr-3.0.302.0')
    ap.add_argument('--tree',default='/linux/build/hyperos3-ginkgo-v1');ap.add_argument('--out',default='/out/audit-v1')
    a=ap.parse_args();out=Path(a.out)
    if not shutil.which('aapt'):raise RuntimeError('aapt unavailable')
    if out.exists():raise RuntimeError('Output already exists; nothing overwritten')
    donor=scan(Path(a.donor));print('DONOR APK TARAMASI TAMAM: '+str(donor['apk_count']),flush=True)
    tree=scan(Path(a.tree));out.mkdir(parents=True,exist_ok=False)
    donor_hashes={r['sha256'] for r in donor['communication_apks']}
    comparisons=[]
    for p in sorted({r['package'] for r in donor['communication_apks']+tree['communication_apks']}):
        d=[r for r in donor['communication_apks'] if r['package']==p]
        w=[r for r in tree['communication_apks'] if r['package']==p]
        if d and w:
            verdict='DONOR_BYTES_PRESENT' if any(x['sha256']==y['sha256'] for x in d for y in w) else 'PACKAGE_PRESENT_BYTES_DIFFER'
        elif d:verdict='ONLY_IN_DONOR'
        else:verdict='ONLY_IN_WORK_TREE'
        comparisons.append(dict(package=p,result=verdict,donor=d,work_tree=w))
    report=dict(status='COMPLETE' if not donor['apk_errors'] and not tree['apk_errors'] else 'INCOMPLETE_APK_ERRORS',
                donor=donor,work_tree=tree,comparison=comparisons,sources_modified=False,
                limits='Offline installed APK files only; runtime roles, enabled state, userdata updates and overlays must be checked separately. Absence conclusions require error-free inventories.')
    (out/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    summary=['# Donor / work-tree communication APK audit','', 'Status: '+report['status'],'',
             '| Package | Result |','| --- | --- |']
    summary += ['| '+r['package']+' | '+r['result']+' |' for r in comparisons]
    (out/'SUMMARY.md').write_text('\n'.join(summary)+'\n')
    print('\n'.join(summary),flush=True)
    print('KAYNAKLAR VE TELEFON DEGISTIRILMEDI.',flush=True)
if __name__=='__main__':main()
