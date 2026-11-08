#!/usr/bin/env python3
"""Prepare an offline, hash-pinned Bluetooth ConfigStore registration experiment. No adb/flash."""
import argparse
import hashlib
import json
from pathlib import Path

SOURCE = "a96b72946f161eb0e585a86386d0913175c40ecb88da66853434fddaf86a0b7b"
CANDIDATE = "fd4ef96ba17e49eb259bbe673d7b7709dc1e40badc961e8bd3d6caa997cab59a"
SIZE = 15912
OFFSET = 0x22ec
OLD = bytes.fromhex("b3070034")
NEW = bytes.fromhex("1f2003d5")

def prepare(data):
    if len(data) != SIZE or hashlib.sha256(data).hexdigest() != SOURCE:
        raise ValueError("Kaynak hash/boyut beklenen Lineage kutuphanesiyle eslesmiyor.")
    if data[OFFSET:OFFSET + len(OLD)] != OLD:
        raise ValueError("Orijinal ARM64 talimatlari eslesmiyor.")
    candidate = data[:OFFSET] + NEW + data[OFFSET + len(OLD):]
    if hashlib.sha256(candidate).hexdigest() != CANDIDATE:
        raise ValueError("Aday hash dogrulamasi basarisiz.")
    return candidate

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True)
    ap.add_argument("--out", default="out/bluetooth-v15-offline")
    args = ap.parse_args()
    original = Path(args.source).read_bytes()
    candidate = prepare(original)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    path = out / "android.hardware.bluetooth@1.0-service-qti"
    path.write_bytes(candidate)
    report = {
        "status": "OFFLINE_CANDIDATE_NOT_DEVICE_TESTED",
        "source_sha256": SOURCE,
        "candidate_sha256": CANDIDATE,
        "size": SIZE,
        "offset": OFFSET,
        "virtual_address": OFFSET,
        "original_hex": OLD.hex(),
        "replacement_hex": NEW.hex(),
        "changed_gate": "ConfigStore registration enhanced-framework gate only",
        "behavior": "Register existing ConfigStore 2.0 implementation; existing 1.0 fallback preserved",
        "modified_region_bytes": len(NEW),
        "changed_byte_values": sum(a != b for a, b in zip(OLD, NEW)),
        "installed": False,
        "flashed": False,
    }
    (out / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("V15 BLUETOOTH OFFLINE ADAYI HAZIR")
    print("SHA256:", CANDIDATE)
    print("Calisma agacina veya vendor imajina kurulmadı. Telefona yazilmadi.")

if __name__ == "__main__":
    main()


