#!/usr/bin/env python3
"""Build-only original-identity camera candidate from hash-pinned tested code."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

ORIGINAL = '48a12d13da98f2e683b185476b9a5516251bcef80fe19aec0ecfde22876d51c5'
WORKING = '815f14e8419f55f23dfa58e796c7462c813a941417455e1d3e17cf7d2eba1186'
PATCHED = {'classes2.dex', 'classes3.dex'}

def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def signature_entry(n):
    u = n.upper()
    return u.startswith('META-INF/') and (u.endswith(('.RSA', '.DSA', '.EC', '.SF')) or u == 'META-INF/MANIFEST.MF')

def compose(original, working, output):
    with zipfile.ZipFile(original) as src, zipfile.ZipFile(working) as tested:
        if len(src.namelist()) != len(set(src.namelist())) or len(tested.namelist()) != len(set(tested.namelist())):
            raise RuntimeError('Duplicate ZIP entries')
        natives = [n for n in src.namelist() if n.startswith('lib/') and n.endswith('.so')]
        if len(natives) != 42 or any(not n.startswith('lib/arm64-v8a/') for n in natives):
            raise RuntimeError('Unexpected native library layout')
        source_entries = {n for n in src.namelist() if not signature_entry(n)}
        tested_entries = {n for n in tested.namelist() if not signature_entry(n)}
        if source_entries != tested_entries:
            raise RuntimeError('Unexpected working APK entry set')
        # V31 differs only in its cloned manifest and the two tested DEX files.
        for n in source_entries - PATCHED - {'AndroidManifest.xml'}:
            if src.read(n) != tested.read(n):
                raise RuntimeError('Unexpected working APK difference: ' + n)
        with zipfile.ZipFile(output, 'w') as dst:
            for info in src.infolist():
                if not signature_entry(info.filename):
                    dst.writestr(info, tested.read(info.filename) if info.filename in PATCHED else src.read(info.filename))
    verify_payload(original, working, output)

def verify_payload(original, working, candidate):
    with zipfile.ZipFile(original) as src, zipfile.ZipFile(working) as tested, zipfile.ZipFile(candidate) as dst:
        expected = {n for n in src.namelist() if not signature_entry(n)}
        actual = {n for n in dst.namelist() if not signature_entry(n)}
        if expected != actual:
            raise RuntimeError('Candidate entry set changed')
        for n in expected:
            reference = tested if n in PATCHED else src
            if dst.read(n) != reference.read(n):
                raise RuntimeError('Candidate payload mismatch: ' + n)

def run(*args):
    subprocess.run(list(map(str, args)), check=True, stdin=subprocess.DEVNULL)

def certificate(apk):
    data = subprocess.check_output(['apksigner', 'verify', '--print-certs', str(apk)], text=True)
    values = re.findall(r'^Signer #\d+ certificate SHA-256 digest: (\S+)$', data, re.M)
    if len(values) != 1:
        raise RuntimeError('Expected one APK signer')
    return values[0]

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--original', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    original, ref, out = a.original.resolve(), a.reference.resolve(), a.out.resolve()
    working = ref / 'camera-v31/pro-test-v1/MiuiCamera-6.2-ginkgo-pro-test.apk'
    key = ref / 'camera-v29/original-test-v1/diagnostic-only.jks'
    if out.exists() or out == ref or ref in out.parents or out in ref.parents or out in original.parents:
        raise SystemExit('Output must be new and separate')
    if digest(original) != ORIGINAL or digest(working) != WORKING or not key.is_file():
        raise SystemExit('Original/working APK or signing key missing/mismatched')
    for tool in ('aapt', 'zipalign', 'apksigner'):
        if not shutil.which(tool):
            raise SystemExit('Missing tool: ' + tool)
    manifest = subprocess.check_output(['aapt', 'dump', 'xmltree', str(original), 'AndroidManifest.xml'], text=True)
    if 'sharedUserId' in manifest:
        raise SystemExit('Refusing shared UID package')
    out.mkdir(parents=True)
    unsigned, aligned, signed = out/'unsigned.apk', out/'aligned.apk', out/'MiuiCamera-6.2-ginkgo-original.apk'
    compose(original, working, unsigned)
    badging = subprocess.check_output(['aapt', 'dump', 'badging', str(unsigned)], text=True)
    if not re.search(r"^package: name='com.android.camera' .*versionName='6\.2\.001130\.0'", badging, re.M):
        raise RuntimeError('Original package/version verification failed')
    run('zipalign', '4', unsigned, aligned)
    run('apksigner', 'sign', '--ks', key, '--ks-key-alias', 'micamera6test', '--ks-pass', 'pass:android', '--key-pass', 'pass:android', '--out', signed, aligned)
    run('apksigner', 'verify', '--verbose', signed)
    run('zipalign', '-c', '4', signed)
    verify_payload(original, working, signed)
    signer = certificate(signed)
    if signer != certificate(working) or signer == certificate(original):
        raise RuntimeError('Unexpected signing identity')
    report = dict(status='ORIGINAL_IDENTITY_APK_REVIEW_ONLY_NOT_INSTALLED', package='com.android.camera',
        apk_sha256=digest(signed), original_sha256=ORIGINAL, working_sha256=WORKING,
        certificate_sha256=signer, original_certificate_preserved=False,
        manifest_byte_identical_to_original=True, native_libraries_preserved=42,
        changed_payload_entries=sorted(PATCHED), offline_tree_modified=False, flashed=False,
        remaining=['System-image staging with original backup and metadata verification',
                   'Native library placement and scoped hidden-API access',
                   'Donor package-manager signature migration runtime verification',
                   'Lock-screen launch and gallery privacy test',
                   'Signature-only permissions and provider integration verification'])
    (out/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print('V34 ORIJINAL PAKET KIMLIKLI KAMERA ADAYI HAZIR')
    print('PAKET: com.android.camera')
    print('SHA256:', report['apk_sha256'])
    print('ORIJINAL MANIFEST VE 42 KUTUPHANE KORUNDU. IMZA DEGISTI.')
    print('CALISMA AGACINA KURULMADI. TELEFONA YAZILMADI. ADB INSTALL ILE KURMAYIN.')

if __name__ == '__main__':
    main()
