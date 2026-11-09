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
IMAGE=OUT/'hyperos3-ginkgo-v32-padded.img'
TEMP=OUT/'hyperos3-ginkgo-v32.building.img'
SIZE=8589934592
validation_path=Path('/reference/mtd-policy-v22/policy-v1/validation.json')
validation=json.loads(validation_path.read_text())
if validation.get('status')!='OFFLINE_INSTALLED_NOT_BOOT_TESTED' or validation.get('previous_policy_sha256')!='64081298a7cbc6e7ac0a2e1c8d0f33491810f249ba92de6a3dc772caeb3a0c6b':
    raise RuntimeError('V22 build validation mismatch')
POLICY=validation['policy_sha256']
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
if IMAGE.exists() or TEMP.exists():raise RuntimeError('Output exists; nothing overwritten')
if digest(Path('/reference/mtd-policy-v22/policy-v1/mtd-v22.policy'))!=POLICY:raise RuntimeError('V22 candidate policy hash mismatch')
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
expected_rc=expected_rc.replace(b'    start ginkgo-mtd\n',b'    restorecon_recursive /mnt/vendor/persist/fdsd\n    start ginkgo-mtd\n')
if digest(rc)!=validation['rc_sha256']:raise RuntimeError('V22 init hash mismatch')
if digest(TREE/'odm/etc/selinux/odm_file_contexts')!=validation['file_contexts_sha256']:raise RuntimeError('V22 file contexts hash mismatch')
if rc.read_bytes()!=expected_rc:raise RuntimeError('V22 single-attempt service changed')
if '    disabled\n' not in rc.read_text() or '    oneshot\n' not in rc.read_text():raise RuntimeError('Service not disabled/oneshot')
xml=ET.parse(TREE/'system_ext/etc/vintf/manifest/ginkgo-mtd-v16.xml').getroot()
if xml.get('type')!='framework' or xml.findtext('hal/name')!='vendor.xiaomi.hardware.mtdservice':raise RuntimeError('VINTF mismatch')
if os.readlink(TREE/'odm/etc/vintf')!='/vendor/odm/etc/vintf':raise RuntimeError('ODM VINTF link changed')
if digest(TREE/'odm/etc/selinux/precompiled_sepolicy')!=POLICY:raise RuntimeError('Policy mismatch')
for name,addition in [('odm_file_contexts','file_contexts.append'),('odm_hwservice_contexts','hwservice_contexts.append')]:
    actual=(TREE/'odm/etc/selinux'/name).read_bytes()
    for line in (BUNDLE/'review'/addition).read_bytes().splitlines():
        if actual.splitlines().count(line)!=1:raise RuntimeError('Missing/duplicate MTD context')
zram=json.loads(Path('/reference/zram-v23/validation.json').read_text())
if zram.get('status')!='OFFLINE_PREPARED_NOT_BOOT_TESTED' or zram.get('original_sha256')!='58b56ede847e23afa20e0970ff421f1ab729cfccfd99b01619a58f4e4ae9f1a8':raise RuntimeError('V23 preparation mismatch')
if digest(TREE/'system_ext/etc/init/perfservice.rc')!=zram['candidate_sha256']:raise RuntimeError('V23 perfservice candidate mismatch')
if POLICY!=zram['policy_sha256']:raise RuntimeError('V23 policy changed')
diag=json.loads(Path('/reference/initdiag-v25/validation.json').read_text())
if diag.get('status')!='OFFLINE_PREPARED_NOT_BOOT_TESTED' or diag.get('original_sha256')!='cc02a2de9ad490e64de3d271db7352e530069bebde591f64e45027ea53650d6a':raise RuntimeError('V25 preparation mismatch')
if digest(TREE/'system/etc/init/hw/init.rc')!=diag['candidate_sha256'] or POLICY!=diag['policy_sha256']:raise RuntimeError('V25 candidate mismatch')

if (TREE/'product/app/GinkgoANXTest').exists() or (TREE/'product/etc/sysconfig/ginkgo-anx-test-hiddenapi.xml').exists():
    raise RuntimeError('ANX tree additions still present')
camera = json.loads(Path('/reference/camera-v32/validation.json').read_text())
if camera.get('status') != 'OFFLINE_WORKING_CAMERA_V31_SYNCED_NOT_BOOT_TESTED' or camera.get('package') != 'com.ginkgo.micamera6test':
    raise RuntimeError('V32 camera preparation mismatch')
if camera.get('apk_sha256') != '815f14e8419f55f23dfa58e796c7462c813a941417455e1d3e17cf7d2eba1186':
    raise RuntimeError('V32 APK baseline mismatch')
expected_apk = 'product/app/GinkgoMiCamera6Test/MiuiCamera.apk'
expected_config = 'product/etc/sysconfig/ginkgo-micamera6-test-hiddenapi.xml'
expected_paths = {expected_apk, expected_config}
items = camera['files']
for item in items:
    rel = Path(item['path'])
    if rel.is_absolute() or '..' in rel.parts:
        raise RuntimeError('Invalid camera path')
    if str(rel) not in (expected_apk, expected_config):
        if rel.parent != Path('product/app/GinkgoMiCamera6Test/lib/arm64') or rel.suffix != '.so' or rel.name == 'libcameraservice.so':
            raise RuntimeError('Unexpected camera file')
        expected_paths.add(str(rel))
    p = TREE / rel
    st = p.stat()
    if p.is_symlink() or digest(p) != item['sha256']:
        raise RuntimeError('Camera file hash mismatch')
    if (st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode)) != (0, 0, 0o644):
        raise RuntimeError('Camera metadata mismatch')
    if os.getxattr(p, 'security.selinux').rstrip(b'\0').decode() != item['selinux']:
        raise RuntimeError('Camera label mismatch')
if len(items) != 44 or len(expected_paths) != 44 or len({i['path'] for i in items}) != 44:
    raise RuntimeError('Camera file count mismatch')
actual_paths = {str(p.relative_to(TREE)) for p in (TREE/'product/app/GinkgoMiCamera6Test').rglob('*') if p.is_file()}
if actual_paths != expected_paths - {expected_config}:
    raise RuntimeError('Unexpected camera app contents')
if digest(TREE/expected_apk) != camera['apk_sha256'] or camera['policy_sha256'] != POLICY:
    raise RuntimeError('Camera APK/policy mismatch')
if digest(TREE/'product/priv-app/MiuiCamera/MiuiCamera.apk') != '48a12d13da98f2e683b185476b9a5516251bcef80fe19aec0ecfde22876d51c5':
    raise RuntimeError('Original camera changed')
cfg = ET.parse(TREE/expected_config).getroot()
if cfg.tag != 'config' or len(cfg) != 1 or cfg[0].tag != 'hidden-api-whitelisted-app' or cfg[0].attrib != {'package':'com.ginkgo.micamera6test'}:
    raise RuntimeError('Hidden API exception scope mismatch')
print('V32 AYRI KAMERA APK, KUTUPHANE VE PAKETE OZEL IZIN KONTROLLERI BASARILI', flush=True)

print('V25 DOSYA, METADATA, TEK BASLATMA TANIMI VE POLITIKA KONTROLLERI BASARILI',flush=True)
subprocess.run(['mkfs.erofs','-zlz4hc,9','-b','4096',str(TEMP),str(TREE)],check=True,stdin=subprocess.DEVNULL)
subprocess.run(['fsck.erofs','--extract',str(TEMP)],check=True,stdin=subprocess.DEVNULL)
actual=TEMP.stat().st_size
if actual>SIZE:raise RuntimeError('Image exceeds system partition')
with TEMP.open('r+b') as f:f.truncate(SIZE)
TEMP.rename(IMAGE)
result={'status':'PACKAGED_SINGLE_ATTEMPT_MTD_NOT_FLASHED','image':IMAGE.name,'erofs_size':actual,'padded_size':SIZE,'sha256':digest(IMAGE),'policy_sha256':POLICY,'automatic_mtd_start':True,'restart_after_exit':False,'boot_tested':False,'persist_relabel_scope':'/mnt/vendor/persist/fdsd','mtd_persist_access':'scoped-record-updates','tee_communication_access':True,'firmware_modified':False}
result['duplicate_late_swapon_removed']=True
result['camera_user_reported_working']=True
result['camera_test_package']='com.ginkgo.micamera6test'
result['camera_apk_sha256']=camera['apk_sha256']
result['status']='PACKAGED_WORKING_CAMERA_V31_NOT_FLASHED'
(OUT/'hyperos3-ginkgo-v32-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('EROFS boyutu: %.3f GiB'%(actual/1024**3))
print('SHA256:',result['sha256'])
print('V32 SISTEM KAMERA TEST IMAJI HAZIR. TELEFONA YAZILMADI.')
