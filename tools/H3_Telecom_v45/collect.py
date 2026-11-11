"""Record the beginning of a user-initiated incoming call; read-only diagnostics."""
from pathlib import Path
import datetime,json,subprocess,sys,tarfile,time
SERIAL='12da33e7'
def adb(*args):
    try:
        r=subprocess.run(['adb','-s',SERIAL,*args],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=20)
        return dict(code=r.returncode,stdout=r.stdout,stderr=r.stderr)
    except subprocess.TimeoutExpired:
        return dict(code='timeout',stdout='',stderr='ADB timeout')
def main():
    state=adb('get-state')
    if state['code']!=0 or state['stdout'].strip()!='device':raise RuntimeError('ADB device unavailable')
    dest=Path('logs')/('incoming-ui-v45-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    dest.mkdir(parents=True,exist_ok=False)
    def save(name,*args):
        r=adb(*args);(dest/name).write_text(r['stdout']+'\n'+r['stderr']);return r
    report={'scope':'Read-only 60-second incoming-call capture; no test call is placed by script',
            'device_changed':False,'resources':{}}
    for name in ['ui_default_package','ui_default_package_dialer','incall_default_class','dialer_default_package']:
        r=adb('shell','cmd','overlay','lookup','--verbose','com.android.server.telecom','com.android.server.telecom:string/'+name)
        report['resources'][name]=r
    save('dialer-package.txt','shell','dumpsys','package','com.google.android.dialer')
    save('telecom-before.txt','shell','dumpsys','telecom')
    save('appops.txt','shell','cmd','appops','get','com.google.android.dialer')
    save('notifications-before.txt','shell','dumpsys','notification')
    process=None
    try:
        with (dest/'live-logcat.txt').open('wb') as log:
            process=subprocess.Popen(['adb','-s',SERIAL,'logcat','-b','all','-v','threadtime','-T','1'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            print('KAYIT BASLADI. Telefonu kilitle; baska bir telefondan normal arama yap.',flush=True)
            print('Arama ekranini izle; acil numara arama. Kayit 60 saniye surecek.',flush=True)
            for n in range(6):
                time.sleep(10)
                if process.poll() is not None:
                    report['capture_ended_early']=process.returncode;break
                print(f'Kayit: {(n+1)*10}/60 saniye',flush=True)
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        save('telecom-after.txt','shell','dumpsys','telecom')
        save('activities.txt','shell','dumpsys','activity','activities')
        (dest/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
        archive=Path(str(dest)+'.tar.gz')
        with tarfile.open(archive,'w:gz') as t:t.add(dest,arcname=dest.name)
        print('PAKET: '+str(archive.resolve()),flush=True)
        if sys.platform=='darwin':subprocess.run(['open','-R',str(archive.resolve())],stdin=subprocess.DEVNULL)
if __name__=='__main__':main()
