# V22: scoped Find Device record updates

V21 runtime shows the device cardapp loads from /vendor/firmware_mnt/image and
returns successful responses (32/64 bytes). That verifies the observed QSEE
commands, not the entire MTD implementation. Repeated QSEE cleanup warnings
remain unresolved. MTD remains running in its dedicated SELinux domain.

At 2026-11-09 00:00:53 and 00:01:05 the Find Device interaction is followed by
MTD denied directory write on fdsd, labeled ginkgo_mtd_persist_file. The user
reports a storage-corrupt-style warning. This is a permission blocker and does
not establish physical corruption or guarantee that the existing st data is
otherwise valid.

V22 removes only the diagnostic guards prohibiting updates of the custom
fdsd persist type. It grants file write/append/create/unlink/rename/setattr and
directory write/add_name/remove_name, permitting record replacement including
temporary-file/rename workflows. Directory creation, removal, renaming and
attribute modification remain explicitly prohibited for MTD. Other persist
labels, raw partitions and modem/TZ firmware receive no new permissions.
The fdsd-only context rule, relabel action, and existing QSEE access are kept.

Preparation changes only the offline precompiled policy. At runtime normal
Find Device client requests may now modify or replace records in fdsd. This
is no longer a read-only persist diagnostic. No explicit delete/reset/format
or key-provisioning command is issued by these tools. Preserve the verified
pre-MTD persist backup locally. Do not fabricate device identities or invoke
attestation/keybox provisioning.

The tool reproduces V21 before compiling with upstream neverallow checks on,
backs up the policy, verifies bytes and metadata, and records validation hashes.
Packaging checks the candidate and current init/context/ELF metadata. Neither
script flashes the phone. Find Device functionality still requires runtime
validation; other ROM stability issues remain outside this change.
