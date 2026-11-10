# Android DEX verifier comparison — 2026-11-11

User ran the phone's /apex/com.android.art/bin/dexdump -c on raw DEX files
under /data/local/tmp/signal-v39-art-20261111-011512 while V35 was running.

| Artifact | DEX bytes | Exit code | Result |
| --- | ---: | ---: | --- |
| Original V35 | 5094848 | 0 | Checksum verified |
| Failed V38 | 5211112 | 1 | Non-zero padding 11 before section of type 61440 at offset 0x4eace0 |
| Repaired V39 | 5210904 | 0 | Checksum verified |

The rejection matches the independently identified orphan-map offset and
hidden-API section type (0xf000). V39 JAR SHA256:
452faaae8d36ac59f4f6b7830ea4fd126b878678f377e79e8184568f40a33300.

This confirms Android DEX file-format/checksum acceptance, not complete
bootclasspath compatibility, method execution, or functional signal behavior.
Next: compare original and V39 in a temporary dex2oat verify compilation with
separate output files. Interpret failures using the original-file control;
compiler environment/SELinux failure is not a candidate verification failure.
No system replacement, property changes, reboot or flash in this step.
