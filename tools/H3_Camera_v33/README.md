# Original camera name and secure-handler diagnostic

The user's resolver checks show normal camera resolves to AssistantCamera when package-restricted and IMAGE_CAPTURE to OneShotImageCapture. Secure camera still resolves to ResolverActivity inside the same package. Inspection of the original Camera 6.2 manifest confirms two secure STILL_IMAGE_CAMERA_SECURE activity handlers: Camera and AssistantCamera. V33 retains only Camera for that action; normal AssistantCamera action and capture handlers are preserved.

This changes only the compiled manifest of the working V31 signed APK (SHA256 815f14e8419f55f23dfa58e796c7462c813a941417455e1d3e17cf7d2eba1186). Application label is restored to original localized resource ID 2132018043. Package identity stays com.ginkgo.micamera6test to preserve tested state/signing. All DEX (including model gate and Pro guard), resources, icon assets and native libraries remain byte-identical. Sign with the existing V29 diagnostic key; same certificate is verified.

This does NOT set global preferred handlers, change SystemUI configuration, remove/disable com.android.camera or Aperture, or modify the offline tree. Multiple camera apps may still cause the generic resolver. Actual locked camera behavior, including gallery/unlock boundaries, must be checked before default-handler cleanup. No assertion that a manifest-only change fully integrates all HyperOS explicit package references.

Mount host out read-only at /reference, this tools directory at /package and host out/camera-v33 at /out. Use existing ginkgo-camera-apk-tools:v27 with --entrypoint python3. Run build_named_camera.py --reference /reference --out /out/named-v1. It refuses existing outputs. Install built APK as a same-signer update only after build verification.

Local validation: actual original Camera 6.2 binary manifest transformed through V29 test identity then V33. Verified restored label resource, one secure handler, unchanged normal handler, balanced XML and duplicate-patch refusal; Python syntax checks passed. Full signed APK build/runtime remains user-side.
