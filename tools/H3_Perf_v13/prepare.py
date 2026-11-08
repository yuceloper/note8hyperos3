"""Build a pinned ARM64 perf lookup experiment; never installs or flashes."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

SOURCE_SHA = '0b2ffd2e0ae31e3907b07f9060eb3284b611f27a44d7aa5bcdf72ac0de0192b3'
CANDIDATE_SHA = 'c03f761417871e9b14102cf49669bff8bd60c12715b26b8b9a617cb8e3d6675a'
SOURCE_SIZE = 94800
REPLACEMENT = bytes.fromhex('5f2403d5e0031f2ac0035fd6')
PATCHES = (
    (0x8f7c, 'isHalTypeAidl', '3f2303d5ff4302d1fd7b06a9'),
    (0x9168, 'getPerfAidlAndLinkToDeath', '3f2303d5ff0303d1fd7b08a9'),
    (0x9e04, 'getPerfServiceAndLinkToDeath', '3f2303d5ff8302d1fd7b06a9'),
    (0xee94, 'getPerfServiceAndLinkToDeathV2_3', '3f2303d5ff8303d1fd7b0aa9'),
)


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def patched(data):
    require(len(data) == SOURCE_SIZE and digest(data) == SOURCE_SHA,
            'Unexpected source: no patch applied')
    require(data[:6] == b'\x7fELF\x02\x01' and
            struct.unpack_from('<H', data, 18)[0] == 183,
            'Expected little-endian ELF64 AArch64')
    result = bytearray(data)
    for offset, name, original in PATCHES:
        require(data[offset:offset + 12] == bytes.fromhex(original),
                'Entry mismatch: ' + name)
        result[offset:offset + 12] = REPLACEMENT
    result = bytes(result)
    allowed = {i for offset, _, _ in PATCHES for i in range(offset, offset + 12)}
    require(all(a == b or i in allowed for i, (a, b) in
                enumerate(zip(data, result))), 'Unexpected changed byte')
    require(digest(result) == CANDIDATE_SHA, 'Candidate hash mismatch')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(not args.source.is_symlink(), 'Source must be a regular file')
    data = args.source.read_bytes()
    candidate = patched(data)
    require(not args.out.exists(), 'Output already exists; choose a new directory')
    args.out.mkdir(parents=True)
    output = args.out / 'libqti-perfd-client_system.so'
    with output.open('xb') as f:
        f.write(candidate)
    require(output.read_bytes() == candidate, 'Output verification failed')
    report = {
        'status': 'OFFLINE_PREPARED_NOT_DEVICE_TESTED',
        'source_sha256': SOURCE_SHA,
        'candidate_sha256': CANDIDATE_SHA,
        'bytes': len(candidate),
        'instruction_ranges_replaced': 4,
        'range_bytes': 12,
        'behavior': 'BTI c; mov w0, wzr; ret (false / service unavailable)',
        'patches': [{'offset': hex(o), 'function': n, 'old': old,
                     'new': REPLACEMENT.hex()} for o, n, old in PATCHES],
        'outside_patch_ranges_unchanged': True,
        'phone_test': 'NOT_RUN',
    }
    (args.out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
