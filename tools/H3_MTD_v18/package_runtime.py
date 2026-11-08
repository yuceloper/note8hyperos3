"""Verify and package the offline single-attempt MTD diagnostic tree. Never flash a device."""
from pathlib import Path
import hashlib
import json
import os
import stat
import subprocess
import xml.etree.ElementTree as ET

TREE=Path('/linux/build/hyperos3-ginkgo-v1')
BUNDLE=Path('/reference/mtd-bundle-v16/bundle-v1')
OUT=Path('/result')
IMAGE=OUT/'hyperos3-ginkgo-v18-padded.img'
TEMP=OUT/'hyperos3-ginkgo-v18.building.img'
SIZE=8589934592
POLICY='25d23c25a5d8ee9af92554d323f5ebc0b8161bf36e4b6caae8388bacd7db6781'
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
if IMAGE.exists() or TEMP.exists():raise RuntimeError('Output exists; nothing overwritten')
manifest=json.loads((BUNDLE/'validation.json').read_text())
if len(manifest['files'])!=59:raise RuntimeError('Unexpected bundle')
for item in manifest['files']:
    rel=Path(item['path'])
    if rel.is_absolute() or '..' in rel.parts:raise RuntimeError('Invalid bundle path')
    p=TREE/rel
    if p.is_symlink() or digest(p)!=item['sha256']:raise RuntimeError('Installed ELF hash mismatch: '+str(p))
    st=p.stat();context=os.getxattr(p,'security.selinux').rstrip(b'\0').decode()
    if (st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode),context)!=(item['uid'],item['gid'],int(item['mode'],8),item['selinux']):
        raise RuntimeError('Installed metadata mismatch: '+str(p))
rc=TREE/'system_ext/etc/init/ginkgo-mtd-v16.rc'
expected_rc=(BUNDLE/'root/system_ext/etc/init/ginkgo-mtd-v16.rc').read_bytes()+b'\n# One start attempt after Android finishes booting; no restart loop.\non property:sys.boot_completed=1\n    start ginkgo-mtd\n'
if rc.read_bytes()!=expected_rc:raise RuntimeError('V18 single-attempt service changed')
if '    disabled\n' not in rc.read_text() or '    oneshot\n' not in rc.read_text():raise RuntimeError('Service not disabled/oneshot')
xml=ET.parse(TREE/'system_ext/etc/vintf/manifest/ginkgo-mtd-v16.xml').getroot()
if xml.get('type')!='framework' or xml.findtext('hal/name')!='vendor.xiaomi.hardware.mtdservice':raise RuntimeError('VINTF mismatch')
if os.readlink(TREE/'odm/etc/vintf')!='/vendor/odm/etc/vintf':raise RuntimeError('ODM VINTF link changed')
if digest(TREE/'odm/etc/selinux/precompiled_sepolicy')!=POLICY:raise RuntimeError('Policy mismatch')
for name,addition in [('odm_file_contexts','file_contexts.append'),('odm_hwservice_contexts','hwservice_contexts.append')]:
    actual=(TREE/'odm/etc/selinux'/name).read_bytes()
    for line in (BUNDLE/'review'/addition).read_bytes().splitlines():
        if actual.splitlines().count(line)!=1:raise RuntimeError('Missing/duplicate MTD context')
print('V18 DOSYA, METADATA, TEK BASLATMA TANIMI VE POLITIKA KONTROLLERI BASARILI',flush=True)
subprocess.run(['mkfs.erofs','-zlz4hc,9','-b','4096',str(TEMP),str(TREE)],check=True,stdin=subprocess.DEVNULL)
subprocess.run(['fsck.erofs','--extract',str(TEMP)],check=True,stdin=subprocess.DEVNULL)
actual=TEMP.stat().st_size
if actual>SIZE:raise RuntimeError('Image exceeds system partition')
with TEMP.open('r+b') as f:f.truncate(SIZE)
TEMP.rename(IMAGE)
result={'status':'PACKAGED_SINGLE_ATTEMPT_MTD_NOT_FLASHED','image':IMAGE.name,'erofs_size':actual,'padded_size':SIZE,'sha256':digest(IMAGE),'policy_sha256':POLICY,'automatic_mtd_start':True,'restart_after_exit':False,'boot_tested':False}
(OUT/'hyperos3-ginkgo-v18-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('EROFS boyutu: %.3f GiB'%(actual/1024**3))
print('SHA256:',result['sha256'])
print('V18 TANI IMAJI HAZIR. MTD ACILIS SONUNDA BIR KEZ BASLATILACAK. TELEFONA YAZILMADI.')
