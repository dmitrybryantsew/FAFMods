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

# ===========================================================================
# 1. NEW PROJECTILES
# ===========================================================================
# Bio Bomb (Gravity ordinance for Air Bomber)
bp_biobomb = """ProjectileBlueprint {
    Audio = {
        Impact = Sound {
            Bank = 'Impacts',
            Cue = 'X_Impact_Land_Gen_Seraphim',
            LodCutoff = 'Weapon_LodCutoff',
        },
    },
    Categories = {
        'RAPTOR',
        'PROJECTILE',
        'INDIRECTFIRE',
    },
    Display = {
        ImpactEffects = {
            Type = 'Large01',
        },
        Mesh = {
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0104/XRA0104_Albedo.dds',
                    LODCutoff = 150,
                    MeshName = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_lod0.scm',
                    ShaderName = 'TMeshNoLighting',
                },
            },
        },
        StrategicIconSize = 2,
        UniformScale = 4.0,
    },
    General = {
        Category = 'Bomb',
        EntityCategory = {
            'RAPTOR',
            'PROJECTILE',
            'INDIRECTFIRE',
        },
        Faction = 'Cybran',
        Weapon = 'Bio Bomb',
    },
    Interface = {
        HelpText = 0,
    },
    Physics = {
        DestroyOnWater = true,
        InitialSpeed = 0,
        Lifetime = 10,
        MaxSpeed = 30,
        RealisticOrdinance = true,
        RotationalVelocity = 180,
        TurnRate = 0,
        VelocityAlign = true,
    },
}
"""
with open(os.path.join(dir_proj_biobomb, "XRA_BioBomb01_proj.bp"), "w") as f:
    f.write(bp_biobomb)

script_biobomb = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile

XRA_BioBomb01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/default_polytrail_01_emit.bp',
    PolyTrailOffset = 0,

    OnImpact = function(self, targetType, targetEntity)
        local army = self.Army
        CreateEmitterAtEntity(self, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp'):ScaleEmitter(2.0)
        CreateEmitterAtEntity(self, army, '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp'):ScaleEmitter(1.5)
        CreateEmitterAtEntity(self, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp'):ScaleEmitter(2.0)
        SinglePolyTrailProjectile.OnImpact(self, targetType, targetEntity)
    end,
}
TypeClass = XRA_BioBomb01
"""
with open(os.path.join(dir_proj_biobomb, "XRA_BioBomb01_script.lua"), "w") as f:
    f.write(script_biobomb)

# Queen Titanic Plasma Projectile
bp_queenplasma = """ProjectileBlueprint {
    Audio = {
        Impact = Sound {
            Bank = 'Impacts',
            Cue = 'Cybran_Expl_Med_Impact',
            LodCutoff = 'Weapon_LodCutoff',
        },
    },
    Categories = {
        'RAPTOR',
        'PROJECTILE',
        'DIRECTFIRE',
    },
    Display = {
        CameraShake = {
            Radius = 15,
            Recoil = 0.5,
            Speed = 0.25,
        },
        ImpactEffects = {
            Type = 'Large01',
        },
        Mesh = {
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0401/XRA0401_Albedo.dds',
                    LODCutoff = 200,
                    MeshName = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_lod0.scm',
                    ShaderName = 'TMeshNoLighting',
                },
            },
        },
        StrategicIconSize = 3,
        UniformScale = 7.0,
    },
    General = {
        Category = 'Direct Fire',
        EntityCategory = {
            'RAPTOR',
            'PROJECTILE',
            'DIRECTFIRE',
        },
        Faction = 'Cybran',
        Weapon = 'Titanic Roar Plasma',
    },
    Interface = {
        HelpText = 0,
    },
    Physics = {
        Acceleration = 0,
        DestroyOnWater = true,
        InitialSpeed = 24,
        Lifetime = 4.0,
        MaxSpeed = 24,
        RotationalVelocity = 300,
        UseGravity = false,
        VelocityAlign = true,
    },
}
"""
with open(os.path.join(dir_proj_queenplasma, "XRA_QueenPlasma01_proj.bp"), "w") as f:
    f.write(bp_queenplasma)

script_queenplasma = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile

XRA_QueenPlasma01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/default_polytrail_01_emit.bp',
    PolyTrailOffset = 0,

    OnImpact = function(self, targetType, targetEntity)
        local army = self.Army
        CreateEmitterAtEntity(self, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp'):ScaleEmitter(3.5)
        CreateEmitterAtEntity(self, army, '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp'):ScaleEmitter(2.5)
        CreateEmitterAtEntity(self, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp'):ScaleEmitter(4.0)
        SinglePolyTrailProjectile.OnImpact(self, targetType, targetEntity)
    end,
}
TypeClass = XRA_QueenPlasma01
"""
with open(os.path.join(dir_proj_queenplasma, "XRA_QueenPlasma01_script.lua"), "w") as f:
    f.write(script_queenplasma)

print("Created Projectiles: XRA_BioBomb01 and XRA_QueenPlasma01")

# ===========================================================================
# 2. XRA0103: KAMIKAZE ACID TICK (DODO)
# ===========================================================================
print("\n--- Porting XRA0103 (Kamikaze Acid Tick) ---")
s3o_dodo = get_bar_file('objects3d/raptors/raptor_dodo.s3o')
pieces_dodo = convert_s3o_to_scm(s3o_dodo, os.path.join(dir_xra0103, "XRA0103_lod0.scm"))
names_dodo = [p.name for p in pieces_dodo]
parents_dodo = [p.parent_idx for p in pieces_dodo]

# Textures
alb_dodo = get_bar_file('unittextures/chicken_yellow_m_color.dds') or get_bar_file('unittextures/chicken_acidgreen_m_color.dds')
with open(os.path.join(dir_xra0103, "XRA0103_Albedo.dds"), "wb") as f:
    f.write(alb_dodo)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0103, "XRA0103_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0103, "XRA0103_SpecTeam.dds"))

# Icon
ico_dodo = get_bar_file('unitpics/raptors/raptor_dodo1.dds')
with open(os.path.join(dir_xra0103, "XRA0103_icon.dds"), "wb") as f:
    f.write(ico_dodo)
with open(os.path.join(icons_dir, "xra0103_icon.dds"), "wb") as f:
    f.write(ico_dodo)

# Walk Animation (Rapid Skitter Sprint)
num_frames = 20
dur = 0.5
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    p = 2.0 * math.pi * t
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_dodo}
    if f_idx == 0:
        pos["base"] = (0.0, 0.0, 0.0)
    
    # Bipedal run cycle
    rot["lthigh"] = (math.sin(p) * math.radians(35.0), 0, 0)
    rot["lknee"] = (-max(0.0, -math.sin(p)) * math.radians(45.0), 0, 0)
    rot["rthigh"] = (-math.sin(p) * math.radians(35.0), 0, 0)
    rot["rknee"] = (-max(0.0, math.sin(p)) * math.radians(45.0), 0, 0)
    
    # Abdomen/Body jiggle
    rot["body"] = (math.sin(p * 2.0) * math.radians(6.0), 0, 0)
    rot["tail"] = (-math.sin(p * 2.0) * math.radians(10.0), 0, 0)
    
    time_sec = t * dur
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_dodo):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0103, "XRA0103_Awalk.sca"), num_frames, dur, names_dodo, parents_dodo, frames)

# Death Collapse
num_frames = 16
dur = 0.6
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    time_sec = t * dur
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_dodo}
    rot["lthigh"] = (math.radians(30.0) * t, 0, math.radians(25.0) * t)
    rot["rthigh"] = (math.radians(30.0) * t, 0, -math.radians(25.0) * t)
    rot["body"] = (math.radians(-20.0) * t, 0, 0)
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_dodo):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0103, "XRA0103_Adeath01.sca"), num_frames, dur, names_dodo, parents_dodo, frames)

bp_xra0103 = """UnitBlueprint {
    Audio = {
        Destroyed = Sound {
            Bank = 'Raptor_Bio_Bomb',
            Cue = 'Attack',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Killed = Sound {
            Bank = 'Raptor_Bio_Bomb',
            Cue = 'Attack',
            LodCutoff = 'UnitMove_LodCutoff',
        },
    },
    Buffs = {
        Regen = {
            Level1 = 1,
            Level2 = 2,
            Level3 = 3,
        },
    },
    BuildIconSortPriority = 25,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYRAPTORHIVE',
        'BUILTBYTIER1FACTORY',
        'BUILTBYTIER2FACTORY',
        'CYBRAN',
        'RAPTOR',
        'MOBILE',
        'LAND',
        'TECH1',
        'KAMIKAZE',
        'DIRECTFIRE',
        'AMPHIBIOUS',
        'VISIBLETORECON',
        'RECLAIMABLE',
    },
    CollisionOffsetY = 0,
    CollisionOffsetZ = 0,
    Defense = {
        ArmorType = 'Normal',
        Health = 110,
        MaxHealth = 110,
        RegenRate = 0.5,
    },
    Description = '<LOC xra0103_desc>Suicide Kamikaze Acid Bomb',
    Display = {
        AnimationWalk = '/mods/RaptorFaction/units/XRA0103/XRA0103_Awalk.sca',
        AnimationWalkRate = 2.4,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0103/XRA0103_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0103/XRA0103_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0103/XRA0103_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0103/XRA0103_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.7,
    },
    Economy = {
        BuildCostEnergy = 350,
        BuildCostMass = 45,
        BuildTime = 160,
    },
    General = {
        Category = 'Direct Fire',
        Classification = 'RULEUC_MilitaryVehicle',
        CommandCaps = {
            RULEUCC_Attack = true,
            RULEUCC_CallCycle = false,
            RULEUCC_Capture = false,
            RULEUCC_Guard = true,
            RULEUCC_Move = true,
            RULEUCC_Nuke = false,
            RULEUCC_Patrol = true,
            RULEUCC_Reclaim = false,
            RULEUCC_Repair = false,
            RULEUCC_RetaliateToggle = true,
            RULEUCC_Stop = true,
            RULEUCC_Transport = false,
        },
        FactionName = 'Raptor',
        Icon = 'land',
        UnitName = '<LOC xra0103_name>Volatile Acid Tick',
    },
    Intel = {
        VisionRadius = 18,
    },
    Interface = {
        HelpText = '<LOC xra0103_help>High-speed suicide kamikaze insect that detonates in a violent acid explosion on contact.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.55,
    LifeBarSize = 0.65,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 5.0,
        MaxBrake = 5.0,
        MaxSpeed = 5.2,
        MaxSpeedReverse = 0,
        MaxSteerForce = 15,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        RotateOnSpot = true,
        RotateOnSpotThreshold = 0.1,
        TurnRadius = 0,
        TurnRate = 220,
    },
    SelectionSizeX = 0.45,
    SelectionSizeZ = 0.6,
    SelectionThickness = 0.65,
    SizeX = 0.55,
    SizeY = 0.6,
    SizeZ = 0.85,
    StrategicIconName = 'icon_land1_bomb',
    StrategicIconSortPriority = 135,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            CollideFriendly = false,
            Damage = 750,
            DamageFriendly = true,
            DamageRadius = 3.5,
            DamageType = 'Normal',
            DisplayName = 'Suicide Acid Detonation',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 180,
            Label = 'Suicide',
            MaxRadius = 2.0,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1,
            SlavedToBody = true,
            TargetCheckInterval = 0.1,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'MOBILE',
                'STRUCTURE DEFENSE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            RackBones = {
                {
                    MuzzleBones = {
                        0,
                    },
                    RackBone = 0,
                },
            },
            RackFireTogether = false,
            RackRecoilDistance = 0,
            RackReloadTimeout = 10,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            Turreted = false,
            WeaponCategory = 'Kamikaze',
        },
    },
}
"""
with open(os.path.join(dir_xra0103, "XRA0103_unit.bp"), "w") as f:
    f.write(bp_xra0103)

script_xra0103 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local Weapon = import('/lua/sim/weapon.lua').Weapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class KamikazeWeapon : Weapon
local KamikazeWeapon = ClassWeapon(Weapon) {
    OnFire = function(self)
        local myUnit = self.unit
        local army = myUnit.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(myUnit, army, emit):ScaleEmitter(2.5)
        end
        myUnit:Kill()
    end,
}

---@class XRA0103 : CWalkingLandUnit
XRA0103 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Suicide = ClassWeapon(KamikazeWeapon) {},
    },

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.5)
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.5)
        end
    end,
}

TypeClass = XRA0103
"""
with open(os.path.join(dir_xra0103, "XRA0103_script.lua"), "w") as f:
    f.write(script_xra0103)

print("Ported XRA0103 Kamikaze Acid Tick successfully.")

# ===========================================================================
# 3. XRA0104: BIOLOGICAL ACID BOMBER
# ===========================================================================
print("\n--- Porting XRA0104 (Bio-Acid Carpet Bomber) ---")
s3o_bomber = get_bar_file('objects3d/raptors/raptoracidbomber.s3o')
pieces_bomber = convert_s3o_to_scm(s3o_bomber, os.path.join(dir_xra0104, "XRA0104_lod0.scm"))
names_bomber = [p.name for p in pieces_bomber]
parents_bomber = [p.parent_idx for p in pieces_bomber]

alb_bomber = get_bar_file('unittextures/chicken_acidgreen_l_color.dds')
with open(os.path.join(dir_xra0104, "XRA0104_Albedo.dds"), "wb") as f:
    f.write(alb_bomber)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0104, "XRA0104_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0104, "XRA0104_SpecTeam.dds"))

ico_bomber = get_bar_file('unitpics/raptors/raptoracidbomber.dds')
with open(os.path.join(dir_xra0104, "XRA0104_icon.dds"), "wb") as f:
    f.write(ico_bomber)
with open(os.path.join(icons_dir, "xra0104_icon.dds"), "wb") as f:
    f.write(ico_bomber)

# Continuous Wing Flap
num_frames = 20
dur = 0.45
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    p = 2.0 * math.pi * t
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_bomber}
    
    # Wing roll around Z
    flap_inner = math.sin(p) * math.radians(32.0)
    flap_outer = math.sin(p - 0.5) * math.radians(45.0)
    rot["liwing"] = (0, 0, flap_inner)
    rot["riwing"] = (0, 0, -flap_inner)
    rot["lowing"] = (0, 0, flap_outer)
    rot["rowing"] = (0, 0, -flap_outer)
    
    # Body bob & pitch
    body_pitch = math.sin(p) * math.radians(5.0)
    rot["body"] = (body_pitch, 0, 0)
    rot["tail"] = (-body_pitch * 1.5, 0, 0)
    
    time_sec = t * dur
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_bomber):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0104, "XRA0104_Afly.sca"), num_frames, dur, names_bomber, parents_bomber, frames)

# Death Tumble
num_frames = 24
dur = 0.8
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    time_sec = t * dur
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_bomber}
    rot["body"] = (math.radians(45.0) * t, math.radians(90.0) * t, 0)
    rot["liwing"] = (0, 0, math.radians(60.0) * t)
    rot["riwing"] = (0, 0, -math.radians(60.0) * t)
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_bomber):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0104, "XRA0104_Adeath01.sca"), num_frames, dur, names_bomber, parents_bomber, frames)

bp_xra0104 = """UnitBlueprint {
    Air = {
        AutoLandTime = 1,
        BankFactor = 2.5,
        BreakOffDistance = 30,
        BreakOffTrigger = 20,
        CanFly = true,
        CombatTurnSpeed = 1.5,
        KMove = 1,
        KTurn = 1,
        LiftFactor = 10,
        MaxAirspeed = 11.0,
        MinAirspeed = 8.0,
        StartTurnDistance = 10,
        TurnSpeed = 1.5,
    },
    Audio = {
        Destroyed = Sound {
            Bank = 'Raptor_Flyer_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Killed = Sound {
            Bank = 'Raptor_Flyer_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
    },
    Buffs = {
        Regen = {
            Level1 = 1,
            Level2 = 2,
            Level3 = 3,
        },
    },
    BuildIconSortPriority = 30,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYRAPTORHIVE',
        'BUILTBYTIER1FACTORY',
        'BUILTBYTIER2FACTORY',
        'CYBRAN',
        'RAPTOR',
        'MOBILE',
        'AIR',
        'TECH1',
        'BOMBER',
        'HIGHALTAIR',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYINDIRECTFIRE',
    },
    CollisionOffsetY = 0,
    Defense = {
        ArmorType = 'Light',
        Health = 220,
        MaxHealth = 220,
        RegenRate = 0.5,
    },
    Description = '<LOC xra0104_desc>Biological Acid Carpet Bomber',
    Display = {
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0104/XRA0104_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0104/XRA0104_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0104/XRA0104_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0104/XRA0104_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.5,
    },
    Economy = {
        BuildCostEnergy = 2250,
        BuildCostMass = 105,
        BuildTime = 700,
    },
    General = {
        Category = 'Bomber',
        Classification = 'RULEUC_MilitaryAircraft',
        CommandCaps = {
            RULEUCC_Attack = true,
            RULEUCC_CallCycle = false,
            RULEUCC_Capture = false,
            RULEUCC_Dock = true,
            RULEUCC_Guard = true,
            RULEUCC_Move = true,
            RULEUCC_Nuke = false,
            RULEUCC_Patrol = true,
            RULEUCC_Reclaim = false,
            RULEUCC_Repair = false,
            RULEUCC_RetaliateToggle = true,
            RULEUCC_Stop = true,
            RULEUCC_Transport = false,
        },
        FactionName = 'Raptor',
        Icon = 'air',
        UnitName = '<LOC xra0104_name>Bio-Acid Bomber',
    },
    Intel = {
        VisionRadius = 32,
    },
    Interface = {
        HelpText = '<LOC xra0104_help>Aerial biological bomber that releases corrosive bile clusters over ground positions.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.45,
    LifeBarSize = 1.2,
    Physics = {
        BankingSlope = 0.5,
        BuildOnLayerCaps = {
            LAYER_Air = true,
        },
        Elevation = 10.0,
        FuelRechargeRate = 0,
        FuelUseTime = 0,
        MaxSpeed = 11.0,
        MotionType = 'RULEUMT_Air',
    },
    SelectionSizeX = 1.4,
    SelectionSizeZ = 1.1,
    SelectionThickness = 0.5,
    SizeSphere = 1.0,
    SizeX = 1.6,
    SizeY = 0.45,
    SizeZ = 1.5,
    StrategicIconName = 'icon_bomber1_directfire',
    StrategicIconSortPriority = 75,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            AutoInitiateAttackCommand = true,
            BallisticArc = 'RULEUBA_None',
            BombDropThreshold = 3,
            Damage = 240,
            DamageFriendly = false,
            DamageRadius = 2.5,
            DamageType = 'Normal',
            DisplayName = 'Bio-Acid Cluster Bomb',
            FireTargetLayerCapsTable = {
                Air = 'Land|Water|Seabed',
            },
            FiringRandomness = 0.5,
            FiringTolerance = 3,
            Label = 'Bomb',
            MaxRadius = 40,
            MuzzleSalvoDelay = 0.15,
            MuzzleSalvoSize = 3,
            MuzzleVelocity = 0,
            NeedToComputeBombDrop = true,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_BioBomb01/XRA_BioBomb01_proj.bp',
            ProjectilesPerOnFire = 3,
            RackBones = {
                {
                    MuzzleBones = {
                        'head',
                    },
                    RackBone = 'head',
                },
            },
            RackFireTogether = false,
            RackRecoilDistance = 0,
            RackReloadTimeout = 10,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RateOfFire = 0.2,
            TargetCheckInterval = 1,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'STRUCTURE DEFENSE',
                'TECH3 MOBILE',
                'TECH2 MOBILE',
                'TECH1 MOBILE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            TrackingRadius = 1.15,
            TurretDualManipulators = false,
            Turreted = false,
            WeaponCategory = 'Bomb',
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Bio_Bomb',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
        },
        {
            AboveWaterTargetsOnly = true,
            Damage = 100,
            DamageFriendly = true,
            DamageRadius = 1,
            DamageType = 'Normal',
            DisplayName = 'Air Crash',
            DummyWeapon = true,
            FiringTolerance = 2,
            Label = 'DeathImpact',
            WeaponCategory = 'Death',
        },
    },
}
"""
with open(os.path.join(dir_xra0104, "XRA0104_unit.bp"), "w") as f:
    f.write(bp_xra0104)

script_xra0104 = """local CAirUnit = import('/lua/cybranunits.lua').CAirUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class XRA0104 : CAirUnit
XRA0104 = ClassUnit(CAirUnit) {
    Weapons = {
        Bomb = ClassWeapon(DefaultProjectileWeapon) {},
    },

    OnCreate = function(self)
        CAirUnit.OnCreate(self)
        local flyAnim = CreateAnimator(self)
        flyAnim:PlayAnim('/mods/RaptorFaction/units/XRA0104/XRA0104_Afly.sca', true)
        flyAnim:SetRate(2.2)
        self.FlyAnim = flyAnim
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.5)
        end
        CAirUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.5)
        end
    end,
}

TypeClass = XRA0104
"""
with open(os.path.join(dir_xra0104, "XRA0104_script.lua"), "w") as f:
    f.write(script_xra0104)

print("Ported XRA0104 Bio-Acid Bomber successfully.")

# ===========================================================================
# 4. XRA0109: BIO-WEAVER (BUILDER & HEALER) - FULL UPGRADE
# ===========================================================================
print("\n--- Upgrading XRA0109 (Bio-Weaver Builder & Field Healer) ---")
s3o_weaver = get_bar_file('objects3d/raptors/raptorhealer1.s3o')
pieces_weaver = convert_s3o_to_scm(s3o_weaver, os.path.join(dir_xra0109, "XRA0109_lod0.scm"))
names_weaver = [p.name for p in pieces_weaver]
parents_weaver = [p.parent_idx for p in pieces_weaver]

alb_weaver = get_bar_file('unittextures/chicken_white_m_color.dds') or get_bar_file('unittextures/chicken_aqua_m_color.dds')
with open(os.path.join(dir_xra0109, "XRA0109_Albedo.dds"), "wb") as f:
    f.write(alb_weaver)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0109, "XRA0109_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0109, "XRA0109_SpecTeam.dds"))

ico_weaver = get_bar_file('unitpics/raptors/raptorhealer.dds')
with open(os.path.join(dir_xra0109, "XRA0109_icon.dds"), "wb") as f:
    f.write(ico_weaver)
with open(os.path.join(icons_dir, "xra0109_icon.dds"), "wb") as f:
    f.write(ico_weaver)

# Walk Animation
num_frames = 24
dur = 0.6
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    p = 2.0 * math.pi * t
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_weaver}
    rot["lthigh"] = (math.sin(p) * math.radians(28.0), 0, 0)
    rot["lknee"] = (-max(0.0, -math.sin(p)) * math.radians(35.0), 0, 0)
    rot["rthigh"] = (-math.sin(p) * math.radians(28.0), 0, 0)
    rot["rknee"] = (-max(0.0, math.sin(p)) * math.radians(35.0), 0, 0)
    rot["body"] = (math.sin(p * 2.0) * math.radians(4.0), 0, 0)
    rot["lupperarm"] = (math.radians(20.0) + math.sin(p) * math.radians(10.0), 0, 0)
    rot["rupperarm"] = (math.radians(20.0) - math.sin(p) * math.radians(10.0), 0, 0)
    time_sec = t * dur
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_weaver):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0109, "XRA0109_Awalk.sca"), num_frames, dur, names_weaver, parents_weaver, frames)

# Build Animation (Weaving appendages)
num_frames = 20
dur = 1.0
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    p = 2.0 * math.pi * t
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_weaver}
    rot["lupperarm"] = (math.sin(p) * math.radians(25.0), math.cos(p) * math.radians(15.0), 0)
    rot["lforearm"] = (math.cos(p) * math.radians(20.0), 0, 0)
    rot["rupperarm"] = (-math.sin(p) * math.radians(25.0), -math.cos(p) * math.radians(15.0), 0)
    rot["rforearm"] = (-math.cos(p) * math.radians(20.0), 0, 0)
    time_sec = t * dur
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_weaver):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0109, "XRA0109_Abuild.sca"), num_frames, dur, names_weaver, parents_weaver, frames)

# Death Collapse
num_frames = 16
dur = 0.6
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    time_sec = t * dur
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_weaver}
    rot["lthigh"] = (math.radians(35.0) * t, 0, math.radians(20.0) * t)
    rot["rthigh"] = (math.radians(35.0) * t, 0, -math.radians(20.0) * t)
    rot["body"] = (math.radians(-25.0) * t, 0, 0)
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_weaver):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0109, "XRA0109_Adeath01.sca"), num_frames, dur, names_weaver, parents_weaver, frames)

bp_xra0109 = """UnitBlueprint {
    Audio = {
        Construct = Sound {
            Bank = 'Raptor_Attack',
            Cue = 'Attack',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Destroyed = Sound {
            Bank = 'Raptor_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Killed = Sound {
            Bank = 'Raptor_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
    },
    Buffs = {
        Regen = {
            Level1 = 2,
            Level2 = 4,
            Level3 = 6,
        },
    },
    BuildIconSortPriority = 10,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYRAPTORHIVE',
        'BUILTBYTIER1FACTORY',
        'BUILTBYTIER2FACTORY',
        'CYBRAN',
        'RAPTOR',
        'MOBILE',
        'LAND',
        'TECH1',
        'CONSTRUCTION',
        'ENGINEER',
        'REPAIR',
        'RECLAIM',
        'AMPHIBIOUS',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'PATROLHELPER',
    },
    CollisionOffsetY = 0,
    Defense = {
        ArmorType = 'Normal',
        Health = 260,
        MaxHealth = 260,
        RegenRate = 2.0,
    },
    Description = '<LOC xra0109_desc>Mobile Engineer & Biological Weaver',
    Display = {
        AnimationWalk = '/mods/RaptorFaction/units/XRA0109/XRA0109_Awalk.sca',
        AnimationWalkRate = 2.2,
        AnimationBuild = '/mods/RaptorFaction/units/XRA0109/XRA0109_Abuild.sca',
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0109/XRA0109_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0109/XRA0109_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0109/XRA0109_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0109/XRA0109_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.85,
    },
    Economy = {
        BuildCostEnergy = 280,
        BuildCostMass = 60,
        BuildRate = 12,
        BuildTime = 280,
        BuildableCategory = {
            'BUILTBYTIER1ENGINEER RAPTOR',
            'RAPTOR STRUCTURE',
            'RAPTOR EXPERIMENTAL',
        },
        MaxBuildDistance = 6,
    },
    General = {
        BuildBones = {
            AimBone = 'head',
            BuildEffectBones = {
                'lblade',
                'rblade',
            },
            PitchBone = 'head',
            YawBone = 'head',
        },
        Category = 'Construction',
        Classification = 'RULEUC_Engineer',
        CommandCaps = {
            RULEUCC_Attack = false,
            RULEUCC_CallCycle = false,
            RULEUCC_Capture = false,
            RULEUCC_Guard = true,
            RULEUCC_Move = true,
            RULEUCC_Nuke = false,
            RULEUCC_Patrol = true,
            RULEUCC_Reclaim = true,
            RULEUCC_Repair = true,
            RULEUCC_RetaliateToggle = false,
            RULEUCC_Stop = true,
            RULEUCC_Transport = false,
        },
        ConstructionBar = true,
        FactionName = 'Raptor',
        Icon = 'land',
        SelectionPriority = 3,
        UnitName = '<LOC xra0109_name>Bio-Weaver',
    },
    Intel = {
        VisionRadius = 20,
    },
    Interface = {
        HelpText = '<LOC xra0109_help>Mobile builder and repair weaver that secretes organic resin structures and passively regenerates nearby wounded raptors.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.5,
    LifeBarSize = 0.65,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 3.8,
        MaxBrake = 3.8,
        MaxSpeed = 3.8,
        MaxSpeedReverse = 0,
        MaxSteerForce = 15,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        RotateOnSpot = true,
        RotateOnSpotThreshold = 0.1,
        TurnRadius = 0,
        TurnRate = 200,
    },
    SelectionSizeX = 0.5,
    SelectionSizeZ = 0.65,
    SelectionThickness = 0.6,
    SizeX = 0.65,
    SizeY = 0.55,
    SizeZ = 0.9,
    StrategicIconName = 'icon_land1_engineer',
    StrategicIconSortPriority = 85,
}
"""
with open(os.path.join(dir_xra0109, "XRA0109_unit.bp"), "w") as f:
    f.write(bp_xra0109)

script_xra0109 = """local ConstructionUnit = import('/lua/defaultunits.lua').ConstructionUnit

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class XRA0109 : ConstructionUnit
XRA0109 = ClassUnit(ConstructionUnit) {
    OnCreate = function(self)
        ConstructionUnit.OnCreate(self)
        self:ForkThread(self.HealerAuraThread)
    end,

    HealerAuraThread = function(self)
        while not self.Dead do
            WaitSeconds(2.0)
            local pos = self:GetPosition()
            local units = self:GetAIBrain():GetUnitsAroundPoint(categories.RAPTOR * categories.MOBILE, pos, 14, 'Ally')
            for _, u in units do
                if not u.Dead and u:GetHealth() < u:GetMaxHealth() then
                    u:AdjustHealth(self, 14)
                end
            end
        end
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.2)
        end
        ConstructionUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.2)
        end
    end,
}

TypeClass = XRA0109
"""
with open(os.path.join(dir_xra0109, "XRA0109_script.lua"), "w") as f:
    f.write(script_xra0109)

print("Upgraded XRA0109 Bio-Weaver successfully.")

# ===========================================================================
# 5. XRA0202: MOBILE BIO-ARTILLERY (MORTAR BUG)
# ===========================================================================
print("\n--- Porting XRA0202 (Mobile Bio-Artillery) ---")
s3o_arty = get_bar_file('objects3d/raptors/raptor_artillery_v2.s3o')
pieces_arty = convert_s3o_to_scm(s3o_arty, os.path.join(dir_xra0202, "XRA0202_lod0.scm"))
names_arty = [p.name for p in pieces_arty]
parents_arty = [p.parent_idx for p in pieces_arty]

alb_arty = get_bar_file('unittextures/chicken_darkgreen_l_color.dds') or get_bar_file('unittextures/chicken_acidgreen_l_color.dds')
with open(os.path.join(dir_xra0202, "XRA0202_Albedo.dds"), "wb") as f:
    f.write(alb_arty)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0202, "XRA0202_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0202, "XRA0202_SpecTeam.dds"))

ico_arty = get_bar_file('unitpics/raptors/raptorr1.dds')
with open(os.path.join(dir_xra0202, "XRA0202_icon.dds"), "wb") as f:
    f.write(ico_arty)
with open(os.path.join(icons_dir, "xra0202_icon.dds"), "wb") as f:
    f.write(ico_arty)

# 6-Legged Tripod Walk Cycle
num_frames = 24
dur = 0.9
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    phase_A = 2.0 * math.pi * t
    phase_B = phase_A + math.pi
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_arty}
    
    # Spine gentle breathing
    for i in range(1, 8):
        rot[f"thor{i}"] = (math.sin(phase_A - i * 0.3) * math.radians(1.2), 0, 0)
        
    # Tripod A
    for side, l_idx in [('l', 1), ('r', 2), ('l', 3)]:
        p = phase_A
        rot[f"thigh{l_idx}{side}"] = (math.sin(p) * math.radians(22.0), 0, math.sin(p) * math.radians(10.0))
        rot[f"leg{l_idx}{side}"] = (-max(0.0, -math.sin(p)) * math.radians(30.0), 0, 0)
        rot[f"foot{l_idx}{side}"] = (math.sin(p) * math.radians(12.0), 0, 0)
        
    # Tripod B
    for side, l_idx in [('r', 1), ('l', 2), ('r', 3)]:
        p = phase_B
        rot[f"thigh{l_idx}{side}"] = (math.sin(p) * math.radians(22.0), 0, math.sin(p) * math.radians(10.0))
        rot[f"leg{l_idx}{side}"] = (-max(0.0, -math.sin(p)) * math.radians(30.0), 0, 0)
        rot[f"foot{l_idx}{side}"] = (math.sin(p) * math.radians(12.0), 0, 0)

    time_sec = t * dur
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_arty):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0202, "XRA0202_Awalk.sca"), num_frames, dur, names_arty, parents_arty, frames)

# Mortar Recoil (Elevating base UP +25 deg, wings splay, tip heaves forward, tail never goes under terrain)
num_frames = 16
dur = 0.8
frames = []
thor_recoil = {
    'thor1': 16.0,
    'thor2': 10.0,
    'thor3': 6.0,
    'thor4': -3.0,
    'thor5': -6.0,
    'thor6': -4.0,
    'thor7': -5.0,
}
for f_idx in range(num_frames):
    t = f_idx / num_frames
    time_sec = t * dur
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_arty}
    curve = math.sin(math.pi * t)
    for b_name, deg in thor_recoil.items():
        rot[b_name] = (curve * math.radians(deg), 0, 0)
    rot['wingl'] = (0, curve * math.radians(25.0), 0)
    rot['wingr'] = (0, -curve * math.radians(25.0), 0)
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_arty):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0202, "XRA0202_Afire.sca"), num_frames, dur, names_arty, parents_arty, frames)

# Death Collapse
num_frames = 20
dur = 0.8
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    time_sec = t * dur
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_arty}
    for side in ['l', 'r']:
        sign = 1 if side == 'l' else -1
        for idx in [1, 2, 3]:
            rot[f"thigh{idx}{side}"] = (0, 0, sign * math.radians(35.0) * t)
    rot["torso"] = (math.radians(-15.0) * t, 0, 0)
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_arty):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0202, "XRA0202_Adeath01.sca"), num_frames, dur, names_arty, parents_arty, frames)

bp_xra0202 = """UnitBlueprint {
    Audio = {
        Destroyed = Sound {
            Bank = 'Raptor_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Killed = Sound {
            Bank = 'Raptor_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
    },
    Buffs = {
        Regen = {
            Level1 = 2,
            Level2 = 4,
            Level3 = 6,
        },
    },
    BuildIconSortPriority = 60,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYRAPTORHIVE',
        'BUILTBYTIER1FACTORY',
        'BUILTBYTIER2FACTORY',
        'BUILTBYTIER3FACTORY',
        'CYBRAN',
        'RAPTOR',
        'MOBILE',
        'LAND',
        'TECH2',
        'INDIRECTFIRE',
        'ARTILLERY',
        'AMPHIBIOUS',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYINDIRECTFIRE',
    },
    CollisionOffsetY = 0.3,
    CollisionOffsetZ = -0.4,
    Defense = {
        ArmorType = 'Normal',
        Health = 650,
        MaxHealth = 650,
        RegenRate = 1.0,
    },
    Description = '<LOC xra0202_desc>Mobile Bio-Artillery',
    Display = {
        AnimationWalk = '/mods/RaptorFaction/units/XRA0202/XRA0202_Awalk.sca',
        AnimationWalkRate = 1.2,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0202/XRA0202_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0202/XRA0202_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0202/XRA0202_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0202/XRA0202_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 1.1,
    },
    Economy = {
        BuildCostEnergy = 2000,
        BuildCostMass = 280,
        BuildTime = 1400,
    },
    General = {
        Category = 'Indirect Fire',
        Classification = 'RULEUC_MilitaryVehicle',
        CommandCaps = {
            RULEUCC_Attack = true,
            RULEUCC_CallCycle = false,
            RULEUCC_Capture = false,
            RULEUCC_Guard = true,
            RULEUCC_Move = true,
            RULEUCC_Nuke = false,
            RULEUCC_Patrol = true,
            RULEUCC_Reclaim = false,
            RULEUCC_Repair = false,
            RULEUCC_RetaliateToggle = true,
            RULEUCC_Stop = true,
            RULEUCC_Transport = false,
        },
        FactionName = 'Raptor',
        Icon = 'amph',
        UnitName = '<LOC xra0202_name>Bio-Mortar Bug',
    },
    Intel = {
        VisionRadius = 24,
    },
    Interface = {
        HelpText = '<LOC xra0202_help>Mobile indirect fire bio-mortar insect that launches heavy arcing corrosive bile over defenses.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.8,
    LifeBarSize = 1.2,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 2.5,
        MaxBrake = 2.5,
        MaxSpeed = 2.5,
        MaxSpeedReverse = 0,
        MaxSteerForce = 15,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        RotateOnSpot = true,
        RotateOnSpotThreshold = 0.1,
        TurnRadius = 0,
        TurnRate = 90,
    },
    SelectionSizeX = 0.9,
    SelectionSizeZ = 1.2,
    SelectionThickness = 0.5,
    SizeX = 1.6,
    SizeY = 1.3,
    SizeZ = 2.8,
    StrategicIconName = 'icon_land2_artillery',
    StrategicIconSortPriority = 115,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            ArtilleryShieldBlocks = true,
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Artillery',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            BallisticArc = 'RULEUBA_HighArc',
            CollideFriendly = false,
            Damage = 85,
            DamageFriendly = false,
            DamageRadius = 2.5,
            DamageType = 'Normal',
            DisplayName = 'Bio-Acid Mortar',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringRandomness = 0.8,
            FiringTolerance = 3,
            Label = 'MainGun',
            MaxRadius = 64,
            MinRadius = 8,
            MuzzleSalvoDelay = 0.18,
            MuzzleSalvoSize = 4,
            MuzzleVelocity = 22,
            MuzzleVelocityReduceDistance = 64,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_BioMortar01/XRA_BioMortar01_proj.bp',
            ProjectilesPerOnFire = 1,
            RackBones = {
                {
                    MuzzleBones = {
                        'flare',
                    },
                    RackBone = 'thor6',
                },
            },
            RackFireTogether = false,
            RackRecoilDistance = 0,
            RackReloadTimeout = 10,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RackSlavedToTurret = false,
            RangeCategory = 'UWRC_IndirectFire',
            RateOfFire = 0.2,
            RenderFireClock = true,
            TargetCheckInterval = 1,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'STRUCTURE DEFENSE',
                'TECH3 MOBILE',
                'TECH2 MOBILE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            TurretBoneMuzzle = 'flare',
            TurretBonePitch = 'thor6',
            TurretBoneYaw = 'torso',
            TurretDualManipulators = false,
            TurretPitch = 10,
            TurretPitchRange = 70,
            TurretPitchSpeed = 50,
            TurretYaw = 0,
            TurretYawRange = 180,
            TurretYawSpeed = 50,
            Turreted = true,
            WeaponCategory = 'Artillery',
        },
    },
}
"""
with open(os.path.join(dir_xra0202, "XRA0202_unit.bp"), "w") as f:
    f.write(bp_xra0202)

script_xra0202 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class BioMortarWeapon : DefaultProjectileWeapon
local BioMortarWeapon = ClassWeapon(DefaultProjectileWeapon) {
    PlayFxMuzzleSequence = function(self, muzzle)
        DefaultProjectileWeapon.PlayFxMuzzleSequence(self, muzzle)
        local unit = self.unit
        if not unit.Dead then
            if not unit.FireAnim then
                unit.FireAnim = CreateAnimator(unit)
                unit.Trash:Add(unit.FireAnim)
            end
            unit.FireAnim:PlayAnim('/mods/RaptorFaction/units/XRA0202/XRA0202_Afire.sca', false)
            unit.FireAnim:SetRate(1.5)
        end
    end,
}

---@class XRA0202 : CWalkingLandUnit
XRA0202 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        MainGun = ClassWeapon(BioMortarWeapon) {},
    },

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.8)
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.8)
        end
    end,
}

TypeClass = XRA0202
"""
with open(os.path.join(dir_xra0202, "XRA0202_script.lua"), "w") as f:
    f.write(script_xra0202)

print("Ported XRA0202 Mobile Bio-Artillery successfully.")

# ===========================================================================
# 6. XRA0205: HOVERING BIO-GUNSHIP
# ===========================================================================
print("\n--- Porting XRA0205 (Hovering Predator Gunship) ---")
s3o_gunship = get_bar_file('objects3d/raptors/spiker_gunship.s3o')
pieces_gunship = convert_s3o_to_scm(s3o_gunship, os.path.join(dir_xra0205, "XRA0205_lod0.scm"))
names_gunship = [p.name for p in pieces_gunship]
parents_gunship = [p.parent_idx for p in pieces_gunship]

alb_gunship = get_bar_file('unittextures/chicken_electric_l_color.dds') or get_bar_file('unittextures/chicken_purple_l_color.dds')
with open(os.path.join(dir_xra0205, "XRA0205_Albedo.dds"), "wb") as f:
    f.write(alb_gunship)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0205, "XRA0205_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0205, "XRA0205_SpecTeam.dds"))

ico_gunship = get_bar_file('unitpics/raptors/raptorf1.dds')
with open(os.path.join(dir_xra0205, "XRA0205_icon.dds"), "wb") as f:
    f.write(ico_gunship)
with open(os.path.join(icons_dir, "xra0205_icon.dds"), "wb") as f:
    f.write(ico_gunship)

# Rapid 4-Wing Hover Animation
num_frames = 16
dur = 0.35
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    p = 2.0 * math.pi * t
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_gunship}
    
    flap_u = math.sin(p) * math.radians(35.0)
    flap_l = math.sin(p + 0.5) * math.radians(40.0)
    rot["liwing"] = (0, 0, flap_u)
    rot["riwing"] = (0, 0, -flap_u)
    rot["lowing"] = (0, 0, flap_l)
    rot["rowing"] = (0, 0, -flap_l)
    rot["body"] = (math.sin(p) * math.radians(4.0), 0, 0)
    rot["tail"] = (-math.sin(p) * math.radians(6.0), 0, 0)
    
    time_sec = t * dur
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_gunship):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0205, "XRA0205_Afly.sca"), num_frames, dur, names_gunship, parents_gunship, frames)

# Death Tumble
num_frames = 20
dur = 0.7
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    time_sec = t * dur
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_gunship}
    rot["body"] = (math.radians(30.0) * t, math.radians(120.0) * t, 0)
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_gunship):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0205, "XRA0205_Adeath01.sca"), num_frames, dur, names_gunship, parents_gunship, frames)

bp_xra0205 = """UnitBlueprint {
    Air = {
        AutoLandTime = 1,
        BankFactor = 0.1,
        BankForward = false,
        CanFly = true,
        CirclingDirChangeFrequencySec = 1,
        CirclingElevationChangeRatio = 0.25,
        CirclingFlight = true,
        CirclingRadiusChangeMaxRatio = 0.9,
        CirclingRadiusChangeMinRatio = 0.6,
        CirclingRadiusVsTurnSpeed = 0.6,
        CombatTurnSpeed = 2.5,
        KMove = 0.8,
        KTurn = 2.0,
        LiftFactor = 7,
        MaxAirspeed = 8.0,
        StartTurnDistance = 5,
        TurnSpeed = 2.5,
    },
    Audio = {
        Destroyed = Sound {
            Bank = 'Raptor_Flyer_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Killed = Sound {
            Bank = 'Raptor_Flyer_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
    },
    Buffs = {
        Regen = {
            Level1 = 2,
            Level2 = 4,
            Level3 = 6,
        },
    },
    BuildIconSortPriority = 40,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYRAPTORHIVE',
        'BUILTBYTIER1FACTORY',
        'BUILTBYTIER2FACTORY',
        'CYBRAN',
        'RAPTOR',
        'MOBILE',
        'AIR',
        'TECH2',
        'GROUNDATTACK',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYDIRECTFIRE',
    },
    CollisionOffsetY = 0,
    Defense = {
        ArmorType = 'Light',
        Health = 850,
        MaxHealth = 850,
        RegenRate = 1.0,
    },
    Description = '<LOC xra0205_desc>Hovering Predator Gunship',
    Display = {
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0205/XRA0205_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0205/XRA0205_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0205/XRA0205_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0205/XRA0205_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.65,
    },
    Economy = {
        BuildCostEnergy = 4800,
        BuildCostMass = 240,
        BuildTime = 1600,
    },
    General = {
        Category = 'Gunship',
        Classification = 'RULEUC_MilitaryAircraft',
        CommandCaps = {
            RULEUCC_Attack = true,
            RULEUCC_CallCycle = false,
            RULEUCC_Capture = false,
            RULEUCC_Dock = true,
            RULEUCC_Guard = true,
            RULEUCC_Move = true,
            RULEUCC_Nuke = false,
            RULEUCC_Patrol = true,
            RULEUCC_Reclaim = false,
            RULEUCC_Repair = false,
            RULEUCC_RetaliateToggle = true,
            RULEUCC_Stop = true,
            RULEUCC_Transport = false,
        },
        FactionName = 'Raptor',
        Icon = 'air',
        UnitName = '<LOC xra0205_name>Bio-Hunter Gunship',
    },
    Intel = {
        VisionRadius = 26,
    },
    Interface = {
        HelpText = '<LOC xra0205_help>Hovering aerial predator that circles over targets, delivering continuous bursts of acidic bio-spikes.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.5,
    LifeBarSize = 1.4,
    Physics = {
        BankingSlope = 0.5,
        BuildOnLayerCaps = {
            LAYER_Air = true,
        },
        Elevation = 8.0,
        FuelRechargeRate = 0,
        FuelUseTime = 0,
        MaxSpeed = 8.0,
        MotionType = 'RULEUMT_Air',
    },
    SelectionSizeX = 1.5,
    SelectionSizeZ = 1.3,
    SelectionThickness = 0.5,
    SizeSphere = 0.8,
    SizeX = 1.6,
    SizeY = 0.45,
    SizeZ = 1.6,
    StrategicIconName = 'icon_gunship2_directfire',
    StrategicIconSortPriority = 65,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Attack',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            AutoInitiateAttackCommand = true,
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            Damage = 28,
            DamageType = 'Normal',
            DisplayName = 'Bio-Stinger Gatling Spikes',
            FireTargetLayerCapsTable = {
                Air = 'Land|Water|Seabed',
            },
            FiringTolerance = 2,
            Label = 'MainGun',
            MaxRadius = 22,
            MuzzleSalvoDelay = 0.1,
            MuzzleSalvoSize = 2,
            MuzzleVelocity = 35,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp',
            ProjectilesPerOnFire = 2,
            RackBones = {
                {
                    MuzzleBones = {
                        'head',
                    },
                    RackBone = 'head',
                },
            },
            RackFireTogether = false,
            RackRecoilDistance = 0,
            RackReloadTimeout = 10,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RackSlavedToTurret = false,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 2.5,
            TargetCheckInterval = 0.25,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'TECH2 MOBILE',
                'TECH1 MOBILE',
                'STRUCTURE DEFENSE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            TurretBoneMuzzle = 'head',
            TurretBonePitch = 'head',
            TurretBoneYaw = 'head',
            TurretDualManipulators = false,
            TurretPitch = -20,
            TurretPitchRange = 70,
            TurretPitchSpeed = 80,
            TurretYaw = 0,
            TurretYawRange = 180,
            TurretYawSpeed = 90,
            Turreted = true,
            WeaponCategory = 'Direct Fire',
        },
        {
            AboveWaterTargetsOnly = true,
            Damage = 150,
            DamageFriendly = true,
            DamageRadius = 1,
            DamageType = 'Normal',
            DisplayName = 'Air Crash',
            DummyWeapon = true,
            FiringTolerance = 2,
            Label = 'DeathImpact',
            WeaponCategory = 'Death',
        },
    },
}
"""
with open(os.path.join(dir_xra0205, "XRA0205_unit.bp"), "w") as f:
    f.write(bp_xra0205)

script_xra0205 = """local CAirUnit = import('/lua/cybranunits.lua').CAirUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class XRA0205 : CAirUnit
XRA0205 = ClassUnit(CAirUnit) {
    Weapons = {
        MainGun = ClassWeapon(DefaultProjectileWeapon) {},
    },

    OnCreate = function(self)
        CAirUnit.OnCreate(self)
        local flyAnim = CreateAnimator(self)
        flyAnim:PlayAnim('/mods/RaptorFaction/units/XRA0205/XRA0205_Afly.sca', true)
        flyAnim:SetRate(2.5)
        self.FlyAnim = flyAnim
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.8)
        end
        CAirUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.8)
        end
    end,
}

TypeClass = XRA0205
"""
with open(os.path.join(dir_xra0205, "XRA0205_script.lua"), "w") as f:
    f.write(script_xra0205)

print("Ported XRA0205 Bio-Hunter Gunship successfully.")

# ===========================================================================
# 7. XRA0301: HEAVY ASSAULT APEX BEHEMOTH
# ===========================================================================
print("\n--- Porting XRA0301 (Heavy Assault Apex Behemoth) ---")
s3o_apex = get_bar_file('objects3d/raptors/raptora2.s3o')
pieces_apex = convert_s3o_to_scm(s3o_apex, os.path.join(dir_xra0301, "XRA0301_lod0.scm"))
names_apex = [p.name for p in pieces_apex]
parents_apex = [p.parent_idx for p in pieces_apex]

alb_apex = get_bar_file('unittextures/chicken_redc_l_color.dds')
with open(os.path.join(dir_xra0301, "XRA0301_Albedo.dds"), "wb") as f:
    f.write(alb_apex)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0301, "XRA0301_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0301, "XRA0301_SpecTeam.dds"))

ico_apex = get_bar_file('unitpics/raptors/raptora2.dds')
with open(os.path.join(dir_xra0301, "XRA0301_icon.dds"), "wb") as f:
    f.write(ico_apex)
with open(os.path.join(icons_dir, "xra0301_icon.dds"), "wb") as f:
    f.write(ico_apex)

# Heavy Stride Walk (2-legged predatory bipedal gait)
num_frames = 24
dur = 0.9
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    p = 2.0 * math.pi * t
    rot = {}
    pos = {p_node.name: list(p_node.local_pos) for p_node in pieces_apex}

    pos['body'][1] += math.sin(2.0 * p) * 0.08
    rot['body'] = (math.sin(2.0 * p) * math.radians(4.0), 0, math.sin(p) * math.radians(3.0))
    rot['tail'] = (-math.sin(2.0 * p) * math.radians(6.0), -math.sin(p) * math.radians(20.0), 0)
    rot['head'] = (-math.sin(2.0 * p) * math.radians(4.0), 0, 0)

    rot['lthigh'] = (math.sin(p) * math.radians(40.0), 0, 0)
    rot['lknee'] = (-max(0.0, -math.sin(p)) * math.radians(50.0), 0, 0)
    rot['lshin'] = (math.sin(p) * math.radians(20.0), 0, 0)
    rot['lfoot'] = (-math.sin(p) * math.radians(15.0), 0, 0)

    rot['rthigh'] = (-math.sin(p) * math.radians(40.0), 0, 0)
    rot['rknee'] = (-max(0.0, math.sin(p)) * math.radians(50.0), 0, 0)
    rot['rshin'] = (-math.sin(p) * math.radians(20.0), 0, 0)
    rot['rfoot'] = (math.sin(p) * math.radians(15.0), 0, 0)

    rot['lforearmu'] = (-math.sin(p) * math.radians(20.0), 0, 0)
    rot['lbladeu'] = (0, 0, math.sin(p) * math.radians(6.0))
    rot['rforearmu'] = (math.sin(p) * math.radians(20.0), 0, 0)
    rot['rbladeu'] = (0, 0, -math.sin(p) * math.radians(6.0))

    rot['lforearml'] = (-math.sin(p) * math.radians(25.0), 0, 0)
    rot['lbladel'] = (0, 0, math.sin(p) * math.radians(8.0))
    rot['rforearml'] = (math.sin(p) * math.radians(25.0), 0, 0)
    rot['rbladel'] = (0, 0, -math.sin(p) * math.radians(8.0))

    time_sec = t * dur
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_apex):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0301, "XRA0301_Awalk.sca"), num_frames, dur, names_apex, parents_apex, frames)

# Scythe Slash Attack
num_frames = 18
dur = 0.65
frames = []
for f_idx in range(num_frames):
    t = f_idx / (num_frames - 1)
    time_sec = t * dur
    rot = {}
    pos = {p_node.name: list(p_node.local_pos) for p_node in pieces_apex}
    slash = math.sin(math.pi * t)

    rot['body'] = (slash * math.radians(4.0), 0, 0)
    rot['head'] = (slash * math.radians(4.0), 0, 0)
    rot['tail'] = (-slash * math.radians(4.0), 0, 0)

    rot['lforearmu'] = (slash * math.radians(45.0), slash * math.radians(20.0), -slash * math.radians(15.0))
    rot['lbladeu'] = (0, slash * math.radians(35.0), -slash * math.radians(20.0))
    rot['rforearmu'] = (slash * math.radians(45.0), -slash * math.radians(20.0), slash * math.radians(15.0))
    rot['rbladeu'] = (0, -slash * math.radians(35.0), slash * math.radians(20.0))

    rot['lforearml'] = (slash * math.radians(35.0), slash * math.radians(25.0), 0)
    rot['lbladel'] = (0, slash * math.radians(30.0), -slash * math.radians(15.0))
    rot['rforearml'] = (slash * math.radians(35.0), -slash * math.radians(25.0), 0)
    rot['rbladel'] = (0, -slash * math.radians(30.0), slash * math.radians(15.0))

    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_apex):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0301, "XRA0301_Aattack.sca"), num_frames, dur, names_apex, parents_apex, frames)

# Death Collapse
num_frames = 24
dur = 1.0
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    time_sec = t * dur
    rot = {}
    pos = {p_node.name: list(p_node.local_pos) for p_node in pieces_apex}
    fall = min(1.0, t * 1.25)

    rot['body'] = (fall * math.radians(25.0), 0, fall * math.radians(12.0))
    pos['body'][1] -= fall * 0.8
    rot['head'] = (fall * math.radians(25.0), 0, 0)
    rot['tail'] = (-fall * math.radians(18.0), 0, fall * math.radians(15.0))
    rot['lthigh'] = (-fall * math.radians(45.0), 0, 0)
    rot['rthigh'] = (-fall * math.radians(45.0), 0, 0)
    rot['lknee'] = (-fall * math.radians(50.0), 0, 0)
    rot['rknee'] = (-fall * math.radians(50.0), 0, 0)
    rot['lforearmu'] = (fall * math.radians(35.0), 0, fall * math.radians(20.0))
    rot['rforearmu'] = (fall * math.radians(35.0), 0, -fall * math.radians(20.0))
    rot['lforearml'] = (fall * math.radians(30.0), 0, fall * math.radians(15.0))
    rot['rforearml'] = (fall * math.radians(30.0), 0, -fall * math.radians(15.0))

    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_apex):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0301, "XRA0301_Adeath01.sca"), num_frames, dur, names_apex, parents_apex, frames)

bp_xra0301 = """UnitBlueprint {
    Audio = {
        Destroyed = Sound {
            Bank = 'Raptor_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Killed = Sound {
            Bank = 'Raptor_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
    },
    Buffs = {
        Regen = {
            Level1 = 3,
            Level2 = 6,
            Level3 = 9,
        },
    },
    BuildIconSortPriority = 20,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYRAPTORHIVE',
        'BUILTBYTIER1FACTORY',
        'BUILTBYTIER2FACTORY',
        'BUILTBYTIER3FACTORY',
        'CYBRAN',
        'RAPTOR',
        'MOBILE',
        'LAND',
        'TECH3',
        'DIRECTFIRE',
        'ANTIAIR',
        'AMPHIBIOUS',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYDIRECTFIRE',
        'OVERLAYANTIAIR',
    },
    CollisionOffsetY = 0.5,
    Defense = {
        ArmorType = 'Heavy',
        Health = 5400,
        MaxHealth = 5400,
        RegenRate = 4.0,
    },
    Description = '<LOC xra0301_desc>Armored Heavy Assault Bruiser',
    Display = {
        AnimationWalk = '/mods/RaptorFaction/units/XRA0301/XRA0301_Awalk.sca',
        AnimationWalkRate = 1.1,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0301/XRA0301_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0301/XRA0301_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0301/XRA0301_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0301/XRA0301_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.7,
    },
    Economy = {
        BuildCostEnergy = 7500,
        BuildCostMass = 920,
        BuildTime = 3200,
    },
    General = {
        Category = 'Direct Fire',
        Classification = 'RULEUC_MilitaryVehicle',
        CommandCaps = {
            RULEUCC_Attack = true,
            RULEUCC_CallCycle = false,
            RULEUCC_Capture = false,
            RULEUCC_Guard = true,
            RULEUCC_Move = true,
            RULEUCC_Nuke = false,
            RULEUCC_Patrol = true,
            RULEUCC_Reclaim = false,
            RULEUCC_Repair = false,
            RULEUCC_RetaliateToggle = true,
            RULEUCC_Stop = true,
            RULEUCC_Transport = false,
        },
        FactionName = 'Raptor',
        Icon = 'amph',
        UnitName = '<LOC xra0301_name>Apex Raptor Behemoth',
    },
    Intel = {
        VisionRadius = 28,
    },
    Interface = {
        HelpText = '<LOC xra0301_help>Towering heavily-armored assault apex raptor armed with devastating cleaving scythes and anti-air bio-spores.',
    },
    LifeBarHeight = 0.08,
    LifeBarOffset = 1.1,
    LifeBarSize = 1.5,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 3.2,
        MaxBrake = 3.2,
        MaxSpeed = 3.2,
        MaxSpeedReverse = 0,
        MaxSteerForce = 15,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        RotateOnSpot = true,
        RotateOnSpotThreshold = 0.1,
        TurnRadius = 0,
        TurnRate = 120,
    },
    SelectionSizeX = 1.3,
    SelectionSizeZ = 1.6,
    SelectionThickness = 0.4,
    SizeX = 1.4,
    SizeY = 2.0,
    SizeZ = 2.0,
    StrategicIconName = 'icon_land3_directfire',
    StrategicIconSortPriority = 115,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Heavy_Attack',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            AutoInitiateAttackCommand = true,
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            Damage = 350,
            DamageFriendly = false,
            DamageRadius = 1.2,
            DamageType = 'Normal',
            DisplayName = 'Heavy Scythe Cleave',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 2,
            Label = 'MainScythe',
            MaxRadius = 18,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            MuzzleVelocity = 30,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp',
            ProjectilesPerOnFire = 1,
            RackBones = {
                {
                    MuzzleBones = {
                        'headfirepoint',
                    },
                    RackBone = 'head',
                },
            },
            RackFireTogether = false,
            RackRecoilDistance = 0,
            RackReloadTimeout = 10,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RackSlavedToTurret = false,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1.5,
            TargetCheckInterval = 0.25,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'TECH3 MOBILE',
                'TECH2 MOBILE',
                'STRUCTURE DEFENSE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            TurretBoneMuzzle = 'headfirepoint',
            TurretBonePitch = 'aimy1',
            TurretBoneYaw = 'aimy1',
            TurretDualManipulators = false,
            TurretPitch = 0,
            TurretPitchRange = 25,
            TurretPitchSpeed = 120,
            TurretYaw = 0,
            TurretYawRange = 45,
            TurretYawSpeed = 120,
            Turreted = true,
            WeaponCategory = 'Direct Fire',
        },
        {
            AboveWaterTargetsOnly = true,
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Spores',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            BallisticArc = 'RULEUBA_None',
            CannotAttackGround = true,
            CollideFriendly = false,
            Damage = 45,
            DamageType = 'Normal',
            DisplayName = 'Defensive Bio-Spores',
            FireTargetLayerCapsTable = {
                Land = 'Air',
                Water = 'Air',
            },
            FiringTolerance = 2,
            Label = 'AASpores',
            MaxRadius = 32,
            MuzzleSalvoDelay = 0.1,
            MuzzleSalvoSize = 2,
            MuzzleVelocity = 35,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_Spore01/XRA_Spore01_proj.bp',
            ProjectilesPerOnFire = 2,
            RackBones = {
                {
                    MuzzleBones = {
                        'body',
                    },
                    RackBone = 'body',
                },
            },
            RackFireTogether = false,
            RackRecoilDistance = 0,
            RackReloadTimeout = 10,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            RangeCategory = 'UWRC_AntiAir',
            RateOfFire = 2.0,
            TargetCheckInterval = 0.3,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'AIR MOBILE HIGHALTAIR',
                'AIR MOBILE BOMBER',
                'AIR MOBILE GROUNDATTACK',
                'AIR MOBILE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            Turreted = false,
            WeaponCategory = 'Anti Air',
        },
    },
}
"""
with open(os.path.join(dir_xra0301, "XRA0301_unit.bp"), "w") as f:
    f.write(bp_xra0301)

script_xra0301 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class ScytheWeapon : DefaultProjectileWeapon
local ScytheWeapon = ClassWeapon(DefaultProjectileWeapon) {
    CreateProjectileAtMuzzle = function(self, muzzle)
        local proj = DefaultProjectileWeapon.CreateProjectileAtMuzzle(self, muzzle)
        if not self.unit.Dead then
            self.unit:PlayAttackAnim()
        end
        return proj
    end,
}

---@class XRA0301 : CWalkingLandUnit
XRA0301 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        MainScythe = ClassWeapon(ScytheWeapon) {},
        AASpores = ClassWeapon(DefaultProjectileWeapon) {},
    },

    PlayAttackAnim = function(self)
        if self.AttackThread then
            KillThread(self.AttackThread)
        end
        self.AttackThread = self:ForkThread(self.AttackAnimThread)
    end,

    AttackAnimThread = function(self)
        if not self.AttackAnim then
            self.AttackAnim = CreateAnimator(self)
            self.Trash:Add(self.AttackAnim)
        end
        self.AttackAnim:PlayAnim('/mods/RaptorFaction/units/XRA0301/XRA0301_Aattack.sca', false)
        self.AttackAnim:SetRate(1.6)
        WaitFor(self.AttackAnim)
        if not self.Dead and self.AttackAnim then
            self.AttackAnim:Destroy()
            self.AttackAnim = nil
        end
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        if self.AttackThread then
            KillThread(self.AttackThread)
        end
        if self.AttackAnim then
            self.AttackAnim:Destroy()
            self.AttackAnim = nil
        end
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.5)
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.5)
        end
    end,
}

TypeClass = XRA0301
"""
with open(os.path.join(dir_xra0301, "XRA0301_script.lua"), "w") as f:
    f.write(script_xra0301)

print("Ported XRA0301 Heavy Assault Apex Behemoth successfully.")

# ===========================================================================
# 8. XRA0401: EXPERIMENTAL MATRIARCH QUEEN TITAN
# ===========================================================================
print("\n--- Porting XRA0401 (Experimental Matriarch Queen Titan) ---")
s3o_queen = get_bar_file('objects3d/raptors/epic_raptorq.s3o')
pieces_queen = convert_s3o_to_scm(s3o_queen, os.path.join(dir_xra0401, "XRA0401_lod0.scm"))
names_queen = [p.name for p in pieces_queen]
parents_queen = [p.parent_idx for p in pieces_queen]

alb_queen = get_bar_file('unittextures/chicken_crimson_l_color.dds') or get_bar_file('unittextures/chicken_vcrimson_l_color.dds')
with open(os.path.join(dir_xra0401, "XRA0401_Albedo.dds"), "wb") as f:
    f.write(alb_queen)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0401, "XRA0401_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0401, "XRA0401_SpecTeam.dds"))

ico_queen = get_bar_file('unitpics/raptors/epic_raptorq.dds')
with open(os.path.join(dir_xra0401, "XRA0401_icon.dds"), "wb") as f:
    f.write(ico_queen)
with open(os.path.join(icons_dir, "xra0401_icon.dds"), "wb") as f:
    f.write(ico_queen)

# Monumental Quadruped Stomp Walk
num_frames = 32
dur = 1.4
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    phase_A = 2.0 * math.pi * t
    phase_B = phase_A + math.pi
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_queen}
    
    # Front-Left & Back-Right (A)
    rot["lthighf"] = (math.sin(phase_A) * math.radians(24.0), 0, 0)
    rot["lkneef"] = (-max(0.0, -math.sin(phase_A)) * math.radians(30.0), 0, 0)
    rot["rthighb"] = (math.sin(phase_A) * math.radians(24.0), 0, 0)
    rot["rkneeb"] = (-max(0.0, -math.sin(phase_A)) * math.radians(30.0), 0, 0)
    
    # Front-Right & Back-Left (B)
    rot["rthighf"] = (math.sin(phase_B) * math.radians(24.0), 0, 0)
    rot["rkneef"] = (-max(0.0, -math.sin(phase_B)) * math.radians(30.0), 0, 0)
    rot["lthighb"] = (math.sin(phase_B) * math.radians(24.0), 0, 0)
    rot["lkneeb"] = (-max(0.0, -math.sin(phase_B)) * math.radians(30.0), 0, 0)
    
    # Body roll and pitch
    rot["body"] = (math.sin(phase_A * 2.0) * math.radians(4.0), 0, math.cos(phase_A) * math.radians(3.0))
    rot["tail"] = (-math.sin(phase_A * 2.0) * math.radians(8.0), 0, 0)
    
    time_sec = t * dur
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_queen):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0401, "XRA0401_Awalk.sca"), num_frames, dur, names_queen, parents_queen, frames)

# Roar Attack Animation
num_frames = 24
dur = 1.2
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    time_sec = t * dur
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_queen}
    roar = math.sin(math.pi * t)
    rot["body"] = (roar * math.radians(20.0), 0, 0)
    rot["head"] = (roar * math.radians(25.0), 0, 0)
    rot["rforearmu"] = (0, roar * math.radians(35.0), 0)
    rot["lforearmu"] = (0, -roar * math.radians(35.0), 0)
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_queen):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0401, "XRA0401_Aroar.sca"), num_frames, dur, names_queen, parents_queen, frames)

# Cataclysmic Death Collapse
num_frames = 36
dur = 1.6
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    time_sec = t * dur
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_queen}
    rot["body"] = (math.radians(-35.0) * t, 0, 0)
    rot["head"] = (math.radians(-25.0) * t, 0, 0)
    rot["lthighf"] = (math.radians(30.0) * t, 0, math.radians(25.0) * t)
    rot["rthighf"] = (math.radians(30.0) * t, 0, -math.radians(25.0) * t)
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_queen):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0401, "XRA0401_Adeath01.sca"), num_frames, dur, names_queen, parents_queen, frames)

bp_xra0401 = """UnitBlueprint {
    Audio = {
        Destroyed = Sound {
            Bank = 'Raptor_Queen_Roar',
            Cue = 'Attack',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Killed = Sound {
            Bank = 'Raptor_Queen_Roar',
            Cue = 'Attack',
            LodCutoff = 'UnitMove_LodCutoff',
        },
    },
    Buffs = {
        Regen = {
            Level1 = 15,
            Level2 = 30,
            Level3 = 45,
        },
    },
    BuildIconSortPriority = 10,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYTIER1ENGINEER',
        'BUILTBYTIER2ENGINEER',
        'BUILTBYTIER3ENGINEER',
        'CYBRAN',
        'RAPTOR',
        'MOBILE',
        'LAND',
        'EXPERIMENTAL',
        'DIRECTFIRE',
        'ANTIAIR',
        'AMPHIBIOUS',
        'NEEDMOBILEBUILD',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYDIRECTFIRE',
        'OVERLAYANTIAIR',
    },
    CollisionOffsetY = 0.5,
    Defense = {
        ArmorType = 'Experimental',
        Health = 68000,
        MaxHealth = 68000,
        RegenRate = 25.0,
    },
    Description = '<LOC xra0401_desc>Experimental Biological Titan',
    Display = {
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0401/XRA0401_Adeath01.sca',
                AnimationRateMax = 1.0,
                AnimationRateMin = 0.8,
                Weight = 100,
            },
        },
        AnimationWalk = '/mods/RaptorFaction/units/XRA0401/XRA0401_Awalk.sca',
        AnimationWalkRate = 0.8,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0401/XRA0401_Albedo.dds',
                    LODCutoff = 350,
                    MeshName = '/mods/RaptorFaction/units/XRA0401/XRA0401_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0401/XRA0401_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0401/XRA0401_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.38,
    },
    Economy = {
        BuildCostEnergy = 320000,
        BuildCostMass = 28000,
        BuildTime = 42000,
    },
    General = {
        Category = 'Experimental',
        Classification = 'RULEUC_MilitaryVehicle',
        CommandCaps = {
            RULEUCC_Attack = true,
            RULEUCC_CallCycle = false,
            RULEUCC_Capture = false,
            RULEUCC_Guard = true,
            RULEUCC_Move = true,
            RULEUCC_Nuke = false,
            RULEUCC_Patrol = true,
            RULEUCC_Reclaim = false,
            RULEUCC_Repair = false,
            RULEUCC_RetaliateToggle = true,
            RULEUCC_Stop = true,
            RULEUCC_Transport = false,
        },
        FactionName = 'Cybran',
        Icon = 'amph',
        UnitName = '<LOC xra0401_name>Matriarch Raptor Queen',
    },
    Intel = {
        VisionRadius = 40,
        WaterVisionRadius = 32,
    },
    Interface = {
        HelpText = '<LOC xra0401_help>Supreme experimental titan boss of the swarm. Boasts earth-shattering roar plasma, colossal crushing scythe sweeps, flak anti-air spores, and field swarmer gestation.',
    },
    LifeBarHeight = 0.15,
    LifeBarOffset = 3.2,
    LifeBarSize = 4.2,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 2.2,
        MaxBrake = 2.2,
        MaxSpeed = 2.2,
        MaxSpeedReverse = 0,
        MaxSteerForce = 20,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        RotateOnSpot = true,
        RotateOnSpotThreshold = 0.1,
        TurnRadius = 0,
        TurnRate = 50,
    },
    SelectionSizeX = 3.5,
    SelectionSizeZ = 4.5,
    SelectionThickness = 0.4,
    SizeX = 4.0,
    SizeY = 4.5,
    SizeZ = 7.0,
    StrategicIconName = 'icon_experimental_generic',
    StrategicIconSortPriority = 15,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Queen_Roar',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            AutoInitiateAttackCommand = true,
            BallisticArc = 'RULEUBA_LowArc',
            CollideFriendly = false,
            Damage = 2200,
            DamageFriendly = false,
            DamageRadius = 4.0,
            DamageType = 'Normal',
            DisplayName = 'Titanic Roar Plasma',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 2,
            Label = 'RoarCannon',
            MaxRadius = 48,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            MuzzleVelocity = 28,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_QueenPlasma01/XRA_QueenPlasma01_proj.bp',
            ProjectilesPerOnFire = 1,
            RackBones = {
                {
                    MuzzleBones = {
                        'head',
                    },
                    RackBone = 'head',
                },
            },
            RackFireTogether = false,
            RackRecoilDistance = 0,
            RackReloadTimeout = 10,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 0.33,
            RenderFireClock = true,
            TargetCheckInterval = 0.5,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'EXPERIMENTAL',
                'TECH3 MOBILE',
                'STRUCTURE DEFENSE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            TurretBoneMuzzle = 'head',
            TurretBonePitch = 'head',
            TurretBoneYaw = 'aimy1',
            TurretDualManipulators = false,
            TurretPitch = 0,
            TurretPitchRange = 45,
            TurretPitchSpeed = 50,
            TurretYaw = 0,
            TurretYawRange = 180,
            TurretYawSpeed = 60,
            Turreted = true,
            WeaponCategory = 'Direct Fire',
        },
        {
            AboveWaterTargetsOnly = true,
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Queen_Cleave',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            AutoInitiateAttackCommand = true,
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            Damage = 1200,
            DamageFriendly = false,
            DamageRadius = 2.5,
            DamageType = 'Normal',
            DisplayName = 'Crushing Scythe Cleave',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 2,
            Label = 'MeleeCleave',
            MaxRadius = 14,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            MuzzleVelocity = 35,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp',
            ProjectilesPerOnFire = 1,
            RackBones = {
                {
                    MuzzleBones = {
                        'head',
                    },
                    RackBone = 'head',
                },
            },
            RackFireTogether = false,
            RackRecoilDistance = 0,
            RackReloadTimeout = 10,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RateOfFire = 1.0,
            TargetCheckInterval = 0.25,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'MOBILE',
                'STRUCTURE DEFENSE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            Turreted = false,
            WeaponCategory = 'Direct Fire',
        },
        {
            AboveWaterTargetsOnly = true,
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Spores',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            BallisticArc = 'RULEUBA_None',
            CannotAttackGround = true,
            CollideFriendly = false,
            Damage = 120,
            DamageType = 'Normal',
            DisplayName = 'Heavy AA Flak Spores',
            FireTargetLayerCapsTable = {
                Land = 'Air',
                Water = 'Air',
            },
            FiringTolerance = 2,
            Label = 'AAFlak',
            MaxRadius = 42,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            MuzzleVelocity = 40,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_Spore01/XRA_Spore01_proj.bp',
            ProjectilesPerOnFire = 3,
            RackBones = {
                {
                    MuzzleBones = {
                        'body',
                    },
                    RackBone = 'body',
                },
            },
            RackFireTogether = false,
            RackRecoilDistance = 0,
            RackReloadTimeout = 10,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RangeCategory = 'UWRC_AntiAir',
            RateOfFire = 1.0,
            TargetCheckInterval = 0.25,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'EXPERIMENTAL',
                'AIR MOBILE BOMBER',
                'AIR MOBILE GROUNDATTACK',
                'AIR MOBILE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            Turreted = false,
            WeaponCategory = 'Anti Air',
        },
    },
}
"""
with open(os.path.join(dir_xra0401, "XRA0401_unit.bp"), "w") as f:
    f.write(bp_xra0401)

script_xra0401 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon
local Eggs = import('/mods/RaptorFaction/lua/RaptorEggs.lua')

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class RoarWeapon : DefaultProjectileWeapon
local RoarWeapon = ClassWeapon(DefaultProjectileWeapon) {
    CreateProjectileAtMuzzle = function(self, muzzle)
        local proj = DefaultProjectileWeapon.CreateProjectileAtMuzzle(self, muzzle)
        if not self.unit.Dead then
            local roarAnim = CreateAnimator(self.unit)
            roarAnim:PlayAnim('/mods/RaptorFaction/units/XRA0401/XRA0401_Aroar.sca', false)
            roarAnim:SetRate(1.2)
        end
        return proj
    end,
}

---@class XRA0401 : CWalkingLandUnit
XRA0401 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        RoarCannon = ClassWeapon(RoarWeapon) {},
        MeleeCleave = ClassWeapon(DefaultProjectileWeapon) {},
        AAFlak = ClassWeapon(DefaultProjectileWeapon) {},
    },

    CreateWreckage = function(self, overkillRatio)
        return nil
    end,

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
        self:ForkThread(self.GestationThread)
    end,

    GestationThread = function(self)
        while not self.Dead do
            WaitSeconds(25.0)
            if not self.Dead then
                local brain = self:GetAIBrain()
                local pos = self:GetPosition()
                for i = 1, 4 do
                    local ox = (math.random() - 0.5) * 6
                    local oz = (math.random() - 0.5) * 6
                    local unit = brain:CreateUnitNearSpot('XRA0101', pos[1] + ox, pos[3] + oz)
                    if unit then
                        CreateEmitterAtEntity(unit, self.Army, '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp'):ScaleEmitter(1.5)
                    end
                end
            end
        end
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(5.0)
        end
        Eggs.SpawnRaptorEgg(self)
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(5.0)
        end
    end,
}

TypeClass = XRA0401
"""
with open(os.path.join(dir_xra0401, "XRA0401_script.lua"), "w") as f:
    f.write(script_xra0401)

print("Ported XRA0401 Experimental Matriarch Queen Titan successfully.")

# ===========================================================================
# 9. INTEGRATION: UPDATE FACTORY ROOST (XRA0107) & BIO-WEAVER (XRA0109)
# ===========================================================================
print("\n--- Updating Factory & Builder Build Categories ---")

bp_roost_path = os.path.join(dir_xra0107, "XRA0107_unit.bp")
if os.path.exists(bp_roost_path):
    with open(bp_roost_path, "r") as f:
        c = f.read()
    # Ensure BuildableCategory contains BUILTBYRAPTORHIVE and RAPTOR MOBILE
    if "BUILTBYRAPTORHIVE" not in c:
        c = c.replace(
            "BuildableCategory = {",
            "BuildableCategory = {\n            'BUILTBYRAPTORHIVE',\n            'RAPTOR MOBILE',"
        )
    with open(bp_roost_path, "w") as f:
        f.write(c)
    print("Updated XRA0107 Gestation Roost build queue.")

# ===========================================================================
# 10. UPDATE MOD INFO & EXPORT ARCHIVE
# ===========================================================================
mod_info_path = os.path.join(mod_dir, "mod_info.lua")
mod_info_content = """name = "Raptor Swarm Faction"
version = 5
copyright = "Beyond All Reason & FAF Communities"
description = "Comprehensive standalone biological Raptor Swarm race. Includes full mobile roster: T1 Melee Swarmer, T1 Kamikaze Tick, T1 Bio-Acid Bomber, T1 Wing Swarmer, T1 Bio-Weaver (Healer & Builder), T2 6-Legged Crawler, T2 Mobile Bio-Artillery, T2 Hovering Bio-Gunship, T3 Heavy Assault Apex Behemoth, and T4 Experimental Matriarch Queen Titan! Supported by Gestation Hives, Burrowing Worms, Bio-Nuke & Anti-Nuke Silos, and 4 Super-Heavy Artillery Spires."
author = "BAR & FAF"
uid = "raptor-swarm-faction-faf-0005"
selectable = true
enabled = true
exclusive = false
ui_only = false
requires = {}
"""
with open(mod_info_path, "w") as f:
    f.write(mod_info_content)

export_zip = os.path.join(os.path.dirname(__file__), "exports", "RaptorFaction.zip")
print(f"\nPackaging updated standalone mod to {export_zip}...")
with zipfile.ZipFile(export_zip, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(mod_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(mod_dir))
            z.write(full_path, rel_path)

print(f"\nSUCCESS: Exported {os.path.getsize(export_zip):,} bytes to {export_zip}")
print("ALL RAPTOR UNIT PORTING TASKS COMPLETED!")
