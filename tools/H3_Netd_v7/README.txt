HyperOS3 ginkgo V7 offline candidate, not boot tested.

Fixes confirmed init file mounton denials using directory binds.
Uses original HyperOS tethering lib64 tree with only libnetd_updatable.so
replaced by matching Lineage23.2 library. All other donor libraries preserved.
Private libbase/libnetdutils/libc++ have unique filenames/SONAME/NEEDED
and relative RUNPATH to avoid replacing donor common libraries.
Dynamic exported symbol names/versions match donor libnetd_updatable.
Java, signed APEX, SELinux policy, encryption, failure handling unchanged.
Requires V6 tree hashes; backs up init to /linux/backups/hyperos3-netd-v7.
No flash. No format. Runtime BPF verifier/network/zygote still need testing.
