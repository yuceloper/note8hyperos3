# V39 device test FAILED — 2026-11-11

Do not use V39 as a working system. System image
SHA256 d8133f8dd1e97bc2fc12c61014d6e3aee56e1f1daeffe608fdbb856f8839aed0
boots but com.android.phone repeatedly crashes during getSignalStrengthResponse_1_2.
The installed JAR hash is the expected
452faaae8d36ac59f4f6b7830ea4fd126b878678f377e79e8184568f40a33300.

Exact error: NoSuchFieldError for SignalStrength V1_2.tdScdma with type
Landroid/hardware/radio/V1_2/TdscdmaSignalStrength; in RILUtils conversion.
The uploaded device framework.jar classes2.dex proves the actual declaration
is V1_2.SignalStrength.tdScdma:Landroid/hardware/radio/V1_0/TdScdmaSignalStrength;.
The name is correct; the field TYPE is wrong. The original V38 patch generator
incorrectly derived this member type from the containing HAL struct version.

This is separate from the V38 DEX layout bug, which V39 fixed. The legacy
1.2 response callback is now actually reached, proving which callback the
vendor uses, but it cannot complete with this incorrect field reference.
DEX format validation and temporary verify compilation did not catch this
runtime reference-resolution error and are insufficient acceptance gates.

The crash buffer also contains dex2oat64 SIGABRT during arm boot compilation
in ClassLinker InitWithoutImage. That boot dependency issue remains unresolved;
do not claim the field fix will resolve it or the user-reported early reboot.

Recovery: known working V35 system image
2a6ef7d44e92d7e337cadadda56d30574e218e980d2b3d1346bc2564e5a648f5.
Keep vendor V26/userdata intact. The offline tree still contains V39 until
explicitly restored. Audit all introduced HAL field references against actual
framework definitions before creating any next candidate; preserve the fixed
DEX layout/version and hidden-API restrictions.
