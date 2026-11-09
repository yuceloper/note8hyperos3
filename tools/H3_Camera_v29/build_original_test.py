#!/usr/bin/env python3
"""Build a diagnostic fork of the ORIGINAL HyperOS Camera 6.2 APK."""
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import zipfile
import zlib
from pathlib import Path
from axml_patch import patch_manifest, NEW

SOURCE_SHA = "48a12d13da98f2e683b185476b9a5516251bcef80fe19aec0ecfde22876d51c5"
DEX_SHA = "47e8c8b0adc2362bafa18eb77d0921670e53d30e59709139e0cae3c0d32aa140"
GATE_SHA = "8dfb380a5426ae5d2bd623fa877686b353b9d9327980893f094855ca97f0a12a"
CODE_OFFSET = 4907780

def digest(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def run(*args):
    subprocess.run(list(map(str, args)), check=True, stdin=subprocess.DEVNULL)

def patch_gate(data):
    if hashlib.sha256(data).hexdigest() != DEX_SHA:
        raise RuntimeError("Unexpected original classes3.dex")
    registers, incoming, outgoing, tries, debug, count = struct.unpack_from("<HHHHII", data, CODE_OFFSET)
    if (registers, incoming, outgoing, tries, count) != (1, 0, 1, 0, 14):
        raise RuntimeError("Unexpected model-gate code layout")
    start = CODE_OFFSET + 16
    old = data[start:start+28]
    if hashlib.sha256(old).hexdigest() != GATE_SHA:
        raise RuntimeError("Unexpected model-gate body")
    result = bytearray(data)
    # Lg6/c;->B()Z: const/4 v0, false; return v0; remaining code units are NOP.
    # This removes only the model-error decision in the isolated test APK.
    result[start:start+28] = b"\x12\x00\x0f\x00" + b"\0"*24
    result[12:32] = hashlib.sha1(result[32:]).digest()
    struct.pack_into("<I", result, 8, zlib.adler32(result[12:]) & 0xffffffff)
    if any(not (8 <= i < 32 or start <= i < start+28)
           for i, (a,b) in enumerate(zip(data, result)) if a != b):
        raise RuntimeError("Unexpected DEX modification")
    if hashlib.sha1(result[32:]).digest() != result[12:32]:
        raise RuntimeError("DEX signature verification failed")
    if zlib.adler32(result[12:]) & 0xffffffff != struct.unpack_from("<I", result, 8)[0]:
        raise RuntimeError("DEX checksum verification failed")
    return bytes(result)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    source, out = a.source.resolve(), a.out.resolve()
    if out.exists() or source == out or out in source.parents:
        raise SystemExit("Refusing existing/invalid output")
    if source.is_symlink() or digest(source) != SOURCE_SHA:
        raise SystemExit("Original Camera 6.2 hash mismatch")
    for name in ("aapt", "zipalign", "apksigner", "keytool"):
        if not shutil.which(name):
            raise SystemExit("Missing tool: " + name)
    with zipfile.ZipFile(source) as z:
        native = [n for n in z.namelist() if n.startswith("lib/") and n.endswith(".so")]
        if len(native) != 42 or any(not n.startswith("lib/arm64-v8a/") for n in native):
            raise RuntimeError("Unexpected original native libraries")
        dex = patch_gate(z.read("classes3.dex"))
        manifest = patch_manifest(z.read("AndroidManifest.xml"))
        out.mkdir(parents=True)
        unsigned = out / "unsigned.apk"
        with zipfile.ZipFile(unsigned, "w") as rebuilt:
            for item in z.infolist():
                n = item.filename
                if n.startswith("META-INF/") and (n.upper().endswith((".RSA", ".DSA", ".EC", ".SF")) or n.upper() == "META-INF/MANIFEST.MF"):
                    continue
                data = manifest if n == "AndroidManifest.xml" else dex if n == "classes3.dex" else z.read(n)
                rebuilt.writestr(item, data)
    with zipfile.ZipFile(source) as before, zipfile.ZipFile(unsigned) as after:
        for name in before.namelist():
            if name in ("AndroidManifest.xml", "classes3.dex") or name not in after.namelist():
                continue
            if before.read(name) != after.read(name):
                raise RuntimeError("Unintended APK entry change: " + name)
    badging = subprocess.check_output(["aapt", "dump", "badging", str(unsigned)], text=True)
    if not re.search(r"^package: name='" + re.escape(NEW) + "'", badging, re.M):
        raise RuntimeError("Diagnostic identity verification failed")
    aligned = out / "aligned.apk"
    run("zipalign", "4", unsigned, aligned)
    key = out / "diagnostic-only.jks"
    run("keytool", "-genkeypair", "-keystore", key, "-storetype", "JKS",
        "-storepass", "android", "-keypass", "android", "-alias", "micamera6test",
        "-keyalg", "RSA", "-keysize", "2048", "-validity", "3650",
        "-dname", "CN=Ginkgo Original Camera 6 Diagnostic", "-noprompt")
    signed = out / "MiuiCamera-6.2-ginkgo-test.apk"
    run("apksigner", "sign", "--ks", key, "--ks-key-alias", "micamera6test",
        "--ks-pass", "pass:android", "--key-pass", "pass:android",
        "--out", signed, aligned)
    run("apksigner", "verify", "--verbose", signed)
    run("zipalign", "-c", "4", signed)
    if digest(source) != SOURCE_SHA:
        raise RuntimeError("Source changed")
    report = {
        "status": "ORIGINAL_6_2_MODEL_GATE_DIAGNOSTIC_NOT_DEVICE_TESTED",
        "package": NEW, "source_apk_sha256": SOURCE_SHA,
        "apk_sha256": digest(signed), "native_library_count": 42,
        "changed_dex": "classes3.dex", "changed_method": "Lg6/c;->B()Z",
        "model_profile_added": False, "creek_profile_forced": False,
        "selinux_changed": False, "original_camera_modified": False,
        "limitations": [
            "Only the unsupported-model auto-close decision is disabled",
            "Generic fallback profile remains; no ginkgo hardware tuning is claimed",
            "Package-name literals remain unchanged and may affect the test fork",
            "System-app/hidden API setup and actual capture testing remain pending"
        ]
    }
    (out / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("ORIJINAL KAMERA 6.2 TANI APK HAZIR")
    print("PAKET:", NEW)
    print("SHA256:", report["apk_sha256"])
    print("YALNIZCA MODEL HATASI KARARI DEGISTIRILDI; KAMERA UYUMU HENUZ DOGRULANMADI.")
    print("KAYNAK APK KORUNDU. TELEFONA KURULMADI.")

if __name__ == "__main__":
    main()
