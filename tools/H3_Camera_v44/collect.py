"""Capture two fresh camera process launches on V43; no ROM/settings changes."""
from pathlib import Path
import argparse, datetime, json, subprocess, sys, tarfile, time

SERIAL='12da33e7'
JAR='1279a5eb44e5a0ff6ca32943af7b7b31f793c668adff9c1849ff146c3f9fe5a0'
APK='a316586185bfa320d9c888667bf044d7ab835004b759a5f1b009c931d52bbeaa'

def run(args,timeout=20):
    try:
        r=subprocess.run(['adb','-s',SERIAL,*args],stdin=subprocess.DEVNULL,
                         capture_output=True,text=True,timeout=timeout)
        return dict(code=r.returncode,stdout=r.stdout,stderr=r.stderr)
    except subprocess.TimeoutExpired as e:
        def text(v):return v.decode(errors='replace') if isinstance(v,bytes) else (v or '')
        return dict(code='timeout',stdout=text(e.stdout),stderr=text(e.stderr))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--reveal',action='store_true');a=ap.parse_args()
    device=run(['shell','getprop','ro.product.device'])
    jar=run(['shell','sha256sum','/system/framework/telephony-common.jar'])
    apk=run(['shell','sha256sum','/product/priv-app/MiuiCamera/MiuiCamera.apk'])
    path=run(['shell','pm','path','com.android.camera'])
    if (device['code']!=0 or device['stdout'].strip()!='ginkgo' or
        jar['code']!=0 or jar['stdout'].split()[:1]!=[JAR] or
        apk['code']!=0 or apk['stdout'].split()[:1]!=[APK] or
        path['code']!=0 or path['stdout'].strip()!='package:/product/priv-app/MiuiCamera/MiuiCamera.apk'):
        raise RuntimeError('V43/system camera baseline not verified; camera not stopped')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    dest=Path('logs')/('camera-v44-'+stamp);dest.mkdir(parents=True,exist_ok=False)
    records={'baseline':dict(device=device,jar=jar,apk=apk,path=path),'attempts':[],
             'scope':'Two force-stops/launches of camera only; read diagnostic logs',
             'system_files_replaced':False,'settings_changed':False,'rebooted':False}
    def save(name,args,timeout=20):
        r=run(args,timeout);(dest/name).write_text(r['stdout']+'\n'+r['stderr'])
        return r
    # Avoid clearing the existing buffers: use the device's timestamp as a boundary.
    start=run(['shell',"date '+%m-%d %H:%M:%S.000'"])
    if start['code']!=0 or not start['stdout'].strip():raise RuntimeError('Device clock unavailable')
    start=start['stdout'].strip();records['device_start']=start
    try:
        save('camera-before.txt',['shell','dumpsys','media.camera'])
        for attempt in [1,2]:
            print(f'KAMERA DENEMESI {attempt}/2: ekrani izle; cekim yapma.',flush=True)
            stop=run(['shell','am','force-stop','com.android.camera'])
            if stop['code']!=0:raise RuntimeError('Camera force-stop failed')
            time.sleep(2)
            launched=save(f'launch-{attempt}.txt',['shell','am','start','-W','-n','com.android.camera/com.android.camera.Camera'])
            time.sleep(8)
            pid=save(f'pid-{attempt}.txt',['shell','pidof','com.android.camera'])
            save(f'camera-after-{attempt}.txt',['shell','dumpsys','media.camera'])
            records['attempts'].append(dict(attempt=attempt,stop=stop,launch=launched,pid=pid))
    except Exception as e:
        records['collection_error']=repr(e)
    finally:
        save('logcat.txt',['logcat','-b','all','-d','-v','threadtime','-T',start],45)
        save('crash.txt',['logcat','-b','crash','-d','-v','threadtime','-T',start])
        save('camera-package.txt',['shell','dumpsys','package','com.android.camera'])
        (dest/'validation.json').write_text(json.dumps(records,indent=2)+'\n')
        archive=Path(str(dest)+'.tar.gz')
        with tarfile.open(archive,'w:gz') as t:t.add(dest,arcname=dest.name)
        print('PAKET: '+str(archive.resolve()),flush=True)
        print('SONUC KAYDEDILDI; KAMERA BASARISI LOG/GOZLEM ILE DEGERLENDIRILECEK.',flush=True)
        if a.reveal and sys.platform=='darwin':subprocess.run(['open','-R',str(archive.resolve())],stdin=subprocess.DEVNULL)
    if 'collection_error' in records:raise SystemExit(1)

if __name__=='__main__':main()
