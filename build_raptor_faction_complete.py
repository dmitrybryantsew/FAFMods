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

# Existing unit directories
dir_xra0101 = os.path.join(units_root, "XRA0101")
dir_xra0105 = os.path.join(units_root, "XRA0105")
dir_xra0201 = os.path.join(units_root, "XRA0201")
dir_xra0106 = os.path.join(units_root, "XRA0106")
dir_xra0107 = os.path.join(units_root, "XRA0107")
dir_xra0108 = os.path.join(units_root, "XRA0108")
dir_xra0208 = os.path.join(units_root, "XRA0208")

# New unit directories
dir_xra0109 = os.path.join(units_root, "XRA0109") # Raptor Bio-Weaver (Builder)
dir_xra0304 = os.path.join(units_root, "XRA0304") # Bio-Nuke Silo
dir_xra0305 = os.path.join(units_root, "XRA0305") # Anti-Nuke Silo
dir_xra0306 = os.path.join(units_root, "XRA0306") # Brood Artillery (Unit Spawning)
dir_xra0307 = os.path.join(units_root, "XRA0307") # EMP Artillery
dir_xra0308 = os.path.join(units_root, "XRA0308") # Acid Artillery
dir_xra0309 = os.path.join(units_root, "XRA0309") # Meteor Artillery

# Projectiles
dir_proj_brood = os.path.join(proj_root, "XRA_BroodShell01")
dir_proj_emp = os.path.join(proj_root, "XRA_ElectroShell01")
dir_proj_acid = os.path.join(proj_root, "XRA_AcidShell01")
dir_proj_meteor = os.path.join(proj_root, "XRA_MeteorShell01")
dir_proj_nuke = os.path.join(proj_root, "XRA_BioNuke01")
dir_proj_antinuke = os.path.join(proj_root, "XRA_AntiNuke01")

all_new_dirs = [
    icons_dir, dir_xra0109, dir_xra0304, dir_xra0305, dir_xra0306, dir_xra0307, dir_xra0308, dir_xra0309,
    dir_proj_brood, dir_proj_emp, dir_proj_acid, dir_proj_meteor, dir_proj_nuke, dir_proj_antinuke,
    raptor_sounds_dir
]
for d in all_new_dirs:
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
# Universal S3O -> SCM Conversion Function
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
# SCA Generator Helper Functions
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

# Generate Audio Banks for Endgame Systems
advanced_audio = [
    ('Raptor_Nuke_Launch', 'Raptor_Nuke_Launch', 'Nuke', 'sounds/raptors/raptor_nuke.wav', 'raptor_nuke.wav'),
    ('Raptor_Nuke_Explosion', 'Raptor_Nuke_Explosion', 'Explosion', 'sounds/raptors/cxplonuk4.wav', 'cxplonuk4.wav'),
    ('Raptor_AntiNuke_Launch', 'Raptor_AntiNuke_Launch', 'Launch', 'sounds/weapons/antinukelaunch.wav', 'antinukelaunch.wav'),
    ('Raptor_EMP_Launch', 'Raptor_EMP_Launch', 'Attack', 'sounds/raptors/empbomb.wav', 'empbomb.wav'),
    ('Raptor_Arty_Launch', 'Raptor_Arty_Launch', 'Attack', 'sounds/raptors/bugarty.wav', 'bugarty.wav'),
]

for sb_name, wb_name, cue, bar_path, fname in advanced_audio:
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
# 1. BUILD RAPTOR BIO-WEAVER (BUILDER / ENGINEER) - XRA0109
# ===========================================================================
print("\n" + "="*70)
print("BUILDING XRA0109: Raptor Bio-Weaver (Mobile Builder & Engineer)")
print("="*70)

# Uses swarmer model as requested
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_lod0.scm"), os.path.join(dir_xra0109, "XRA0109_lod0.scm"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_Albedo.dds"), os.path.join(dir_xra0109, "XRA0109_Albedo.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0109, "XRA0109_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0109, "XRA0109_SpecTeam.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_Awalk.sca"), os.path.join(dir_xra0109, "XRA0109_Awalk.sca"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_Adeath01.sca"), os.path.join(dir_xra0109, "XRA0109_Adeath01.sca"))

# Icon
icon_healer = get_bar_file('unitpics/raptors/raptorhealer.dds')
if icon_healer:
    with open(os.path.join(dir_xra0109, "XRA0109_icon.dds"), "wb") as f:
        f.write(icon_healer)
    with open(os.path.join(icons_dir, "xra0109_icon.dds"), "wb") as f:
        f.write(icon_healer)

bp_weaver = """UnitBlueprint {
    AI = {
        TargetBones = {
            'body',
            'head',
        },
    },
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
            Level4 = 8,
            Level5 = 10,
        },
    },
    BuildIconSortPriority = 20,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYRAPTORHIVE',
        'RAPTOR',
        'MOBILE',
        'LAND',
        'TECH1',
        'CONSTRUCTION',
        'ENGINEER',
        'REPAIR',
        'RECLAIM',
        'PATROLHELPER',
        'SHOWQUEUE',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'SORTCONSTRUCTION',
    },
    CollisionOffsetY = 0.5,
    Defense = {
        AirThreatLevel = 0,
        ArmorType = 'Normal',
        EconomyThreatLevel = 1,
        Health = 220,
        MaxHealth = 220,
        RegenRate = 3,
        SubThreatLevel = 0,
        SurfaceThreatLevel = 0,
    },
    Description = '<LOC xra0109_desc>Biological Builder & Structure Weaver',
    Display = {
        Abilities = {
            '<LOC ability_engineeringsuite>Engineering Suite',
            'Bio-Structure Weaving',
            'Living Bio-Carapace Regen',
        },
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0109/XRA0109_Adeath01.sca',
                AnimationRateMax = 1.2,
                AnimationRateMin = 0.8,
                Weight = 100,
            },
        },
        AnimationWalk = '/mods/RaptorFaction/units/XRA0109/XRA0109_Awalk.sca',
        AnimationWalkRate = 1.6,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0109/XRA0109_Albedo.dds',
                    LODCutoff = 250,
                    MeshName = '/mods/RaptorFaction/units/XRA0109/XRA0109_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0109/XRA0109_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0109/XRA0109_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 1.0,
    },
    Economy = {
        BuildCostEnergy = 260,
        BuildCostMass = 55,
        BuildRate = 15,
        BuildTime = 260,
        BuildableCategory = {
            'RAPTOR STRUCTURE',
        },
        MaxBuildDistance = 6,
    },
    General = {
        BuildBones = {
            AimBone = 'head',
            BuildEffectBones = {
                'head',
                'lscythe',
                'rscythe',
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
            RULEUCC_Pause = true,
            RULEUCC_Reclaim = true,
            RULEUCC_Repair = true,
            RULEUCC_RetaliateToggle = false,
            RULEUCC_Stop = true,
            RULEUCC_Tactical = false,
            RULEUCC_Transport = false,
        },
        ConstructionBar = true,
        FactionName = 'Raptor',
        Icon = 'land',
        SelectionPriority = 3,
        TechLevel = 'RULEUTL_Basic',
        UnitName = '<LOC xra0109_name>Raptor Bio-Weaver',
        UnitWeight = 1,
    },
    Intel = {
        VisionRadius = 18,
    },
    Interface = {
        HelpText = '<LOC xra0109_help>Mobile Bio-Builder. Weaves organic Raptor nests, defense spires, subterranean worms, and super-heavy artillery.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.4,
    LifeBarSize = 0.8,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 3.6,
        MaxBrake = 3.6,
        MaxSpeed = 3.8,
        MaxSpeedReverse = 0,
        MaxSteerForce = 10,
        MeshExtentsX = 1.0,
        MeshExtentsY = 0.9,
        MeshExtentsZ = 1.2,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Land',
        TurnRadius = 0,
        TurnRate = 180,
    },
    SelectionCenterOffsetX = 0,
    SelectionCenterOffsetZ = 0,
    SelectionSizeX = 0.7,
    SelectionSizeZ = 0.8,
    SelectionThickness = 0.65,
    SizeX = 0.8,
    SizeY = 0.9,
    SizeZ = 1.0,
    StrategicIconName = 'icon_land1_engineer',
    StrategicIconSortPriority = 105,
}
"""

with open(os.path.join(dir_xra0109, "XRA0109_unit.bp"), "w") as f:
    f.write(bp_weaver)

script_weaver = """local ConstructionUnit = import('/lua/defaultunits.lua').ConstructionUnit

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

XRA0109 = Class(ConstructionUnit) {
    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.0)
        end
        ConstructionUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        local scale = 1.0 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}

TypeClass = XRA0109
"""

with open(os.path.join(dir_xra0109, "XRA0109_script.lua"), "w") as f:
    f.write(script_weaver)

print("Created XRA0109 Raptor Bio-Weaver.")

# ===========================================================================
# 2. BUILD STRATEGIC BIO-NUKE SILO (XRA0304)
# ===========================================================================
print("\n" + "="*70)
print("BUILDING XRA0304: Strategic Bio-Nuke Silo (Apex Spore ICBM)")
print("="*70)

shutil.copyfile(os.path.join(dir_xra0208, "XRA0208_lod0.scm"), os.path.join(dir_xra0304, "XRA0304_lod0.scm"))
shutil.copyfile(os.path.join(dir_xra0208, "XRA0208_NormalsTS.dds"), os.path.join(dir_xra0304, "XRA0304_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0208, "XRA0208_SpecTeam.dds"), os.path.join(dir_xra0304, "XRA0304_SpecTeam.dds"))
shutil.copyfile(os.path.join(dir_xra0208, "XRA0208_Aidle.sca"), os.path.join(dir_xra0304, "XRA0304_Aidle.sca"))
shutil.copyfile(os.path.join(dir_xra0208, "XRA0208_Adeath01.sca"), os.path.join(dir_xra0304, "XRA0304_Adeath01.sca"))

# Crimson Bio-Nuke Worm Albedo
albedo_nuke = get_bar_file('unittextures/chicken_crimson_l_color.dds')
if not albedo_nuke:
    albedo_nuke = get_bar_file('unittextures/chicken_darkgreen_l_color.dds')
with open(os.path.join(dir_xra0304, "XRA0304_Albedo.dds"), "wb") as f:
    f.write(albedo_nuke)

icon_nuke = get_bar_file('unitpics/raptors/raptor_turrets.dds')
if icon_nuke:
    with open(os.path.join(dir_xra0304, "XRA0304_icon.dds"), "wb") as f:
        f.write(icon_nuke)
    with open(os.path.join(icons_dir, "xra0304_icon.dds"), "wb") as f:
        f.write(icon_nuke)

# Nuke Projectile: XRA_BioNuke01
bp_nukeproj = """ProjectileBlueprint {
    Audio = {
        ExistLoop = Sound {
            Bank = 'UELWeapon',
            Cue = 'UEF_Nuke_Flight',
            LodCutoff = 'DefaultLodCutoff',
        },
        ImpactTerrain = Sound {
            Bank = 'Explosions',
            Cue = 'UEF_Nuke_Impact',
            LodCutoff = 'Weapon_LodCutoff',
        },
        ImpactWater = Sound {
            Bank = 'Explosions',
            Cue = 'UEF_Nuke_Impact',
            LodCutoff = 'Weapon_LodCutoff',
        },
        NukeExplosion = Sound {
            Bank = 'Explosions',
            Cue = 'UEF_Nuke_Impact',
            LodCutoff = 'Weapon_LodCutoff',
        },
    },
    Categories = {
        'RAPTOR',
        'PROJECTILE',
        'STRATEGIC',
        'MISSILE',
        'INDIRECTFIRE',
        'KILLAIRONCOLLISION',
        'NOSPLASHDAMAGE',
    },
    Defense = {
        Health = 25000,
        MaxHealth = 25000,
    },
    DesiredShooterCap = 1,
    Display = {
        CameraFollowTimeout = 5,
        CameraFollowsProjectile = true,
        Mesh = {
            IconFadeInZoom = 200,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0304/XRA0304_Albedo.dds',
                    LODCutoff = 150,
                    MeshName = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_lod0.scm',
                    ShaderName = 'TMeshNoLighting',
                },
            },
        },
        StrategicIconSize = 3,
        UniformScale = 8.0,
    },
    Economy = {
        BuildCostEnergy = 1350000,
        BuildCostMass = 12000,
        BuildTime = 324000,
    },
    General = {
        Category = 'Missile',
        EntityCategory = {
            'RAPTOR',
            'PROJECTILE',
            'STRATEGIC',
            'MISSILE',
        },
        Faction = 'Raptor',
    },
    Physics = {
        Acceleration = 3,
        CollideEntity = false,
        CollideSurface = false,
        DestroyOnWater = false,
        InitialSpeed = 0,
        Lifetime = 600,
        MaxSpeed = 35,
        RotationalVelocity = 0,
        RotationalVelocityRange = 0,
        TrackTarget = true,
        TrackTargetGround = true,
        TurnRate = 0,
        UseGravity = false,
        VelocityAlign = true,
    },
    StrategicIconName = '/textures/ui/common/game/unit-over/icon-nuke_bmp.dds',
}
"""

with open(os.path.join(dir_proj_nuke, "XRA_BioNuke01_proj.bp"), "w") as f:
    f.write(bp_nukeproj)

script_nukeproj = """local NukeProjectile = import('/lua/sim/projectiles/nukeprojectile.lua').NukeProjectile

---@class XRA_BioNuke01 : NukeProjectile
XRA_BioNuke01 = ClassProjectile(NukeProjectile) {
    FxSplashScale = 0.5,
    FxTrails = {},

    InitialEffects = {
        '/effects/emitters/seraphim_inaino_fxtrails_01_emit.bp',
        '/effects/emitters/seraphim_inaino_fxtrails_02_emit.bp',
    },
    ThrustEffects = {
        '/effects/emitters/seraphim_inaino_fxtrails_01_emit.bp',
        '/effects/emitters/seraphim_inaino_fxtrails_02_emit.bp',
    },
    LaunchEffects = {
        '/effects/emitters/seraphim_inaino_fxtrails_01_emit.bp',
        '/effects/emitters/seraphim_inaino_fxtrails_02_emit.bp',
    },

    ---@param self XRA_BioNuke01
    OnCreate = function(self)
        NukeProjectile.OnCreate(self)
        self.effectEntityPath = '/effects/entities/InainoEffectController01/InainoEffectController01_proj.bp'
        self:LauncherCallbacks()
    end,

    DoTakeDamage = function(self, instigator, amount, vector, damageType)
        if damageType == 'AntiNuke' then
            self:Destroy()
        else
            NukeProjectile.DoTakeDamage(self, instigator, amount, vector, damageType)
        end
    end,
}

TypeClass = XRA_BioNuke01
"""

with open(os.path.join(dir_proj_nuke, "XRA_BioNuke01_script.lua"), "w") as f:
    f.write(script_nukeproj)

bp_silo = """UnitBlueprint {
    AI = {
        TargetBones = {
            'head',
            'seg3',
            'aimy',
            'base',
        },
    },
    Audio = {
        NuclearLaunchDetected = Sound {
            Bank = 'XGG',
            Cue = 'Computer_Computer_MissileLaunch_01351',
        },
        Destroyed = Sound {
            Bank = 'Raptor_Roost_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
    },
    BuildIconSortPriority = 80,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'RAPTOR',
        'STRUCTURE',
        'STRATEGIC',
        'SILO',
        'NUKE',
        'TECH3',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'SORTSTRATEGIC',
    },
    CollisionOffsetY = 0.5,
    Defense = {
        ArmorType = 'Structure',
        EconomyThreatLevel = 50,
        Health = 5800,
        MaxHealth = 5800,
        RegenRate = 8,
    },
    Description = '<LOC xra0304_desc>Strategic Bio-Nuke Worm Silo',
    Display = {
        Abilities = {
            '<LOC ability_manuallaunch>Manual Launch',
            '<LOC ability_nuke>Strategic Missile Launcher',
            'Living Bio-Carapace Regen',
        },
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0304/XRA0304_Adeath01.sca',
                Weight = 100,
            },
        },
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0304/XRA0304_Albedo.dds',
                    LODCutoff = 280,
                    MeshName = '/mods/RaptorFaction/units/XRA0304/XRA0304_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0304/XRA0304_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0304/XRA0304_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 1.6,
    },
    Economy = {
        BuildCostEnergy = 210000,
        BuildCostMass = 12000,
        BuildRate = 1080,
        BuildTime = 9000,
    },
    Footprint = {
        SizeX = 4,
        SizeZ = 4,
    },
    General = {
        Category = 'Strategic',
        Classification = 'RULEUC_Weapon',
        CommandCaps = {
            RULEUCC_Nuke = true,
            RULEUCC_Pause = true,
            RULEUCC_Reclaim = false,
            RULEUCC_Repair = false,
            RULEUCC_RetaliateToggle = true,
            RULEUCC_SiloBuildNuke = true,
            RULEUCC_Stop = true,
        },
        FactionName = 'Raptor',
        Icon = 'land',
        SelectionPriority = 5,
        TechLevel = 'RULEUTL_Secret',
        UnitName = '<LOC xra0304_name>Apex Bio-Nuke Worm',
        UnitWeight = 1,
    },
    Intel = {
        VisionRadius = 28,
    },
    LifeBarHeight = 0.08,
    LifeBarOffset = 2.0,
    LifeBarSize = 3.5,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
        },
        DragCoefficient = 0.2,
        FlattenSkirt = true,
        MaxSteerForce = 0,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_None',
        OccupyGround = true,
        SkirtOffsetX = -1.0,
        SkirtOffsetZ = -1.0,
        SkirtSizeX = 6,
        SkirtSizeZ = 6,
        TurnRate = 0,
    },
    SelectionSizeX = 2.6,
    SelectionSizeZ = 2.6,
    SelectionThickness = 0.38,
    SizeX = 3.2,
    SizeY = 4.8,
    SizeZ = 3.2,
    StrategicIconName = 'icon_structure3_missile',
    StrategicIconSortPriority = 175,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Nuke_Launch',
                    Cue = 'Nuke',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            CountedProjectile = true,
            Damage = 25000,
            DamageFriendly = true,
            DamageRadius = 30,
            DamageType = 'Nuke',
            DisplayName = 'Bio-Nuclear Spore ICBM',
            EnergyDrainPerSecond = 0,
            EnergyRequired = 0,
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
            },
            FiringTolerance = 15,
            ForceSingleFire = true,
            InitialProjectileStorage = 0,
            Label = 'NukeMissiles',
            ManualFire = true,
            MaxProjectileStorage = 5,
            MaxRadius = 20000,
            MinRadius = 150,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            MuzzleVelocity = 0,
            NukeInnerRingDamage = 25000,
            NukeInnerRingRadius = 30,
            NukeInnerRingTicks = 24,
            NukeInnerRingTotalTime = 0,
            NukeOuterRingDamage = 500,
            NukeOuterRingRadius = 40,
            NukeOuterRingTicks = 20,
            NukeOuterRingTotalTime = 0,
            NukeWeapon = true,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_BioNuke01/XRA_BioNuke01_proj.bp',
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
            RangeCategory = 'UWRC_IndirectFire',
            RateOfFire = 1,
            TargetCheckInterval = 0.5,
            TargetRestrictDisallow = 'UNTARGETABLE',
            WeaponCategory = 'Missile',
        },
    },
}
"""

with open(os.path.join(dir_xra0304, "XRA0304_unit.bp"), "w") as f:
    f.write(bp_silo)

script_silo = """local CStructureUnit = import('/lua/cybranunits.lua').CStructureUnit
local NukeWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon
local RaptorCreep = import('/mods/RaptorFaction/lua/RaptorCreep.lua')
local Targeting = import('/mods/RaptorFaction/lua/RaptorTargeting.lua')

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

XRA0304 = Class(CStructureUnit) {
    Weapons = {
        NukeMissiles = Class(NukeWeapon) {},
    },

    OnCreate = function(self)
        CStructureUnit.OnCreate(self)
        self.IdleAnim = CreateAnimator(self)
        self.IdleAnim:PlayAnim('/mods/RaptorFaction/units/XRA0304/XRA0304_Aidle.sca', true)
        self.Trash:Add(self.IdleAnim)

        if self:GetFractionComplete() == 1.0 then
            RaptorCreep.StartCreepNode(self, 36, 1.0)
            self:StartNukeThread()
        end
    end,

    OnStopBeingBuilt = function(self, builder, layer)
        CStructureUnit.OnStopBeingBuilt(self, builder, layer)
        if not self.CreepNode then
            RaptorCreep.StartCreepNode(self, 36, 1.0)
        end
        self:StartNukeThread()
    end,

    StartNukeThread = function(self)
        if self.NukeThreadActive then return end
        local brain = self:GetAIBrain()
        if brain and brain.BrainType == 'Human' then return end
        self.NukeThreadActive = true
        self:ForkThread(self.AutoNukeThread)
    end,

    AutoNukeThread = function(self)
        WaitSeconds(90)
        while not self.Dead do
            self:GiveNukeSiloAmmo(1)
            WaitSeconds(10)
            if not self.Dead then
                local army = self:GetArmy()
                local targetPos = Targeting.GetWeightedRandomEnemyTarget(army)
                if targetPos then
                    local ox = (math.random() - 0.5) * 35
                    local oz = (math.random() - 0.5) * 35
                    local tx = targetPos[1] + ox
                    local tz = targetPos[3] + oz
                    local ty = GetSurfaceHeight(tx, tz)
                    IssueNuke({self}, Vector(tx, ty, tz))
                end
            end
            WaitSeconds(180)
        end
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(5.0)
        end
        CStructureUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        local scale = 5.0 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}

TypeClass = XRA0304
"""

with open(os.path.join(dir_xra0304, "XRA0304_script.lua"), "w") as f:
    f.write(script_silo)

print("Created XRA0304 Strategic Bio-Nuke Silo.")

# ===========================================================================
# 3. BUILD CHITINOUS ANTI-NUKE SILO (XRA0305)
# ===========================================================================
print("\n" + "="*70)
print("BUILDING XRA0305: Chitinous Anti-Nuke Silo (Anti-Nuke Interceptor Worm)")
print("="*70)

shutil.copyfile(os.path.join(dir_xra0208, "XRA0208_lod0.scm"), os.path.join(dir_xra0305, "XRA0305_lod0.scm"))
shutil.copyfile(os.path.join(dir_xra0208, "XRA0208_Aidle.sca"), os.path.join(dir_xra0305, "XRA0305_Aidle.sca"))
shutil.copyfile(os.path.join(dir_xra0208, "XRA0208_Adeath01.sca"), os.path.join(dir_xra0305, "XRA0305_Adeath01.sca"))
shutil.copyfile(os.path.join(dir_xra0208, "XRA0208_NormalsTS.dds"), os.path.join(dir_xra0305, "XRA0305_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0208, "XRA0208_SpecTeam.dds"), os.path.join(dir_xra0305, "XRA0305_SpecTeam.dds"))
shutil.copyfile(os.path.join(dir_xra0208, "XRA0208_Albedo.dds"), os.path.join(dir_xra0305, "XRA0305_Albedo.dds"))

icon_anuke = get_bar_file('unitpics/raptors/raptor_turrets.dds')
if icon_anuke:
    with open(os.path.join(dir_xra0305, "XRA0305_icon.dds"), "wb") as f:
        f.write(icon_anuke)
    with open(os.path.join(icons_dir, "xra0305_icon.dds"), "wb") as f:
        f.write(icon_anuke)

# Interceptor Projectile: XRA_AntiNuke01
bp_anukeproj = """ProjectileBlueprint {
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
        'ANTIMISSILE',
    },
    Display = {
        Mesh = {
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0305/XRA0305_Albedo.dds',
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
        Category = 'Defense',
        EntityCategory = {
            'RAPTOR',
            'PROJECTILE',
            'ANTIMISSILE',
        },
        Faction = 'Raptor',
    },
    Physics = {
        Acceleration = 30,
        DestroyOnWater = false,
        HitAssumptionRange = 2,
        InitialSpeed = 40,
        LeadTarget = true,
        Lifetime = 90,
        MaxSpeed = 90,
        TrackTarget = true,
        TurnRate = 240,
        UseGravity = false,
        VelocityAlign = true,
    },
}
"""

with open(os.path.join(dir_proj_antinuke, "XRA_AntiNuke01_proj.bp"), "w") as f:
    f.write(bp_anukeproj)

script_anukeproj = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile

XRA_AntiNuke01 = Class(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/seraphim_autocannon_polytrail_01_emit.bp',
}

TypeClass = XRA_AntiNuke01
"""

with open(os.path.join(dir_proj_antinuke, "XRA_AntiNuke01_script.lua"), "w") as f:
    f.write(script_anukeproj)

bp_anukesilo = """UnitBlueprint {
    AI = {
        TargetBones = {
            'head',
            'seg3',
            'aimy',
            'base',
        },
    },
    Audio = {
        Destroyed = Sound {
            Bank = 'Raptor_Roost_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
    },
    BuildIconSortPriority = 75,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'RAPTOR',
        'STRUCTURE',
        'DEFENSE',
        'ANTIMISSILE',
        'SILO',
        'TECH3',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYDEFENSE',
        'SORTDEFENSE',
    },
    CollisionOffsetY = 0.5,
    Defense = {
        ArmorType = 'Structure',
        EconomyThreatLevel = 30,
        Health = 4800,
        MaxHealth = 4800,
        RegenRate = 6,
    },
    Description = '<LOC xra0305_desc>Strategic Anti-Nuke Worm Silo',
    Display = {
        Abilities = {
            '<LOC ability_stratmissiledefense>Strategic Missile Defense',
            'Living Bio-Carapace Regen',
        },
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0305/XRA0305_Adeath01.sca',
                Weight = 100,
            },
        },
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0305/XRA0305_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0305/XRA0305_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0305/XRA0305_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0305/XRA0305_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 1.3,
    },
    Economy = {
        BuildCostEnergy = 105000,
        BuildCostMass = 7500,
        BuildRate = 1080,
        BuildTime = 5800,
    },
    Footprint = {
        SizeX = 3,
        SizeZ = 3,
    },
    General = {
        Category = 'Defense',
        Classification = 'RULEUC_Countermeasure',
        CommandCaps = {
            RULEUCC_Pause = true,
            RULEUCC_Reclaim = false,
            RULEUCC_Repair = false,
            RULEUCC_RetaliateToggle = true,
            RULEUCC_SiloBuildTactical = true,
            RULEUCC_Stop = true,
        },
        FactionName = 'Raptor',
        Icon = 'land',
        SelectionPriority = 5,
        TechLevel = 'RULEUTL_Secret',
        UnitName = '<LOC xra0305_name>Chitinous Anti-Nuke Worm',
        UnitWeight = 1,
    },
    Intel = {
        VisionRadius = 24,
    },
    LifeBarHeight = 0.08,
    LifeBarOffset = 1.6,
    LifeBarSize = 2.6,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
        },
        DragCoefficient = 0.2,
        FlattenSkirt = true,
        MaxSteerForce = 0,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_None',
        OccupyGround = true,
        SkirtOffsetX = -0.5,
        SkirtOffsetZ = -0.5,
        SkirtSizeX = 4,
        SkirtSizeZ = 4,
        TurnRate = 0,
    },
    SelectionSizeX = 1.8,
    SelectionSizeZ = 1.8,
    SelectionThickness = 0.5,
    SizeX = 2.4,
    SizeY = 3.6,
    SizeZ = 2.4,
    StrategicIconName = 'icon_structure3_antimissile',
    StrategicIconSortPriority = 195,
    Weapon = {
        {
            AlwaysRecheckTarget = false,
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_AntiNuke_Launch',
                    Cue = 'Launch',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            CountedProjectile = true,
            Damage = 30000,
            DamageType = 'AntiNuke',
            DisplayName = 'Chitin Starburst Interceptor',
            EffectiveRadius = 90,
            FireTargetLayerCapsTable = {
                Land = 'Air',
            },
            FiringTolerance = 60,
            ForceSingleFire = true,
            InitialProjectileStorage = 1,
            Label = 'AntiNuke',
            MaxProjectileStorage = 5,
            MaxRadius = 90,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            MuzzleVelocity = 90,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_AntiNuke01/XRA_AntiNuke01_proj.bp',
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
            RackReloadTimeout = 0,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RangeCategory = 'UWRC_Countermeasure',
            RateOfFire = 0.6,
            TargetCheckInterval = 0.1,
            TargetRestrictDisallow = 'UNTARGETABLE',
            TargetRestrictOnlyAllow = 'STRATEGIC MISSILE',
            TargetType = 'RULEWTT_HighArc',
            TrackingRadius = 2.0,
            TurretDualManipulators = false,
            TurretPitch = 0,
            TurretPitchRange = 0,
            TurretPitchSpeed = 0,
            TurretYaw = 0,
            TurretYawRange = 0,
            TurretYawSpeed = 0,
            Turreted = false,
            WeaponCategory = 'Defense',
        },
    },
}
"""

with open(os.path.join(dir_xra0305, "XRA0305_unit.bp"), "w") as f:
    f.write(bp_anukesilo)

script_anukesilo = """local CStructureUnit = import('/lua/cybranunits.lua').CStructureUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon
local RaptorCreep = import('/mods/RaptorFaction/lua/RaptorCreep.lua')

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

XRA0305 = Class(CStructureUnit) {
    Weapons = {
        AntiNuke = Class(DefaultProjectileWeapon) {},
    },

    OnCreate = function(self)
        CStructureUnit.OnCreate(self)
        self.IdleAnim = CreateAnimator(self)
        self.IdleAnim:PlayAnim('/mods/RaptorFaction/units/XRA0305/XRA0305_Aidle.sca', true)
        self.Trash:Add(self.IdleAnim)

        if self:GetFractionComplete() == 1.0 then
            RaptorCreep.StartCreepNode(self, 34, 1.0)
        end
    end,

    OnStopBeingBuilt = function(self, builder, layer)
        CStructureUnit.OnStopBeingBuilt(self, builder, layer)
        if not self.CreepNode then
            RaptorCreep.StartCreepNode(self, 34, 1.0)
        end
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(3.5)
        end
        CStructureUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        local scale = 3.5 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}

TypeClass = XRA0305
"""

with open(os.path.join(dir_xra0305, "XRA0305_script.lua"), "w") as f:
    f.write(script_anukesilo)

print("Created XRA0305 Chitinous Anti-Nuke Silo.")

# ===========================================================================
# 4. BUILD THE 4 SUPER-HEAVY ARTILLERY SPIRES (XRA0306 .. XRA0309)
# ===========================================================================
arty_configs = [
    {
        'id': 'XRA0306',
        'name': 'Brood Gestation Artillery Spire (Unit-Spawning Shells)',
        'unitname': '<LOC xra0306_name>Brood Artillery Spire',
        'desc': '<LOC xra0306_desc>Long-Range Biological Artillery. Launches living egg pods that hatch 2 Swarmers on impact.',
        's3o': 'objects3d/raptors/raptor_turretxl_brood_v2.s3o',
        'dir': dir_xra0306,
        'albedo': 'chicken_purple_l_color.dds',
        'icon': 'unitpics/raptors/raptorbroodarty.dds',
        'range': 600,
        'rof': 0.05,
        'damage': 25,
        'damage_radius': 1.5,
        'proj_id': '/mods/RaptorFaction/projectiles/XRA_BroodShell01/XRA_BroodShell01_proj.bp',
        'sound_bank': 'Raptor_Arty_Launch',
        'sound_cue': 'Attack',
        'salvo_size': 12,
        'salvo_delay': 0.15,
        'randomness': 2.2,
    },
    {
        'id': 'XRA0307',
        'name': 'Bio-EMP Electro Artillery Spire',
        'unitname': '<LOC xra0307_name>Bio-EMP Artillery Spire',
        'desc': '<LOC xra0307_desc>Long-Range EMP Artillery. Fires high-voltage bio-plasma globes that paralyze units and collapse shields.',
        's3o': 'objects3d/raptors/raptor_turretxl_electric_v2.s3o',
        'dir': dir_xra0307,
        'albedo': 'chicken_electric_l_color.dds',
        'icon': 'unitpics/raptors/raptor_turrets_electric.dds',
        'range': 650,
        'rof': 0.05,
        'damage': 350,
        'damage_radius': 6.0,
        'proj_id': '/mods/RaptorFaction/projectiles/XRA_ElectroShell01/XRA_ElectroShell01_proj.bp',
        'sound_bank': 'Raptor_Arty_Launch',
        'sound_cue': 'Attack',
        'salvo_size': 16,
        'salvo_delay': 0.12,
        'randomness': 2.4,
    },
    {
        'id': 'XRA0308',
        'name': 'Corrosive Acid Artillery Spire',
        'unitname': '<LOC xra0308_name>Corrosive Acid Artillery Spire',
        'desc': '<LOC xra0308_desc>Long-Range Acid Artillery. Bombards enemy bases with dense corrosive bile that dissolves hulls and defenses.',
        's3o': 'objects3d/raptors/raptor_turretxl_acid_v2.s3o',
        'dir': dir_xra0308,
        'albedo': 'chicken_acidgreen_l_color.dds',
        'icon': 'unitpics/raptors/raptoracidartyxl.dds',
        'range': 700,
        'rof': 0.05,
        'damage': 350,
        'damage_radius': 6.0,
        'proj_id': '/mods/RaptorFaction/projectiles/XRA_AcidShell01/XRA_AcidShell01_proj.bp',
        'sound_bank': 'Raptor_Arty_Launch',
        'sound_cue': 'Attack',
        'salvo_size': 16,
        'salvo_delay': 0.12,
        'randomness': 2.4,
    },
    {
        'id': 'XRA0309',
        'name': 'Meteor Cataclysm Artillery Spire',
        'unitname': '<LOC xra0309_name>Meteor Cataclysm Spire',
        'desc': '<LOC xra0309_desc>Extreme-Range Planetary Artillery. Launches apocalyptic volcanic chitin meteors that pulverize fortifications.',
        's3o': 'objects3d/raptors/raptor_turretxl_meteor_v2.s3o',
        'dir': dir_xra0309,
        'albedo': 'chicken_apex_l_color.dds',
        'icon': 'unitpics/raptors/raptor_turretxl_meteor.dds',
        'range': 750,
        'rof': 0.04,
        'damage': 3500,
        'damage_radius': 9.0,
        'proj_id': '/mods/RaptorFaction/projectiles/XRA_MeteorShell01/XRA_MeteorShell01_proj.bp',
        'sound_bank': 'Raptor_Arty_Launch',
        'sound_cue': 'Attack',
        'salvo_size': 3,
        'salvo_delay': 0.5,
        'randomness': 1.4,
    },
]

# Write Projectile for Brood Artillery: XRA_BroodShell01
bp_broodproj = """ProjectileBlueprint {
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
        Mesh = {
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0306/XRA0306_Albedo.dds',
                    LODCutoff = 150,
                    MeshName = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_lod0.scm',
                    ShaderName = 'TMeshNoLighting',
                },
            },
        },
        StrategicIconSize = 2,
        UniformScale = 6.0,
    },
    General = {
        Category = 'Artillery',
        EntityCategory = {
            'RAPTOR',
            'PROJECTILE',
            'INDIRECTFIRE',
        },
        Faction = 'Raptor',
    },
    Physics = {
        Acceleration = 0,
        DestroyOnWater = false,
        InitialSpeed = 40,
        LeadTarget = true,
        Lifetime = 25,
        MaxSpeed = 70,
        RotationalVelocity = 100,
        UseGravity = true,
        VelocityAlign = true,
    },
}
"""
with open(os.path.join(dir_proj_brood, "XRA_BroodShell01_proj.bp"), "w") as f:
    f.write(bp_broodproj)

script_broodproj = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile

XRA_BroodShell01 = Class(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/seraphim_aireau_autocannon_polytrail_01_emit.bp',

    OnImpact = function(self, targetType, targetEntity)
        local army = self:GetArmy()
        local pos = self:GetPosition()
        SinglePolyTrailProjectile.OnImpact(self, targetType, targetEntity)
        
        -- Spawn 2 living Raptor Swarmers directly from the brood egg shell!
        for i = 1, 2 do
            local angle = math.random() * 2 * math.pi
            local dist = 1.0 + math.random() * 2.0
            local x = pos[1] + math.cos(angle) * dist
            local z = pos[3] + math.sin(angle) * dist
            local y = GetSurfaceHeight(x, z)
            CreateUnitHPR('XRA0101', army, x, y, z, 0, math.random(0, 360), 0)
        end
    end,
}

TypeClass = XRA_BroodShell01
"""
with open(os.path.join(dir_proj_brood, "XRA_BroodShell01_script.lua"), "w") as f:
    f.write(script_broodproj)

# Helper for other 3 artillery projectiles
def make_arty_proj(p_dir, p_id, mesh_unit, poly, impact_bank='Impacts', impact_cue='X_Impact_Land_Gen_Seraphim', custom_script=None):
    bp_text = f"""ProjectileBlueprint {{
    Audio = {{
        Impact = Sound {{
            Bank = '{impact_bank}',
            Cue = '{impact_cue}',
            LodCutoff = 'Weapon_LodCutoff',
        }},
        ImpactTerrain = Sound {{
            Bank = '{impact_bank}',
            Cue = '{impact_cue}',
            LodCutoff = 'Weapon_LodCutoff',
        }},
        ImpactWater = Sound {{
            Bank = '{impact_bank}',
            Cue = '{impact_cue}',
            LodCutoff = 'Weapon_LodCutoff',
        }},
    }},
    Categories = {{
        'RAPTOR',
        'PROJECTILE',
        'INDIRECTFIRE',
    }},
    Display = {{
        Mesh = {{
            LODs = {{
                {{
                    AlbedoName = '/mods/RaptorFaction/units/{mesh_unit}/{mesh_unit}_Albedo.dds',
                    LODCutoff = 150,
                    MeshName = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_lod0.scm',
                    ShaderName = 'TMeshNoLighting',
                }},
            }},
        }},
        StrategicIconSize = 2,
        UniformScale = 7.0,
    }},
    General = {{
        Category = 'Artillery',
        EntityCategory = {{
            'RAPTOR',
            'PROJECTILE',
            'INDIRECTFIRE',
        }},
        Faction = 'Raptor',
    }},
    Physics = {{
        Acceleration = 0,
        DestroyOnWater = false,
        InitialSpeed = 45,
        LeadTarget = true,
        Lifetime = 25,
        MaxSpeed = 80,
        RotationalVelocity = 120,
        UseGravity = true,
        VelocityAlign = true,
    }},
}}
"""
    with open(os.path.join(p_dir, f"{p_id}_proj.bp"), "w") as f:
        f.write(bp_text)

    if custom_script:
        lua_text = custom_script
    else:
        lua_text = f"""local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile

{p_id} = Class(SinglePolyTrailProjectile) {{
    PolyTrail = '{poly}',
}}

TypeClass = {p_id}
"""
    with open(os.path.join(p_dir, f"{p_id}_script.lua"), "w") as f:
        f.write(lua_text)

script_emp_proj = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile
local CreateEmitterAtEntity = CreateEmitterAtEntity

local EMPHitEffects = {
    '/effects/emitters/cybran_empgrenade_hit_01_emit.bp',
    '/effects/emitters/cybran_empgrenade_hit_02_emit.bp',
    '/effects/emitters/build_sparks_blue_02_emit.bp',
}

XRA_ElectroShell01 = Class(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/seraphim_aireau_autocannon_polytrail_01_emit.bp',

    OnImpact = function(self, targetType, targetEntity)
        local army = self:GetArmy()
        local pos = self:GetPosition()

        for _, emit in EMPHitEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.0)
        end

        local brain = self:GetAIBrain()
        if brain then
            local targets = brain:GetUnitsAroundPoint(categories.MOBILE + categories.STRUCTURE, pos, 8.0, 'Enemy')
            for _, t in targets do
                if not t.Dead then
                    t:SetStunned(12.0)
                    if t.MyShield and t.MyShield:IsOn() then
                        t.MyShield:ApplyDamage(1500)
                    end
                end
            end
        end

        SinglePolyTrailProjectile.OnImpact(self, targetType, targetEntity)
    end,
}

TypeClass = XRA_ElectroShell01
"""

make_arty_proj(dir_proj_emp, "XRA_ElectroShell01", "XRA0307", "/effects/emitters/seraphim_aireau_autocannon_polytrail_01_emit.bp", impact_bank='Raptor_EMP_Launch', impact_cue='Attack', custom_script=script_emp_proj)
make_arty_proj(dir_proj_acid, "XRA_AcidShell01", "XRA0308", "/effects/emitters/default_polytrail_07_emit.bp")

script_meteor_proj = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile

---@class XRA_MeteorShell01 : SinglePolyTrailProjectile
XRA_MeteorShell01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/plasma_cannon_polytrail_04_emit.bp',
    PolyTrailOffset = 0,
    FxTrails = {
        '/effects/emitters/flamethrower_02_emit.bp',
    },
    FxTrailScale = 1.5,
    FxTrailOffset = 0,

    FxImpactTrajectoryAligned = false,

    FxImpactUnit = {
        '/effects/emitters/flash_01_emit.bp',
        '/effects/emitters/Small_test_fire.bp',
        '/effects/emitters/plasma_cannon_hit_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
        '/effects/emitters/destruction_land_hit_puff_05_emit.bp',
        '/effects/emitters/proton_bomb_hit_02_emit.bp',
    },
    FxImpactProp = {
        '/effects/emitters/flash_01_emit.bp',
        '/effects/emitters/Small_test_fire.bp',
        '/effects/emitters/plasma_cannon_hit_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
        '/effects/emitters/destruction_land_hit_puff_05_emit.bp',
        '/effects/emitters/proton_bomb_hit_02_emit.bp',
    },
    FxImpactLand = {
        '/effects/emitters/flash_01_emit.bp',
        '/effects/emitters/Small_test_fire.bp',
        '/effects/emitters/plasma_cannon_hit_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
        '/effects/emitters/destruction_land_hit_puff_05_emit.bp',
        '/effects/emitters/proton_bomb_hit_02_emit.bp',
    },
    FxImpactWater = {
        '/effects/emitters/napalm_hvy_waterflash_emit.bp',
        '/effects/emitters/napalm_hvy_water_smoke_emit.bp',
    },
    FxImpactUnderWater = {
        '/effects/emitters/napalm_hvy_waterflash_emit.bp',
    },

    FxLandHitScale = 2.2,
    FxUnitHitScale = 2.2,
    FxPropHitScale = 2.2,
    FxWaterHitScale = 2.2,
}

TypeClass = XRA_MeteorShell01
"""


make_arty_proj(dir_proj_meteor, "XRA_MeteorShell01", "XRA0309", "/effects/emitters/plasma_cannon_polytrail_04_emit.bp", impact_bank='Raptor_Nuke_Explosion', impact_cue='Explosion', custom_script=script_meteor_proj)

# Build each of the 4 Artillery Spire units
for cfg in arty_configs:
    u_id = cfg['id']
    u_dir = cfg['dir']
    print(f"\nBuilding {u_id}: {cfg['name']}...")

    s3o_data = get_bar_file(cfg['s3o'])
    assert s3o_data, f"Could not find {cfg['s3o']}!"
    scm_path = os.path.join(u_dir, f"{u_id}_lod0.scm")
    pcs = convert_s3o_to_scm(s3o_data, scm_path)

    p_names = [p.name for p in pcs]
    p_links = [p.parent_idx for p in pcs]
    rest_p = {p.name: p.local_pos for p in pcs}

    # Textures
    albedo_raw = get_bar_file('unittextures/' + cfg['albedo'])
    if not albedo_raw:
        albedo_raw = get_bar_file('unittextures/chicken_darkgreen_l_color.dds')
    with open(os.path.join(u_dir, f"{u_id}_Albedo.dds"), "wb") as f:
        f.write(albedo_raw)
    shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(u_dir, f"{u_id}_NormalsTS.dds"))
    shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(u_dir, f"{u_id}_SpecTeam.dds"))

    # Icon
    icon_raw = get_bar_file(cfg['icon'])
    if icon_raw:
        with open(os.path.join(u_dir, f"{u_id}_icon.dds"), "wb") as f:
            f.write(icon_raw)
        with open(os.path.join(icons_dir, f"{u_id.lower()}_icon.dds"), "wb") as f:
            f.write(icon_raw)

    # Animations
    num_idle = 24
    idle_dur = 3.0
    idle_f = []
    for f_idx in range(num_idle):
        t_ratio = f_idx / num_idle
        phase = 2.0 * math.pi * t_ratio
        idle_f.extend([t_ratio * idle_dur, 0])
        rot_d = {name: (0.0, 0.0, 0.0) for name in p_names}
        pos_d = {name: rest_p[name] for name in p_names}
        for i in range(1, 6):
            sn = f"seg{i}"
            if sn in p_names:
                rot_d[sn] = (math.sin(phase - i*0.4) * math.radians(2.5), 0.0, math.cos(phase - i*0.4) * math.radians(2.0))
        for b in p_names:
            rx, ry, rz = rot_d[b]
            px, py, pz = pos_d[b]
            qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
            idle_f.extend([px, py, pz, qw, qx, qy, qz])

    save_sca_file(os.path.join(u_dir, f"{u_id}_Aidle.sca"), num_idle, idle_dur, p_names, p_links, idle_f)

    num_death = 24
    death_dur = 1.3
    death_f = []
    for f_idx in range(num_death):
        t_ratio = f_idx / (num_death - 1)
        prog = 1.0 - math.cos(t_ratio * math.pi * 0.5)
        death_f.extend([t_ratio * death_dur, 0])
        rot_d = {name: (0.0, 0.0, 0.0) for name in p_names}
        pos_d = {name: rest_p[name] for name in p_names}
        for i in range(1, 6):
            sn = f"seg{i}"
            if sn in p_names:
                rot_d[sn] = (prog * math.radians(18.0), 0.0, prog * math.radians(8.0))
        for b in p_names:
            rx, ry, rz = rot_d[b]
            px, py, pz = pos_d[b]
            qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
            death_f.extend([px, py, pz, qw, qx, qy, qz])

    save_sca_file(os.path.join(u_dir, f"{u_id}_Adeath01.sca"), num_death, death_dur, p_names, p_links, death_f)

    # Blueprint
    bp_arty_text = f"""UnitBlueprint {{
    AI = {{
        TargetBones = {{
            'aimy',
            'head',
            'flare',
        }},
    }},
    Audio = {{
        Destroyed = Sound {{
            Bank = 'Raptor_Roost_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        }},
    }},
    Buffs = {{
        Regen = {{
            Level1 = 6,
            Level2 = 12,
            Level3 = 18,
            Level4 = 24,
            Level5 = 30,
        }},
    }},
    BuildIconSortPriority = 70,
    Categories = {{
        'PRODUCTSC1',
        'SELECTABLE',
        'RAPTOR',
        'STRUCTURE',
        'STRATEGIC',
        'INDIRECTFIRE',
        'ARTILLERY',
        'TECH3',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYINDIRECTFIRE',
        'SORTSTRATEGIC',
    }},
    CollisionOffsetY = 0.5,
    Defense = {{
        ArmorType = 'Structure',
        EconomyThreatLevel = 40,
        Health = 8500,
        MaxHealth = 8500,
        RegenRate = 10,
    }},
    Description = '{cfg['desc']}',
    Display = {{
        Abilities = {{
            '<LOC ability_artillery>Artillery',
            'Strategic Long-Range Bombardment',
            'Living Bio-Carapace Regen',
        }},
        AnimationDeath = {{
            {{
                Animation = '/mods/RaptorFaction/units/{u_id}/{u_id}_Adeath01.sca',
                Weight = 100,
            }},
        }},
        Mesh = {{
            IconFadeInZoom = 130,
            LODs = {{
                {{
                    AlbedoName = '/mods/RaptorFaction/units/{u_id}/{u_id}_Albedo.dds',
                    LODCutoff = 300,
                    MeshName = '/mods/RaptorFaction/units/{u_id}/{u_id}_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/{u_id}/{u_id}_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/{u_id}/{u_id}_SpecTeam.dds',
                    ShaderName = 'Insect',
                }},
            }},
        }},
        UniformScale = 1.6,
    }},
    Economy = {{
        BuildCostEnergy = 160000,
        BuildCostMass = 11000,
        BuildTime = 9500,
    }},
    Footprint = {{
        SizeX = 4,
        SizeZ = 4,
    }},
    General = {{
        Category = 'Strategic',
        Classification = 'RULEUC_Weapon',
        CommandCaps = {{
            RULEUCC_Attack = true,
            RULEUCC_Guard = false,
            RULEUCC_Move = false,
            RULEUCC_Patrol = false,
            RULEUCC_RetaliateToggle = true,
            RULEUCC_Stop = true,
        }},
        FactionName = 'Raptor',
        Icon = 'land',
        SelectionPriority = 5,
        TechLevel = 'RULEUTL_Secret',
        UnitName = '{cfg['unitname']}',
        UnitWeight = 1,
    }},
    Intel = {{
        VisionRadius = 28,
    }},
    LifeBarHeight = 0.08,
    LifeBarOffset = 1.6,
    LifeBarSize = 2.8,
    Physics = {{
        BankingSlope = 0,
        BuildOnLayerCaps = {{
            LAYER_Land = true,
            LAYER_Water = true,
        }},
        DragCoefficient = 0.2,
        FlattenSkirt = true,
        MaxSteerForce = 0,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_None',
        OccupyGround = true,
        SkirtOffsetX = -0.5,
        SkirtOffsetZ = -0.5,
        SkirtSizeX = 5,
        SkirtSizeZ = 5,
        TurnRate = 0,
    }},
    SelectionSizeX = 2.4,
    SelectionSizeZ = 2.4,
    SelectionThickness = 0.45,
    SizeX = 2.8,
    SizeY = 5.2,
    SizeZ = 2.8,
    StrategicIconName = 'icon_structure3_artillery',
    StrategicIconSortPriority = 180,
    Weapon = {{
        {{
            AboveWaterTargetsOnly = true,
            Audio = {{
                Fire = Sound {{
                    Bank = '{cfg['sound_bank']}',
                    Cue = '{cfg['sound_cue']}',
                    LodCutoff = 'Weapon_LodCutoff',
                }},
            }},
            BallisticArc = 'RULEUBA_HighArc',
            CollideFriendly = false,
            Damage = {cfg['damage']},
            DamageFriendly = false,
            DamageRadius = {cfg['damage_radius']},
            DamageType = 'Normal',
            DisplayName = '{cfg['name']}',
            FireTargetLayerCapsTable = {{
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            }},
            FiringRandomness = {cfg.get('randomness', 0.4)},
            FiringTolerance = 15,
            Label = 'MainGun',
            MaxRadius = {cfg['range']},
            MinRadius = 25,
            MuzzleSalvoDelay = {cfg.get('salvo_delay', 0)},
            MuzzleSalvoSize = {cfg.get('salvo_size', 1)},
            MuzzleVelocity = 75,
            MuzzleVelocityReduceDistance = 600,
            ProjectileId = '{cfg['proj_id']}',
            RackBones = {{
                {{
                    MuzzleBones = {{
                        'flare',
                    }},
                    RackBone = 'flare',
                }},
            }},
            RackFireTogether = false,
            RackRecoilDistance = 0,
            RackReloadTimeout = 0,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RackSlavedToTurret = false,
            RangeCategory = 'UWRC_IndirectFire',
            RateOfFire = {cfg['rof']},
            RenderFireClock = true,
            TargetCheckInterval = 1.0,
            TargetPriorities = {{
                'STRUCTURE STRATEGIC',
                'STRUCTURE EXPERIMENTAL',
                'TECH3 MOBILE',
                'ALLUNITS',
            }},
            TargetRestrictDisallow = 'UNTARGETABLE',
            TurretBoneMuzzle = 'flare',
            TurretBonePitch = 'head',
            TurretBoneYaw = 'aimy',
            TurretDualManipulators = false,
            TurretPitch = 40,
            TurretPitchRange = 80,
            TurretPitchSpeed = 45,
            TurretYaw = 0,
            TurretYawRange = 180,
            TurretYawSpeed = 45,
            Turreted = true,
            WeaponCategory = 'Artillery',
        }},
    }},
}}
"""
    with open(os.path.join(u_dir, f"{u_id}_unit.bp"), "w") as f:
        f.write(bp_arty_text)

    lua_arty_text = f"""local CStructureUnit = import('/lua/cybranunits.lua').CStructureUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {{
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}}

local ArtyWeapon = Class(DefaultProjectileWeapon) {{}}

{u_id} = Class(CStructureUnit) {{
    Weapons = {{
        MainGun = Class(ArtyWeapon) {{}},
    }},

    OnCreate = function(self)
        CStructureUnit.OnCreate(self)
        self.IdleAnim = CreateAnimator(self)
        self.IdleAnim:PlayAnim('/mods/RaptorFaction/units/{u_id}/{u_id}_Aidle.sca', true)
        self.Trash:Add(self.IdleAnim)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(4.0)
        end
        CStructureUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}}

TypeClass = {u_id}
"""
    with open(os.path.join(u_dir, f"{u_id}_script.lua"), "w") as f:
        f.write(lua_arty_text)

print("Created all 4 Super-Heavy Artillery Spires.")

# ===========================================================================
# 5. FACTION ISOLATION: REMOVE CYBRAN FROM ALL RAPTOR BLUEPRINTS
# ===========================================================================
print("\n" + "="*70)
print("ISOLATING RAPTOR FACTION: Removing Cybran / Seraphim categories...")
print("="*70)

def clean_blueprint_faction(bp_path, is_mobile=False, is_factory=False):
    if not os.path.exists(bp_path):
        return
    with open(bp_path, 'r') as f:
        content = f.read()

    # Remove Cybran and Seraphim categories
    content = content.replace("'CYBRAN',", "")
    content = content.replace("'SERAPHIM',", "")
    content = content.replace("FactionName = 'Cybran'", "FactionName = 'Raptor'")

    # If mobile unit, make it built by Raptor Hive
    if is_mobile:
        content = content.replace("'BUILTBYTIER1FACTORY',", "'BUILTBYRAPTORHIVE',")
        content = content.replace("'BUILTBYTIER2FACTORY',", "'BUILTBYRAPTORHIVE',")
        content = content.replace("'BUILTBYTIER3FACTORY',", "'BUILTBYRAPTORHIVE',")

    # If structure, remove Cybran engineers/commander build flags
    if not is_mobile:
        content = content.replace("'BUILTBYTIER1ENGINEER',", "")
        content = content.replace("'BUILTBYTIER2ENGINEER',", "")
        content = content.replace("'BUILTBYTIER3ENGINEER',", "")
        content = content.replace("'BUILTBYCOMMANDER',", "")

    # For factory hive, update buildable category to RAPTOR MOBILE
    if is_factory:
        content = content.replace(
            "BuildableCategory = {\n            'BUILTBYTIER1FACTORY RAPTOR MOBILE',\n            'BUILTBYTIER2FACTORY RAPTOR MOBILE',\n            'BUILTBYTIER3FACTORY RAPTOR MOBILE',\n            'RAPTOR MOBILE',\n        },",
            "BuildableCategory = {\n            'BUILTBYRAPTORHIVE RAPTOR MOBILE',\n            'RAPTOR MOBILE',\n        },"
        )

    with open(bp_path, 'w') as f:
        f.write(content)
    print(f"Cleaned blueprint for Faction isolation: {os.path.basename(bp_path)}")

# Apply isolation across all existing units
clean_blueprint_faction(os.path.join(dir_xra0101, "XRA0101_unit.bp"), is_mobile=True)
clean_blueprint_faction(os.path.join(dir_xra0105, "XRA0105_unit.bp"), is_mobile=True)
clean_blueprint_faction(os.path.join(dir_xra0201, "XRA0201_unit.bp"), is_mobile=True)
clean_blueprint_faction(os.path.join(dir_xra0107, "XRA0107_unit.bp"), is_mobile=False, is_factory=True)
clean_blueprint_faction(os.path.join(dir_xra0108, "XRA0108_unit.bp"), is_mobile=False)
clean_blueprint_faction(os.path.join(dir_xra0106, "XRA0106_unit.bp"), is_mobile=False)
clean_blueprint_faction(os.path.join(dir_xra0208, "XRA0208_unit.bp"), is_mobile=False)

# ===========================================================================
# 6. UPDATE MOD INFO & EXPORT ARCHIVE
# ===========================================================================
mod_info_path = os.path.join(mod_dir, "mod_info.lua")
mod_info_content = """name = "Raptor Swarm Faction"
version = 4
copyright = "Beyond All Reason & FAF Communities"
description = "Standalone biological Raptor Swarm race. Includes mobile swarmers, fliers, heavy crawlers, the Bio-Weaver builder, Gestation Hive, Point Defense Spire, AA Spire, Burrowing Worm, Strategic Bio-Nuke Silo, Anti-Nuke Silo, and 4 super-heavy artillery spires (Brood Unit-Spawner, Bio-EMP, Acid, Meteor)."
author = "BAR & FAF"
uid = "raptor-swarm-faction-faf-0004"
selectable = true
enabled = true
exclusive = false
ui_only = false
requires = {}
"""

with open(mod_info_path, "w") as f:
    f.write(mod_info_content)

export_zip = os.path.join(os.path.dirname(__file__), "exports", "RaptorFaction.zip")
print(f"\nPackaging full standalone mod to {export_zip}...")
with zipfile.ZipFile(export_zip, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(mod_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(mod_dir))
            z.write(full_path, rel_path)

print("\nALL EXPANSION TASKS COMPLETED SUCCESSFULLY!")
