# Installed Gallery V36 reference findings

Reference: gallery-v36-reference-20261109-202548.zip. Installed APK /product/priv-app/MIUIGalleryGlobal/MIUIGalleryGlobal.apk, SHA256 7644d5053289a364bef85b8f149e874739392dba46d2b340e6cd31c6a320f1d2. Static analysis only; reference contains code/resources and package dumps, not user photos.

## Confirmed service behavior

Manifest permission com.miui.gallery.permission.BIND_SERVICE is signature-only (0x2). GalleryBackgroundService is exported and requires that permission. Its onBind returns a Messenger binder, starts a PreloadJob for the latest media, and may bind the camera AIDL background service on quick-snap devices. Its MessengerHandler accepts message what=0, constructs CameraPreviewParams from the Bundle and stores it in CameraPreviewManager. No additional caller-package/certificate validation was found in the inspected onBind or MessengerHandler methods. Removing the manifest permission would expose this entry point and is not an appropriate fix.

PreloadJob respects Gallery CTA/storage permission before loading the latest media. The thumbnail payload includes URI, a ParcelFileDescriptor and dimensions. CameraPreviewFactory can build a bitmap from that shared buffer. Its handles predicate requires both camera-preview mode and existing CameraPreviewParams; without params this factory does not handle the image. Its open method has a bounded wait. This is an acceleration path; do not infer a missing normal image viewer from the bind denial.

Among all four DEX files, the sole discovered call constructing CameraPreviewParams from a Bundle and submitting it to CameraPreviewManager is the protected service's MessengerHandler. No equivalent public intent intake was found in this scan. Ordinary camera REVIEW intents are constructed separately on the Camera side, targeting com.miui.gallery.

## Integration limit and next runtime acceptance

Camera uses a new local signer while Gallery retains its donor signer. A privapp-permissions entry does not convert this pure signature permission into a grantable privileged permission. No original OEM private signing key is available in this workflow. Restoring this protected optimization would require an explicitly designed trust/integration change; it is not accomplished by suppressing a log or bypassing a bind exception.

Keep the donor Gallery, signature permission and user data unchanged. First verify ordinary behavior: new still capture opens through the camera thumbnail, zoom/review works, recorded video plays with sound, return-to-camera works, and lock-screen review does not expose older media before authentication. If these pass, record shared-buffer/preload acceleration as an unsupported integration rather than a broken gallery. If a test fails, collect that precise transition and investigate its actual error before building another APK.

No V36 APK or ROM image was built. No Gallery manifest, signing identity, permissions, service code or phone state was changed by this investigation. Custom LUT compatibility and immediate-postboot camera launch delay remain open separately.
