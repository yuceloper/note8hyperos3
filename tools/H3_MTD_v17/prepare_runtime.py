"""Compile MTD hwbinder access and install a single-attempt boot diagnostic."""
from pathlib import Path
import hashlib
import json
import os
import stat
import subprocess

TREE=Path('/linux/build/hyperos3-ginkgo-v1')
REF=Path('/reference')
OUT=Path('/result/runtime-v1')
BACKUP=Path('/linux/backups/hyperos3-mtd-v17-runtime')
EXPECTED='ed11c4971bea1c35ec7caf4ccaa224484a4540f66c4c4bd4ced8df32fc34aed8'
policy=TREE/'odm/etc/selinux/precompiled_sepolicy'
rc=TREE/'system_ext/etc/init/ginkgo-mtd-v16.rc'
def sha(data):return hashlib.sha256(data).hexdigest()
def meta(p):
 st=p.stat();return(st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode),{k:os.getxattr(p,k) for k in os.listxattr(p)})
if OUT.exists() or BACKUP.exists():raise RuntimeError('Candidate or backup exists; nothing overwritten')
if sha(policy.read_bytes())!=EXPECTED:raise RuntimeError('V16 policy baseline mismatch')
old_rc=(REF/'mtd-bundle-v16/bundle-v1/root/system_ext/etc/init/ginkgo-mtd-v16.rc').read_bytes()
if rc.read_bytes()!=old_rc or b'    disabled\n' not in old_rc or b'    oneshot\n' not in old_rc:
 raise RuntimeError('Disabled V16 service definition mismatch')
inputs=[]
for part,name in [('system','plat'),('system_ext','system_ext'),('product','product')]:
 base=TREE/part/'etc/selinux';inputs += [base/f'{name}_sepolicy.cil',base/'mapping/202504.cil']
v=REF/'policy-lineage23-v1'
inputs += [v/'plat_pub_versioned.compat-v2.cil',v/'vendor_sepolicy.compat-v2.cil',v/'odm/selinux/odm_sepolicy.cil',REF/'policy-fingerprint-v11/fingerprint-read.cil',REF/'mtd-policy-v16/foundation-v1/mtd-foundation.cil']
for p in inputs:
 if not p.is_file():raise RuntimeError('Missing input: '+str(p))
OUT.mkdir()
def compile_policy(files,name):
 dest=OUT/(name+'.policy')
 with (OUT/(name+'.log')).open('w') as log:
  r=subprocess.run(['secilc','-m','-M','true','-G','-c','30',*map(str,files),'-o',str(dest),'-f',str(OUT/(name+'.file_contexts'))],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:
  print((OUT/(name+'.log')).read_text());raise RuntimeError('Compilation failed; ROM unchanged')
 return dest
print('V16 yeniden dogrulaniyor...',flush=True)
baseline=compile_policy(inputs,'baseline-v16')
if baseline.read_bytes()!=policy.read_bytes():raise RuntimeError('V16 reproduction mismatch')
extra=OUT/'hwbinder.cil'
extra.write_text('(allow ginkgo_mtd hwbinder_device (chr_file (read write open getattr ioctl map)))\n')
print('V17 hwbinder adayi neverallow kontrolleriyle derleniyor...',flush=True)
candidate=compile_policy(inputs+[extra],'mtd-runtime')
new_rc=old_rc+b'\n# One start attempt after Android finishes booting; no restart loop.\non property:sys.boot_completed=1\n    start ginkgo-mtd\n'
(OUT/'ginkgo-mtd.rc.candidate').write_bytes(new_rc)
original=[(policy,policy.read_bytes(),meta(policy)),(rc,old_rc,meta(rc))]
BACKUP.mkdir(parents=True)
for p,data,_ in original:(BACKUP/p.name).write_bytes(data)
try:
 policy.write_bytes(candidate.read_bytes());rc.write_bytes(new_rc)
 for p,_,metadata in original:
  if meta(p)!=metadata:raise RuntimeError('Metadata changed')
 if policy.read_bytes()!=candidate.read_bytes() or rc.read_bytes()!=new_rc:raise RuntimeError('Installed bytes mismatch')
except BaseException:
 for p,data,_ in original:p.write_bytes(data)
 raise
validation={'status':'OFFLINE_RUNTIME_DIAGNOSTIC_NOT_BOOT_TESTED','policy_sha256':sha(candidate.read_bytes()),'rc_sha256':sha(new_rc),'previous_policy_sha256':EXPECTED,'trigger':'sys.boot_completed=1','oneshot':True,'lazy_interface_start':False,'persist_tee_permissions_added':False}
(OUT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
print('V17 TEK BASLATMA DENEMESI CALISMA AGACINA KURULDU.')
print('POLITIKA SHA256:',validation['policy_sha256'])
print('PERSIST/TEE IZNI EKLENMEDI. TELEFONA YAZILMADI.')
