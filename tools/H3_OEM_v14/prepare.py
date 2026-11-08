#!/usr/bin/env python3
"""Prepare an offline, hash-pinned OEM unsupported-response experiment. No adb/flash."""
import argparse
import hashlib
import json
from pathlib import Path

SOURCE = "81dfdda1848b39995ccabe99a04c616972f6330372ce69c3ed724781bc3a82d8"
CANDIDATE = "68f026e5d2a3da6c2ddb451d847e6624ffb19ce43f7a767d8bd85ec20417ef7b"
SIZE = 33462032
OFFSET = 0x1b51820
OLD = bytes.fromhex("e8f340f9002140b9e11742b9e2fb40f9e30341f95715079401000014e8f740f95efcff9701000014")
NEW = bytes.fromhex("280142511fa90a7140a4ff54e8f340f9002140b9e11742b9e2fb40f9e30341f95415079493fdff17")

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
    ap.add_argument("--out", default="out/oem-v14-offline")
    args = ap.parse_args()
    original = Path(args.source).read_bytes()
    candidate = prepare(original)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    path = out / "libril-qc-hal-qmi.so"
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
        "request_id": "0x802aa",
        "response": "Existing vendor REQUEST_NOT_SUPPORTED callback, error 6",
        "modified_region_bytes": len(NEW),
        "changed_byte_values": sum(a != b for a, b in zip(OLD, NEW)),
        "installed": False,
        "flashed": False,
    }
    (out / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("V14 OEM OFFLINE ADAYI HAZIR")
    print("SHA256:", CANDIDATE)
    print("Calisma agacina veya vendor imajina kurulmadı. Telefona yazilmadi.")

if __name__ == "__main__":
    main()
