"""Binary XML helpers for restoring the working original-camera label/routing."""
import struct

ANDROID = 'http://schemas.android.com/apk/res/android'
OLD = 'com.android.camera'
NEW = 'com.ginkgo.micamera6test'
U32 = 0xffffffff

def chunks(data):
    typ, hdr, size = struct.unpack_from('<HHI', data)
    if (typ, hdr, size) != (3, 8, len(data)):
        raise ValueError('Not a complete binary XML document')
    pos = 8
    result = []
    while pos < len(data):
        t, h, n = struct.unpack_from('<HHI', data, pos)
        if n < h or h < 8 or pos+n > len(data):
            raise ValueError('Invalid binary XML chunk')
        result.append((t, bytearray(data[pos:pos+n])))
        pos += n
    return result

def strings_from_pool(pool):
    t, h, size, count, styles, flags, start, style_start = struct.unpack_from('<HHIIIIII', pool)
    if t != 1 or h != 28 or styles or flags & 256 or style_start:
        raise ValueError('Expected unstyled UTF16 source string pool')
    result = []
    for i in range(count):
        pos = start + struct.unpack_from('<I', pool, h + i*4)[0]
        length = struct.unpack_from('<H', pool, pos)[0]; pos += 2
        if length & 0x8000:
            length = ((length & 0x7fff) << 16) | struct.unpack_from('<H', pool, pos)[0]
            pos += 2
        result.append(bytes(pool[pos:pos+length*2]).decode('utf-16le'))
    return result

def make_pool(strings):
    body = bytearray(); offsets = []
    for s in strings:
        value = s.encode('utf-16le'); length = len(value)//2
        if length >= 32768:
            raise ValueError('Unexpected long manifest string')
        offsets.append(len(body))
        body += struct.pack('<H', length) + value + b'\x00\x00'
    body += b'\x00' * (-len(body) % 4)
    start = 28+4*len(strings)
    return (struct.pack('<HHIIIIII', 1, 28, start+len(body), len(strings), 0, 0, start, 0)
            + b''.join(struct.pack('<I', x) for x in offsets) + body)

def attributes(node, strings):
    name = strings[struct.unpack_from('<I', node, 20)[0]]
    start, stride, count = struct.unpack_from('<HHH', node, 24)
    if stride != 20:
        raise ValueError('Unexpected attribute width')
    result = []
    for i in range(count):
        pos = 16+start+i*stride
        ns, key, raw, size, reserved, typ, val = struct.unpack_from('<IIIHBBI', node, pos)
        value = strings[val] if typ == 3 else val
        result.append((pos, '' if ns == U32 else strings[ns], strings[key], value))
    return name, result

PACKAGE = "com.ginkgo.micamera6test"
SECURE_ACTION = "android.media.action.STILL_IMAGE_CAMERA_SECURE"
ORIGINAL_LABEL = 2132018043

def finalize_manifest(data):
    parts = chunks(data)
    strings = strings_from_pool(next(n for t,n in parts if t == 1))
    result = []
    stack = []
    skip = 0
    removed = labels = 0
    secure_components = []
    package = None
    for typ, node in parts:
        if typ == 0x102:
            tag, attrs = attributes(node, strings)
            values = {(ns,key):value for _,ns,key,value in attrs}
            if tag == "manifest":
                package = values.get(("", "package"))
            parent_activity = next((v.get((ANDROID,"name")) for t,v in reversed(stack)
                                    if t in ("activity", "activity-alias")), None)
            stack.append((tag,values))
            drop = (tag == "action" and parent_activity == "com.android.camera.AssistantCamera"
                    and values.get((ANDROID,"name")) == SECURE_ACTION)
            if skip or drop:
                skip += 1
                if drop:
                    removed += 1
                continue
            if tag == "application":
                for pos, ns, key, value in attrs:
                    if ns == ANDROID and key == "label":
                        if value != "Xiaomi Camera 6.2 Test":
                            raise ValueError("Unexpected test label")
                        struct.pack_into("<I", node, pos+8, U32)
                        struct.pack_into("<HBBI", node, pos+12, 8, 0, 1, ORIGINAL_LABEL)
                        labels += 1
            if tag == "action" and values.get((ANDROID,"name")) == SECURE_ACTION:
                secure_components.append(parent_activity)
        elif typ == 0x103:
            if not stack:
                raise ValueError("Unbalanced XML")
            tag,_ = stack.pop()
            if strings[struct.unpack_from("<I",node,20)[0]] != tag:
                raise ValueError("Mismatched XML end")
            if skip:
                skip -= 1
                continue
        elif skip:
            continue
        result.append(bytes(node))
    if (package != PACKAGE or stack or skip or removed != 1 or labels != 1
            or secure_components != ["com.android.camera.Camera"]):
        raise ValueError("Unexpected original-camera routing/label")
    body = b"".join(result)
    output = struct.pack("<HHI",3,8,8+len(body)) + body
    chunks(output)
    return output

