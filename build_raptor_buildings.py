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

dir_xra0101 = os.path.join(units_root, "XRA0101")
dir_xra0107 = os.path.join(units_root, "XRA0107") # Hive
dir_xra0108 = os.path.join(units_root, "XRA0108") # Acid Spire
dir_xra0106 = os.path.join(units_root, "XRA0106") # Spore AA Spire
dir_xra0208 = os.path.join(units_root, "XRA0208") # Burrowing Worm

dir_proj_spore = os.path.join(proj_root, "XRA_Spore01")
dir_proj_mortar = os.path.join(proj_root, "XRA_BioMortar01")

for d in [icons_dir, dir_xra0107, dir_xra0108, dir_xra0106, dir_xra0208, dir_proj_spore, dir_proj_mortar, raptor_sounds_dir]:
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
# S3O -> SCM Conversion Function
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

    parse_piece(52)

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
        # Mandatory 28-byte dummy root pose required by Supreme Commander / FAF CAnimData loader
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

# Generate Audio Banks for Structures
struct_audio = [
    ('Raptor_Roost_Death', 'Raptor_Roost_Death', 'Death', 'sounds/raptors/roostdie.wav', 'roostdie.wav'),
    ('Raptor_Turret_Attack', 'Raptor_Turret_Attack', 'Attack', 'sounds/raptors/bugattack.wav', 'bugattack.wav'),
    ('Raptor_Worm_Roar', 'Raptor_Worm_Roar', 'Attack', 'sounds/raptors/bigraptorbreath.wav', 'bigraptorbreath.wav'),
]

for sb_name, wb_name, cue, bar_path, fname in struct_audio:
    wdata = get_bar_file(bar_path)
    if wdata:
        xwb, xsb = build_xact_bank(sb_name, wb_name, cue, wdata)
        with open(os.path.join(sounds_dir, f'{sb_name}.xwb'), 'wb') as f:
            f.write(xwb)
        with open(os.path.join(sounds_dir, f'{sb_name}.xsb'), 'wb') as f:
            f.write(xsb)
        with open(os.path.join(raptor_sounds_dir, fname), 'wb') as f:
            f.write(wdata)
        print(f"Generated Structure Audio Bank: {sb_name}")

# ===========================================================================
# 1. BUILD XRA0107: RAPTOR HIVE / GESTATION NEST (FACTORY & BIOMASS NEXUS)
# ===========================================================================
print("\n" + "="*70)
print("BUILDING XRA0107: Raptor Gestation Hive (Organic Factory)")
print("="*70)

s3o_hive = get_bar_file('objects3d/raptors/raptor_hive.s3o')
assert s3o_hive, "raptor_hive.s3o not found!"
scm_hive_path = os.path.join(dir_xra0107, "XRA0107_lod0.scm")
pieces_hive = convert_s3o_to_scm(s3o_hive, scm_hive_path)

piece_names_hive = [p.name for p in pieces_hive]
parent_indices_hive = [p.parent_idx for p in pieces_hive]
rest_pos_hive = {p.name: p.local_pos for p in pieces_hive}

# Textures
albedo_hive = get_bar_file('unittextures/chicken_darkgreen_l_color.dds')
with open(os.path.join(dir_xra0107, "XRA0107_Albedo.dds"), "wb") as f:
    f.write(albedo_hive)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0107, "XRA0107_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0107, "XRA0107_SpecTeam.dds"))

# Icon
icon_hive = get_bar_file('unitpics/raptors/raptor_hive.dds')
if icon_hive:
    with open(os.path.join(dir_xra0107, "XRA0107_icon.dds"), "wb") as f:
        f.write(icon_hive)
    with open(os.path.join(icons_dir, "xra0107_icon.dds"), "wb") as f:
        f.write(icon_hive)

# Hive Animations:
# Radial angles for petal arms 1..5:
# arm1: -36 deg, arm2: +37 deg, arm3: +109 deg, arm4: +179 deg, arm5: -109 deg
arm_angles = {
    'arm1': math.radians(-36.0),
    'arm2': math.radians(37.0),
    'arm3': math.radians(109.0),
    'arm4': math.radians(179.0),
    'arm5': math.radians(-109.0),
}

# A. Idle Animation (Gentle Biological Breathing)
num_idle_frames = 30
idle_dur = 3.0
idle_frames_hive = []

for f_idx in range(num_idle_frames):
    t_ratio = f_idx / num_idle_frames
    time_sec = t_ratio * idle_dur
    phase = 2.0 * math.pi * t_ratio

    idle_frames_hive.append(time_sec)
    idle_frames_hive.append(0)

    rot_dict = {name: (0.0, 0.0, 0.0) for name in piece_names_hive}
    pos_dict = {name: rest_pos_hive[name] for name in piece_names_hive}

    # armbase subtle pulse
    armbase_bob = math.sin(phase) * 0.06
    lx, ly, lz = rest_pos_hive['armbase']
    pos_dict['armbase'] = (lx, ly + armbase_bob, lz)

    # Petal arms breathe slightly outward and back
    petal_spread = math.sin(phase) * math.radians(7.0)
    for arm_name, theta in arm_angles.items():
        pitch = math.cos(theta) * petal_spread
        roll = math.sin(theta) * petal_spread
        rot_dict[arm_name] = (pitch, 0.0, roll)

    for b_name in piece_names_hive:
        rx, ry, rz = rot_dict[b_name]
        px, py, pz = pos_dict[b_name]
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        idle_frames_hive.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(
    os.path.join(dir_xra0107, "XRA0107_Aidle.sca"),
    num_idle_frames, idle_dur,
    piece_names_hive, parent_indices_hive,
    idle_frames_hive
)

# B. Active Gestation Animation (Open Petals & Rhythmic Deep Hatching Pulse)
num_act_frames = 24
act_dur = 1.2
act_frames_hive = []

for f_idx in range(num_act_frames):
    t_ratio = f_idx / num_act_frames
    time_sec = t_ratio * act_dur
    phase = 2.0 * math.pi * t_ratio

    act_frames_hive.append(time_sec)
    act_frames_hive.append(0)

    rot_dict = {name: (0.0, 0.0, 0.0) for name in piece_names_hive}
    pos_dict = {name: rest_pos_hive[name] for name in piece_names_hive}

    armbase_pulse = math.sin(phase) * 0.14
    lx, ly, lz = rest_pos_hive['armbase']
    pos_dict['armbase'] = (lx, ly + armbase_pulse, lz)

    # Petals open wide and pulse rhythmically
    petal_spread = math.radians(24.0) + math.sin(phase) * math.radians(12.0)
    for arm_name, theta in arm_angles.items():
        pitch = math.cos(theta) * petal_spread
        roll = math.sin(theta) * petal_spread
        rot_dict[arm_name] = (pitch, 0.0, roll)

    for b_name in piece_names_hive:
        rx, ry, rz = rot_dict[b_name]
        px, py, pz = pos_dict[b_name]
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        act_frames_hive.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(
    os.path.join(dir_xra0107, "XRA0107_Aactive.sca"),
    num_act_frames, act_dur,
    piece_names_hive, parent_indices_hive,
    act_frames_hive
)

# C. Death Animation (Spasm, outward recoil then collapse inward)
num_death_frames = 24
death_dur = 1.3
death_frames_hive = []

for f_idx in range(num_death_frames):
    t_ratio = f_idx / (num_death_frames - 1)
    time_sec = t_ratio * death_dur

    death_frames_hive.append(time_sec)
    death_frames_hive.append(0)

    rot_dict = {name: (0.0, 0.0, 0.0) for name in piece_names_hive}
    pos_dict = {name: rest_pos_hive[name] for name in piece_names_hive}

    if t_ratio < 0.35:
        # Violent spasm recoil
        sub = t_ratio / 0.35
        petal_spread = sub * math.radians(45.0)
        lx, ly, lz = rest_pos_hive['armbase']
        pos_dict['armbase'] = (lx, ly + sub * 0.25, lz)
    else:
        # Collapse inward onto rupture
        sub = (t_ratio - 0.35) / 0.65
        petal_spread = (1.0 - sub) * math.radians(45.0) - sub * math.radians(35.0)
        lx, ly, lz = rest_pos_hive['armbase']
        pos_dict['armbase'] = (lx, ly - sub * 0.45, lz)

    for arm_name, theta in arm_angles.items():
        pitch = math.cos(theta) * petal_spread
        roll = math.sin(theta) * petal_spread
        rot_dict[arm_name] = (pitch, 0.0, roll)

    for b_name in piece_names_hive:
        rx, ry, rz = rot_dict[b_name]
        px, py, pz = pos_dict[b_name]
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        death_frames_hive.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(
    os.path.join(dir_xra0107, "XRA0107_Adeath01.sca"),
    num_death_frames, death_dur,
    piece_names_hive, parent_indices_hive,
    death_frames_hive
)

# Blueprint: XRA0107_unit.bp
bp_hive_content = """UnitBlueprint {
    AI = {
        TargetBones = {
            'base',
            'topflare',
            'armbase',
        },
    },
    Audio = {
        Construct = Sound {
            Bank = 'Raptor_Attack',
            Cue = 'Attack',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Destroyed = Sound {
            Bank = 'Raptor_Roost_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Killed = Sound {
            Bank = 'Raptor_Roost_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
    },
    Buffs = {
        Regen = {
            Level1 = 4,
            Level2 = 8,
            Level3 = 12,
            Level4 = 16,
            Level5 = 20,
        },
    },
    BuildIconSortPriority = 50,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYTIER1ENGINEER',
        'BUILTBYTIER2ENGINEER',
        'BUILTBYTIER3ENGINEER',
        'BUILTBYCOMMANDER',
        'CYBRAN',
        'RAPTOR',
        'STRUCTURE',
        'FACTORY',
        'LAND',
        'TECH1',
        'CONSTRUCTION',
        'RALLYPOINT',
        'SHOWQUEUE',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'SORTCONSTRUCTION',
    },
    CollisionOffsetY = 0.5,
    Defense = {
        AirThreatLevel = 0,
        ArmorType = 'Structure',
        EconomyThreatLevel = 3,
        Health = 3800,
        MaxHealth = 3800,
        RegenRate = 5,
        SubThreatLevel = 0,
        SurfaceThreatLevel = 0,
    },
    Description = '<LOC xra0107_desc>Biological Gestation Hive & Biomass Nexus',
    Display = {
        Abilities = {
            '<LOC ability_factory>Factory',
            'Biomass Generation (+20E, +1.5M)',
            'Living Bio-Carapace Regen',
        },
        AnimationBuild = '/mods/RaptorFaction/units/XRA0107/XRA0107_Aactive.sca',
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0107/XRA0107_Adeath01.sca',
                AnimationRateMax = 1.0,
                AnimationRateMin = 1.0,
                Weight = 100,
            },
        },
        BuildAttachBone = 'topflare',
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0107/XRA0107_Albedo.dds',
                    LODCutoff = 280,
                    MeshName = '/mods/RaptorFaction/units/XRA0107/XRA0107_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0107/XRA0107_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0107/XRA0107_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 1.0,
    },
    Economy = {
        BuildCostEnergy = 2200,
        BuildCostMass = 240,
        BuildRate = 20,
        BuildTime = 350,
        BuildableCategory = {
            'BUILTBYTIER1FACTORY RAPTOR MOBILE',
            'BUILTBYTIER2FACTORY RAPTOR MOBILE',
            'BUILTBYTIER3FACTORY RAPTOR MOBILE',
            'RAPTOR MOBILE',
        },
        ProductionPerSecondEnergy = 20,
        ProductionPerSecondMass = 1.5,
        StorageEnergy = 500,
        StorageMass = 100,
    },
    Footprint = {
        SizeX = 5,
        SizeZ = 5,
    },
    General = {
        BuildBones = {
            BuildEffectBones = {
                'topflare',
                'arm1',
                'arm2',
                'arm3',
                'arm4',
                'arm5',
            },
        },
        Category = 'Factory',
        Classification = 'RULEUC_Factory',
        CommandCaps = {
            RULEUCC_Attack = false,
            RULEUCC_CallCycle = false,
            RULEUCC_Capture = false,
            RULEUCC_Guard = true,
            RULEUCC_Move = true,
            RULEUCC_Nuke = false,
            RULEUCC_Patrol = true,
            RULEUCC_Pause = true,
            RULEUCC_Reclaim = false,
            RULEUCC_Repair = false,
            RULEUCC_RetaliateToggle = true,
            RULEUCC_Stop = true,
            RULEUCC_Tactical = false,
            RULEUCC_Transport = false,
        },
        ConstructionBar = true,
        FactionName = 'Cybran',
        Icon = 'land',
        SelectionPriority = 5,
        TechLevel = 'RULEUTL_Basic',
        UnitName = '<LOC xra0107_name>Raptor Gestation Roost',
        UnitWeight = 1,
    },
    Intel = {
        VisionRadius = 24,
    },
    Interface = {
        HelpText = '<LOC xra0107_help>Biological Factory Nest. Gestates and spawns Raptor swarmers, heavy crawlers, and aerial hunters.',
    },
    LifeBarHeight = 0.08,
    LifeBarOffset = 2.4,
    LifeBarSize = 4.0,
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
        RaisedPlatforms = {},
        RollOffPoints = {
            { UnitSpin = 0,   X = 0,   Y = 0, Z = 6.5 },
            { UnitSpin = 72,  X = 6.2, Y = 0, Z = 2.0 },
            { UnitSpin = 144, X = 3.8, Y = 0, Z = -5.3 },
            { UnitSpin = 216, X = -3.8,Y = 0, Z = -5.3 },
            { UnitSpin = 288, X = -6.2,Y = 0, Z = 2.0 },
        },
        SkirtOffsetX = -1.5,
        SkirtOffsetZ = -1.5,
        SkirtSizeX = 8,
        SkirtSizeZ = 8,
        TurnRate = 0,
    },
    SelectionSizeX = 3.6,
    SelectionSizeZ = 3.6,
    SelectionThickness = 0.38,
    SizeX = 4.8,
    SizeY = 3.2,
    SizeZ = 4.8,
    StrategicIconName = 'icon_factory1_land',
    StrategicIconSortPriority = 215,
}
"""

with open(os.path.join(dir_xra0107, "XRA0107_unit.bp"), "w") as f:
    f.write(bp_hive_content)

# Script: XRA0107_script.lua
script_hive_content = """local FactoryUnit = import('/lua/defaultunits.lua').FactoryUnit

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

XRA0107 = Class(FactoryUnit) {
    OnCreate = function(self)
        FactoryUnit.OnCreate(self)
        self.IdleAnim = CreateAnimator(self)
        self.IdleAnim:PlayAnim('/mods/RaptorFaction/units/XRA0107/XRA0107_Aidle.sca', true)
        self.Trash:Add(self.IdleAnim)
    end,

    OnStartBuild = function(self, unitBeingBuilt, order)
        FactoryUnit.OnStartBuild(self, unitBeingBuilt, order)
        if not self.BuildAnim then
            self.BuildAnim = CreateAnimator(self)
            self.Trash:Add(self.BuildAnim)
        end
        self.BuildAnim:PlayAnim('/mods/RaptorFaction/units/XRA0107/XRA0107_Aactive.sca', true)
    end,

    OnStopBuild = function(self, unitBeingBuilt)
        FactoryUnit.OnStopBuild(self, unitBeingBuilt)
        if self.BuildAnim then
            self.BuildAnim:SetRate(0)
        end
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtBone(self, 'topflare', army, emit):ScaleEmitter(1.2)
        end
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(4.0)
        end
        FactoryUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        local scale = 4.0 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}

TypeClass = XRA0107
"""

with open(os.path.join(dir_xra0107, "XRA0107_script.lua"), "w") as f:
    f.write(script_hive_content)

print("Created XRA0107 Raptor Gestation Hive.")

# ===========================================================================
# 2. HELPER FOR SERPENTINE TURRET ANIMATIONS (XRA0108, XRA0106, XRA0208)
# ===========================================================================
def generate_turret_animations(target_dir, unit_id, piece_names, parent_indices, rest_positions, idle_scale=1.0, death_scale=1.0):
    # A. Idle Serpentine Scanning Animation
    num_idle = 24
    idle_dur = 2.4
    idle_frames = []

    for f_idx in range(num_idle):
        t_ratio = f_idx / num_idle
        time_sec = t_ratio * idle_dur
        phase = 2.0 * math.pi * t_ratio

        idle_frames.append(time_sec)
        idle_frames.append(0)

        rot_dict = {name: (0.0, 0.0, 0.0) for name in piece_names}
        pos_dict = {name: rest_positions[name] for name in piece_names}

        # Wave through seg1..seg5
        for i in range(1, 6):
            s_name = f"seg{i}"
            if s_name in piece_names:
                p_seg = phase - i * 0.5
                wave_x = math.sin(p_seg) * math.radians(3.5 * idle_scale)
                wave_z = math.cos(p_seg) * math.radians(3.0 * idle_scale)
                rot_dict[s_name] = (wave_x, 0.0, wave_z)

        # Head counters slightly to keep forward gaze
        if 'head' in piece_names:
            rot_dict['head'] = (-math.sin(phase - 2.5) * math.radians(2.5 * idle_scale), 0.0, 0.0)

        for b_name in piece_names:
            rx, ry, rz = rot_dict[b_name]
            px, py, pz = pos_dict[b_name]
            qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
            idle_frames.extend([px, py, pz, qw, qx, qy, qz])

    save_sca_file(
        os.path.join(target_dir, f"{unit_id}_Aidle.sca"),
        num_idle, idle_dur,
        piece_names, parent_indices,
        idle_frames
    )

    # B. Death Collapse Animation
    num_death = 24
    death_dur = 1.2
    death_frames = []

    for f_idx in range(num_death):
        t_ratio = f_idx / (num_death - 1)
        time_sec = t_ratio * death_dur
        progress = 1.0 - math.cos(t_ratio * math.pi * 0.5)

        death_frames.append(time_sec)
        death_frames.append(0)

        rot_dict = {name: (0.0, 0.0, 0.0) for name in piece_names}
        pos_dict = {name: rest_positions[name] for name in piece_names}

        # Stalk topples forward and sideways
        for i in range(1, 6):
            s_name = f"seg{i}"
            if s_name in piece_names:
                bend_x = progress * math.radians(16.0 * death_scale)
                bend_z = progress * math.radians(6.0 * death_scale)
                rot_dict[s_name] = (bend_x, 0.0, bend_z)

        if 'head' in piece_names:
            rot_dict['head'] = (progress * math.radians(25.0 * death_scale), 0.0, 0.0)

        for b_name in piece_names:
            rx, ry, rz = rot_dict[b_name]
            px, py, pz = pos_dict[b_name]
            qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
            death_frames.extend([px, py, pz, qw, qx, qy, qz])

    save_sca_file(
        os.path.join(target_dir, f"{unit_id}_Adeath01.sca"),
        num_death, death_dur,
        piece_names, parent_indices,
        death_frames
    )

# ===========================================================================
# 3. BUILD XRA0108: BIO-ACID DEFENSE SPIRE (T1 POINT DEFENSE)
# ===========================================================================
print("\n" + "="*70)
print("BUILDING XRA0108: Bio-Acid Defense Spire (Point Defense)")
print("="*70)

s3o_spire = get_bar_file('objects3d/raptors/raptor_turrets_acid_v2.s3o')
assert s3o_spire, "raptor_turrets_acid_v2.s3o not found!"
scm_spire_path = os.path.join(dir_xra0108, "XRA0108_lod0.scm")
pieces_spire = convert_s3o_to_scm(s3o_spire, scm_spire_path)

piece_names_spire = [p.name for p in pieces_spire]
parent_indices_spire = [p.parent_idx for p in pieces_spire]
rest_pos_spire = {p.name: p.local_pos for p in pieces_spire}

# Textures
albedo_spire = get_bar_file('unittextures/chicken_acidgreen_l_color.dds')
with open(os.path.join(dir_xra0108, "XRA0108_Albedo.dds"), "wb") as f:
    f.write(albedo_spire)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0108, "XRA0108_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0108, "XRA0108_SpecTeam.dds"))

# Icon
icon_spire = get_bar_file('unitpics/raptors/raptor_turrets_acid.dds')
if icon_spire:
    with open(os.path.join(dir_xra0108, "XRA0108_icon.dds"), "wb") as f:
        f.write(icon_spire)
    with open(os.path.join(icons_dir, "xra0108_icon.dds"), "wb") as f:
        f.write(icon_spire)

generate_turret_animations(dir_xra0108, "XRA0108", piece_names_spire, parent_indices_spire, rest_pos_spire, idle_scale=1.0, death_scale=1.0)

# Blueprint: XRA0108_unit.bp
bp_spire_content = """UnitBlueprint {
    AI = {
        TargetBones = {
            'aimy',
            'head',
            'flare',
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
            Level1 = 3,
            Level2 = 6,
            Level3 = 9,
            Level4 = 12,
            Level5 = 15,
        },
    },
    BuildIconSortPriority = 60,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYTIER1ENGINEER',
        'BUILTBYTIER2ENGINEER',
        'BUILTBYTIER3ENGINEER',
        'BUILTBYCOMMANDER',
        'CYBRAN',
        'RAPTOR',
        'STRUCTURE',
        'DEFENSE',
        'DIRECTFIRE',
        'TECH1',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYDIRECTFIRE',
        'SORTDEFENSE',
    },
    CollisionOffsetY = 0.4,
    Defense = {
        AirThreatLevel = 0,
        ArmorType = 'Structure',
        EconomyThreatLevel = 1,
        Health = 1350,
        MaxHealth = 1350,
        RegenRate = 3,
        SubThreatLevel = 0,
        SurfaceThreatLevel = 6,
    },
    Description = '<LOC xra0108_desc>Biological Acid Point Defense Spire',
    Display = {
        Abilities = {
            '<LOC ability_pointdefense>Point Defense',
            'Rapid Acid Spine Spitter',
            'Living Bio-Carapace Regen',
        },
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0108/XRA0108_Adeath01.sca',
                AnimationRateMax = 1.1,
                AnimationRateMin = 0.9,
                Weight = 100,
            },
        },
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0108/XRA0108_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0108/XRA0108_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0108/XRA0108_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0108/XRA0108_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 1.0,
    },
    Economy = {
        BuildCostEnergy = 1900,
        BuildCostMass = 220,
        BuildTime = 250,
    },
    Footprint = {
        SizeX = 2,
        SizeZ = 2,
    },
    General = {
        Category = 'Defense',
        Classification = 'RULEUC_Weapon',
        CommandCaps = {
            RULEUCC_Attack = true,
            RULEUCC_CallCycle = false,
            RULEUCC_Capture = false,
            RULEUCC_Guard = false,
            RULEUCC_Move = false,
            RULEUCC_Nuke = false,
            RULEUCC_Patrol = false,
            RULEUCC_Reclaim = false,
            RULEUCC_Repair = false,
            RULEUCC_RetaliateToggle = true,
            RULEUCC_Stop = true,
            RULEUCC_Tactical = false,
            RULEUCC_Transport = false,
        },
        FactionName = 'Cybran',
        Icon = 'land',
        SelectionPriority = 5,
        TechLevel = 'RULEUTL_Basic',
        UnitName = '<LOC xra0108_name>Bio-Acid Spire',
        UnitWeight = 1,
    },
    Intel = {
        VisionRadius = 28,
    },
    Interface = {
        HelpText = '<LOC xra0108_help>Organic Point Defense Spire. Spews rapid-fire acidic spines at approaching enemy ground targets.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.45,
    LifeBarSize = 1.1,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        FlattenSkirt = true,
        MaxSteerForce = 0,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_None',
        OccupyGround = true,
        SkirtOffsetX = 0,
        SkirtOffsetZ = 0,
        SkirtSizeX = 2,
        SkirtSizeZ = 2,
        TurnRate = 0,
    },
    SelectionSizeX = 1.1,
    SelectionSizeZ = 1.1,
    SelectionThickness = 0.6,
    SizeX = 1.2,
    SizeY = 2.4,
    SizeZ = 1.2,
    StrategicIconName = 'icon_structure1_directfire',
    StrategicIconSortPriority = 205,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Turret_Attack',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            BallisticArc = 'RULEUBA_LowArc',
            CollideFriendly = false,
            Damage = 50,
            DamageType = 'Normal',
            DisplayName = 'Acid Spire Spine Spitter',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 2,
            Label = 'MainGun',
            MaxRadius = 26,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            MuzzleVelocity = 35,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp',
            ProjectileLifetimeUsesMultiplier = 1.15,
            ProjectilesPerOnFire = 1,
            RackBones = {
                {
                    MuzzleBones = {
                        'flare',
                    },
                    RackBone = 'flare',
                },
            },
            RackFireTogether = false,
            RackRecoilDistance = 0,
            RackReloadTimeout = 0,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RackSlavedToTurret = false,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 2.0,
            TargetCheckInterval = 0.3,
            TargetPriorities = {
                'MOBILE TECH1',
                'MOBILE TECH2',
                'MOBILE TECH3',
                'COMMAND',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            TrackingRadius = 1.15,
            TurretBoneMuzzle = 'flare',
            TurretBonePitch = 'head',
            TurretBoneYaw = 'aimy',
            TurretDualManipulators = false,
            TurretPitch = 0,
            TurretPitchRange = 60,
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

with open(os.path.join(dir_xra0108, "XRA0108_unit.bp"), "w") as f:
    f.write(bp_spire_content)

# Script: XRA0108_script.lua
script_spire_content = """local CStructureUnit = import('/lua/cybranunits.lua').CStructureUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

local AcidTurretWeapon = Class(DefaultProjectileWeapon) {
    FxMuzzleFlash = {
        '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    },
}

XRA0108 = Class(CStructureUnit) {
    Weapons = {
        MainGun = Class(AcidTurretWeapon) {},
    },

    OnCreate = function(self)
        CStructureUnit.OnCreate(self)
        self.IdleAnim = CreateAnimator(self)
        self.IdleAnim:PlayAnim('/mods/RaptorFaction/units/XRA0108/XRA0108_Aidle.sca', true)
        self.Trash:Add(self.IdleAnim)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.0)
        end
        CStructureUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        local scale = 2.0 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}

TypeClass = XRA0108
"""

with open(os.path.join(dir_xra0108, "XRA0108_script.lua"), "w") as f:
    f.write(script_spire_content)

print("Created XRA0108 Bio-Acid Spire.")

# ===========================================================================
# 4. BUILD XRA0106: SPORE ANTI-AIR SPIRE (T1/T2 ANTI-AIR DEFENSE)
# ===========================================================================
print("\n" + "="*70)
print("BUILDING XRA0106: Spore Anti-Air Spire (Biological AA)")
print("="*70)

s3o_aa = get_bar_file('objects3d/raptors/raptor_turrets_v2.s3o')
assert s3o_aa, "raptor_turrets_v2.s3o not found!"
scm_aa_path = os.path.join(dir_xra0106, "XRA0106_lod0.scm")
pieces_aa = convert_s3o_to_scm(s3o_aa, scm_aa_path)

piece_names_aa = [p.name for p in pieces_aa]
parent_indices_aa = [p.parent_idx for p in pieces_aa]
rest_pos_aa = {p.name: p.local_pos for p in pieces_aa}

# Textures (Electric blue chitin for AA Spore theme)
albedo_aa = get_bar_file('unittextures/chicken_blue_l_color.dds')
with open(os.path.join(dir_xra0106, "XRA0106_Albedo.dds"), "wb") as f:
    f.write(albedo_aa)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0106, "XRA0106_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0106, "XRA0106_SpecTeam.dds"))

# Icon
icon_aa = get_bar_file('unitpics/raptors/raptor_turrets_antiair.dds')
if icon_aa:
    with open(os.path.join(dir_xra0106, "XRA0106_icon.dds"), "wb") as f:
        f.write(icon_aa)
    with open(os.path.join(icons_dir, "xra0106_icon.dds"), "wb") as f:
        f.write(icon_aa)

generate_turret_animations(dir_xra0106, "XRA0106", piece_names_aa, parent_indices_aa, rest_pos_aa, idle_scale=1.1, death_scale=1.0)

# Projectile: XRA_Spore01
proj_spore_bp = """ProjectileBlueprint {
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
        'ANTIAIR',
    },
    Display = {
        ImpactEffects = {
            Type = 'Small01',
        },
        Mesh = {
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0106/XRA0106_Albedo.dds',
                    LODCutoff = 150,
                    MeshName = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_lod0.scm',
                    ShaderName = 'TMeshNoLighting',
                },
            },
        },
        StrategicIconSize = 1,
        UniformScale = 3.0,
    },
    General = {
        Category = 'Anti Air',
        EntityCategory = {
            'RAPTOR',
            'PROJECTILE',
            'ANTIAIR',
        },
        Faction = 'Cybran',
        Weapon = 'Bio Spore Flak',
    },
    Interface = {
        HelpText = 0,
    },
    Physics = {
        Acceleration = 8,
        DestroyOnWater = true,
        InitialSpeed = 25,
        Lifetime = 3.5,
        MaxSpeed = 45,
        RotationalVelocity = 400,
        RotationalVelocityRange = 200,
        TrackTarget = true,
        TrackingRadius = 1.4,
        TurnRate = 360,
        UseGravity = false,
        VelocityAlign = true,
    },
}
"""

with open(os.path.join(dir_proj_spore, "XRA_Spore01_proj.bp"), "w") as f:
    f.write(proj_spore_bp)

proj_spore_script = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile

XRA_Spore01 = Class(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/seraphim_aireau_autocannon_polytrail_01_emit.bp',
    PolyTrailOffset = 0,
}

TypeClass = XRA_Spore01
"""

with open(os.path.join(dir_proj_spore, "XRA_Spore01_script.lua"), "w") as f:
    f.write(proj_spore_script)

# Blueprint: XRA0106_unit.bp
bp_aa_content = """UnitBlueprint {
    AI = {
        TargetBones = {
            'aimy',
            'head',
            'flare',
        },
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
            Level1 = 3,
            Level2 = 6,
            Level3 = 9,
            Level4 = 12,
            Level5 = 15,
        },
    },
    BuildIconSortPriority = 65,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYTIER1ENGINEER',
        'BUILTBYTIER2ENGINEER',
        'BUILTBYTIER3ENGINEER',
        'BUILTBYCOMMANDER',
        'CYBRAN',
        'RAPTOR',
        'STRUCTURE',
        'DEFENSE',
        'ANTIAIR',
        'TECH1',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYANTIAIR',
        'SORTDEFENSE',
    },
    CollisionOffsetY = 0.4,
    Defense = {
        AirThreatLevel = 5,
        ArmorType = 'Structure',
        EconomyThreatLevel = 1,
        Health = 1200,
        MaxHealth = 1200,
        RegenRate = 3,
        SubThreatLevel = 0,
        SurfaceThreatLevel = 0,
    },
    Description = '<LOC xra0106_desc>Biological Spore Anti-Air Defense Spire',
    Display = {
        Abilities = {
            '<LOC ability_aa>Anti-Air',
            'Tracking Bio-Spore Swarm',
            'Living Bio-Carapace Regen',
        },
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0106/XRA0106_Adeath01.sca',
                AnimationRateMax = 1.1,
                AnimationRateMin = 0.9,
                Weight = 100,
            },
        },
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0106/XRA0106_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0106/XRA0106_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0106/XRA0106_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0106/XRA0106_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 1.0,
    },
    Economy = {
        BuildCostEnergy = 1800,
        BuildCostMass = 200,
        BuildTime = 220,
    },
    Footprint = {
        SizeX = 2,
        SizeZ = 2,
    },
    General = {
        Category = 'Defense',
        Classification = 'RULEUC_Weapon',
        CommandCaps = {
            RULEUCC_Attack = true,
            RULEUCC_CallCycle = false,
            RULEUCC_Capture = false,
            RULEUCC_Guard = false,
            RULEUCC_Move = false,
            RULEUCC_Nuke = false,
            RULEUCC_Patrol = false,
            RULEUCC_Reclaim = false,
            RULEUCC_Repair = false,
            RULEUCC_RetaliateToggle = true,
            RULEUCC_Stop = true,
            RULEUCC_Tactical = false,
            RULEUCC_Transport = false,
        },
        FactionName = 'Cybran',
        Icon = 'land',
        SelectionPriority = 5,
        TechLevel = 'RULEUTL_Basic',
        UnitName = '<LOC xra0106_name>Bio-Spore AA Spire',
        UnitWeight = 1,
    },
    Intel = {
        VisionRadius = 26,
    },
    Interface = {
        HelpText = '<LOC xra0106_help>Anti-Air Bio Spire. Launches high-velocity heat-seeking organic spores that seek and tear apart enemy aircraft.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.45,
    LifeBarSize = 1.1,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        FlattenSkirt = true,
        MaxSteerForce = 0,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_None',
        OccupyGround = true,
        SkirtOffsetX = 0,
        SkirtOffsetZ = 0,
        SkirtSizeX = 2,
        SkirtSizeZ = 2,
        TurnRate = 0,
    },
    SelectionSizeX = 1.1,
    SelectionSizeZ = 1.1,
    SelectionThickness = 0.6,
    SizeX = 1.2,
    SizeY = 2.4,
    SizeZ = 1.2,
    StrategicIconName = 'icon_structure1_antiair',
    StrategicIconSortPriority = 205,
    Weapon = {
        {
            AboveWaterTargetsOnly = false,
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Flyer_Attack',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            Damage = 60,
            DamageType = 'Normal',
            DisplayName = 'Bio-Spore Anti-Air Flak',
            FireTargetLayerCapsTable = {
                Land = 'Air',
                Water = 'Air',
            },
            FiringTolerance = 2,
            Label = 'AAGun',
            MaxRadius = 38,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            MuzzleVelocity = 40,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_Spore01/XRA_Spore01_proj.bp',
            ProjectileLifetimeUsesMultiplier = 1.25,
            ProjectilesPerOnFire = 1,
            RackBones = {
                {
                    MuzzleBones = {
                        'flare',
                    },
                    RackBone = 'flare',
                },
            },
            RackFireTogether = false,
            RackRecoilDistance = 0,
            RackReloadTimeout = 0,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RackSlavedToTurret = false,
            RangeCategory = 'UWRC_AntiAir',
            RateOfFire = 2.0,
            TargetCheckInterval = 0.25,
            TargetPriorities = {
                'HIGHPRIAIR',
                'BOMBER',
                'GROUNDATTACK',
                'AIR MOBILE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE, LAND, STRUCTURE, NAVAL',
            TrackingRadius = 1.4,
            TurretBoneMuzzle = 'flare',
            TurretBonePitch = 'head',
            TurretBoneYaw = 'aimy',
            TurretDualManipulators = false,
            TurretPitch = 45,
            TurretPitchRange = 90,
            TurretPitchSpeed = 120,
            TurretYaw = 0,
            TurretYawRange = 180,
            TurretYawSpeed = 120,
            Turreted = true,
            WeaponCategory = 'Anti Air',
        },
    },
}
"""

with open(os.path.join(dir_xra0106, "XRA0106_unit.bp"), "w") as f:
    f.write(bp_aa_content)

# Script: XRA0106_script.lua
script_aa_content = """local CStructureUnit = import('/lua/cybranunits.lua').CStructureUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

local BioSporeWeapon = Class(DefaultProjectileWeapon) {
    FxMuzzleFlash = {
        '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
    },
}

XRA0106 = Class(CStructureUnit) {
    Weapons = {
        AAGun = Class(BioSporeWeapon) {},
    },

    OnCreate = function(self)
        CStructureUnit.OnCreate(self)
        self.IdleAnim = CreateAnimator(self)
        self.IdleAnim:PlayAnim('/mods/RaptorFaction/units/XRA0106/XRA0106_Aidle.sca', true)
        self.Trash:Add(self.IdleAnim)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.0)
        end
        CStructureUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        local scale = 2.0 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}

TypeClass = XRA0106
"""

with open(os.path.join(dir_xra0106, "XRA0106_script.lua"), "w") as f:
    f.write(script_aa_content)

print("Created XRA0106 Spore Anti-Air Spire.")

# ===========================================================================
# 5. BUILD XRA0208: BURROWING BIO-WORM (T2 HEAVY SUBTERRANEAN DEFENSE)
# ===========================================================================
print("\n" + "="*70)
print("BUILDING XRA0208: Burrowing Bio-Worm (Heavy Defense & Corrosive Mortar)")
print("="*70)

s3o_worm = get_bar_file('objects3d/raptors/raptor_worm_green.s3o')
assert s3o_worm, "raptor_worm_green.s3o not found!"
scm_worm_path = os.path.join(dir_xra0208, "XRA0208_lod0.scm")
pieces_worm = convert_s3o_to_scm(s3o_worm, scm_worm_path)

piece_names_worm = [p.name for p in pieces_worm]
parent_indices_worm = [p.parent_idx for p in pieces_worm]
rest_pos_worm = {p.name: p.local_pos for p in pieces_worm}

# Textures
albedo_worm = get_bar_file('unittextures/chicken_darkgreen_l_color.dds')
with open(os.path.join(dir_xra0208, "XRA0208_Albedo.dds"), "wb") as f:
    f.write(albedo_worm)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0208, "XRA0208_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0208, "XRA0208_SpecTeam.dds"))

# Icon
icon_worm = get_bar_file('unitpics/raptors/raptor_turrets.dds')
if icon_worm:
    with open(os.path.join(dir_xra0208, "XRA0208_icon.dds"), "wb") as f:
        f.write(icon_worm)
    with open(os.path.join(icons_dir, "xra0208_icon.dds"), "wb") as f:
        f.write(icon_worm)

generate_turret_animations(dir_xra0208, "XRA0208", piece_names_worm, parent_indices_worm, rest_pos_worm, idle_scale=1.4, death_scale=1.3)

# Projectile: XRA_BioMortar01
proj_mortar_bp = """ProjectileBlueprint {
    Audio = {
        Impact = Sound {
            Bank = 'Raptor_Bio_Bomb',
            Cue = 'Attack',
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
                    AlbedoName = '/mods/RaptorFaction/units/XRA0208/XRA0208_Albedo.dds',
                    LODCutoff = 150,
                    MeshName = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_lod0.scm',
                    ShaderName = 'TMeshNoLighting',
                },
            },
        },
        StrategicIconSize = 1,
        UniformScale = 1.8,
    },
    General = {
        Category = 'Artillery',
        EntityCategory = {
            'RAPTOR',
            'PROJECTILE',
            'INDIRECTFIRE',
        },
        Faction = 'Cybran',
        Weapon = 'Bio Mortar',
    },
    Interface = {
        HelpText = 0,
    },
    Physics = {
        Acceleration = 0,
        DestroyOnWater = true,
        InitialSpeed = 22,
        Lifetime = 6,
        MaxSpeed = 26,
        RotationalVelocity = 150,
        UseGravity = true,
        VelocityAlign = true,
    },
}
"""

with open(os.path.join(dir_proj_mortar, "XRA_BioMortar01_proj.bp"), "w") as f:
    f.write(proj_mortar_bp)

proj_mortar_script = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile

XRA_BioMortar01 = Class(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/default_polytrail_07_emit.bp',
    PolyTrailOffset = 0,
}

TypeClass = XRA_BioMortar01
"""

with open(os.path.join(dir_proj_mortar, "XRA_BioMortar01_script.lua"), "w") as f:
    f.write(proj_mortar_script)

# Blueprint: XRA0208_unit.bp
bp_worm_content = """UnitBlueprint {
    AI = {
        TargetBones = {
            'aimy',
            'head',
            'flare',
        },
    },
    Audio = {
        Destroyed = Sound {
            Bank = 'Raptor_Roost_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Killed = Sound {
            Bank = 'Raptor_Roost_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        },
    },
    Buffs = {
        Regen = {
            Level1 = 5,
            Level2 = 10,
            Level3 = 15,
            Level4 = 20,
            Level5 = 25,
        },
    },
    BuildIconSortPriority = 62,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYTIER2ENGINEER',
        'BUILTBYTIER3ENGINEER',
        'BUILTBYCOMMANDER',
        'CYBRAN',
        'RAPTOR',
        'STRUCTURE',
        'DEFENSE',
        'DIRECTFIRE',
        'TECH2',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYDIRECTFIRE',
        'SORTDEFENSE',
    },
    CollisionOffsetY = 0.5,
    Defense = {
        AirThreatLevel = 0,
        ArmorType = 'Structure',
        EconomyThreatLevel = 2,
        Health = 5400,
        MaxHealth = 5400,
        RegenRate = 8,
        SubThreatLevel = 0,
        SurfaceThreatLevel = 15,
    },
    Description = '<LOC xra0208_desc>Heavy Subterranean Bio-Worm Defense',
    Display = {
        Abilities = {
            '<LOC ability_pointdefense>Heavy Point Defense',
            'High-Damage Corrosive Bile Mortar (Splash AOE)',
            'Living Bio-Carapace Regen',
        },
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0208/XRA0208_Adeath01.sca',
                AnimationRateMax = 1.0,
                AnimationRateMin = 1.0,
                Weight = 100,
            },
        },
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0208/XRA0208_Albedo.dds',
                    LODCutoff = 280,
                    MeshName = '/mods/RaptorFaction/units/XRA0208/XRA0208_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0208/XRA0208_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0208/XRA0208_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 1.0,
    },
    Economy = {
        BuildCostEnergy = 6800,
        BuildCostMass = 750,
        BuildTime = 800,
    },
    Footprint = {
        SizeX = 3,
        SizeZ = 3,
    },
    General = {
        Category = 'Defense',
        Classification = 'RULEUC_Weapon',
        CommandCaps = {
            RULEUCC_Attack = true,
            RULEUCC_CallCycle = false,
            RULEUCC_Capture = false,
            RULEUCC_Guard = false,
            RULEUCC_Move = false,
            RULEUCC_Nuke = false,
            RULEUCC_Patrol = false,
            RULEUCC_Reclaim = false,
            RULEUCC_Repair = false,
            RULEUCC_RetaliateToggle = true,
            RULEUCC_Stop = true,
            RULEUCC_Tactical = false,
            RULEUCC_Transport = false,
        },
        FactionName = 'Cybran',
        Icon = 'land',
        SelectionPriority = 5,
        TechLevel = 'RULEUTL_Advanced',
        UnitName = '<LOC xra0208_name>Burrowing Bio-Worm',
        UnitWeight = 1,
    },
    Intel = {
        VisionRadius = 36,
    },
    Interface = {
        HelpText = '<LOC xra0208_help>Heavy Subterranean Defense. Massive segmented bio-worm that withstands heavy assault and spits destructive corrosive bile with splash damage.',
    },
    LifeBarHeight = 0.08,
    LifeBarOffset = 0.8,
    LifeBarSize = 1.8,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
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
    SizeX = 2.0,
    SizeY = 4.2,
    SizeZ = 2.0,
    StrategicIconName = 'icon_structure2_directfire',
    StrategicIconSortPriority = 200,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Worm_Roar',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            BallisticArc = 'RULEUBA_LowArc',
            CollideFriendly = false,
            Damage = 250,
            DamageRadius = 2.5,
            DamageType = 'Normal',
            DisplayName = 'Heavy Bio-Acid Mortar',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 2,
            Label = 'MainGun',
            MaxRadius = 45,
            MinRadius = 5,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            MuzzleVelocity = 30,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_BioMortar01/XRA_BioMortar01_proj.bp',
            ProjectileLifetimeUsesMultiplier = 1.3,
            ProjectilesPerOnFire = 1,
            RackBones = {
                {
                    MuzzleBones = {
                        'flare',
                    },
                    RackBone = 'flare',
                },
            },
            RackFireTogether = false,
            RackRecoilDistance = 0,
            RackReloadTimeout = 0,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RackSlavedToTurret = false,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1.0,
            TargetCheckInterval = 0.5,
            TargetPriorities = {
                'TECH3 MOBILE',
                'TECH2 MOBILE',
                'TECH1 MOBILE',
                'COMMAND',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            TrackingRadius = 1.15,
            TurretBoneMuzzle = 'flare',
            TurretBonePitch = 'head',
            TurretBoneYaw = 'aimy',
            TurretDualManipulators = false,
            TurretPitch = 15,
            TurretPitchRange = 65,
            TurretPitchSpeed = 60,
            TurretYaw = 0,
            TurretYawRange = 180,
            TurretYawSpeed = 60,
            Turreted = true,
            WeaponCategory = 'Direct Fire',
        },
    },
}
"""

with open(os.path.join(dir_xra0208, "XRA0208_unit.bp"), "w") as f:
    f.write(bp_worm_content)

# Script: XRA0208_script.lua
script_worm_content = """local CStructureUnit = import('/lua/cybranunits.lua').CStructureUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

local WormBileWeapon = Class(DefaultProjectileWeapon) {
    FxMuzzleFlash = {
        '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
    },
}

XRA0208 = Class(CStructureUnit) {
    Weapons = {
        MainGun = Class(WormBileWeapon) {},
    },

    OnCreate = function(self)
        CStructureUnit.OnCreate(self)
        self.IdleAnim = CreateAnimator(self)
        self.IdleAnim:PlayAnim('/mods/RaptorFaction/units/XRA0208/XRA0208_Aidle.sca', true)
        self.Trash:Add(self.IdleAnim)
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

TypeClass = XRA0208
"""

with open(os.path.join(dir_xra0208, "XRA0208_script.lua"), "w") as f:
    f.write(script_worm_content)

print("Created XRA0208 Burrowing Bio-Worm.")

# ===========================================================================
# 6. UPDATE MOD INFO & EXPORT ARCHIVE
# ===========================================================================
mod_info_path = os.path.join(mod_dir, "mod_info.lua")
mod_info_content = """name = "Raptor Swarm Faction"
version = 3
copyright = "Beyond All Reason & FAF Communities"
description = "Adds the biological Raptor Swarm faction with mobile swarmers (XRA0101), fliers (XRA0105), heavy crawlers (XRA0201), and a full biological structure suite: Raptor Gestation Hive (XRA0107), Bio-Acid Spire (XRA0108), Spore Anti-Air Spire (XRA0106), and Burrowing Bio-Worm (XRA0208)."
author = "BAR & FAF"
uid = "raptor-swarm-faction-faf-0003"
selectable = true
enabled = true
exclusive = false
ui_only = false
requires = {}
"""

with open(mod_info_path, "w") as f:
    f.write(mod_info_content)

export_zip = os.path.join(os.path.dirname(__file__), "exports", "RaptorFaction.zip")
print(f"Packaging mod to {export_zip}...")
with zipfile.ZipFile(export_zip, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(mod_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(mod_dir))
            z.write(full_path, rel_path)

print("ALL BUILDING PORTS COMPLETED SUCCESSFULLY!")
