"""Fix observed init execution and system_server MTD HIDL access denials."""
from pathlib import Path
import hashlib, json, os, stat, subprocess
TREE=Path('/linux/build/hyperos3-ginkgo-v1')
REF=Path('/reference');OUT=Path('/result/policy-v1')
BACKUP=Path('/linux/backups/hyperos3-mtd-v18-policy')
EXPECTED='ed11c4971bea1c35ec7caf4ccaa224484a4540f66c4c4bd4ced8df32fc34aed8'
RULES='''(allow init ginkgo_mtd_exec (file (getattr open read execute map)))
(allow system_server ginkgo_mtd_hwservice (hwservice_manager (find)))
(allow system_server ginkgo_mtd (binder (call transfer)))
(allow ginkgo_mtd system_server (binder (transfer)))
(allow system_server ginkgo_mtd (fd (use)))
'''
def sha(b):return hashlib.sha256(b).hexdigest()
def meta(p):
 s=p.stat();return(s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode),{k:os.getxattr(p,k) for k in os.listxattr(p)})
policy=TREE/'odm/etc/selinux/precompiled_sepolicy'
rc=TREE/'system_ext/etc/init/ginkgo-mtd-v16.rc'
expected_rc=(REF/'mtd-policy-v17/runtime-v1/ginkgo-mtd.rc.candidate').read_bytes()
if rc.read_bytes()!=expected_rc:raise RuntimeError('V17 init definition mismatch')
if sha(policy.read_bytes())!=EXPECTED:raise RuntimeError('V17 policy mismatch')
if OUT.exists() or BACKUP.exists():raise RuntimeError('Candidate/backup exists; nothing overwritten')
inputs=[]
for part,name in [('system','plat'),('system_ext','system_ext'),('product','product')]:
 d=TREE/part/'etc/selinux';inputs += [d/f'{name}_sepolicy.cil',d/'mapping/202504.cil']
v=REF/'policy-lineage23-v1'
inputs += [v/'plat_pub_versioned.compat-v2.cil',v/'vendor_sepolicy.compat-v2.cil',v/'odm/selinux/odm_sepolicy.cil',REF/'policy-fingerprint-v11/fingerprint-read.cil',REF/'mtd-policy-v16/foundation-v1/mtd-foundation.cil',REF/'mtd-policy-v17/runtime-v1/hwbinder.cil']
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
print('V17 politikasi yeniden dogrulaniyor...',flush=True)
baseline=compile_policy(inputs,'baseline-v17')
if baseline.read_bytes()!=policy.read_bytes():raise RuntimeError('Baseline reproduction mismatch')
extra=OUT/'init-client.cil';extra.write_text(RULES)
print('V18 init ve HIDL istemci adayi neverallow kontrolleriyle derleniyor...',flush=True)
candidate=compile_policy(inputs+[extra],'mtd-v18')
original=policy.read_bytes();metadata=meta(policy)
BACKUP.mkdir(parents=True);(BACKUP/'precompiled_sepolicy').write_bytes(original)
try:
 policy.write_bytes(candidate.read_bytes())
 if policy.read_bytes()!=candidate.read_bytes() or meta(policy)!=metadata:raise RuntimeError('Installed policy verification failed')
except BaseException:
 policy.write_bytes(original);raise
result={'status':'OFFLINE_INSTALLED_NOT_BOOT_TESTED','previous_policy_sha256':EXPECTED,'policy_sha256':sha(candidate.read_bytes()),'rc_sha256':sha(expected_rc),'persist_tee_permissions_added':False,'aidl_default_service_permissions_added':False}
(OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('V18 POLITIKA CALISMA AGACINA KURULDU.')
print('POLITIKA SHA256:',result['policy_sha256'])
print('INIT TANIMI KORUNDU. PERSIST/TEE IZNI EKLENMEDI. TELEFONA YAZILMADI.')
