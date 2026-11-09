#!/usr/bin/env python3
"""One explicitly requested reboot, followed by bounded read-only boot telemetry."""
import argparse
import json
import re
import subprocess
import tarfile
import time
from datetime import datetime
from pathlib import Path

BASIC=r'''
echo ===uptime
cat /proc/uptime
echo ===boot_id
cat /proc/sys/kernel/random/boot_id
echo ===boot_completed
getprop sys.boot_completed
echo ===sim
getprop gsm.sim.state
echo ===operator
getprop gsm.operator.alpha
echo ===network_type
getprop gsm.network.type
echo ===phone_pid
pidof com.android.phone
echo ===system_server_pid
pidof system_server
echo ===cpu
head -n 1 /proc/stat
echo ===memory
cat /proc/meminfo
echo ===pressure_cpu
cat /proc/pressure/cpu 2>/dev/null
echo ===pressure_memory
cat /proc/pressure/memory 2>/dev/null
echo ===pressure_io
cat /proc/pressure/io 2>/dev/null
echo ===vmstat
cat /proc/vmstat
'''

def sections(text):
    result={};key=None
    for line in text.splitlines():
        if line.startswith('==='):key=line[3:];result[key]=[]
        elif key is not None:result[key].append(line)
    return {k:'\n'.join(v).strip() for k,v in result.items()}

def cpu_ticks(text):
    fields=text.split()
    if not fields or fields[0]!='cpu' or len(fields)<5:return None
    try:
        values=list(map(int,fields[1:9]));return (sum(values),values[3]+(values[4] if len(values)>4 else 0))
    except ValueError:return None

def busy_percent(previous,current):
    if previous is None or current is None:return None
    total=current[0]-previous[0];idle=current[1]-previous[1]
    if total<=0 or not 0<=idle<=total:return None
    return round(100*(total-idle)/total,2)

def registration(text):
    # Avoid storing subscription IDs/cell identity from the registry dump.
    result=[]
    for line in text.splitlines():
        if 'mServiceState=' in line:
            result.append({k:re.findall(k+r'=([^,}]+)',line) for k in ('mVoiceRegState','mDataRegState','getRilVoiceRadioTechnology','getRilDataRadioTechnology')})
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--serial',default='12da33e7')
    parser.add_argument('--seconds',type=int,default=180)
    parser.add_argument('--reboot',action='store_true',help='Required: reboot the connected ginkgo exactly once')
    args=parser.parse_args()
    if not args.reboot:raise SystemExit('Use --reboot to explicitly request one reboot and collection')
    if not 30<=args.seconds<=600:raise SystemExit('Collection duration must be 30..600 seconds')
    if not Path('tools/H3_Boot_v37').is_dir():raise SystemExit('Run from note8hyperos3 repo root')
    prefix=['adb','-s',args.serial]
    def call(*cmd,timeout=10):
        return subprocess.run(prefix+list(cmd),stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=timeout)
    def required(*cmd):
        r=call(*cmd)
        if r.returncode:raise RuntimeError(r.stderr.strip() or 'ADB command failed')
        return r.stdout.strip()
    if required('shell','getprop','ro.product.device')!='ginkgo':raise SystemExit('Refusing unexpected device')
    old_id=required('shell','cat','/proc/sys/kernel/random/boot_id')
    if not re.fullmatch(r'[0-9a-fA-F-]{36}',old_id):raise SystemExit('Boot ID unreadable; no reboot performed')
    dest=Path('logs')/('v37-boot-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    dest.mkdir(parents=True,exist_ok=False)
    def save(name,r):
        (dest/name).write_text(r.stdout+'\n=== stderr ===\n'+r.stderr+'\n=== exit ===\n'+str(r.returncode)+'\n')
    save('preflight.txt',call('shell','getprop ro.build.fingerprint; getprop ro.vendor.build.fingerprint; pm path com.android.camera; sha256sum /product/priv-app/MiuiCamera/MiuiCamera.apk; dumpsys battery'))
    # Use a single shell-script argument to adb shell, which joins its arguments.
    # No commands after reboot change device state.
    events=[]
    def event(kind,**data):events.append(dict(kind=kind,host_utc=datetime.utcnow().isoformat()+'Z',**data))
    print('Telefon bir kez yeniden baslatiliyor. SIM PIN ve ekran kilidini normal hizinda gir.',flush=True)
    try:
        reboot=call('reboot');save('reboot-command.txt',reboot);event('reboot_requested',exit_code=reboot.returncode)
    except subprocess.TimeoutExpired:
        event('reboot_command_timeout')
    begin=time.monotonic();new_id=None;stream=None;logfile=None
    try:
        print('Yeni acilisin ADB baglantisi bekleniyor...',flush=True)
        while time.monotonic()-begin<120:
            try:
                r=call('shell','cat','/proc/sys/kernel/random/boot_id',timeout=4)
                value=r.stdout.strip()
                if r.returncode==0 and re.fullmatch(r'[0-9a-fA-F-]{36}',value) and value!=old_id:
                    new_id=value;break
            except subprocess.TimeoutExpired:pass
            time.sleep(1)
        if new_id is None:raise RuntimeError('New boot not observed within 120s; no second reboot attempted')
        event('new_boot_adb_available',seconds_since_request=round(time.monotonic()-begin,2),boot_id=new_id)
        print('Kayit basladi. Kamera veya agir uygulama acma; PIN ve kilidi normal sekilde ac.',flush=True)
        logfile=(dest/'logcat.txt').open('ab')
        def start_stream():
            return subprocess.Popen(prefix+['logcat','-b','all','-v','threadtime'],stdin=subprocess.DEVNULL,stdout=logfile,stderr=subprocess.STDOUT)
        stream=start_stream();start=time.monotonic();last_heavy=-100;last_print=-100;previous=None;samples=[]
        with (dest/'timeline.jsonl').open('w') as timeline:
            while time.monotonic()-start<args.seconds:
                tick=time.monotonic();elapsed=round(tick-start,2)
                if stream.poll() is not None:
                    event('logcat_stream_exited',exit_code=stream.returncode);stream=start_stream()
                try:
                    r=call('shell',BASIC,timeout=7)
                    sample=dict(host_elapsed=elapsed,exit_code=r.returncode,fields=sections(r.stdout),stderr=r.stderr)
                    fields=sample['fields']
                    if fields.get('boot_id') and fields['boot_id']!=new_id:
                        event('unexpected_reboot');raise RuntimeError('Unexpected additional reboot observed')
                    current=cpu_ticks(fields.get('cpu',''));sample['cpu_busy_percent']=busy_percent(previous,current);previous=current
                    samples.append(sample);timeline.write(json.dumps(sample)+'\n');timeline.flush()
                except subprocess.TimeoutExpired:
                    event('sample_timeout',elapsed=elapsed)
                if elapsed-last_heavy>=15:
                    last_heavy=elapsed
                    for name,command in [('registration','dumpsys telephony.registry'),('top','top -b -n 2 -d 1 -m 15')]:
                        try:
                            r=call('shell',command,timeout=7)
                            if name=='registration':
                                with (dest/'registration.jsonl').open('a') as f:f.write(json.dumps(dict(host_elapsed=round(time.monotonic()-start,2),states=registration(r.stdout),exit_code=r.returncode,stderr=r.stderr))+'\n')
                            else:save('top-%03d.txt'%int(elapsed),r)
                        except subprocess.TimeoutExpired:event(name+'_timeout',elapsed=elapsed)
                if elapsed-last_print>=15:
                    last_print=elapsed;fields=samples[-1]['fields'] if samples else {}
                    print('%3ds | uptime=%s | boot=%s | SIM=%s'%(int(elapsed),fields.get('uptime','?').split(' ')[0],fields.get('boot_completed','?'),fields.get('sim','?')),flush=True)
                time.sleep(max(0,5-(time.monotonic()-tick)))
        summary={}
        for field in ('sim','boot_completed','operator','network_type','phone_pid','system_server_pid'):
            changes=[];last=None
            for sample in samples:
                value=sample['fields'].get(field,'')
                if value!=last:
                    changes.append(dict(host_elapsed=sample['host_elapsed'],device_uptime=sample['fields'].get('uptime'),value=value));last=value
            summary[field]=changes
        summary['note']='First observed state only; early boot before ADB and exact PIN entry time are not measured. Operator label alone does not prove service.'
        (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        event('collection_completed',samples=len(samples))
    except (Exception,KeyboardInterrupt) as e:
        event('collection_incomplete',reason=str(e));print('Kayit tamamlanamadi:',str(e),flush=True)
    finally:
        if stream is not None and stream.poll() is None:
            stream.terminate()
            try:stream.wait(timeout=5)
            except subprocess.TimeoutExpired:stream.kill();stream.wait()
        if logfile is not None:logfile.close()
        (dest/'events.json').write_text(json.dumps(events,indent=2)+'\n')
        archive=Path(str(dest)+'.tar.gz')
        with tarfile.open(archive,'w:gz') as tar:tar.add(dest,arcname=dest.name)
        print('PAKET:',archive.resolve(),flush=True)
        print('Ayar/izin degistirilmedi. Flash veya veri silme yapilmadi.',flush=True)
        subprocess.run(['open','-R',str(archive)],stdin=subprocess.DEVNULL,check=False)

if __name__=='__main__':main()
