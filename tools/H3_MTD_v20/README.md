# V20: scoped read-only persist diagnostic

The pre-MTD persist backup reports mnt_vendor_file on the persist root, fdsd,
and fdsd/st. The existing st file is 628 bytes, mode 0600, owner root:system.
The runtime capture shows MTD HIDL worker calls denied while searching
/mnt/vendor and opening qseecom. Shell is independently denied HIDL find;
its lshal null warnings do not prove the service is absent.

V20 adds a dedicated ginkgo_mtd_persist_file type only for
/mnt/vendor/persist/fdsd(/.*)?. It permits MTD directory traversal/listing
and file read/map, plus ancestor directory search/getattr on mnt_vendor_file.
It grants no access to files carrying the generic mnt_vendor_file label.
The init action relabels only the fdsd subtree before the existing single
start attempt. This changes on-device SELinux metadata on next boot; it does
not delete, recreate, or explicitly write st contents. Preserve the verified
pre-MTD persist backup locally; do not upload device key material.

Explicit neverallow rules prohibit MTD persist-content writes and tee_device
access. These checks remain enabled in the candidate compilation. QSEE/TEE
operations therefore remain blocked and full Find Device functionality is
not expected from this diagnostic alone. No AIDL facade is introduced.

The prepare tool reproduces the V19 baseline, backs up policy/init/context
files, and preserves their ownership, modes and xattrs during installation.
The packaging tool validates ELF hashes/metadata, candidate policy, init and
context hashes before building the system image. Neither tool flashes a phone.
