# V30 original Camera 6.2 system diagnostic

The ORIGINAL Camera 6.2 fork com.ginkgo.micamera6test crashed as a user app during reflected ResourcesManager.getOrCreateActivityResourcesStructLocked(IBinder). The uploaded donor framework contains that exact method in classes.dex. No framework API deletion/patch is justified by this crash. Stage it as a non-privileged system app with a package-specific hidden API allowlist, then retest; success remains unverified.

Input APK: out/camera-v29/original-test-v1/MiuiCamera-6.2-ginkgo-test.apk, SHA256 76cff12c13114e17d2ac9c33622e3f7476a186d3b9df78e768bc3b28dc0ecdd0. This is the V29 original Camera 6.2 model-gate diagnostic, not ANX. It is not fully adapted; generic profile/package-literal limitations remain.

prepare.py expects named work volume at /linux (read-write), host out/camera-v29 at /reference (read-only), out/camera-v28 at /legacy (read-only), and out/camera-v30 at /out. It verifies original APK and policy baselines and, if present, all 64 V28 ANX added files. ANX app/sysconfig are moved to /linux/backups/hyperos3-camera-v30-stage/previous-anx-* without deletion. New app is product/app/GinkgoMiCamera6Test/MiuiCamera.apk plus 42 bundled arm64 libraries. Product sysconfig allows hidden APIs only for com.ginkgo.micamera6test. No global policy, privileged permission, SELinux, original camera, vendor or boot edit.

The new files inherit product labels and root:root 0755 directories/0644 files. Final verification failure restores both new additions and previous ANX state. An interrupted process may leave staging; inspect rather than overwrite.

package.py retains V25 base packaging checks, verifies all 44 new files, absence of V28 additions, unchanged original camera/policy, scoped sysconfig, EROFS fsck, and 8 GiB padding. Mount all host out at /reference read-only, work volume at /linux read-only, and out/images at /result. Produces hyperos3-ginkgo-v30-padded.img. No flash.

Validation performed: Python compilation and temporary-filesystem migration/backup/rollback fixtures with inode-based emulated SELinux labels. Actual Linux-volume metadata, EROFS build, hidden API behavior and camera capture require user-side checks. Existing V26 vendor/boot unchanged. Do not flash V28 ANX image for this path.
