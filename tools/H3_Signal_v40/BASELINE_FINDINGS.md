# V35 ART baseline findings — 2026-11-11

Archive: signal-v40-art-baseline-20261111-020337-069831.tar.gz.
Original telephony-common.jar hash verified; boot completed; phone PID 3421
at uptime 492s. Crash buffer output was empty at capture.

- zygote64_32 and both 32/64-bit ABIs are configured.
- Boot artifacts exist under /system/framework/arm and arm64, including
  primary boot.art/boot.oat and boot-telephony-common.*. No artifacts were
  found at the queried /apex/com.android.art/javalib/arm{,64} paths; that alone
  is not evidence of missing boot images because the system paths are populated.
- core-oj.jar (5924944 bytes) contains classes.dex (5903264 bytes), DEX039.
- core-libart.jar (626577 bytes) contains classes.dex (626292 bytes), DEX039.
  The hypothesis that these two core JARs contain no DEX fallback is not supported.
- The live system listing reports exactly one Structure needs cleaning error:
  /system/framework/arm64/boot.vdex. This is a filesystem read/metadata symptom,
  not a proven hardware failure or proof of the earlier arm dex2oat abort cause.
- V35 main log includes repeated dex2oat SELinux denials reading
  vendor_default_prop. They also occur on the working baseline; do not grant
  broad access or assume they explain the V39 failure.
- One app-image checksum mismatch is logged for a Qualcomm app after reverting
  the system. It is not evidence of a new global boot-image defect by itself.

Next: compare exact root/arm/arm64 boot.vdex files and symlink metadata between
the read-only offline tree and live V35. The previous V39 InitWithoutImage abort
was instruction-set arm, whereas this listing error is arm64; do not conflate
them without further evidence. Keep V40 uninstalled until read-path behavior
is understood. Raw logs/binaries remain outside git.
