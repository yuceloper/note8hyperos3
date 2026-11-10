# V41 — V35-content EROFS symlink layout experiment

Keep V40 uninstalled. V41 changes packaging only, using the restored V35 JAR,
preoptimization files, camera, policy, MTD and other existing baseline contents.
No kernel/vendor/policy change, cache clearing or source-tree link replacement.

## Evidence and inference

V35 common boot.vdex and its arm alias read with matching source hashes.
Only the live arm64 alias returns EUCLEAN; both source aliases are correct.
The V35 stored image has 4096-byte blocks and metadata start block 0:

| Alias | NID | Inode offset within block | Inode bytes | Xattr bytes | Target bytes | End relative to original block |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| arm/boot.vdex | 148095357 | 4000 | 64 | 16 | 12 | 4092 |
| arm64/boot.vdex | 154175614 | 4032 | 64 | 16 | 12 | 4124 |

Both are layout 2 (flat inline). The arm64 inode/xattr/target span the metadata
block boundary. Older fast-symlink code can incorrectly reject otherwise valid
images when that payload is outside the inode's page, instead of using the
normal symlink read path. This strongly matches the asymmetry, but the exact
device kernel source and its error log have not established the code path.

Primary kernel example:
https://android.googlesource.com/kernel/common/+/158eae71734679b43e8731c48eec269746118385/fs/erofs/inode.c
Upstream maintainer fix explanation:
https://lists.openwall.net/linux-kernel/2024/09/09/84

The dump tool's minimum-upstream-kernel label is not proof that a 4.14 Android
kernel lacks backported EROFS support. Do not attribute the separate arm
InitWithoutImage compiler abort to this arm64 path without a device comparison.

## Builder correction

A native probe with unmodified erofs-utils 1.8.6 proved that -E noinline_data
still emits layout-2 symlinks. Its lib/inode.c condition only checks S_ISREG.
The source-pinned builder extends that single condition to S_ISLNK as well.
With inline data enabled, original behavior is unchanged. With noinline_data,
symlinks use flat-plain layout 0 and avoid the old fast-symlink path.

Source archive: Debian's upstream erofs-utils 1.8.6 tarball.
SHA256: 5b221dc3fd6d151425b30534ede46fb7a90dc233a8659cba0372796b0a066547.
Original lib/inode.c SHA256:
7423597551f0ad7e63d1fdd359aa44fffb29c63022c63dfde12fd39f54c5ffc0
Patched lib/inode.c SHA256:
4f3564ba02c6765e2b1c49e66ec1f97b6a11a6efddafe8352e09d13c03197068

Source checks verified the unique condition replacement and byte-identical
reversal; repeat/unexpected input is rejected. The Docker build must compile
the patched tools and pass a real 16-symlink image probe. Native execution of
the patched tools is still pending that build; do not claim it already passed.

## Build tools first

```bash
bash <<'SH'
set -euo pipefail
cd "$HOME/note8hyperos3"
git fetch origin investigate/erofs-v41-symlink-layout
git restore --source=FETCH_HEAD --worktree -- tools/H3_EROFS_v41
docker build -t ginkgo-port-tools:erofs-v41-symlink tools/H3_EROFS_v41
SH
```

No work-volume/device mount or ROM image creation occurs in this build.
The build fails if noinline_data still leaves any probe symlink at layout 2.

## Package after the tool probe succeeds

Run package.py in the new image with the usual Linux work volume read-only,
tools read-only, out mounted /reference read-only and out/images mounted /result.
It retains all V35 packaging checks, requires V35 telephony source/preopt
hashes and metadata from the V39 recovery manifest, then runs the tool probe.
It uses -E noinline_data for the full image and audits **every source symlink**
in the resulting image through dump.erofs. Every link must be layout 0, with
matching target-string byte length; critical arm/arm64 boot.vdex links must
be included. It then runs full fsck extraction verification before padding.

Output: hyperos3-ginkgo-v41-padded.img, 8589934592 bytes, validation JSON.
No flash is included. Keep the original V35 image as rollback.
The full-image audit and live-phone boot.vdex read test remain pending.
Do not treat V41 as proof of the separate compiler issue or of V40 signal behavior.
