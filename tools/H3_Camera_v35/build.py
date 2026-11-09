#!/usr/bin/env python3
"""Build a V35 candidate that omits only the startup vendor-write probe."""
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

SOURCE_SHA='538d855e942c8fe3ce6c21ab5559d4f42004730491ddbf8e10b90391ef277a6e'
DEX_SHA='02d250f7ed92c8a3c6ce59b659e6b385b86d917a04572b9c413a8ec2e1920a68'
CODE=5735836
BODY_SHA='43c58cbfdb236b76e44ea531053ed5334d9cf958547eb6599d801b3cc44ffd0f'

def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def patch(data):
    if hashlib.sha256(data).hexdigest()!=DEX_SHA:raise RuntimeError('classes.dex mismatch')
    if struct.unpack_from('<HHHHII',data,CODE)!=(4,1,3,0,0,158):raise RuntimeError('Unexpected run() layout')
    start=CODE+16
    if hashlib.sha256(data[start:start+316]).hexdigest()!=BODY_SHA:raise RuntimeError('Unexpected run() body')
    if data[start+66:start+70]!=bytes.fromhex('6203489c') or data[start+218:start+220]!=b'\x0e\x00':
        raise RuntimeError('Unexpected probe entry/return')
    result=bytearray(data)
    # Lz/B.run() case at byte 66: jump to its own return at 218.
    # Preserve other synthetic Runnable cases and all actual LUT operations.
    result[start+66:start+70]=bytes.fromhex('29004c00')
    result[12:32]=hashlib.sha1(result[32:]).digest()
    struct.pack_into('<I',result,8,zlib.adler32(result[12:])&0xffffffff)
    if any(not(8<=i<32 or start+66<=i<start+70) for i,(a,b) in enumerate(zip(data,result)) if a!=b):
        raise RuntimeError('Unexpected DEX changes')
    return bytes(result)

def sig(n):
    n=n.upper()
    return n.startswith('META-INF/') and (n.endswith(('.RSA','.DSA','.EC','.SF')) or n=='META-INF/MANIFEST.MF')

def run(*a):subprocess.run(list(map(str,a)),check=True,stdin=subprocess.DEVNULL)

def certificate(apk):
    out=subprocess.check_output(['apksigner','verify','--print-certs',str(apk)],text=True)
    certs=re.findall(r'^Signer #\d+ certificate SHA-256 digest: (\S+)$',out,re.M)
    if len(certs)!=1:raise RuntimeError('Expected one signer')
    return certs[0]

def main():
    p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    ref,out=a.reference.resolve(),a.out.resolve()
    source=ref/'camera-v34/original-identity-v1/MiuiCamera-6.2-ginkgo-original.apk'
    key=ref/'camera-v29/original-test-v1/diagnostic-only.jks'
    if out.exists() or ref==out or ref in out.parents or out in ref.parents:raise SystemExit('Output must be new and separate')
    if digest(source)!=SOURCE_SHA or not key.is_file():raise SystemExit('V34 APK/key missing or mismatch')
    for tool in ('aapt','zipalign','apksigner'):
        if not shutil.which(tool):raise SystemExit('Missing tool: '+tool)
    out.mkdir(parents=True)
    unsigned,aligned,signed=out/'unsigned.apk',out/'aligned.apk',out/'MiuiCamera-6.2-ginkgo-v35.apk'
    with zipfile.ZipFile(source) as before:
        patched=patch(before.read('classes.dex'))
        with zipfile.ZipFile(unsigned,'w') as after:
            for item in before.infolist():
                if not sig(item.filename):after.writestr(item,patched if item.filename=='classes.dex' else before.read(item.filename))
    badging=subprocess.check_output(['aapt','dump','badging',str(unsigned)],text=True)
    if not re.search(r"^package: name='com.android.camera' ",badging,re.M):raise RuntimeError('Package mismatch')
    run('zipalign','4',unsigned,aligned)
    run('apksigner','sign','--ks',key,'--ks-key-alias','micamera6test','--ks-pass','pass:android','--key-pass','pass:android','--out',signed,aligned)
    run('apksigner','verify','--verbose',signed);run('zipalign','-c','4',signed)
    if certificate(source)!=certificate(signed):raise RuntimeError('Signer differs from V34')
    with zipfile.ZipFile(source) as before,zipfile.ZipFile(signed) as after:
        expected={n for n in before.namelist() if not sig(n)}
        if expected!={n for n in after.namelist() if not sig(n)}:raise RuntimeError('Entry set changed')
        for n in expected:
            if after.read(n)!=(patched if n=='classes.dex' else before.read(n)):raise RuntimeError('Unexpected payload change: '+n)
    report=dict(status='STARTUP_WRITE_PROBE_OMITTED_NOT_RUNTIME_TESTED',package='com.android.camera',apk_sha256=digest(signed),
        source_sha256=SOURCE_SHA,same_signer_as_v34=True,changed_method='Lz/B;->run()V case at byte 66',
        startup_test_write_omitted=True,real_lut_paths_changed=False,actual_lut_compatibility_verified=False,
        gallery_signature_permission_fixed=False,manifest_resources_native_preserved=True,
        policy_changed=False,offline_tree_modified=False,installed=False)
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('V35 BASLANGIC YAZMA TESTI ADAYI HAZIR')
    print('SHA256:',report['apk_sha256'])
    print('V34 IMZASI VE ASIL PAKET KIMLIGI KORUNDU.')
    print('GERCEK LUT YOLLARI/POLITIKA DEGISTIRILMEDI. GALERI IZNI HENUZ COZULMEDI.')
    print('TELEFONA KURULMADI. RUNTIME TEST BEKLENIYOR.')

if __name__=='__main__':main()
