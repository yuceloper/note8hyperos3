"""Narrow binary Android manifest identity patch; preserve resource IDs."""
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

def patch_manifest(data):
    parts = chunks(data)
    pools = [i for i, (t, _) in enumerate(parts) if t == 1]
    if len(pools) != 1:
        raise ValueError('Expected one string pool')
    strings = strings_from_pool(parts[pools[0]][1])
    def idx(value):
        if value not in strings:
            strings.append(value)
        return strings.index(value)
    declared = {}
    for typ, node in parts:
        if typ != 0x102:
            continue
        tag, attrs = attributes(node, strings)
        for _, ns, key, value in attrs:
            if tag in ('permission', 'permission-tree', 'permission-group') and ns == ANDROID and key == 'name':
                declared[value] = NEW+'.declared.'+value
    class_attrs = {
        'application': ('name', 'backupAgent', 'appComponentFactory', 'manageSpaceActivity'),
        'activity': ('name', 'parentActivityName'),
        'activity-alias': ('name', 'targetActivity', 'parentActivityName'),
        'provider': ('name',), 'service': ('name',), 'receiver': ('name',),
        'instrumentation': ('name',),
    }
    kept = []; skipping = 0; seen_package = False; seen_app = set()
    for typ, node in parts:
        if typ == 0x102:
            tag, attrs = attributes(node, strings)
            values = {(ns, key): value for _, ns, key, value in attrs}
            drop = tag == 'original-package' or (tag == 'action' and values.get((ANDROID, 'name')) in (
                'android.intent.action.BOOT_COMPLETED', 'android.intent.action.LOCKED_BOOT_COMPLETED'))
            if skipping or drop:
                skipping += 1
                continue
            for pos, ns, key, value in attrs:
                new = value
                if tag == 'manifest' and ns == '' and key == 'package':
                    if value != OLD:
                        raise ValueError('Unexpected package')
                    new = NEW; seen_package = True
                if ns == ANDROID:
                    if key == 'sharedUserId':
                        raise ValueError('Unexpected shared UID')
                    if key in class_attrs.get(tag, ()) and isinstance(value, str):
                        if value.startswith('.'):
                            new = OLD+value
                        elif '.' not in value:
                            new = OLD+'.'+value
                    if isinstance(value, str) and value in declared:
                        new = declared[value]
                    if tag == 'provider' and key == 'authorities':
                        new = (NEW+'.resourceprovider.'+str(value) if isinstance(value, int) else ';'.join(NEW+'.provider'+str(i)+'.'+v for i,v in enumerate(value.split(';'))))
                    if key in ('taskAffinity', 'process') and isinstance(value, str) and value.startswith(OLD):
                        new = NEW+value[len(OLD):]
                    if tag == 'application' and key == 'label':
                        new = 'Xiaomi Camera 6.2 Test'; seen_app.add(key)
                    if tag == 'application' and key == 'extractNativeLibs':
                        struct.pack_into('<I', node, pos+8, U32)
                        struct.pack_into('<HBBI', node, pos+12, 8, 0, 0x12, U32)
                        seen_app.add(key)
                        continue
                if new != value:
                    value_idx = idx(new)
                    struct.pack_into('<I', node, pos+8, value_idx)
                    struct.pack_into('<HBBI', node, pos+12, 8, 0, 3, value_idx)
        elif typ == 0x103 and skipping:
            skipping -= 1
            continue
        elif skipping:
            continue
        kept.append((typ, node))
    if not seen_package or seen_app != {'label', 'extractNativeLibs'} or skipping:
        raise ValueError('Source manifest preconditions not met')
    body = b''.join(make_pool(strings) if t == 1 else bytes(n) for t,n in kept)
    result = struct.pack('<HHI', 3, 8, 8+len(body)) + body
    chunks(result)
    return result
