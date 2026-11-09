#!/usr/bin/env python3
"""Restore the original camera label and select one secure handler in the working fork."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from manifest_defaults import finalize_manifest, PACKAGE

SOURCE_SHA = "815f14e8419f55f23dfa58e796c7462c813a941417455e1d3e17cf7d2eba1186"

def digest(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

def run(*args):
    subprocess.run(list(map(str,args)),check=True,stdin=subprocess.DEVNULL)

def certificate(apk):
    output = subprocess.check_output(["apksigner","verify","--print-certs",str(apk)],text=True)
    values = re.findall(r"^Signer #\d+ certificate SHA-256 digest: (\S+)$",output,re.M)
    if len(values) != 1:
        raise RuntimeError("Expected one signer")
    return values[0]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--reference",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    ref,out=a.reference.resolve(),a.out.resolve()
    source=ref/"camera-v31/pro-test-v1/MiuiCamera-6.2-ginkgo-pro-test.apk"
    key=ref/"camera-v29/original-test-v1/diagnostic-only.jks"
    if out.exists() or ref==out or ref in out.parents or out in ref.parents:
        raise SystemExit("Output must be new and separate")
    if digest(source)!=SOURCE_SHA or not key.is_file():
        raise SystemExit("Working APK/key missing or mismatch")
    for name in ("aapt","zipalign","apksigner"):
        if not shutil.which(name):
            raise SystemExit("Missing tool: "+name)
    out.mkdir(parents=True)
    unsigned=out/"unsigned.apk"
    with zipfile.ZipFile(source) as before,zipfile.ZipFile(unsigned,"w") as after:
        manifest=finalize_manifest(before.read("AndroidManifest.xml"))
        for item in before.infolist():
            name=item.filename
            if name.startswith("META-INF/") and (name.upper().endswith((".RSA",".DSA",".EC",".SF")) or name.upper()=="META-INF/MANIFEST.MF"):
                continue
            after.writestr(item,manifest if name=="AndroidManifest.xml" else before.read(name))
    with zipfile.ZipFile(source) as before,zipfile.ZipFile(unsigned) as after:
        for name in after.namelist():
            if name!="AndroidManifest.xml" and before.read(name)!=after.read(name):
                raise RuntimeError("Unintended entry change: "+name)
    badging=subprocess.check_output(["aapt","dump","badging",str(unsigned)],text=True)
    if not re.search(r"^package: name='"+re.escape(PACKAGE)+"'",badging,re.M):
        raise RuntimeError("Package identity changed")
    aligned,signed=out/"aligned.apk",out/"MiuiCamera-6.2-ginkgo-named.apk"
    run("zipalign","4",unsigned,aligned)
    run("apksigner","sign","--ks",key,"--ks-key-alias","micamera6test",
        "--ks-pass","pass:android","--key-pass","pass:android","--out",signed,aligned)
    run("apksigner","verify","--verbose",signed)
    run("zipalign","-c","4",signed)
    if certificate(source)!=certificate(signed):
        raise RuntimeError("Working APK signer mismatch")
    report={
        "status":"ORIGINAL_CAMERA_LABEL_SECURE_HANDLER_NOT_DEVICE_TESTED",
        "package":PACKAGE,"source_sha256":SOURCE_SHA,"apk_sha256":digest(signed),
        "application_label":"Original localized resource 2132018043",
        "secure_handler":"com.android.camera.Camera",
        "removed_secure_handler":"com.android.camera.AssistantCamera",
        "normal_handler":"com.android.camera.AssistantCamera",
        "all_dex_resources_native_libraries_preserved":True,
        "preferred_default_set":False,"old_camera_removed":False,
        "offline_tree_modified":False,"same_signer":True,
        "remaining":"Confirm secure launch and lock-screen behavior before default-handler cleanup."
    }
    (out/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
    print("ORIJINAL KAMERA ADI VE TEK KILIT EKRANI BILESENI ADAYI HAZIR")
    print("PAKET:",PACKAGE)
    print("SHA256:",report["apk_sha256"])
    for line in badging.splitlines():
        if line.startswith("application-label:") or line.startswith("application-label-tr:"):
            print(line)
    print("CEKIM KODU/PRO DUZELTMESI/KUTUPHANELER KORUNDU. TELEFONA KURULMADI.")

if __name__=="__main__":
    main()
