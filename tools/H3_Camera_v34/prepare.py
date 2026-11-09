#!/usr/bin/env python3
"""Stage V34 original-identity camera offline, with verified rollback."""
import base64
import hashlib
import json
import os
import shutil
import stat
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

TREE = Path('/linux/build/hyperos3-ginkgo-v1')
REF = Path('/reference')
OUT = Path('/out')
BACKUP = Path('/linux/backups/hyperos3-camera-v34')
APP = TREE/'product/priv-app/MiuiCamera'
TARGET = APP/'MiuiCamera.apk'
SOURCE = REF/'camera-v34/original-identity-v1/MiuiCamera-6.2-ginkgo-original.apk'
OLD = '48a12d13da98f2e683b185476b9a5516251bcef80fe19aec0ecfde22876d51c5'
NEW = '538d855e942c8fe3ce6c21ab5559d4f42004730491ddbf8e10b90391ef277a6e'
POLICY = 'd38305ac8bff790d9f18ec8541e412ce05344a43827c6fda73ff7d12146e952a'

def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def meta(p):
    s=p.stat()
    return dict(uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode),inode=s.st_ino,
        xattrs={k:base64.b64encode(os.getxattr(p,k)).decode() for k in sorted(os.listxattr(p))})

def rewrite(src,dst):
    with src.open('rb') as a,dst.open('r+b') as b:
        shutil.copyfileobj(a,b,8*1024*1024);b.truncate();b.flush();os.fsync(b.fileno())

def label(p,mode,context):
    os.chown(p,0,0);os.chmod(p,mode);os.setxattr(p,'security.selinux',context)
    m=meta(p)
    if (m['uid'],m['gid'],m['mode'])!=(0,0,mode) or os.getxattr(p,'security.selinux')!=context:
        raise RuntimeError('Metadata mismatch: '+str(p))

def main():
    if os.geteuid()!=0:raise RuntimeError('Container root required')
    for p in (BACKUP,OUT/'validation.json',APP/'lib'):
        if p.exists() or p.is_symlink():raise RuntimeError('Refusing existing path: '+str(p))
    if any(p.is_symlink() for p in [APP,TARGET,APP/'oat',*APP.rglob('*')]):
        raise RuntimeError('Unexpected camera symlink')
    expected={'MiuiCamera.apk','oat/arm64/MiuiCamera.odex','oat/arm64/MiuiCamera.vdex'}
    if {str(p.relative_to(APP)) for p in APP.rglob('*') if p.is_file()}!=expected:
        raise RuntimeError('Unexpected original camera contents')
    if digest(TARGET)!=OLD or digest(SOURCE)!=NEW or digest(TREE/'odm/etc/selinux/precompiled_sepolicy')!=POLICY:
        raise RuntimeError('APK/policy baseline mismatch')
    report=json.loads((REF/'camera-v34/original-identity-v1/validation.json').read_text())
    if report.get('apk_sha256')!=NEW or report.get('package')!='com.android.camera' or report.get('status')!='ORIGINAL_IDENTITY_APK_REVIEW_ONLY_NOT_INSTALLED':
        raise RuntimeError('Candidate report mismatch')
    clone=TREE/'product/app/GinkgoMiCamera6Test'
    clone_report=json.loads((REF/'camera-v32/validation.json').read_text())
    if clone_report.get('apk_sha256')!='815f14e8419f55f23dfa58e796c7462c813a941417455e1d3e17cf7d2eba1186':
        raise RuntimeError('Fallback report mismatch')
    for item in clone_report['files']:
        rel=Path(item['path'])
        if rel.is_absolute() or '..' in rel.parts or not (str(rel).startswith('product/app/GinkgoMiCamera6Test/') or str(rel)=='product/etc/sysconfig/ginkgo-micamera6-test-hiddenapi.xml'):
            raise RuntimeError('Fallback scope mismatch')
        if digest(TREE/rel)!=item['sha256']:raise RuntimeError('Fallback changed')
    hidden=TREE/'system/etc/sysconfig/hiddenapi-package-whitelist.xml'
    permissions=TREE/'product/etc/permissions/privapp-permissions-product.xml'
    if not any(e.attrib.get('package')=='com.android.camera' for e in ET.parse(hidden).getroot().findall('hidden-api-whitelisted-app')):
        raise RuntimeError('Missing original hidden API allowlist')
    if not any(e.attrib.get('package')=='com.android.camera' for e in ET.parse(permissions).getroot().findall('privapp-permissions')):
        raise RuntimeError('Missing original privileged permission list')
    unchanged={str(p.relative_to(TREE)):digest(p) for p in (hidden,permissions,TREE/'odm/etc/selinux/precompiled_sepolicy')}
    before={n:dict(sha256=digest(APP/n),metadata=meta(APP/n)) for n in expected}
    if {'security.ima','security.evm','security.capability'} & set(before['MiuiCamera.apk']['metadata']['xattrs']):
        raise RuntimeError('Unexpected APK integrity xattrs')
    file_context=os.getxattr(TARGET,'security.selinux');dir_context=os.getxattr(APP,'security.selinux')
    BACKUP.mkdir(parents=True)
    shutil.copyfile(TARGET,BACKUP/'MiuiCamera-original.apk')
    if digest(BACKUP/'MiuiCamera-original.apk')!=OLD:raise RuntimeError('Backup failed')
    (BACKUP/'original-metadata.json').write_text(json.dumps(before,indent=2)+'\n')
    staged=BACKUP/'candidate-lib';(staged/'arm64').mkdir(parents=True)
    with zipfile.ZipFile(SOURCE) as z:
        names=[n for n in z.namelist() if n.startswith('lib/') and not n.endswith('/')]
        if len(names)!=42 or len(set(names))!=42:raise RuntimeError('Expected 42 native files')
        for n in names:
            parts=Path(n).parts
            if len(parts)!=3 or parts[:2]!=('lib','arm64-v8a') or not n.endswith('.so'):raise RuntimeError('Invalid native path')
            data=z.read(n)
            if data[:5]!=b'\x7fELF\x02' or int.from_bytes(data[18:20],'little')!=183:raise RuntimeError('Not AArch64')
            p=staged/'arm64'/parts[-1];p.write_bytes(data);label(p,0o644,file_context)
    for p in (staged,staged/'arm64'):label(p,0o755,dir_context)
    moved_oat=moved_lib=rewritten=False
    try:
        (APP/'oat').rename(BACKUP/'original-oat');moved_oat=True
        staged.rename(APP/'lib');moved_lib=True
        rewritten=True;rewrite(SOURCE,TARGET)
        if digest(TARGET)!=NEW or meta(TARGET)!=before['MiuiCamera.apk']['metadata']:raise RuntimeError('APK metadata changed')
        for n in expected-{'MiuiCamera.apk'}:
            p=BACKUP/'original-oat'/Path(n).relative_to('oat')
            if digest(p)!=before[n]['sha256'] or meta(p)!=before[n]['metadata']:raise RuntimeError('OAT backup mismatch')
        for rel,h in unchanged.items():
            if digest(TREE/rel)!=h:raise RuntimeError('Unrelated baseline changed')
        files=[]
        for p in [TARGET,*sorted((APP/'lib/arm64').glob('*.so'))]:
            files.append(dict(path=str(p.relative_to(TREE)),sha256=digest(p),metadata=meta(p)))
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/'validation.json').write_text(json.dumps(dict(status='OFFLINE_ORIGINAL_CAMERA_V34_INSTALLED_NOT_BOOT_TESTED',
            package='com.android.camera',apk_sha256=NEW,backup=str(BACKUP),files=files,unchanged=unchanged,
            fallback_preserved=True,policy_changed=False,signature_migration_tested=False),indent=2)+'\n')
    except BaseException:
        if rewritten:rewrite(BACKUP/'MiuiCamera-original.apk',TARGET)
        if moved_lib:(APP/'lib').rename(staged)
        if moved_oat:(BACKUP/'original-oat').rename(APP/'oat')
        for n,item in before.items():
            if digest(APP/n)!=item['sha256'] or meta(APP/n)!=item['metadata']:raise RuntimeError('Rollback verification failed')
        raise
    print('V34 ASIL KAMERA CALISMA AGACINA YERLESTIRILDI')
    print('SHA256:',NEW)
    print('ESKI APK/OAT YEDEKLENDI. APK INODE, IZIN VE ETIKETLERI KORUNDU.')
    print('42 KUTUPHANE YERLESTIRILDI. CALISAN TEST KAMERASI KORUNDU.')
    print('IZIN LISTELERI VE POLITIKA DEGISTIRILMEDI. TELEFONA YAZILMADI.')

if __name__=='__main__':main()
