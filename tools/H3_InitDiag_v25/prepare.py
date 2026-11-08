"""Add kernel-log markers around existing boot-completed commands. Offline only."""
from pathlib import Path
import hashlib
import json
import os
import stat

TREE = Path('/linux/build/hyperos3-ginkgo-v1')
OUT = Path('/result')
BACKUP = Path('/linux/backups/hyperos3-initdiag-v25')
TARGET = TREE / 'system/etc/init/hw/init.rc'
EXPECTED = 'cc02a2de9ad490e64de3d271db7352e530069bebde591f64e45027ea53650d6a'
POLICY = 'd38305ac8bff790d9f18ec8541e412ce05344a43827c6fda73ff7d12146e952a'
def instrument(original):
    result = []
    mapping = []
    active = False
    for number, line in enumerate(original.splitlines(keepends=True), 1):
        stripped = line.strip()
        if stripped and not line[:1].isspace() and not stripped.startswith(b'#'):
            active = line.startswith(b'on ') and b'property:sys.boot_completed=1' in line
        if active and line[:1].isspace() and stripped and not stripped.startswith(b'#'):
            ident = 'C%02d' % (len(mapping) + 1)
            prefix = b'    write /dev/kmsg "<6>GINKGO_INIT_V25 ' + ident.encode()
            result.append(prefix + b' BEFORE"\n')
            result.append(line)
            result.append(prefix + b' AFTER"\n')
            mapping.append({'id':ident, 'original_line':number, 'command':stripped.decode()})
        else:
            result.append(line)
    candidate = b''.join(result)
    reconstructed = b''.join(l for l in candidate.splitlines(keepends=True) if b'GINKGO_INIT_V25 ' not in l)
    if reconstructed != original or not mapping:
        raise RuntimeError('Marker-only reconstruction failed')
    return candidate, mapping
def sha(data):
    return hashlib.sha256(data).hexdigest()
def metadata(path):
    st = path.stat()
    return (st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode),
            {n: os.getxattr(path, n) for n in os.listxattr(path)})
def main():
    if TARGET.is_symlink() or not TARGET.is_file():
        raise RuntimeError('Unexpected target')
    original = TARGET.read_bytes()
    if sha(original) != EXPECTED:
        raise RuntimeError('V23 init.rc source mismatch; nothing changed')
    if sha((TREE/'odm/etc/selinux/precompiled_sepolicy').read_bytes()) != POLICY:
        raise RuntimeError('V22 policy mismatch; nothing changed')
    if BACKUP.exists() or (OUT/'validation.json').exists():
        raise RuntimeError('Backup/output already exists; nothing overwritten')
    candidate, mapping = instrument(original)
    if sha((TREE/'system_ext/etc/init/perfservice.rc').read_bytes()) != '9fe704db8ef299bbfb2dcf08bc644a95c57383aa61f3525c6ad290607502fb0d':
        raise RuntimeError('V23 zRAM change missing')
    before = metadata(TARGET)
    BACKUP.mkdir(parents=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (BACKUP/'init.rc').write_bytes(original)
    (BACKUP/'metadata.json').write_text(json.dumps({'uid':before[0], 'gid':before[1], 'mode':oct(before[2]), 'xattrs':{n:v.hex() for n,v in before[3].items()}}, indent=2)+'\n')
    try:
        with TARGET.open('r+b') as f:
            f.write(candidate)
            f.truncate()
            f.flush()
            os.fsync(f.fileno())
        if TARGET.read_bytes() != candidate or metadata(TARGET) != before:
            raise RuntimeError('Content or metadata verification failed')
    except BaseException:
        with TARGET.open('r+b') as f:
            f.write(original)
            f.truncate()
            f.flush()
            os.fsync(f.fileno())
        raise
    (OUT/'init.rc.candidate').write_bytes(candidate)
    (OUT/'validation.json').write_text(json.dumps({'status':'OFFLINE_PREPARED_NOT_BOOT_TESTED', 'original_sha256':EXPECTED, 'candidate_sha256':sha(candidate), 'policy_sha256':POLICY, 'change':'kernel markers only', 'markers':mapping, 'metadata_preserved':True, 'sigabrt_fixed':False}, indent=2)+'\n')
    print('V25 INIT TANI ISARETLERI HAZIR:', len(mapping))
    print('SHA256:', sha(candidate))
    print('ASIl KOMUTLAR, INIT IKILISI VE POLITIKA KORUNDU. TELEFONA YAZILMADI.')
if __name__ == '__main__':
    main()
