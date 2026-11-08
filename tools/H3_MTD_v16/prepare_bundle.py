"""Prepare a reviewable MTD bundle; do not modify the ROM tree or phone."""
from pathlib import Path
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET

reference = Path('/reference')
probe = reference / 'mtd-linker-v16/runpath-v1'
policy = reference / 'mtd-policy-v16/foundation-v1/mtd-foundation.policy'
output = Path('/result/bundle-v1')
expected_policy = 'ed11c4971bea1c35ec7caf4ccaa224484a4540f66c4c4bd4ced8df32fc34aed8'
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
if output.exists():
    raise RuntimeError('Output exists; nothing overwritten')
if digest(policy) != expected_policy:
    raise RuntimeError('V16 foundation policy hash mismatch')
manifest = json.loads((probe / 'validation.json').read_text())
if manifest['status'] != 'LINKER_PROBE_ONLY_NOT_INSTALLED' or len(manifest['files']) != 59:
    raise RuntimeError('Unexpected probe manifest')
verified = []
seen = set()
for item in manifest['files']:
    relative = Path(item['file'])
    if relative.is_absolute() or '..' in relative.parts or str(relative) in seen:
        raise RuntimeError('Invalid file path')
    seen.add(str(relative))
    source = probe / relative
    if digest(source) != item['sha256']:
        raise RuntimeError('Probe hash mismatch: ' + str(relative))
    if str(relative) != 'bin/ginkgo-mtd@1.3' and relative.parent != Path('lib64/ginkgo-mtd-v16'):
        raise RuntimeError('Unexpected probe destination')
    verified.append((source, relative))
if 'bin/ginkgo-mtd@1.3' not in seen:
    raise RuntimeError('Missing executable')
output.mkdir()
root = output / 'root'
records = []
for source, relative in verified:
    destination = root / 'system_ext' / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    executable = str(relative).startswith('bin/')
    destination.chmod(0o755 if executable else 0o644)
    records.append({'path': str(destination.relative_to(root)), 'sha256': digest(destination), 'uid': 0, 'gid': 2000 if executable else 0, 'mode': '0755' if executable else '0644', 'selinux': 'u:object_r:ginkgo_mtd_exec:s0' if executable else 'u:object_r:system_lib_file:s0'})
init = root / 'system_ext/etc/init/ginkgo-mtd-v16.rc'
init.parent.mkdir(parents=True, exist_ok=True)
init.write_text('''# Diagnostic service: no automatic or lazy start.
service ginkgo-mtd /system_ext/bin/ginkgo-mtd@1.3
    class hal
    user root
    group system drmrpc
    disabled
    oneshot
''')
assets = output / 'review'
assets.mkdir()
vintf = '''<manifest version="1.0" type="device">
    <hal format="hidl">
        <name>vendor.xiaomi.hardware.mtdservice</name>
        <transport>hwbinder</transport>
        <version>1.3</version>
        <interface>
            <name>IMTService</name>
            <instance>default</instance>
        </interface>
    </hal>
</manifest>
'''
ET.fromstring(vintf)
(assets / 'manifest.ginkgo-mtd.xml').write_text(vintf)
(assets / 'file_contexts.append').write_text('/system_ext/bin/ginkgo-mtd@1\\.3 u:object_r:ginkgo_mtd_exec:s0\n/system_ext/lib64/ginkgo-mtd-v16(/.*)? u:object_r:system_lib_file:s0\n')
(assets / 'hwservice_contexts.append').write_text('vendor.xiaomi.hardware.mtdservice::IMTService u:object_r:ginkgo_mtd_hwservice:s0\n')
shutil.copyfile(policy, assets / 'precompiled_sepolicy.candidate')
(output / 'validation.json').write_text(json.dumps({'status': 'REVIEW_BUNDLE_ONLY_NOT_INSTALLED', 'policy_sha256': expected_policy, 'files': records, 'automatic_start': False, 'lazy_interface_start': False, 'persist_tee_permissions_added': False, 'vintf_destination': 'PENDING_EXISTING_ODM_LAYOUT_REVIEW', 'policy_installation': 'NOT_PERFORMED', 'limitations': ['Installed linker namespace untested', 'Runtime read/map permissions incomplete', 'Persist and TEE compatibility untested']}, indent=2) + '\n')
print('V16 MTD INCELEME PAKETI HAZIR: 59 ELF + DEVRE DISI SERVIS TANIMI')
print('VINTF VE POLITIKA YALNIZCA INCELEME DOSYALARI OLARAK EKLENDI.')
print('CALISMA AGACINA KURULMADI. TELEFONA YAZILMADI.')
