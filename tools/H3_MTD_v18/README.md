# V18: MTD init execution and HIDL client policy

V17 boot completed, but ginkgo-mtd stopped without registering its HIDL service.
The runtime capture shows init denied file execute on ginkgo_mtd_exec at
2026-11-08 20:00:55.862. The foundation had a process transition and target-domain
entrypoint permission, but omitted the source init file execute permission.

The capture also shows system_server denied find on ginkgo_mtd_hwservice.
V18 adds the normal init executable access and typed HIDL client binder/FD rules
for system_server. It does not grant access to default_android_service or invent
an AIDL implementation. Persist/TEE permissions remain unchanged.

The tool reproduces V17 with neverallow checks enabled before compiling V18.
It installs only the offline precompiled policy, preserving metadata and backing
up the previous binary. Init keeps the V17 single-attempt trigger. No device is
flashed by this script. MTD functionality and installed linker namespace remain
unverified until the next runtime test.
