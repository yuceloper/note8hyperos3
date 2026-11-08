from pathlib import Path
import hashlib
import json
import os
import shutil
import struct

package = Path('/package')
root = Path('/linux/build/hyperos3-ginkgo-v1')
backup = Path('/linux/backups/hyperos3-bpf-v6')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
expected = json.loads((package / 'inputs.json').read_text())
assets = json.loads((package / 'assets-sha256.json').read_text())
init = root / 'system/etc/init/hw/init.rc'
prop = root / 'product/etc/build.prop'
apex = root / 'system/apex/com.google.android.tethering_compressed.apex'
policy = root / 'odm/etc/selinux/precompiled_sepolicy'
for name, p in [('init', init), ('product', prop), ('apex', apex), ('policy', policy)]:
    assert sha(p) == expected[name], f'Kaynak hash uyusmazligi: {p}'
for name, digest in assets.items():
    assert sha(package / name) == digest, f'Paket hash uyusmazligi: {name}'
    data = (package / name).read_bytes()
    assert data[:4] == b'\x7fELF', name
    machine = struct.unpack_from('<H', data, 18)[0]
    assert machine == (247 if name.endswith('.o') else 183), name
assert (root / 'system/lib64/libz.so').is_file(), 'libz.so bulunamadi'
assert not backup.exists(), 'V6 yedegi zaten mevcut'
for name in ['system/bin/ginkgo-netbpfload', 'system/lib64/ginkgo-bpf-v6',
             'system/etc/ginkgo-bpf-v6', 'system/etc/init/ginkgo-bpf-v6.rc']:
    assert not os.path.lexists(root / name), f'Hedef zaten mevcut: {name}'
assert b'ro.bpf.kver_override=' not in prop.read_bytes(), 'BPF ayari zaten mevcut'

old_init = init.read_bytes()
needle = b'on load-bpf-programs\n    exec_start bpfloader\n'
assert old_init.count(needle) == 1, 'BPF tetikleyicisi beklenenden farkli'
objects = sorted((package / 'assets/mainline').glob('*.o'))
assert len(objects) == 5
action = b'on load-bpf-programs\n'
for obj in objects:
    action += (f'    mount none /system/etc/ginkgo-bpf-v6/mainline/{obj.name} '
               f'/apex/com.android.tethering/etc/bpf/mainline/{obj.name} bind\n').encode()
action += b'    exec_start ginkgo-bpfloader\n    wait_for_prop bpf.progs_loaded 1\n'
new_init = old_init.replace(needle, action, 1)
new_prop = prop.read_bytes().rstrip(b'\n') + b'\n\n# Ginkgo: Lineage 23.2 BPF compatibility level\nro.bpf.kver_override=5.10.239\n'
rc = b'''service ginkgo-bpfloader /system/bin/ginkgo-netbpfload
    user root
    group root graphics network_stack net_admin net_bw_acct net_bw_stats net_raw system
    capabilities CHOWN SYS_ADMIN NET_ADMIN
    seclabel u:r:bpfloader:s0
    file /dev/kmsg w
    rlimit memlock 1073741824 1073741824
    disabled
    oneshot
    reboot_on_failure reboot,ginkgo-bpfloader-failed
'''

backup.mkdir(parents=True)
def context(p, name):
    os.setxattr(p, 'security.selinux', ('u:object_r:' + name + ':s0').encode() + b'\0')

def edit(p, data):
    rel = p.relative_to(root)
    saved = backup / rel
    saved.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, saved)
    st = p.stat()
    attrs = {k: os.getxattr(p, k) for k in os.listxattr(p)}
    with p.open('r+b') as f:
        f.write(data)
        f.truncate()
    os.chown(p, st.st_uid, st.st_gid)
    os.chmod(p, st.st_mode & 0o7777)
    for k, v in attrs.items():
        os.setxattr(p, k, v)
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert p.read_bytes() == data
    assert all(os.getxattr(p, k) == v for k, v in attrs.items())

for rel, label in [('system/lib64/ginkgo-bpf-v6', 'system_lib_file'),
                   ('system/etc/ginkgo-bpf-v6', 'system_file'),
                   ('system/etc/ginkgo-bpf-v6/mainline', 'system_file')]:
    p = root / rel
    p.mkdir()
    os.chown(p, 0, 0)
    p.chmod(0o755)
    context(p, label)

def install(src, rel, mode, label):
    p = root / rel
    shutil.copyfile(src, p)
    os.chown(p, 0, 0)
    p.chmod(mode)
    context(p, label)
    assert sha(p) == sha(src)

install(package / 'assets/netbpfload', 'system/bin/ginkgo-netbpfload', 0o755, 'bpfloader_exec')
for src in (package / 'assets/lib64').glob('*.so'):
    install(src, 'system/lib64/ginkgo-bpf-v6/' + src.name, 0o644, 'system_lib_file')
for src in objects:
    install(src, 'system/etc/ginkgo-bpf-v6/mainline/' + src.name, 0o644, 'system_file')
p = root / 'system/etc/init/ginkgo-bpf-v6.rc'
p.write_bytes(rc)
os.chown(p, 0, 0)
p.chmod(0o644)
context(p, 'system_file')
edit(init, new_init)
edit(prop, new_prop)
assert sha(apex) == expected['apex']
assert sha(policy) == expected['policy']
report = {'status': 'OFFLINE_PREPARED_NOT_BOOT_TESTED',
          'init_sha256': sha(init), 'product_prop_sha256': sha(prop),
          'donor_apex_sha256': sha(apex), 'policy_sha256': sha(policy),
          'assets': assets}
(backup / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
print('V6 BPF ADAYI HAZIR. TELEFONA YAZILMADI.')
