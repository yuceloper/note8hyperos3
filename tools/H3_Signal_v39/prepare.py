"""Repair the proven V38 DEX layout defect. Offline review only; no install/flash."""
from pathlib import Path
import argparse,hashlib,json,struct,sys,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'H3_Signal_v38'))
from build import checksum,definitions,maps,strip_hidden,u32,uleb
SOURCE='f3c66613c8433783c1b6b8608b7e89721b7a3d9d127ad7e92bf0817f80c7b258'
FAILED='f7249325117c9777652d374f2431e3a2589f0c06c13aadbad1c867ec2cf31d0f'
HIDDEN='15f53cbeee10955b9dded772f7a62e587339f0da094dd7f560e03ddc21303be2'
def sha(b):return hashlib.sha256(b).hexdigest()

def class_data_end(b):
    entries=maps(b);items=[e for e in entries if e[0]==0x2000]
    if len(items)!=1:raise RuntimeError('Expected one class-data section')
    _,_,count,o=items[0]
    for _ in range(count):
        counts=[]
        for _ in range(4):v,o=uleb(b,o);counts.append(v)
        for group,n in enumerate(counts):
            for _ in range(n):
                for _ in range(2 if group<2 else 3):v,o=uleb(b,o)
                if o>len(b):raise RuntimeError('Class data out of range')
    return o

def check_class_data_padding(b):
    end=class_data_end(b)
    starts=[e[3] for e in maps(b) if e[3]>=end and e[0]!=0x2000]
    if not starts:raise RuntimeError('No following section')
    following=min(starts)
    if any(b[end:following]):raise RuntimeError('Non-zero bytes between class-data end and next section at '+hex(end))
    return end,following

def repair(original,bad):
    if original[:8]!=b'dex\n039\0' or bad[:8]!=b'dex\n035\0':raise RuntimeError('Unexpected source/failed DEX versions')
    if len(original)!=u32(original,32) or len(bad)!=u32(bad,32):raise RuntimeError('DEX size mismatch')
    if checksum(original)!=original or checksum(bad)!=bad:raise RuntimeError('DEX checksum mismatch')
    if definitions(original)!=definitions(bad):raise RuntimeError('Definitions/member order mismatch')
    _,hidden=strip_hidden(original);_,hidden_bad=strip_hidden(bad)
    if sha(hidden)!=HIDDEN or hidden_bad!=hidden:raise RuntimeError('Hidden-API data mismatch')
    entries=maps(bad);end=class_data_end(bad)
    hidden_entry=next(e for e in entries if e[0]==0xf000)
    gap=bad[end:hidden_entry[3]]
    # Prove the gap is exactly the orphaned assembler map, not arbitrary data.
    old_entries=[(t,u,n,end if t==0x1000 else o) for t,u,n,o in entries if t!=0xf000]
    old_entries.sort(key=lambda e:e[3])
    expected=struct.pack('<I',len(old_entries))+b''.join(struct.pack('<HHII',*e) for e in old_entries)
    if gap!=expected or len(gap)!=208:raise RuntimeError('Failed candidate does not contain the exact known orphan map')
    keep=[e for e in entries if e[0] not in (0xf000,0x1000)]
    if any(e[3]>=end for e in keep):raise RuntimeError('Unexpected mapped section after class data')
    b=bytearray(bad[:end]);b[:8]=original[:8]
    hidden_off=len(b);b.extend(hidden)
    while len(b)%4:b.append(0)
    map_off=len(b);new_entries=keep+[(0xf000,0,1,hidden_off),(0x1000,0,1,map_off)]
    new_entries.sort(key=lambda e:e[3]);b.extend(struct.pack('<I',len(new_entries)))
    for e in new_entries:b.extend(struct.pack('<HHII',*e))
    struct.pack_into('<I',b,52,map_off);struct.pack_into('<I',b,32,len(b));struct.pack_into('<I',b,104,len(b)-u32(b,108))
    fixed=checksum(b)
    if fixed[112:end]!=bad[112:end]:raise RuntimeError('Method/data payload changed during layout repair')
    if definitions(fixed)!=definitions(original):raise RuntimeError('Repaired definitions mismatch')
    _,restored=strip_hidden(fixed)
    if restored!=hidden:raise RuntimeError('Hidden-API flags changed')
    check_class_data_padding(fixed)
    return fixed,{'orphan_map_removed_bytes':len(gap),'class_data_end':end,'old_hidden_api_offset':hidden_entry[3],
        'new_hidden_api_offset':hidden_off,'dex_version':fixed[4:7].decode(),'method_and_data_bytes_unchanged_from_v38':True}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--failed',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();source=Path(a.source);failed=Path(a.failed);out=Path(a.out)
    if sha(source.read_bytes())!=SOURCE or sha(failed.read_bytes())!=FAILED:raise RuntimeError('Exact input JAR hashes required')
    if out.exists():raise RuntimeError('Output exists; nothing overwritten')
    with zipfile.ZipFile(source) as zs,zipfile.ZipFile(failed) as zf:
        if zs.namelist()!=zf.namelist() or zf.testzip():raise RuntimeError('JAR entries invalid')
        for name in zs.namelist():
            if name!='classes.dex' and zs.read(name)!=zf.read(name):raise RuntimeError('Unexpected non-DEX entry change')
        fixed,details=repair(zs.read('classes.dex'),zf.read('classes.dex'))
        out.mkdir(parents=True,exist_ok=False);target=out/'telephony-common-v39.jar'
        with zipfile.ZipFile(target,'w') as z:
            for item in zf.infolist():z.writestr(item,fixed if item.filename=='classes.dex' else zf.read(item.filename))
    with zipfile.ZipFile(target) as z:
        if z.testzip() or z.read('classes.dex')!=fixed:raise RuntimeError('Output JAR verification failed')
    result={'status':'OFFLINE_REVIEW_ONLY_NOT_INSTALLED_NOT_ART_VERIFIED','source_sha256':SOURCE,'failed_v38_sha256':FAILED,
        'candidate_sha256':sha(target.read_bytes()),'hidden_api_sha256':HIDDEN,**details}
    (out/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print('V39 DEX YAPI ADAYI HAZIR')
    print('SHA256: '+result['candidate_sha256'])
    print('208 BAYT ARTIK TABLO KALDIRILDI. DEX 039 VE GIZLI API KISITLAMALARI KORUNDU.')
    print('SINIF/METOT KODU V38 ILE AYNI. ART TESTI YAPILMADI. CALISMA AGACI VE TELEFON DEGISTIRILMEDI.')
if __name__=='__main__':main()
