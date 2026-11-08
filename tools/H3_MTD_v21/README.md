# V21: existing-firmware QSEE communication diagnostic

Two V20 live captures reproduce tee_device read/write denials followed by
QSEECom open failure, cardapp start failure and null FID. No persist traversal
denial recurs in these captures. Recovery read-only inspection confirms the
device modem image contains cardapp.b00 through b07 and cardapp.mdt. File
presence alone does not verify the donor client's secure-world protocol.

V21 reproduces V20 exactly, then removes only the diagnostic TEE neverallow
introduced by V20. It adds QSEE and ION device read/write/ioctl/map and firmware
file read access. It keeps all upstream neverallow checks and the explicit
neverallow rules prohibiting MTD writes to its persist file/directory type.
No firmware, vendor, boot, existing persist contents, or application signatures
are replaced by these preparation tools. No raw RPMB/block-device permissions
or provisioning commands are introduced.

QSEE communication is not a read-only operation simply because normal persist
writes remain denied: secure-world behavior belongs to the existing trustlet.
The runtime test must establish whether cardapp loads and normal client FID/
sign requests succeed. Do not invoke provisioning, install keyboxes, erase
secure storage, replace modem/TZ firmware, or fabricate device identities.
The verified pre-MTD persist backup remains a local rollback artifact, not a
backup of RPMB or all secure-world state.

The init single-attempt trigger and fdsd-only relabel operation remain as in
V20. Candidate preparation and packaging do not flash a phone. Functionality
and stability are unverified until device testing.
