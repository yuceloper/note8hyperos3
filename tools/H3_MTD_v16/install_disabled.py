"""Install the disabled diagnostic MTD candidate into an offline ROM tree."""
from pathlib import Path
import hashlib
import json
import os
import stat
import xml.etree.ElementTree as ET

TREE = Path('/linux/build/hyperos3-ginkgo-v1')
BUNDLE = Path('/reference/mtd-bundle-v16/bundle-v1')
BACKUP = Path('/linux/backups/hyperos3-mtd-v16-disabled')
OLD = '4deded9b6bd729155ed39c5e8e9c7a0673ecc9fb7a82a5c7c624c24d5d8d7475'
NEW = 'ed11c4971bea1c35ec7caf4ccaa224484a4540f66c4c4bd4ced8df32fc34aed8'
def sha(data): return hashlib.sha256(data).hexdigest()
def meta(p):
    st = p.stat()
    return (st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode), {k: os.getxattr(p,k) for k in os.listxattr(p)})
def safe(p):
    relative = p.relative_to(TREE)
    current = TREE
    for component in relative.parts:
        current = current / component
        if current.is_symlink(): raise RuntimeError('Symlink destination rejected: ' + str(current))
if BACKUP.exists(): raise RuntimeError('Backup already exists; refusing repeat install')
policy_target = TREE/'odm/etc/selinux/precompiled_sepolicy'
if sha(policy_target.read_bytes()) != OLD: raise RuntimeError('V11 baseline mismatch')
policy = (BUNDLE/'review/precompiled_sepolicy.candidate').read_bytes()
if sha(policy) != NEW: raise RuntimeError('V16 policy mismatch')
manifest = json.loads((BUNDLE/'validation.json').read_text())
if manifest['status'] != 'REVIEW_BUNDLE_ONLY_NOT_INSTALLED' or len(manifest['files']) != 59:
    raise RuntimeError('Invalid bundle')
jobs = []
for item in manifest['files']:
    rel = Path(item['path'])
    if rel.is_absolute() or '..' in rel.parts: raise RuntimeError('Invalid relative path')
    if str(rel) != 'system_ext/bin/ginkgo-mtd@1.3' and rel.parent != Path('system_ext/lib64/ginkgo-mtd-v16'):
        raise RuntimeError('Unexpected bundle path')
    data = (BUNDLE/'root'/rel).read_bytes()
    if sha(data) != item['sha256']: raise RuntimeError('Bundle hash mismatch')
    executable = str(rel) == 'system_ext/bin/ginkgo-mtd@1.3'
    jobs.append((TREE/rel,data,0o755 if executable else 0o644,2000 if executable else 0,'ginkgo_mtd_exec' if executable else 'system_lib_file'))
rc = (BUNDLE/'root/system_ext/etc/init/ginkgo-mtd-v16.rc').read_text()
expected_rc = '# Diagnostic service: no automatic or lazy start.\nservice ginkgo-mtd /system_ext/bin/ginkgo-mtd@1.3\n    class hal\n    user root\n    group system drmrpc\n    disabled\n    oneshot\n'
if rc != expected_rc: raise RuntimeError('Service definition changed')
jobs.append((TREE/'system_ext/etc/init/ginkgo-mtd-v16.rc',rc.encode(),0o644,0,'system_file'))
xml = ET.fromstring((BUNDLE/'review/manifest.ginkgo-mtd.xml').read_text())
if xml.get('type') != 'device' or xml.findtext('hal/name') != 'vendor.xiaomi.hardware.mtdservice':
    raise RuntimeError('Unexpected VINTF asset')
xml.set('type','framework')
vintf = ET.tostring(xml,encoding='utf-8') + b'\n'
jobs.append((TREE/'system_ext/etc/vintf/manifest/ginkgo-mtd-v16.xml',vintf,0o644,0,'system_file'))
changes = [(policy_target,policy)]
for name, addition in [('odm_file_contexts','file_contexts.append'),('odm_hwservice_contexts','hwservice_contexts.append')]:
    p = TREE/'odm/etc/selinux'/name
    old = p.read_bytes()
    if b'ginkgo_mtd' in old or b'mtdservice' in old: raise RuntimeError('Existing MTD context requires review')
    changes.append((p,old.rstrip(b'\n') + (b'\n' if old else b'') + (BUNDLE/'review'/addition).read_bytes()))
if len({str(p) for p,*_ in jobs}) != len(jobs): raise RuntimeError('Duplicate destination')
for p,*_ in jobs:
    safe(p)
    if p.exists(): raise RuntimeError('Destination already exists: '+str(p))
for p,_ in changes:
    safe(p)
    if not p.is_file(): raise RuntimeError('Missing existing policy file')
original = [(p,p.read_bytes(),meta(p)) for p,_ in changes]
BACKUP.mkdir(parents=True)
for p,data,_ in original:
    dest=BACKUP/p.relative_to(TREE);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
created=[]; dirs=[]
try:
    for p,data,mode,gid,label in jobs:
        missing=[];parent=p.parent
        while not parent.exists(): missing.append(parent);parent=parent.parent
        for d in reversed(missing):
            d.mkdir();dirs.append(d);os.chown(d,0,0);d.chmod(0o755)
            os.setxattr(d,'security.selinux',b'u:object_r:system_file:s0')
        with p.open('xb') as f: created.append(p);f.write(data)
        os.chown(p,0,gid);p.chmod(mode)
        context=('u:object_r:'+label+':s0').encode()
        os.setxattr(p,'security.selinux',context)
        actual=meta(p)
        if p.read_bytes()!=data or actual[:3]!=(0,gid,mode) or actual[3].get('security.selinux',b'').rstrip(b'\0')!=context:
            raise RuntimeError('Installed file verification failed: '+str(p))
    for p,data in changes: p.write_bytes(data)
    for (p,data),(_,_,old_meta) in zip(changes,original):
        if p.read_bytes()!=data or meta(p)!=old_meta: raise RuntimeError('Policy metadata changed')
except BaseException:
    for p,data,_ in original: p.write_bytes(data)
    for p in reversed(created): p.unlink()
    for d in reversed(dirs): d.rmdir()
    raise
(BACKUP/'installation.json').write_text(json.dumps({'status':'OFFLINE_INSTALLED_DISABLED_NOT_BOOT_TESTED','policy_sha256':NEW,'new_files':[str(p.relative_to(TREE)) for p,*_ in jobs],'original_files':{str(p.relative_to(TREE)):sha(data) for p,data,_ in original},'automatic_start':False,'persist_tee_permissions_added':False},indent=2)+'\n')
print('V16 MTD DOSYALARI VE DEVRE DISI SERVIS CALISMA AGACINA KURULDU.')
print('VINTF SYSTEM_EXT ALTINDA. ODM VINTF BAGLANTISI KORUNDU.')
print('POLITIKA SHA256:',NEW)
print('PERSIST/TEE ERISIMI EKLENMEDI. TELEFONA YAZILMADI.')
