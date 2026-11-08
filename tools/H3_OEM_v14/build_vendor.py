#!/usr/bin/env python3
"""Build a separate ext4 vendor experiment by patching mapped data blocks only."""
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

from prepare import prepare, SOURCE, CANDIDATE, OFFSET, OLD, NEW

EXPECTED_IMAGE_HASH = "e8f49bb8c25cb983caee5249ba08b4c72c74fa68600538d13e5fa5e69fd505f6"
TARGET = "/lib64/libril-qc-hal-qmi.so"

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def debug(image, command):
    r = subprocess.run(["debugfs", "-R", command, str(image)],
                       capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise RuntimeError(r.stdout + r.stderr)
    return r.stdout

def fscheck(image, log):
    r = subprocess.run(["e2fsck", "-f", "-n", str(image)],
                       capture_output=True, text=True, timeout=300)
    log.write_text(r.stdout + r.stderr)
    if r.returncode:
        raise RuntimeError("Salt okunur e2fsck basarisiz: " + str(log))

def build(image, candidate_path, out):
    image = image.resolve(strict=True)
    if not image.is_file():
        raise ValueError("Girdi normal bir imaj dosyasi olmali.")
    if digest(image) != EXPECTED_IMAGE_HASH:
        raise ValueError("Lineage vendor imajinin SHA256 degeri eslesmiyor.")
    candidate = candidate_path.read_bytes()
    if hashlib.sha256(candidate).hexdigest() != CANDIDATE:
        raise ValueError("V14 aday kutuphane hash degeri eslesmiyor.")
    with image.open("rb") as stream:
        stream.seek(1024)
        sb = stream.read(1024)
    if len(sb) != 1024 or struct.unpack_from("<H", sb, 56)[0] != 0xef53:
        raise ValueError("Ham ext4 imaji gerekli; sparse/EROFS kabul edilmez.")
    log_block_size = struct.unpack_from("<I", sb, 24)[0]
    if log_block_size > 6:
        raise ValueError("Gecersiz blok boyutu.")
    block_size = 1024 << log_block_size
    if struct.unpack_from("<I", sb, 100)[0] & 0x200:
        raise ValueError("Bigalloc imaj desteklenmiyor.")
    stat_before = debug(image, "stat " + TARGET)
    flags = re.search(r"Flags:\s*(0x[0-9a-fA-F]+)", stat_before)
    if not flags or int(flags.group(1), 16) & 0x100800:
        raise ValueError("Inode flags okunamadi veya verity/encryption etkin.")
    ea_before = debug(image, "ea_list " + TARGET)
    if "security.ima" in ea_before or "security.evm" in ea_before:
        raise ValueError("Icerige bagli IMA/EVM etiketi var.")
    out.mkdir(parents=True, exist_ok=False)
    fscheck(image, out / "source-e2fsck.txt")
    with tempfile.TemporaryDirectory(prefix="h3-oem-") as td:
        extracted = Path(td) / "source.so"
        debug(image, "dump " + TARGET + " " + str(extracted))
        original = extracted.read_bytes()
        if prepare(original) != candidate:
            raise ValueError("Imagdaki kutuphane ile aday eslesmiyor.")
        spans = []
        done = 0
        while done < len(OLD):
            logical, intra = divmod(OFFSET + done, block_size)
            raw = debug(image, "bmap " + TARGET + " " + str(logical)).strip()
            if not re.fullmatch(r"[0-9]+", raw) or int(raw) == 0:
                raise ValueError("Fiziksel blok eslemesi okunamadi: " + raw)
            physical = int(raw) * block_size + intra
            count = min(len(OLD) - done, block_size - intra)
            if physical + count > image.stat().st_size:
                raise ValueError("Esleme imaj sinirini asiyor.")
            spans.append((physical, done, count))
            done += count
        partial = out / "vendor-ginkgo-v14.img.partial"
        print("AYRI VENDOR KOPYASI HAZIRLANIYOR", flush=True)
        with image.open("rb") as src, partial.open("xb") as dst:
            shutil.copyfileobj(src, dst, 8 * 1024 * 1024)
        with partial.open("r+b") as stream:
            for physical, start, count in spans:
                stream.seek(physical)
                if stream.read(count) != OLD[start:start + count]:
                    raise ValueError("Fiziksel bloktaki orijinal baytlar eslesmiyor.")
                stream.seek(physical)
                stream.write(NEW[start:start + count])
        # Full-image comparison: changes are permitted only in mapped patch bytes.
        allowed = {p + j for p, _, n in spans for j in range(n)}
        changed = 0
        position = 0
        with image.open("rb") as a, partial.open("rb") as b:
            while True:
                left, right = a.read(4 * 1024 * 1024), b.read(4 * 1024 * 1024)
                if len(left) != len(right):
                    raise ValueError("Imaj boyutu degisti.")
                if not left:
                    break
                if left != right:
                    for j, (x, y) in enumerate(zip(left, right)):
                        if x != y:
                            if position + j not in allowed:
                                raise ValueError("Yama disinda imaj degisikligi var.")
                            changed += 1
                position += len(left)
        if changed != sum(x != y for x, y in zip(OLD, NEW)):
            raise ValueError("Degisen bayt sayisi beklenenden farkli.")
        if debug(partial, "stat " + TARGET) != stat_before:
            raise ValueError("Inode metadata degisti.")
        if debug(partial, "ea_list " + TARGET) != ea_before:
            raise ValueError("Extended attribute/SELinux metadata degisti.")
        verify = Path(td) / "candidate.so"
        debug(partial, "dump " + TARGET + " " + str(verify))
        if digest(verify) != CANDIDATE:
            raise ValueError("Imadan geri okunan aday hash degeri eslesmiyor.")
        fscheck(partial, out / "candidate-e2fsck.txt")
        if digest(image) != EXPECTED_IMAGE_HASH:
            raise ValueError("Kaynak imaj degismis.")
        image_hash = digest(partial)
        final = out / "vendor-ginkgo-v14.img"
        partial.rename(final)
        report = {
            "status": "OFFLINE_IMAGE_NOT_FLASHED_NOT_BOOT_TESTED",
            "source_image_sha256": EXPECTED_IMAGE_HASH,
            "candidate_image_sha256": image_hash,
            "source_library_sha256": SOURCE,
            "candidate_library_sha256": CANDIDATE,
            "image_bytes": final.stat().st_size,
            "changed_byte_values": changed,
            "physical_spans": spans,
            "inode_and_xattrs_unchanged": True,
            "full_image_diff_checked": True,
            "read_only_fscheck_passed": True,
            "flashed": False,
        }
        (out / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
        print("V14 VENDOR TEST IMAJI HAZIR", flush=True)
        print("SHA256:", image_hash)
        print("IZINLER, INODE VE SELINUX METADATA KORUNDU.")
        print("TELEFONA YAZILMADI.")

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--image", required=True, type=Path)
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    build(args.image, args.candidate, args.out)

if __name__ == "__main__":
    main()
