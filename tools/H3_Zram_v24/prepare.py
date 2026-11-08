"""Same-size, exact-source patch of three duplicate late zRAM commands."""
import hashlib
SOURCE = '443938a2560f64256dcc0076ff6edfe75002e0efd0941f9429ab92871fa96fa3'
CANDIDATE = '58583f98ac2a909a368e035f7ce0d0a58789048407c20149a25a879893891c5d'
OFFSET = 14591
OLD = b'    write /sys/block/zram0/comp_algorithm lz4\n    # Enable zRAM data deduplication feature\n    write /sys/block/zram0/use_dedup 1\n    # Mount swap partitions specified in fstab\n    swapon_all /vendor/etc/fstab.zram'
NEW = b'    #rite /sys/block/zram0/comp_algorithm lz4\n    # Enable zRAM data deduplication feature\n    #rite /sys/block/zram0/use_dedup 1\n    # Mount swap partitions specified in fstab\n    #wapon_all /vendor/etc/fstab.zram'

def prepare(original):
    if hashlib.sha256(original).hexdigest() != SOURCE:
        raise ValueError('V15 init.target.rc source hash mismatch')
    if original[OFFSET:OFFSET+len(OLD)] != OLD:
        raise ValueError('Source commands mismatch')
    result = original[:OFFSET] + NEW + original[OFFSET+len(OLD):]
    if len(result) != len(original) or hashlib.sha256(result).hexdigest() != CANDIDATE:
        raise ValueError('Candidate validation failed')
    return result
