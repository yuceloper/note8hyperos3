"""Prepare a review-only telephony JAR. Does not install or flash anything."""
from pathlib import Path
import argparse, hashlib, json, re, struct, subprocess, zipfile, zlib
from patch_smali import patch
SOURCE_SHA='f3c66613c8433783c1b6b8608b7e89721b7a3d9d127ad7e92bf0817f80c7b258'

def sha(b): return hashlib.sha256(b).hexdigest()
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def checksum(b):
    b=bytearray(b);b[12:32]=hashlib.sha1(b[32:]).digest()
    struct.pack_into('<I',b,8,zlib.adler32(b[12:])&0xffffffff)
    return bytes(b)
def maps(b):
    off=u32(b,52)
    return [struct.unpack_from('<HHII',b,off+4+12*i) for i in range(u32(b,off))]
def strip_hidden(b):
    entries=maps(b);h=[x for x in entries if x[0]==0xf000]
    if len(h)!=1 or h[0][2]!=1:raise RuntimeError('Expected one hidden-API section')
    off=h[0][3];raw=b[off:off+u32(b,off)]
    entries.remove(h[0]);b=bytearray(b);mo=u32(b,52)
    struct.pack_into('<I',b,mo,len(entries))
    for i,e in enumerate(entries):struct.pack_into('<HHII',b,mo+4+12*i,*e)
    return checksum(b),raw

def uleb(b,o):
    v=0;s=0
    while True:
        x=b[o];o+=1;v|=(x&127)<<s
        if not x&128:return v,o
        s+=7
        if s>35:raise RuntimeError('Bad ULEB')

def definitions(b):
    # Exact declaration order is what the raw hidden-API member flags index.
    so=u32(b,60);to=u32(b,68);po=u32(b,76);fo=u32(b,84);mo=u32(b,92)
    strings=[]
    for i in range(u32(b,56)):
        o=u32(b,so+4*i);_,o=uleb(b,o);end=b.index(0,o)
        strings.append(b[o:end].decode('utf-8',errors='surrogateescape'))
    types=[strings[u32(b,to+4*i)] for i in range(u32(b,64))]
    protos=[]
    for i in range(u32(b,72)):
        _,rt,pa=struct.unpack_from('<III',b,po+12*i)
        args=[] if pa==0 else [types[struct.unpack_from('<H',b,pa+4+2*j)[0]] for j in range(u32(b,pa))]
        protos.append('('+''.join(args)+')'+types[rt])
    fields=[]
    for i in range(u32(b,80)):
        c,t,n=struct.unpack_from('<HHI',b,fo+8*i);fields.append((types[c],strings[n],types[t]))
    methods=[]
    for i in range(u32(b,88)):
        c,p,n=struct.unpack_from('<HHI',b,mo+8*i);methods.append((types[c],strings[n],protos[p]))
    result=[];co=u32(b,100)
    for i in range(u32(b,96)):
        ci,access,superi,interfaces,source,annotations,data,staticvalues=struct.unpack_from('<8I',b,co+32*i)
        groups=[];o=data
        if data:
            counts=[]
            for _ in range(4):n,o=uleb(b,o);counts.append(n)
            for g,n in enumerate(counts):
                index=0;items=[]
                for _ in range(n):
                    delta,o=uleb(b,o);index+=delta;flags,o=uleb(b,o)
                    key=(fields if g<2 else methods)[index]
                    if g>=2:_,o=uleb(b,o)
                    # The only signature widened is a private helper, never an external API.
                    if key[0]=='Lcom/android/internal/telephony/RadioResponse;' and key[1]=='responseSignalStrength':
                        key=(key[0],key[1],key[2].replace('Landroid/hardware/radio/V1_4/SignalStrength;','Ljava/lang/Object;'))
                    items.append((key,flags))
                groups.append(items)
        result.append((types[ci],access,groups))
    return result

def restore_hidden(original, rebuilt, hidden):
    if definitions(original)!=definitions(rebuilt):raise RuntimeError('Class/member order or access flags changed')
    b=bytearray(rebuilt)
    while len(b)%4:b.append(0)
    off=len(b);b.extend(hidden)
    while len(b)%4:b.append(0)
    mo=len(b);entries=[e for e in maps(rebuilt) if e[0]!=0x1000]
    if any(e[0]==0xf000 for e in entries):raise RuntimeError('Unexpected hidden API section in assembler output')
    entries += [(0xf000,0,1,off),(0x1000,0,1,mo)]
    entries.sort(key=lambda e:e[3]);b.extend(struct.pack('<I',len(entries)))
    for e in entries:b.extend(struct.pack('<HHII',*e))
    struct.pack_into('<I',b,52,mo);struct.pack_into('<I',b,32,len(b))
    struct.pack_into('<I',b,104,len(b)-u32(b,108))
    result=checksum(b)
    _,restored=strip_hidden(result)
    if restored!=hidden:raise RuntimeError('Hidden-API flags not preserved byte for byte')
    return result

EXPECTED={
 'RadioResponse.smali':{'responseSignalStrength(Landroid/hardware/radio/V1_0/RadioResponseInfo;Ljava/lang/Object;)V','getSignalStrengthResponse(Landroid/hardware/radio/V1_0/RadioResponseInfo;Landroid/hardware/radio/V1_0/SignalStrength;)V','getSignalStrengthResponse_1_2(Landroid/hardware/radio/V1_0/RadioResponseInfo;Landroid/hardware/radio/V1_2/SignalStrength;)V','getSignalStrengthResponse_1_4(Landroid/hardware/radio/V1_0/RadioResponseInfo;Landroid/hardware/radio/V1_4/SignalStrength;)V'},
 'RadioIndication.smali':{'currentSignalStrength(ILandroid/hardware/radio/V1_0/SignalStrength;)V','currentSignalStrength_1_2(ILandroid/hardware/radio/V1_2/SignalStrength;)V'},
 'RILUtils.smali':{'convertHalSignalStrength(Ljava/lang/Object;)Landroid/telephony/SignalStrength;','convertHalTdscdmaSignalStrength(Ljava/lang/Object;)Landroid/telephony/CellSignalStrengthTdscdma;'},
}

def canonical(s):
    lines=[];labels={}
    for line in s.splitlines():
        line=line.strip()
        if not line or line.startswith(('#','.line ','.local ','.end local ','.restart local ','.prologue','.epilogue','.source ')):continue
        if line.startswith('.field '):
            line=re.sub(r' = (?:false|0x0|null)$','',line)
        # Labels generated from code offsets can move when method bodies grow.
        line=re.sub(r':[A-Za-z_][A-Za-z0-9_]*',lambda m:labels.setdefault(m.group(),' :L'+str(len(labels))).strip(),line)
        lines.append(line)
    return '\n'.join(lines)

def method_inventory(s):
    out={}
    for m in re.finditer(r'^\.method ([^\n]+)\n.*?^\.end method',s,re.M|re.S):
        key=m.group(1).split()[-1]
        if key.startswith('responseSignalStrength('):key=key.replace('Landroid/hardware/radio/V1_4/SignalStrength;','Ljava/lang/Object;')
        if key in out:raise RuntimeError('Duplicate method')
        out[key]=canonical(m.group())
    remainder=re.sub(r'^\.method [^\n]+\n.*?^\.end method','',s,flags=re.M|re.S)
    return out,canonical(remainder)

def verify_methods(before,after):
    files=sorted(p.relative_to(before) for p in before.rglob('*.smali'))
    if files!=sorted(p.relative_to(after) for p in after.rglob('*.smali')):raise RuntimeError('Class list changed')
    changed=[]
    for rel in files:
        a,ra=method_inventory((before/rel).read_text());b,rb=method_inventory((after/rel).read_text())
        if ra!=rb or a.keys()!=b.keys():raise RuntimeError('Declaration changes: '+str(rel))
        for name in a:
            if a[name]!=b[name]:
                if name not in EXPECTED.get(rel.name,set()):raise RuntimeError('Unexpected method changed: '+str(rel)+' '+name)
                changed.append((rel.name,name))
    if set(changed)!={(f,n) for f,names in EXPECTED.items() for n in names}:raise RuntimeError('Expected method change set mismatch')
    return changed,len(files)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--classpath',default='/usr/share/java/*');a=ap.parse_args()
    source=Path(a.source);out=Path(a.out)
    if sha(source.read_bytes())!=SOURCE_SHA:raise RuntimeError('Unrecognized source JAR; nothing changed')
    out.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(source) as z:original=z.read('classes.dex')
    stripped,hidden=strip_hidden(original);(out/'input-nohidden.dex').write_bytes(stripped)
    def java(main,*args):
        r=subprocess.run(['java','-cp',a.classpath,main,*map(str,args)],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=180)
        if r.returncode or 'Error' in r.stderr or 'Exception' in r.stderr:raise RuntimeError(r.stderr or r.stdout)
    java('org.jf.baksmali.Main','d',out/'input-nohidden.dex','-o',out/'before')
    import shutil
    shutil.copytree(out/'before',out/'patched');patch(out/'patched')
    java('org.jf.smali.Main','a',out/'patched','-o',out/'rebuilt.dex')
    rebuilt=(out/'rebuilt.dex').read_bytes();final=restore_hidden(original,rebuilt,hidden)
    (out/'candidate.dex').write_bytes(final)
    stripped_final,_=strip_hidden(final);(out/'verify-nohidden.dex').write_bytes(stripped_final)
    java('org.jf.baksmali.Main','d',out/'verify-nohidden.dex','-o',out/'verified')
    changed,count=verify_methods(out/'before',out/'verified')
    target=out/'telephony-common-v38.jar'
    with zipfile.ZipFile(source) as zin,zipfile.ZipFile(target,'w') as zout:
        for item in zin.infolist():zout.writestr(item,final if item.filename=='classes.dex' else zin.read(item.filename))
    with zipfile.ZipFile(source) as zin,zipfile.ZipFile(target) as zout:
        if zin.namelist()!=zout.namelist() or zout.testzip():raise RuntimeError('JAR structure verification failed')
        for name in zin.namelist():
            if name!='classes.dex' and zin.read(name)!=zout.read(name):raise RuntimeError('Unexpected JAR entry change')
    report={'status':'REVIEW_ONLY_NOT_INSTALLED_NOT_RUNTIME_TESTED','source_sha256':SOURCE_SHA,'candidate_sha256':sha(target.read_bytes()),'hidden_api_sha256':sha(hidden),'class_count':count,'changed_methods':changed,'request_proxy_and_signal_controller_unchanged':True,'source_reference':'https://android.googlesource.com/platform/frameworks/opt/telephony/+/refs/heads/android13-release/src/java/com/android/internal/telephony/RILUtils.java'}
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('V38 ESKI SINYAL CEVABI ADAYI HAZIR')
    print('SHA256: '+report['candidate_sha256'])
    print('8 YONTEM / 3 SINIF. GIZLI API KISITLAMALARI BIREBIR KORUNDU.')
    print('CALISMA AGACINA KURULMADI. TELEFONA YAZILMADI. RUNTIME TEST BEKLENIYOR.')
if __name__=='__main__':main()
