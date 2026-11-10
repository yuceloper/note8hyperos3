# boot.vdex live/offline comparison — 2026-11-11

The original offline V35 tree has two regular symlinks:
- system/framework/arm/boot.vdex -> ../boot.vdex
- system/framework/arm64/boot.vdex -> ../boot.vdex

Both offline aliases and their common target read successfully, with SHA256
3a265e2317b907d253c1e17c5f9bdc92beb3b9c4231efc2eba48d5806ec27b82.
The target is 111604 bytes.

On the live V35 phone, common target and arm alias read successfully with
that same hash. arm64/boot.vdex returns Structure needs cleaning for both
listing and hash read; readlink does not return a target for that alias.

Therefore the common target's contents agree, and the observed asymmetry is
specific to the live arm64 alias/read path. The unpacked source alone cannot
establish correctness of the stored EROFS inode or flashed image bytes.
Do not replace an already-correct source symlink as a speculative fix, assume
SELinux caused EUCLEAN, infer hardware failure, or attribute the earlier arm
boot compiler crash directly to this arm64 path without evidence.

Next: inspect superblock and both alias inodes in the actual known V35 padded
EROFS image using dump.erofs, alongside the device kernel/mount information.
Distinguish image construction/old-kernel decoding from device readback issues
before any further write. V40 remains an uninstalled review JAR.
