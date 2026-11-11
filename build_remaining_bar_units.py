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

# Reference existing unit
dir_xra0101 = os.path.join(units_root, "XRA0101")
dir_xra0103 = os.path.join(units_root, "XRA0103")
dir_xra0104 = os.path.join(units_root, "XRA0104")
dir_xra0107 = os.path.join(units_root, "XRA0107") # Factory
dir_xra0109 = os.path.join(units_root, "XRA0109") # Builder
dir_xra0401 = os.path.join(units_root, "XRA0401")

# 8 New Unit Directories
dir_xra0100 = os.path.join(units_root, "XRA0100") # Mini Raptor Swarmer (Small Version)
dir_xra0111 = os.path.join(units_root, "XRA0111") # Bio-Recon Scout (Pidgeon)
dir_xra0203 = os.path.join(units_root, "XRA0203") # Bio-EMP Shock Tick (Electric Dodo)
dir_xra0204 = os.path.join(units_root, "XRA0204") # Brood Swarm Bomber (Unit-Spawning Bombs)
dir_xra0206 = os.path.join(units_root, "XRA0206") # Pyro All-Terrain Raptor (Flamer)
dir_xra0302 = os.path.join(units_root, "XRA0302") # Psychic Brain Bug (Overseer Intel / Stealth Jammer)
dir_xra0303 = os.path.join(units_root, "XRA0303") # Raptor Matriarch (Mini-Queen Sub-Boss)
dir_xra0310 = os.path.join(units_root, "XRA0310") # Behemoth Heavy Dodo (Heavy Suicide Bomb)

# New Projectiles
dir_proj_brood_egg = os.path.join(proj_root, "XRA_BroodEggBomb01")
dir_proj_pyro = os.path.join(proj_root, "XRA_PyroStream01")
dir_proj_neuro = os.path.join(proj_root, "XRA_NeuroBlast01")

new_dirs = [
    icons_dir, dir_xra0100, dir_xra0111, dir_xra0203, dir_xra0204,
    dir_xra0206, dir_xra0302, dir_xra0303, dir_xra0310,
    dir_proj_brood_egg, dir_proj_pyro, dir_proj_neuro, raptor_sounds_dir
]
for d in new_dirs:
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

# Generate Audio Banks for New Special Units
new_audio = [
    ('Raptor_Flamer', 'Raptor_Flamer', 'Attack', 'sounds/raptors/cflamhvy1.wav', 'cflamhvy1.wav'),
    ('Raptor_Electric', 'Raptor_Electric', 'Attack', 'sounds/weapons-mult/alien_electric.wav', 'alien_electric.wav'),
]

for sb_name, wb_name, cue, bar_path, fname in new_audio:
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

# ===========================================================================
# PROJECTILES: Brood Egg Bomb, Pyro Stream, Psychic Blast
# ===========================================================================
# 1. Brood Egg Bomb (Spawns living Swarmers on impact!)
bp_brood_egg = """ProjectileBlueprint {
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
                    AlbedoName = '/mods/RaptorFaction/units/XRA0204/XRA0204_Albedo.dds',
                    LODCutoff = 150,
                    MeshName = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_lod0.scm',
                    ShaderName = 'TMeshNoLighting',
                },
            },
        },
        StrategicIconSize = 2,
        UniformScale = 4.5,
    },
    General = {
        Category = 'Bomb',
        EntityCategory = {
            'RAPTOR',
            'PROJECTILE',
            'INDIRECTFIRE',
        },
        Faction = 'Cybran',
        Weapon = 'Brood Egg Bomb',
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
        RotationalVelocity = 120,
        TurnRate = 0,
        VelocityAlign = true,
    },
}
"""
with open(os.path.join(dir_proj_brood_egg, "XRA_BroodEggBomb01_proj.bp"), "w") as f:
    f.write(bp_brood_egg)

script_brood_egg = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile

XRA_BroodEggBomb01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/default_polytrail_01_emit.bp',
    PolyTrailOffset = 0,

    OnImpact = function(self, targetType, targetEntity)
        local army = self.Army
        local pos = self:GetPosition()
        local launcher = self:GetLauncher()
        if launcher and not launcher.Dead then
            local brain = launcher:GetAIBrain()
            if brain then
                for i = 1, 2 do
                    local ox = (math.random() - 0.5) * 3
                    local oz = (math.random() - 0.5) * 3
                    local unit = brain:CreateUnitNearSpot('XRA0101', pos[1] + ox, pos[3] + oz)
                    if unit then
                        CreateEmitterAtEntity(unit, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp'):ScaleEmitter(1.5)
                        CreateEmitterAtEntity(unit, army, '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp'):ScaleEmitter(1.2)
                    end
                end
            end
        end
        CreateEmitterAtEntity(self, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp'):ScaleEmitter(2.5)
        SinglePolyTrailProjectile.OnImpact(self, targetType, targetEntity)
    end,
}
TypeClass = XRA_BroodEggBomb01
"""
with open(os.path.join(dir_proj_brood_egg, "XRA_BroodEggBomb01_script.lua"), "w") as f:
    f.write(script_brood_egg)

# 2. Pyro Stream (Flamethrower Projectile & Emitters)
emit_root = os.path.join(mod_dir, "effects", "emitters")
os.makedirs(emit_root, exist_ok=True)

emit_flame = """EmitterBlueprint {
    BlueprintId = 'raptor_bio_flame_01',
    Lifetime = 1.50,
    Repeattime = 1.50,
    TextureFramecount = 1.00,
    Blendmode = 3.00,
    LocalVelocity = false,
    LocalAcceleration = false,
    Gravity = false,
    AlignRotation = false,
    AlignToBone = false,
    Flat = false,
    LODCutoff = 300.00,
    EmitIfVisible = true,
    CatchupEmit = true,
    CreateIfVisible = false,
    SnapToWaterline = false,
    OnlyEmitOnWater = false,
    InterpolateEmission = true,
    TextureStripcount = 4.00,
    SortOrder = 10.00,
    Texture = '/textures/particles/fire_flame_add_05.dds',
    RampTexture = '/textures/particles/ramp_fire_09.dds',
    XDirectionCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.00, z=0.30 },
        },
    },
    YDirectionCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.20, z=0.30 },
        },
    },
    ZDirectionCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.00, z=0.30 },
        },
    },
    EmitRateCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=45.00, z=0.00 },
        },
    },
    LifetimeCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.45, z=0.10 },
        },
    },
    VelocityCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=1.20, z=0.50 },
        },
    },
    StartSizeCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.40, z=0.15 },
        },
    },
    EndSizeCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=1.80, z=0.30 },
        },
    },
    InitialRotationCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=180.00, z=360.00 },
        },
    },
    RotationRateCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=15.00, z=20.00 },
        },
    },
    FrameRateCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=1.00, z=0.00 },
        },
    },
    TextureSelectionCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=2.00, z=4.00 },
        },
    },
    RampSelectionCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.00, z=0.00 },
        },
    },
}
"""
with open(os.path.join(emit_root, "raptor_bio_flame_01_emit.bp"), "w") as f:
    f.write(emit_flame)

emit_smoke = """EmitterBlueprint {
    BlueprintId = 'raptor_bio_smoke_01',
    Lifetime = 1.50,
    Repeattime = 1.50,
    TextureFramecount = 1.00,
    Blendmode = 0.00,
    LocalVelocity = false,
    LocalAcceleration = false,
    Gravity = false,
    AlignRotation = false,
    AlignToBone = false,
    Flat = false,
    LODCutoff = 250.00,
    EmitIfVisible = true,
    CatchupEmit = true,
    CreateIfVisible = false,
    SnapToWaterline = false,
    OnlyEmitOnWater = false,
    InterpolateEmission = true,
    TextureStripcount = 1.00,
    SortOrder = -5.00,
    Texture = '/textures/particles/cloud_smoke_alpha_black.dds',
    RampTexture = '/textures/particles/ramp_fire_smoke_01.dds',
    XDirectionCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.00, z=0.40 },
        },
    },
    YDirectionCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.60, z=0.30 },
        },
    },
    ZDirectionCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.00, z=0.40 },
        },
    },
    EmitRateCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=25.00, z=0.00 },
        },
    },
    LifetimeCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.75, z=0.20 },
        },
    },
    VelocityCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=1.50, z=0.50 },
        },
    },
    StartSizeCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.50, z=0.20 },
        },
    },
    EndSizeCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=2.20, z=0.40 },
        },
    },
    InitialRotationCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=180.00, z=360.00 },
        },
    },
    RotationRateCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=10.00, z=15.00 },
        },
    },
    FrameRateCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=1.00, z=0.00 },
        },
    },
    TextureSelectionCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.00, z=0.00 },
        },
    },
    RampSelectionCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.00, z=0.00 },
        },
    },
}
"""
with open(os.path.join(emit_root, "raptor_bio_smoke_01_emit.bp"), "w") as f:
    f.write(emit_smoke)

emit_muzzle = """EmitterBlueprint {
    BlueprintId = 'raptor_bio_flame_muzzle_01',
    Lifetime = 0.20,
    Repeattime = 0.20,
    TextureFramecount = 1.00,
    Blendmode = 3.00,
    LocalVelocity = true,
    LocalAcceleration = false,
    Gravity = false,
    AlignRotation = false,
    AlignToBone = false,
    Flat = false,
    LODCutoff = 250.00,
    EmitIfVisible = true,
    CatchupEmit = true,
    CreateIfVisible = false,
    SnapToWaterline = false,
    OnlyEmitOnWater = false,
    InterpolateEmission = true,
    TextureStripcount = 4.00,
    SortOrder = 10.00,
    Texture = '/textures/particles/fire_flame_add_05.dds',
    RampTexture = '/textures/particles/ramp_fire_09.dds',
    XDirectionCurve = {
        XRange = 0.20,
        Keys = {
            { x=0.10, y=0.00, z=0.20 },
        },
    },
    YDirectionCurve = {
        XRange = 0.20,
        Keys = {
            { x=0.10, y=0.00, z=0.20 },
        },
    },
    ZDirectionCurve = {
        XRange = 0.20,
        Keys = {
            { x=0.10, y=1.50, z=0.50 },
        },
    },
    EmitRateCurve = {
        XRange = 0.20,
        Keys = {
            { x=0.05, y=30.00, z=0.00 },
            { x=0.18, y=0.00, z=0.00 },
        },
    },
    LifetimeCurve = {
        XRange = 0.20,
        Keys = {
            { x=0.10, y=0.25, z=0.05 },
        },
    },
    VelocityCurve = {
        XRange = 0.20,
        Keys = {
            { x=0.05, y=5.00, z=1.00 },
            { x=0.15, y=1.00, z=0.50 },
        },
    },
    StartSizeCurve = {
        XRange = 0.20,
        Keys = {
            { x=0.10, y=0.30, z=0.10 },
        },
    },
    EndSizeCurve = {
        XRange = 0.20,
        Keys = {
            { x=0.10, y=1.10, z=0.20 },
        },
    },
    InitialRotationCurve = {
        XRange = 0.20,
        Keys = {
            { x=0.10, y=180.00, z=360.00 },
        },
    },
    RotationRateCurve = {
        XRange = 0.20,
        Keys = {
            { x=0.10, y=10.00, z=20.00 },
        },
    },
    FrameRateCurve = {
        XRange = 0.20,
        Keys = {
            { x=0.10, y=1.00, z=0.00 },
        },
    },
    TextureSelectionCurve = {
        XRange = 0.20,
        Keys = {
            { x=0.10, y=2.00, z=4.00 },
        },
    },
    RampSelectionCurve = {
        XRange = 0.20,
        Keys = {
            { x=0.10, y=0.00, z=0.00 },
        },
    },
}
"""
with open(os.path.join(emit_root, "raptor_bio_flame_muzzle_01_emit.bp"), "w") as f:
    f.write(emit_muzzle)

bp_pyro = """ProjectileBlueprint {
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
        StrategicIconSize = 1,
    },
    General = {
        Category = 'Direct Fire',
        EntityCategory = {
            'RAPTOR',
            'PROJECTILE',
            'DIRECTFIRE',
        },
        Faction = 'Cybran',
        Weapon = 'Bio Napalm Stream',
    },
    Physics = {
        Acceleration = 0,
        DestroyOnWater = true,
        InitialSpeed = 28,
        Lifetime = 0.8,
        MaxSpeed = 28,
        UseGravity = false,
        VelocityAlign = true,
    },
}
"""
with open(os.path.join(dir_proj_pyro, "XRA_PyroStream01_proj.bp"), "w") as f:
    f.write(bp_pyro)

script_pyro = """local SingleCompositeEmitterProjectile = import('/lua/sim/defaultprojectiles.lua').SingleCompositeEmitterProjectile

---@class XRA_PyroStream01 : SingleCompositeEmitterProjectile
XRA_PyroStream01 = ClassProjectile(SingleCompositeEmitterProjectile) {
    BeamName = '/effects/emitters/missile_exhaust_fire_beam_01_emit.bp',
    PolyTrail = '/effects/emitters/plasma_cannon_polytrail_04_emit.bp',
    PolyTrailOffset = 0,
    FxTrails = {
        '/mods/RaptorFaction/effects/emitters/raptor_bio_flame_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_bio_smoke_01_emit.bp',
        '/effects/emitters/flamethrower_02_emit.bp',
    },
    FxTrailScale = 1.0,
    FxTrailOffset = 0,

    FxImpactTrajectoryAligned = false,

    FxImpactUnit = {
        '/effects/emitters/napalm_flash_emit.bp',
        '/effects/emitters/Small_test_fire.bp',
        '/effects/emitters/plasma_cannon_hit_01_emit.bp',
        '/effects/emitters/destruction_land_hit_puff_01_emit.bp',
    },
    FxImpactProp = {
        '/effects/emitters/napalm_flash_emit.bp',
        '/effects/emitters/Small_test_fire.bp',
        '/effects/emitters/plasma_cannon_hit_01_emit.bp',
        '/effects/emitters/destruction_land_hit_puff_01_emit.bp',
    },
    FxImpactLand = {
        '/effects/emitters/napalm_flash_emit.bp',
        '/effects/emitters/Small_test_fire.bp',
        '/effects/emitters/plasma_cannon_hit_01_emit.bp',
        '/effects/emitters/destruction_land_hit_puff_01_emit.bp',
    },
    FxImpactWater = {
        '/effects/emitters/napalm_hvy_waterflash_emit.bp',
        '/effects/emitters/napalm_hvy_water_smoke_emit.bp',
    },
    FxImpactUnderWater = {
        '/effects/emitters/napalm_hvy_waterflash_emit.bp',
    },

    FxLandHitScale = 0.8,
    FxUnitHitScale = 0.8,
    FxPropHitScale = 0.8,
    FxWaterHitScale = 0.8,
}
TypeClass = XRA_PyroStream01
"""
with open(os.path.join(dir_proj_pyro, "XRA_PyroStream01_script.lua"), "w") as f:
    f.write(script_pyro)

# 3. Neuro Blast (Brain Bug Psionic Neuro-Disrupter)
bp_neuro = """ProjectileBlueprint {
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
        Mesh = {
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0302/XRA0302_Albedo.dds',
                    LODCutoff = 150,
                    MeshName = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_lod0.scm',
                    ShaderName = 'TMeshNoLighting',
                },
            },
        },
        StrategicIconSize = 2,
        UniformScale = 3.5,
    },
    General = {
        Category = 'Direct Fire',
        EntityCategory = {
            'RAPTOR',
            'PROJECTILE',
            'DIRECTFIRE',
        },
        Faction = 'Cybran',
        Weapon = 'Neuro Psionic Blast',
    },
    Physics = {
        Acceleration = 0,
        DestroyOnWater = true,
        InitialSpeed = 35,
        Lifetime = 2.0,
        MaxSpeed = 35,
        UseGravity = false,
        VelocityAlign = true,
    },
}
"""
with open(os.path.join(dir_proj_neuro, "XRA_NeuroBlast01_proj.bp"), "w") as f:
    f.write(bp_neuro)

script_neuro = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile

XRA_NeuroBlast01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/seraphim_aireau_autocannon_polytrail_01_emit.bp',
    OnImpact = function(self, targetType, targetEntity)
        local pos = self:GetPosition()
        local brain = self:GetLauncher() and self:GetLauncher():GetAIBrain()
        if brain then
            local targets = brain:GetUnitsAroundPoint(categories.MOBILE, pos, 4.0, 'Enemy')
            for _, t in targets do
                if not t.Dead then
                    t:SetStunned(4.0)
                end
            end
        end
        SinglePolyTrailProjectile.OnImpact(self, targetType, targetEntity)
    end,
}
TypeClass = XRA_NeuroBlast01
"""
with open(os.path.join(dir_proj_neuro, "XRA_NeuroBlast01_script.lua"), "w") as f:
    f.write(script_neuro)

print("Created Projectiles: XRA_BroodEggBomb01, XRA_PyroStream01, XRA_NeuroBlast01")

# ===========================================================================
# 1. XRA0100: MINI RAPTOR SWARMER (SMALL VERSION)
# ===========================================================================
print("\n--- Porting XRA0100 (Mini Raptor Swarmer - Small Version) ---")
s3o_mini = get_bar_file('objects3d/raptors/raptor_mini.s3o')
pieces_mini = convert_s3o_to_scm(s3o_mini, os.path.join(dir_xra0100, "XRA0100_lod0.scm"))
names_mini = [p.name for p in pieces_mini]
parents_mini = [p.parent_idx for p in pieces_mini]

alb_mini = get_bar_file('unittextures/chicken_1_s_color.dds') or get_bar_file('unittextures/chicken_c3_s_color.dds')
with open(os.path.join(dir_xra0100, "XRA0100_Albedo.dds"), "wb") as f:
    f.write(alb_mini)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0100, "XRA0100_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0100, "XRA0100_SpecTeam.dds"))

ico_mini = get_bar_file('unitpics/raptors/raptor1.dds')
with open(os.path.join(dir_xra0100, "XRA0100_icon.dds"), "wb") as f:
    f.write(ico_mini)
with open(os.path.join(icons_dir, "xra0100_icon.dds"), "wb") as f:
    f.write(ico_mini)

# Walk Animation (Ultra Rapid Skitter)
num_frames = 20
dur = 0.4
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    p = 2.0 * math.pi * t
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_mini}
    rot["lthigh"] = (math.sin(p) * math.radians(35.0), 0, 0)
    rot["lknee"] = (-max(0.0, -math.sin(p)) * math.radians(45.0), 0, 0)
    rot["rthigh"] = (-math.sin(p) * math.radians(35.0), 0, 0)
    rot["rknee"] = (-max(0.0, math.sin(p)) * math.radians(45.0), 0, 0)
    rot["body"] = (math.sin(p * 2.0) * math.radians(5.0), 0, 0)
    time_sec = t * dur
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_mini):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0100, "XRA0100_Awalk.sca"), num_frames, dur, names_mini, parents_mini, frames)

# Death Collapse
num_frames = 16
dur = 0.5
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    time_sec = t * dur
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_mini}
    rot["body"] = (math.radians(-25.0) * t, 0, 0)
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_mini):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0100, "XRA0100_Adeath01.sca"), num_frames, dur, names_mini, parents_mini, frames)

bp_xra0100 = """UnitBlueprint {
    AI = {
        TargetBones = {
            'body',
            'head',
        },
    },
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
            Level1 = 1,
            Level2 = 2,
            Level3 = 3,
            Level4 = 4,
            Level5 = 5,
        },
    },
    BuildIconSortPriority = 15,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYRAPTORHIVE',
        'BUILTBYTIER1FACTORY',
        'CYBRAN',
        'RAPTOR',
        'MOBILE',
        'LAND',
        'TECH1',
        'DIRECTFIRE',
        'AMPHIBIOUS',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'BOT',
        'OVERLAYDIRECTFIRE',
    },
    CollisionOffsetY = 0,
    Defense = {
        AirThreatLevel = 0,
        ArmorType = 'Normal',
        EconomyThreatLevel = 0,
        Health = 85,
        MaxHealth = 85,
        RegenRate = 0.5,
        SubThreatLevel = 0,
        SurfaceThreatLevel = 1,
    },
    Description = '<LOC xra0100_desc>Mini Raptor Larva (Small Raider)',
    Display = {
        AnimationWalk = '/mods/RaptorFaction/units/XRA0100/XRA0100_Awalk.sca',
        AnimationWalkRate = 2.8,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0100/XRA0100_Albedo.dds',
                    LODCutoff = 240,
                    MeshName = '/mods/RaptorFaction/units/XRA0100/XRA0100_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0100/XRA0100_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0100/XRA0100_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        SpawnRandomRotation = true,
        UniformScale = 0.65,
    },
    Economy = {
        BuildCostEnergy = 80,
        BuildCostMass = 15,
        BuildTime = 60,
    },
    General = {
        Category = 'Direct Fire',
        Classification = 'RULEUC_MilitaryVehicle',
        CommandCaps = {
            RULEUCC_Attack = true,
            RULEUCC_CallTransport = true,
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
        TechLevel = 'RULEUTL_Basic',
        UnitName = '<LOC xra0100_name>Raptor Larva',
        UnitWeight = 1,
    },
    Intel = {
        VisionRadius = 16,
    },
    Interface = {
        HelpText = '<LOC xra0100_help>Ultra-cheap miniature swarmer that overwhelms enemy positions through immense numerical superiority.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.35,
    LifeBarSize = 0.5,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
            LAYER_Seabed = true,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 4.8,
        MaxBrake = 4.8,
        MaxSpeed = 4.8,
        MaxSpeedReverse = 0,
        MaxSteerForce = 15,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        RotateOnSpot = true,
        RotateOnSpotThreshold = 0.1,
        TurnRadius = 0,
        TurnRate = 240,
    },
    SelectionSizeX = 0.35,
    SelectionSizeZ = 0.5,
    SelectionThickness = 0.7,
    SizeX = 0.45,
    SizeY = 0.4,
    SizeZ = 0.7,
    StrategicIconName = 'icon_land1_directfire',
    StrategicIconSortPriority = 135,
    Veteran = {
        Level1 = 2,
        Level2 = 4,
        Level3 = 6,
        Level4 = 8,
        Level5 = 10,
    },
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
            BallisticArc = 'RULEUBA_LowArc',
            CollideFriendly = false,
            Damage = 14,
            DamageRadius = 0,
            DamageType = 'Normal',
            DisplayName = 'Larva Claws',
            FireTargetLayerCapsTable = {
                Air = 'Land|Water|Seabed',
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringRandomnessWhileMoving = 0,
            FiringTolerance = 3,
            Label = 'Claws',
            MaxRadius = 12,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            MuzzleVelocity = 30,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp',
            ProjectileLifetimeUsesMultiplier = 1.15,
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
            RackSlavedToTurret = false,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 2.0,
            SlavedToBody = true,
            SlavedToBodyArcRange = 35,
            TargetCheckInterval = 0.16,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'TECH1 MOBILE',
                'TECH2 MOBILE',
                'TECH3 MOBILE',
                'STRUCTURE DEFENSE',
                'SPECIALLOWPRI',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            TrackingRadius = 1.15,
            TurretBoneMuzzle = 'head',
            TurretBonePitch = 'aimy1',
            TurretBoneYaw = 'aimy1',
            TurretDualManipulators = false,
            TurretPitch = 0,
            TurretPitchRange = 25,
            TurretPitchSpeed = 180,
            TurretYaw = 0,
            TurretYawRange = 35,
            TurretYawSpeed = 180,
            Turreted = true,
            WeaponCategory = 'Direct Fire',
        },
    },
}
"""
with open(os.path.join(dir_xra0100, "XRA0100_unit.bp"), "w") as f:
    f.write(bp_xra0100)

script_xra0100 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon
local EffectTemplate = import('/lua/EffectTemplates.lua')

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class RaptorWeapon : DefaultProjectileWeapon
local RaptorWeapon = ClassWeapon(DefaultProjectileWeapon) {
    FxMuzzleFlash = EffectTemplate.PhasicAutoGunMuzzleFlash,

    CreateProjectileAtMuzzle = function(self, muzzle)
        local proj = DefaultProjectileWeapon.CreateProjectileAtMuzzle(self, muzzle)
        self.unit:PlayMandibladesAttack()
        return proj
    end,
}

---@class XRA0100 : CWalkingLandUnit
XRA0100 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Claws = ClassWeapon(RaptorWeapon) {},
        MainClaws = ClassWeapon(RaptorWeapon) {},
    },

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
        self.Rotators = {
            lforearm = CreateRotator(self, 'lforearm', 'y', 0, 700, 1200),
            rforearm = CreateRotator(self, 'rforearm', 'y', 0, 700, 1200),
            lblade = CreateRotator(self, 'lblade', 'y', 0, 700, 1200),
            rblade = CreateRotator(self, 'rblade', 'y', 0, 700, 1200),
        }
    end,

    PlayMandibladesAttack = function(self)
        if self.MandibleThread then
            KillThread(self.MandibleThread)
        end
        self.MandibleThread = self:ForkThread(self.MandibleAttackThread)
    end,

    MandibleAttackThread = function(self)
        local rot = self.Rotators
        if not rot then return end

        -- Snap mandiblades shut inward (matching BAR Shot1: -140 and 140 degrees)
        rot.lforearm:SetGoal(-140)
        rot.lforearm:SetSpeed(700)
        rot.rforearm:SetGoal(140)
        rot.rforearm:SetSpeed(700)
        rot.lblade:SetGoal(140)
        rot.lblade:SetSpeed(700)
        rot.rblade:SetGoal(-140)
        rot.rblade:SetSpeed(700)

        WaitFor(rot.rblade)

        -- Smoothly open back up
        rot.lforearm:SetGoal(0)
        rot.lforearm:SetSpeed(200)
        rot.rforearm:SetGoal(0)
        rot.rforearm:SetSpeed(200)
        rot.lblade:SetGoal(0)
        rot.lblade:SetSpeed(200)
        rot.rblade:SetGoal(0)
        rot.rblade:SetSpeed(200)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(0.8)
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        local scale = 0.8 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}

TypeClass = XRA0100
"""
with open(os.path.join(dir_xra0100, "XRA0100_script.lua"), "w") as f:
    f.write(script_xra0100)

print("Ported XRA0100 Mini Raptor Larva successfully.")

# ===========================================================================
# 2. XRA0111: BIO-RECON SCOUT (PIDGEON/AIR SCOUT)
# ===========================================================================
print("\n--- Porting XRA0111 (Bio-Recon Air Scout) ---")
s3o_scout = get_bar_file('objects3d/raptors/raptorairscout1.s3o')
pieces_scout = convert_s3o_to_scm(s3o_scout, os.path.join(dir_xra0111, "XRA0111_lod0.scm"))
names_scout = [p.name for p in pieces_scout]
parents_scout = [p.parent_idx for p in pieces_scout]

alb_scout = get_bar_file('unittextures/chicken_white_s_color.dds') or get_bar_file('unittextures/chicken_blue_s_color.dds')
with open(os.path.join(dir_xra0111, "XRA0111_Albedo.dds"), "wb") as f:
    f.write(alb_scout)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0111, "XRA0111_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0111, "XRA0111_SpecTeam.dds"))

ico_scout = get_bar_file('unitpics/raptors/raptorairscout.dds')
with open(os.path.join(dir_xra0111, "XRA0111_icon.dds"), "wb") as f:
    f.write(ico_scout)
with open(os.path.join(icons_dir, "xra0111_icon.dds"), "wb") as f:
    f.write(ico_scout)

# Rapid Flapping Animation
num_frames = 16
dur = 0.35
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    p = 2.0 * math.pi * t
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_scout}
    flap = math.sin(p) * math.radians(35.0)
    rot["liwing"] = (0, 0, flap)
    rot["riwing"] = (0, 0, -flap)
    rot["lowing"] = (0, 0, flap * 1.3)
    rot["rowing"] = (0, 0, -flap * 1.3)
    rot["body"] = (math.sin(p) * math.radians(4.0), 0, 0)
    time_sec = t * dur
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_scout):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0111, "XRA0111_Afly.sca"), num_frames, dur, names_scout, parents_scout, frames)

# Death Collapse
num_frames = 16
dur = 0.5
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    time_sec = t * dur
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_scout}
    rot["body"] = (math.radians(45.0) * t, math.radians(60.0) * t, 0)
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_scout):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0111, "XRA0111_Adeath01.sca"), num_frames, dur, names_scout, parents_scout, frames)

bp_xra0111 = """UnitBlueprint {
    Air = {
        AutoLandTime = 1,
        BankFactor = 1.5,
        CanFly = true,
        CombatTurnSpeed = 2.0,
        KMove = 1.5,
        KTurn = 2.0,
        LiftFactor = 12,
        MaxAirspeed = 18.0,
        MinAirspeed = 12.0,
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
    BuildIconSortPriority = 20,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYRAPTORHIVE',
        'BUILTBYTIER1FACTORY',
        'CYBRAN',
        'RAPTOR',
        'MOBILE',
        'AIR',
        'TECH1',
        'INTELLIGENCE',
        'SCOUT',
        'HIGHALTAIR',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYRADAR',
    },
    CollisionOffsetY = 0,
    Defense = {
        ArmorType = 'Light',
        Health = 90,
        MaxHealth = 90,
        RegenRate = 0.5,
    },
    Description = '<LOC xra0111_desc>High-Speed Biological Air Scout',
    Display = {
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0111/XRA0111_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0111/XRA0111_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0111/XRA0111_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0111/XRA0111_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.7,
    },
    Economy = {
        BuildCostEnergy = 550,
        BuildCostMass = 40,
        BuildTime = 200,
    },
    General = {
        Category = 'Utility',
        Classification = 'RULEUC_MilitaryAircraft',
        CommandCaps = {
            RULEUCC_Attack = false,
            RULEUCC_CallCycle = false,
            RULEUCC_Capture = false,
            RULEUCC_Dock = true,
            RULEUCC_Guard = true,
            RULEUCC_Move = true,
            RULEUCC_Nuke = false,
            RULEUCC_Patrol = true,
            RULEUCC_Reclaim = false,
            RULEUCC_Repair = false,
            RULEUCC_RetaliateToggle = false,
            RULEUCC_Stop = true,
            RULEUCC_Transport = false,
        },
        FactionName = 'Raptor',
        Icon = 'air',
        UnitName = '<LOC xra0111_name>Bio-Recon Scout',
    },
    Intel = {
        RadarRadius = 60,
        VisionRadius = 45,
    },
    Interface = {
        HelpText = '<LOC xra0111_help>Blindingly fast winged raptor with acute bio-sonar senses for broad battlefield reconnaissance.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.4,
    LifeBarSize = 0.75,
    Physics = {
        BankingSlope = 0.5,
        BuildOnLayerCaps = {
            LAYER_Air = true,
        },
        Elevation = 14.0,
        MaxSpeed = 18.0,
        MotionType = 'RULEUMT_Air',
    },
    SelectionSizeX = 0.85,
    SelectionSizeZ = 0.7,
    SelectionThickness = 0.6,
    SizeX = 0.9,
    SizeY = 0.3,
    SizeZ = 0.85,
    StrategicIconName = 'icon_fighter1_intel',
    StrategicIconSortPriority = 70,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            Damage = 50,
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
with open(os.path.join(dir_xra0111, "XRA0111_unit.bp"), "w") as f:
    f.write(bp_xra0111)

script_xra0111 = """local CAirUnit = import('/lua/cybranunits.lua').CAirUnit

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class XRA0111 : CAirUnit
XRA0111 = ClassUnit(CAirUnit) {
    OnCreate = function(self)
        CAirUnit.OnCreate(self)
        local flyAnim = CreateAnimator(self)
        flyAnim:PlayAnim('/mods/RaptorFaction/units/XRA0111/XRA0111_Afly.sca', true)
        flyAnim:SetRate(2.8)
        self.FlyAnim = flyAnim
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.0)
        end
        CAirUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.0)
        end
    end,
}

TypeClass = XRA0111
"""
with open(os.path.join(dir_xra0111, "XRA0111_script.lua"), "w") as f:
    f.write(script_xra0111)

print("Ported XRA0111 Bio-Recon Scout successfully.")

# ===========================================================================
# 3. XRA0203: BIO-EMP SHOCK TICK (ELECTRIC DODO)
# ===========================================================================
print("\n--- Porting XRA0203 (Bio-EMP Shock Tick) ---")
s3o_emp_dodo = get_bar_file('objects3d/raptors/raptor_dodo_electric.s3o')
pieces_emp_dodo = convert_s3o_to_scm(s3o_emp_dodo, os.path.join(dir_xra0203, "XRA0203_lod0.scm"))
names_emp_dodo = [p.name for p in pieces_emp_dodo]
parents_emp_dodo = [p.parent_idx for p in pieces_emp_dodo]

alb_emp_dodo = get_bar_file('unittextures/chicken_electric_m_color.dds') or get_bar_file('unittextures/chicken_electric_l_color.dds')
with open(os.path.join(dir_xra0203, "XRA0203_Albedo.dds"), "wb") as f:
    f.write(alb_emp_dodo)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0203, "XRA0203_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0203, "XRA0203_SpecTeam.dds"))

ico_emp_dodo = get_bar_file('unitpics/raptors/raptor_dodo1_electric.dds')
with open(os.path.join(dir_xra0203, "XRA0203_icon.dds"), "wb") as f:
    f.write(ico_emp_dodo)
with open(os.path.join(icons_dir, "xra0203_icon.dds"), "wb") as f:
    f.write(ico_emp_dodo)

# Walk & Death
shutil.copyfile(os.path.join(dir_xra0103, "XRA0103_Awalk.sca"), os.path.join(dir_xra0203, "XRA0203_Awalk.sca"))
shutil.copyfile(os.path.join(dir_xra0103, "XRA0103_Adeath01.sca"), os.path.join(dir_xra0203, "XRA0203_Adeath01.sca"))

bp_xra0203 = """UnitBlueprint {
    Audio = {
        Destroyed = Sound {
            Bank = 'Raptor_EMP_Launch',
            Cue = 'Attack',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Killed = Sound {
            Bank = 'Raptor_EMP_Launch',
            Cue = 'Attack',
            LodCutoff = 'UnitMove_LodCutoff',
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
        'LAND',
        'TECH2',
        'KAMIKAZE',
        'DIRECTFIRE',
        'AMPHIBIOUS',
        'VISIBLETORECON',
        'RECLAIMABLE',
    },
    CollisionOffsetY = 0,
    Defense = {
        ArmorType = 'Normal',
        Health = 280,
        MaxHealth = 280,
        RegenRate = 1.0,
    },
    Description = '<LOC xra0203_desc>Bio-EMP Shock Kamikaze & Shield Breaker',
    Display = {
        AnimationWalk = '/mods/RaptorFaction/units/XRA0203/XRA0203_Awalk.sca',
        AnimationWalkRate = 2.4,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0203/XRA0203_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0203/XRA0203_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0203/XRA0203_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0203/XRA0203_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.8,
    },
    Economy = {
        BuildCostEnergy = 1200,
        BuildCostMass = 120,
        BuildTime = 400,
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
        UnitName = '<LOC xra0203_name>Bio-EMP Shock Tick',
    },
    Intel = {
        VisionRadius = 20,
    },
    Interface = {
        HelpText = '<LOC xra0203_help>Bioluminescent electric tick filled with pressurized bio-plasma. Deals 2,500 damage to shields and paralyzes nearby enemy units in a 6-second EMP blast.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.6,
    LifeBarSize = 0.75,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 4.8,
        MaxBrake = 4.8,
        MaxSpeed = 4.8,
        MaxSpeedReverse = 0,
        MaxSteerForce = 15,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        RotateOnSpot = true,
        RotateOnSpotThreshold = 0.1,
        TurnRadius = 0,
        TurnRate = 220,
    },
    SelectionSizeX = 0.55,
    SelectionSizeZ = 0.65,
    SelectionThickness = 0.6,
    SizeX = 0.65,
    SizeY = 0.65,
    SizeZ = 0.95,
    StrategicIconName = 'icon_land2_bomb',
    StrategicIconSortPriority = 130,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            CollideFriendly = false,
            Damage = 450,
            DamageToShields = 2500,
            DamageFriendly = false,
            DamageRadius = 5.0,
            DamageType = 'Normal',
            DisplayName = 'Bio-EMP Detonation',
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
                'SHIELD',
                'TECH3 MOBILE',
                'TECH2 MOBILE',
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
with open(os.path.join(dir_xra0203, "XRA0203_unit.bp"), "w") as f:
    f.write(bp_xra0203)

script_xra0203 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local Weapon = import('/lua/sim/weapon.lua').Weapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class EMPSuicideWeapon : Weapon
local EMPSuicideWeapon = ClassWeapon(Weapon) {
    OnFire = function(self)
        local myUnit = self.unit
        local army = myUnit.Army
        local pos = myUnit:GetPosition()
        local brain = myUnit:GetAIBrain()
        if brain then
            local targets = brain:GetUnitsAroundPoint(categories.MOBILE + categories.STRUCTURE, pos, 5.0, 'Enemy')
            for _, t in targets do
                if not t.Dead then
                    t:SetStunned(6.0)
                    if t.MyShield and t.MyShield:IsOn() then
                        t.MyShield:ApplyDamage(2500)
                    end
                end
            end
        end
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(myUnit, army, emit):ScaleEmitter(2.5)
        end
        myUnit:Kill()
    end,
}

---@class XRA0203 : CWalkingLandUnit
XRA0203 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Suicide = ClassWeapon(EMPSuicideWeapon) {},
    },

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        local pos = self:GetPosition()
        local brain = self:GetAIBrain()
        if brain then
            local targets = brain:GetUnitsAroundPoint(categories.MOBILE + categories.STRUCTURE, pos, 5.0, 'Enemy')
            for _, t in targets do
                if not t.Dead then
                    t:SetStunned(6.0)
                    if t.MyShield and t.MyShield:IsOn() then
                        t.MyShield:ApplyDamage(2500)
                    end
                end
            end
        end
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.5)
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}

TypeClass = XRA0203
"""
with open(os.path.join(dir_xra0203, "XRA0203_script.lua"), "w") as f:
    f.write(script_xra0203)

print("Ported XRA0203 Bio-EMP Shock Tick successfully.")

# ===========================================================================
# 4. XRA0204: BROOD SWARM BOMBER (SPAWNING BOMBS)
# ===========================================================================
print("\n--- Porting XRA0204 (Brood Swarm Bomber) ---")
s3o_brood_b = get_bar_file('objects3d/raptors/raptorbroodbomber.s3o')
pieces_brood_b = convert_s3o_to_scm(s3o_brood_b, os.path.join(dir_xra0204, "XRA0204_lod0.scm"))
names_brood_b = [p.name for p in pieces_brood_b]
parents_brood_b = [p.parent_idx for p in pieces_brood_b]

alb_brood_b = get_bar_file('unittextures/chicken_purple_l_color.dds') or get_bar_file('unittextures/chicken_acidgreen_l_color.dds')
with open(os.path.join(dir_xra0204, "XRA0204_Albedo.dds"), "wb") as f:
    f.write(alb_brood_b)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0204, "XRA0204_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0204, "XRA0204_SpecTeam.dds"))

ico_brood_b = get_bar_file('unitpics/raptors/raptorbroodbomber.dds')
with open(os.path.join(dir_xra0204, "XRA0204_icon.dds"), "wb") as f:
    f.write(ico_brood_b)
with open(os.path.join(icons_dir, "xra0204_icon.dds"), "wb") as f:
    f.write(ico_brood_b)

# Fly and Death
shutil.copyfile(os.path.join(dir_xra0104, "XRA0104_Afly.sca"), os.path.join(dir_xra0204, "XRA0204_Afly.sca"))
shutil.copyfile(os.path.join(dir_xra0104, "XRA0104_Adeath01.sca"), os.path.join(dir_xra0204, "XRA0204_Adeath01.sca"))

bp_xra0204 = """UnitBlueprint {
    Air = {
        AutoLandTime = 1,
        BankFactor = 2.0,
        BreakOffDistance = 35,
        BreakOffTrigger = 20,
        CanFly = true,
        CombatTurnSpeed = 1.6,
        KMove = 1,
        KTurn = 1,
        LiftFactor = 10,
        MaxAirspeed = 10.5,
        MinAirspeed = 7.5,
        StartTurnDistance = 10,
        TurnSpeed = 1.6,
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
    BuildIconSortPriority = 35,
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
        'BOMBER',
        'HIGHALTAIR',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYINDIRECTFIRE',
    },
    CollisionOffsetY = 0,
    Defense = {
        ArmorType = 'Light',
        Health = 650,
        MaxHealth = 650,
        RegenRate = 1.0,
    },
    Description = '<LOC xra0204_desc>Brood Cluster Bomber (Living Swarm Salvos)',
    Display = {
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0204/XRA0204_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0204/XRA0204_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0204/XRA0204_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0204/XRA0204_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.5,
    },
    Economy = {
        BuildCostEnergy = 4200,
        BuildCostMass = 220,
        BuildTime = 1400,
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
        UnitName = '<LOC xra0204_name>Brood Swarm Bomber',
    },
    Intel = {
        VisionRadius = 32,
    },
    Interface = {
        HelpText = '<LOC xra0204_help>Living swarm bomber that drops egg cluster bombs. On impact, each bomb ruptures and births live Raptor Swarmers directly behind enemy defenses.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.6,
    LifeBarSize = 1.6,
    Physics = {
        BankingSlope = 0.5,
        BuildOnLayerCaps = {
            LAYER_Air = true,
        },
        Elevation = 10.5,
        MaxSpeed = 10.5,
        MotionType = 'RULEUMT_Air',
    },
    SelectionSizeX = 1.8,
    SelectionSizeZ = 1.4,
    SelectionThickness = 0.5,
    SizeX = 1.9,
    SizeY = 0.5,
    SizeZ = 1.9,
    StrategicIconName = 'icon_bomber2_directfire',
    StrategicIconSortPriority = 75,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            AutoInitiateAttackCommand = true,
            BallisticArc = 'RULEUBA_None',
            BombDropThreshold = 3,
            Damage = 150,
            DamageRadius = 3.0,
            DamageType = 'Normal',
            DisplayName = 'Brood Egg Bomb',
            FireTargetLayerCapsTable = {
                Air = 'Land|Water|Seabed',
            },
            FiringRandomness = 0.5,
            FiringTolerance = 3,
            Label = 'Bomb',
            MaxRadius = 45,
            MuzzleSalvoDelay = 0.2,
            MuzzleSalvoSize = 2,
            MuzzleVelocity = 0,
            NeedToComputeBombDrop = true,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_BroodEggBomb01/XRA_BroodEggBomb01_proj.bp',
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
            RateOfFire = 0.2,
            TargetCheckInterval = 1,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'STRUCTURE DEFENSE',
                'TECH3 MOBILE',
                'TECH2 MOBILE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
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
with open(os.path.join(dir_xra0204, "XRA0204_unit.bp"), "w") as f:
    f.write(bp_xra0204)

script_xra0204 = """local CAirUnit = import('/lua/cybranunits.lua').CAirUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class XRA0204 : CAirUnit
XRA0204 = ClassUnit(CAirUnit) {
    Weapons = {
        Bomb = ClassWeapon(DefaultProjectileWeapon) {},
    },

    OnCreate = function(self)
        CAirUnit.OnCreate(self)
        local flyAnim = CreateAnimator(self)
        flyAnim:PlayAnim('/mods/RaptorFaction/units/XRA0204/XRA0204_Afly.sca', true)
        flyAnim:SetRate(2.0)
        self.FlyAnim = flyAnim
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.8)
        end
        CAirUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}

TypeClass = XRA0204
"""
with open(os.path.join(dir_xra0204, "XRA0204_script.lua"), "w") as f:
    f.write(script_xra0204)

print("Ported XRA0204 Brood Swarm Bomber successfully.")

# ===========================================================================
# 5. XRA0206: PYRO ALL-TERRAIN RAPTOR (FLAMETHROWER)
# ===========================================================================
print("\n--- Porting XRA0206 (Pyro All-Terrain Raptor) ---")
s3o_pyro = get_bar_file('objects3d/raptors/raptorpyroallterrain.s3o')
pieces_pyro = convert_s3o_to_scm(s3o_pyro, os.path.join(dir_xra0206, "XRA0206_lod0.scm"))
names_pyro = [p.name for p in pieces_pyro]
parents_pyro = [p.parent_idx for p in pieces_pyro]

alb_pyro = get_bar_file('unittextures/chicken_red_l_color.dds') or get_bar_file('unittextures/chicken_crimson_l_color.dds')
with open(os.path.join(dir_xra0206, "XRA0206_Albedo.dds"), "wb") as f:
    f.write(alb_pyro)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0206, "XRA0206_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0206, "XRA0206_SpecTeam.dds"))

ico_pyro = get_bar_file('unitpics/raptors/raptorpyroallterrain.dds')
with open(os.path.join(dir_xra0206, "XRA0206_icon.dds"), "wb") as f:
    f.write(ico_pyro)
with open(os.path.join(icons_dir, "xra0206_icon.dds"), "wb") as f:
    f.write(ico_pyro)

# Quadruped Stride
num_frames = 24
dur = 0.8
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    p = 2.0 * math.pi * t
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_pyro}
    
    rot["lfthigh"] = (math.sin(p) * math.radians(24.0), 0, 0)
    rot["rfthigh"] = (-math.sin(p) * math.radians(24.0), 0, 0)
    rot["rbthigh"] = (math.sin(p) * math.radians(24.0), 0, 0)
    rot["lbthigh"] = (-math.sin(p) * math.radians(24.0), 0, 0)
    rot["body"] = (math.sin(p * 2.0) * math.radians(4.0), 0, 0)
    time_sec = t * dur
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_pyro):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0206, "XRA0206_Awalk.sca"), num_frames, dur, names_pyro, parents_pyro, frames)

# Death Collapse
num_frames = 16
dur = 0.6
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    time_sec = t * dur
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_pyro}
    rot["body"] = (math.radians(-25.0) * t, 0, 0)
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_pyro):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0206, "XRA0206_Adeath01.sca"), num_frames, dur, names_pyro, parents_pyro, frames)

bp_xra0206 = """UnitBlueprint {
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
    BuildIconSortPriority = 50,
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
        'TECH2',
        'DIRECTFIRE',
        'AMPHIBIOUS',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYDIRECTFIRE',
    },
    CollisionOffsetY = 0,
    Defense = {
        ArmorType = 'Normal',
        Health = 1200,
        MaxHealth = 1200,
        RegenRate = 2.0,
    },
    Description = '<LOC xra0206_desc>All-Terrain Bio-Flamethrower',
    Display = {
        AnimationWalk = '/mods/RaptorFaction/units/XRA0206/XRA0206_Awalk.sca',
        AnimationWalkRate = 1.5,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0206/XRA0206_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0206/XRA0206_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0206/XRA0206_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0206/XRA0206_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 1.05,
    },
    Economy = {
        BuildCostEnergy = 1600,
        BuildCostMass = 190,
        BuildTime = 900,
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
        UnitName = '<LOC xra0206_name>Pyro Raptor',
    },
    Intel = {
        VisionRadius = 22,
    },
    Interface = {
        HelpText = '<LOC xra0206_help>All-terrain fire bug that sprays high-temperature biological liquid napalm, roasting defenses and piercing armor.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.7,
    LifeBarSize = 0.95,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 3.6,
        MaxBrake = 3.6,
        MaxSpeed = 3.6,
        MaxSpeedReverse = 0,
        MaxSteerForce = 15,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        RotateOnSpot = true,
        RotateOnSpotThreshold = 0.1,
        TurnRadius = 0,
        TurnRate = 180,
    },
    SelectionCenterOffsetX = 0,
    SelectionCenterOffsetZ = -0.15,
    SelectionSizeX = 0.85,
    SelectionSizeZ = 1.05,
    SelectionThickness = 0.55,
    SizeX = 1.0,
    SizeY = 0.8,
    SizeZ = 1.5,
    CollisionOffsetY = 0.25,
    StrategicIconName = 'icon_land2_directfire',
    StrategicIconSortPriority = 120,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Flamer',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            AutoInitiateAttackCommand = false,
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            Damage = 35,
            DamageRadius = 1.5,
            DamageType = 'Normal',
            DisplayName = 'Bio Napalm Spray',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 2,
            Label = 'MainGun',
            MaxRadius = 18,
            MuzzleSalvoDelay = 0.05,
            MuzzleSalvoSize = 5,
            MuzzleVelocity = 28,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_PyroStream01/XRA_PyroStream01_proj.bp',
            RackBones = {
                {
                    MuzzleBones = {
                        'flare',
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
            RateOfFire = 1.5,
            TargetCheckInterval = 0.25,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'TECH2 MOBILE',
                'TECH1 MOBILE',
                'STRUCTURE DEFENSE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            TurretBoneMuzzle = 'flare',
            TurretBonePitch = 'head',
            TurretBoneYaw = 'aimy1',
            TurretPitch = 0,
            TurretPitchRange = 50,
            TurretPitchSpeed = 80,
            TurretYaw = 0,
            TurretYawRange = 180,
            TurretYawSpeed = 90,
            Turreted = true,
            WeaponCategory = 'Direct Fire',
        },
    },
}
"""
with open(os.path.join(dir_xra0206, "XRA0206_unit.bp"), "w") as f:
    f.write(bp_xra0206)

script_xra0206 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BioFlameWeapon = ClassWeapon(DefaultProjectileWeapon) {
    FxMuzzleFlash = {
        '/mods/RaptorFaction/effects/emitters/raptor_bio_flame_muzzle_01_emit.bp',
        '/effects/emitters/default_muzzle_flash_01_emit.bp',
    },
    FxMuzzleFlashScale = 0.7,
}

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class XRA0206 : CWalkingLandUnit
XRA0206 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        MainGun = ClassWeapon(BioFlameWeapon) {},
    },

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.5)
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}

TypeClass = XRA0206
"""
with open(os.path.join(dir_xra0206, "XRA0206_script.lua"), "w") as f:
    f.write(script_xra0206)

print("Ported XRA0206 Pyro All-Terrain Raptor successfully.")

# ===========================================================================
# 6. XRA0302: PSYCHIC BRAIN BUG (OVERSEER / STEALTH JAMMER)
# ===========================================================================
print("\n--- Porting XRA0302 (Psychic Brain Bug Overseer) ---")
s3o_brain = get_bar_file('objects3d/raptors/brain_bug.s3o')
pieces_brain = convert_s3o_to_scm(s3o_brain, os.path.join(dir_xra0302, "XRA0302_lod0.scm"))
names_brain = [p.name for p in pieces_brain]
parents_brain = [p.parent_idx for p in pieces_brain]

alb_brain = get_bar_file('unittextures/chicken_purple_l_color.dds') or get_bar_file('unittextures/chicken_electric_l_color.dds')
with open(os.path.join(dir_xra0302, "XRA0302_Albedo.dds"), "wb") as f:
    f.write(alb_brain)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0302, "XRA0302_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0302, "XRA0302_SpecTeam.dds"))

ico_brain = get_bar_file('unitpics/raptors/raptorh5.dds')
with open(os.path.join(dir_xra0302, "XRA0302_icon.dds"), "wb") as f:
    f.write(ico_brain)
with open(os.path.join(icons_dir, "xra0302_icon.dds"), "wb") as f:
    f.write(ico_brain)

# Slow Stately Hover / Walk
num_frames = 24
dur = 1.0
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    p = 2.0 * math.pi * t
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_brain}
    rot["lthigh"] = (math.sin(p) * math.radians(20.0), 0, 0)
    rot["rthigh"] = (-math.sin(p) * math.radians(20.0), 0, 0)
    rot["body"] = (math.sin(p * 2.0) * math.radians(3.0), 0, 0)
    rot["head"] = (math.sin(p * 2.0) * math.radians(6.0), 0, 0)
    time_sec = t * dur
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_brain):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0302, "XRA0302_Awalk.sca"), num_frames, dur, names_brain, parents_brain, frames)

# Death
num_frames = 20
dur = 0.8
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    time_sec = t * dur
    rot = {}
    pos = {p_node.name: p_node.local_pos for p_node in pieces_brain}
    rot["body"] = (math.radians(-30.0) * t, 0, 0)
    frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_brain):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if f_idx == 0 and b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos[b_name]
        frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0302, "XRA0302_Adeath01.sca"), num_frames, dur, names_brain, parents_brain, frames)

bp_xra0302 = """UnitBlueprint {
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
    BuildIconSortPriority = 15,
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
        'INTELLIGENCE',
        'RADAR',
        'COUNTERINTELLIGENCE',
        'DIRECTFIRE',
        'AMPHIBIOUS',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYRADAR',
        'OVERLAYOMNI',
    },
    CollisionOffsetY = 0,
    Defense = {
        ArmorType = 'Normal',
        Health = 3800,
        MaxHealth = 3800,
        RegenRate = 3.0,
    },
    Description = '<LOC xra0302_desc>Psychic Overseer (Omni-Radar & Stealth Jammer)',
    Display = {
        AnimationWalk = '/mods/RaptorFaction/units/XRA0302/XRA0302_Awalk.sca',
        AnimationWalkRate = 1.0,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0302/XRA0302_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0302/XRA0302_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0302/XRA0302_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0302/XRA0302_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.6,
    },
    Economy = {
        BuildCostEnergy = 6000,
        BuildCostMass = 480,
        BuildTime = 2400,
        MaintenanceConsumptionPerSecondEnergy = 25,
    },
    General = {
        Category = 'Intelligence',
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
        OrderOverrides = {
            RULEUTC_StealthToggle = {
                bitmapId = 'stealth-field',
                helpText = 'toggle_stealth_field',
            },
        },
        ToggleCaps = {
            RULEUTC_StealthToggle = true,
        },
        UnitName = '<LOC xra0302_name>Brain Bug Overseer',
    },
    Intel = {
        OmniRadius = 25,
        RadarRadius = 75,
        RadarStealthFieldRadius = 24,
        VisionRadius = 45,
    },
    Interface = {
        HelpText = '<LOC xra0302_help>Giant psychic command bug that projects broad omni-vision, biological radar, stealth cloaking fields, and disruptive neuro-blasts.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.85,
    LifeBarSize = 1.3,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 2.4,
        MaxBrake = 2.4,
        MaxSpeed = 2.4,
        MaxSpeedReverse = 0,
        MaxSteerForce = 15,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        RotateOnSpot = true,
        RotateOnSpotThreshold = 0.1,
        TurnRadius = 0,
        TurnRate = 80,
    },
    SelectionSizeX = 1.1,
    SelectionSizeZ = 1.4,
    SelectionThickness = 0.5,
    SizeX = 1.3,
    SizeY = 1.1,
    SizeZ = 1.8,
    StrategicIconName = 'icon_land3_intel',
    StrategicIconSortPriority = 110,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Electric',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            AutoInitiateAttackCommand = true,
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            Damage = 250,
            DamageRadius = 4.0,
            DamageType = 'Normal',
            DisplayName = 'Neuro Psionic Blast',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 2,
            Label = 'MainGun',
            MaxRadius = 32,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            MuzzleVelocity = 35,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_NeuroBlast01/XRA_NeuroBlast01_proj.bp',
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
            RateOfFire = 0.5,
            TargetCheckInterval = 0.5,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'TECH3 MOBILE',
                'TECH2 MOBILE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            TurretBoneMuzzle = 'headfirepoint',
            TurretBonePitch = 'head',
            TurretBoneYaw = 'aimy1',
            TurretPitch = 0,
            TurretPitchRange = 40,
            TurretPitchSpeed = 40,
            TurretYaw = 0,
            TurretYawRange = 180,
            TurretYawSpeed = 50,
            Turreted = true,
            WeaponCategory = 'Direct Fire',
        },
    },
}
"""
with open(os.path.join(dir_xra0302, "XRA0302_unit.bp"), "w") as f:
    f.write(bp_xra0302)

script_xra0302 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class XRA0302 : CWalkingLandUnit
XRA0302 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        MainGun = ClassWeapon(DefaultProjectileWeapon) {},
    },

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.2)
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}

TypeClass = XRA0302
"""
with open(os.path.join(dir_xra0302, "XRA0302_script.lua"), "w") as f:
    f.write(script_xra0302)

print("Ported XRA0302 Psychic Brain Bug successfully.")

# ===========================================================================
# 7. XRA0303: RAPTOR MATRIARCH (MINI-QUEEN SUB-BOSS)
# ===========================================================================
print("\n--- Porting XRA0303 (Raptor Matriarch Mini-Queen) ---")
s3o_matriarch = get_bar_file('objects3d/raptors/raptor_miniqueen_basic.s3o')
pieces_matriarch = convert_s3o_to_scm(s3o_matriarch, os.path.join(dir_xra0303, "XRA0303_lod0.scm"))
names_matriarch = [p.name for p in pieces_matriarch]
parents_matriarch = [p.parent_idx for p in pieces_matriarch]

alb_matriarch = get_bar_file('unittextures/chicken_vcrimson_l_color.dds') or get_bar_file('unittextures/chicken_crimson_l_color.dds')
with open(os.path.join(dir_xra0303, "XRA0303_Albedo.dds"), "wb") as f:
    f.write(alb_matriarch)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0303, "XRA0303_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0303, "XRA0303_SpecTeam.dds"))

ico_matriarch = get_bar_file('unitpics/raptors/raptor_miniqueen_basic.dds')
with open(os.path.join(dir_xra0303, "XRA0303_icon.dds"), "wb") as f:
    f.write(ico_matriarch)
with open(os.path.join(icons_dir, "xra0303_icon.dds"), "wb") as f:
    f.write(ico_matriarch)

# Dedicated Animations for Matriarch using pieces_matriarch rest positions
pos_matriarch = {p.name: p.local_pos for p in pieces_matriarch}

# 1. Walk Animation
num_frames = 32
dur = 1.2
walk_frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    phase_A = 2.0 * math.pi * t
    phase_B = phase_A + math.pi
    rot = {}
    rot['lthighf'] = (math.sin(phase_A) * math.radians(22.0), 0, 0)
    rot['lkneef'] = (-max(0.0, -math.sin(phase_A)) * math.radians(28.0), 0, 0)
    rot['rthighb'] = (math.sin(phase_A) * math.radians(22.0), 0, 0)
    rot['rkneeb'] = (-max(0.0, -math.sin(phase_A)) * math.radians(28.0), 0, 0)
    rot['rthighf'] = (math.sin(phase_B) * math.radians(22.0), 0, 0)
    rot['rkneef'] = (-max(0.0, -math.sin(phase_B)) * math.radians(28.0), 0, 0)
    rot['lthighb'] = (math.sin(phase_B) * math.radians(22.0), 0, 0)
    rot['lkneeb'] = (-max(0.0, -math.sin(phase_B)) * math.radians(28.0), 0, 0)
    rot['body'] = (math.sin(phase_A * 2.0) * math.radians(3.5), 0, math.cos(phase_A) * math.radians(2.5))
    rot['tail'] = (-math.sin(phase_A * 2.0) * math.radians(6.0), math.sin(phase_A) * math.radians(14.0), 0)
    rot['head'] = (-math.sin(phase_A * 2.0) * math.radians(2.5), 0, 0)
    rot['rforearmu'] = (math.sin(phase_A) * math.radians(12.0), 0, 0)
    rot['lforearmu'] = (-math.sin(phase_A) * math.radians(12.0), 0, 0)
    time_sec = t * dur
    walk_frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_matriarch):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos_matriarch[b_name]
        walk_frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0303, "XRA0303_Awalk.sca"), num_frames, dur, names_matriarch, parents_matriarch, walk_frames)

# 2. Roar Animation
num_frames = 24
dur = 1.1
roar_frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    time_sec = t * dur
    rot = {}
    roar = math.sin(math.pi * t)
    rot['body'] = (roar * math.radians(18.0), 0, 0)
    rot['head'] = (roar * math.radians(22.0), 0, 0)
    rot['rforearmu'] = (0, roar * math.radians(30.0), 0)
    rot['lforearmu'] = (0, -roar * math.radians(30.0), 0)
    rot['rforearml'] = (roar * math.radians(20.0), 0, 0)
    rot['lforearml'] = (roar * math.radians(20.0), 0, 0)
    roar_frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_matriarch):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos_matriarch[b_name]
        roar_frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0303, "XRA0303_Aroar.sca"), num_frames, dur, names_matriarch, parents_matriarch, roar_frames)

# 3. Death Animation
num_frames = 36
dur = 1.5
death_frames = []
for f_idx in range(num_frames):
    t = f_idx / (num_frames - 1)
    time_sec = t * dur
    rot = {}
    rot['body'] = (math.radians(-30.0) * t, 0, math.radians(8.0) * t)
    rot['head'] = (math.radians(-20.0) * t, 0, 0)
    rot['lthighf'] = (math.radians(25.0) * t, 0, math.radians(20.0) * t)
    rot['rthighf'] = (math.radians(25.0) * t, 0, -math.radians(20.0) * t)
    rot['lthighb'] = (-math.radians(20.0) * t, 0, math.radians(25.0) * t)
    rot['rthighb'] = (-math.radians(20.0) * t, 0, -math.radians(25.0) * t)
    death_frames.extend([time_sec, 0])
    for b_idx, b_name in enumerate(names_matriarch):
        rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        if b_idx == 0:
            px, py, pz = 0.0, 0.0, 0.0
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
        else:
            px, py, pz = pos_matriarch[b_name]
        death_frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(os.path.join(dir_xra0303, "XRA0303_Adeath01.sca"), num_frames, dur, names_matriarch, parents_matriarch, death_frames)

bp_xra0303 = """UnitBlueprint {
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
            Level1 = 5,
            Level2 = 10,
            Level3 = 15,
        },
    },
    BuildIconSortPriority = 12,
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
    CollisionOffsetY = 0.2,
    Defense = {
        ArmorType = 'Heavy',
        Health = 18000,
        MaxHealth = 18000,
        RegenRate = 8.0,
    },
    Description = '<LOC xra0303_desc>Raptor Matriarch (Sub-Boss Commander)',
    Display = {
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0303/XRA0303_Adeath01.sca',
                AnimationRateMax = 1.0,
                AnimationRateMin = 0.8,
                Weight = 100,
            },
        },
        AnimationWalk = '/mods/RaptorFaction/units/XRA0303/XRA0303_Awalk.sca',
        AnimationWalkRate = 1.0,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0303/XRA0303_Albedo.dds',
                    LODCutoff = 280,
                    MeshName = '/mods/RaptorFaction/units/XRA0303/XRA0303_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0303/XRA0303_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0303/XRA0303_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.55,
    },
    Economy = {
        BuildCostEnergy = 32000,
        BuildCostMass = 2600,
        BuildTime = 8400,
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
        FactionName = 'Cybran',
        Icon = 'amph',
        UnitName = '<LOC xra0303_name>Raptor Matriarch',
    },
    Intel = {
        VisionRadius = 32,
    },
    Interface = {
        HelpText = '<LOC xra0303_help>Formidable sub-boss matriarch raptor armed with concentrated bio-plasma, heavy scythe cleaves, and defensive anti-air spores.',
    },
    LifeBarHeight = 0.1,
    LifeBarOffset = 1.6,
    LifeBarSize = 2.2,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 2.6,
        MaxBrake = 2.6,
        MaxSpeed = 2.6,
        MaxSpeedReverse = 0,
        MaxSteerForce = 15,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        RotateOnSpot = true,
        RotateOnSpotThreshold = 0.1,
        TurnRadius = 0,
        TurnRate = 80,
    },
    SelectionSizeX = 1.8,
    SelectionSizeZ = 2.4,
    SelectionThickness = 0.45,
    SizeX = 2.2,
    SizeY = 2.2,
    SizeZ = 3.5,
    StrategicIconName = 'icon_land3_directfire',
    StrategicIconSortPriority = 100,
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
            Damage = 750,
            DamageRadius = 2.5,
            DamageType = 'Normal',
            DisplayName = 'Corrosive Plasma Blob',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 2,
            Label = 'PlasmaBlob',
            MaxRadius = 36,
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
            RateOfFire = 0.5,
            TargetCheckInterval = 0.5,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'TECH3 MOBILE',
                'TECH2 MOBILE',
                'STRUCTURE DEFENSE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            TurretBoneMuzzle = 'head',
            TurretBonePitch = 'head',
            TurretBoneYaw = 'aimy1',
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
                    Bank = 'Raptor_Heavy_Attack',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            Damage = 450,
            DamageRadius = 1.5,
            DamageType = 'Normal',
            DisplayName = 'Scythe Cleave',
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
            Damage = 45,
            DamageType = 'Normal',
            DisplayName = 'Bio-Spores',
            FireTargetLayerCapsTable = {
                Land = 'Air',
                Water = 'Air',
            },
            FiringTolerance = 2,
            Label = 'AASpores',
            MaxRadius = 35,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
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
            RangeCategory = 'UWRC_AntiAir',
            RateOfFire = 1.5,
            TargetCheckInterval = 0.3,
            TargetPriorities = {
                'SPECIALHIGHPRI',
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
with open(os.path.join(dir_xra0303, "XRA0303_unit.bp"), "w") as f:
    f.write(bp_xra0303)

script_xra0303 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon
local Eggs = import('/mods/RaptorFaction/lua/RaptorEggs.lua')

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class XRA0303 : CWalkingLandUnit
XRA0303 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        PlasmaBlob = ClassWeapon(DefaultProjectileWeapon) {},
        MeleeCleave = ClassWeapon(DefaultProjectileWeapon) {},
        AASpores = ClassWeapon(DefaultProjectileWeapon) {},
    },

    CreateWreckage = function(self, overkillRatio)
        return nil
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(3.5)
        end
        Eggs.SpawnRaptorEgg(self)
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}

TypeClass = XRA0303
"""
with open(os.path.join(dir_xra0303, "XRA0303_script.lua"), "w") as f:
    f.write(script_xra0303)

print("Ported XRA0303 Raptor Matriarch successfully.")

# ===========================================================================
# 8. XRA0310: BEHEMOTH HEAVY DODO (HEAVY SUICIDE BOMB)
# ===========================================================================
print("\n--- Porting XRA0310 (Behemoth Heavy Dodo - Heavy Version) ---")
s3o_big_dodo = get_bar_file('objects3d/raptors/big_raptor_dodo.s3o')
pieces_big_dodo = convert_s3o_to_scm(s3o_big_dodo, os.path.join(dir_xra0310, "XRA0310_lod0.scm"))
names_big_dodo = [p.name for p in pieces_big_dodo]
parents_big_dodo = [p.parent_idx for p in pieces_big_dodo]

alb_big_dodo = get_bar_file('unittextures/chicken_apex_l_color.dds') or get_bar_file('unittextures/chicken_red_l_color.dds')
with open(os.path.join(dir_xra0310, "XRA0310_Albedo.dds"), "wb") as f:
    f.write(alb_big_dodo)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0310, "XRA0310_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0310, "XRA0310_SpecTeam.dds"))

ico_big_dodo = get_bar_file('unitpics/raptors/raptor_dodo2.dds')
with open(os.path.join(dir_xra0310, "XRA0310_icon.dds"), "wb") as f:
    f.write(ico_big_dodo)
with open(os.path.join(icons_dir, "xra0310_icon.dds"), "wb") as f:
    f.write(ico_big_dodo)

# Walk & Death
shutil.copyfile(os.path.join(dir_xra0103, "XRA0103_Awalk.sca"), os.path.join(dir_xra0310, "XRA0310_Awalk.sca"))
shutil.copyfile(os.path.join(dir_xra0103, "XRA0103_Adeath01.sca"), os.path.join(dir_xra0310, "XRA0310_Adeath01.sca"))

bp_xra0310 = """UnitBlueprint {
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
    BuildIconSortPriority = 35,
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
        'KAMIKAZE',
        'DIRECTFIRE',
        'AMPHIBIOUS',
        'VISIBLETORECON',
        'RECLAIMABLE',
    },
    CollisionOffsetY = 0,
    Defense = {
        ArmorType = 'Heavy',
        Health = 3400,
        MaxHealth = 3400,
        RegenRate = 3.0,
    },
    Description = '<LOC xra0310_desc>Behemoth Heavy Acid Dodo (Cratering Bomb)',
    Display = {
        AnimationWalk = '/mods/RaptorFaction/units/XRA0310/XRA0310_Awalk.sca',
        AnimationWalkRate = 1.8,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0310/XRA0310_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0310/XRA0310_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0310/XRA0310_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0310/XRA0310_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.85,
    },
    Economy = {
        BuildCostEnergy = 6800,
        BuildCostMass = 650,
        BuildTime = 2200,
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
        UnitName = '<LOC xra0310_name>Behemoth Heavy Dodo',
    },
    Intel = {
        VisionRadius = 24,
    },
    Interface = {
        HelpText = '<LOC xra0310_help>Colossal heavily armored suicide bug that detonates in a cataclysmic 3,500 damage acid explosion, obliterating hardened base perimeters.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.85,
    LifeBarSize = 1.1,
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
        TurnRate = 160,
    },
    SelectionSizeX = 0.85,
    SelectionSizeZ = 1.1,
    SelectionThickness = 0.5,
    SizeX = 1.0,
    SizeY = 1.1,
    SizeZ = 1.6,
    StrategicIconName = 'icon_land3_bomb',
    StrategicIconSortPriority = 125,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            CollideFriendly = false,
            Damage = 3500,
            DamageFriendly = true,
            DamageRadius = 6.0,
            DamageType = 'Normal',
            DisplayName = 'Cataclysmic Acid Crater Detonation',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 180,
            Label = 'Suicide',
            MaxRadius = 2.5,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1,
            SlavedToBody = true,
            TargetCheckInterval = 0.1,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'EXPERIMENTAL',
                'TECH3 MOBILE',
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
with open(os.path.join(dir_xra0310, "XRA0310_unit.bp"), "w") as f:
    f.write(bp_xra0310)

script_xra0310 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local Weapon = import('/lua/sim/weapon.lua').Weapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class BigDodoSuicideWeapon : Weapon
local BigDodoSuicideWeapon = ClassWeapon(Weapon) {
    OnFire = function(self)
        local myUnit = self.unit
        local army = myUnit.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(myUnit, army, emit):ScaleEmitter(4.0)
        end
        myUnit:Kill()
    end,
}

---@class XRA0310 : CWalkingLandUnit
XRA0310 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Suicide = ClassWeapon(BigDodoSuicideWeapon) {},
    },

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(4.0)
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}

TypeClass = XRA0310
"""
with open(os.path.join(dir_xra0310, "XRA0310_script.lua"), "w") as f:
    f.write(script_xra0310)

print("Ported XRA0310 Behemoth Heavy Dodo successfully.")

# ===========================================================================
# UPDATE MOD INFO & EXPORT ARCHIVE
# ===========================================================================
mod_info_path = os.path.join(mod_dir, "mod_info.lua")
mod_info_content = """name = "Raptor Swarm Faction"
version = 6
copyright = "Beyond All Reason & FAF Communities"
description = "Exhaustive, 100% complete standalone biological Raptor Swarm race ported directly from Beyond All Reason (BAR). Features 31 production-ready units across T1, T2, T3, and T4 Experimental! Includes small & heavy versions (Mini Swarmers, Behemoth Heavy Dodos), Electric EMP Shock Ticks with shield disrupters, Brood Bombers with living swarmer-spawning egg salvos, Pyro All-Terrain Flamers, the Psychic Brain Bug Overseer (omni-vision & radar stealth jammer), the Raptor Matriarch Sub-Boss, and the Experimental Raptor Queen Titan!"
author = "BAR & FAF"
uid = "raptor-swarm-faction-faf-0006"
selectable = true
enabled = true
exclusive = false
ui_only = false
requires = {}
"""
with open(mod_info_path, "w") as f:
    f.write(mod_info_content)

export_zip = os.path.join(os.path.dirname(__file__), "exports", "RaptorFaction.zip")
print(f"\nPackaging full complete standalone mod to {export_zip}...")
with zipfile.ZipFile(export_zip, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(mod_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(mod_dir))
            z.write(full_path, rel_path)

print(f"\nSUCCESS: Exported {os.path.getsize(export_zip):,} bytes to {export_zip}")
print("ALL REMAINING BAR RAPTOR UNITS PORTED SUCCESSFULLY!")
