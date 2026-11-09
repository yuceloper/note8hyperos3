# V34 original camera identity — build only

The lock-screen trace explicitly launches `com.android.camera/.Camera`. The working V31/V33 fork uses `com.ginkgo.micamera6test`, so default intent selection cannot redirect that explicit component.

This builder starts from the hash-pinned original donor Camera 6.2 APK and copies only classes2.dex and classes3.dex from the hash-pinned, runtime-tested V31 fork. The original manifest, package, component names, providers, permissions, localized labels, resources and 42 native libraries remain byte-identical. The existing local diagnostic key signs the candidate; this is NOT the donor certificate. No private key belongs in git.

The builder checks all other working APK entries against the donor and rejects unrelated differences. It verifies the signed output payload and signer, refuses a shared UID manifest, and writes validation.json. Output must be new. No tree installation, package-state editing, permission change, uninstall, reboot or flash is performed. Do not install this APK with adb install over the differently signed original.

## Pending integration

System-image staging must back up the original APK and metadata, preserve permissions and labels, explicitly arrange native libraries and scoped hidden-API access, and retain the working clone. Existing system-app signature migration must be tested on this donor package manager. AOSP ReconcilePackageUtils includes a system-directory certificate-change path with data retention; that is not proof of HyperOS behavior. Signature-protected permissions and integrations may differ after resigning.

Runtime acceptance includes normal capture, Pro, front/rear camera, video/audio, external IMAGE_CAPTURE, gallery/provider behavior, lock-screen launch and ensuring pre-existing photos remain protected while locked. Only after these pass should the clone or other camera defaults be cleaned up.

## Validation performed

Python syntax check and synthetic ZIP fixtures: original manifest retention, both DEX transfers, 42 native files, signature-entry removal and rejection of unrelated resource changes. Actual signing/build requires the user's pinned V31 APK and private local key. No new phone test has been performed.
