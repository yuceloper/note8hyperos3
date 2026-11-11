# V43: V40 signal conversion with V41 EROFS packaging

User-reported V42 context-v2 result on 2026-11-11: ISOLATED_CONVERSION_PASSED, phone PID unchanged. Probe SHA256 cb3b052721de708c314e92957242d4690a669875bce2080491c1f43f7b3415ff; archive ginkgo-signal-probe-20261111-093349-552140.tar.gz. V39 tdScdma field-error negative control passed; V40 synthetic HAL1.2 LTE=-86/TD=-70 and HAL1.0 LTE=-93/TD=-75 passed. Raw archive has not been reviewed here. This proves isolated conversion only, not complete radio callbacks or boot stability.

The candidate JAR is exactly V40 (1279a5eb44e5a0ff6ca32943af7b7b31f793c668adff9c1849ff146c3f9fe5a0). Install requires the V42 successful runtime report and original V35/V41 offline telephony baseline. It retains JAR metadata and backs up 11 regular preopt files plus four aliases on the same Linux volume. Never flash from these scripts.

package.py retains baseline camera, MTD, policy and init checks and uses the V41 patched EROFS builder, noinline_data, all-symlink audit and fsck extraction. Use ginkgo-port-tools:erofs-v41-symlink. No vendor, policy or modem changes. V41 image remains the device rollback baseline.

Local checks: Python compilation; successful fixture install/backup; injected post-JAR-write failure restored original bytes and all 15 preopt objects with original inode/metadata. Container SELinux xattrs and full image packaging require the user's Linux volume. Full device boot, SIM PIN, real LTE signal update, calls and mobile data remain untested for V43.

restore.py restores the offline original tree from /linux/backups/hyperos3-signal-v43 and /out/stage-v1/validation.json, where /out is host out/signal-v43. It does not restore or flash the phone.
