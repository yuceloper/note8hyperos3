#!/usr/bin/env python3
"""Freeze an ANXCamera review candidate. Does not install or flash."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

APK_SHA = "1865a651c7ac8df642e599e61ef25952a0c0dbd1b6e7b2ef46c3cb050088c535"

def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    out = args.out.resolve()
    if out.exists():
        raise SystemExit("Output already exists; refusing overwrite")
    if source == out or source in out.parents or out in source.parents:
        raise SystemExit("Source/output must be separate")
    app = source / "proprietary/system/priv-app/ANXCamera"
    apk = app / "ANXCamera.apk"
    if not apk.is_file() or sha(apk) != APK_SHA:
        raise SystemExit("APK source hash mismatch")
    files = [(apk, Path("app/ANXCamera.apk"))]
    libs = sorted(p for p in (app / "lib/arm64").glob("*.so")
                  if not p.name.startswith("._"))
    if len(libs) != 63:
        raise SystemExit("Expected exactly 63 arm64 source libraries")
    excluded = []
    for p in libs:
        if p.is_symlink():
            raise SystemExit("Unexpected symlink: " + str(p))
        with p.open("rb") as f:
            header = f.read(20)
        if (header[:5] != b"\x7fELF\x02" or
                int.from_bytes(header[18:20], "little") != 183):
            raise SystemExit("Not AArch64 ELF: " + str(p))
        if p.name == "libcameraservice.so":
            excluded.append({"path": str(p.relative_to(source)), "sha256": sha(p)})
            continue
        files.append((p, Path("app/lib/arm64") / p.name))
    for name in ("features/ginkgo.xml",
                 "features/cheatcodes/cheatcodes.json",
                 "proprietary/system/etc/permissions/privapp-permissions_com.android.camera.xml"):
        p = source / name
        if not p.is_file() or p.is_symlink():
            raise SystemExit("Missing/invalid reference: " + name)
        files.append((p, Path("review-only") / name))
    for p, _ in files:
        if p.is_symlink():
            raise SystemExit("Unexpected source symlink")
    out.mkdir(parents=True)
    manifest = []
    for src, rel in files:
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        expected = sha(src)
        if sha(dst) != expected:
            raise RuntimeError("Copy verification failed: " + str(rel))
        manifest.append({"path": str(rel), "sha256": expected,
                         "size": dst.stat().st_size})
    report = {
        "status": "REVIEW_CANDIDATE_NOT_INSTALLABLE",
        "apk_package": "com.android.camera",
        "apk_sha256": APK_SHA,
        "arm64_library_count": len(libs) - len(excluded),
        "excluded": excluded,
        "files": manifest,
        "pending": [
            "Separate package identity or controlled system replacement with signature/data handling",
            "APK signing and app linker namespace validation",
            "Actual JNI/symbol compatibility and camera capture tests",
            "Optional mode dependencies and narrowly scoped permissions"
        ],
        "policy_imported": False,
        "system_tree_modified": False,
        "phone_modified": False
    }
    (out / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "README.txt").write_text(
        "REVIEW ONLY. This is not an installable APK or ROM image.\n"
        "The original signed APK is unchanged. No policy or global properties applied.\n"
        "libcameraservice.so excluded. Review-only XML/JSON is not installed.\n"
    )
    print("V27 CAMERA REVIEW CANDIDATE PREPARED")
    print("APK SHA256:", APK_SHA)
    print("Arm64 libraries:", report["arm64_library_count"])
    print("NOT INSTALLED. NOT FLASHED. SIGNATURE CONFLICT REMAINS.")
    print("Report:", out / "validation.json")

if __name__ == "__main__":
    main()
