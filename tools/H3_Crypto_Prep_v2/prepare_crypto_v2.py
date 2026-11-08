from pathlib import Path
import hashlib,json,os,shutil,stat
prep=Path('/prep');root=Path('/linux/build/hyperos3-ginkgo-v1')
meta=json.loads((prep/'validation.json').read_text())
p=root/'system/etc/fstab.emmc'
backup=Path('/linux/backups/hyperos3-crypto-v2')
sha=lambda b:hashlib.sha256(b).hexdigest()
assert p.is_file() and not p.is_symlink(),'fstab.emmc bulunamadi'
assert sha(p.read_bytes())==meta['previous_fstab_sha256'],'Beklenen v1 fstab hash uyusmuyor'
assert not backup.exists(),'Crypto v2 yedegi zaten mevcut; tekrar uygulanmadi'
new=(prep/'fstab.emmc').read_bytes()
assert sha(new)==meta['fstab_sha256'],'Aday fstab hash uyusmuyor'
assert sha((prep/'boot-ginkgo-h3-standardkeys-v2.img').read_bytes())==meta['boot_sha256'],'Boot hash uyusmuyor'
old=p.read_bytes();oldlines=old.splitlines();newlines=new.splitlines()
assert len(oldlines)==len(newlines)
diffs=[(a,b) for a,b in zip(oldlines,newlines) if a!=b]
assert len(diffs)==1 and diffs[0][0].split()[1]==b'/data'
assert diffs[0][1]==diffs[0][0].replace(b'+wrappedkey_v0',b'').replace(b':wrappedkey_v0',b'')
st=p.stat();attrs={n:os.getxattr(p,n) for n in os.listxattr(p)}
backup.mkdir(parents=True);shutil.copy2(p,backup/'fstab.emmc.v1')
with p.open('r+b') as f:f.write(new);f.truncate()
os.utime(p,ns=(st.st_atime_ns,st.st_mtime_ns))
assert sha(p.read_bytes())==meta['fstab_sha256']
now=p.stat();assert (now.st_uid,now.st_gid,stat.S_IMODE(now.st_mode))==(st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode))
assert all(os.getxattr(p,n)==v for n,v in attrs.items())
print('YALNIZCA DATA WRAPPEDKEY SECENEKLERI KALDIRILDI.')
print('FBE V2 VE METADATA SIFRELEMESI KORUNDU. METADATA KORUNDU.')
print('ESLESEN BOOT: boot-ginkgo-h3-standardkeys-v2.img')
print('TELEFONA YAZILMADI. FORMAT YAPILMADI.')
