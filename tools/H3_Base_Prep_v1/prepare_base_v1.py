from pathlib import Path
import hashlib, json, os, shutil, stat

prep=Path('/prep')
root=Path('/linux/build/hyperos3-ginkgo-v1')
policy=Path('/policy')
meta=json.loads((prep/'validation.json').read_text())

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(condition,message):
    if not condition: raise RuntimeError(message)
def label(p,context): os.setxattr(p,'security.selinux',context.encode()+b'\0')
def directory(p):
    p.mkdir(exist_ok=True)
    os.chown(p,0,0); os.chmod(p,0o755)
    label(p,'u:object_r:vendor_configs_file:s0')
def install(src,dst,context):
    with dst.open('xb') as f: f.write(src.read_bytes())
    os.chown(dst,0,0); os.chmod(dst,0o644)
    label(dst,context)

init=root/'system/etc/init/hw/init.rc'
odm=root/'odm'
etc=odm/'etc'
backup=Path('/linux/backups/hyperos3-base-prep-v1')
require(root.is_dir() and not root.is_symlink(),'Calisma agaci bulunamadi')
require(odm.is_dir() and not odm.is_symlink(),'ODM gercek dizin olmali')
require(etc.is_symlink() and os.readlink(etc)=='/vendor/odm/etc','ODM/etc beklenen vendor baglantisi degil')
require(not backup.exists(),'Bu hazirlik zaten uygulanmis veya yedek mevcut')
require(digest(init)==meta['source_init_sha256'],'Init kaynak hash uyusmuyor')
require(digest(prep/'init.rc.candidate')==meta['patched_init_sha256'],'Init aday hash uyusmuyor')
compiled=policy/'combined-compat-v2.policy'
require(digest(compiled)==meta['policy_sha256'],'Politika hash uyusmuyor')
contexts=policy/'odm/selinux'
labels={
 'odm_sepolicy.cil':'sepolicy_file',
 'odm_file_contexts':'file_contexts_file',
 'odm_seapp_contexts':'seapp_contexts_file',
 'odm_property_contexts':'property_contexts_file',
 'odm_service_contexts':'vendor_service_contexts_file',
 'odm_hwservice_contexts':'hwservice_contexts_file',
 'odm_mac_permissions.xml':'mac_perms_file',
}
require(set(labels)==set(meta['odm_context_sha256']),'Beklenmeyen ODM context listesi')
for name,sha in meta['odm_context_sha256'].items():
    require(digest(contexts/name)==sha,'ODM context hash uyusmuyor: '+name)
hashes={}
for partition,name in [('system','plat'),('system_ext','system_ext'),('product','product')]:
    src=root/partition/'etc/selinux'/f'{name}_sepolicy_and_mapping.sha256'
    require(src.is_file() and len(src.read_text().strip())==64,'Platform hash dosyasi eksik: '+str(src))
    hashes[name]=src

print('TUM ON KONTROLLER BASARILI',flush=True)
backup.mkdir(parents=True)
shutil.copy2(init,backup/'init.rc')
(backup/'odm-etc-link.txt').write_text(os.readlink(etc)+'\n')
etc.unlink()
directory(etc)
for name in meta['odm_entries']:
    (etc/name).symlink_to('/vendor/odm/etc/'+name)
selinux=etc/'selinux'
directory(selinux)
for name,typ in labels.items(): install(contexts/name,selinux/name,'u:object_r:'+typ+':s0')
install(compiled,selinux/'precompiled_sepolicy','u:object_r:sepolicy_file:s0')
for name,src in hashes.items():
    install(src,selinux/f'precompiled_sepolicy.{name}_sepolicy_and_mapping.sha256','u:object_r:sepolicy_file:s0')
st=init.stat()
before_xattrs={n:os.getxattr(init,n) for n in os.listxattr(init)}
with init.open('r+b') as f:
    f.write((prep/'init.rc.candidate').read_bytes());f.truncate()
os.utime(init,ns=(st.st_atime_ns,st.st_mtime_ns))
require(digest(init)==meta['patched_init_sha256'],'Init yazma dogrulamasi basarisiz')
require((init.stat().st_uid,init.stat().st_gid,stat.S_IMODE(init.stat().st_mode))==(st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode)),'Init metadata degisti')
require(all(os.getxattr(init,n)==v for n,v in before_xattrs.items()),'Init xattr degisti')
require(digest(selinux/'precompiled_sepolicy')==meta['policy_sha256'],'Politika yazma dogrulamasi basarisiz')
print('POLITIKA ODM ALTINA KURULDU. VENDOR ODM AYARLARI BAGLANTILARLA KORUNDU.')
print('EARLY_HAL POST-FS ASAMASINA ALINDI. INIT METADATA KORUNDU.')
print('VINTF VE BOOT HENUZ HAZIR DEGIL. TELEFONA YAZILMADI.')
