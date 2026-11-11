"""Run isolated synthetic signal conversion; never replace system code or reboot."""
from pathlib import Path
import argparse,datetime,hashlib,json,subprocess,sys,tarfile
SOURCE='f3c66613c8433783c1b6b8608b7e89721b7a3d9d127ad7e92bf0817f80c7b258'
INPUTS={'v39':'452faaae8d36ac59f4f6b7830ea4fd126b878678f377e79e8184568f40a33300',
        'v40':'1279a5eb44e5a0ff6ca32943af7b7b31f793c668adff9c1849ff146c3f9fe5a0'}
MARKERS=['V39_NEGATIVE_CONTROL_OK:','V40_V1_2_OK:','V40_V1_0_OK:','PROBE_ALL_OK']
def run(adb,serial,args,timeout=15):
    try:
        r=subprocess.run([adb,'-s',serial,*args],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=timeout)
        return {'code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    except subprocess.TimeoutExpired as e:
        def text(v):return v.decode(errors='replace') if isinstance(v,bytes) else (v or '')
        return {'code':'timeout','stdout':text(e.stdout),'stderr':text(e.stderr)}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--probe',default='out/signal-v42/probe-v1/signal-conversion-probe.jar')
    ap.add_argument('--adb',default='adb');ap.add_argument('--serial',default='12da33e7');ap.add_argument('--reveal',action='store_true');a=ap.parse_args()
    probe=Path(a.probe);validation=json.loads(probe.with_name('validation.json').read_text())
    h=hashlib.sha256(probe.read_bytes()).hexdigest()
    if validation.get('status')!='ISOLATED_PROBE_BUILT_NOT_RUN' or validation.get('probe_sha256')!=h:
        raise RuntimeError('Probe manifest/hash mismatch')
    for version,wanted in INPUTS.items():
        if validation.get('inputs',{}).get(version,{}).get('jar_sha256')!=wanted:raise RuntimeError('Wrong converter input')
    def adb(args,timeout=15):return run(a.adb,a.serial,args,timeout)
    product=adb(['shell','getprop','ro.product.device'])
    baseline=adb(['shell','sha256sum','/system/framework/telephony-common.jar'])
    before=adb(['shell','pidof','com.android.phone'])
    if product['code']!=0 or product['stdout'].strip()!='ginkgo':raise RuntimeError('Ginkgo not verified')
    if baseline['code']!=0 or not baseline['stdout'].split() or baseline['stdout'].split()[0]!=SOURCE:
        raise RuntimeError('Working V35/V41 telephony baseline required')
    if before['code']!=0 or not before['stdout'].strip():raise RuntimeError('Phone service must be running')
    name='ginkgo-signal-probe-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    remote='/data/local/tmp/'+name;dest=Path('logs')/name;dest.mkdir(parents=True,exist_ok=False)
    steps=[]
    for args in [['shell','mkdir',remote],['push',str(probe),remote+'/probe.jar'],['shell','chmod','0444',remote+'/probe.jar']]:
        r=adb(args);steps.append({'args':args,'result':r})
        if r['code']!=0:
            (dest/'setup-failure.json').write_text(json.dumps(steps,indent=2)+'\n')
            raise RuntimeError('Probe setup failed; see '+str(dest))
    print('IZOLE TEST CALISIYOR; TELEFON SERVISI DEGISTIRILMIYOR...',flush=True)
    command=f'CLASSPATH={remote}/probe.jar /system/bin/app_process64 /system/bin --nice-name=ginkgo-signal-probe com.ginkgo.signalprobe.Main'
    result=adb(['shell',command],timeout=45)
    after=adb(['shell','pidof','com.android.phone'])
    output=result['stdout']+'\n'+result['stderr'];(dest/'runtime.txt').write_text(output)
    markers={m:m in result['stdout'] for m in MARKERS}
    passed=result['code']==0 and all(markers.values())
    unchanged=after['code']==0 and after['stdout'].strip()==before['stdout'].strip()
    report={'status':'ISOLATED_CONVERSION_PASSED' if passed and unchanged else 'REVIEW_REQUIRED',
        'probe_sha256':h,'returncode':result['code'],'markers':markers,'phone_pid_unchanged':unchanged,
        'before':before,'after':after,'setup':steps,'remote_probe_directory':remote,
        'system_files_replaced':False,'radio_configuration_changed':False,'rebooted':False,
        'limitations':'Synthetic converter payloads only; no system/binder/modem signal fix installation'}
    (dest/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    archive=Path(str(dest)+'.tar.gz')
    with tarfile.open(archive,'w:gz') as t:
        for p in sorted(dest.iterdir()):t.add(p,arcname=dest.name+'/'+p.name,recursive=False)
    print('\n'.join(output.splitlines()[-100:]))
    print('SONUC: '+report['status']);print('TELEFON PID AYNI: '+str(unchanged));print('PAKET: '+str(archive.resolve()))
    if a.reveal and sys.platform=='darwin':subprocess.run(['open','-R',str(archive.resolve())],stdin=subprocess.DEVNULL,check=True)
    if not passed or not unchanged:raise SystemExit(1)
if __name__=='__main__':main()
