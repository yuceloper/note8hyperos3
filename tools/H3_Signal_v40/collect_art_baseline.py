"""Read-only V35 ART/boot-image reference collector. No device writes or reboot."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,subprocess,sys,tarfile,tempfile,zipfile
SOURCE='f3c66613c8433783c1b6b8608b7e89721b7a3d9d127ad7e92bf0817f80c7b258'

def sha_file(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def run_adb(adb,serial,args,timeout=15):
    if args[0] not in ('shell','pull'):raise RuntimeError('Read-only adb command required')
    try:
        r=subprocess.run([adb,'-s',serial,*args],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=timeout)
        return {'code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    except subprocess.TimeoutExpired as e:
        def txt(v):return v.decode(errors='replace') if isinstance(v,bytes) else (v or '')
        return {'code':'timeout','stdout':txt(e.stdout),'stderr':txt(e.stderr)}

def inventory(p):
    with zipfile.ZipFile(p) as z:
        dex=[]
        for item in z.infolist():
            if re.fullmatch(r'classes(?:\d+)?\.dex',item.filename):
                with z.open(item) as f:header=f.read(112)
                dex.append({'name':item.filename,'size':item.file_size,'magic_hex':header[:8].hex()})
        return {'sha256':sha_file(p),'size':p.stat().st_size,'entry_count':len(z.infolist()),'dex_entries':dex}

def collect(adb,serial,logs):
    product=run_adb(adb,serial,['shell','getprop','ro.product.device'])
    if product['code']!=0 or product['stdout'].strip()!='ginkgo':raise RuntimeError('Ginkgo device not verified')
    jar=run_adb(adb,serial,['shell','sha256sum','/system/framework/telephony-common.jar'])
    if jar['code']!=0 or not jar['stdout'].split() or jar['stdout'].split()[0]!=SOURCE:raise RuntimeError('Phone must be on original V35 JAR before baseline capture')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    dest=Path(logs)/('signal-v40-art-baseline-'+stamp);dest.mkdir(parents=True,exist_ok=False)
    (dest/'baseline-check.json').write_text(json.dumps({'product':product,'jar':jar},indent=2)+'\n')
    props=['ro.zygote','ro.product.cpu.abilist','ro.product.cpu.abilist32','ro.product.cpu.abilist64',
           'dalvik.vm.boot-image','dalvik.vm.dex2oat64.enabled','dalvik.vm.isa.arm.variant',
           'dalvik.vm.isa.arm.features','dalvik.vm.isa.arm64.variant','dalvik.vm.dex2oat-filter',
           'dalvik.vm.image-dex2oat-filter','dalvik.vm.usejit','sys.boot_completed']
    jobs=[('properties',['shell','\n'.join('echo '+p+'; getprop '+p for p in props)]),
          ('classpath',['shell','printenv BOOTCLASSPATH DEX2OATBOOTCLASSPATH SYSTEMSERVERCLASSPATH']),
          ('boot-images',['shell', '''for d in /apex/com.android.art/javalib/arm /apex/com.android.art/javalib/arm64 /system/framework/arm /system/framework/arm64; do
 echo "=== $d ==="
 ls -ldZ "$d"
 ls -lZ "$d"/boot*.art "$d"/boot*.oat "$d"/boot*.vdex 2>&1
done''']),
          ('art-tools',['shell','ls -lZ /apex/com.android.art/bin/odrefresh /apex/com.android.art/bin/dex2oat32 /apex/com.android.art/bin/dex2oat64']),
          ('current-phone',['shell','cat /proc/uptime; pidof com.android.phone']),
          ('crash',['shell','logcat -b crash -d -t 100'])]
    summary={'status':'READ_ONLY_V35_ART_BASELINE','commands':{},'core_jars':{}}
    for name,args in jobs:
        print('OKUNUYOR: '+name,flush=True);r=run_adb(adb,serial,args)
        (dest/(name+'.txt')).write_text(r['stdout']+'\n'+r['stderr'])
        summary['commands'][name]=r['code']
    print('OKUNUYOR: filtrelenmis ART kayitlari',flush=True)
    r=run_adb(adb,serial,['shell','logcat -b all -d -t 30000'],timeout=20)
    pattern=re.compile(r'odrefresh|odsign|dex2oat|ClassLinker|ImageSpace|OatFileAssistant|boot image|bootclasspath|InitWithoutImage',re.I)
    selected=[l for l in (r['stdout']+'\n'+r['stderr']).splitlines() if pattern.search(l)]
    (dest/'art-log.txt').write_text('\n'.join(selected[-1500:])+'\n')
    summary['commands']['art-log']=r['code']
    with tempfile.TemporaryDirectory(prefix='ginkgo-art-reference-') as temporary:
        for name in ['core-oj.jar','core-libart.jar']:
            print('INCELENIYOR: '+name,flush=True)
            p=Path(temporary)/name
            r=run_adb(adb,serial,['pull','/apex/com.android.art/javalib/'+name,str(p)],timeout=25)
            if r['code']==0 and p.is_file():
                try:summary['core_jars'][name]=inventory(p)
                except Exception as e:summary['core_jars'][name]={'error':repr(e)}
            else:summary['core_jars'][name]={'error':r}
    (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    archive=Path(str(dest)+'.tar.gz')
    with tarfile.open(archive,'w:gz') as t:
        for p in sorted(dest.iterdir()):t.add(p,arcname=dest.name+'/'+p.name,recursive=False)
    print('PAKET: '+str(archive.resolve()),flush=True)
    print('TELEFONA YAZMA, DERLEME, REBOOT VEYA FLASH YAPILMADI.',flush=True)
    return archive

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--adb',default='adb');ap.add_argument('--serial',default='12da33e7')
    ap.add_argument('--logs',default='logs');ap.add_argument('--reveal',action='store_true');a=ap.parse_args()
    archive=collect(a.adb,a.serial,a.logs)
    if a.reveal and sys.platform=='darwin':subprocess.run(['open','-R',str(archive.resolve())],stdin=subprocess.DEVNULL,check=True)
if __name__=='__main__':main()
