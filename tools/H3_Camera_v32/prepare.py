#!/usr/bin/env python3
"""Persist the user-tested V31 Camera 6.2 APK in the existing V30 offline app."""
from pathlib import Path
import base64
import hashlib
import json
import os
import shutil
import stat
import zipfile

TREE = Path("/linux/build/hyperos3-ginkgo-v1")
REFERENCE = Path("/reference")
OUT = Path("/out")
SOURCE = REFERENCE / "camera-v31/pro-test-v1/MiuiCamera-6.2-ginkgo-pro-test.apk"
BASE_REPORT = REFERENCE / "camera-v30/validation.json"
TARGET = TREE / "product/app/GinkgoMiCamera6Test/MiuiCamera.apk"
BACKUP = Path("/linux/backups/hyperos3-camera-v32")
OLD_SHA = "76cff12c13114e17d2ac9c33622e3f7476a186d3b9df78e768bc3b28dc0ecdd0"
NEW_SHA = "815f14e8419f55f23dfa58e796c7462c813a941417455e1d3e17cf7d2eba1186"
POLICY_SHA = "d38305ac8bff790d9f18ec8541e412ce05344a43827c6fda73ff7d12146e952a"
ORIGINAL_SHA = "48a12d13da98f2e683b185476b9a5516251bcef80fe19aec0ecfde22876d51c5"

def digest(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def metadata(p):
    s = p.stat()
    return {"uid": s.st_uid, "gid": s.st_gid, "mode": stat.S_IMODE(s.st_mode),
            "inode": s.st_ino,
            "xattrs": {k: base64.b64encode(os.getxattr(p,k)).decode()
                       for k in sorted(os.listxattr(p))}}

def rewrite(source, target):
    # Opening the existing inode preserves ownership, mode and SELinux label.
    with source.open("rb") as src, target.open("r+b") as dst:
        dst.seek(0)
        shutil.copyfileobj(src, dst, 8*1024*1024)
        dst.truncate()
        dst.flush()
        os.fsync(dst.fileno())

def main():
    if BACKUP.exists() or (OUT/"validation.json").exists():
        raise RuntimeError("Output/backup exists; refusing overwrite")
    if digest(SOURCE) != NEW_SHA or TARGET.is_symlink() or digest(TARGET) != OLD_SHA:
        raise RuntimeError("Camera APK baseline mismatch")
    report = json.loads(BASE_REPORT.read_text())
    if report.get("status") != "OFFLINE_SYSTEM_TEST_INSTALLED_NOT_BOOT_TESTED" or report.get("package") != "com.ginkgo.micamera6test" or report.get("apk_sha256") != OLD_SHA:
        raise RuntimeError("V30 validation mismatch")
    if len(report["files"]) != 44:
        raise RuntimeError("Unexpected V30 file count")
    for item in report["files"]:
        rel = Path(item["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise RuntimeError("Invalid reference path")
        p = TREE / rel
        if p.is_symlink() or digest(p) != item["sha256"]:
            raise RuntimeError("V30 file changed: " + str(rel))
    if digest(TREE/"odm/etc/selinux/precompiled_sepolicy") != POLICY_SHA:
        raise RuntimeError("Policy changed")
    if digest(TREE/"product/priv-app/MiuiCamera/MiuiCamera.apk") != ORIGINAL_SHA:
        raise RuntimeError("Original donor camera changed")
    # V31 changes only classes2.dex: ensure existing manifest, resources,
    # model-gate patch and all bundled native libraries stay byte-identical.
    with zipfile.ZipFile(TARGET) as old, zipfile.ZipFile(SOURCE) as new:
        old_names = {n for n in old.namelist() if not n.startswith("META-INF/")}
        new_names = {n for n in new.namelist() if not n.startswith("META-INF/")}
        if old_names != new_names:
            raise RuntimeError("Unexpected APK entry-set change")
        for name in old_names - {"classes2.dex"}:
            if old.read(name) != new.read(name):
                raise RuntimeError("Unintended APK entry change: " + name)
        for name in sorted(n for n in new_names if n.startswith("lib/") and n.endswith(".so")):
            p = TARGET.parent/"lib/arm64"/Path(name).name
            if hashlib.sha256(new.read(name)).hexdigest() != digest(p):
                raise RuntimeError("Bundled native library mismatch")
    before = metadata(TARGET)
    if {"security.ima", "security.evm", "security.capability"} & set(before["xattrs"]):
        raise RuntimeError("Unexpected integrity/capability xattrs")
    BACKUP.mkdir(parents=True)
    backup_apk = BACKUP/"MiuiCamera-v30.apk"
    shutil.copyfile(TARGET, backup_apk)
    if digest(backup_apk) != OLD_SHA:
        raise RuntimeError("Backup hash mismatch")
    (BACKUP/"metadata.json").write_text(json.dumps(before, indent=2)+"\n")
    (BACKUP/"v30-validation.json").write_text(BASE_REPORT.read_text())
    changed = False
    try:
        changed = True
        rewrite(SOURCE, TARGET)
        if digest(TARGET) != NEW_SHA or metadata(TARGET) != before:
            raise RuntimeError("New APK/metadata verification failed")
        for item in report["files"]:
            if item["path"] == str(TARGET.relative_to(TREE)):
                item["sha256"] = NEW_SHA
        report.update({
            "status": "OFFLINE_WORKING_CAMERA_V31_SYNCED_NOT_BOOT_TESTED",
            "apk_sha256": NEW_SHA, "previous_apk_sha256": OLD_SHA,
            "backup": str(BACKUP), "user_reported_v31_working": True,
            "fresh_image_boot_tested": False, "package_identity_changed": False,
            "original_camera_removed": False, "app_label_changed": False
        })
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT/"validation.json").write_text(json.dumps(report, indent=2)+"\n")
    except BaseException:
        if changed:
            rewrite(backup_apk, TARGET)
            if digest(TARGET) != OLD_SHA or metadata(TARGET) != before:
                raise RuntimeError("Rollback verification failed; inspect backup")
        raise
    print("CALISAN V31 KAMERA APK ROM AGACINA YERLESTIRILDI")
    print("SHA256:", NEW_SHA)
    print("V30 APK YEDEGI, INODE VE ETIKETLER DOGRULANDI.")
    print("MEVCUT DONOR KAMERA KORUNDU. TELEFONA YAZILMADI.")

if __name__ == "__main__":
    main()
