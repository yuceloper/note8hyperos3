# V40 field type correction — review only

V39 device testing reached getSignalStrengthResponse_1_2 but phone crashed
with NoSuchFieldError. The member name tdScdma was correct; its requested type
V1_2.TdscdmaSignalStrength was incorrect. Actual framework.jar declares it as
V1_0.TdScdmaSignalStrength even within V1_2.SignalStrength.

Actual framework.jar SHA256:
6a78c1a8e689a7bbc138e0771ff22fb583f28e7ae888bbeee5286d3be497f47d

An audit of all 12 introduced field references against declared fields in all
framework.jar DEX files found exactly this one mismatch; the other 11 match.
prepare.py refuses different inputs or a different mismatch set. It replaces
only that field-ID's two-byte type index, preserves every instruction byte
and all other DEX data, verifies field-ID sorting/uniqueness, fixes checksums,
and rechecks declarations, hidden-API restrictions, version and section padding.
All 12 new references must resolve to exact owner/name/type declarations.

Inputs are exact original JAR and V39 hashes, plus the actual framework hash.
The local review candidate is
1279a5eb44e5a0ff6ca32943af7b7b31f793c668adff9c1849ff146c3f9fe5a0.
This is not runtime tested. No install/package/flash script is included.

## First restore the offline V35 tree

Phone V35 recovery was user-confirmed after the failed V39 test. Offline tree
still needs tools/H3_Signal_v39/restore.py to restore its own V39 backup.
Do not use the V38 restore script for V39. The V39 script imports its sibling
installer constants and restores /linux/backups/hyperos3-signal-v39.

## Prepare after restoration

Mount the Linux volume read-only, tools read-only, all out inputs read-only
and out/signal-v40 as a writable output directory. Invoke:

```
python3 /tools/H3_Signal_v40/prepare.py \
  --source /reference/signal-v38-reference/telephony-common.jar \
  --v39 /reference/signal-v39/review-v1/telephony-common-v39.jar \
  --framework /linux/build/hyperos3-ginkgo-v1/system/framework/framework.jar \
  --out /result/review-v1
```

The framework hash guard stops before writing if the offline framework differs
from the uploaded live reference. No device files/properties are changed.

Next gate: Android file verifier, then actual method/field resolution against
the running framework. Temporary compilation alone did not detect this
external field-resolution failure in V39 and cannot be treated as proof.

Also unresolved: arm boot-image dex2oat ClassLinker InitWithoutImage abort and
user-reported early reboot. Investigate boot-image dependency handling before
another system image; a corrected field type does not prove that issue fixed.
