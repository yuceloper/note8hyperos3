"""Same-size, exact-source patch of automatic vendor engineering test-service start."""
import hashlib
SOURCE = '12ec1e2847b736ac41c28543ac3222030365d9c819d4dd1b1b5ecd868536dcf3'
CANDIDATE = '3b548d790bcd206b63be908ab8b32d052b45b0e8ac488802aa87cb6b723505df'
OFFSET = 20039
OLD = b'    start qti-testscripts'
NEW = b'    #tart qti-testscripts'

def prepare(original):
    if hashlib.sha256(original).hexdigest() != SOURCE:
        raise ValueError('V24 init.qcom.rc source hash mismatch')
    if original[OFFSET:OFFSET+len(OLD)] != OLD:
        raise ValueError('Source commands mismatch')
    result = original[:OFFSET] + NEW + original[OFFSET+len(OLD):]
    if len(result) != len(original) or hashlib.sha256(result).hexdigest() != CANDIDATE:
        raise ValueError('Candidate validation failed')
    return result
