#!/usr/bin/env python3
"""Collect donor MTD dependency closure for offline analysis, never install it."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct

def needed(path):
    b = path.read_bytes()
    if b[:6] != b'\x7fELF\x02\x01':
        raise ValueError('Expected ELF64 little endian: ' + str(path))
    offset = struct.unpack_from('<Q', b, 40)[0]
    size, count = struct.unpack_from('<HH', b, 58)
    if size < 64 or offset + size * count > len(b):
        raise ValueError('Invalid ELF section table')
    sections = [struct.unpack_from('<IIQQQQIIQQ', b, offset + i * size)
                for i in range(count)]
    result = []
    for s in sections:
        if s[1] != 6:
            continue
        strings = sections[s[6]]
        start, end = strings[4], strings[4] + strings[5]
        for p in range(s[4], s[4] + s[5], 16):
            tag, value = struct.unpack_from('<qQ', b, p)
            if tag == 1:
                name_start = start + value
                name_end = b.find(b'\0', name_start, end)
                if name_end < name_start:
                    raise ValueError('Invalid DT_NEEDED')
                result.append(b[name_start:name_end].decode())
    return result

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    base, out = args.source.resolve(strict=True), args.out
    roots = [base / p for p in ('odm/lib64', 'vendor/lib64',
             'system_ext/lib64', 'system/system/lib64', 'product/lib64')]
    def resolve(name):
        for root in roots:
            p = root / name
            if p.is_file() and p.resolve().is_relative_to(base):
                return p
        return None
    queue = [base / 'odm/bin/mtd@1.3']
    if not queue[0].is_file():
        raise SystemExit('Donor MTD executable missing')
    out.mkdir(parents=True, exist_ok=False)
    visited, records, missing = set(), [], []
    external = {'libc.so', 'libm.so', 'libdl.so', 'libdl_android.so'}
    while queue:
        p = queue.pop(0)
        if p in visited:
            continue
        visited.add(p)
        deps = needed(p)
        relative = p.relative_to(base)
        target = out / 'files' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
        metadata = p.stat()
        attrs = {k: base64.b64encode(os.getxattr(p, k)).decode()
                 for k in os.listxattr(p)}
        records.append({'file': str(relative), 'sha256': hashlib.sha256(
            target.read_bytes()).hexdigest(), 'needed': deps,
            'mode': metadata.st_mode & 0o7777, 'uid': metadata.st_uid,
            'gid': metadata.st_gid, 'xattrs_base64': attrs})
        for name in deps:
            if name in external:
                continue
            dependency = resolve(name)
            if dependency is None:
                missing.append({'needed_by': str(relative), 'library': name})
            else:
                queue.append(dependency)
    for name in ('vendor_file_contexts', 'vendor_hwservice_contexts',
                 'vendor_service_contexts', 'vendor_property_contexts',
                 'vendor_sepolicy.cil'):
        relative = Path('vendor/etc/selinux') / name
        p = base / relative
        if p.is_file():
            target = out / 'files' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, target)
            records.append({'file': str(relative), 'kind': 'policy_reference',
                            'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
    report = {'status': 'REFERENCE_ONLY_NOT_INSTALLED', 'files': records,
              'runtime_external': sorted(external), 'unresolved': missing,
              'selection_order': [str(p.relative_to(base)) for p in roots]}
    (out / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print('TOPLANAN ELF:', len(visited))
    print('COZULEMEYEN BAGIMLILIK:', len(missing))
    print('Yalniz inceleme paketi. Calisma agaci ve telefon degistirilmedi.')

if __name__ == '__main__':
    main()
