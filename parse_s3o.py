import os, gzip, struct

pkg = r'P:\Games\Beyond-All-Reason\data\packages\ad33f718d83a34e194d7182194a91ede.sdp'
with gzip.open(pkg, 'rb') as gz:
    data = gz.read()

pos = 0
entries = {}
while pos < len(data):
    namelen = data[pos]
    pos += 1
    name = data[pos:pos+namelen].decode('utf-8', 'ignore')
    pos += namelen
    md5_bytes = data[pos:pos+16]
    pos += 16
    crc = struct.unpack('<I', data[pos:pos+4])[0]
    pos += 4
    size = struct.unpack('>I', data[pos:pos+4])[0]
    pos += 4
    md5_hex = data[pos-24:pos-8].hex()
    entries[name] = (md5_hex, size)

def get_file(name):
    for k in entries:
        if k.lower() == name.lower():
            md5_hex, size = entries[k]
            sub = md5_hex[:2]
            fn = md5_hex[2:] + '.gz'
            p = os.path.join(r'P:\Games\Beyond-All-Reason\data\pool', sub, fn)
            with gzip.open(p, 'rb') as gz:
                return gz.read()
    return None

s3o = get_file('objects3d/raptors/raptor.s3o')
magic, ver, rad, h, mx, my, mz, root_off, col_off, tex1_off, tex2_off = struct.unpack('<12sI5f4I', s3o[:52])

def parse_piece(off, parent_name='None', depth=0):
    name_off, n_child, child_off, n_verts, v_off, v_type, prim_type, idx_cnt, idx_off, col_data, ox, oy, oz = struct.unpack('<10I3f', s3o[off:off+52])
    name = s3o[name_off:].split(b'\x00')[0].decode('latin1')
    print('  '*depth + f'Piece \"{name}\": parent={parent_name}, offset=({ox:.2f}, {oy:.2f}, {oz:.2f}), verts={n_verts}, indices={idx_cnt}, prim={prim_type}')
    if n_child > 0 and child_off > 0:
        child_offsets = struct.unpack(f'<{n_child}I', s3o[child_off:child_off+4*n_child])
        for co in child_offsets:
            parse_piece(co, name, depth+1)

parse_piece(root_off)
