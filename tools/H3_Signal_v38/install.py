"""Install V38 into the offline Linux tree only, with verified rollback data."""
from pathlib import Path
import argparse, base64, hashlib, json, os, stat, zipfile
SOURCE='f3c66613c8433783c1b6b8608b7e89721b7a3d9d127ad7e92bf0817f80c7b258'
CANDIDATE='f7249325117c9777652d374f2431e3a2589f0c06c13aadbad1c867ec2cf31d0f'
REL=Path('system/framework/telephony-common.jar')
PREOPT=[Path('system/framework/telephony-common.jar.fsv_meta'),
        Path('system/framework/boot-telephony-common.vdex'),
        Path('system/framework/boot-telephony-common.vdex.fsv_meta')]
for arch in ['arm','arm64']:
    for ext in ['art','oat']:
        PREOPT += [Path(f'system/framework/{arch}/boot-telephony-common.{ext}'),
                   Path(f'system/framework/{arch}/boot-telephony-common.{ext}.fsv_meta')]

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def meta(p):
    s=p.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:raise RuntimeError('Expected regular non-hardlinked file: '+str(p))
    return {'inode':s.st_ino,'uid':s.st_uid,'gid':s.st_gid,'mode':stat.S_IMODE(s.st_mode),
            'mtime_ns':s.st_mtime_ns,'xattrs':{n:base64.b64encode(os.getxattr(p,n)).decode() for n in sorted(os.listxattr(p))}}
def plain_path(tree,rel):
    p=tree
    for part in rel.parts:
        p=p/part
        if p.is_symlink():raise RuntimeError('Symlink in installation path: '+str(p))
    return p

def rewrite(p,data,metadata):
    # In-place rewrite retains inode, mode, owner, SELinux label and xattrs.
    # Do not call setxattr on unchanged security attributes (Docker can reject it).
    with p.open('r+b') as f:
        f.seek(0);f.write(data);f.truncate();f.flush();os.fsync(f.fileno())
    os.utime(p,ns=(p.stat().st_atime_ns,metadata['mtime_ns']))
    if meta(p)!=metadata:raise RuntimeError('JAR metadata changed unexpectedly')

def install(tree,candidate,report,out,backup,expected=CANDIDATE):
    tree=Path(tree);candidate=Path(candidate);out=Path(out);backup=Path(backup)
    jar=plain_path(tree,REL)
    if digest(jar)!=SOURCE:raise RuntimeError('Offline source JAR hash mismatch; no changes')
    if digest(candidate)!=expected:raise RuntimeError('Candidate JAR hash mismatch; no changes')
    r=json.loads(Path(report).read_text())
    if (r.get('status')!='REVIEW_ONLY_NOT_INSTALLED_NOT_RUNTIME_TESTED' or
        r.get('source_sha256')!=SOURCE or r.get('candidate_sha256')!=expected or
        r.get('hidden_api_sha256')!='15f53cbeee10955b9dded772f7a62e587339f0da094dd7f560e03ddc21303be2' or
        r.get('class_count')!=3367 or len(r.get('changed_methods',[]))!=8 or
        r.get('request_proxy_and_signal_controller_unchanged') is not True):
        raise RuntimeError('Review report mismatch; no changes')
    with zipfile.ZipFile(jar) as a,zipfile.ZipFile(candidate) as b:
        if a.namelist()!=b.namelist() or b.testzip():raise RuntimeError('JAR entry verification failed')
        for name in a.namelist():
            if name!='classes.dex' and a.read(name)!=b.read(name):raise RuntimeError('Non-DEX entry changed')
    if backup.exists() or out.exists():raise RuntimeError('Backup/output already exists; nothing overwritten')
    items={str(REL):{'sha256':SOURCE,'metadata':meta(jar)}}
    for rel in PREOPT:
        p=plain_path(tree,rel)
        if not p.exists():raise RuntimeError('Expected preoptimization file missing: '+str(rel))
        items[str(rel)]={'sha256':digest(p),'metadata':meta(p)}
    for arch in ['arm','arm64']:
        unexpected=set((tree/'system/framework'/arch).glob('boot-telephony-common.*'))-{tree/r for r in PREOPT}
        if unexpected:raise RuntimeError('Unexpected target preoptimization files: '+str(unexpected))
    out.mkdir(parents=True,exist_ok=False);backup.mkdir(parents=True,exist_ok=False)
    original=jar.read_bytes();replacement=candidate.read_bytes()
    (backup/'telephony-common.original.jar').write_bytes(original)
    manifest={'status':'BACKUP_VERIFIED_BEFORE_INSTALL','files':items,'candidate_sha256':expected}
    (backup/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if digest(backup/'telephony-common.original.jar')!=SOURCE:raise RuntimeError('Original JAR backup failed')
    moved=[];written=False
    try:
        for rel in PREOPT:
            src=tree/rel;dst=backup/'preopt'/rel;dst.parent.mkdir(parents=True,exist_ok=True)
            # A same-filesystem rename preserves all preopt metadata and inodes.
            src.rename(dst);moved.append(rel)
            if digest(dst)!=items[str(rel)]['sha256'] or meta(dst)!=items[str(rel)]['metadata']:
                raise RuntimeError('Preopt backup verification failed: '+str(rel))
        written=True;rewrite(jar,replacement,items[str(REL)]['metadata'])
        if digest(jar)!=expected:raise RuntimeError('Installed JAR hash mismatch')
        for rel in PREOPT:
            if (tree/rel).exists():raise RuntimeError('Stale target preopt still present')
        result={'status':'OFFLINE_INSTALLED_NOT_BOOT_TESTED','source_sha256':SOURCE,
                'candidate_sha256':expected,'backup':str(backup),'files':items,
                'moved_preoptimization_files':list(map(str,PREOPT))}
        (out/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    except BaseException as error:
        failures=[]
        if written:
            try:
                rewrite(jar,original,items[str(REL)]['metadata'])
                if digest(jar)!=SOURCE:raise RuntimeError('Original JAR restore hash mismatch')
            except BaseException as e:failures.append(str(e))
        for rel in reversed(moved):
            try:
                dst=tree/rel;src=backup/'preopt'/rel
                if dst.exists():raise RuntimeError('Rollback destination unexpectedly exists: '+str(dst))
                src.rename(dst)
                if digest(dst)!=items[str(rel)]['sha256'] or meta(dst)!=items[str(rel)]['metadata']:
                    raise RuntimeError('Preopt rollback verification failed: '+str(rel))
            except BaseException as e:failures.append(str(e))
        (backup/'failure.json').write_text(json.dumps({'error':repr(error),'rollback_failures':failures},indent=2)+'\n')
        if failures:raise RuntimeError('ROLLBACK INCOMPLETE: '+repr(failures)) from error
        raise RuntimeError('Installation failed; original JAR and preopt restored and verified: '+repr(error)) from error
    print('V38 TELEPHONY JAR CALISMA AGACINA YERLESTIRILDI')
    print('SHA256: '+expected)
    print('JAR INODE/IZIN/ETIKETLERI KORUNDU. 11 ESKI DERLEME/META DOSYASI YEDEGE TASINDI.')
    print('POLITIKA VE VENDOR DEGISTIRILMEDI. TELEFONA YAZILMADI.')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--candidate',required=True);ap.add_argument('--report',required=True)
    a=ap.parse_args();tree=Path('/linux/build/hyperos3-ginkgo-v1')
    p=plain_path(tree,REL)
    if os.getxattr(p,'security.selinux').rstrip(b'\0')!=b'u:object_r:system_file:s0':
        raise RuntimeError('Unexpected source JAR SELinux label; no changes')
    install(tree,Path(a.candidate),Path(a.report),Path('/out/stage-v1'),Path('/linux/backups/hyperos3-signal-v38'))
if __name__=='__main__':main()
