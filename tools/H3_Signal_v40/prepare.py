"""Correct one external HIDL field type and audit all added fields. Review only."""
from pathlib import Path
import argparse,hashlib,json,struct,sys,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'H3_Signal_v38'))
from build import checksum,definitions,maps,strip_hidden,u32,uleb
SOURCE='f3c66613c8433783c1b6b8608b7e89721b7a3d9d127ad7e92bf0817f80c7b258'
V39='452faaae8d36ac59f4f6b7830ea4fd126b878678f377e79e8184568f40a33300'
FRAMEWORK='6a78c1a8e689a7bbc138e0771ff22fb583f28e7ae888bbeee5286d3be497f47d'
OLD=('Landroid/hardware/radio/V1_2/SignalStrength;','tdScdma','Landroid/hardware/radio/V1_2/TdscdmaSignalStrength;')
NEW=(OLD[0],OLD[1],'Landroid/hardware/radio/V1_0/TdScdmaSignalStrength;')

def sha(b):return hashlib.sha256(b).hexdigest()
def table(b):
    strings=[]
    for i in range(u32(b,56)):
        o=u32(b,u32(b,60)+4*i);_,o=uleb(b,o)
        strings.append(b[o:b.index(0,o)].decode('utf-8',errors='surrogateescape'))
    types=[strings[u32(b,u32(b,68)+4*i)] for i in range(u32(b,64))]
    result=[]
    for i in range(u32(b,80)):
        c,t,n=struct.unpack_from('<HHI',b,u32(b,84)+8*i)
        result.append((types[c],strings[n],types[t]))
    return types,result

def padding(b):
    e=next(e for e in maps(b) if e[0]==0x2000);o=e[3]
    for _ in range(e[2]):
        counts=[]
        for _ in range(4):v,o=uleb(b,o);counts.append(v)
        for g,n in enumerate(counts):
            for _ in range(n):
                for _ in range(2 if g<2 else 3):v,o=uleb(b,o)
    following=min(e[3] for e in maps(b) if e[0]!=0x2000 and e[3]>=o)
    if any(b[o:following]):raise RuntimeError('Non-zero class-data section padding')

def framework_fields(path):
    out=set()
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.endswith('.dex'):
                for cls,flags,groups in definitions(z.read(name)):
                    out.update(key for group in groups[:2] for key,access in group)
    return out

def fix(original,bad,declared):
    if bad[:8]!=b'dex\n039\0' or checksum(bad)!=bad:raise RuntimeError('V39 header/checksum mismatch')
    padding(bad);types,fields=table(bad);_,source_fields=table(original)
    introduced=set(fields)-set(source_fields)
    mismatched=introduced-declared
    if len(introduced)!=12 or mismatched!={OLD} or NEW not in declared:
        raise RuntimeError('Unexpected new-field audit: '+repr(mismatched))
    if fields.count(OLD)!=1 or NEW in fields:raise RuntimeError('Expected unique erroneous field reference')
    index=fields.index(OLD);offset=u32(bad,84)+index*8+2
    b=bytearray(bad);struct.pack_into('<H',b,offset,types.index(NEW[2]));fixed=checksum(b)
    _,after=table(fixed)
    if after[:index]!=fields[:index] or after[index]!=NEW or after[index+1:]!=fields[index+1:]:
        raise RuntimeError('More than one field reference changed')
    # DEX field-ID ordering: class_idx, name_idx, type_idx.
    ids=[struct.unpack_from('<HHI',fixed,u32(fixed,84)+8*i) for i in range(u32(fixed,80))]
    keys=[(c,n,t) for c,t,n in ids]
    if keys!=sorted(set(keys)):raise RuntimeError('Field-ID order/uniqueness changed')
    masked=bytearray(fixed);masked[8:32]=bad[8:32];masked[offset:offset+2]=bad[offset:offset+2]
    if masked!=bad:raise RuntimeError('Unexpected method/data/header modification')
    if (set(after)-set(source_fields))-declared:raise RuntimeError('Unresolved newly introduced field')
    if definitions(original)!=definitions(bad) or definitions(bad)!=definitions(fixed):raise RuntimeError('Class/member definitions changed')
    _,hidden=strip_hidden(original);_,hidden40=strip_hidden(fixed)
    if hidden!=hidden40:raise RuntimeError('Hidden-API restrictions changed')
    padding(fixed)
    return fixed,{'field_id_index':index,'field_type_offset':offset,'old_field':OLD,'new_field':NEW,
        'introduced_field_count':12,'all_introduced_fields_match_framework':True,
        'method_code_unchanged_from_v39':True,'hidden_api_sha256':sha(hidden),'dex_version':'039'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--v39',required=True)
    ap.add_argument('--framework',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    source=Path(a.source);v39=Path(a.v39);fw=Path(a.framework);out=Path(a.out)
    for p,expected in [(source,SOURCE),(v39,V39),(fw,FRAMEWORK)]:
        if sha(p.read_bytes())!=expected:raise RuntimeError('Exact reference hash required: '+str(p))
    if out.exists():raise RuntimeError('Output already exists')
    declared=framework_fields(fw)
    with zipfile.ZipFile(source) as zs,zipfile.ZipFile(v39) as zv:
        if zs.namelist()!=zv.namelist() or zv.testzip():raise RuntimeError('JAR structure mismatch')
        for n in zs.namelist():
            if n!='classes.dex' and zs.read(n)!=zv.read(n):raise RuntimeError('Non-DEX entry changed')
        fixed,details=fix(zs.read('classes.dex'),zv.read('classes.dex'),declared)
        out.mkdir(parents=True,exist_ok=False);target=out/'telephony-common-v40.jar'
        with zipfile.ZipFile(target,'w') as z:
            for item in zv.infolist():z.writestr(item,fixed if item.filename=='classes.dex' else zv.read(item.filename))
    with zipfile.ZipFile(target) as z:
        if z.testzip() or z.read('classes.dex')!=fixed:raise RuntimeError('Output JAR verification failed')
    result={'status':'OFFLINE_FIELD_AUDITED_NOT_INSTALLED_NOT_RUNTIME_TESTED','source_sha256':SOURCE,
        'previous_v39_sha256':V39,'framework_sha256':FRAMEWORK,'candidate_sha256':sha(target.read_bytes()),**details}
    (out/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print('V40 TEK ALAN TURU ADAYI HAZIR')
    print('SHA256: '+result['candidate_sha256'])
    print('12 YENI ALAN CIHAZ FRAMEWORK TANIMLARIYLA DOGRULANDI.')
    print('METOT KODU DEGISTIRILMEDI. DEX 039 VE GIZLI API KISITLAMALARI KORUNDU.')
    print('CALISMA AGACI VE TELEFON DEGISTIRILMEDI. RUNTIME TEST BEKLENIYOR.')
if __name__=='__main__':main()
