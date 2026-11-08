HyperOS3 creek TR + Lineage23.2 ginkgo SELinux offline candidate.
Removes 3 ot_rcp kernel>=6.13 nlmsg rules; removes unsupported permission names from 9 vendor-qti-testscripts dontaudit rules; removes 14 conflicting debug/test allow rules (including duplicated keymint rule). Existing neverallows remain enabled. No permissions added. Coredump/debug tracing functionality may be reduced. Compilation does not prove boot or runtime compatibility. Nothing installed or flashed.
Use the same read-only donor volume and policy-lineage23-v1 output directory.
Also removes one vendor_init camera-property set allow from a separate public-policy candidate. Camera property initialization requires runtime verification.
