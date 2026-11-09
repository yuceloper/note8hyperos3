# Original HyperOS Camera 6.2 diagnostic

This returns to the actual creek HyperOS Camera APK version 6.2.001130.0, not ANX. Source SHA256: 48a12d13da98f2e683b185476b9a5516251bcef80fe19aec0ecfde22876d51c5.

build_original_test.py creates a separately signed com.ginkgo.micamera6test fork. The binary manifest changes installed identity, provider authorities, custom permission names, native extraction and label. Java class names stay original. Boot broadcast actions and original-package marker are removed. One provider authority is originally a resource reference; it is replaced with a unique literal in the test manifest. No resource table rewrite is done.

The only DEX change is Lg6/c;->B()Z in classes3.dex: return false for the unsupported-device error decision. Exact original APK, DEX and method-body hashes/layout are required. DEX signature/checksum are recomputed. Other DEX entries, resources, assets and all 42 original arm64 libraries are preserved byte-for-byte. The app still uses its generic fallback profile; this does not add real ginkgo support and does not force the MediaTek creek profile. No claim of camera capture compatibility.

Verified locally against the uploaded original APK: source manifest structural parsing, 13 unique isolated provider authorities, exact method match, patch scope and DEX integrity fields, Python compilation. Full signed APK build/device test pending on the user's Docker tools image.

Use the existing ginkgo-camera-apk-tools:v27 image with --entrypoint python3 and mount this tools directory at /package. The source is read-only, preferably the original donor APK in note8-hyperos3-work. Output must be a new directory.

V28 was an ANX-only diagnostic and must not be flashed for this path. The offline tree currently has V28 ANX additions; remove/rollback only those verified additions before preparing any original-camera system test image. The original com.android.camera and Aperture remain the working comparison/recovery apps. This stage does not edit the tree, apply hidden API policy or install the test APK. Package-name literals may still affect the diagnostic fork; system-app setup remains pending.
