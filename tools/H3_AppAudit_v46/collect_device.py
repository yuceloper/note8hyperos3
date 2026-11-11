"""Collect app origin/role evidence only; never change defaults or uninstall apps."""
from pathlib import Path
import datetime,json,subprocess,tarfile,sys
def main():
    source=Path('out/app-audit-v46/audit-v1')
    if not (source/'audit.json').is_file():raise RuntimeError('Run offline APK audit first')
    dest=Path('logs')/('app-origin-v46-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    dest.mkdir(parents=True,exist_ok=False)
    commands={
        'all-packages':['shell','pm','list','packages','-f','-u'],
        'disabled-packages':['shell','pm','list','packages','-d'],
        'dialer-role':['shell','cmd','role','get-role-holders','android.app.role.DIALER'],
        'sms-role':['shell','cmd','role','get-role-holders','android.app.role.SMS'],
        'overlays':['shell','cmd','overlay','list'],
    }
    for pkg in ['com.google.android.dialer','com.google.android.contacts','com.google.android.apps.messaging',
                'com.android.contacts','com.android.incallui','com.android.mms','com.xiaomi.phone']:
        commands[pkg]=['shell','dumpsys','package',pkg]
    results={}
    for name,args in commands.items():
        try:
            r=subprocess.run(['adb','-s','12da33e7',*args],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=25)
            (dest/(name+'.txt')).write_text(r.stdout+'\n'+r.stderr);results[name]=r.returncode
        except subprocess.TimeoutExpired:results[name]='timeout'
    for filename in ['audit.json','SUMMARY.md']:(dest/filename).write_bytes((source/filename).read_bytes())
    (dest/'collection.json').write_text(json.dumps({'commands':results,'device_modified':False},indent=2)+'\n')
    archive=Path(str(dest)+'.tar.gz')
    with tarfile.open(archive,'w:gz') as t:t.add(dest,arcname=dest.name)
    print('PAKET: '+str(archive.resolve()))
    if sys.platform=='darwin':subprocess.run(['open','-R',str(archive.resolve())],stdin=subprocess.DEVNULL)
if __name__=='__main__':main()
