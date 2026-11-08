"""Offline regression checks. Requires the exact local original library."""
import argparse
import contextlib
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
import install
from prepare import CANDIDATE_SHA, SOURCE_SHA, PATCHES, patched, digest


def check(ok, message):
    if not ok:
        raise RuntimeError(message)


def fail(call, message):
    try:
        call()
    except (RuntimeError, FileNotFoundError):
        return
    raise RuntimeError(message)


def sections(data):
    off = struct.unpack_from('<Q', data, 40)[0]
    size, count, string_index = struct.unpack_from('<HHH', data, 58)
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, off + i * size)
               for i in range(count)]
    strings_header = headers[string_index]
    strings = data[strings_header[4]:strings_header[4] + strings_header[5]]
    return {strings[h[0]:].split(b'\0')[0].decode():
            (None if h[1] == 8 else data[h[4]:h[4] + h[5]]) for h in headers}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    args = p.parse_args()
    source = args.source.read_bytes()
    candidate = patched(source)
    check(digest(source) == SOURCE_SHA and digest(candidate) == CANDIDATE_SHA,
          'Pinned hash check failed')
    old_sections, new_sections = sections(source), sections(candidate)
    check(old_sections.keys() == new_sections.keys(), 'Section list changed')
    check([n for n in old_sections if old_sections[n] != new_sections[n]] == ['.text'],
          'Non-code sections changed')
    fail(lambda: patched(candidate), 'Double patch was accepted')
    fail(lambda: patched(source[:-1]), 'Truncated source was accepted')
    changed = bytearray(source)
    changed[0x8000] ^= 1
    fail(lambda: patched(bytes(changed)), 'Unknown source was accepted')
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = base / 'tree'
        target = root / install.LIBRARY
        target.parent.mkdir(parents=True)
        target.write_bytes(source)
        target.chmod(0o640)
        os.setxattr(target, 'user.perf-v13-test', b'keep-this')
        probe = root / 'baseline'
        probe.write_bytes(b'fixture baseline')
        real_baseline = install.BASELINE
        real_argv = sys.argv
        install.BASELINE = {'baseline': digest(probe.read_bytes())}
        backup = base / 'backup'

        def run(restore=False):
            sys.argv = ['install.py', '--root', str(root), '--backup', str(backup)]
            if restore:
                sys.argv.append('--restore')
            with contextlib.redirect_stdout(io.StringIO()):
                install.main()

        try:
            probe.write_bytes(b'wrong baseline')
            fail(run, 'Wrong baseline was accepted')
            check(not backup.exists() and target.read_bytes() == source,
                  'Baseline rejection mutated the tree')
            probe.write_bytes(b'fixture baseline')
            before = install.metadata(target)
            run()
            check(target.read_bytes() == candidate, 'Install content mismatch')
            after = install.metadata(target)
            check(all(before[k] == after[k] for k in
                      ('uid', 'gid', 'mode', 'xattrs', 'mtime_ns')),
                  'Install did not preserve metadata')
            fail(run, 'Double install was accepted')
            run(restore=True)
            check(target.read_bytes() == source, 'Restore mismatch')
            after = install.metadata(target)
            check(all(before[k] == after[k] for k in
                      ('uid', 'gid', 'mode', 'xattrs', 'mtime_ns')),
                  'Restore did not preserve metadata')
        finally:
            install.BASELINE = real_baseline
            sys.argv = real_argv
        bad = base / 'bad.so'
        bad.write_bytes(b'bad')
        out = base / 'should-not-exist'
        result = subprocess.run([sys.executable, '-O', str(Path(__file__).with_name('prepare.py')),
                                 '--source', str(bad), '--out', str(out)],
                                capture_output=True)
        check(result.returncode != 0 and not out.exists(),
              'Optimized Python bypassed validation')
    print(json.dumps({'result': 'PASS', 'source_sha256': SOURCE_SHA,
                      'candidate_sha256': CANDIDATE_SHA,
                      'checks': ['pinned source/output hashes', 'only .text changed',
                                 'reject unknown/truncated/already patched input',
                                 'reject invalid tree baseline before writes',
                                 'fixture install/restore bytes and metadata',
                                 'reject double install', 'validation active under python -O'],
                      'limits': 'Temporary fixture uses user xattr, not security.selinux; no Android runtime test'},
                     indent=2))


if __name__ == '__main__':
    main()
