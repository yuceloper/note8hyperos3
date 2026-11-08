Offline boot + fstab crypto alignment candidate, not boot tested.
Use after H3_Boot_Prep_v1. Removes only +wrappedkey_v0 and :wrappedkey_v0 from /data fstab flags, matching the running device configuration supplied by user. Keeps FBE v2, metadata encryption and inlinecrypt. Other entries including metadata mount unchanged.
The same resulting fstab is embedded in boot ramdisk and installed to the HyperOS3 system tree. Kernel, DTB and cmdline are byte-identical to Boot_Prep_v1. Original unlocked-device/AVB limitations from v1 remain.
Existing encrypted data keys and Android17-to-16 app/framework database compatibility are NOT verified. No formatting, flashing, vendor image modification or recovery action is performed.
Installer validates previous and candidate hashes and one-line-only delta before writing. Backs up previous fstab under /linux/backups/hyperos3-crypto-v2; preserves ownership, mode, xattrs and timestamps.
Use the v2 boot candidate together with the updated tree, not the v1 boot. Do not flash until image packaging and final preflight are complete. Full VINTF/APEX/deprecation tests remain unverified.
