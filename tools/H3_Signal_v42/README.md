# V42 — isolated conversion probe before another signal image

V41 is the current working packaging baseline: the arm64 boot.vdex EUCLEAN
was no longer observed, SIM loaded, calls/data work, and bars remain empty.
V41 intentionally retains original V35 telephony code. No V40 installation yet.

The probe extracts two actual methods from exact V39 and V40 JARs:
convertHalSignalStrength(Object) and convertHalTdscdmaSignalStrength(Object).
Their instruction bodies are copied into separately named diagnostic classes.
Only calls to the copied TD helper are redirected to that diagnostic owner;
other unchanged public helpers resolve from the running V35/V41 RILUtils.
No full RILUtils class, system JAR, phone APK or modem is replaced.

The test builds synthetic old-HIDL payload objects in an app_process64 child:
1. The V39 converter must raise NoSuchFieldError mentioning tdScdma. This is
   caught inside the test process; it must not terminate the phone service.
2. V40 HAL 1.2 conversion must return LTE RSRP -86 and TD-SCDMA RSCP -70.
3. V40 HAL 1.0 conversion must return LTE RSRP -93 and TD-SCDMA RSCP -75.
4. Only successful measurement assertions print PROBE_ALL_OK.

The builder requires exact known V39/V40 hashes, strips hidden-API metadata
only from temporary disassembly copies, assembles the diagnostic classes into
a new standalone DEX without that metadata, then disassembles them again to
compare copied converter methods. Original/candidate JARs stay read-only.
Probe bytes are diagnostic only; do not install them as system components.

## Build and run from Mac

```bash
bash <<'SH'
set -euo pipefail
cd "$HOME/note8hyperos3"
git fetch origin investigate/signal-v42-runtime-probe
git restore --source=FETCH_HEAD --worktree -- tools/H3_Signal_v38 tools/H3_Signal_v42
mkdir -p out/signal-v42
docker run --rm --entrypoint python3 \
  -v "$PWD/tools:/tools:ro" \
  -v "$PWD/out:/reference:ro" \
  -v "$PWD/out/signal-v42:/result" \
  ginkgo-camera-apk-tools:v27 \
  /tools/H3_Signal_v42/build_probe.py \
    --v39 /reference/signal-v39/review-v1/telephony-common-v39.jar \
    --v40 /reference/signal-v40/review-v1/telephony-common-v40.jar \
    --out /result/probe-v1 </dev/null
python3 tools/H3_Signal_v42/run_probe.py --reveal </dev/null
SH
```

The runner verifies ginkgo and original telephony JAR hash plus running phone
PID. It creates a unique /data/local/tmp/ginkgo-signal-probe-* directory, pushes
only the probe JAR, makes it read-only (0444), and runs its standalone Main
in an app_process64 process. It does not install an APK, modify settings,
replace system files, reboot, clear caches or change modem configuration.
Output is retained in that temporary directory; host logs and a tar.gz are
under logs/ginkgo-signal-probe-*. The runner returns success only with all four
markers, exit code zero, and an unchanged com.android.phone PID.

A timeout, hidden-API/access restriction, unavailable CLI environment or any
unexpected error is REVIEW_REQUIRED, not proof the production candidate is
bad. Do not broaden permissions or disable system restrictions on failure.

## Validation and limits

Local smali assembly and copied-method roundtrip comparison passed. Runner
fixtures cover success, missing assertion marker, runtime error and changed
phone PID; only full success is accepted. Real device execution is pending.

This tests actual conversion instruction bodies against the running framework
with synthetic data. It does not test real modem callbacks, service registration,
whole bootclasspath replacement, restart timing, UI bars or long-term stability.
A passed probe is a gate for evaluating the next V41-packed signal image,
not a declaration that the ROM or signal fix is complete.
