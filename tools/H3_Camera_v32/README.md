# Persist the working original Camera 6.2 fork

The user reports V31 works after the Pro preview guard. This records a user report, not an exhaustive camera certification. V30 system image plus V31 userdata APK update is the current device state. V32 copies the exact user-tested signed V31 APK into the existing separate system camera slot so future images contain the same code.

V31 SHA256: 815f14e8419f55f23dfa58e796c7462c813a941417455e1d3e17cf7d2eba1186. V30 slot SHA256: 76cff12c13114e17d2ac9c33622e3f7476a186d3b9df78e768bc3b28dc0ecdd0.

prepare.py mounts work volume at /linux read-write, all host out at /reference read-only and host out/camera-v32 at /out. It verifies V30's 44 files, original donor camera and policy, and proves that all non-signature APK entries except classes2.dex are unchanged between V29/V30 and V31. All 42 bundled libraries must match the new APK. It backs up the old APK and metadata outside the build tree, rewrites the existing inode, verifies ownership/mode/all xattrs, and restores old content on final verification failure. Unexpected integrity/capability attributes cause refusal. No existing output/backup is overwritten.

Package identity, test label, hidden API allowlist, original donor camera, native libraries, permissions policy, vendor and boot remain unchanged. In particular, this does NOT yet replace com.android.camera or remove the test suffix; final app identity/default-handler integration and clean-install behavior remain separate work. Existing original donor camera is intentionally retained for recovery/comparison.

package.py retains the complete V30/V25 baseline checks and verifies V32's installed APK before EROFS build/fsck and 8 GiB padding. Use /linux read-only, host out at /reference read-only, out/images at /result. Output hyperos3-ginkgo-v32-padded.img. No device flashing.

Local validation: Python compilation and temporary filesystem fixtures for APK sync, backup, inode/user-xattr retention and injected-failure rollback. Actual source APK exists on the user's Mac; real-volume and packaging validation run there. Fresh image boot/clean install are not claimed. The ROM remains experimental; first-minute load and signal reporting delays are deferred by user choice.
