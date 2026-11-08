from pathlib import Path
from zipfile import ZipFile
import hashlib, json, os, shutil, subprocess, tempfile

pkg = Path('/package')
root = Path('/linux/build/hyperos3-ginkgo-v1')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
init = root / 'system/etc/init/hw/init.rc'
apex = root / 'system/apex/com.google.android.tethering_compressed.apex'
policy = root / 'odm/etc/selinux/precompiled_sepolicy'
backup = Path('/linux/backups/hyperos3-netd-v7')
target = root / 'system/etc/ginkgo-tethering-v7'
policy_hash = '9704fd3d823f20d2a1a9b8c93aea859134b5b6ad233e46336ad96ba6c87a9a45'
apex_hash = '3f784eb2fc022d1d6a0457698a60ee18e140b90228a826b88586cfb2dc591dcd'
assert sha(init) == (pkg / 'expected-init.sha256').read_text().strip(), 'V6 init hash uyusmazligi'
assert sha(apex) == apex_hash, 'Donor APEX hash uyusmazligi'
assert sha(policy) == policy_hash, 'Politika hash uyusmazligi'
assert not backup.exists() and not os.path.lexists(target), 'V7 hedefi veya yedegi mevcut'
for rel, digest in json.loads((pkg / 'assets-sha256.json').read_text()).items():
    assert sha(pkg / rel) == digest, rel
old = (pkg / 'old-action.txt').read_bytes()
data = init.read_bytes()
assert data.count(old) == 1
new = b'''on load-bpf-programs
    mount none /system/etc/ginkgo-tethering-v7/lib64 /apex/com.android.tethering/lib64 bind
    mount none /system/etc/ginkgo-bpf-v6/mainline /apex/com.android.tethering/etc/bpf/mainline bind
    exec_start ginkgo-bpfloader
    wait_for_prop bpf.progs_loaded 1
'''

with tempfile.TemporaryDirectory(prefix='h3-netd-v7-') as tmp:
    tmp = Path(tmp)
    with ZipFile(apex) as z:
        z.extract('original_apex', tmp)
    with ZipFile(tmp / 'original_apex') as z:
        z.extract('apex_payload.img', tmp)
    stage = tmp / 'stage'
    stage.mkdir()
    result = subprocess.run(['debugfs', '-R', f'rdump /lib64 {stage}', str(tmp / 'apex_payload.img')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    lib = stage / 'lib64'
    assert (lib / 'libnetd_updatable.so').is_file(), result.stdout + result.stderr
    assert not any(p.is_symlink() for p in lib.rglob('*')), 'Beklenmeyen kutuphane baglantisi'
    originals = {str(p.relative_to(lib)): sha(p) for p in lib.rglob('*') if p.is_file()}
    assert len(originals) >= 15, 'APEX kutuphaneleri eksik'
    shutil.copyfile(pkg / 'assets/libnetd_updatable.so', lib / 'libnetd_updatable.so')
    private = lib / 'ginkgo-netd-v7'
    private.mkdir()
    for src in (pkg / 'assets/private').glob('*.so'):
        shutil.copyfile(src, private / src.name)
    for rel, digest in originals.items():
        if rel != 'libnetd_updatable.so':
            assert sha(lib / rel) == digest, rel
    backup.mkdir(parents=True)
    shutil.copy2(init, backup / 'init.rc')
    shutil.copytree(stage, target)

def label(p, name):
    os.setxattr(p, 'security.selinux', ('u:object_r:' + name + ':s0').encode() + b'\0')

for p in [target, *target.rglob('*')]:
    os.chown(p, 0, 0)
    p.chmod(0o755 if p.is_dir() else 0o644)
    label(p, 'system_file' if p == target else 'system_lib_file')

st = init.stat()
attrs = {k: os.getxattr(init, k) for k in os.listxattr(init)}
with init.open('r+b') as f:
    f.write(data.replace(old, new, 1))
    f.truncate()
os.chown(init, st.st_uid, st.st_gid)
os.chmod(init, st.st_mode & 0o7777)
for k, v in attrs.items():
    os.setxattr(init, k, v)
os.utime(init, ns=(st.st_atime_ns, st.st_mtime_ns))
assert all(os.getxattr(init, k) == v for k, v in attrs.items())
assert sha(apex) == apex_hash and sha(policy) == policy_hash
report = {'status': 'OFFLINE_PREPARED_NOT_BOOT_TESTED', 'init_sha256': sha(init),
          'original_donor_libraries_preserved_except': 'libnetd_updatable.so',
          'original_donor_library_count': len(originals),
          'apex_sha256': sha(apex), 'policy_sha256': sha(policy)}
(backup / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
print('V7 DIZIN BAGLAMALARI VE NETD ADAYI HAZIR. TELEFONA YAZILMADI.')
