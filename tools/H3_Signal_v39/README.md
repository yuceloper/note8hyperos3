# V39 DEX layout investigation — not ready to install

V35 phone recovery was user-confirmed. Offline V35 tree recovery must also be
confirmed before further image work. V38 remains a failed device test.

## Confirmed binary defect

Exact inputs:
- Original telephony-common.jar:
  f3c66613c8433783c1b6b8608b7e89721b7a3d9d127ad7e92bf0817f80c7b258
- Failed phone-tested V38 JAR:
  f7249325117c9777652d374f2431e3a2589f0c06c13aadbad1c867ec2cf31d0f

Both SettingsObserver and cat.CatLog class definitions exist in both JARs;
their absence from the runtime was not evidence that they had been removed.

The V38 DEX class_data section ends at 0x4eace0 (5156064). Its next mapped
section, hidden-API data, begins at 0x4eadb0 (5156272). The 208-byte gap contains
the assembler's original 17-entry map table, starting with nonzero byte 0x11.
V38's hidden-API restoration appended a new map without removing this old map.
It left nonzero data where ART expects section padding to be zero.

AOSP Android 16 DexFileVerifier::CheckIntraSection calls CheckPadding between
sections; CheckPadding rejects nonzero bytes for DEX versions below 041:
https://android.googlesource.com/platform/art/+/refs/heads/android16-release/libdexfile/dex/dex_file_verifier.cc

A separate format regression is also present: the original header is DEX 039,
but smali generated DEX 035. This repair restores the original 039 version;
do not attribute the entire device failure to that version change alone.

## Scope

prepare.py accepts only these exact two JAR hashes. It proves the gap equals
the obsolete map table, removes that gap, relocates unchanged hidden-API data
and the current map, restores the original version, updates sizes/checksums,
and compares all class/member declarations and order. Every byte between the
DEX header and the end of class_data is unchanged from failed V38, so this
step does not alter the eight-method signal patch or any other method code.
The original hidden-API section remains byte-identical with SHA256
15f53cbeee10955b9dded772f7a62e587339f0da094dd7f560e03ddc21303be2.

Regression checks on actual artifacts: original padding accepted; known V38
padding rejected; repaired padding accepted; original DEX version retained;
both reported missing class definitions remain; declarations/member order
and checksums match; code/data bytes before the removed table unchanged.

These checks are not full ART verification and do not prove the signal fix.
Next gate: use Android's own DEX verifier/compiler on both failed V38 and V39,
without replacing system files, rebooting, or flashing. Also assess boot image
dependency invalidation separately before preparing another system image.
No installation or packaging script is provided for V39.

## Prepare on Mac

```bash
bash <<'SH'
set -euo pipefail
cd "$HOME/note8hyperos3"
git fetch origin investigate/signal-v39-dex-layout
git restore --source=FETCH_HEAD --worktree -- tools/H3_Signal_v38 tools/H3_Signal_v39
mkdir -p out/signal-v39
docker run --rm --entrypoint python3 \
  -v "$PWD/tools:/tools:ro" \
  -v "$PWD/out/signal-v38-reference:/source:ro" \
  -v "$PWD/out/signal-v38/review-v1:/failed:ro" \
  -v "$PWD/out/signal-v39:/out" \
  ginkgo-port-tools:erofs \
  /tools/H3_Signal_v39/prepare.py \
    --source /source/telephony-common.jar \
    --failed /failed/telephony-common-v38.jar \
    --out /out/review-v1 </dev/null
SH
```

No work-volume mount and no device access. Original and failed artifacts are
read-only. Output: telephony-common-v39.jar and validation.json. Do not run the
V38 installer on V39; it pins the failed V38 hash and must reject this artifact.
