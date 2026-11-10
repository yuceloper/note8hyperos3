"""Restore legacy HIDL signal responses/indications. No polling/UI changes."""
from pathlib import Path
import re
BASE = Path('com/android/internal/telephony')

def method(text, name, descriptor):
    pat = r'(?m)^\.method [^\n]*\b' + re.escape(name + descriptor) + r'\n.*?^\.end method'
    found = list(re.finditer(pat, text, re.S | re.M))
    if len(found) != 1:
        raise RuntimeError('Expected exactly one method: ' + name + descriptor)
    return found[0]

def patch(root):
    root = Path(root)
    p = root/BASE/'RadioResponse.smali'
    s = p.read_text()
    old = 'responseSignalStrength(Landroid/hardware/radio/V1_0/RadioResponseInfo;Landroid/hardware/radio/V1_4/SignalStrength;)V'
    new = old.replace('Landroid/hardware/radio/V1_4/SignalStrength;', 'Ljava/lang/Object;')
    if s.count(old) != 2: raise RuntimeError('Response helper reference mismatch')
    s = s.replace(old, new)
    for suffix, version in [('', '1_0'), ('_1_2', '1_2')]:
        name = 'getSignalStrengthResponse' + suffix
        desc = f'(Landroid/hardware/radio/V1_0/RadioResponseInfo;Landroid/hardware/radio/V{version}/SignalStrength;)V'
        m = method(s, name, desc)
        if '->responseNotSupported(' not in m.group(): raise RuntimeError('Legacy response is not original stub')
        body = f'''.method public {name}{desc}
    .registers 3
    invoke-direct {{p0, p1, p2}}, Lcom/android/internal/telephony/RadioResponse;->{new}
    return-void
.end method'''
        s = s[:m.start()] + body + s[m.end():]
    p.write_text(s)
    p = root/BASE/'RadioIndication.smali';s=p.read_text()
    desc14 = '(ILandroid/hardware/radio/V1_4/SignalStrength;)V'
    template = method(s, 'currentSignalStrength_1_4', desc14).group()
    for name, version in [('currentSignalStrength','1_0'),('currentSignalStrength_1_2','1_2')]:
        desc = f'(ILandroid/hardware/radio/V{version}/SignalStrength;)V'
        m = method(s,name,desc)
        if 'unsupported on IRadio < 1.4' not in m.group(): raise RuntimeError('Legacy indication is not original stub')
        body = template.replace('currentSignalStrength_1_4'+desc14, name+desc)
        s=s[:m.start()]+body+s[m.end():]
    p.write_text(s)
    p=root/BASE/'RILUtils.smali';s=p.read_text()
    desc='(Ljava/lang/Object;)Landroid/telephony/SignalStrength;'
    m=method(s,'convertHalSignalStrength',desc);body=m.group()
    marker='    instance-of v1, p0, Landroid/hardware/radio/V1_4/SignalStrength;'
    if body.count(marker)!=1 or '.registers 8' not in body:raise RuntimeError('Signal converter mismatch')
    branches=''
    for version in ['1_0','1_2']:
        v=f'Landroid/hardware/radio/V{version}/SignalStrength;'
        label='ginkgo_next_'+version
        branches+=f'''    instance-of v1, p0, {v}
    if-eqz v1, :{label}
    check-cast p0, {v}
    new-instance v0, Landroid/telephony/SignalStrength;
    iget-object v1, p0, {v}->cdma:Landroid/hardware/radio/V1_0/CdmaSignalStrength;
    iget-object v2, p0, {v}->evdo:Landroid/hardware/radio/V1_0/EvdoSignalStrength;
    invoke-static {{v1, v2}}, Lcom/android/internal/telephony/RILUtils;->convertHalCdmaSignalStrength(Landroid/hardware/radio/V1_0/CdmaSignalStrength;Landroid/hardware/radio/V1_0/EvdoSignalStrength;)Landroid/telephony/CellSignalStrengthCdma;
    move-result-object v1
    iget-object v2, p0, {v}->{'gw' if version=='1_0' else 'gsm'}:Landroid/hardware/radio/V1_0/GsmSignalStrength;
    invoke-static {{v2}}, Lcom/android/internal/telephony/RILUtils;->convertHalGsmSignalStrength(Landroid/hardware/radio/V1_0/GsmSignalStrength;)Landroid/telephony/CellSignalStrengthGsm;
    move-result-object v2
'''
        if version=='1_0':
            branches+='''    new-instance v3, Landroid/telephony/CellSignalStrengthWcdma;
    invoke-direct {v3}, Landroid/telephony/CellSignalStrengthWcdma;-><init>()V
'''
        else:
            branches+=f'''    iget-object v3, p0, {v}->wcdma:Landroid/hardware/radio/V1_2/WcdmaSignalStrength;
    invoke-static {{v3}}, Lcom/android/internal/telephony/RILUtils;->convertHalWcdmaSignalStrength(Ljava/lang/Object;)Landroid/telephony/CellSignalStrengthWcdma;
    move-result-object v3
'''
        branches+=f'''    iget-object v4, p0, {v}->tdScdma:Landroid/hardware/radio/V{version}/{'TdScdmaSignalStrength' if version=='1_0' else 'TdscdmaSignalStrength'};
    invoke-static {{v4}}, Lcom/android/internal/telephony/RILUtils;->convertHalTdscdmaSignalStrength(Ljava/lang/Object;)Landroid/telephony/CellSignalStrengthTdscdma;
    move-result-object v4
    iget-object v5, p0, {v}->lte:Landroid/hardware/radio/V1_0/LteSignalStrength;
    invoke-static {{v5}}, Lcom/android/internal/telephony/RILUtils;->convertHalLteSignalStrength(Ljava/lang/Object;)Landroid/telephony/CellSignalStrengthLte;
    move-result-object v5
    new-instance v6, Landroid/telephony/CellSignalStrengthNr;
    invoke-direct {{v6}}, Landroid/telephony/CellSignalStrengthNr;-><init>()V
    invoke-direct/range {{v0 .. v6}}, Landroid/telephony/SignalStrength;-><init>(Landroid/telephony/CellSignalStrengthCdma;Landroid/telephony/CellSignalStrengthGsm;Landroid/telephony/CellSignalStrengthWcdma;Landroid/telephony/CellSignalStrengthTdscdma;Landroid/telephony/CellSignalStrengthLte;Landroid/telephony/CellSignalStrengthNr;)V
    return-object v0
    :{label}
'''
    body=body.replace(marker, branches+marker);s=s[:m.start()]+body+s[m.end():]
    desc='(Ljava/lang/Object;)Landroid/telephony/CellSignalStrengthTdscdma;'
    m=method(s,'convertHalTdscdmaSignalStrength',desc);body=m.group()
    marker='    check-cast p0, Landroid/hardware/radio/V1_2/TdscdmaSignalStrength;'
    if body.count(marker)!=1 or '.registers 5' not in body:raise RuntimeError('TD converter mismatch')
    branch='''    instance-of v1, p0, Landroid/hardware/radio/V1_0/TdScdmaSignalStrength;
    if-eqz v1, :ginkgo_td12
    check-cast p0, Landroid/hardware/radio/V1_0/TdScdmaSignalStrength;
    new-instance v1, Landroid/telephony/CellSignalStrengthTdscdma;
    iget p0, p0, Landroid/hardware/radio/V1_0/TdScdmaSignalStrength;->rscp:I
    const v2, 0x7fffffff
    if-eq p0, v2, :ginkgo_td_rscp
    neg-int p0, p0
    :ginkgo_td_rscp
    invoke-direct {v1, v2, v2, p0}, Landroid/telephony/CellSignalStrengthTdscdma;-><init>(III)V
    return-object v1
    :ginkgo_td12
'''
    body=body.replace(marker,branch+marker);s=s[:m.start()]+body+s[m.end():]
    p.write_text(s)

if __name__=='__main__':
    import sys
    patch(sys.argv[1])
