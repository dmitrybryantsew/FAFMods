import os
import gzip
import struct
import math
import shutil
import zipfile
from scm_io import pad, pad_file, write_scm

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
icons_dir = os.path.join(mod_dir, "icons", "units")
units_root = os.path.join(mod_dir, "units")
dir_xra0101 = os.path.join(units_root, "XRA0101")
dir_xra0201 = os.path.join(units_root, "XRA0201")
dir_xra0105 = os.path.join(units_root, "XRA0105")

os.makedirs(icons_dir, exist_ok=True)
os.makedirs(dir_xra0201, exist_ok=True)
os.makedirs(dir_xra0105, exist_ok=True)

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

    # Root piece offset in S3O is at offset 52
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
    print(f"Created SCA: {filepath} ({num_frames} frames, {duration:.2f}s, size={file_size} bytes - Verified OK)")

# ===========================================================================
# 1. BUILD XRA0201: 6-LEGGED ALL-TERRAIN HEAVY CRAWLER
# ===========================================================================
print("\n" + "="*70)
print("BUILDING XRA0201: 6-Legged All-Terrain Heavy Crawler")
print("="*70)

s3o_6leg = get_bar_file('objects3d/raptors/raptor_6legged_l.s3o')
assert s3o_6leg, "Could not find raptor_6legged_l.s3o in BAR pool!"

scm_6leg_path = os.path.join(dir_xra0201, "XRA0201_lod0.scm")
pieces_6leg = convert_s3o_to_scm(s3o_6leg, scm_6leg_path)

piece_names_6leg = [p.name for p in pieces_6leg]
parent_indices_6leg = [p.parent_idx for p in pieces_6leg]
rest_pos_6leg = {p.name: p.local_pos for p in pieces_6leg}

# Copy Textures for XRA0201
albedo_6leg_raw = get_bar_file('unittextures/chicken_purple_l_color.dds')
assert albedo_6leg_raw, "chicken_purple_l_color.dds not found!"
with open(os.path.join(dir_xra0201, "XRA0201_Albedo.dds"), "wb") as f:
    f.write(albedo_6leg_raw)

# Shared normal and specular maps from XRA0101
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0201, "XRA0201_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0201, "XRA0201_SpecTeam.dds"))

# Icon for XRA0201
# Note: In BAR's lua config (raptor_6legged_l.lua), it referenced raptorc3c.DDS (a 4-legged lizard placeholder).
# We use our dedicated, custom-rendered 6-legged crawler portrait with soft shadow.
custom_icon_6leg = os.path.join(os.path.dirname(__file__), "static", "img", "XRA0201_icon.dds")
if os.path.exists(custom_icon_6leg):
    shutil.copyfile(custom_icon_6leg, os.path.join(dir_xra0201, "XRA0201_icon.dds"))
    shutil.copyfile(custom_icon_6leg, os.path.join(icons_dir, "xra0201_icon.dds"))
    print("Exported custom rendered XRA0201 6-legged crawler unit icons.")
else:
    icon_6leg_raw = get_bar_file('unitpics/raptors/raptorc3c.dds')
    if icon_6leg_raw:
        with open(os.path.join(dir_xra0201, "XRA0201_icon.dds"), "wb") as f:
            f.write(icon_6leg_raw)
        with open(os.path.join(icons_dir, "xra0201_icon.dds"), "wb") as f:
            f.write(icon_6leg_raw)
        print("Exported XRA0201 fallback unit icons.")

# Generate XRA0201 Walk Animation (Alternating Tripod + Spine Wave)
num_walk_frames = 24
walk_duration = 0.85
walk_frames_6leg = []

for f_idx in range(num_walk_frames):
    t_ratio = f_idx / num_walk_frames
    time_sec = t_ratio * walk_duration
    phase_A = 2.0 * math.pi * t_ratio
    phase_B = phase_A + math.pi

    walk_frames_6leg.append(time_sec)
    walk_frames_6leg.append(0)

    rot_dict = {name: (0.0, 0.0, 0.0) for name in piece_names_6leg}
    pos_dict = {name: rest_pos_6leg[name] for name in piece_names_6leg}

    # Torso bobbing and subtle sway
    torso_bob = math.sin(2.0 * phase_A) * 0.02
    torso_yaw = math.sin(phase_A) * math.radians(2.0)
    torso_roll = math.cos(phase_A) * math.radians(1.5)
    rot_dict['torso'] = (0.0, torso_yaw, torso_roll)
    lx, ly, lz = rest_pos_6leg['torso']
    pos_dict['torso'] = (lx, ly + torso_bob, lz)

    # Spine undulating wave through thor1..thor7
    for i in range(1, 8):
        b_name = f"thor{i}"
        wave_y = math.sin(phase_A - i * 0.45) * math.radians(5.0)
        wave_x = math.cos(phase_A - i * 0.45) * math.radians(2.5)
        rot_dict[b_name] = (wave_x, wave_y, 0.0)

    # Tripod A: Front-Left (1l), Mid-Right (2r), Rear-Left (3l)
    for leg_id, side in [(1, 'l'), (2, 'r'), (3, 'l')]:
        p = phase_A
        # Forward/backward stride on Y, lift on Z
        stride_sign = 1.0 if side == 'l' else -1.0
        thigh_yaw = math.sin(p) * math.radians(22.0) * stride_sign
        # Lift is only active when leg swings forward
        lift = max(0.0, math.sin(p)) * math.radians(18.0) * stride_sign
        knee_bend = -max(0.0, math.sin(p)) * math.radians(25.0) * stride_sign
        foot_plant = -math.sin(p) * math.radians(10.0) * stride_sign

        rot_dict[f"thigh{leg_id}{side}"] = (0.0, thigh_yaw, lift)
        rot_dict[f"leg{leg_id}{side}"] = (0.0, 0.0, knee_bend)
        rot_dict[f"foot{leg_id}{side}"] = (0.0, 0.0, foot_plant)

    # Tripod B: Front-Right (1r), Mid-Left (2l), Rear-Right (3r)
    for leg_id, side in [(1, 'r'), (2, 'l'), (3, 'r')]:
        p = phase_B
        stride_sign = 1.0 if side == 'l' else -1.0
        thigh_yaw = math.sin(p) * math.radians(22.0) * stride_sign
        lift = max(0.0, math.sin(p)) * math.radians(18.0) * stride_sign
        knee_bend = -max(0.0, math.sin(p)) * math.radians(25.0) * stride_sign
        foot_plant = -math.sin(p) * math.radians(10.0) * stride_sign

        rot_dict[f"thigh{leg_id}{side}"] = (0.0, thigh_yaw, lift)
        rot_dict[f"leg{leg_id}{side}"] = (0.0, 0.0, knee_bend)
        rot_dict[f"foot{leg_id}{side}"] = (0.0, 0.0, foot_plant)

    for b_name in piece_names_6leg:
        rx, ry, rz = rot_dict[b_name]
        px, py, pz = pos_dict[b_name]
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        walk_frames_6leg.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(
    os.path.join(dir_xra0201, "XRA0201_Awalk.sca"),
    num_walk_frames, walk_duration,
    piece_names_6leg, parent_indices_6leg,
    walk_frames_6leg
)

# Generate XRA0201 Death Animation (Legs collapse inwards, body drops to ground)
num_death_frames = 20
death_duration = 0.95
death_frames_6leg = []

for f_idx in range(num_death_frames):
    t_ratio = f_idx / (num_death_frames - 1)
    time_sec = t_ratio * death_duration
    progress = 1.0 - math.cos(t_ratio * math.pi * 0.5) # Ease in

    death_frames_6leg.append(time_sec)
    death_frames_6leg.append(0)

    rot_dict = {name: (0.0, 0.0, 0.0) for name in piece_names_6leg}
    pos_dict = {name: rest_pos_6leg[name] for name in piece_names_6leg}

    # Torso drops down to ground level
    lx, ly, lz = rest_pos_6leg['torso']
    pos_dict['torso'] = (lx, ly - 0.55 * progress, lz)
    rot_dict['torso'] = (progress * math.radians(10.0), 0.0, progress * math.radians(8.0))

    # Spine curls back limp
    for i in range(1, 8):
        rot_dict[f"thor{i}"] = (-progress * math.radians(12.0), progress * math.radians(4.0), 0.0)

    # All legs splay and curl inwards
    for side in ['l', 'r']:
        s = 1.0 if side == 'l' else -1.0
        for leg_id in [1, 2, 3]:
            rot_dict[f"thigh{leg_id}{side}"] = (0.0, 0.0, progress * math.radians(35.0) * s)
            rot_dict[f"leg{leg_id}{side}"] = (0.0, 0.0, -progress * math.radians(50.0) * s)
            rot_dict[f"foot{leg_id}{side}"] = (0.0, 0.0, progress * math.radians(40.0) * s)

    for b_name in piece_names_6leg:
        rx, ry, rz = rot_dict[b_name]
        px, py, pz = pos_dict[b_name]
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        death_frames_6leg.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(
    os.path.join(dir_xra0201, "XRA0201_Adeath01.sca"),
    num_death_frames, death_duration,
    piece_names_6leg, parent_indices_6leg,
    death_frames_6leg
)

# XRA0201 Blueprint
bp_6leg_content = """UnitBlueprint {
    AI = {
        TargetBones = {
            'torso',
            'thor4',
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
    BuildIconSortPriority = 35,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYTIER2FACTORY',
        'CYBRAN',
        'RAPTOR',
        'MOBILE',
        'LAND',
        'TECH2',
        'DIRECTFIRE',
        'ALLTERRAIN',
        'AMPHIBIOUS',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'BOT',
        'OVERLAYDIRECTFIRE',
    },
    CollisionOffsetY = 0.4,
    Defense = {
        AirThreatLevel = 0,
        ArmorType = 'Normal',
        EconomyThreatLevel = 0,
        Health = 2650,
        MaxHealth = 2650,
        RegenRate = 5,
        SubThreatLevel = 0,
        SurfaceThreatLevel = 8,
    },
    Description = '<LOC xra0201_desc>Biological T2 All-Terrain Heavy Crawler',
    Display = {
        Abilities = {
            '<LOC ability_allterrain>All-Terrain',
            '<LOC ability_amphibious>Amphibious',
            'Biological Armor',
        },
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0201/XRA0201_Adeath01.sca',
                AnimationRateMax = 1.1,
                AnimationRateMin = 0.9,
                Weight = 100,
            },
        },
        AnimationWalk = '/mods/RaptorFaction/units/XRA0201/XRA0201_Awalk.sca',
        AnimationWalkRate = 1.4,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0201/XRA0201_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0201/XRA0201_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0201/XRA0201_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0201/XRA0201_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        PlaceholderMeshName = 'UXL0021',
        SpawnRandomRotation = true,
        UniformScale = 1.1,
    },
    Economy = {
        BuildCostEnergy = 2400,
        BuildCostMass = 320,
        BuildTime = 1200,
        TeleportEnergyMod = 0.15,
        TeleportMassMod = 1,
        TeleportTimeMod = 0.01,
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
        FactionName = 'Cybran',
        Icon = 'amph',
        TechLevel = 'RULEUTL_Advanced',
        UnitName = 'Heavy Raptor Crawler',
        UnitWeight = 1,
    },
    Intel = {
        VisionRadius = 26,
        WaterVisionRadius = 20,
    },
    Interface = {
        HelpText = '<LOC xra0201_help>Armored 6-legged all-terrain crawler equipped with venomous bio-acid spine artillery launcher.',
    },
    LifeBarHeight = 0.08,
    LifeBarOffset = 0.8,
    LifeBarSize = 1.2,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Air = false,
            LAYER_Land = true,
            LAYER_Orbit = false,
            LAYER_Seabed = true,
            LAYER_Sub = false,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        Elevation = 0,
        MaxAcceleration = 3.2,
        MaxBrake = 3.2,
        MaxSpeed = 3.6,
        MaxSpeedReverse = 0,
        MaxSteerForce = 15,
        MeshExtentsX = 1.4,
        MeshExtentsY = 1.2,
        MeshExtentsZ = 2.0,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        RotateOnSpot = true,
        RotateOnSpotThreshold = 0.5,
        TurnRadius = 0,
        TurnRate = 180,
    },
    SelectionCenterOffsetZ = -0.1,
    SelectionSizeX = 0.9,
    SelectionSizeZ = 1.2,
    SelectionThickness = 0.45,
    SizeX = 1.2,
    SizeY = 1.1,
    SizeZ = 1.8,
    StrategicIconName = 'icon_bot2_directfire',
    StrategicIconSortPriority = 115,
    Veteran = {
        Level1 = 6,
        Level2 = 12,
        Level3 = 18,
        Level4 = 24,
        Level5 = 30,
    },
    Weapon = {
        {
            AboveWaterTargetsOnly = false,
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Attack',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            BallisticArc = 'RULEUBA_LowArc',
            CollideFriendly = false,
            Damage = 175,
            DamageRadius = 1.0,
            DamageType = 'Normal',
            DisplayName = 'Acid Stinger Spines',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Seabed = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringRandomness = 0.2,
            FiringTolerance = 2,
            Label = 'SpineStinger',
            MaxRadius = 26,
            MuzzleSalvoDelay = 0.15,
            MuzzleSalvoSize = 2,
            MuzzleVelocity = 32,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp',
            ProjectileLifetimeUsesMultiplier = 1.3,
            ProjectilesPerOnFire = 2,
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
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1.0,
            TargetCheckInterval = 0.25,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'TECH2 MOBILE',
                'TECH3 MOBILE',
                'TECH1 MOBILE',
                'STRUCTURE DEFENSE',
                'SPECIALLOWPRI',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            TrackingRadius = 1.15,
            TurretBoneMuzzle = 'flare',
            TurretBonePitch = 'thor6',
            TurretBoneYaw = 'torso',
            TurretDualManipulators = false,
            TurretPitch = 10,
            TurretPitchRange = 55,
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

with open(os.path.join(dir_xra0201, "XRA0201_unit.bp"), "w", encoding="utf-8") as f:
    f.write(bp_6leg_content)
print("Created XRA0201_unit.bp.")

# XRA0201 Script
script_6leg_content = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon
local EffectTemplate = import('/lua/EffectTemplates.lua')

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFlesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class RaptorCrawlerWeapon : DefaultProjectileWeapon
local RaptorCrawlerWeapon = ClassWeapon(DefaultProjectileWeapon) {
    FxMuzzleFlash = EffectTemplate.PhasicAutoGunMuzzleFlash,

    CreateProjectileAtMuzzle = function(self, muzzle)
        local proj = DefaultProjectileWeapon.CreateProjectileAtMuzzle(self, muzzle)
        self.unit:PlayAttackMotion()
        return proj
    end,
}

---@class XRA0201 : CWalkingLandUnit
XRA0201 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        SpineStinger = ClassWeapon(RaptorCrawlerWeapon) {},
    },

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
        self.AttackAnimRotator = CreateRotator(self, 'thor7', 'x', 0, 300, 300)
    end,

    PlayAttackMotion = function(self)
        if self.AttackThread then KillThread(self.AttackThread) end
        self.AttackThread = self:ForkThread(function()
            local r = self.AttackAnimRotator
            if not r then return end
            r:SetGoal(-25); r:SetSpeed(240)
            WaitFor(r)
            r:SetGoal(0); r:SetSpeed(120)
        end)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        local bloodEmitters = {
            '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
            '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
            '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
        }
        for _, emit in bloodEmitters do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.4)
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        local bloodEmitters = {
            '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
            '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
            '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
        }
        local scale = 1.5 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in bloodEmitters do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}

TypeClass = XRA0201
"""

with open(os.path.join(dir_xra0201, "XRA0201_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_6leg_content)
print("Created XRA0201_script.lua.")


# ===========================================================================
# 2. BUILD XRA0105: FLYING AIR SWARM FIGHTER
# ===========================================================================
print("\n" + "="*70)
print("BUILDING XRA0105: Flying Air Swarm Fighter")
print("="*70)

s3o_fly = get_bar_file('objects3d/raptors/raptorw1_mini.s3o')
assert s3o_fly, "Could not find raptorw1_mini.s3o in BAR pool!"

scm_fly_path = os.path.join(dir_xra0105, "XRA0105_lod0.scm")
pieces_fly = convert_s3o_to_scm(s3o_fly, scm_fly_path)

piece_names_fly = [p.name for p in pieces_fly]
parent_indices_fly = [p.parent_idx for p in pieces_fly]
rest_pos_fly = {p.name: p.local_pos for p in pieces_fly}

# Copy Textures for XRA0105
albedo_fly_raw = get_bar_file('unittextures/chicken_1_m_color.dds')
assert albedo_fly_raw, "chicken_1_m_color.dds not found!"
with open(os.path.join(dir_xra0105, "XRA0105_Albedo.dds"), "wb") as f:
    f.write(albedo_fly_raw)

shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0105, "XRA0105_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0105, "XRA0105_SpecTeam.dds"))

# Icon for XRA0105
icon_fly_raw = get_bar_file('unitpics/raptors/raptorw1_mini.dds')
if icon_fly_raw:
    with open(os.path.join(dir_xra0105, "XRA0105_icon.dds"), "wb") as f:
        f.write(icon_fly_raw)
    with open(os.path.join(icons_dir, "xra0105_icon.dds"), "wb") as f:
        f.write(icon_fly_raw)
    print("Exported XRA0105 unit icons.")

# Generate XRA0105 Flight Cycle Animation (Flapping Wings + Aerodynamic Phase Lag + Bobbing)
num_fly_frames = 20
fly_duration = 0.45
fly_frames = []

for f_idx in range(num_fly_frames):
    t_ratio = f_idx / num_fly_frames
    time_sec = t_ratio * fly_duration
    phase = 2.0 * math.pi * t_ratio

    fly_frames.append(time_sec)
    fly_frames.append(0)

    rot_dict = {name: (0.0, 0.0, 0.0) for name in piece_names_fly}
    pos_dict = {name: rest_pos_fly[name] for name in piece_names_fly}

    # Wing Flapping (Z-axis roll)
    # Inner wing moves +-30 degrees
    flap_inner = math.sin(phase) * math.radians(30.0)
    # Outer wing flaps with 35-degree (0.6 rad) aerodynamic delay and greater amplitude (+-42 deg)
    flap_outer = math.sin(phase - 0.6) * math.radians(42.0)

    # Left wings roll positive up, right wings roll negative up
    rot_dict["liwing"] = (0.0, 0.0, flap_inner)
    rot_dict["lowing"] = (0.0, 0.0, flap_outer)
    rot_dict["riwing"] = (0.0, 0.0, -flap_inner)
    rot_dict["rowing"] = (0.0, 0.0, -flap_outer)

    # Body Vertical Lift & Pitch bobbing
    # When wings flap down (phase ~ pi/2), body receives upward impulse
    lift = -math.sin(phase) * 0.06
    body_pitch = math.sin(phase) * math.radians(4.0)
    lx, ly, lz = rest_pos_fly["body"]
    pos_dict["body"] = (lx, ly + lift, lz)
    rot_dict["body"] = (body_pitch, 0.0, 0.0)

    # Tail counter-balance pitch
    rot_dict["tail"] = (-body_pitch * 1.6, 0.0, 0.0)

    # Head and mandibles remain stable for weapon tracking
    rot_dict["head"] = (0.0, 0.0, 0.0)

    for b_name in piece_names_fly:
        rx, ry, rz = rot_dict[b_name]
        px, py, pz = pos_dict[b_name]
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        fly_frames.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(
    os.path.join(dir_xra0105, "XRA0105_Afly.sca"),
    num_fly_frames, fly_duration,
    piece_names_fly, parent_indices_fly,
    fly_frames
)

# Generate XRA0105 Death Animation (Folded wings spiral / tumble crash)
num_death_fly = 24
death_fly_dur = 1.1
death_frames_fly = []

for f_idx in range(num_death_fly):
    t_ratio = f_idx / (num_death_fly - 1)
    time_sec = t_ratio * death_fly_dur
    progress = 1.0 - math.cos(t_ratio * math.pi * 0.5)

    death_frames_fly.append(time_sec)
    death_frames_fly.append(0)

    rot_dict = {name: (0.0, 0.0, 0.0) for name in piece_names_fly}
    pos_dict = {name: rest_pos_fly[name] for name in piece_names_fly}

    # Body falls and pitches downward violently into a spin
    lx, ly, lz = rest_pos_fly["body"]
    pos_dict["body"] = (lx, ly - 1.2 * progress, lz)
    pitch = progress * math.radians(70.0)
    roll = progress * math.radians(240.0)
    rot_dict["body"] = (pitch, 0.0, roll)

    # Wings fold back limp along body
    rot_dict["liwing"] = (progress * math.radians(30.0), 0.0, -progress * math.radians(60.0))
    rot_dict["riwing"] = (progress * math.radians(30.0), 0.0, progress * math.radians(60.0))
    rot_dict["lowing"] = (0.0, 0.0, -progress * math.radians(45.0))
    rot_dict["rowing"] = (0.0, 0.0, progress * math.radians(45.0))
    rot_dict["tail"] = (-progress * math.radians(45.0), 0.0, 0.0)

    for b_name in piece_names_fly:
        rx, ry, rz = rot_dict[b_name]
        px, py, pz = pos_dict[b_name]
        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        death_frames_fly.extend([px, py, pz, qw, qx, qy, qz])

save_sca_file(
    os.path.join(dir_xra0105, "XRA0105_Adeath01.sca"),
    num_death_fly, death_fly_dur,
    piece_names_fly, parent_indices_fly,
    death_frames_fly
)

# XRA0105 Blueprint
bp_fly_content = """UnitBlueprint {
    AI = {
        TargetBones = {
            'body',
            'head',
        },
    },
    Air = {
        AutoLandTime = 1,
        BankFactor = 1.2,
        BankForward = false,
        BreakOffDistance = 15,
        BreakOffTrigger = 10,
        CanFly = true,
        CombatTurnSpeed = 1.8,
        EngageDistance = 50,
        KLift = 3,
        KLiftDamping = 2.5,
        KMove = 1.5,
        KMoveDamping = 1,
        KRoll = 1.5,
        KRollDamping = 1,
        KTurn = 1.5,
        KTurnDamping = 1.5,
        LiftFactor = 7,
        MaxAirspeed = 13.5,
        MinAirspeed = 7,
        StartTurnDistance = 5,
        TightTurnMultiplier = 1.05,
        TurnSpeed = 2.4,
        WingLoopRange = 0,
    },
    Audio = {
        AirUnitWaterImpact = Sound {
            Bank = 'Explosions',
            Cue = 'Expl_Water_Lrg_01',
            LodCutoff = 'UnitMove_LodCutoff',
        },
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
            Level4 = 4,
            Level5 = 5,
        },
    },
    BuildIconSortPriority = 30,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYTIER1FACTORY',
        'CYBRAN',
        'RAPTOR',
        'MOBILE',
        'AIR',
        'TECH1',
        'ANTIAIR',
        'HIGHALTAIR',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYANTIAIR',
    },
    CollisionOffsetY = 0.2,
    Defense = {
        AirThreatLevel = 3,
        ArmorType = 'Light',
        EconomyThreatLevel = 0,
        Health = 135,
        MaxHealth = 135,
        RegenRate = 2,
        SubThreatLevel = 0,
        SurfaceThreatLevel = 0,
    },
    Description = '<LOC xra0105_desc>Biological T1 Air Swarm Fighter',
    Display = {
        Abilities = {
            '<LOC ability_aa>Anti-Air',
            'Bio Wing Membrane',
        },
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0105/XRA0105_Adeath01.sca',
                AnimationRateMax = 1.2,
                AnimationRateMin = 0.8,
                Weight = 100,
            },
        },
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0105/XRA0105_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0105/XRA0105_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0105/XRA0105_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0105/XRA0105_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        PlaceholderMeshName = 'UXA0001',
        SpawnRandomRotation = true,
        UniformScale = 1.3,
    },
    Economy = {
        BuildCostEnergy = 1800,
        BuildCostMass = 45,
        BuildTime = 450,
    },
    Footprint = {
        MaxSlope = 0.25,
        SizeX = 1,
        SizeZ = 1,
    },
    General = {
        Category = 'Fighter',
        Classification = 'RULEUC_MilitaryAircraft',
        CommandCaps = {
            RULEUCC_Attack = true,
            RULEUCC_CallTransport = false,
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
        FactionName = 'Cybran',
        Icon = 'air',
        TechLevel = 'RULEUTL_Basic',
        UnitName = 'Raptor Wing Swarmer',
        UnitWeight = 1,
    },
    Intel = {
        VisionRadius = 28,
    },
    Interface = {
        HelpText = '<LOC xra0105_help>Fast agile biological flyer specializing in aerial interception using venomous bio-projectiles and snapping scissor mandibles.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.5,
    LifeBarSize = 0.8,
    Physics = {
        BuildOnLayerCaps = {
            LAYER_Air = true,
            LAYER_Land = false,
            LAYER_Orbit = false,
            LAYER_Seabed = false,
            LAYER_Sub = false,
            LAYER_Water = false,
        },
        Elevation = 9.5,
        FuelRechargeRate = 5,
        FuelUseTime = 400,
        GroundCollisionOffset = 1.6,
        MaxSpeed = 13.5,
        MeshExtentsX = 1.5,
        MeshExtentsY = 0.5,
        MeshExtentsZ = 1.2,
        MotionType = 'RULEUMT_Air',
    },
    SelectionSizeX = 0.8,
    SelectionSizeZ = 0.7,
    SelectionThickness = 0.45,
    SizeSphere = 1.6,
    SizeX = 1.2,
    SizeY = 0.4,
    SizeZ = 1.0,
    StrategicIconName = 'icon_fighter1_antiair',
    StrategicIconSortPriority = 75,
    Transport = {
        AirClass = true,
        TransportClass = 1,
    },
    Veteran = {
        Level1 = 2,
        Level2 = 4,
        Level3 = 6,
        Level4 = 8,
        Level5 = 10,
    },
    Weapon = {
        {
            Audio = {
                Fire = Sound {
                    Bank = 'Raptor_Flyer_Attack',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            AutoInitiateAttackCommand = true,
            BallisticArc = 'RULEUBA_None',
            CannotAttackGround = true,
            CollideFriendly = false,
            Damage = 18,
            DamageType = 'Normal',
            DisplayName = 'Bio Aerial Spores',
            FireTargetLayerCapsTable = {
                Air = 'Air',
            },
            FiringTolerance = 2,
            Label = 'AirBioSpike',
            MaxRadius = 24,
            MuzzleSalvoDelay = 0.1,
            MuzzleSalvoSize = 2,
            MuzzleVelocity = 45,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp',
            ProjectileLifetimeUsesMultiplier = 1.25,
            ProjectilesPerOnFire = 2,
            RackBones = {
                {
                    MuzzleBones = {
                        'firepoint',
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
            RangeCategory = 'UWRC_AntiAir',
            RateOfFire = 2.0,
            TargetCheckInterval = 0.2,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'AIR MOBILE TECH1',
                'AIR MOBILE TECH2',
                'AIR MOBILE TECH3',
                'SPECIALLOWPRI',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE, LAND, STRUCTURE',
            TargetRestrictOnlyAllow = 'AIR',
            TrackingRadius = 1.25,
            TurretBoneMuzzle = 'firepoint',
            TurretBonePitch = 'head',
            TurretBoneYaw = 'body',
            TurretDualManipulators = false,
            TurretPitch = 0,
            TurretPitchRange = 40,
            TurretPitchSpeed = 120,
            TurretYaw = 0,
            TurretYawRange = 40,
            TurretYawSpeed = 120,
            Turreted = true,
            WeaponCategory = 'Anti Air',
        },
        {
            AboveWaterTargetsOnly = true,
            Damage = 25,
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

with open(os.path.join(dir_xra0105, "XRA0105_unit.bp"), "w", encoding="utf-8") as f:
    f.write(bp_fly_content)
print("Created XRA0105_unit.bp.")

# XRA0105 Script
script_fly_content = """local CAirUnit = import('/lua/cybranunits.lua').CAirUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon
local EffectTemplate = import('/lua/EffectTemplates.lua')

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class RaptorAirWeapon : DefaultProjectileWeapon
local RaptorAirWeapon = ClassWeapon(DefaultProjectileWeapon) {
    FxMuzzleFlash = EffectTemplate.PhasicAutoGunMuzzleFlash,

    CreateProjectileAtMuzzle = function(self, muzzle)
        local proj = DefaultProjectileWeapon.CreateProjectileAtMuzzle(self, muzzle)
        self.unit:PlayBiteAttack()
        return proj
    end,
}

---@class XRA0105 : CAirUnit
XRA0105 = ClassUnit(CAirUnit) {
    Weapons = {
        AirBioSpike = ClassWeapon(RaptorAirWeapon) {},
    },

    OnCreate = function(self)
        CAirUnit.OnCreate(self)
        self.Rotators = {
            lsack = CreateRotator(self, 'lsack', 'y', 0, 600, 1000),
            rsack = CreateRotator(self, 'rsack', 'y', 0, 600, 1000),
            lblade = CreateRotator(self, 'lblade', 'y', 0, 600, 1000),
            rblade = CreateRotator(self, 'rblade', 'y', 0, 600, 1000),
        }
        -- Native C++ continuous flapping animation using generated Afly.sca
        local flyAnim = CreateAnimator(self)
        flyAnim:PlayAnim('/mods/RaptorFaction/units/XRA0105/XRA0105_Afly.sca', true)
        flyAnim:SetRate(2.2)
        self.FlyAnimManip = flyAnim
        self.Trash:Add(flyAnim)
    end,

    PlayBiteAttack = function(self)
        if self.BiteThread then KillThread(self.BiteThread) end
        self.BiteThread = self:ForkThread(function()
            local r = self.Rotators
            if not r then return end
            r.lsack:SetGoal(-45); r.lsack:SetSpeed(600)
            r.rsack:SetGoal(45);  r.rsack:SetSpeed(600)
            r.lblade:SetGoal(55); r.lblade:SetSpeed(600)
            r.rblade:SetGoal(-55); r.rblade:SetSpeed(600)
            WaitFor(r.rblade)
            r.lsack:SetGoal(0); r.lsack:SetSpeed(160)
            r.rsack:SetGoal(0); r.rsack:SetSpeed(160)
            r.lblade:SetGoal(0); r.lblade:SetSpeed(160)
            r.rblade:SetGoal(0); r.rblade:SetSpeed(160)
        end)
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
        local scale = 1.1 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}

TypeClass = XRA0105
"""

with open(os.path.join(dir_xra0105, "XRA0105_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_fly_content)
print("Created XRA0105_script.lua.")


# ===========================================================================
# 3. UPDATE MOD_INFO.LUA
# ===========================================================================
mod_info_content = """name = "Raptor Swarm Faction"
version = 2
copyright = "Beyond All Reason & FAF Communities"
description = "Adds the biological Raptor Swarm faction with 3 fully playable units: T1 Raptor Swarmer (XRA0101), T2 6-Legged All-Terrain Crawler (XRA0201), and T1 Winged Swarm Fighter (XRA0105). Spawnable in F2 cheat menu under 'Raptor'."
author = "BAR & FAF"
uid = "raptor-swarm-faction-faf-0002"
selectable = true
enabled = true
exclusive = false
ui_only = false
requires = {}
"""

with open(os.path.join(mod_dir, "mod_info.lua"), "w", encoding="utf-8") as f:
    f.write(mod_info_content)
# ===========================================================================
# 3.5 GENERATE MICROSOFT XACT SOUND BANKS (RAPTOR AUDIO)
# ===========================================================================
import wave

sounds_dir = os.path.join(mod_dir, "sounds")
raptor_sounds_dir = os.path.join(sounds_dir, "raptors")
os.makedirs(raptor_sounds_dir, exist_ok=True)

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
    
    # 1. XWB
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
    
    # 2. XSB
    sb = bytearray(sb_tmpl[:277])
    sb_name_64 = soundbank_name.encode('ascii')[:63].ljust(64, b'\x00')
    sb[0x4a : 0x4a + 64] = sb_name_64
    sb[0x8a : 0x8a + 64] = wb_name_64
    sb[229] = 0  # loopCount = 0 (play once, disable infinite repeat!)
    for i in range(16):
        struct.pack_into('<H', sb, 239 + i*2, 0)
    cue_bytes = cue_name.encode('ascii') + b'\x00'
    sb.extend(cue_bytes)
    struct.pack_into('<H', sb, 0x1e, len(cue_bytes))
    crc = calc_xact_crc(sb[18:])
    struct.pack_into('<H', sb, 8, crc)
    return bytes(xwb_bytes), bytes(sb)

# Prepare WAVs
import io
atk_wav = get_bar_file('sounds/raptors/smallraptorattack.wav')
d_wav = get_bar_file('sounds/raptors/smallraptordead.wav')
fly_atk_wav = get_bar_file('sounds/raptors/talonattack.wav')
fly_d_wav = get_bar_file('sounds/raptors/talondie.wav')

# Silence wav
silence_buf = io.BytesIO()
with wave.open(silence_buf, 'wb') as sw:
    sw.setnchannels(1)
    sw.setsampwidth(2)
    sw.setframerate(44100)
    sw.writeframes(b'\x00' * 8820)
silence_wav = silence_buf.getvalue()

banks = [
    ('Raptor_Attack', 'Raptor_Attack', 'Attack', atk_wav, 'smallraptorattack.wav'),
    ('Raptor_Death', 'Raptor_Death', 'Death', d_wav, 'smallraptordead.wav'),
    ('Raptor_Flyer_Attack', 'Raptor_Flyer_Attack', 'Attack', fly_atk_wav, 'talonattack.wav'),
    ('Raptor_Flyer_Death', 'Raptor_Flyer_Death', 'Death', fly_d_wav, 'talondie.wav'),
    ('Raptor_Silence', 'Raptor_Silence', 'Silence', silence_wav, 'silence.wav'),
]

for sb_name, wb_name, cue, wdata, fname in banks:
    if wdata:
        xwb, xsb = build_xact_bank(sb_name, wb_name, cue, wdata)
        with open(os.path.join(sounds_dir, f'{sb_name}.xwb'), 'wb') as f:
            f.write(xwb)
        with open(os.path.join(sounds_dir, f'{sb_name}.xsb'), 'wb') as f:
            f.write(xsb)
        with open(os.path.join(raptor_sounds_dir, fname), 'wb') as f:
            f.write(wdata)
        print(f"Generated XACT bank: {sb_name}")

# ===========================================================================
# 3.8 GENERATE BLOODY DEATH PARTICLES
# ===========================================================================
effects_dir = os.path.join(mod_dir, "effects", "emitters")
os.makedirs(effects_dir, exist_ok=True)

blood_emitters_data = {
    'raptor_blood_spray_01_emit.bp': '''EmitterBlueprint {
    BlueprintId = 'raptor_blood_spray_01',
    Lifetime = 0.80,
    Repeattime = 0.80,
    TextureFramecount = 4.00,
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
    SortOrder = 0.00,
    Texture = '/textures/particles/build_paint_spray_01.dds',
    RampTexture = '/textures/particles/ramp_red_build_spray.dds',
    XDirectionCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.40, y=0.00, z=0.50 },
        },
    },
    YDirectionCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.40, y=0.60, z=0.30 },
        },
    },
    ZDirectionCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.40, y=0.00, z=0.50 },
        },
    },
    EmitRateCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.05, y=35.00, z=0.00 },
            { x=0.25, y=0.00, z=0.00 },
        },
    },
    LifetimeCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.40, y=0.75, z=0.20 },
        },
    },
    VelocityCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.10, y=4.50, z=1.50 },
            { x=0.60, y=0.50, z=0.00 },
        },
    },
    XAccelCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.40, y=0.00, z=0.00 },
        },
    },
    YAccelCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.40, y=-0.50, z=0.00 },
        },
    },
    ZAccelCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.40, y=0.00, z=0.00 },
        },
    },
    StartSizeCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.10, y=0.35, z=0.10 },
        },
    },
    EndSizeCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.70, y=0.55, z=0.15 },
        },
    },
    InitialRotationCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.40, y=180.00, z=180.00 },
        },
    },
    RotationRateCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.40, y=0.00, z=45.00 },
        },
    },
    FrameRateCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.40, y=2.00, z=1.00 },
        },
    },
    TextureSelectionCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.40, y=0.00, z=0.00 },
        },
    },
    RampSelectionCurve = {
        XRange = 0.80,
        Keys = {
            { x=0.40, y=0.00, z=0.00 },
        },
    },
}
''',
    'raptor_flesh_chunks_01_emit.bp': '''EmitterBlueprint {
    BlueprintId = 'raptor_flesh_chunks_01',
    Lifetime = 1.20,
    Repeattime = 1.20,
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
    TextureStripcount = 16.00,
    SortOrder = 0.00,
    Texture = '/textures/particles/debris_alpha_02.dds',
    RampTexture = '/textures/particles/ramp_red_02.dds',
    XDirectionCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.60, y=0.00, z=0.45 },
        },
    },
    YDirectionCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.60, y=0.75, z=0.25 },
        },
    },
    ZDirectionCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.60, y=0.00, z=0.45 },
        },
    },
    EmitRateCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.05, y=18.00, z=0.00 },
            { x=0.20, y=0.00, z=0.00 },
        },
    },
    LifetimeCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.60, y=1.00, z=0.20 },
        },
    },
    VelocityCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.10, y=5.00, z=1.80 },
            { x=0.80, y=0.20, z=0.00 },
        },
    },
    XAccelCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.60, y=0.00, z=0.00 },
        },
    },
    YAccelCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.60, y=-0.70, z=0.00 },
        },
    },
    ZAccelCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.60, y=0.00, z=0.00 },
        },
    },
    StartSizeCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.10, y=0.25, z=0.10 },
        },
    },
    EndSizeCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.90, y=0.25, z=0.10 },
        },
    },
    InitialRotationCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.60, y=180.00, z=180.00 },
        },
    },
    RotationRateCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.60, y=90.00, z=90.00 },
        },
    },
    FrameRateCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.60, y=0.00, z=0.00 },
        },
    },
    TextureSelectionCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.60, y=8.00, z=16.00 },
        },
    },
    RampSelectionCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.60, y=1.00, z=1.00 },
        },
    },
}
''',
    'raptor_blood_cloud_01_emit.bp': '''EmitterBlueprint {
    BlueprintId = 'raptor_blood_cloud_01',
    Lifetime = 1.00,
    Repeattime = 1.00,
    TextureFramecount = 1.00,
    Blendmode = 0.00,
    LocalVelocity = false,
    LocalAcceleration = false,
    Gravity = false,
    AlignRotation = false,
    AlignToBone = false,
    Flat = false,
    LODCutoff = 200.00,
    EmitIfVisible = true,
    CatchupEmit = true,
    CreateIfVisible = false,
    SnapToWaterline = false,
    OnlyEmitOnWater = false,
    InterpolateEmission = true,
    TextureStripcount = 1.00,
    SortOrder = 0.00,
    Texture = '/textures/particles/cloud_smoke_alpha_03.dds',
    RampTexture = '/textures/particles/ramp_red_01.dds',
    XDirectionCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.00, z=0.20 },
        },
    },
    YDirectionCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.30, z=0.15 },
        },
    },
    ZDirectionCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.00, z=0.20 },
        },
    },
    EmitRateCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.05, y=8.00, z=0.00 },
            { x=0.20, y=0.00, z=0.00 },
        },
    },
    LifetimeCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.90, z=0.10 },
        },
    },
    VelocityCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.10, y=1.80, z=0.50 },
            { x=0.70, y=0.10, z=0.00 },
        },
    },
    XAccelCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.00, z=0.00 },
        },
    },
    YAccelCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.05, z=0.00 },
        },
    },
    ZAccelCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.00, z=0.00 },
        },
    },
    StartSizeCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.10, y=0.60, z=0.20 },
        },
    },
    EndSizeCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.80, y=1.80, z=0.40 },
        },
    },
    InitialRotationCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=180.00, z=180.00 },
        },
    },
    RotationRateCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.00, z=15.00 },
        },
    },
    FrameRateCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.50, y=0.00, z=0.00 },
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
''',
}

for fname, content in blood_emitters_data.items():
    with open(os.path.join(effects_dir, fname), "w", encoding="utf-8") as f:
        f.write(content)
print("Generated bloody death particle emitter blueprints.")

# ===========================================================================
# 4. PACKAGE MOD ZIP EXPORT
# ===========================================================================
export_dir = r"E:\Games\FAFMods\exports"
os.makedirs(export_dir, exist_ok=True)
zip_path = os.path.join(export_dir, "RaptorFaction.zip")

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(mod_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(mod_dir))
            zipf.write(full_path, rel_path)

print(f"Mod successfully packaged and exported to: {zip_path}")
print("ALL TASKS COMPLETED!")
