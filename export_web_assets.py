import os
import struct
import math
import json
import gzip
import shutil
from PIL import Image

# 1. Read BAR Pool S3O
pkg = r'P:\Games\Beyond-All-Reason\data\packages\ad33f718d83a34e194d7182194a91ede.sdp'
with gzip.open(pkg, 'rb') as gz:
    pkg_data = gz.read()

entries = {}
pos = 0
while pos < len(pkg_data):
    namelen = pkg_data[pos]
    pos += 1
    name = pkg_data[pos:pos+namelen].decode('utf-8', 'ignore')
    pos += namelen
    md5_bytes = pkg_data[pos:pos+16]
    pos += 16
    crc = struct.unpack('<I', pkg_data[pos:pos+4])[0]
    pos += 4
    size = struct.unpack('>I', pkg_data[pos:pos+4])[0]
    pos += 4
    md5_hex = md5_bytes.hex()
    entries[name.lower()] = (md5_hex, size)

def get_bar_file(relpath):
    k = relpath.lower().replace('\\', '/')
    if k in entries:
        md5_hex, size = entries[k]
        sub = md5_hex[:2]
        fn = md5_hex[2:] + '.gz'
        p = os.path.join(r'P:\Games\Beyond-All-Reason\data\pool', sub, fn)
        with gzip.open(p, 'rb') as gz:
            return gz.read()
    return None

raptor_s3o = get_bar_file('objects3d/raptors/raptor.s3o')
spike_s3o = get_bar_file('objects3d/raptors/spike.s3o')
assert raptor_s3o and spike_s3o, "Could not find S3O files!"

SCALE = 0.06

# 2. Extract Raptor Pieces Hierarchy
pieces = []
def parse_s3o_tree(offset, parent_name=None):
    name_off, n_child, child_off, n_verts, v_off, v_type, prim_type, idx_cnt, idx_off, col_data, ox, oy, oz = struct.unpack('<10I3f', raptor_s3o[offset:offset+52])
    name = raptor_s3o[name_off:].split(b'\x00')[0].decode('latin1')
    
    verts = []
    uvs = []
    normals = []
    if n_verts > 0:
        for v in range(n_verts):
            v_data = raptor_s3o[v_off + v*32 : v_off + (v+1)*32]
            vx, vy, vz, nx, ny, nz, tu, tv = struct.unpack('<8f', v_data)
            verts.extend([round(vx * SCALE, 5), round(vy * SCALE, 5), round(vz * SCALE, 5)])
            normals.extend([round(nx, 4), round(ny, 4), round(nz, 4)])
            uvs.extend([round(tu, 4), round(1.0 - tv, 4)])
            
    indices = []
    if idx_cnt > 0:
        idx_data = raptor_s3o[idx_off : idx_off + idx_cnt*4]
        indices = list(struct.unpack(f'<{idx_cnt}I', idx_data))
        
    p_info = {
        'name': name,
        'parent': parent_name,
        'pivot': [round(ox * SCALE, 5), round(oy * SCALE, 5), round(oz * SCALE, 5)],
        'vertices': verts,
        'normals': normals,
        'uvs': uvs,
        'indices': indices
    }
    pieces.append(p_info)
    
    if n_child > 0 and child_off > 0:
        child_offsets = struct.unpack(f'<{n_child}I', raptor_s3o[child_off : child_off + 4*n_child])
        for co in child_offsets:
            parse_s3o_tree(co, name)

parse_s3o_tree(52)

# 3. Extract Spike Projectile Mesh
name_off, n_child, child_off, n_verts, v_off, v_type, prim_type, idx_cnt, idx_off, col_data, ox, oy, oz = struct.unpack('<10I3f', spike_s3o[52:104])
spike_verts = []
spike_uvs = []
spike_normals = []
for v in range(n_verts):
    v_data = spike_s3o[v_off + v*32 : v_off + (v+1)*32]
    vx, vy, vz, nx, ny, nz, tu, tv = struct.unpack('<8f', v_data)
    spike_verts.extend([round((ox + vx) * SCALE, 5), round((oy + vy) * SCALE, 5), round((oz + vz) * SCALE, 5)])
    spike_normals.extend([round(nx, 4), round(ny, 4), round(nz, 4)])
    spike_uvs.extend([round(tu, 4), round(1.0 - tv, 4)])

idx_data = spike_s3o[idx_off : idx_off + idx_cnt*4]
spike_indices = list(struct.unpack(f'<{idx_cnt}I', idx_data))

spike_info = {
    'name': 'spike',
    'vertices': spike_verts,
    'normals': spike_normals,
    'uvs': spike_uvs,
    'indices': spike_indices
}

# 4. Save JSON Assets to static/data
static_data_dir = r"e:\Games\FAFMods\static\data"
os.makedirs(static_data_dir, exist_ok=True)

with open(os.path.join(static_data_dir, "raptor_model.json"), "w", encoding="utf-8") as f:
    json.dump({'pieces': pieces}, f)

with open(os.path.join(static_data_dir, "spike_model.json"), "w", encoding="utf-8") as f:
    json.dump(spike_info, f)

# 5. Save PNG Textures
img_dir = r"e:\Games\FAFMods\static\img"
os.makedirs(img_dir, exist_ok=True)
mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
albedo_path = os.path.join(mod_dir, "units", "XRA0101", "XRA0101_Albedo.dds")
im = Image.open(albedo_path)
im.save(os.path.join(img_dir, "raptor_albedo.png"))

# 6. Save Sounds
sounds_dir = r"e:\Games\FAFMods\static\sounds"
os.makedirs(sounds_dir, exist_ok=True)
for sname in ['smallraptorattack.wav', 'smallraptordead.wav']:
    sdata = get_bar_file(f'sounds/raptors/{sname}')
    with open(os.path.join(sounds_dir, sname), 'wb') as f:
        f.write(sdata)

print(f"Exported {len(pieces)} pieces to raptor_model.json, spike to spike_model.json, textures and sounds!")
