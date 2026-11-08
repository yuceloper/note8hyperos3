H3 BPF V6 - OFFLINE CANDIDATE, NOT BOOT TESTED

Source: Lineage 23.2 ginkgo 20261007 tethering CAPEX.
Private netbpfload and libbase/libbpf/libc++ have relative DT_RUNPATH.
Five mainline BPF objects are bind mounted only at load-bpf-programs.
Only that trigger calls the standalone service. Donor APEX is unchanged.
Original APEX service definition and HyperOS Java/native connectivity stay intact.
ro.bpf.kver_override=5.10.239 follows Lineage sm6125-common product.prop.
This is a userspace compatibility setting, not a kernel upgrade.
Loader success, verifier acceptance, network map ABI, hyper_bpfloader and
subsequent network startup still require runtime validation.
SELinux enforcement/policy, failure reboot and bpf.progs_loaded gating retained.
Backups: /linux/backups/hyperos3-bpf-v6
Run prepare_bpf_v6.py in the existing tools container with package at /package.
No phone flash is performed by the installer.
