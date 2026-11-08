"""Prepare scoped Find Device persist record updates after successful QSEE responses."""
from pathlib import Path
import hashlib, json, os, stat, subprocess
TREE=Path('/linux/build/hyperos3-ginkgo-v1');REF=Path('/reference')
OUT=Path('/result/policy-v1');BACKUP=Path('/linux/backups/hyperos3-mtd-v22-fdsd')
EXPECTED='64081298a7cbc6e7ac0a2e1c8d0f33491810f249ba92de6a3dc772caeb3a0c6b'
FILE_GUARD='(neverallow ginkgo_mtd ginkgo_mtd_persist_file (file (write append create unlink rename setattr)))\n'
DIR_GUARD='(neverallow ginkgo_mtd ginkgo_mtd_persist_file (dir (write create add_name remove_name rmdir rename setattr)))\n'
RULES='(allow ginkgo_mtd ginkgo_mtd_persist_file (file (write append create unlink rename setattr)))\n(allow ginkgo_mtd ginkgo_mtd_persist_file (dir (write add_name remove_name)))\n(neverallow ginkgo_mtd ginkgo_mtd_persist_file (dir (create rmdir rename setattr)))\n'
def sha(b):return hashlib.sha256(b).hexdigest()
def meta(p):
 s=p.stat();return(s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode),{k:os.getxattr(p,k) for k in os.listxattr(p)})
policy=TREE/'odm/etc/selinux/precompiled_sepolicy'
rc=TREE/'system_ext/etc/init/ginkgo-mtd-v16.rc'
expected_rc=(REF/'mtd-policy-v20/policy-v1/ginkgo-mtd.rc.candidate').read_bytes()
if rc.read_bytes()!=expected_rc:raise RuntimeError('V21 init mismatch')
if sha(policy.read_bytes())!=EXPECTED:raise RuntimeError('V21 policy mismatch')
if OUT.exists() or BACKUP.exists():raise RuntimeError('Candidate/backup exists; nothing overwritten')
inputs=[]
for part,name in [('system','plat'),('system_ext','system_ext'),('product','product')]:
 d=TREE/part/'etc/selinux';inputs += [d/f'{name}_sepolicy.cil',d/'mapping/202504.cil']
v=REF/'policy-lineage23-v1'
inputs += [v/'plat_pub_versioned.compat-v2.cil',v/'vendor_sepolicy.compat-v2.cil',v/'odm/selinux/odm_sepolicy.cil',REF/'policy-fingerprint-v11/fingerprint-read.cil',REF/'mtd-policy-v16/foundation-v1/mtd-foundation.cil',REF/'mtd-policy-v17/runtime-v1/hwbinder.cil',REF/'mtd-policy-v18/policy-v1/init-client.cil',REF/'mtd-policy-v19/policy-v1/readiness.cil']
persist=REF/'mtd-policy-v21/policy-v1/persist-readonly-qsee-compatible.cil'
qsee=REF/'mtd-policy-v21/policy-v1/qsee.cil'
old_persist=persist.read_text()
if old_persist.count(FILE_GUARD)!=1 or old_persist.count(DIR_GUARD)!=1:raise RuntimeError('Expected V21 persist write guards mismatch')
for p in inputs+[persist,qsee]:
 if not p.is_file():raise RuntimeError('Missing policy source: '+str(p))
OUT.mkdir()
def compile_policy(files,name):
 dest=OUT/(name+'.policy')
 with (OUT/(name+'.log')).open('w') as log:
  r=subprocess.run(['secilc','-m','-M','true','-G','-c','30',*map(str,files),'-o',str(dest),'-f',str(OUT/(name+'.file_contexts'))],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:
  print((OUT/(name+'.log')).read_text());raise RuntimeError('Compilation failed; ROM unchanged')
 return dest
print('V21 politikasi birebir dogrulaniyor...',flush=True)
baseline=compile_policy(inputs+[persist,qsee],'baseline-v21')
if baseline.read_bytes()!=policy.read_bytes():raise RuntimeError('Baseline reproduction mismatch')
compat=OUT/'persist-scoped-write.cil'
compat.write_text(old_persist.replace(FILE_GUARD,'').replace(DIR_GUARD,''))
extra=OUT/'fdsd-update.cil';extra.write_text(RULES)
print('V22 fdsd kayit guncelleme adayi neverallow kontrolleriyle derleniyor...',flush=True)
candidate=compile_policy(inputs+[compat,qsee,extra],'mtd-v22')
original=policy.read_bytes();metadata=meta(policy)
BACKUP.mkdir(parents=True);(BACKUP/'precompiled_sepolicy').write_bytes(original)
try:
 policy.write_bytes(candidate.read_bytes())
 if policy.read_bytes()!=candidate.read_bytes() or meta(policy)!=metadata:raise RuntimeError('Policy installation verification failed')
except BaseException:
 policy.write_bytes(original);raise
result={'status':'OFFLINE_INSTALLED_NOT_BOOT_TESTED','previous_policy_sha256':EXPECTED,'policy_sha256':sha(candidate.read_bytes()),'rc_sha256':sha(expected_rc),'file_contexts_sha256':sha((TREE/'odm/etc/selinux/odm_file_contexts').read_bytes()),'persist_write_permissions_added':True,'persist_write_scope':'ginkgo_mtd_persist_file: /mnt/vendor/persist/fdsd subtree','tee_communication_permissions_added':False,'tee_communication_permissions_preserved':True,'firmware_modified':False,'init_changed':False}
(OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('V22 FDSD KAYIT GUNCELLEME ADAYI CALISMA AGACINA KURULDU.')
print('POLITIKA SHA256:',result['policy_sha256'])
print('YAZMA IZNI YALNIZCA FDSD OZEL ETIKETINE VERILDI. DOSYA SILME VEYA FORMAT YAPILMADI. TELEFONA YAZILMADI.')
