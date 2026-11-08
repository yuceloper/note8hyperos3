"""Prepare narrowly labeled, read-only MTD persist diagnostics; no TEE access."""
from pathlib import Path
import hashlib, json, os, stat, subprocess
TREE=Path('/linux/build/hyperos3-ginkgo-v1')
REF=Path('/reference');OUT=Path('/result/policy-v1')
BACKUP=Path('/linux/backups/hyperos3-mtd-v20-readonly')
EXPECTED='8c7b8c054535615d714ed65fc9a62078fa024b9c0220a3e23d86085e3b2b6776'
RULES='(type ginkgo_mtd_persist_file)\n(roletype object_r ginkgo_mtd_persist_file)\n(typeattributeset file_type (ginkgo_mtd_persist_file))\n(typeattributeset vendor_persist_type (ginkgo_mtd_persist_file))\n(allow ginkgo_mtd mnt_vendor_file (dir (getattr search)))\n(allow ginkgo_mtd ginkgo_mtd_persist_file (dir (getattr search open read)))\n(allow ginkgo_mtd ginkgo_mtd_persist_file (file (getattr open read map)))\n(allow init ginkgo_mtd_persist_file (dir (getattr search open read relabelto)))\n(allow init ginkgo_mtd_persist_file (file (getattr relabelto)))\n(neverallow ginkgo_mtd ginkgo_mtd_persist_file (file (write append create unlink rename setattr)))\n(neverallow ginkgo_mtd ginkgo_mtd_persist_file (dir (write create add_name remove_name rmdir rename setattr)))\n(neverallow ginkgo_mtd tee_device (chr_file (open read write ioctl map)))\n'
def sha(b):return hashlib.sha256(b).hexdigest()
def meta(p):
 s=p.stat();return(s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode),{k:os.getxattr(p,k) for k in os.listxattr(p)})
policy=TREE/'odm/etc/selinux/precompiled_sepolicy'
rc=TREE/'system_ext/etc/init/ginkgo-mtd-v16.rc'
expected_rc=(REF/'mtd-policy-v17/runtime-v1/ginkgo-mtd.rc.candidate').read_bytes()
if rc.read_bytes()!=expected_rc:raise RuntimeError('V19 init definition mismatch')
if sha(policy.read_bytes())!=EXPECTED:raise RuntimeError('V19 policy mismatch')
if OUT.exists() or BACKUP.exists():raise RuntimeError('Candidate/backup exists; nothing overwritten')
inputs=[]
for part,name in [('system','plat'),('system_ext','system_ext'),('product','product')]:
 d=TREE/part/'etc/selinux';inputs += [d/f'{name}_sepolicy.cil',d/'mapping/202504.cil']
v=REF/'policy-lineage23-v1'
inputs += [v/'plat_pub_versioned.compat-v2.cil',v/'vendor_sepolicy.compat-v2.cil',v/'odm/selinux/odm_sepolicy.cil',REF/'policy-fingerprint-v11/fingerprint-read.cil',REF/'mtd-policy-v16/foundation-v1/mtd-foundation.cil',REF/'mtd-policy-v17/runtime-v1/hwbinder.cil',REF/'mtd-policy-v18/policy-v1/init-client.cil',REF/'mtd-policy-v19/policy-v1/readiness.cil']
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
print('V19 politikasi yeniden dogrulaniyor...',flush=True)
baseline=compile_policy(inputs,'baseline-v19')
if baseline.read_bytes()!=policy.read_bytes():raise RuntimeError('Baseline reproduction mismatch')
extra=OUT/'persist-readonly.cil';extra.write_text(RULES)
print('V20 fdsd etiket ve salt okunur erisim adayi neverallow kontrolleriyle derleniyor...',flush=True)
candidate=compile_policy(inputs+[extra],'mtd-v20')
contexts=TREE/'odm/etc/selinux/odm_file_contexts'
old_contexts=contexts.read_bytes()
if b'ginkgo_mtd_persist_file' in old_contexts:raise RuntimeError('Persist context already installed')
append=b'/mnt/vendor/persist/fdsd(/.*)? u:object_r:ginkgo_mtd_persist_file:s0\n'
new_contexts=old_contexts.rstrip(b'\n')+b'\n'+append
if expected_rc.count(b'    start ginkgo-mtd\n')!=1:raise RuntimeError('Unexpected init trigger')
new_rc=expected_rc.replace(b'    start ginkgo-mtd\n',b'    restorecon_recursive /mnt/vendor/persist/fdsd\n    start ginkgo-mtd\n')
(OUT/'ginkgo-mtd.rc.candidate').write_bytes(new_rc)
(OUT/'file_contexts.append').write_bytes(append)
original=[(policy,policy.read_bytes(),meta(policy)),(rc,rc.read_bytes(),meta(rc)),(contexts,old_contexts,meta(contexts))]
changes=[(policy,candidate.read_bytes()),(rc,new_rc),(contexts,new_contexts)]
BACKUP.mkdir(parents=True)
for p,data,_ in original:(BACKUP/p.name).write_bytes(data)
try:
 for p,data in changes:p.write_bytes(data)
 for (p,data),(_,_,metadata) in zip(changes,original):
  if p.read_bytes()!=data or meta(p)!=metadata:raise RuntimeError('Installed bytes/metadata mismatch')
except BaseException:
 for p,data,_ in original:p.write_bytes(data)
 raise
result={'status':'OFFLINE_INSTALLED_NOT_BOOT_TESTED','previous_policy_sha256':EXPECTED,'policy_sha256':sha(candidate.read_bytes()),'rc_sha256':sha(new_rc),'file_contexts_sha256':sha(new_contexts),'persist_relabel_scope':'/mnt/vendor/persist/fdsd','mtd_persist_access':'read-only','persist_write_permissions_added':False,'tee_permissions_added':False,'aidl_default_service_permissions_added':False}
(OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('V20 POLITIKA CALISMA AGACINA KURULDU.')
print('POLITIKA SHA256:',result['policy_sha256'])
print('YALNIZCA FDSD ETIKETI VE OKUMA ERISIMI. DOSYA YAZMA/TEE IZNI YOK. TELEFONA YAZILMADI.')
