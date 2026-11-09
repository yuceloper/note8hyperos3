# V35 startup write-probe candidate

The Chinese toast is resource 0x7f140ac9. ActivityBase$c handles message 13 by displaying it. Lz/B.run(), branch at byte 66, checks whether the package certificate list contains 7B6DC7079C34739CE81159719FB5EB61D2A03225. For a different certificate it tries writing literal `test` to `Test.txt` under `/mnt/vendor/persist/camera/` or `/data/vendor/camera/` depending on the camera capability version. On failure it logs MIVILutSaver and sends message 13. The user's live log confirms this failure.

Real LUT producer and consumer paths also exist in Z4/b.b, Z4/d construction, a5/d construction and e3/A.l8. These paths are left unchanged. Redirecting only the probe or all paths to application-private storage would not prove native/HAL access or LUT compatibility.

This candidate changes exactly one four-byte instruction in classes.dex: the case entry at 66 becomes goto/16 to its own return at 218. This omits the startup write probe, including its certificate branch and test-file creation. It does not alter general certificate checking, Android permission enforcement, the shared toast handler or actual LUT processing. All other payload entries remain identical to the hash-pinned V34 APK; DEX header digests are recomputed. The local V29 key must be retained and is never uploaded.

This is removal of an inapplicable startup diagnostic, NOT a fix for real LUT permissions. Imported/custom LUTs remain unverified. The separate GalleryBackgroundService denial requires com.miui.gallery.permission.BIND_SERVICE, a signature-only permission, and remains unresolved. No SELinux access is broadened and no permission protection level is weakened.

Validation: original donor classes.dex hash/layout and body hash checked; patch applied to real uploaded donor DEX; checksum and SHA1 checked; modified DEX reparsed and goto target verified as the existing return; repeated patch refused. The user must build/sign with local V34 APK and key, then test runtime. No app installation, image staging or flash is done by build.py.
