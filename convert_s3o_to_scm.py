import os, gzip, struct, math
from scm_io import pad, pad_file, write_scm

# 1. Read S3O from BAR pool
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

s3o_data = get_file('objects3d/raptors/raptor.s3o')
assert s3o_data, "Could not find raptor.s3o in BAR pool!"

SCALE = 0.06

class PieceNode:
    def __init__(self, name, parent_idx, ox, oy, oz):
        self.name = name
        self.parent_idx = parent_idx
        # S3O coordinates: X right, Y up, Z forward
        self.local_pos = (ox * SCALE, oy * SCALE, oz * SCALE)
        self.world_pos = (0, 0, 0)
        self.verts = []
        self.indices = []

pieces = []

def parse_tree(offset, parent_idx=-1):
    name_off, n_child, child_off, n_verts, v_off, v_type, prim_type, idx_cnt, idx_off, col_data, ox, oy, oz = struct.unpack('<10I3f', s3o_data[offset:offset+52])
    name = s3o_data[name_off:].split(b'\x00')[0].decode('latin1')
    
    current_idx = len(pieces)
    node = PieceNode(name, parent_idx, ox, oy, oz)
    
    if parent_idx >= 0:
        pw = pieces[parent_idx].world_pos
        node.world_pos = (pw[0] + node.local_pos[0], pw[1] + node.local_pos[1], pw[2] + node.local_pos[2])
    else:
        node.world_pos = node.local_pos
        
    pieces.append(node)
    
    if n_verts > 0:
        for v in range(n_verts):
            v_data = s3o_data[v_off + v*32 : v_off + (v+1)*32]
            vx, vy, vz, nx, ny, nz, tu, tv = struct.unpack('<8f', v_data)
            wx = node.world_pos[0] + vx * SCALE
            wy = node.world_pos[1] + vy * SCALE
            wz = node.world_pos[2] + vz * SCALE
            node.verts.append((wx, wy, wz, nx, ny, nz, tu, tv))
            
    if idx_cnt > 0:
        idx_data = s3o_data[idx_off : idx_off + idx_cnt*4]
        raw_indices = struct.unpack(f'<{idx_cnt}I', idx_data)
        node.indices = list(raw_indices)
        
    if n_child > 0 and child_off > 0:
        child_offsets = struct.unpack(f'<{n_child}I', s3o_data[child_off : child_off + 4*n_child])
        for co in child_offsets:
            parse_tree(co, current_idx)

parse_tree(52)

total_bone_data = []
bone_name_data = []
offset_val = 48
offset_val += pad(offset_val)

for p in pieces:
    offset_val += len(p.name) + 1
    bone_name_data.append(bytearray(p.name.encode('ascii')))

bone_name_offset = 48 + pad(48)
current_name_off = bone_name_offset

for p in pieces:
    # 4x4 inverse bind matrix: translation by -world_pos
    wx, wy, wz = p.world_pos
    inv_mat = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        -wx, -wy, -wz, 1.0
    ]
    lx, ly, lz = p.local_pos
    # Identity rotation in Supreme Commander quaternion format: (w=1, x=0, y=0, z=0)
    rot = (1.0, 0.0, 0.0, 0.0)
    
    total_bone_data.extend((*inv_mat, lx, ly, lz, *rot, current_name_off, p.parent_idx, 0, 0))
    current_name_off += len(p.name) + 1

# Vertices & Faces
total_vert_data = []
total_face_data = []
vert_counter = 0

for piece_idx, p in enumerate(pieces):
    base_vert_idx = vert_counter
    for (wx, wy, wz, nx, ny, nz, tu, tv) in p.verts:
        n_len = math.sqrt(nx*nx + ny*ny + nz*nz)
        if n_len > 0.0001:
            nx, ny, nz = nx/n_len, ny/n_len, nz/n_len
        else:
            nx, ny, nz = 0.0, 1.0, 0.0
            
        if abs(ny) < 0.9:
            tx, ty, tz = -nz, 0.0, nx
        else:
            tx, ty, tz = 1.0, 0.0, 0.0
        t_len = math.sqrt(tx*tx + ty*ty + tz*tz)
        if t_len > 0:
            tx, ty, tz = tx/t_len, ty/t_len, tz/t_len
            
        bx = ny*tz - nz*ty
        by = nz*tx - nx*tz
        bz = nx*ty - ny*tx
        
        u = tu
        v = 1.0 - tv
        
        total_vert_data.extend((wx, wy, wz, nx, ny, nz, tx, ty, tz, bx, by, bz, u, v, u, v, piece_idx, 0, 0, 0))
        vert_counter += 1
        
    for idx in p.indices:
        total_face_data.append(base_vert_idx + idx)

off_after_names = bone_name_offset + sum(len(p.name)+1 for p in pieces)
bone_offset = off_after_names + pad(off_after_names)

off_after_bones = bone_offset + len(pieces) * 108
vert_offset = off_after_bones + pad(off_after_bones)

off_after_verts = vert_offset + vert_counter * 68
face_offset = off_after_verts + pad(off_after_verts)

modl = [
    b'MODL', 5,
    bone_offset, len(pieces),
    vert_offset, 0, vert_counter,
    face_offset, len(total_face_data),
    0, 0, len(pieces)
]

mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
scm_output = os.path.join(mod_dir, "units", "XRA0101", "XRA0101_lod0.scm")
write_scm(scm_output, modl, total_bone_data, bone_name_data, total_vert_data, total_face_data)
print(f"SUCCESS: Wrote SCM model with correct (w=1, x=0, y=0, z=0) rotation to {scm_output}")
