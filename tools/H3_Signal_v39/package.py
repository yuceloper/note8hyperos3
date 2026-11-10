"""Verify and package the offline single-attempt MTD diagnostic tree. Never flash a device."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "H3_Camera_v35"))
from pathlib import Path
import hashlib
import base64
import zipfile
import json
import os
import stat
import subprocess
import xml.etree.ElementTree as ET

TREE=Path('/linux/build/hyperos3-ginkgo-v1')
BUNDLE=Path('/reference/mtd-bundle-v16/bundle-v1')
OUT=Path('/result')
IMAGE=OUT/'hyperos3-ginkgo-v39-padded.img'
TEMP=OUT/'hyperos3-ginkgo-v39.building.img'
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
# Verify V35 app and retain the V32 fallback, V34 migration backup and ROM baseline checks.
v34=json.loads(Path('/reference/camera-v35/stage-v1/validation.json').read_text())
build35=json.loads(Path('/reference/camera-v35/startup-probe-v2/validation.json').read_text())
V34_SHA=build35['apk_sha256']
app=TREE/'product/priv-app/MiuiCamera'
apk=app/'MiuiCamera.apk'
backup=Path('/linux/backups/hyperos3-camera-v34')
if v34.get('status')!='OFFLINE_ORIGINAL_CAMERA_V35_SYNCED_NOT_BOOT_TESTED' or v34.get('package')!='com.android.camera' or v34.get('apk_sha256')!=V34_SHA:
    raise RuntimeError('V34 preparation report mismatch')
if not v34.get('fallback_preserved') or v34.get('policy_changed') is not False:
    raise RuntimeError('V34 scope mismatch')
from prepare import verify_candidate
verify_candidate(Path('/linux/backups/hyperos3-camera-v35/MiuiCamera-v34.apk'),apk,build35)
if digest(apk)!=V34_SHA or (app/'oat').exists() or (app/'oat').is_symlink():
    raise RuntimeError('V34 APK/OAT mismatch')
if digest(backup/'MiuiCamera-original.apk')!='48a12d13da98f2e683b185476b9a5516251bcef80fe19aec0ecfde22876d51c5':
    raise RuntimeError('Original APK backup mismatch')
def metadata(p):
    s=p.stat()
    return dict(uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode),inode=s.st_ino,
        xattrs={k:base64.b64encode(os.getxattr(p,k)).decode() for k in sorted(os.listxattr(p))})
original_metadata=json.loads((backup/'original-metadata.json').read_text())
if metadata(apk)!=original_metadata['MiuiCamera.apk']['metadata']:
    raise RuntimeError('Original APK inode/metadata changed')
for n,item in original_metadata.items():
    rel=Path(n)
    if n=='MiuiCamera.apk':continue
    if rel.is_absolute() or '..' in rel.parts or rel.parts[0]!='oat':raise RuntimeError('Invalid OAT backup path')
    saved=backup/'original-oat'/rel.relative_to('oat')
    if digest(saved)!=item['sha256'] or metadata(saved)!=item['metadata']:
        raise RuntimeError('OAT backup verification failed')
with zipfile.ZipFile(apk) as z,zipfile.ZipFile(backup/'MiuiCamera-original.apk') as original:
    if z.read('AndroidManifest.xml')!=original.read('AndroidManifest.xml'):
        raise RuntimeError('Original manifest changed')
    names=[n for n in z.namelist() if n.startswith('lib/') and n.endswith('.so')]
    if len(names)!=42 or len(set(names))!=42:raise RuntimeError('V34 native count mismatch')
    expected_v34={str(apk.relative_to(TREE))}
    for n in names:
        rel=Path(n)
        if len(rel.parts)!=3 or rel.parts[:2]!=('lib','arm64-v8a'):raise RuntimeError('Invalid native path')
        target=app/'lib/arm64'/rel.name
        if digest(target)!=hashlib.sha256(z.read(n)).hexdigest():raise RuntimeError('V34 native payload mismatch')
        expected_v34.add(str(target.relative_to(TREE)))
files=v34['files']
if len(files)!=43 or {i['path'] for i in files}!=expected_v34:
    raise RuntimeError('V34 file records mismatch')
if any(p.is_symlink() for p in [app,*app.rglob('*')]):raise RuntimeError('V34 app symlink')
if {str(p.relative_to(TREE)) for p in app.rglob('*') if p.is_file()}!=expected_v34:
    raise RuntimeError('Unexpected V34 app contents')
for item in files:
    target=TREE/item['path']
    if digest(target)!=item['sha256'] or metadata(target)!=item['metadata']:
        raise RuntimeError('V34 file/metadata mismatch: '+item['path'])
    m=metadata(target)
    if (m['uid'],m['gid'],m['mode'])!=(0,0,0o644) or os.getxattr(target,'security.selinux').rstrip(b'\0')!=b'u:object_r:system_file:s0':
        raise RuntimeError('V34 file label/mode mismatch')
for directory in [app,app/'lib',app/'lib/arm64']:
    m=metadata(directory)
    if (m['uid'],m['gid'],m['mode'])!=(0,0,0o755) or os.getxattr(directory,'security.selinux').rstrip(b'\0')!=b'u:object_r:system_file:s0':
        raise RuntimeError('V34 directory metadata mismatch')
expected_unchanged={'system/etc/sysconfig/hiddenapi-package-whitelist.xml','product/etc/permissions/privapp-permissions-product.xml','odm/etc/selinux/precompiled_sepolicy'}
if set(v34['unchanged'])!=expected_unchanged:raise RuntimeError('V34 unchanged scope mismatch')
for rel,h in v34['unchanged'].items():
    if digest(TREE/rel)!=h:raise RuntimeError('V34 baseline file changed')
hidden=ET.parse(TREE/'system/etc/sysconfig/hiddenapi-package-whitelist.xml').getroot()
if not any(e.get('package')=='com.android.camera' for e in hidden.findall('hidden-api-whitelisted-app')):
    raise RuntimeError('Original camera hidden API allowlist missing')
print('V35 ASIL KAMERA, 42 KUTUPHANE, YEDEK VE METADATA KONTROLLERI BASARILI',flush=True)
cfg = ET.parse(TREE/expected_config).getroot()
if cfg.tag != 'config' or len(cfg) != 1 or cfg[0].tag != 'hidden-api-whitelisted-app' or cfg[0].attrib != {'package':'com.ginkgo.micamera6test'}:
    raise RuntimeError('Hidden API exception scope mismatch')
print('V32 AYRI KAMERA APK, KUTUPHANE VE PAKETE OZEL IZIN KONTROLLERI BASARILI', flush=True)

print('V25 DOSYA, METADATA, TEK BASLATMA TANIMI VE POLITIKA KONTROLLERI BASARILI',flush=True)

# V39 checks supplement every retained V35 baseline check above.
V39_SHA='452faaae8d36ac59f4f6b7830ea4fd126b878678f377e79e8184568f40a33300'
SOURCE38='f3c66613c8433783c1b6b8608b7e89721b7a3d9d127ad7e92bf0817f80c7b258'
stage38=json.loads(Path('/reference/signal-v39/stage-v1/validation.json').read_text())
backup38=Path('/linux/backups/hyperos3-signal-v39')
saved38=json.loads((backup38/'manifest.json').read_text())
if stage38.get('status')!='OFFLINE_INSTALLED_NOT_BOOT_TESTED' or stage38.get('source_sha256')!=SOURCE38 or stage38.get('candidate_sha256')!=V39_SHA:
    raise RuntimeError('V39 installation report mismatch')
if saved38.get('status')!='BACKUP_VERIFIED_BEFORE_INSTALL' or saved38.get('candidate_sha256')!=V39_SHA or saved38.get('files')!=stage38.get('files'):
    raise RuntimeError('V39 backup manifest mismatch')
jar38=Path('system/framework/telephony-common.jar')
links38={}
preopt38={Path('system/framework/telephony-common.jar.fsv_meta'),Path('system/framework/boot-telephony-common.vdex'),Path('system/framework/boot-telephony-common.vdex.fsv_meta')}
for arch38 in ['arm','arm64']:
    for ext38 in ['art','oat']:
        preopt38.update([Path(f'system/framework/{arch38}/boot-telephony-common.{ext38}'),Path(f'system/framework/{arch38}/boot-telephony-common.{ext38}.fsv_meta')])
    for suffix38 in ['', '.fsv_meta']:
        rel38=Path(f'system/framework/{arch38}/boot-telephony-common.vdex{suffix38}')
        links38[rel38]=f'../boot-telephony-common.vdex{suffix38}'
preopt38.update(links38)
if set(stage38['files'])!={str(r) for r in preopt38|{jar38}} or set(stage38.get('moved_preoptimization_files',[]))!={str(r) for r in preopt38}:
    raise RuntimeError('V39 backup scope mismatch')
def meta38(p):
    st=p.lstat()
    if not (stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode)) or st.st_nlink!=1:
        raise RuntimeError('V39 unexpected file type: '+str(p))
    return {'inode':st.st_ino,'uid':st.st_uid,'gid':st.st_gid,'mode':stat.S_IMODE(st.st_mode),
        'mtime_ns':st.st_mtime_ns,'link_target':os.readlink(p) if p.is_symlink() else None,
        'xattrs':{n:base64.b64encode(os.getxattr(p,n,follow_symlinks=False)).decode() for n in sorted(os.listxattr(p,follow_symlinks=False))}}
if (TREE/jar38).is_symlink() or digest(TREE/jar38)!=V39_SHA or meta38(TREE/jar38)!=stage38['files'][str(jar38)]['metadata']:
    raise RuntimeError('V39 installed JAR or metadata mismatch')
if digest(backup38/'telephony-common.original.jar')!=SOURCE38:
    raise RuntimeError('V39 original JAR backup mismatch')
for rel38 in preopt38:
    installed38=TREE/rel38
    if installed38.exists() or installed38.is_symlink():raise RuntimeError('V39 stale preopt: '+str(rel38))
    saved_file38=backup38/'preopt'/rel38
    if rel38 in links38:
        if not saved_file38.is_symlink() or os.readlink(saved_file38)!=links38[rel38]:
            raise RuntimeError('V39 backed up alias mismatch')
        h38=hashlib.sha256((b'symlink'+bytes([0]))+os.fsencode(os.readlink(saved_file38))).hexdigest()
    else:
        if saved_file38.is_symlink():raise RuntimeError('V39 regular backup became symlink')
        h38=digest(saved_file38)
    item38=stage38['files'][str(rel38)]
    if h38!=item38['sha256'] or meta38(saved_file38)!=item38['metadata']:
        raise RuntimeError('V39 preopt backup hash/metadata mismatch: '+str(rel38))
print('V39 JAR, 11 YEDEK DOSYA VE 4 VDEX BAGLANTISI DOGRULANDI. PAKETLENIYOR...',flush=True)

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
result['status']='PACKAGED_SIGNAL_V39_NOT_FLASHED'
result['telephony_common_sha256']=V39_SHA
result['legacy_signal_runtime_tested']=False
result['dexdump_user_reported_passed']=True
result['temporary_dex2oat_verify_user_reported_passed']=True
result['v35_baseline_checks_retained']=True
result['target_preopt_files_moved_to_backup']=15
result['original_camera_package']='com.android.camera'
result['original_camera_apk_sha256']=V34_SHA
result['signature_migration_user_reported_working']=True
result['fresh_v35_system_image_boot_tested']=False
result['gallery_signature_permission_fixed']=False
result['actual_lut_compatibility_verified']=False
result['fallback_camera_preserved']=True
(OUT/'hyperos3-ginkgo-v39-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('EROFS boyutu: %.3f GiB'%(actual/1024**3))
print('SHA256:',result['sha256'])
print('V39 SINYAL TEST IMAJI HAZIR. TELEFONA YAZILMADI.')

