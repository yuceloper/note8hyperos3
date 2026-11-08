# V20 MTD diagnostic runtime

Device ginkgo, system V20, vendor V15. User reports boot_completed=1 and ginkgo-mtd running in u:r:ginkgo_mtd:s0, PID 4409. Installed policy SHA256: 4ed1232de10626224c017ca7ea51fbcd9a332f4ae2f6ccbf1ef11ec2764219c5.

Reviewed capture: v20-mtd-20261108-214857, 27,527 log lines. Capture includes boot and events through 2026-11-08 21:48:58. The MTD startup audit shows system_prop read denied and init->MTD noatsecure denied. The previously observed mnt_vendor_file directory-search denial does not recur in this capture. No new MTD tee_device denial appears in the captured text. Absence of those denials does not verify actual persist read success, correct labels, or TEE functionality.

MiuiBatteryServiceImpl still reports eccSign is null at 21:31:54.025. Full Find Device functionality remains unverified. Shell cannot inspect persist paths under the current policy, as expected. Existing init-child SIGABRT at 21:31:49 is unresolved and is not attributed to MTD.

Next check: capture a bounded live log while opening the existing Find Device settings screen, without toggling account/activation state or granting additional permissions. No further policy change is justified solely by this capture. Persist writes and TEE access remain prohibited in the V20 diagnostic policy.
