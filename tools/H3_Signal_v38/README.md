# V38: legacy HIDL signal response compatibility (review candidate)

Baseline: system V35 + vendor V26. Calls and mobile data work while bars disappear.
No vendor, modem, policy, UI, radio proxy, SignalStrengthController, or polling changes.
No synthetic levels, cached-level workaround, or blanket suppression of radio errors.

## Evidence

The V37 capture contains a valid LTE notification at 11:56:36.108 (RSRP -86,
level 4), a rejected SIGNAL_STRENGTH response at 11:56:36.914, and an all-invalid
notification at 11:56:37.241. Registration remains IN_SERVICE.

Important distinction: the `not supported on IRadio < 1.4` message originates
from **RadioResponse.responseNotSupported**, not the request-version guard.
The original getSignalStrengthResponse and getSignalStrengthResponse_1_2
callbacks call that helper, which overwrites RadioResponseInfo.error with 6.
SignalStrengthController then handles that error by publishing a default
SignalStrength. The old currentSignalStrength and currentSignalStrength_1_2
indications are also logging-only stubs. Their original payloads are discarded.

The capture does not distinguish which legacy callback version delivered that
response; both legacy versions are restored. The failure does not prove the
whole modem supports only HAL <1.4. The request path already issues a modern
request; its existing version checks and proxy are deliberately preserved.

## Change

Three classes, eight methods:

- RadioResponse: process 1.0/1.2 response payloads through the normal response
  lifecycle; widen the existing private helper's payload parameter to Object.
  The 1.4 caller is updated to that same helper; its behavior is unchanged.
- RadioIndication: use the existing 1.4 processing pattern for 1.0/1.2 callbacks,
  including processIndication and registrant notification.
- RILUtils: restore 1.0/1.2 signal conversion and 1.0 TD-SCDMA conversion.
  Existing GSM/CDMA/LTE conversion helpers remain unchanged. Absent NR is a
  default unavailable CellSignalStrengthNr, not fabricated 5G.

Mapping reference: Android Open Source Project, Android 13 RILUtils:
https://android.googlesource.com/platform/frameworks/opt/telephony/+/refs/heads/android13-release/src/java/com/android/internal/telephony/RILUtils.java

## Build review only (Mac)

The input is the previously pulled live system JAR. The builder accepts only
SHA256 f3c66613c8433783c1b6b8608b7e89721b7a3d9d127ad7e92bf0817f80c7b258.
It does not modify the original file or the Linux work volume.

```bash
bash <<'SH'
set -euo pipefail
cd "$HOME/note8hyperos3"
git fetch origin experiment/signal-v38-legacy-response
git restore --source=FETCH_HEAD --worktree -- tools/H3_Signal_v38
mkdir -p out/signal-v38
docker run --rm \
  -v "$PWD/tools/H3_Signal_v38:/package:ro" \
  -v "$PWD/out/signal-v38-reference:/source:ro" \
  -v "$PWD/out/signal-v38:/out" \
  ginkgo-camera-apk-tools:v27 \
  python3 /package/build.py \
    --source /source/telephony-common.jar --out /out/review-v1 </dev/null
cat out/signal-v38/review-v1/validation.json
SH
```

Output: out/signal-v38/review-v1/telephony-common-v38.jar and validation.json.
The output directory must not already exist. A failed build is never reused.
Smali/baksmali must be available in /usr/share/java (existing camera tools image).

## Verification and limits

Framework DEX hidden-API restrictions include newer flags not understood by
smali 2.5.2. The builder temporarily removes the map entry only from an analysis
copy, disassembles/reassembles, checks declaration order/access flags, then
restores the **entire original hidden-API section byte for byte** into the
candidate with a new valid map, sizes, SHA1 and Adler32. No hidden-API flags are
converted, cleared, or granted. Class/member order is checked before restoring.

A second disassembly verifies the exact eight-method allowlist across all 3,367
classes. All other methods and declarations must be equivalent (implicit zero
static initializers and regenerated labels are normalized). Every non-DEX JAR
entry is byte-identical to the input. Original source and output hashes are
recorded. No runtime test has occurred; assembly and these comparisons do not
substitute for ART verification on the phone.

Next step after reviewing the successful build: back up the exact offline V35
JAR and its preoptimization files, prepare an isolated system image with the
candidate, preserve metadata, and retain a working V35 rollback image. Do not
push the JAR onto a running system or install it as an APK. No install/flash
script is included in this review step.

Runtime acceptance: repeated boots and PIN unlock; signal remains a live
measurement for several minutes and changes with reception; calls/data remain
working; airplane mode and SIM/radio-off must clear service and bars; confirm
no verifier errors, phone crashes/ANRs, or forced REQUEST_NOT_SUPPORTED from
the legacy signal callbacks. The modern callbacks and real modem-error paths
must continue to work. Raw captures and JARs stay local, never in git.
