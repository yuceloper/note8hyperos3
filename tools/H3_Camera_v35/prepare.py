#!/usr/bin/env python3
"""Persist the tested, page-aligned V35 update in the offline original camera."""
import base64
import hashlib
import json
import os
import shutil
import stat
import zipfile
from pathlib import Path
from build import patch, sig, verify_native_alignment, SOURCE_SHA

TREE=Path('/linux/build/hyperos3-ginkgo-v1')
REF=Path('/reference')
OUT=Path('/out')
TARGET=TREE/'product/priv-app/MiuiCamera/MiuiCamera.apk'
SOURCE=REF/'camera-v35/startup-probe-v2/MiuiCamera-6.2-ginkgo-v35.apk'
BACKUP=Path('/linux/backups/hyperos3-camera-v35')

def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def meta(p):
    s=p.stat()
    return dict(uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode),inode=s.st_ino,
        xattrs={k:base64.b64encode(os.getxattr(p,k)).decode() for k in sorted(os.listxattr(p))})

def rewrite(source,target):
    with source.open('rb') as a,target.open('r+b') as b:
        shutil.copyfileobj(a,b,8*1024*1024);b.truncate();b.flush();os.fsync(b.fileno())

def verify_candidate(original,candidate,report):
    if digest(original)!=SOURCE_SHA:raise RuntimeError('V34 source mismatch')
    if report.get('status')!='STARTUP_WRITE_PROBE_OMITTED_NOT_RUNTIME_TESTED' or report.get('package')!='com.android.camera' or report.get('source_sha256')!=SOURCE_SHA:
        raise RuntimeError('V35 build report mismatch')
    if report.get('same_signer_as_v34') is not True or report.get('native_alignment_verified') is not True or report.get('native_zip_alignment_bytes')!=4096:
        raise RuntimeError('Missing V35 signing/alignment validation')
    if digest(candidate)!=report.get('apk_sha256'):raise RuntimeError('V35 APK hash mismatch')
    verify_native_alignment(candidate)
    with zipfile.ZipFile(original) as old,zipfile.ZipFile(candidate) as new:
        old_names={n for n in old.namelist() if not sig(n)}
        new_names={n for n in new.namelist() if not sig(n)}
        if old_names!=new_names or len(new.namelist())!=len(set(new.namelist())):raise RuntimeError('Unexpected APK entry set')
        patched=patch(old.read('classes.dex'))
        for n in old_names:
            if new.read(n)!=(patched if n=='classes.dex' else old.read(n)):raise RuntimeError('Unexpected V35 payload change: '+n)

def records_verified(report):
    files=report['files']
    if len(files)!=43 or len({i['path'] for i in files})!=43:raise RuntimeError('V34 file count mismatch')
    expected={str(TARGET.relative_to(TREE))}
    with zipfile.ZipFile(TARGET) as z:
        for n in z.namelist():
            if n.startswith('lib/') and n.endswith('.so'):
                rel=Path(n)
                if len(rel.parts)!=3 or rel.parts[:2]!=('lib','arm64-v8a'):raise RuntimeError('Invalid native path')
                expected.add('product/priv-app/MiuiCamera/lib/arm64/'+rel.name)
    if {i['path'] for i in files}!=expected:raise RuntimeError('V34 scope mismatch')
    for item in files:
        p=TREE/item['path']
        if p.is_symlink() or digest(p)!=item['sha256'] or meta(p)!=item['metadata']:raise RuntimeError('V34 file/metadata changed: '+item['path'])
    return files

def main():
    if os.geteuid()!=0:raise RuntimeError('Container root required')
    for p in (BACKUP,OUT/'validation.json'):
        if p.exists() or p.is_symlink():raise RuntimeError('Refusing existing output: '+str(p))
    report=json.loads((REF/'camera-v34/stage-v1/validation.json').read_text())
    if report.get('status')!='OFFLINE_ORIGINAL_CAMERA_V34_INSTALLED_NOT_BOOT_TESTED' or report.get('package')!='com.android.camera' or report.get('apk_sha256')!=SOURCE_SHA:
        raise RuntimeError('V34 stage report mismatch')
    for p in [TARGET.parent,*TARGET.parent.rglob('*')]:
        if p.is_symlink():raise RuntimeError('Unexpected app symlink')
    if (TARGET.parent/'oat').exists():raise RuntimeError('Unexpected OAT files')
    files=records_verified(report)
    build_report=json.loads((REF/'camera-v35/startup-probe-v2/validation.json').read_text())
    verify_candidate(TARGET,SOURCE,build_report)
    unchanged=report['unchanged']
    if set(unchanged)!={'system/etc/sysconfig/hiddenapi-package-whitelist.xml','product/etc/permissions/privapp-permissions-product.xml','odm/etc/selinux/precompiled_sepolicy'}:raise RuntimeError('Baseline scope mismatch')
    for rel,h in unchanged.items():
        if digest(TREE/rel)!=h:raise RuntimeError('Baseline changed')
    # Preserve the fallback camera without changing its package or native files.
    fallback=json.loads((REF/'camera-v32/validation.json').read_text())
    for item in fallback['files']:
        rel=Path(item['path'])
        if rel.is_absolute() or '..' in rel.parts or not (str(rel).startswith('product/app/GinkgoMiCamera6Test/') or str(rel)=='product/etc/sysconfig/ginkgo-micamera6-test-hiddenapi.xml'):
            raise RuntimeError('Invalid fallback path')
        if digest(TREE/rel)!=item['sha256']:raise RuntimeError('Fallback changed')
    before=meta(TARGET)
    if {'security.ima','security.evm','security.capability'} & set(before['xattrs']):raise RuntimeError('Unexpected integrity xattrs')
    BACKUP.mkdir(parents=True)
    saved=BACKUP/'MiuiCamera-v34.apk';shutil.copyfile(TARGET,saved)
    if digest(saved)!=SOURCE_SHA:raise RuntimeError('V34 backup failed')
    (BACKUP/'metadata.json').write_text(json.dumps(before,indent=2)+'\n')
    (BACKUP/'stage-v34.json').write_text(json.dumps(report,indent=2)+'\n')
    changed=False
    try:
        changed=True;rewrite(SOURCE,TARGET)
        if meta(TARGET)!=before:raise RuntimeError('APK metadata changed')
        verify_candidate(saved,TARGET,build_report)
        for item in files:
            if item['path']==str(TARGET.relative_to(TREE)):item['sha256']=build_report['apk_sha256']
            p=TREE/item['path']
            if digest(p)!=item['sha256'] or meta(p)!=item['metadata']:raise RuntimeError('Post-install validation failed')
        for rel,h in unchanged.items():
            if digest(TREE/rel)!=h:raise RuntimeError('Unrelated baseline changed')
        report.update(status='OFFLINE_ORIGINAL_CAMERA_V35_SYNCED_NOT_BOOT_TESTED',apk_sha256=build_report['apk_sha256'],
            previous_apk_sha256=SOURCE_SHA,v35_backup=str(BACKUP),user_reported_update_working=True,
            fresh_system_image_boot_tested=False,native_zip_alignment_bytes=4096,
            gallery_signature_permission_fixed=False,actual_lut_compatibility_verified=False)
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    except BaseException:
        if changed:
            rewrite(saved,TARGET)
            if digest(TARGET)!=SOURCE_SHA or meta(TARGET)!=before:raise RuntimeError('Rollback verification failed')
        raise
    print('V35 CALISAN KAMERA ROM AGACINA AKTARILDI')
    print('SHA256:',build_report['apk_sha256'])
    print('V34 YEDEGI, APK INODE/IZIN/ETIKETLERI VE 42 KUTUPHANE DOGRULANDI.')
    print('TEST KAMERASI VE POLITIKA KORUNDU. TELEFONA YAZILMADI.')
    print('GALERI IMZA IZNI VE OZEL LUT UYUMLULUGU ACIK KONULAR.')

if __name__=='__main__':main()
