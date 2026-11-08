"""Allow MTD to read hwservicemanager readiness properties."""
from pathlib import Path
import hashlib, json, os, stat, subprocess
TREE=Path('/linux/build/hyperos3-ginkgo-v1')
REF=Path('/reference');OUT=Path('/result/policy-v1')
BACKUP=Path('/linux/backups/hyperos3-mtd-v19-policy')
EXPECTED='25d23c25a5d8ee9af92554d323f5ebc0b8161bf36e4b6caae8388bacd7db6781'
RULES='''(allow ginkgo_mtd hwservicemanager_prop (file (getattr open read map)))
'''
def sha(b):return hashlib.sha256(b).hexdigest()
def meta(p):
 s=p.stat();return(s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode),{k:os.getxattr(p,k) for k in os.listxattr(p)})
policy=TREE/'odm/etc/selinux/precompiled_sepolicy'
rc=TREE/'system_ext/etc/init/ginkgo-mtd-v16.rc'
expected_rc=(REF/'mtd-policy-v17/runtime-v1/ginkgo-mtd.rc.candidate').read_bytes()
if rc.read_bytes()!=expected_rc:raise RuntimeError('V18 init definition mismatch')
if sha(policy.read_bytes())!=EXPECTED:raise RuntimeError('V18 policy mismatch')
if OUT.exists() or BACKUP.exists():raise RuntimeError('Candidate/backup exists; nothing overwritten')
inputs=[]
for part,name in [('system','plat'),('system_ext','system_ext'),('product','product')]:
 d=TREE/part/'etc/selinux';inputs += [d/f'{name}_sepolicy.cil',d/'mapping/202504.cil']
v=REF/'policy-lineage23-v1'
inputs += [v/'plat_pub_versioned.compat-v2.cil',v/'vendor_sepolicy.compat-v2.cil',v/'odm/selinux/odm_sepolicy.cil',REF/'policy-fingerprint-v11/fingerprint-read.cil',REF/'mtd-policy-v16/foundation-v1/mtd-foundation.cil',REF/'mtd-policy-v17/runtime-v1/hwbinder.cil',REF/'mtd-policy-v18/policy-v1/init-client.cil']
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
print('V18 politikasi yeniden dogrulaniyor...',flush=True)
baseline=compile_policy(inputs,'baseline-v18')
if baseline.read_bytes()!=policy.read_bytes():raise RuntimeError('Baseline reproduction mismatch')
extra=OUT/'readiness.cil';extra.write_text(RULES)
print('V19 hwservicemanager hazirlik okuma adayi neverallow kontrolleriyle derleniyor...',flush=True)
candidate=compile_policy(inputs+[extra],'mtd-v19')
original=policy.read_bytes();metadata=meta(policy)
BACKUP.mkdir(parents=True);(BACKUP/'precompiled_sepolicy').write_bytes(original)
try:
 policy.write_bytes(candidate.read_bytes())
 if policy.read_bytes()!=candidate.read_bytes() or meta(policy)!=metadata:raise RuntimeError('Installed policy verification failed')
except BaseException:
 policy.write_bytes(original);raise
result={'status':'OFFLINE_INSTALLED_NOT_BOOT_TESTED','previous_policy_sha256':EXPECTED,'policy_sha256':sha(candidate.read_bytes()),'rc_sha256':sha(expected_rc),'persist_tee_permissions_added':False,'aidl_default_service_permissions_added':False}
(OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('V19 POLITIKA CALISMA AGACINA KURULDU.')
print('POLITIKA SHA256:',result['policy_sha256'])
print('INIT TANIMI KORUNDU. PERSIST/TEE IZNI EKLENMEDI. TELEFONA YAZILMADI.')
