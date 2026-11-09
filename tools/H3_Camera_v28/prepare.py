#!/usr/bin/env python3
"""Add a separate, non-privileged system camera test to the offline tree."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import stat
import zipfile
import xml.etree.ElementTree as ET

TREE = Path("/linux/build/hyperos3-ginkgo-v1")
APK = Path("/reference/test-apk-v2/ANXCamera-ginkgo-test.apk")
OUT = Path("/out")
APP = TREE / "product/app/GinkgoANXTest"
CONFIG = TREE / "product/etc/sysconfig/ginkgo-anx-test-hiddenapi.xml"
EXPECTED = "54274a8e2c2ed971f66bd5332e5ddc687d1d095533f8f45f8d170f0aaf483180"
ORIGINAL = TREE / "product/priv-app/MiuiCamera/MiuiCamera.apk"
ORIGINAL_SHA = "48a12d13da98f2e683b185476b9a5516251bcef80fe19aec0ecfde22876d51c5"
POLICY = TREE / "odm/etc/selinux/precompiled_sepolicy"
POLICY_SHA = "d38305ac8bff790d9f18ec8541e412ce05344a43827c6fda73ff7d12146e952a"
STAGE = Path("/linux/backups/hyperos3-camera-v28-stage")
XML = b'<?xml version="1.0" encoding="utf-8"?>\n<config>\n    <hidden-api-whitelisted-app package="com.ginkgo.anxtest" />\n</config>\n'

def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def metadata(path, mode, context):
    os.chown(path, 0, 0)
    os.chmod(path, mode)
    os.setxattr(path, "security.selinux", context)
    s = path.stat()
    if (s.st_uid, s.st_gid, stat.S_IMODE(s.st_mode)) != (0, 0, mode):
        raise RuntimeError("Metadata verification failed: " + str(path))
    if os.getxattr(path, "security.selinux") != context:
        raise RuntimeError("Label verification failed")

def main():
    if os.geteuid() != 0:
        raise RuntimeError("Container root required for offline metadata")
    for p in (APP, CONFIG, STAGE, OUT / "validation.json"):
        if p.exists() or p.is_symlink():
            raise RuntimeError("Refusing existing output: " + str(p))
    if digest(APK) != EXPECTED or digest(ORIGINAL) != ORIGINAL_SHA:
        raise RuntimeError("APK baseline mismatch")
    if digest(POLICY) != POLICY_SHA:
        raise RuntimeError("Policy baseline mismatch")
    for p in (TREE / "product/app", CONFIG.parent, ORIGINAL.parent):
        if not p.is_dir() or p.is_symlink():
            raise RuntimeError("Unexpected tree layout: " + str(p))
    file_context = os.getxattr(ORIGINAL, "security.selinux")
    dir_context = os.getxattr(ORIGINAL.parent, "security.selinux")
    config_template = next(iter(sorted(CONFIG.parent.glob("*.xml"))), None)
    if config_template is None or config_template.is_symlink():
        raise RuntimeError("Missing sysconfig metadata template")
    config_context = os.getxattr(config_template, "security.selinux")
    records = []
    with zipfile.ZipFile(APK) as z:
        natives = [n for n in z.namelist() if n.startswith("lib/")]
        if len(natives) != 62 or len(set(natives)) != 62:
            raise RuntimeError("Expected 62 unique native libraries")
        for name in natives:
            rel = Path(name)
            if len(rel.parts) != 3 or rel.parts[:2] != ("lib", "arm64-v8a") or rel.suffix != ".so" or rel.name == "libcameraservice.so":
                raise RuntimeError("Unexpected native entry")
        STAGE.mkdir(parents=True)
        staged_app = STAGE / "GinkgoANXTest"
        (staged_app / "lib/arm64").mkdir(parents=True)
        staged_apk = staged_app / "ANXCamera.apk"
        shutil.copyfile(APK, staged_apk)
        for name in natives:
            target = staged_app / "lib/arm64" / Path(name).name
            data = z.read(name)
            if data[:5] != b"\x7fELF\x02" or int.from_bytes(data[18:20], "little") != 183:
                raise RuntimeError("Not AArch64: " + name)
            target.write_bytes(data)
    for p in [staged_app, staged_app / "lib", staged_app / "lib/arm64"]:
        metadata(p, 0o755, dir_context)
    for p in sorted(staged_app.rglob("*")):
        if p.is_file():
            metadata(p, 0o644, file_context)
            records.append({"path": str((APP / p.relative_to(staged_app)).relative_to(TREE)),
                            "sha256": digest(p), "selinux": file_context.rstrip(b"\0").decode()})
    staged_config = STAGE / CONFIG.name
    staged_config.write_bytes(XML)
    metadata(staged_config, 0o644, config_context)
    if len(ET.fromstring(XML)) != 1:
        raise RuntimeError("Invalid sysconfig")
    records.append({"path": str(CONFIG.relative_to(TREE)), "sha256": digest(staged_config),
                    "selinux": config_context.rstrip(b"\0").decode()})
    app_installed = config_installed = False
    try:
        staged_app.rename(APP); app_installed = True
        staged_config.rename(CONFIG); config_installed = True
        for item in records:
            p = TREE / item["path"]
            if digest(p) != item["sha256"] or os.getxattr(p, "security.selinux").rstrip(b"\0").decode() != item["selinux"]:
                raise RuntimeError("Installed file mismatch")
        if digest(ORIGINAL) != ORIGINAL_SHA or digest(POLICY) != POLICY_SHA:
            raise RuntimeError("Baseline changed")
        OUT.mkdir(parents=True, exist_ok=True)
        result = {"status": "OFFLINE_SYSTEM_TEST_INSTALLED_NOT_BOOT_TESTED",
                  "package": "com.ginkgo.anxtest", "apk_sha256": EXPECTED,
                  "original_camera_sha256": ORIGINAL_SHA, "policy_sha256": POLICY_SHA,
                  "files": records, "privileged": False, "policy_changed": False,
                  "global_hidden_api_policy_changed": False,
                  "hidden_api_scope": "com.ginkgo.anxtest",
                  "note": "Per-package allowlist allows hidden APIs broadly for this test app; it is not a single-method exception."}
        (OUT / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    except BaseException:
        if config_installed:
            CONFIG.rename(staged_config)
        if app_installed:
            APP.rename(staged_app)
        raise
    print("V28 AYRI SISTEM KAMERA TESTI CALISMA AGACINA EKLENDI")
    print("PAKET: com.ginkgo.anxtest; 62 uygulama ici arm64 kutuphanesi")
    print("MEVCUT KAMERA VE SELINUX POLITIKASI KORUNDU.")
    print("HIDDEN API IZNI YALNIZCA TEST PAKETINE AIT. TELEFONA YAZILMADI.")

if __name__ == "__main__":
    main()
