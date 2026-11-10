# Read-only boot-image investigation

User confirmed offline V35 restoration (original JAR, eleven preopt files and
four aliases) and produced V40 review JAR SHA256
1279a5eb44e5a0ff6ca32943af7b7b31f793c668adff9c1849ff146c3f9fe5a0.
Do not install it yet: arm boot-image compilation abort remains unresolved.

collect_art_baseline.py requires a ginkgo phone with the original V35 JAR.
It records selected runtime/ABI properties, boot classpaths, arm/arm64 ART
and system boot-image file listings, compiler tool metadata, phone PID,
crash buffer and ART-related log lines. It pulls core-oj.jar/core-libart.jar
into a host temporary directory solely to inventory DEX presence and hashes;
binary contents are not included in the archive. Reads are timeout-bounded,
permission errors are recorded, unrelated main-buffer log lines are dropped.

No device push, shell write, compilation, settings change, cache clearing,
reboot or flash. Output is logs/signal-v40-art-baseline-TIMESTAMP.tar.gz.

Run from the Mac repository:

```
python3 tools/H3_Signal_v40/collect_art_baseline.py --reveal </dev/null
```

Fixtures verified archive creation with readable/denied core JAR pulls,
exclusion of unrelated main-buffer lines and binaries, and early rejection
of a wrong device/baseline without an output artifact. Real device capture
is still required. The script does not execute or test V40 conversion code.

Purpose: determine whether missing/invalid boot images or unavailable DEX
fallback in core JARs explains the arm InitWithoutImage abort, distinguish
it from the fixed legacy field reference, and avoid another speculative
system flash. Presence/absence of a file alone is not proof of the cause.
