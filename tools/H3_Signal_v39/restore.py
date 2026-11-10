"""Restore the offline V35 telephony JAR and exact preopt files. Never flash."""
from pathlib import Path
import json
from install import SOURCE,CANDIDATE,REL,PREOPT,LINKS,digest,meta,rewrite,plain_path

def restore(tree,backup,stage):
    tree=Path(tree);backup=Path(backup);stage=Path(stage)
    jar=plain_path(tree,REL);manifest=json.loads((backup/'manifest.json').read_text())
    items=manifest['files'];report=backup/'restored-v35.json'
    if (manifest.get('status')!='BACKUP_VERIFIED_BEFORE_INSTALL' or manifest.get('candidate_sha256')!=CANDIDATE
        or set(items)!={str(r) for r in PREOPT+[REL]}):raise RuntimeError('Unexpected backup manifest')
    original=backup/'telephony-common.original.jar'
    if digest(original)!=SOURCE:raise RuntimeError('Original JAR backup hash mismatch')
    original_meta=items[str(REL)]['metadata']
    if digest(jar)==SOURCE and report.exists():
        if meta(jar)!=original_meta:raise RuntimeError('Restored JAR metadata mismatch')
        for rel in PREOPT:
            p=plain_path(tree,rel)
            if digest(p)!=items[str(rel)]['sha256'] or meta(p)!=items[str(rel)]['metadata']:
                raise RuntimeError('Previously restored preopt changed: '+str(rel))
        print('V35 CALISMA AGACI ZATEN GERI YUKLENMIS; TEKRAR DOGRULANDI.');return
    if digest(jar)!=CANDIDATE or meta(jar)!=original_meta:raise RuntimeError('Installed V39 JAR hash/metadata mismatch')
    stage_data=json.loads(stage.read_text())
    if stage_data.get('status')!='OFFLINE_INSTALLED_NOT_BOOT_TESTED' or stage_data.get('files')!=items:
        raise RuntimeError('Stage report mismatch')
    for rel in PREOPT:
        dst=tree/rel;src=backup/'preopt'/rel
        if dst.exists() or dst.is_symlink():raise RuntimeError('Restore destination occupied: '+str(rel))
        if rel in LINKS:
            if not src.is_symlink() or src.readlink()!=Path(LINKS[rel]):raise RuntimeError('Backup symlink target mismatch')
        elif src.is_symlink():raise RuntimeError('Regular backup unexpectedly symlink')
        if digest(src)!=items[str(rel)]['sha256'] or meta(src)!=items[str(rel)]['metadata']:
            raise RuntimeError('Preopt backup verification failed: '+str(rel))
    failed=backup/'telephony-common.failed-v39.jar'
    if failed.exists() or report.exists():raise RuntimeError('Recovery output already exists; nothing overwritten')
    failed.write_bytes(jar.read_bytes())
    if digest(failed)!=CANDIDATE:raise RuntimeError('Failed candidate preservation failed')
    moved=[];written=False
    try:
        written=True;rewrite(jar,original.read_bytes(),original_meta)
        if digest(jar)!=SOURCE:raise RuntimeError('Original JAR restore hash mismatch')
        for rel in PREOPT:
            src=backup/'preopt'/rel;dst=tree/rel
            src.rename(dst);moved.append(rel)
            if digest(dst)!=items[str(rel)]['sha256'] or meta(dst)!=items[str(rel)]['metadata']:
                raise RuntimeError('Restored artifact verification failed: '+str(rel))
        report.write_text(json.dumps({'status':'OFFLINE_V35_TELEPHONY_RESTORED','jar_sha256':SOURCE,
            'restored_artifacts':list(map(str,PREOPT)),'preserved_failed_candidate':str(failed)},indent=2)+'\n')
    except BaseException as error:
        errors=[]
        for rel in reversed(moved):
            try:
                dst=backup/'preopt'/rel
                if dst.exists() or dst.is_symlink():raise RuntimeError('Recovery rollback path occupied')
                (tree/rel).rename(dst)
                if digest(dst)!=items[str(rel)]['sha256'] or meta(dst)!=items[str(rel)]['metadata']:
                    raise RuntimeError('Recovery rollback artifact mismatch')
            except BaseException as e:errors.append(repr(e))
        if written:
            try:
                rewrite(jar,failed.read_bytes(),original_meta)
                if digest(jar)!=CANDIDATE:raise RuntimeError('Recovery rollback JAR mismatch')
            except BaseException as e:errors.append(repr(e))
        if report.exists():report.unlink()
        (backup/'restore-failure.json').write_text(json.dumps({'error':repr(error),'rollback_errors':errors},indent=2)+'\n')
        raise RuntimeError('Restore failed; rollback errors='+repr(errors)) from error
    print('V35 TELEPHONY CALISMA AGACI GERI YUKLENDI')
    print('SHA256: '+SOURCE)
    print('11 DOSYA VE 4 BAGLANTI; INODE/IZIN/ETIKETLER DOGRULANDI.')
    print('V39 ADAYI KORUNDU. TELEFONA YAZILMADI.')

if __name__=='__main__':
    restore('/linux/build/hyperos3-ginkgo-v1','/linux/backups/hyperos3-signal-v39','/out/stage-v1/validation.json')
