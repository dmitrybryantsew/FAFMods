import os
import gzip
import struct
import math
import wave
import io
import shutil
import zipfile
from scm_io import pad, pad_file, write_scm

# ---------------------------------------------------------------------------
# Directories & Setup
# ---------------------------------------------------------------------------
mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
icons_dir = os.path.join(mod_dir, "icons", "units")
units_root = os.path.join(mod_dir, "units")
proj_root = os.path.join(mod_dir, "projectiles")
sounds_dir = os.path.join(mod_dir, "sounds")
raptor_sounds_dir = os.path.join(sounds_dir, "raptors")

# Unit directories
dir_xra0101 = os.path.join(units_root, "XRA0101")
dir_xra0103 = os.path.join(units_root, "XRA0103") # Kamikaze Tick / Dodo
dir_xra0104 = os.path.join(units_root, "XRA0104") # Biological Acid Bomber
dir_xra0105 = os.path.join(units_root, "XRA0105") # Flying Raptor Fighter
dir_xra0107 = os.path.join(units_root, "XRA0107") # Gestation Roost (Factory)
dir_xra0109 = os.path.join(units_root, "XRA0109") # Bio-Weaver Builder & Healer
dir_xra0201 = os.path.join(units_root, "XRA0201") # 6-Legged Crawler Spiker
dir_xra0202 = os.path.join(units_root, "XRA0202") # Mobile Bio-Artillery / Mortar Bug
dir_xra0205 = os.path.join(units_root, "XRA0205") # Hovering Bio-Gunship
dir_xra0301 = os.path.join(units_root, "XRA0301") # Heavy Assault Apex Behemoth
dir_xra0401 = os.path.join(units_root, "XRA0401") # Experimental Matriarch Queen Titan

# Projectiles
dir_proj_biobomb = os.path.join(proj_root, "XRA_BioBomb01")
dir_proj_queenplasma = os.path.join(proj_root, "XRA_QueenPlasma01")

target_dirs = [
    icons_dir, dir_xra0103, dir_xra0104, dir_xra0109, dir_xra0202, dir_xra0205,
    dir_xra0301, dir_xra0401, dir_proj_biobomb, dir_proj_queenplasma, raptor_sounds_dir
]
for d in target_dirs:
    os.makedirs(d, exist_ok=True)

# ---------------------------------------------------------------------------
# BAR Pool Indexing
# ---------------------------------------------------------------------------
print("Indexing BAR package...")
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
    entries[name.lower().replace('\\', '/')] = (md5_bytes.hex(), size)

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

print(f"BAR package indexed ({len(entries)} files).")

# ---------------------------------------------------------------------------
# S3O -> SCM Converter
# ---------------------------------------------------------------------------
SCALE = 0.06

class PieceNode:
    def __init__(self, name, parent_idx, ox, oy, oz):
        self.name = name
        self.parent_idx = parent_idx
        self.local_pos = (ox * SCALE, oy * SCALE, oz * SCALE)
        self.world_pos = (0.0, 0.0, 0.0)
        self.verts = []
        self.indices = []

def convert_s3o_to_scm(s3o_bytes, scm_filepath):
    pieces = []
    root_offset = struct.unpack('<I', s3o_bytes[36:40])[0]

    def parse_piece(offset, parent_idx=-1):
        name_off, n_child, child_off, n_verts, v_off, v_type, prim_type, idx_cnt, idx_off, col_data, ox, oy, oz = struct.unpack('<10I3f', s3o_bytes[offset:offset+52])
        name = s3o_bytes[name_off:].split(b'\x00')[0].decode('latin1')
        c_idx = len(pieces)
        node = PieceNode(name, parent_idx, ox, oy, oz)
        if parent_idx >= 0:
            pw = pieces[parent_idx].world_pos
            node.world_pos = (pw[0] + node.local_pos[0], pw[1] + node.local_pos[1], pw[2] + node.local_pos[2])
        else:
            node.world_pos = node.local_pos
        pieces.append(node)

        if n_verts > 0:
            for v in range(n_verts):
                v_data = s3o_bytes[v_off + v*32 : v_off + (v+1)*32]
                vx, vy, vz, nx, ny, nz, tu, tv = struct.unpack('<8f', v_data)
                wx = node.world_pos[0] + vx * SCALE
                wy = node.world_pos[1] + vy * SCALE
                wz = node.world_pos[2] + vz * SCALE
                node.verts.append((wx, wy, wz, nx, ny, nz, tu, tv))

        if idx_cnt > 0:
            idx_data = s3o_bytes[idx_off : idx_off + idx_cnt*4]
            node.indices = list(struct.unpack(f'<{idx_cnt}I', idx_data))

        if n_child > 0 and child_off > 0:
            child_offsets = struct.unpack(f'<{n_child}I', s3o_bytes[child_off : child_off + 4*n_child])
            for co in child_offsets:
                parse_piece(co, c_idx)

    parse_piece(root_offset)

    bone_name_offset = 48 + pad(48)
    total_bone_data = []
    bone_name_data = []
    current_name_off = bone_name_offset

    for p in pieces:
        bone_name_data.append(bytearray(p.name.encode('ascii')))
        wx, wy, wz = p.world_pos
        inv_mat = [
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            -wx, -wy, -wz, 1.0
        ]
        lx, ly, lz = p.local_pos
        rot = (1.0, 0.0, 0.0, 0.0)
        total_bone_data.extend((*inv_mat, lx, ly, lz, *rot, current_name_off, p.parent_idx, 0, 0))
        current_name_off += len(p.name) + 1

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

    off_after_names = bone_name_offset + sum(len(p.name) + 1 for p in pieces)
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

    write_scm(scm_filepath, modl, total_bone_data, bone_name_data, total_vert_data, total_face_data)
    print(f"Created SCM: {scm_filepath} ({len(pieces)} bones, {vert_counter} verts, {len(total_face_data)//3} tris)")
    return pieces

# ---------------------------------------------------------------------------
# SCA Generator
# ---------------------------------------------------------------------------
def euler_to_quat(rot_x, rot_y, rot_z):
    cx = math.cos(rot_x * 0.5)
    sx = math.sin(rot_x * 0.5)
    cy = math.cos(rot_y * 0.5)
    sy = math.sin(rot_y * 0.5)
    cz = math.cos(rot_z * 0.5)
    sz = math.sin(rot_z * 0.5)

    qw = cx * cy * cz + sx * sy * sz
    qx = sx * cy * cz - cx * sy * sz
    qy = cx * sy * cz + sx * cy * sz
    qz = cx * cy * sz - sx * sy * cz
    return (qw, qx, qy, qz)

def save_sca_file(filepath, num_frames, duration, piece_names, parent_indices, frames_data):
    names_str = chr(0).join(piece_names) + chr(0)
    num_bones = len(piece_names)
    frame_size = 8 + num_bones * 28

    with open(filepath, 'w+b') as f:
        f.write(b'\x00' * 36)

        pad_file(f, b'NAME')
        names_off = f.tell()
        f.write(names_str.encode('ascii'))

        pad_file(f, b'LINK')
        links_off = f.tell()
        f.write(struct.pack(f'<{num_bones}i', *parent_indices))

        pad_file(f, b'DATA')
        anim_data_off = f.tell()
        f.write(struct.pack('<7f', 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0))
        fmt = '<' + f'fi{num_bones * 7}f' * num_frames
        f.write(struct.pack(fmt, *frames_data))

        f.seek(0)
        header = [
            b'ANIM', 5,
            num_frames, duration, num_bones,
            names_off, links_off, anim_data_off, frame_size
        ]
        f.write(struct.pack('<4s2If5I', *header))

    file_size = os.path.getsize(filepath)
    expected_size = anim_data_off + 28 + (num_frames * frame_size)
    assert file_size == expected_size, f"Size mismatch for {filepath}: got {file_size}, expected {expected_size}"
    print(f"Created SCA: {filepath} ({num_frames} frames, {duration:.2f}s, size={file_size} bytes - OK)")

# ---------------------------------------------------------------------------
# XACT Audio Engine Bank Generator
# ---------------------------------------------------------------------------
p_xsb = r'C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\ExperimentalsExpanded\sounds\PSB1301SB.xsb'
with open(p_xsb, 'rb') as f:
    sb_tmpl = bytearray(f.read())

def make_crc16_table():
    tbl = []
    for i in range(256):
        curr = i
        for _ in range(8):
            if curr & 1:
                curr = (curr >> 1) ^ 0x8408
            else:
                curr = curr >> 1
        tbl.append(curr)
    return tbl

CRC16_TABLE = make_crc16_table()

def calc_xact_crc(data):
    crc = 0xFFFF
    for b in data:
        idx = (crc ^ b) & 0xFF
        crc = (crc >> 8) ^ CRC16_TABLE[idx]
    return (~crc) & 0xFFFF

def build_xact_bank(soundbank_name, wavebank_name, cue_name, wav_bytes):
    with wave.open(io.BytesIO(wav_bytes), 'rb') as w:
        wav_pcm = w.readframes(w.getnframes())
        num_samples = w.getnframes()
        rate = w.getframerate()
        channels = w.getnchannels()
        bits = w.getsampwidth() * 8
        
    pcm_len = len(wav_pcm)
    pad_bytes = (4 - (pcm_len % 4)) % 4
    wav_pcm_padded = wav_pcm + (b'\x00' * pad_bytes)
    seg4_len = len(wav_pcm_padded)
    
    wb_header = struct.pack('<4sII10I',
        b'WBND', 43, 42,
        52, 96,
        148, 24,
        172, 0,
        0, 0,
        172, seg4_len
    )
    wb_name_64 = wavebank_name.encode('ascii')[:63].ljust(64, b'\x00')
    seg0 = struct.pack('<II64sIIIIQ',
        524288, 1, wb_name_64,
        24, 64, 4, 0, 132060651052792696
    )
    wFormatTag = 0
    nChannels = channels
    nSamplesPerSec = rate
    wBlockAlign = channels * (bits // 8)
    wBitsPerSample = 1 if bits == 16 else 0
    fmt = (wFormatTag & 0x3) | ((nChannels & 0x7) << 2) | ((nSamplesPerSec & 0x3FFFF) << 5) | ((wBlockAlign & 0xFF) << 23) | ((wBitsPerSample & 0x1) << 31)
    dwFlagsAndDuration = (num_samples << 4) & 0xFFFFFFFF
    seg1 = struct.pack('<6I', dwFlagsAndDuration, fmt, 0, pcm_len, 0, 0)
    xwb_bytes = wb_header + seg0 + seg1 + wav_pcm_padded
    
    sb = bytearray(sb_tmpl[:277])
    sb_name_64 = soundbank_name.encode('ascii')[:63].ljust(64, b'\x00')
    sb[0x4a : 0x4a + 64] = sb_name_64
    sb[0x8a : 0x8a + 64] = wb_name_64
    sb[229] = 0  # loopCount = 0 (one-shot)
    for i in range(16):
        struct.pack_into('<H', sb, 239 + i*2, 0)
    cue_bytes = cue_name.encode('ascii') + b'\x00'
    sb.extend(cue_bytes)
    struct.pack_into('<H', sb, 0x1e, len(cue_bytes))
    crc = calc_xact_crc(sb[18:])
    struct.pack_into('<H', sb, 8, crc)
    return bytes(xwb_bytes), bytes(sb)

# Generate Audio Banks for New Units
audio_to_generate = [
    ('Raptor_Artillery', 'Raptor_Artillery', 'Attack', 'sounds/raptors/bugarty.wav', 'bugarty.wav'),
    ('Raptor_Heavy_Attack', 'Raptor_Heavy_Attack', 'Attack', 'sounds/raptors/smallraptorattack.wav', 'smallraptorattack.wav'),
    ('Raptor_Spores', 'Raptor_Spores', 'Attack', 'sounds/weapons-mult/spore_xl.wav', 'spore_xl.wav'),
    ('Raptor_Bio_Bomb', 'Raptor_Bio_Bomb', 'Attack', 'sounds/bombs/alien_bombrel.wav', 'alien_bombrel.wav'),
    ('Raptor_Queen_Roar', 'Raptor_Queen_Roar', 'Attack', 'sounds/raptors/bigraptorroar.wav', 'bigraptorroar.wav'),
    ('Raptor_Queen_Cleave', 'Raptor_Queen_Cleave', 'Attack', 'sounds/raptors/bigraptorbreath.wav', 'bigraptorbreath.wav'),
    ('Raptor_Dodo_Hiss', 'Raptor_Dodo_Hiss', 'Attack', 'sounds/raptors/smallraptorhiss.wav', 'smallraptorhiss.wav'),
]

for sb_name, wb_name, cue, bar_path, fname in audio_to_generate:
    wdata = get_bar_file(bar_path)
    if wdata:
        xwb, xsb = build_xact_bank(sb_name, wb_name, cue, wdata)
        with open(os.path.join(sounds_dir, f'{sb_name}.xwb'), 'wb') as f:
            f.write(xwb)
        with open(os.path.join(sounds_dir, f'{sb_name}.xsb'), 'wb') as f:
            f.write(xsb)
        with open(os.path.join(raptor_sounds_dir, fname), 'wb') as f:
            f.write(wdata)
        print(f"Generated Audio Bank: {sb_name}")

print("\n--- Pipeline Initialization Complete ---")
