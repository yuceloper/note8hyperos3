#!/usr/bin/env python3
"""Guard one invalid Pro shutter preview resource in the original Camera 6.2 fork."""
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

BASE_SHA = "76cff12c13114e17d2ac9c33622e3f7476a186d3b9df78e768bc3b28dc0ecdd0"
DEX_SHA = "a415bbe9dc31753acab9802471dce0198f9f876df39c0283b26699a8e681ab64"
PACKAGE = "com.ginkgo.micamera6test"
CLASS_PATH = Path("com/android/camera2/compat/theme/custom/mm/manually/ManualWorkspaceItem.smali")
METHOD = "getPanelComponentManuallyET(ILjava/util/List;Ljava/lang/String;)V"

def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def run(*args):
    subprocess.run(list(map(str, args)), check=True, stdin=subprocess.DEVNULL)

def guard_smali(text):
    header = re.compile(r"(?m)^\.method[^\n]* " + re.escape(METHOD) + r"[ \t]*$")
    matches = list(header.finditer(text))
    if len(matches) != 1:
        raise RuntimeError("Expected exactly one shutter preview method")
    start = matches[0].start()
    end = text.index(".end method", matches[0].end()) + len(".end method")
    old = text[start:end]
    if ":ginkgo_et_unavailable" in old:
        raise RuntimeError("Method already patched")
    call = re.compile(r"(?m)^(?P<indent>[ \t]*)invoke-virtual \{[vp]\d+, (?P<res>[vp]\d+)\}, Landroid/app/Application;->getString\(I\)Ljava/lang/String;$")
    found = list(call.finditer(old))
    if len(found) != 1 or old.count("return-void") != 1:
        raise RuntimeError("Unexpected shutter preview control flow")
    match = found[0]
    guard = match["indent"] + "if-lez " + match["res"] + ", :ginkgo_et_unavailable\n\n"
    changed = old[:match.start()] + guard + old[match.start():]
    changed, count = re.subn(r"(?m)^(?P<indent>[ \t]*)return-void[ \t]*$",
                            r"    :ginkgo_et_unavailable\n\g<indent>return-void", changed)
    if count != 1:
        raise RuntimeError("Unexpected return count")
    result = text[:start] + changed + text[end:]
    # Prove that removing exactly the inserted guard and label recovers the input.
    recovered = result.replace(guard, "", 1).replace("    :ginkgo_et_unavailable\n", "", 1)
    if recovered != text:
        raise RuntimeError("Unexpected smali modifications")
    return result, match["res"]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    ref, out = args.reference.resolve(), args.out.resolve()
    base = ref / "original-test-v1/MiuiCamera-6.2-ginkgo-test.apk"
    key = ref / "original-test-v1/diagnostic-only.jks"
    if out.exists() or ref == out or ref in out.parents or out in ref.parents:
        raise SystemExit("Output must be new and separate")
    if digest(base) != BASE_SHA or not key.is_file():
        raise SystemExit("V29 base APK/key mismatch or missing key")
    for tool in ("java", "aapt", "zipalign", "apksigner"):
        if not shutil.which(tool):
            raise SystemExit("Missing tool: " + tool)
    out.mkdir(parents=True)
    dex_path = out / "original-classes2.dex"
    with zipfile.ZipFile(base) as z:
        data = z.read("classes2.dex")
    if hashlib.sha256(data).hexdigest() != DEX_SHA:
        raise RuntimeError("Source classes2.dex mismatch")
    dex_path.write_bytes(data)
    smali = out / "smali"
    run("java", "-cp", "/usr/share/java/*", "org.jf.baksmali.Main",
        "disassemble", "--api", "35", "--output", smali, dex_path)
    target = smali / CLASS_PATH
    original_text = target.read_text()
    candidate_text, register = guard_smali(original_text)
    target.write_text(candidate_text)
    patched = out / "patched-classes2.dex"
    run("java", "-cp", "/usr/share/java/*", "org.jf.smali.Main",
        "assemble", "--api", "35", "--output", patched, smali)
    patched_data = patched.read_bytes()
    if hashlib.sha1(patched_data[32:]).digest() != patched_data[12:32]:
        raise RuntimeError("Rebuilt DEX signature mismatch")
    if (zlib.adler32(patched_data[12:]) & 0xffffffff) != struct.unpack_from("<I", patched_data, 8)[0]:
        raise RuntimeError("Rebuilt DEX checksum mismatch")
    unsigned = out / "unsigned.apk"
    with zipfile.ZipFile(base) as before, zipfile.ZipFile(unsigned, "w") as after:
        for item in before.infolist():
            name = item.filename
            if name.startswith("META-INF/") and (name.upper().endswith((".RSA", ".DSA", ".EC", ".SF")) or name.upper() == "META-INF/MANIFEST.MF"):
                continue
            after.writestr(item, patched_data if name == "classes2.dex" else before.read(name))
    with zipfile.ZipFile(base) as before, zipfile.ZipFile(unsigned) as after:
        for name in after.namelist():
            if name != "classes2.dex" and before.read(name) != after.read(name):
                raise RuntimeError("Unintended APK entry change: " + name)
    badging = subprocess.check_output(["aapt", "dump", "badging", str(unsigned)], text=True)
    if not re.search(r"^package: name='" + re.escape(PACKAGE) + "'", badging, re.M):
        raise RuntimeError("Package identity changed")
    aligned, signed = out / "aligned.apk", out / "MiuiCamera-6.2-ginkgo-pro-test.apk"
    run("zipalign", "4", unsigned, aligned)
    run("apksigner", "sign", "--ks", key, "--ks-key-alias", "micamera6test",
        "--ks-pass", "pass:android", "--key-pass", "pass:android", "--out", signed, aligned)
    run("apksigner", "verify", "--verbose", signed)
    run("zipalign", "-c", "4", signed)
    def signer(apk):
        output = subprocess.check_output(["apksigner", "verify", "--print-certs", str(apk)], text=True)
        certs = re.findall(r"^Signer #\d+ certificate SHA-256 digest: (\S+)$", output, re.M)
        if len(certs) != 1:
            raise RuntimeError("Unexpected signer count")
        return certs[0]
    if signer(base) != signer(signed):
        raise RuntimeError("APK signer differs from installed system test")
    report = {
        "status": "ORIGINAL_6_2_PRO_PREVIEW_GUARD_NOT_DEVICE_TESTED",
        "package": PACKAGE, "base_apk_sha256": BASE_SHA,
        "apk_sha256": digest(signed), "same_signer_as_v29": True,
        "changed_method": METHOD, "guard_register": register,
        "behavior": "Skip only the ET workspace preview entry when its string resource ID is <= 0",
        "pro_mode_disabled": False, "capture_parameters_changed": False,
        "manifest_resources_native_libraries_changed": False,
        "note": "classes2.dex is reassembled; only this smali method is edited. V29 model-gate diagnostic remains."
    }
    (out / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("ORIJINAL KAMERA 6.2 PRO ONIZLEME ADAYI HAZIR")
    print("PAKET:", PACKAGE)
    print("SHA256:", report["apk_sha256"])
    print("IMZA V29/V30 ILE AYNI. PRO MODU VE CEKIM AYARLARI KORUNDU.")
    print("TELEFONA KURULMADI. RUNTIME TEST BEKLENIYOR.")

if __name__ == "__main__":
    main()
