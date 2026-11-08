from pathlib import Path
import hashlib,json,os
prep=Path('/prep')
root=Path('/linux/build/hyperos3-ginkgo-v1')
meta=json.loads((prep/'validation.json').read_text())
fstab=root/'system/etc/fstab.emmc'
rc=root/'system/etc/init/ginkgo-fstab-v1.rc'
policy=root/'odm/etc/selinux/precompiled_sepolicy'
expected='9704fd3d823f20d2a1a9b8c93aea859134b5b6ad233e46336ad96ba6c87a9a45'
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
require(root.is_dir() and not root.is_symlink(),'Calisma agaci yok')
require(not fstab.exists() and not fstab.is_symlink(),'fstab.emmc zaten mevcut')
require(not rc.exists() and not rc.is_symlink(),'Init bind adayi zaten mevcut')
require(hashlib.sha256(policy.read_bytes()).hexdigest()==expected,'Kurulu politika uyusmuyor')
data=(prep/'fstab.emmc').read_bytes()
require(hashlib.sha256(data).hexdigest()==meta['fstab_sha256'],'fstab aday hash uyusmuyor')
boot=prep/'boot-ginkgo-h3-erofs-candidate.img'
require(hashlib.sha256(boot.read_bytes()).hexdigest()==meta['candidate_boot_sha256'],'Boot aday hash uyusmuyor')
for p,content,typ in [(fstab,data,'vendor_configs_file'),(rc,b'on early-init\n    # Keep vendor mount_all consistent with the first-stage EROFS fstab.\n    mount none /system/etc/fstab.emmc /vendor/etc/fstab.qcom bind\n','system_file')]:
 with p.open('xb') as f:f.write(content)
 os.chown(p,0,0);os.chmod(p,0o644)
 os.setxattr(p,'security.selinux',('u:object_r:'+typ+':s0').encode()+b'\0')
 require(p.read_bytes()==content,'Yazma dogrulamasi basarisiz')
print('EROFS FSTAB VE ERKEN VENDOR FSTAB BIND ADAYI KURULDU.')
print('SIFRELEME SECENEKLERI KORUNDU. VENDOR IMAJI DEGISTIRILMEDI.')
print('BOOT ADAYI OFFLINE HAZIR. TELEFONA YAZILMADI.')
