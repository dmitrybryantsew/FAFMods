"""
Import Zero-K Models into Supreme Commander FAF (Raptor Swarm Faction)
Ports 7 selected models from Zero-K zk-stable.sdz:
  1. chicken_digger    -> XRA0116: Subterranean Digger (T1 Burrowing Raider)
  2. chickend          -> XRA0121: Chitin Spore Tube (T1 Static Creep Defense Tube)
  3. chicken_shield    -> XRA0225: Bio-Shield Beetle (T2 Mobile Carapace Shield & AA)
  4. chicken_rafflesia -> XRA0226: Rafflesia Shield Bloom (T2 Static Bio-Shield Canopy)
  5. chicken_blimpy    -> XRA0227: Bio-Zeppelin Blimpy (T2 Living Brood Carrier & Dodo Bomber)
  6. chicken_tiamat    -> XRA0328: Tiamat Bio-Juggernaut (T3 Heavy Armored Bruiser)
  7. chicken_dragon    -> XRA0329: Apex White Dragon Herald (T3 Prime Assault Sub-Boss)
"""

import os
import io
import math
import struct
import shutil
import zipfile
from PIL import Image
from scm_io import pad, pad_file, write_scm

ZK_PATH = r"P:\SteamLibrary\steamapps\common\Zero-K\games\zk-stable.sdz"
MOD_DIR = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
UNITS_ROOT = os.path.join(MOD_DIR, "units")
ICONS_DIR = os.path.join(MOD_DIR, "icons", "units")
REF_XRA0101 = os.path.join(UNITS_ROOT, "XRA0101")
REF_NORMALS = os.path.join(REF_XRA0101, "XRA0101_NormalsTS.dds")
REF_SPECTEAM = os.path.join(REF_XRA0101, "XRA0101_SpecTeam.dds")
REF_ICON = os.path.join(REF_XRA0101, "XRA0101_icon.dds")

# ---------------------------------------------------------------------------
# S3O Parser & SCM Builder
# ---------------------------------------------------------------------------
class PieceNode:
    def __init__(self, name, parent_idx, ox, oy, oz, scale=0.06):
        self.name = name
        self.parent_idx = parent_idx
        self.local_pos = (ox * scale, oy * scale, oz * scale)
        self.world_pos = (0.0, 0.0, 0.0)
        self.verts = []
        self.indices = []

def convert_s3o_to_scm(s3o_bytes, scm_filepath, scale=0.06):
    magic, ver, rad, h, mx, my, mz, root_off, col_off, tex1_off, tex2_off = struct.unpack('<12sI5f4I', s3o_bytes[:52])
    pieces = []

    def parse_piece(off, parent_idx=-1):
        name_off, n_child, child_off, n_verts, v_off, v_type, prim_type, idx_cnt, idx_off, col_data, ox, oy, oz = struct.unpack('<10I3f', s3o_bytes[off:off+52])
        name = s3o_bytes[name_off:].split(b'\x00')[0].decode('latin1', 'ignore').strip()
        if not name:
            name = f"piece_{len(pieces)}"
        curr_idx = len(pieces)
        node = PieceNode(name, parent_idx, ox, oy, oz, scale=scale)
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
                wx = node.world_pos[0] + vx * scale
                wy = node.world_pos[1] + vy * scale
                wz = node.world_pos[2] + vz * scale
                node.verts.append((wx, wy, wz, nx, ny, nz, tu, tv))

        if idx_cnt > 0:
            idx_data = s3o_bytes[idx_off : idx_off + idx_cnt*4]
            raw_indices = struct.unpack(f'<{idx_cnt}I', idx_data)
            node.indices = list(raw_indices)

        if n_child > 0 and child_off > 0:
            child_offsets = struct.unpack(f'<{n_child}I', s3o_bytes[child_off : child_off + 4*n_child])
            for co in child_offsets:
                parse_piece(co, curr_idx)

    parse_piece(root_off)

    total_bone_data = []
    bone_name_data = []
    for p in pieces:
        bone_name_data.append(bytearray(p.name.encode('ascii', 'ignore')))

    bone_name_offset = 48 + pad(48)
    cur_name_off = bone_name_offset

    for p in pieces:
        inv_rest = [
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            -p.world_pos[0], -p.world_pos[1], -p.world_pos[2], 1.0
        ]
        pos = [p.local_pos[0], p.local_pos[1], p.local_pos[2]]
        rot = [1.0, 0.0, 0.0, 0.0]
        p_idx = p.parent_idx

        bone_entry = inv_rest + pos + rot + [cur_name_off, p_idx, 0, 0]
        total_bone_data.extend(bone_entry)
        cur_name_off += len(p.name) + 1

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
    print(f"Created SCM: {os.path.basename(scm_filepath)} ({len(pieces)} bones, {vert_counter} verts)")
    return pieces

# ---------------------------------------------------------------------------
# Procedural Animation Generator (SCA)
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
    qz = cx * cy * sz - sx * sz * cz
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

def generate_procedural_anims(pieces, walk_path, death_path, motion_type="LAND"):
    names = [p.name for p in pieces]
    parents = [p.parent_idx for p in pieces]
    num_frames = 20
    dur = 0.6 if motion_type != "AIR" else 0.8
    frames = []

    for f_idx in range(num_frames):
        t = f_idx / num_frames
        p = t * 2.0 * math.pi
        rot = {}
        pos = {p_node.name: p_node.local_pos for p_node in pieces}

        if motion_type == "AIR":
            # Blimpy / Flying creature animation
            for b_name in names:
                low = b_name.lower()
                if 'wing' in low:
                    sign = 1.0 if 'l' in low else -1.0
                    rot[b_name] = (0, 0, math.sin(p) * math.radians(24.0) * sign)
                elif 'sack' in low:
                    sign = 1.0 if 'l' in low else -1.0
                    rot[b_name] = (math.sin(p) * math.radians(8.0), 0, math.cos(p) * math.radians(6.0) * sign)
                elif 'tail' in low:
                    rot[b_name] = (0, math.sin(p) * math.radians(12.0), 0)
                elif 'body' in low or 'base' in low:
                    rot[b_name] = (math.sin(p) * math.radians(4.0), 0, 0)
        elif motion_type == "STRUCTURE":
            # Static organic breathing / pulsing animation
            for b_name in names:
                low = b_name.lower()
                if 'tentacle' in low or 'rotator' in low:
                    rot[b_name] = (math.sin(p) * math.radians(8.0), math.cos(p) * math.radians(6.0), 0)
                elif 'body' in low or 'center' in low:
                    rot[b_name] = (math.sin(p) * math.radians(3.0), 0, 0)
        else:
            # Land Walker (Biped / Quadruped)
            for b_name in names:
                low = b_name.lower()
                is_back = 'b' in low
                phase_offset = math.pi if is_back else 0.0
                sign = 1.0 if 'l' in low else -1.0

                if 'thigh' in low or 'upperleg' in low:
                    rot[b_name] = (math.sin(p + phase_offset) * math.radians(32.0) * sign, 0, 0)
                elif 'knee' in low or 'shin' in low or 'foot' in low:
                    rot[b_name] = (-max(0.0, math.sin((p + phase_offset) * sign)) * math.radians(35.0), 0, 0)
                elif 'arm' in low or 'blade' in low:
                    rot[b_name] = (0, math.sin(p) * math.radians(12.0) * sign, 0)
                elif 'tail' in low:
                    rot[b_name] = (0, math.sin(p) * math.radians(12.0), 0)
                elif 'body' in low:
                    rot[b_name] = (math.sin(p * 2.0) * math.radians(3.0), 0, 0)

        time_sec = t * dur
        frames.extend([time_sec, 0])
        for b_idx, b_name in enumerate(names):
            rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
            qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
            if f_idx == 0 and b_idx == 0:
                px, py, pz = 0.0, 0.0, 0.0
                qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
            else:
                px, py, pz = pos[b_name]
            frames.extend([px, py, pz, qw, qx, qy, qz])

    save_sca_file(walk_path, num_frames, dur, names, parents, frames)

    # Death collapse animation
    d_frames = 12
    d_dur = 0.5
    dframes = []
    for f_idx in range(d_frames):
        t = f_idx / d_frames
        rot = {}
        pos = {p_node.name: p_node.local_pos for p_node in pieces}
        for b_name in names:
            if 'body' in b_name.lower() or 'base' in b_name.lower():
                rot[b_name] = (math.radians(-25.0) * t, 0, 0)
        time_sec = t * d_dur
        dframes.extend([time_sec, 0])
        for b_idx, b_name in enumerate(names):
            rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
            qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
            if f_idx == 0 and b_idx == 0:
                px, py, pz = 0.0, 0.0, 0.0
                qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
            else:
                px, py, pz = pos[b_name]
            dframes.extend([px, py, pz, qw, qx, qy, qz])

    save_sca_file(death_path, d_frames, d_dur, names, parents, dframes)

# ---------------------------------------------------------------------------
# Zero-K Unit Definitions to Import
# ---------------------------------------------------------------------------
MODELS_TO_IMPORT = [
    {
        "id": "XRA0116",
        "zk_name": "chicken_digger",
        "name": "Subterranean Digger",
        "desc": "High-Speed Burrowing Raider & Scout",
        "tech": "T1", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/chicken_digger.s3o",
        "tex": "unittextures/brownchicken_team.dds",
        "icon": "unitpics/chicken_digger.png",
        "scale": 0.08, "hp": 260, "regen": 2.0, "speed": 4.6,
        "mass": 55, "energy": 450, "buildtime": 180,
        "size_x": 0.8, "size_y": 0.7, "size_z": 0.9,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "TECH1", "BUILTBYRAPTORHIVE", "RAPTOR", "AMPHIBIOUS"],
        "abilities": ["Amphibious", "High-Speed Burrower", "Regenerates (+2 hp/s)"],
        "weapons": [{
            "name": "Serrated Mandible Claws",
            "damage": 35, "rof": 1.2, "range": 14, "target": "LAND"
        }]
    },
    {
        "id": "XRA0121",
        "zk_name": "chickend",
        "name": "Chitin Spore Tube",
        "desc": "Biological Creep Defense Tube",
        "tech": "T1", "type": "DEFENSE", "motion": "RULEUMT_None",
        "s3o": "objects3d/tube.s3o",
        "tex": "unittextures/meat.dds",
        "icon": "unitpics/chickend.png",
        "scale": 0.065, "hp": 750, "regen": 3.0, "speed": 0,
        "mass": 110, "energy": 800, "buildtime": 320,
        "size_x": 1.2, "size_y": 2.8, "size_z": 1.2,
        "categories": ["STRUCTURE", "DEFENSE", "DIRECTFIRE", "ANTIAIR", "TECH1", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Creep Defense Tube", "Bio-Spore Dart Launcher", "Regenerates (+3 hp/s)"],
        "weapons": [{
            "name": "Bio-Spore Dart",
            "damage": 45, "rof": 1.5, "range": 26, "target": "BOTH"
        }]
    },
    {
        "id": "XRA0225",
        "zk_name": "chicken_shield",
        "name": "Bio-Shield Beetle",
        "desc": "Mobile Bio-Carapace Shield Generator & AA",
        "tech": "T2", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/chicken_shield.s3o",
        "tex": "unittextures/whitechicken.dds",
        "icon": "unitpics/chicken_shield.png",
        "scale": 0.065, "hp": 1650, "regen": 3.0, "speed": 3.2,
        "mass": 420, "energy": 5500, "buildtime": 1200,
        "size_x": 1.8, "size_y": 1.4, "size_z": 1.9,
        "categories": ["LAND", "MOBILE", "DEFENSE", "SHIELD", "TECH2", "BUILTBYRAPTORHIVE", "RAPTOR", "AMPHIBIOUS"],
        "abilities": ["Mobile Bio-Carapace Shield (2,800 HP)", "Anti-Air Aero Spores", "Amphibious"],
        "has_shield": True, "shield_hp": 2800, "shield_size": 18,
        "weapons": [{
            "name": "Aero-Spore Flak",
            "damage": 55, "rof": 2.0, "range": 32, "target": "AIR"
        }]
    },
    {
        "id": "XRA0226",
        "zk_name": "chicken_rafflesia",
        "name": "Rafflesia Shield Bloom",
        "desc": "Static Bio-Shield Canopy Generator",
        "tech": "T2", "type": "DEFENSE", "motion": "RULEUMT_None",
        "s3o": "objects3d/chicken_rafflesia.s3o",
        "tex": "unittextures/chicken_rafflesia_1.dds",
        "icon": "unitpics/chicken_rafflesia.png",
        "scale": 0.12, "hp": 2200, "regen": 5.0, "speed": 0,
        "mass": 650, "energy": 8000, "buildtime": 1600,
        "size_x": 2.2, "size_y": 1.8, "size_z": 2.2,
        "categories": ["STRUCTURE", "DEFENSE", "SHIELD", "TECH2", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Bio-Shield Canopy Dome (7,500 HP)", "Nest Protection", "Regenerates (+5 hp/s)"],
        "has_shield": True, "shield_hp": 7500, "shield_size": 32,
        "weapons": []
    },
    {
        "id": "XRA0227",
        "zk_name": "chicken_blimpy",
        "name": "Bio-Zeppelin Blimpy",
        "desc": "Aerial Living Brood Carrier & Dodo Bomber",
        "tech": "T2", "type": "AIR", "motion": "RULEUMT_Air",
        "s3o": "objects3d/chicken_blimpy.s3o",
        "tex": "unittextures/pinkchicken.dds",
        "icon": "unitpics/chicken_blimpy.png",
        "scale": 0.075, "hp": 1850, "regen": 2.5, "speed": 11.5,
        "mass": 480, "energy": 9000, "buildtime": 1800,
        "size_x": 1.8, "size_y": 1.5, "size_z": 2.4,
        "categories": ["AIR", "MOBILE", "BOMBER", "HIGHPRIAIR", "TECH2", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Air Bio-Zeppelin", "Living Brood Bomb Salvos", "Regenerates (+2.5 hp/s)"],
        "is_flying": True,
        "weapons": [{
            "name": "Living Brood Egg Drop",
            "damage": 220, "rof": 0.25, "range": 45, "target": "LAND"
        }]
    },
    {
        "id": "XRA0328",
        "zk_name": "chicken_tiamat",
        "name": "Tiamat Bio-Juggernaut",
        "desc": "Heavy Armored Assault Bruiser & Riot Walker",
        "tech": "T3", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/chickenbroodqueen.s3o",
        "tex": "unittextures/whitechicken_team.dds",
        "icon": "unitpics/chicken_tiamat.png",
        "scale": 0.08, "hp": 6800, "regen": 8.0, "speed": 3.0,
        "mass": 1600, "energy": 26000, "buildtime": 4200,
        "size_x": 2.4, "size_y": 2.2, "size_z": 2.8,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "TECH3", "BUILTBYRAPTORHIVE", "RAPTOR", "AMPHIBIOUS"],
        "abilities": ["Amphibious", "Personal Carapace Shield (4,500 HP)", "Bio-Flamethrower", "Regenerates (+8 hp/s)"],
        "has_shield": True, "shield_hp": 4500, "shield_size": 5,
        "weapons": [
            {
                "name": "Heavy Scythe Cleavers",
                "damage": 380, "rof": 1.0, "range": 18, "target": "LAND"
            },
            {
                "name": "Thermal Bio-Flamethrower",
                "damage": 120, "rof": 3.0, "range": 22, "target": "LAND"
            }
        ]
    },
    {
        "id": "XRA0329",
        "zk_name": "chicken_dragon",
        "name": "Apex White Dragon Herald",
        "desc": "Prime Assault Titan & Mid-Game Herald",
        "tech": "T3", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/chicken_dragon.s3o",
        "tex": "unittextures/bluechicken.dds",
        "icon": "unitpics/chicken_dragon.png",
        "scale": 0.075, "hp": 28000, "regen": 18.0, "speed": 2.8,
        "mass": 6200, "energy": 95000, "buildtime": 12000,
        "size_x": 3.6, "size_y": 3.2, "size_z": 4.2,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "EXPERIMENTAL", "TECH3", "BUILTBYRAPTORHIVE", "RAPTOR", "AMPHIBIOUS"],
        "abilities": ["Amphibious", "Apex Herald Titan", "Multi-Vector Plasma Blob", "Tracking Spore Swarm", "Regenerates (+18 hp/s)"],
        "weapons": [
            {
                "name": "Titanic Dragon Cleave",
                "damage": 750, "rof": 1.0, "range": 22, "target": "LAND"
            },
            {
                "name": "Volcanic Magma Goo",
                "damage": 320, "rof": 0.6, "range": 38, "target": "LAND"
            },
            {
                "name": "Apex Dragon Spores",
                "damage": 60, "rof": 2.5, "range": 42, "target": "BOTH"
            }
        ]
    }
]

# ---------------------------------------------------------------------------
# Execution Pipeline
# ---------------------------------------------------------------------------
def run_import():
    print(f"Opening Zero-K archive: {ZK_PATH}")
    assert os.path.exists(ZK_PATH), f"Zero-K archive not found at {ZK_PATH}"

    with zipfile.ZipFile(ZK_PATH, 'r') as zk:
        namelist = set(zk.namelist())

        for u in MODELS_TO_IMPORT:
            uid = u["id"]
            u_dir = os.path.join(UNITS_ROOT, uid)
            os.makedirs(u_dir, exist_ok=True)
            print(f"\n==================================================")
            print(f"IMPORTING [{uid}] {u['name']} (from {u['zk_name']})")
            print(f"==================================================")

            # 1. S3O -> SCM Conversion
            s3o_path = u["s3o"]
            assert s3o_path in namelist, f"S3O {s3o_path} not found in Zero-K archive!"
            s3o_bytes = zk.read(s3o_path)
            scm_path = os.path.join(u_dir, f"{uid}_lod0.scm")
            pieces = convert_s3o_to_scm(s3o_bytes, scm_path, scale=u["scale"])

            # 2. Textures Extraction & Setup
            # Albedo
            albedo_path = os.path.join(u_dir, f"{uid}_Albedo.dds")
            tex_path = u["tex"]
            if tex_path in namelist:
                tex_bytes = zk.read(tex_path)
                try:
                    im = Image.open(io.BytesIO(tex_bytes))
                    im.save(albedo_path, format="DDS")
                    print(f"Extracted Albedo texture: {tex_path} -> {os.path.basename(albedo_path)}")
                except Exception as e:
                    print(f"Warning converting texture {tex_path} with Pillow ({e}), writing raw bytes")
                    with open(albedo_path, "wb") as f_tex:
                        f_tex.write(tex_bytes)
            else:
                shutil.copyfile(os.path.join(REF_XRA0101, "XRA0101_Albedo.dds"), albedo_path)
                print("Copied fallback Albedo texture")

            # Normals & SpecTeam
            shutil.copyfile(REF_NORMALS, os.path.join(u_dir, f"{uid}_NormalsTS.dds"))
            shutil.copyfile(REF_SPECTEAM, os.path.join(u_dir, f"{uid}_SpecTeam.dds"))

            # Icon
            icon_path = os.path.join(u_dir, f"{uid}_icon.dds")
            zk_icon_path = u["icon"]
            if zk_icon_path in namelist:
                icon_bytes = zk.read(zk_icon_path)
                try:
                    im_icon = Image.open(io.BytesIO(icon_bytes)).convert("RGBA")
                    im_icon = im_icon.resize((128, 128), Image.Resampling.LANCZOS)
                    im_icon.save(icon_path, format="DDS")
                    shutil.copyfile(icon_path, os.path.join(ICONS_DIR, f"{uid}_icon.dds"))
                    print(f"Generated icon: {os.path.basename(icon_path)}")
                except Exception as e:
                    print(f"Icon conversion error: {e}, falling back to reference icon")
                    shutil.copyfile(REF_ICON, icon_path)
                    shutil.copyfile(REF_ICON, os.path.join(ICONS_DIR, f"{uid}_icon.dds"))
            else:
                shutil.copyfile(REF_ICON, icon_path)
                shutil.copyfile(REF_ICON, os.path.join(ICONS_DIR, f"{uid}_icon.dds"))

            # 3. Procedural SCA Animations
            is_flying = u.get("is_flying", False)
            motion_cat = "AIR" if is_flying else ("STRUCTURE" if u["type"] in ("DEFENSE", "STRUCTURE") else "LAND")
            anim_walk_name = f"{uid}_Afly.sca" if is_flying else f"{uid}_Awalk.sca"
            anim_death_name = f"{uid}_Adeath01.sca"
            anim_walk_path = os.path.join(u_dir, anim_walk_name)
            anim_death_path = os.path.join(u_dir, anim_death_name)
            generate_procedural_anims(pieces, anim_walk_path, anim_death_path, motion_type=motion_cat)
            print(f"Generated animations: {anim_walk_name}, {anim_death_name}")

            # 4. Blueprint Generation
            is_structure = u["type"] in ("DEFENSE", "STRUCTURE")
            piece_names = [p.name for p in pieces]

            # Choose best weapon bones
            muzzle_candidate = pieces[0].name
            for cand in ['firepoint', 'dodobomb', 'head', 'center']:
                if cand in piece_names:
                    muzzle_candidate = cand
                    break

            if is_structure:
                pitch_candidate = 'body' if 'body' in piece_names else pieces[0].name
                yaw_candidate = pitch_candidate
            else:
                pitch_candidate = 'head' if 'head' in piece_names else pieces[0].name
                yaw_candidate = pitch_candidate

            weapons_bp_list = []
            for widx, w in enumerate(u.get("weapons", [])):
                w_name = w["name"]
                w_dmg = w["damage"]
                w_rof = w["rof"]
                w_range = w["range"]
                target_type = w.get("target", "LAND")
                if target_type == "AIR":
                    target_caps = "Air = 'Air', Land = 'Air'"
                    rcat = "UWRC_AntiAir"
                elif target_type == "BOTH":
                    target_caps = "Air = 'Air|Land', Land = 'Air|Land', Water = 'Air|Land'"
                    rcat = "UWRC_DirectFire"
                else:
                    target_caps = "Air = 'Land|Water', Land = 'Land|Water', Water = 'Land|Water'"
                    rcat = "UWRC_DirectFire"

                w_low = w_name.lower()
                if "spore" in w_low:
                    proj_id = "/mods/RaptorFaction/projectiles/XRA_Spore01/XRA_Spore01_proj.bp"
                    w_bank = "Raptor_Spores"
                elif "bomb" in w_low or "egg" in w_low:
                    proj_id = "/mods/RaptorFaction/projectiles/XRA_DodoBomb01/XRA_DodoBomb01_proj.bp"
                    w_bank = "Raptor_Bio_Bomb"
                elif "flame" in w_low or "pyro" in w_low:
                    proj_id = "/mods/RaptorFaction/projectiles/XRA_PyroStream01/XRA_PyroStream01_proj.bp"
                    w_bank = "Raptor_Flamer"
                elif "dragon" in w_low or "plasma" in w_low:
                    proj_id = "/mods/RaptorFaction/projectiles/XRA_QueenPlasma01/XRA_QueenPlasma01_proj.bp"
                    w_bank = "Raptor_Queen_Roar"
                else:
                    proj_id = "/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp"
                    w_bank = "Raptor_Turret_Attack" if is_structure else "Raptor_Attack"

                if uid == "XRA0227" and widx == 0:
                    weapons_bp_list.append(f"""        {{
            AboveWaterTargetsOnly = true,
            Audio = {{
                Fire = Sound {{
                    Bank = 'Raptor_Bio_Bomb',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                }},
            }},
            AutoInitiateAttackCommand = true,
            BallisticArc = 'RULEUBA_None',
            BombDropThreshold = 3.5,
            CollideFriendly = false,
            Damage = {w_dmg},
            DamageRadius = 3.5,
            DamageType = 'Normal',
            DisplayName = '{w_name}',
            FireTargetLayerCapsTable = {{
                Air = 'Land|Water|Seabed',
                Land = 'Land|Water|Seabed',
            }},
            FiringRandomness = 0.05,
            FiringTolerance = 6,
            FixBombTrajectory = true,
            Label = 'Bomb',
            MaxRadius = {w_range},
            MinRadius = 0,
            MuzzleSalvoDelay = 0.2,
            MuzzleSalvoSize = 2,
            MuzzleVelocity = 0,
            NeedToComputeBombDrop = true,
            ProjectileId = '{proj_id}',
            ProjectilesPerOnFire = 2,
            RackBones = {{
                {{
                    MuzzleBones = {{
                        '{muzzle_candidate}',
                    }},
                    RackBone = '{muzzle_candidate}',
                }},
            }},
            RackFireTogether = false,
            RackRecoilDistance = 0,
            RackReloadTimeout = 10,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RackSlavedToTurret = false,
            RangeCategory = 'UWRC_IndirectFire',
            RateOfFire = {w_rof},
            TargetCheckInterval = 1,
            TargetPriorities = {{
                'SPECIALHIGHPRI',
                'STRUCTURE DEFENSE',
                'TECH3 MOBILE',
                'TECH2 MOBILE',
                'ALLUNITS',
            }},
            TargetRestrictDisallow = 'UNTARGETABLE',
            TrackingRadius = 1.25,
            TurretDualManipulators = false,
            Turreted = false,
            WeaponCategory = 'Bomb',
        }},""")
                    continue

                w_label = f"Weapon{widx+1}"

                weapons_bp_list.append(f"""        {{
            AboveWaterTargetsOnly = true,
            Audio = {{
                Fire = Sound {{
                    Bank = '{w_bank}',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                }},
            }},
            BallisticArc = 'RULEUBA_LowArc',
            CollideFriendly = false,
            Damage = {w_dmg},
            DamageRadius = 1.0,
            DamageType = 'Normal',
            DisplayName = '{w_name}',
            FireTargetLayerCapsTable = {{
                {target_caps}
            }},
            FiringTolerance = 2,
            Label = '{w_label}',
            MaxRadius = {w_range},
            MuzzleSalvoDelay = 0.1,
            MuzzleSalvoSize = 1,
            MuzzleVelocity = 35,
            ProjectileId = '{proj_id}',
            ProjectileLifetimeUsesMultiplier = 1.15,
            ProjectilesPerOnFire = 1,
            RackBones = {{
                {{
                    MuzzleBones = {{
                        '{muzzle_candidate}',
                    }},
                    RackBone = '{muzzle_candidate}',
                }},
            }},
            RackFireTogether = false,
            RackRecoilDistance = 0,
            RackReloadTimeout = 10,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RackSlavedToTurret = false,
            RangeCategory = '{rcat}',
            RateOfFire = {w_rof},
            TargetCheckInterval = 0.3,
            TargetPriorities = {{
                'COMMAND',
                'EXPERIMENTAL',
                'TECH3',
                'TECH2',
                'TECH1',
                'ALLUNITS',
            }},
            TargetRestrictDisallow = 'UNTARGETABLE',
            TrackingRadius = 1.4 if uid == 'XRA0121' else 1.15,
            TurretBoneMuzzle = '{muzzle_candidate}',
            TurretDualManipulators = false,
            TurretPitch = 0,
            TurretPitchRange = 0 if uid == 'XRA0121' else 45,
            TurretPitchSpeed = 0 if uid == 'XRA0121' else 60,
            TurretYaw = 0,
            TurretYawRange = 0 if uid == 'XRA0121' else 180,
            TurretYawSpeed = 0 if uid == 'XRA0121' else 90,
            Turreted = False if uid == 'XRA0121' else True,
            WeaponCategory = 'Direct Fire',
        }},""")

            weapons_str = "\n".join(weapons_bp_list)

            # Shield block if applicable
            shield_bp_str = ""
            if u.get("has_shield"):
                s_hp = u["shield_hp"]
                s_sz = u["shield_size"]
                shield_bp_str = f"""        Shield = {{
            ImpactEffects = 'CybranShieldHit01',
            ImpactMesh = '/effects/entities/ShieldSection01/ShieldSection01_mesh',
            Mesh = '/effects/entities/CybranShield01/CybranShield01_mesh',
            MeshZMult = 1,
            RegenAssistMult = 60,
            ShieldEnergyDrainRechargeTime = 5,
            ShieldMaxHealth = {s_hp},
            ShieldRechargeTime = 24,
            ShieldRegenRate = {int(s_hp / 30)},
            ShieldRegenStartTime = 3,
            ShieldSize = {s_sz},
            ShieldVerticalOffset = 0,
        }},"""

            # Categories string with required engine recon/selection flags
            unit_cats = list(u["categories"])
            for req in ['PRODUCTSC1', 'SELECTABLE', 'VISIBLETORECON', 'RECLAIMABLE']:
                if req not in unit_cats:
                    unit_cats.insert(0, req)
            if is_structure and 'SORTDEFENSE' not in unit_cats and 'DEFENSE' in unit_cats:
                unit_cats.append('SORTDEFENSE')
            if 'DIRECTFIRE' in unit_cats and 'OVERLAYDIRECTFIRE' not in unit_cats:
                unit_cats.append('OVERLAYDIRECTFIRE')
            if 'ANTIAIR' in unit_cats and 'OVERLAYANTIAIR' not in unit_cats:
                unit_cats.append('OVERLAYANTIAIR')
            cats_str = ",\n        ".join(f"'{c}'" for c in unit_cats)
            abilities_str = ",\n        ".join(f"'<LOC>{a}'" for a in u["abilities"])

            # Strategic icon
            if uid == "XRA0121":
                strat_icon = 'icon_structure1_directfire'
            elif uid == "XRA0226":
                strat_icon = 'icon_structure2_shield'
            elif uid == "XRA0225":
                strat_icon = 'icon_bot2_shield'
            elif uid == "XRA0227":
                strat_icon = 'icon_bomber2_directfire'
            elif uid == "XRA0328":
                strat_icon = 'icon_bot3_directfire'
            elif uid == "XRA0329":
                strat_icon = 'icon_experimental_generic'
            else:
                strat_icon = f'icon_bot{"2" if u["tech"] == "T2" else ("3" if u["tech"] == "T3" else "1")}_directfire'

            strat_priority = 205 if is_structure else (110 if u["tech"] == "T3" else 115)
            death_audio_bank = 'Raptor_Flyer_Death' if is_flying else ('Raptor_Roost_Death' if is_structure else 'Raptor_Death')

            # Display animations: only walking units have AnimationWalk
            if is_structure:
                walk_anim_bp = ""
            else:
                walk_anim_bp = f"""        AnimationWalk = '/mods/RaptorFaction/units/{uid}/{anim_walk_name}',
        AnimationWalkRate = 1.2,"""

            # Physics table
            if is_structure:
                physics_bp = f"""    Physics = {{
        BankingSlope = 0,
        BuildOnLayerCaps = {{
            LAYER_Air = false,
            LAYER_Land = true,
            LAYER_Orbit = false,
            LAYER_Seabed = true,
            LAYER_Sub = false,
            LAYER_Water = false,
        }},
        DragCoefficient = 0.2,
        FlattenSkirt = true,
        MaxSteerForce = 0,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_None',
        OccupyGround = true,
        SkirtOffsetX = 0,
        SkirtOffsetZ = 0,
        SkirtSizeX = 1,
        SkirtSizeZ = 1,
        TurnRate = 0,
    }},"""
            else:
                elevation_str = "Elevation = 14.0," if is_flying else ""
                air_bp = f"""    Air = {{
        AutoLandTime = 0,
        BankFactor = 1.5,
        BankForward = false,
        BreakOffDistance = 32,
        BreakOffIfNearNewTarget = true,
        BreakOffTrigger = 20,
        CanFly = true,
        CombatTurnSpeed = 1.2,
        EngageDistance = 45,
        KLift = 2,
        KLiftDamping = 2.5,
        KMove = 1,
        KMoveDamping = 2,
        KRoll = 1,
        KRollDamping = 1.5,
        KTurn = 0.7,
        KTurnDamping = 1,
        LiftFactor = 8,
        MaxAirspeed = {u['speed']},
        MinAirspeed = {u['speed']},
        PredictAheadForBombDrop = 3,
        RandomBreakOffDistanceMult = 1.5,
        StartTurnDistance = 1.5,
        TightTurnMultiplier = 0,
        TurnSpeed = 1.2,
        Winged = true,
    }},
""" if is_flying else ""
                physics_bp = f"""    Physics = {{
        BackUpDistance = 4,
        BankingSlope = 0.5,
        BuildOnLayerCaps = {{
            LAYER_Air = {"true" if is_flying else "false"},
            LAYER_Land = {"false" if is_flying else "true"},
            LAYER_Orbit = false,
            LAYER_Seabed = {"false" if is_flying else "true"},
            LAYER_Sub = false,
            LAYER_Water = false,
        }},
        DragCoefficient = 0.2,
        {elevation_str}
        MaxAcceleration = {u["speed"] * 0.8:.1f},
        MaxBrake = {u["speed"] * 1.2:.1f},
        MaxSpeed = 0.5 if is_flying else {u["speed"]},
        MaxSpeedReverse = 0,
        MaxSteerForce = 10,
        MinSpeedPercent = 0,
        MotionType = '{u["motion"]}',
        TurnRadius = 5,
        TurnRate = 75,
    }},"""

            bp_content = f"""UnitBlueprint {{
{air_bp}    Audio = {{
        AmbientMove = Sound {{
            Bank = 'XRA_Units',
            Cue = 'Raptor_Ambient',
            LodCutoff = 'UnitMove_LodCutoff',
        }},
        Destroyed = Sound {{
            Bank = '{death_audio_bank}',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        }},
    }},
    Categories = {{
        {cats_str},
    }},
    Defense = {{
        ArmorType = 'Normal',
        Health = {u["hp"]},
        MaxHealth = {u["hp"]},
        RegenRate = {u["regen"]},
{shield_bp_str}
    }},
    Description = '<LOC {uid.lower()}_desc>{u["desc"]}',
    Display = {{
        Abilities = {{
            {abilities_str},
        }},
        AnimationDeath = {{
            {{
                Animation = '/mods/RaptorFaction/units/{uid}/{anim_death_name}',
                AnimationRateLifetime = 1.0,
                Weight = 100,
            }},
        }},
{walk_anim_bp}
        Mesh = {{
            IconFadeInZoom = 130,
            LODs = {{
                {{
                    AlbedoName = '/mods/RaptorFaction/units/{uid}/{uid}_Albedo.dds',
                    LODCutoff = 215,
                    MeshName = '/mods/RaptorFaction/units/{uid}/{uid}_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/{uid}/{uid}_NormalsTS.dds',
                    ShaderName = 'Insect',
                    SpecularName = '/mods/RaptorFaction/units/{uid}/{uid}_SpecTeam.dds',
                }},
            }},
        }},
        UniformScale = 1.0,
    }},
    Economy = {{
        BuildCostEnergy = {u["energy"]},
        BuildCostMass = {u["mass"]},
        BuildTime = {u["buildtime"]},
    }},
    General = {{
        Category = '{"Air" if is_flying else ("Defense" if is_structure else "Direct Fire")}',
        Classification = '{"RULEUC_Weapon" if is_structure else "RULEUC_MilitaryVehicle"}',
        CommandCaps = {{
            RULEUCC_Attack = true,
            RULEUCC_CallTransport = false,
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
        }},
        FactionName = 'Raptor',
        Icon = '{"air" if is_flying else ("amph" if "AMPHIBIOUS" in u["categories"] else "land")}',
        TechLevel = 'RULEUTL_{"Secret" if u["tech"] == "T3" else ("Advanced" if u["tech"] == "T2" else "Basic")}',
        UnitName = '<LOC {uid.lower()}_name>{u["name"]}',
        UnitWeight = 1,
    }},
    Intel = {{
        VisionRadius = 24,
    }},
    Interface = {{
        HelpText = '<LOC {uid.lower()}_help>{u["desc"]}',
    }},
    LifeBarHeight = 0.08,
    LifeBarOffset = 0.45,
    LifeBarSize = 1.0,
{physics_bp}
    SelectionSizeX = {u["size_x"]},
    SelectionSizeZ = {u["size_z"]},
    SelectionThickness = 0.5,
    SizeX = {u["size_x"]},
    SizeY = {u["size_y"]},
    SizeZ = {u["size_z"]},
    StrategicIconName = '{strat_icon}',
    StrategicIconSortPriority = {strat_priority},
    Weapon = {{
{weapons_str}
    }},
}}
"""
            bp_file = os.path.join(u_dir, f"{uid}_unit.bp")
            with open(bp_file, "w", encoding="utf-8") as f_bp:
                f_bp.write(bp_content)
            print(f"Created blueprint: {os.path.basename(bp_file)}")

            # 5. Unit Script Generation (only if not already customized!)
            script_file = os.path.join(u_dir, f"{uid}_script.lua")
            if not os.path.exists(script_file):
                base_class = "CAirUnit" if is_flying else ("CStructureUnit" if is_structure else "CWalkingLandUnit")
                module_import = "/lua/cybranunits.lua"

                script_content = f"""local {base_class} = import('{module_import}').{base_class}
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon
local EffectTemplate = import('/lua/EffectTemplates.lua')
local Eggs = import('/mods/RaptorFaction/lua/RaptorEggs.lua')

---@class RaptorWeapon : DefaultProjectileWeapon
local RaptorWeapon = ClassWeapon(DefaultProjectileWeapon) {{
    FxMuzzleFlash = EffectTemplate.PhasicAutoGunMuzzleFlash,
}}

---@class {uid} : {base_class}
{uid} = ClassUnit({base_class}) {{
    Weapons = {{
        Weapon1 = ClassWeapon(RaptorWeapon) {{}},
        Weapon2 = ClassWeapon(RaptorWeapon) {{}},
        Weapon3 = ClassWeapon(RaptorWeapon) {{}},
    }},

    CreateWreckage = function(self, overkillRatio)
        Eggs.SpawnRaptorEgg(self)
        return nil
    end,
}}

TypeClass = {uid}
"""
                with open(script_file, "w", encoding="utf-8") as f_sc:
                    f_sc.write(script_content)
                print(f"Created script: {os.path.basename(script_file)}")
            else:
                print(f"Preserved existing custom script: {os.path.basename(script_file)}")

    print("\nAll 7 Zero-K models imported successfully!")

if __name__ == "__main__":
    run_import()
