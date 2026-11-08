"""Remove only the donor's duplicate late swapon action. Offline only."""
from pathlib import Path
import hashlib
import json
import os
import stat

TREE = Path('/linux/build/hyperos3-ginkgo-v1')
OUT = Path('/result')
BACKUP = Path('/linux/backups/hyperos3-zram-v23')
TARGET = TREE / 'system_ext/etc/init/perfservice.rc'
EXPECTED = '58b56ede847e23afa20e0970ff421f1ab729cfccfd99b01619a58f4e4ae9f1a8'
POLICY = 'd38305ac8bff790d9f18ec8541e412ce05344a43827c6fda73ff7d12146e952a'
BLOCK = b'on property:ro.vendor.qti.per_boot_created=1\n    # Run swapon command to enable zram\n    swapon_all /vendor/etc/fstab.default\n'
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
    if sha(original) != EXPECTED or original.count(BLOCK) != 1:
        raise RuntimeError('V22 perfservice source mismatch; nothing changed')
    if sha((TREE/'odm/etc/selinux/precompiled_sepolicy').read_bytes()) != POLICY:
        raise RuntimeError('V22 policy mismatch; nothing changed')
    if BACKUP.exists() or (OUT/'validation.json').exists():
        raise RuntimeError('Backup/output already exists; nothing overwritten')
    candidate = original.replace(BLOCK, b'# Ginkgo: zRAM is already active before boot_completed.\n# Keep the existing swap setup; do not run donor swapon_all again.\n')
    if b'swapon_all' in b'\n'.join(l for l in candidate.splitlines() if not l.lstrip().startswith(b'#')):
        raise RuntimeError('Unexpected remaining swapon command')
    before = metadata(TARGET)
    BACKUP.mkdir(parents=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (BACKUP/'perfservice.rc').write_bytes(original)
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
    (OUT/'perfservice.rc.candidate').write_bytes(candidate)
    (OUT/'validation.json').write_text(json.dumps({'status':'OFFLINE_PREPARED_NOT_BOOT_TESTED', 'original_sha256':EXPECTED, 'candidate_sha256':sha(candidate), 'policy_sha256':POLICY, 'change':'remove duplicate late swapon_all only', 'metadata_preserved':True, 'sigabrt_fixed':False}, indent=2)+'\n')
    print('V23: YALNIZCA IKINCI SWAPON_ALL CAGRISI KALDIRILDI.')
    print('SHA256:', sha(candidate))
    print('PERFSERVICE VE POLITIKA KORUNDU. TELEFONA YAZILMADI.')
if __name__ == '__main__':
    main()
