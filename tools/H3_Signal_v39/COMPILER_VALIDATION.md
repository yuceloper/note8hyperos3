# Temporary compiler check — 2026-11-11

On the recovered V35 phone, the user ran dex2oat64 with compiler-filter=verify,
instruction-set=arm64 and Xms32m/Xmx256m on the original DEX and V39 DEX.
Both returned exit code 0; captured output tails were empty. Separate OAT
outputs were under /data/local/tmp/signal-v39-art-20261111-011512.

Combined with DEVICE_VALIDATION.md, V39 passes device DEX file verification
and temporary compilation. This does not establish replacement bootclasspath
compatibility or working radio behavior: the running phone still uses V35.

install.py requires original V35 JAR hash and all original target preopt files
plus VDEX aliases. It uses a separate hyperos3-signal-v39 backup, preserves JAR
metadata and moves exactly eleven regular files and four links. It pins V39
SHA256 452faaae8d36ac59f4f6b7830ea4fd126b878678f377e79e8184568f40a33300.
Fixture validation used the actual V39 candidate/review report: successful
staging preserved all metadata and backup entries; a failure injected after
JAR write restored original JAR and all preopt files/links byte for byte.

package.py retains all V35 camera/MTD/policy/zram/init checks, additionally
checks installed V39 JAR and every backup inode/hash/metadata, and generates
hyperos3-ginkgo-v39-padded.img. No flash is part of either script. Keep the
working V35 system image for device rollback. Functional signal behavior and
new-system boot remain untested until that explicit device test.
