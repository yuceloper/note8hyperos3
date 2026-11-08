"""Compile an offline MTD policy foundation; never install or start a daemon."""
from pathlib import Path
import hashlib
import subprocess

EXPECTED = "4deded9b6bd729155ed39c5e8e9c7a0673ecc9fb7a82a5c7c624c24d5d8d7475"
tree = Path("/linux/build/hyperos3-ginkgo-v1")
vendor = Path("/reference/policy-lineage23-v1")
out = Path("/result/foundation-v1")
if out.exists():
    raise RuntimeError("Output exists; nothing overwritten")
inputs = []
for part, name in [("system", "plat"), ("system_ext", "system_ext"), ("product", "product")]:
    base = tree / part / "etc/selinux"
    inputs += [base / f"{name}_sepolicy.cil", base / "mapping/202504.cil"]
inputs += [vendor / "plat_pub_versioned.compat-v2.cil", vendor / "vendor_sepolicy.compat-v2.cil", vendor / "odm/selinux/odm_sepolicy.cil", Path("/reference/policy-fingerprint-v11/fingerprint-read.cil")]
for p in inputs:
    if not p.is_file():
        raise RuntimeError(f"Missing: {p}")
installed = tree / "odm/etc/selinux/precompiled_sepolicy"
if hashlib.sha256(installed.read_bytes()).hexdigest() != EXPECTED:
    raise RuntimeError("Installed baseline changed")
out.mkdir()
def compile_policy(files, name):
    dest = out / (name + ".policy")
    with (out / (name + ".log")).open("w") as log:
        result = subprocess.run(["secilc", "-m", "-M", "true", "-G", "-c", "30", *map(str, files), "-o", str(dest), "-f", str(out / (name + ".file_contexts"))], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        print((out / (name + ".log")).read_text())
        raise RuntimeError("Compilation failed; nothing installed")
    return dest
baseline = compile_policy(inputs, "baseline")
if baseline.read_bytes() != installed.read_bytes():
    raise RuntimeError("Baseline reproduction mismatch")
CIL = '(type ginkgo_mtd)\n(roletype object_r ginkgo_mtd)\n(typeattributeset domain (ginkgo_mtd))\n(type ginkgo_mtd_exec)\n(roletype object_r ginkgo_mtd_exec)\n(typeattributeset file_type (ginkgo_mtd_exec))\n(typeattributeset exec_type (ginkgo_mtd_exec))\n(typeattributeset vendor_file_type (ginkgo_mtd_exec))\n(type ginkgo_mtd_hwservice)\n(roletype object_r ginkgo_mtd_hwservice)\n(typeattributeset hwservice_manager_type (ginkgo_mtd_hwservice))\n(typeattributeset protected_hwservice (ginkgo_mtd_hwservice))\n(typetransition init ginkgo_mtd_exec process ginkgo_mtd)\n(allow init ginkgo_mtd (process (transition rlimitinh siginh)))\n(allow ginkgo_mtd ginkgo_mtd_exec (file (entrypoint read open getattr execute map)))\n(allow ginkgo_mtd init (process (sigchld)))\n(allow ginkgo_mtd hwservicemanager (binder (call transfer)))\n(allow hwservicemanager ginkgo_mtd (binder (call transfer)))\n(allow ginkgo_mtd hwservicemanager (fd (use)))\n(allow hwservicemanager ginkgo_mtd (fd (use)))\n(allow ginkgo_mtd ginkgo_mtd_hwservice (hwservice_manager (add find)))\n(allow ginkgo_mtd hidl_base_hwservice (hwservice_manager (add)))\n(allow platform_app ginkgo_mtd_hwservice (hwservice_manager (find)))\n(allow platform_app ginkgo_mtd (binder (call transfer)))\n(allow ginkgo_mtd platform_app (binder (transfer)))\n(allow platform_app ginkgo_mtd (fd (use)))\n'
candidate = out / "mtd-foundation.cil"
candidate.write_text(CIL)
policy = compile_policy(inputs + [candidate], "mtd-foundation")
print("V16 MTD POLITIKA TEMELI DERLENDI. NEVERALLOW KONTROLLERI ACIK.")
print("SHA256:", hashlib.sha256(policy.read_bytes()).hexdigest())
print("PERSIST VE TEE ERISIMI EKLENMEDI. SERVIS BASLATILMADI.")
print("CALISMA AGACINA KURULMADI. TELEFONA YAZILMADI.")
