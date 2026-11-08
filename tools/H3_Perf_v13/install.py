"""Install/restore V13 in an offline V12 Linux tree, preserving metadata."""
import argparse
import base64
import json
import os
import stat
from pathlib import Path
from prepare import CANDIDATE_SHA, SOURCE_SHA, digest, patched, require

BASELINE = {
    'system_ext/etc/build.prop': '07e761aba69407913231851db9a798626d8fd326ee05d991b3cb3b988c07cadc',
    'system_ext/lib64/libsurfaceflinger.so': 'bb7f41dd2f81bb0949b6674d5ee8d4fa74b5a551d6b47bddb0b28d891c13ee37',
    'odm/etc/selinux/precompiled_sepolicy': '4deded9b6bd729155ed39c5e8e9c7a0673ecc9fb7a82a5c7c624c24d5d8d7475',
}
LIBRARY = 'system_ext/lib64/libqti-perfd-client_system.so'


def metadata(path):
    st = path.stat()
    return {
        'uid': st.st_uid, 'gid': st.st_gid, 'mode': stat.S_IMODE(st.st_mode),
        'atime_ns': st.st_atime_ns, 'mtime_ns': st.st_mtime_ns,
        'xattrs': {n: base64.b64encode(os.getxattr(path, n)).decode()
                  for n in os.listxattr(path)},
    }


def rewrite(path, data, meta):
    if path.read_bytes() != data:
        require(not {'security.capability', 'security.ima', 'security.evm'} &
                set(os.listxattr(path)),
                'Content-sensitive security xattrs require separate handling; no write')
        with path.open('r+b') as f:
            f.write(data)
            f.truncate()
            f.flush()
            os.fsync(f.fileno())
    st = path.stat()
    if (st.st_uid, st.st_gid) != (meta['uid'], meta['gid']):
        os.chown(path, meta['uid'], meta['gid'])
    if stat.S_IMODE(path.stat().st_mode) != meta['mode']:
        os.chmod(path, meta['mode'])
    current_attrs = {n: os.getxattr(path, n) for n in os.listxattr(path)}
    for name, value in meta['xattrs'].items():
        expected = base64.b64decode(value)
        if current_attrs.get(name) != expected:
            os.setxattr(path, name, expected)
    require(path.read_bytes() == data, 'Write verification failed')
    now = metadata(path)
    require(all(now[k] == meta[k] for k in ('uid', 'gid', 'mode', 'xattrs')),
            'Ownership, mode or xattr mismatch')
    os.utime(path, ns=(meta['atime_ns'], meta['mtime_ns']))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--backup', type=Path, required=True)
    p.add_argument('--restore', action='store_true')
    args = p.parse_args()
    root = args.root
    require(root.is_absolute() and root.is_dir() and not root.is_symlink(),
            'Expected an existing absolute offline tree directory')
    root = root.resolve()
    require(root != Path('/'), 'Live root is not allowed')
    target = root / LIBRARY
    require(target.is_file() and not target.is_symlink() and
            target.resolve().is_relative_to(root), 'Invalid library path')
    backup = args.backup
    require(backup.is_absolute(), 'Backup must be absolute')
    require(not backup.resolve().is_relative_to(root), 'Backup must be outside build tree')
    for relative, expected in BASELINE.items():
        f = root / relative
        require(f.is_file() and not f.is_symlink() and
                f.resolve().is_relative_to(root) and digest(f.read_bytes()) == expected,
                'V12 baseline mismatch: ' + relative)
    if args.restore:
        require(digest(target.read_bytes()) in (CANDIDATE_SHA, SOURCE_SHA),
                'Restore expects the V13 candidate or original V12 after interrupted rollback')
        original_path = backup / 'libqti-perfd-client_system.so'
        require(original_path.is_file() and not original_path.is_symlink(), 'Missing backup')
        original = original_path.read_bytes()
        require(digest(original) == SOURCE_SHA, 'Backup hash mismatch')
        meta = json.loads((backup / 'metadata.json').read_text())
        rewrite(target, original, meta)
        print('V12 PERF LIBRARY RESTORED. NO FLASH PERFORMED.')
        return
    require(not backup.exists(), 'Backup already exists; not applying twice')
    meta = metadata(target)
    original = target.read_bytes()
    candidate = patched(original)
    backup.mkdir(parents=True)
    with (backup / 'libqti-perfd-client_system.so').open('xb') as f:
        f.write(original)
        f.flush()
        os.fsync(f.fileno())
    (backup / 'metadata.json').write_text(json.dumps(meta, indent=2) + '\n')
    require(digest((backup / 'libqti-perfd-client_system.so').read_bytes()) == SOURCE_SHA,
            'Backup verification failed')
    try:
        rewrite(target, candidate, meta)
    except Exception:
        rewrite(target, original, meta)
        raise
    print('V13 OFFLINE TREE PREPARED. SHA256:', CANDIDATE_SHA)
    print('BACKUP AND METADATA VERIFIED. NO FLASH PERFORMED.')


if __name__ == '__main__':
    main()
