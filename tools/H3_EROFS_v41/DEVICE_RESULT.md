# V41 device result — 2026-11-11

User-built system image SHA256:
d827c53bd4581a77db6aeedf0d6a50fe0808c2a7e3b714b8a97348ee78f09fd7.
The packaging audit checked all 452 symlinks before image creation completed.

After flashing and booting:
- arm64/boot.vdex lists normally as ../boot.vdex.
- Its hash is 3a265e2317b907d253c1e17c5f9bdc92beb3b9c4231efc2eba48d5806ec27b82,
  matching original common VDEX and source tree.
- SIM state LOADED,ABSENT; phone process PID 3157.
- Captured last crash buffer output is empty.
- User confirms calls and mobile internet work; bars remain empty after ~3 min.

The previously repeatable arm64 alias EUCLEAN is no longer observed under
this test. This supports the non-inline-symlink packaging workaround. It does
not prove every boot/compiler path or long-term stability. The separate early
reboot has not been explicitly retested/reported. V41 retains V35 application
and telephony contents; empty bars remain expected because V40 was not installed.

Use V41 as the working packaging baseline for further signal work, retain V35
for rollback, and keep the V40 review artifact uninstalled until an isolated
runtime conversion test validates the corrected old-HIDL member types.
