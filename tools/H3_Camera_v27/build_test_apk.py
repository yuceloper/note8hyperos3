#!/usr/bin/env python3
"""Build a separately named diagnostic APK; never installs or changes the ROM."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

OLD = "com.android.camera"
NEW = "com.ginkgo.anxtest"
A = "{http://schemas.android.com/apk/res/android}"
EXPECTED = "1865a651c7ac8df642e599e61ef25952a0c0dbd1b6e7b2ef46c3cb050088c535"
from axml_patch import patch_manifest

def digest(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def run(*args):
    subprocess.run(list(map(str, args)), check=True, stdin=subprocess.DEVNULL)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    ref, out = args.reference.resolve(), args.out.resolve()
    if out.exists() or ref == out or ref in out.parents or out in ref.parents:
        raise SystemExit("Output must be new and separate")
    report = json.loads((ref / "validation.json").read_text())
    if report.get("status") != "REVIEW_CANDIDATE_NOT_INSTALLABLE":
        raise SystemExit("Unexpected reference status")
    for item in report["files"]:
        rel = Path(item["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise SystemExit("Invalid reference path")
        file = ref / rel
        if file.is_symlink() or not file.is_file() or digest(file) != item["sha256"]:
            raise SystemExit("Reference changed: " + str(rel))
    apk = ref / "app/ANXCamera.apk"
    if digest(apk) != EXPECTED:
        raise SystemExit("APK hash mismatch")
    for tool in ("aapt", "zipalign", "apksigner", "keytool"):
        if not shutil.which(tool):
            raise SystemExit("Missing tool: " + tool)
    out.mkdir(parents=True)
    libs = ref / "app/lib/arm64"
    sources = sorted(libs.glob("*.so"))
    if len(sources) != 62 or any(p.name == "libcameraservice.so" for p in sources):
        raise RuntimeError("Unexpected library selection")
    unsigned, aligned = out / "unsigned.apk", out / "aligned.apk"
    with zipfile.ZipFile(apk) as original, zipfile.ZipFile(unsigned, "w") as rebuilt:
        patched = patch_manifest(original.read("AndroidManifest.xml"))
        for item in original.infolist():
            if item.filename.startswith("META-INF/") and (
                item.filename.upper().endswith((".RSA", ".DSA", ".EC", ".SF"))
                or item.filename.upper() == "META-INF/MANIFEST.MF"
            ):
                continue
            if item.filename.startswith("lib/"):
                raise RuntimeError("Unexpected native files in source APK")
            data = patched if item.filename == "AndroidManifest.xml" else original.read(item.filename)
            rebuilt.writestr(item, data)
        for lib in sources:
            rebuilt.write(lib, "lib/arm64-v8a/" + lib.name,
                          compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(apk) as before, zipfile.ZipFile(unsigned) as after:
        dex_names = [name for name in before.namelist()
                     if re.fullmatch(r"classes[0-9]*\.dex", name)]
        if not dex_names:
            raise RuntimeError("Source contains no DEX")
        for name in dex_names:
            if before.read(name) != after.read(name):
                raise RuntimeError("DEX unexpectedly changed: " + name)
        if before.read("resources.arsc") != after.read("resources.arsc"):
            raise RuntimeError("Resource table unexpectedly changed")
        for lib in sources:
            if after.read("lib/arm64-v8a/" + lib.name) != lib.read_bytes():
                raise RuntimeError("Native library changed")
    badging = subprocess.check_output(["aapt", "dump", "badging", str(unsigned)], text=True)
    if not re.search(r"^package: name='" + re.escape(NEW) + "'", badging, re.M):
        raise RuntimeError("Built APK identity mismatch")
    run("zipalign", "4", unsigned, aligned)
    key = out / "diagnostic-only.jks"
    run("keytool", "-genkeypair", "-keystore", key, "-storetype", "JKS",
        "-storepass", "android", "-keypass", "android", "-alias", "anxtest",
        "-keyalg", "RSA", "-keysize", "2048", "-validity", "3650",
        "-dname", "CN=Ginkgo ANX Diagnostic Only", "-noprompt")
    signed = out / "ANXCamera-ginkgo-test.apk"
    run("apksigner", "sign", "--ks", key, "--ks-key-alias", "anxtest",
        "--ks-pass", "pass:android", "--key-pass", "pass:android",
        "--out", signed, aligned)
    run("apksigner", "verify", "--verbose", signed)
    run("zipalign", "-c", "4", signed)
    result = {
        "status": "DIAGNOSTIC_APK_BUILT_NOT_DEVICE_TESTED",
        "package": NEW, "source_apk_sha256": EXPECTED,
        "apk_sha256": digest(signed),
        "native_libraries": len(sources),
        "original_dex_preserved": True,
        "manifest_method": "binary_string_pool_and_attributes",
        "original_camera_modified": False,
        "privileged_permissions_granted": False,
        "policy_changed": False,
        "limitations": [
            "Package-name literals in original code are unchanged and may break this fork",
            "User-app linker namespace differs from shell test",
            "System device-feature files and privileged permissions are not installed",
            "Successful build does not establish camera compatibility"
        ]
    }
    (out / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print("DIAGNOSTIC APK:", signed)
    print("PACKAGE:", NEW)
    print("SHA256:", result["apk_sha256"])
    print("NOT INSTALLED. ORIGINAL CAMERA UNCHANGED.")

if __name__ == "__main__":
    main()
