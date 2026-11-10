"""Require non-inline on-disk symlinks to avoid old fast-symlink boundary bugs."""
from pathlib import Path
import os,re,subprocess,tempfile

CRITICAL=('system/framework/arm/boot.vdex','system/framework/arm64/boot.vdex')

def info(image,path):
    r=subprocess.run(['dump.erofs','--path=/'+path,str(image)],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=15)
    if r.returncode:raise RuntimeError('dump.erofs failed for '+path+': '+r.stderr)
    s=r.stdout
    def value(pattern):
        m=re.search(pattern,s)
        if not m:raise RuntimeError('Unrecognized dump output for '+path+': '+s)
        return int(m.group(1))
    if 'symlink file' not in s:raise RuntimeError('Image entry is not a symlink: '+path)
    return {'path':path,'nid':value(r'\bNID:\s*(\d+)'),'layout':value(r'\bLayout:\s*(\d+)'),'size':value(r'\bSize:\s*(\d+)')}

def audit(image,tree,require_critical=True):
    tree=Path(tree);paths=sorted(str(p.relative_to(tree)) for p in tree.rglob('*') if p.is_symlink())
    if not paths:raise RuntimeError('No source symlinks found')
    if require_critical and not set(CRITICAL)<=set(paths):raise RuntimeError('Critical boot.vdex aliases missing')
    critical=[]
    for i,path in enumerate(paths,1):
        item=info(image,path)
        if item['layout']!=0:raise RuntimeError('Non-inline symlink layout required: '+repr(item))
        expected=len(os.fsencode(os.readlink(tree/path)))
        if item['size']!=expected:raise RuntimeError('Symlink length mismatch: '+path)
        if path in CRITICAL:critical.append(item)
        if i%100==0:print('SYMLINK KONTROLU: %d/%d'%(i,len(paths)),flush=True)
    return {'all_symlinks_layout_zero':True,'checked_count':len(paths),'critical':critical}

def probe():
    with tempfile.TemporaryDirectory(prefix='erofs-v41-probe-') as td:
        base=Path(td);source=base/'root';source.mkdir();(source/'target').write_bytes(b'probe\n')
        for i in range(16):(source/('link-%02d'%i)).symlink_to('target')
        image=base/'probe.img'
        r=subprocess.run(['mkfs.erofs','-b','4096','-E','noinline_data',str(image),str(source)],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=30)
        if r.returncode:raise RuntimeError('noinline_data probe failed: '+r.stderr)
        result=audit(image,source,require_critical=False)
        subprocess.run(['fsck.erofs',str(image)],stdin=subprocess.DEVNULL,capture_output=True,text=True,check=True,timeout=30)
        return result
