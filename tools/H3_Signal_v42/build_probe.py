"""Extract actual V39/V40 converter methods into isolated diagnostic classes."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'H3_Signal_v38'))
from build import strip_hidden,canonical
V39='452faaae8d36ac59f4f6b7830ea4fd126b878678f377e79e8184568f40a33300'
V40='1279a5eb44e5a0ff6ca32943af7b7b31f793c668adff9c1849ff146c3f9fe5a0'
RIL='Lcom/android/internal/telephony/RILUtils;'
SIGNATURES=['convertHalSignalStrength(Ljava/lang/Object;)Landroid/telephony/SignalStrength;',
            'convertHalTdscdmaSignalStrength(Ljava/lang/Object;)Landroid/telephony/CellSignalStrengthTdscdma;']
def sha(b):return hashlib.sha256(b).hexdigest()
def extract(s,signature):
    matches=list(re.finditer(r'^\.method [^\n]*\b'+re.escape(signature)+r'\n.*?^\.end method',s,re.M|re.S))
    if len(matches)!=1:raise RuntimeError('Expected unique actual converter: '+signature)
    if '.method public static ' not in matches[0].group():raise RuntimeError('Unexpected converter access')
    return matches[0].group()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--v39',required=True);ap.add_argument('--v40',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--classpath',default='/usr/share/java/*');a=ap.parse_args();out=Path(a.out)
    inputs=[('39',Path(a.v39),V39),('40',Path(a.v40),V40)]
    for _,p,h in inputs:
        if sha(p.read_bytes())!=h:raise RuntimeError('Exact converter input hash required: '+str(p))
    if out.exists():raise RuntimeError('Output already exists')
    out.mkdir(parents=True,exist_ok=False);smali=out/'probe-smali';smali.mkdir()
    def java(main,*args):
        r=subprocess.run(['java','-cp',a.classpath,main,*map(str,args)],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=120)
        if r.returncode or 'Error' in r.stderr or 'Exception' in r.stderr:raise RuntimeError(r.stderr or r.stdout)
    expected_methods={}
    report={'status':'ISOLATED_PROBE_BUILT_NOT_RUN','probe_revision':2,'inputs':{},'purpose':'Synthetic HAL payload conversion only; no modem/system replacement'}
    for version,p,h in inputs:
        with zipfile.ZipFile(p) as z:dex=z.read('classes.dex')
        stripped,_=strip_hidden(dex);dexpath=out/('v'+version+'-analysis.dex');dexpath.write_bytes(stripped)
        folder=out/('v'+version+'-smali')
        java('org.jf.baksmali.Main','d','--classes',RIL,dexpath,'-o',folder)
        text=(folder/'com/android/internal/telephony/RILUtils.smali').read_text()
        methods=[extract(text,sig) for sig in SIGNATURES]
        owner='Lcom/ginkgo/signalprobe/V'+version+'Converters;'
        # Only calls to the copied TD helper use the probe owner. All unchanged
        # public conversion helpers resolve from the currently running V35 framework.
        body='\n\n'.join(methods).replace(RIL+'->'+SIGNATURES[1],owner+'->'+SIGNATURES[1])
        expected_methods[version]=[extract(body,sig) for sig in SIGNATURES]
        target=smali/('V'+version+'Converters.smali')
        target.write_text('.class public final '+owner+'\n.super Ljava/lang/Object;\n\n'+body+'\n')
        report['inputs']['v'+version]={'jar_sha256':h,'methods':SIGNATURES,'original_method_text_sha256':[sha(m.encode()) for m in methods]}
    (smali/'Main.smali').write_text(Path(__file__).with_name('Main.smali.template').read_text())
    java('org.jf.smali.Main','a',smali,'-o',out/'classes.dex')
    java('org.jf.baksmali.Main','d',out/'classes.dex','-o',out/'roundtrip')
    for version in ['39','40']:
        p=out/'roundtrip/com/ginkgo/signalprobe'/('V'+version+'Converters.smali')
        text=p.read_text()
        for sig,expected_method in zip(SIGNATURES,expected_methods[version]):
            if canonical(extract(text,sig))!=canonical(expected_method):raise RuntimeError('Copied converter roundtrip mismatch: '+version+' '+sig)
    target=out/'signal-conversion-probe.jar'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as z:z.write(out/'classes.dex','classes.dex')
    report['probe_sha256']=sha(target.read_bytes())
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('V42 IZOLE SINYAL DONUSTURME TESTI HAZIR')
    print('SHA256: '+report['probe_sha256'])
    print('V39/V40 GERCEK DONUSTURUCU METOTLARI. SISTEM JARLARI DEGISTIRILMEDI. TELEFONA KURULMADI.')
if __name__=='__main__':main()
