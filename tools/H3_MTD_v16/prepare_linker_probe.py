"""Build an isolated RUNPATH probe. Does not install or execute MTD."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

source = Path('/reference/mtd-reference/dependency-reference-v1')
out = Path('/result/runpath-v1')
patcher = shutil.which('patchelf')
if not patcher:
    raise RuntimeError('patchelf bulunamadi; hicbir aday olusturulmadi')
if out.exists():
    raise RuntimeError('Aday dizini zaten var; uzerine yazilmadi')
manifest = json.loads((source / 'manifest.json').read_text())
selected = []
names = set()
for item in manifest['files']:
    path = source / 'files' / item['file']
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != item['sha256']:
        raise RuntimeError('Kaynak hash uyusmazligi: ' + item['file'])
    if 'needed' not in item:
        continue
    if data[:6] != b'\x7fELF\x02\x01':
        raise RuntimeError('ELF64 LE bekleniyordu')
    is_main = item['file'] == 'odm/bin/mtd@1.3'
    target = Path('bin/ginkgo-mtd@1.3') if is_main else Path('lib64/ginkgo-mtd-v16') / path.name
    if str(target) in names:
        raise RuntimeError('Cakisan dosya: ' + str(target))
    names.add(str(target))
    selected.append((item, path, target, is_main))
if len(selected) != 59 or sum(row[3] for row in selected) != 1:
    raise RuntimeError('Beklenen 59 ELF bulunamadi')
if next(row[0]['sha256'] for row in selected if row[3]) != '23acbea8ee9efcc5f1e57bd8500b8a4d3d54331b87a799c38305a54800ce1793':
    raise RuntimeError('MTD kaynak surumu uyusmuyor')
out.mkdir()
records = []
for item, path, relative, is_main in selected:
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)
    target.chmod(0o755 if is_main else 0o644)
    runpath = '$ORIGIN/../lib64/ginkgo-mtd-v16' if is_main else '$ORIGIN'
    subprocess.run([patcher, '--set-rpath', runpath, str(target)], check=True, stdin=subprocess.DEVNULL)
    actual_path = subprocess.check_output([patcher, '--print-rpath', str(target)], text=True).strip()
    needed = subprocess.check_output([patcher, '--print-needed', str(target)], text=True).splitlines()
    if actual_path != runpath or sorted(needed) != sorted(item['needed']):
        raise RuntimeError('ELF bagimlilik/RUNPATH kontrolu basarisiz: ' + str(relative))
    records.append({'file': str(relative), 'source': item['file'], 'source_sha256': item['sha256'], 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'runpath': runpath, 'needed': needed})
(out / 'validation.json').write_text(json.dumps({'status': 'LINKER_PROBE_ONLY_NOT_INSTALLED', 'files': records}, indent=2) + '\n')
print('V16 RUNPATH TEST ADAYI HAZIR: 59 ELF')
print('SERVIS BASLATILMADI. CALISMA AGACI VE TELEFON DEGISTIRILMEDI.')
