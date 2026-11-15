import os
import gzip
import struct
import math
import shutil
from scm_io import pad, pad_file, write_scm

# ---------------------------------------------------------------------------
# Setup & Directory Paths
# ---------------------------------------------------------------------------
mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
icons_dir = os.path.join(mod_dir, "icons", "units")
units_root = os.path.join(mod_dir, "units")
proj_root = os.path.join(mod_dir, "projectiles")
sounds_dir = os.path.join(mod_dir, "sounds")

pkg_path = r'P:\Games\Beyond-All-Reason\data\packages\44fd01f1d430f1c94f27b75b242738df.sdp'
with gzip.open(pkg_path, 'rb') as gz:
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
    def parse_piece_tree(offset, parent_idx=-1):
        name_off, n_child, child_off, n_verts, v_off, v_type, prim_type, idx_cnt, idx_off, col_data, ox, oy, oz = struct.unpack('<10I3f', s3o_bytes[offset:offset+52])
        name = s3o_bytes[name_off:].split(b'\x00')[0].decode('latin1')
        curr_idx = len(pieces)
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
            raw_indices = struct.unpack(f'<{idx_cnt}I', idx_data)
            node.indices = list(raw_indices)
        if n_child > 0 and child_off > 0:
            child_offsets = struct.unpack(f'<{n_child}I', s3o_bytes[child_off : child_off + 4*n_child])
            for co in child_offsets:
                parse_piece_tree(co, curr_idx)

    parse_piece_tree(52)

    total_bone_data = []
    bone_name_data = []
    for p in pieces:
        bone_name_data.append(bytearray(p.name.encode('ascii')))

    bone_name_offset = 48 + pad(48)
    current_name_off = bone_name_offset

    for p in pieces:
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
    print(f"Created SCM: {os.path.basename(scm_filepath)} ({len(pieces)} bones, {vert_counter} verts)")
    return pieces

# ---------------------------------------------------------------------------
# Procedural SCA Generator
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

def generate_procedural_anims(pieces, walk_path, death_path, is_flying=False):
    names = [p.name for p in pieces]
    parents = [p.parent_idx for p in pieces]
    num_frames = 20
    dur = 0.6 if not is_flying else 0.8
    frames = []

    for f_idx in range(num_frames):
        t = f_idx / num_frames
        p = t * 2.0 * math.pi
        rot = {}
        pos = {p_node.name: p_node.local_pos for p_node in pieces}

        if is_flying:
            for b_name in names:
                if 'wing' in b_name.lower():
                    sign = 1.0 if 'l' in b_name.lower() or 'li' in b_name.lower() else -1.0
                    rot[b_name] = (0, 0, math.sin(p) * math.radians(28.0) * sign)
                elif 'tail' in b_name.lower():
                    rot[b_name] = (0, math.sin(p) * math.radians(10.0), 0)
                elif 'body' in b_name.lower():
                    rot[b_name] = (math.sin(p) * math.radians(4.0), 0, 0)
        else:
            for b_name in names:
                low = b_name.lower()
                if 'leg' in low or 'thigh' in low or 'upperleg' in low:
                    sign = 1.0 if 'l' in low else -1.0
                    rot[b_name] = (math.sin(p) * math.radians(35.0) * sign, 0, 0)
                elif 'knee' in low or 'shin' in low or 'foot' in low or 'forearm' in low:
                    sign = 1.0 if 'l' in low else -1.0
                    rot[b_name] = (-max(0.0, math.sin(p * sign)) * math.radians(40.0), 0, 0)
                elif 'body' in low or 'torso' in low:
                    rot[b_name] = (math.sin(p * 2.0) * math.radians(4.0), 0, 0)

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
            if 'body' in b_name.lower() or 'torso' in b_name.lower():
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

print("SCM & SCA generators initialized.")

# ---------------------------------------------------------------------------
# Unit Definitions: 25 Subtypes & Variants
# ---------------------------------------------------------------------------
NEW_UNITS = [
    # --- AIR UNITS ---
    {
        "id": "XRA0213",
        "name": "Bio-Dive Kamikaze Tick",
        "desc": "Air Dive-Bomb Suicide Tick",
        "tech": "T2", "type": "AIR", "motion": "RULEUMT_Air",
        "s3o": "objects3d/raptors/raptor_dodo_air.s3o",
        "tex": "unittextures/chicken_red_s_color.dds",
        "scale": 0.055, "hp": 480, "regen": 1.0, "speed": 15.0,
        "mass": 140, "energy": 2800, "buildtime": 750,
        "shared_sca": None, "is_flying": True,
        "is_kamikaze": True, "kamikaze_dmg": 1400, "kamikaze_radius": 3.5,
        "categories": ["AIR", "MOBILE", "HIGHPRIAIR", "KAMIKAZE", "TECH2", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Amphibious", "Kamikaze Detonation (1,400 DMG)", "High-Speed Aerial Dive"]
    },
    {
        "id": "XRA0314",
        "name": "Apex Air Crow",
        "desc": "Heavy Air Superiority Raptor",
        "tech": "T3", "type": "AIR", "motion": "RULEUMT_Air",
        "s3o": "objects3d/raptors/raptor_crow.s3o",
        "tex": "unittextures/chicken_vcrimson_m_color.dds",
        "scale": 0.065, "hp": 1850, "regen": 3.0, "speed": 22.0,
        "mass": 650, "energy": 14000, "buildtime": 2400,
        "shared_sca": None, "is_flying": True,
        "categories": ["AIR", "MOBILE", "ANTIAIR", "HIGHPRIAIR", "TECH3", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Air Superiority Fighter", "Tracking Bio-Spore Volleys", "Regenerates (+3 hp/s)"],
        "weapons": [{
            "name": "Apex Spore Interceptor",
            "type": "Spore", "damage": 70, "rof": 3.0, "salvo": 2, "range": 36,
            "target": "AIR", "proj": "/mods/RaptorFaction/projectiles/XRA_Spore01/XRA_Spore01_proj.bp"
        }]
    },
    {
        "id": "XRA0215",
        "name": "Bio-Healer Drone",
        "desc": "Aerial Bio-Repair & Regen Drone",
        "tech": "T2", "type": "AIR", "motion": "RULEUMT_Air",
        "s3o": "objects3d/raptors/raptor_droneb.s3o",
        "tex": "unittextures/chicken_whitehc_s_color.dds",
        "scale": 0.06, "hp": 750, "regen": 4.0, "speed": 10.0,
        "mass": 280, "energy": 4500, "buildtime": 1100,
        "shared_sca": None, "is_flying": True, "is_healer": True,
        "categories": ["AIR", "MOBILE", "REPAIR", "ENGINEER", "TECH2", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Aerial Bio-Repair Beam", "Biological Regen Aura (+30 hp/s)", "Regenerates (+4 hp/s)"]
    },
    {
        "id": "XRA0216",
        "name": "Corrosive Acid Gunship",
        "desc": "Heavy Corrosive Acid Gunship",
        "tech": "T2", "type": "AIR", "motion": "RULEUMT_Air",
        "s3o": "objects3d/raptors/raptorf1.s3o",
        "tex": "unittextures/chicken_acidgreen_l_color.dds",
        "scale": 0.06, "hp": 1100, "regen": 2.0, "speed": 8.5,
        "mass": 320, "energy": 6000, "buildtime": 1400,
        "shared_sca": "XRA0205", "is_flying": True,
        "categories": ["AIR", "MOBILE", "GROUNDATTACK", "DIRECTFIRE", "TECH2", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Corrosive Bile Spit", "Shield Disruption", "Regenerates (+2 hp/s)"],
        "weapons": [{
            "name": "Acid Slime Mortar",
            "type": "Acid", "damage": 90, "rof": 1.0, "salvo": 2, "range": 24,
            "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_AcidSpike01/XRA_AcidSpike01_proj.bp"
        }]
    },
    {
        "id": "XRA0217",
        "name": "Bio-EMP Shock Gunship",
        "desc": "Paralyzer Lightning Gunship",
        "tech": "T2", "type": "AIR", "motion": "RULEUMT_Air",
        "s3o": "objects3d/raptors/raptorf1.s3o",
        "tex": "unittextures/chicken_electric_l_color.dds",
        "scale": 0.06, "hp": 1100, "regen": 2.0, "speed": 8.5,
        "mass": 320, "energy": 6500, "buildtime": 1400,
        "shared_sca": "XRA0205", "is_flying": True,
        "categories": ["AIR", "MOBILE", "GROUNDATTACK", "DIRECTFIRE", "TECH2", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Paralyzer Lightning Arc", "Disables Enemy Shields & Tech", "Regenerates (+2 hp/s)"],
        "weapons": [{
            "name": "Paralyzer Lightning Arc",
            "type": "EMP", "damage": 40, "rof": 4.0, "salvo": 1, "range": 22,
            "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp"
        }]
    },
    {
        "id": "XRA0218",
        "name": "Bio-Inferno Gunship",
        "desc": "Thermal Napalm Fire Gunship",
        "tech": "T2", "type": "AIR", "motion": "RULEUMT_Air",
        "s3o": "objects3d/raptors/raptorf1.s3o",
        "tex": "unittextures/chicken_black_l_color.dds",
        "scale": 0.06, "hp": 1200, "regen": 2.0, "speed": 8.5,
        "mass": 340, "energy": 6800, "buildtime": 1450,
        "shared_sca": "XRA0205", "is_flying": True,
        "categories": ["AIR", "MOBILE", "GROUNDATTACK", "DIRECTFIRE", "TECH2", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Thermal Napalm Flame Spray", "High AoE Cone", "Regenerates (+2 hp/s)"],
        "weapons": [{
            "name": "Bio Napalm Spray",
            "type": "Fire", "damage": 30, "rof": 8.0, "salvo": 1, "range": 18,
            "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_PyroStream01/XRA_PyroStream01_proj.bp"
        }]
    },
    {
        "id": "XRA0219",
        "name": "Bio-Spore AA Gunship",
        "desc": "Anti-Air Interceptor Gunship",
        "tech": "T2", "type": "AIR", "motion": "RULEUMT_Air",
        "s3o": "objects3d/raptors/raptorf1.s3o",
        "tex": "unittextures/chicken_red_l_color.dds",
        "scale": 0.06, "hp": 1050, "regen": 2.0, "speed": 11.0,
        "mass": 310, "energy": 5800, "buildtime": 1350,
        "shared_sca": "XRA0205", "is_flying": True,
        "categories": ["AIR", "MOBILE", "ANTIAIR", "TECH2", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Deadly Defensive Spores", "Anti-Air Tracking Pods", "Regenerates (+2 hp/s)"],
        "weapons": [{
            "name": "Deadly Defensive Spores",
            "type": "AA", "damage": 80, "rof": 2.0, "salvo": 2, "range": 36,
            "target": "AIR", "proj": "/mods/RaptorFaction/projectiles/XRA_Spore01/XRA_Spore01_proj.bp"
        }]
    },
    {
        "id": "XRA0224",
        "name": "Bio-EMP Disruption Bomber",
        "desc": "EMP Disruption Carpet Bomber",
        "tech": "T2", "type": "AIR", "motion": "RULEUMT_Air",
        "s3o": "objects3d/raptors/raptorebomber1.s3o",
        "tex": "unittextures/chicken_electric_l_color.dds",
        "scale": 0.06, "hp": 700, "regen": 1.5, "speed": 11.5,
        "mass": 260, "energy": 5500, "buildtime": 1200,
        "shared_sca": "XRA0104", "is_flying": True,
        "categories": ["AIR", "MOBILE", "BOMBER", "HIGHPRIAIR", "TECH2", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["EMP Shock Bombs", "Base Defense Paralyzer", "Regenerates (+1.5 hp/s)"],
        "weapons": [{
            "name": "Bio-EMP Shock Bomb",
            "type": "Bomb", "damage": 250, "rof": 0.25, "salvo": 3, "range": 45,
            "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_ElectroBomb01/XRA_ElectroBomb01_proj.bp"
        }]
    },

    # --- ARTILLERY & DODOS ---
    {
        "id": "XRA0222",
        "name": "Mobile Brood Mortar Bug",
        "desc": "Living Brood Artillery Bug",
        "tech": "T2", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptor_artillery_brood_small.s3o",
        "tex": "unittextures/chicken_blue_l_color.dds",
        "scale": 0.06, "hp": 750, "regen": 1.5, "speed": 2.8,
        "mass": 340, "energy": 3800, "buildtime": 1100,
        "shared_sca": "XRA0202", "is_flying": False,
        "categories": ["LAND", "MOBILE", "INDIRECTFIRE", "ARTILLERY", "ALLTERRAIN", "TECH2", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["All-Terrain", "Living Brood Shells (Spawns Larvae on impact)", "Regenerates (+1.5 hp/s)"],
        "weapons": [{
            "name": "Brood Egg Mortar",
            "type": "Brood", "damage": 50, "rof": 0.25, "salvo": 1, "range": 60,
            "min_range": 8, "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_BroodEggBomb01/XRA_BroodEggBomb01_proj.bp"
        }]
    },
    {
        "id": "XRA0322",
        "name": "Mobile EMP Bio-Artillery",
        "desc": "Heavy EMP Paralyzer Artillery",
        "tech": "T3", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptor_artillery_electric_v2.s3o",
        "tex": "unittextures/chicken_electric_l_color.dds",
        "scale": 0.07, "hp": 1600, "regen": 3.0, "speed": 2.4,
        "mass": 880, "energy": 12000, "buildtime": 2800,
        "shared_sca": "XRA0202", "is_flying": False,
        "categories": ["LAND", "MOBILE", "INDIRECTFIRE", "ARTILLERY", "ALLTERRAIN", "TECH3", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["All-Terrain", "Long-Range EMP Paralyzer Bombardment", "Shield Disruptor", "Regenerates (+3 hp/s)"],
        "weapons": [{
            "name": "Bio-EMP Artillery Shell",
            "type": "EMP", "damage": 550, "rof": 0.2, "salvo": 1, "range": 90,
            "min_range": 15, "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_ElectroShell01/XRA_ElectroShell01_proj.bp"
        }]
    },
    {
        "id": "XRA0323",
        "name": "Mobile Acid Bio-Artillery",
        "desc": "Heavy Corrosive Acid Artillery",
        "tech": "T3", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptor_artillery_acid_v2.s3o",
        "tex": "unittextures/chicken_acidgreen_l_color.dds",
        "scale": 0.07, "hp": 1600, "regen": 3.0, "speed": 2.4,
        "mass": 880, "energy": 12000, "buildtime": 2800,
        "shared_sca": "XRA0202", "is_flying": False,
        "categories": ["LAND", "MOBILE", "INDIRECTFIRE", "ARTILLERY", "ALLTERRAIN", "TECH3", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["All-Terrain", "Corrosive Acid Bombardment (Armor Melt AoE)", "Regenerates (+3 hp/s)"],
        "weapons": [{
            "name": "Corrosive Acid Shell",
            "type": "Acid", "damage": 420, "rof": 0.2, "salvo": 1, "range": 95,
            "min_range": 15, "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_AcidShell01/XRA_AcidShell01_proj.bp"
        }]
    },
    {
        "id": "XRA0320",
        "name": "Behemoth EMP Shock Dodo",
        "desc": "Heavy EMP Blackout Kamikaze",
        "tech": "T3", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptor_dodo2_electric.s3o",
        "tex": "unittextures/chicken_electric_l_color.dds",
        "scale": 0.08, "hp": 3200, "regen": 3.0, "speed": 4.2,
        "mass": 750, "energy": 9000, "buildtime": 2100,
        "shared_sca": "XRA0310", "is_flying": False,
        "is_kamikaze": True, "kamikaze_dmg": 2200, "kamikaze_radius": 6.0,
        "categories": ["LAND", "MOBILE", "KAMIKAZE", "TECH3", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Amphibious", "Massive EMP Blackout Pulse (2,200 DMG, Stuns 25r)", "Regenerates (+3 hp/s)"]
    },

    # --- SPIKERS (RANGED SKIRMISHERS) ---
    {
        "id": "XRA0210",
        "name": "Chitin Needle Spiker",
        "desc": "Ranged Chitin Needle Skirmisher",
        "tech": "T2", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptors.s3o",
        "tex": "unittextures/chicken_green_m_color.dds",
        "scale": 0.06, "hp": 850, "regen": 2.0, "speed": 4.2,
        "mass": 220, "energy": 2400, "buildtime": 850,
        "shared_sca": None, "is_flying": False,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "TECH2", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Amphibious", "Rapid Needle Spines", "Skirmisher Kiting", "Regenerates (+2 hp/s)"],
        "weapons": [{
            "name": "Chitin Needle Gun",
            "type": "Kinetic", "damage": 32, "rof": 3.0, "salvo": 1, "range": 28,
            "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp"
        }]
    },
    {
        "id": "XRA0312",
        "name": "Apex Heavy Needle Spiker",
        "desc": "Long-Range Armor-Piercing Rail Spiker",
        "tech": "T3", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptors2.s3o",
        "tex": "unittextures/chicken_darkgreen_m_color.dds",
        "scale": 0.07, "hp": 2400, "regen": 4.0, "speed": 3.6,
        "mass": 680, "energy": 8500, "buildtime": 2200,
        "shared_sca": None, "is_flying": False,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "SNIPER", "TECH3", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Amphibious", "Armor-Piercing Rail Spines (42 range)", "Regenerates (+4 hp/s)"],
        "weapons": [{
            "name": "Heavy Chitin Rail Spiker",
            "type": "Kinetic", "damage": 140, "rof": 2.0, "salvo": 1, "range": 42,
            "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp"
        }]
    },

    # --- SPECTRE (CLOAKED STEALTH) LINE ---
    {
        "id": "XRA0211",
        "name": "Spectre Cloaked Swarmer",
        "desc": "Permanently Cloaked Ambush Swarmer",
        "tech": "T2", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptor1x_spectre.s3o",
        "tex": "unittextures/chicken_yellow_m_color.dds",
        "scale": 0.06, "hp": 450, "regen": 2.0, "speed": 4.8,
        "mass": 180, "energy": 3200, "buildtime": 750,
        "shared_sca": "XRA0101", "is_flying": False, "is_cloaked": True,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "CLOAK", "STEALTH", "TECH2", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Personal Cloak", "Radar Stealth", "Ambush Claws (110 DPS)", "Regenerates (+2 hp/s)"],
        "weapons": [{
            "name": "Spectre Spike Claws",
            "type": "Kinetic", "damage": 55, "rof": 2.0, "salvo": 1, "range": 14,
            "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp"
        }]
    },
    {
        "id": "XRA0313",
        "name": "Spectre Stalker Behemoth",
        "desc": "Heavy Cloaked Assault Behemoth",
        "tech": "T3", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptora_spectre.s3o",
        "tex": "unittextures/chicken_yellow_l_color.dds",
        "scale": 0.075, "hp": 4600, "regen": 5.0, "speed": 3.4,
        "mass": 1100, "energy": 14000, "buildtime": 3400,
        "shared_sca": "XRA0301", "is_flying": False, "is_cloaked": True,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "CLOAK", "STEALTH", "TECH3", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Personal Cloak", "Radar Stealth", "Heavy Scythe Cleaves (480 DPS)", "Anti-Air Spores (160 DPS)", "Regenerates (+5 hp/s)"],
        "weapons": [
            {
                "name": "Spectre Heavy Scythes",
                "type": "Kinetic", "damage": 240, "rof": 2.0, "salvo": 1, "range": 18,
                "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp"
            },
            {
                "name": "Anti-Air Bio Spores",
                "type": "AA", "damage": 80, "rof": 2.0, "salvo": 1, "range": 26,
                "target": "AIR", "proj": "/mods/RaptorFaction/projectiles/XRA_Spore01/XRA_Spore01_proj.bp"
            }
        ]
    },
    {
        "id": "XRA0318",
        "name": "Spectre Phantom Spiker",
        "desc": "Cloaked Long-Range Sniper Bug",
        "tech": "T3", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptors2_spectre.s3o",
        "tex": "unittextures/chicken_yellow_m_color.dds",
        "scale": 0.07, "hp": 2200, "regen": 4.0, "speed": 3.6,
        "mass": 780, "energy": 9500, "buildtime": 2400,
        "shared_sca": None, "is_flying": False, "is_cloaked": True,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "SNIPER", "CLOAK", "STEALTH", "TECH3", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Personal Cloak", "Silent Armor-Piercing Sniping (38 range)", "Regenerates (+4 hp/s)"],
        "weapons": [{
            "name": "Silent Phantom Needler",
            "type": "Kinetic", "damage": 120, "rof": 2.0, "salvo": 1, "range": 38,
            "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp"
        }]
    },

    # --- ELEMENTAL SUB-BOSS MATRIARCHS ---
    {
        "id": "XRA0331",
        "name": "Acid Matriarch Sub-Boss",
        "desc": "T3 Acid Matriarch Commander",
        "tech": "T3", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptor_miniqueen_acid.s3o",
        "tex": "unittextures/chicken_acidgreen_l_color.dds",
        "scale": 0.075, "hp": 19000, "regen": 10.0, "speed": 2.6,
        "mass": 2800, "energy": 32000, "buildtime": 7200,
        "shared_sca": "XRA0303", "is_flying": False,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "SUBCOMMANDER", "TECH3", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Sub-Boss Commander", "Corrosive Acid Mortar & Breath (750 DPS)", "Regenerates (+10 hp/s)"],
        "weapons": [
            {
                "name": "Caustic Acid Blob",
                "type": "Acid", "damage": 250, "rof": 2.0, "salvo": 1, "range": 36,
                "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_AcidSpike01/XRA_AcidSpike01_proj.bp"
            },
            {
                "name": "Heavy Acid Mortar",
                "type": "Acid", "damage": 250, "rof": 1.0, "salvo": 1, "range": 45,
                "min_range": 8, "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_AcidShell01/XRA_AcidShell01_proj.bp"
            }
        ]
    },
    {
        "id": "XRA0332",
        "name": "Storm Matriarch Sub-Boss",
        "desc": "T3 Storm Matriarch Commander",
        "tech": "T3", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptor_miniqueen_electric.s3o",
        "tex": "unittextures/chicken_electric_l_color.dds",
        "scale": 0.075, "hp": 19000, "regen": 10.0, "speed": 2.6,
        "mass": 2800, "energy": 34000, "buildtime": 7200,
        "shared_sca": "XRA0303", "is_flying": False,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "SUBCOMMANDER", "TECH3", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Sub-Boss Commander", "Twin Chain Lightning Arcs (820 DPS)", "EMP Stun Field", "Regenerates (+10 hp/s)"],
        "weapons": [
            {
                "name": "Storm Lightning Beam",
                "type": "EMP", "damage": 410, "rof": 2.0, "salvo": 1, "range": 35,
                "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp"
            }
        ]
    },
    {
        "id": "XRA0333",
        "name": "Pyro Matriarch Sub-Boss",
        "desc": "T3 Pyro Matriarch Commander",
        "tech": "T3", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptor_miniqueen_fire.s3o",
        "tex": "unittextures/chicken_black_l_color.dds",
        "scale": 0.075, "hp": 19000, "regen": 10.0, "speed": 2.6,
        "mass": 2800, "energy": 32000, "buildtime": 7200,
        "shared_sca": "XRA0303", "is_flying": False,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "SUBCOMMANDER", "TECH3", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Sub-Boss Commander", "Quadruple Flamethrowers (1,050 DPS)", "Thermal Firestorm", "Regenerates (+10 hp/s)"],
        "weapons": [
            {
                "name": "Quad Napalm Flamer",
                "type": "Fire", "damage": 35, "rof": 30.0, "salvo": 1, "range": 25,
                "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_PyroStream01/XRA_PyroStream01_proj.bp"
            }
        ]
    },
    {
        "id": "XRA0334",
        "name": "Broodmother Matriarch Sub-Boss",
        "desc": "T3 Broodmother Matriarch Commander",
        "tech": "T3", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptor_miniqueen_healer.s3o",
        "tex": "unittextures/chicken_white_l_color.dds",
        "scale": 0.075, "hp": 22000, "regen": 15.0, "speed": 2.6,
        "mass": 3200, "energy": 36000, "buildtime": 7800,
        "shared_sca": "XRA0303", "is_flying": False, "is_healer": True,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "SUBCOMMANDER", "REPAIR", "TECH3", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Sub-Boss Commander", "Massive Swarm Regen Aura (+50 hp/s)", "Heavy Cleave Claws (650 DPS)", "Regenerates (+15 hp/s)"],
        "weapons": [
            {
                "name": "Broodmother Claws",
                "type": "Kinetic", "damage": 325, "rof": 2.0, "salvo": 1, "range": 22,
                "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp"
            }
        ]
    },
    {
        "id": "XRA0335",
        "name": "Shadow Matriarch Sub-Boss",
        "desc": "T3 Shadow Matriarch Stealth Commander",
        "tech": "T3", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptor_miniqueen_spectre.s3o",
        "tex": "unittextures/chicken_yellow_l_color.dds",
        "scale": 0.075, "hp": 17000, "regen": 8.0, "speed": 2.8,
        "mass": 2900, "energy": 35000, "buildtime": 7500,
        "shared_sca": "XRA0303", "is_flying": False, "is_cloaked": True,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "SUBCOMMANDER", "CLOAK", "STEALTH", "TECH3", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Sub-Boss Commander", "Cloaked Stealth Ambush (920 DPS)", "Plasma Goo Blast", "Regenerates (+8 hp/s)"],
        "weapons": [
            {
                "name": "Shadow Scythe Cleaves",
                "type": "Kinetic", "damage": 460, "rof": 2.0, "salvo": 1, "range": 22,
                "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp"
            }
        ]
    },

    # --- ELEMENTAL SWARMER SUBTYPES ---
    {
        "id": "XRA0112",
        "name": "Caustic Acid Swarmer",
        "desc": "Light Acid Spit & Corrosive Swarmer",
        "tech": "T1", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptoracidswarmer.s3o",
        "tex": "unittextures/chicken_acidgreen_s_color.dds",
        "scale": 0.06, "hp": 210, "regen": 2.0, "speed": 4.6,
        "mass": 65, "energy": 700, "buildtime": 240,
        "shared_sca": "XRA0101", "is_flying": False,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "TECH1", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Amphibious", "Caustic Acid Spit", "Leaves Acid Puddle on Death", "Regenerates (+2 hp/s)"],
        "weapons": [{
            "name": "Acid Saliva",
            "type": "Acid", "damage": 45, "rof": 1.0, "salvo": 1, "range": 16,
            "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_AcidSpike01/XRA_AcidSpike01_proj.bp"
        }]
    },
    {
        "id": "XRA0113",
        "name": "Shock EMP Swarmer",
        "desc": "Light Shock & Shield-Breaker Swarmer",
        "tech": "T1", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/raptore1.s3o",
        "tex": "unittextures/chicken_electric_s_color.dds",
        "scale": 0.06, "hp": 220, "regen": 2.0, "speed": 4.6,
        "mass": 70, "energy": 800, "buildtime": 250,
        "shared_sca": "XRA0101", "is_flying": False,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "TECH1", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Amphibious", "Electric Shock Claws", "Shield Disruptor", "Regenerates (+2 hp/s)"],
        "weapons": [{
            "name": "Shock Claws",
            "type": "EMP", "damage": 42, "rof": 1.0, "salvo": 1, "range": 14,
            "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp"
        }]
    },
    {
        "id": "XRA0114",
        "name": "Brood Swarmer",
        "desc": "Living Brood Swarmer (Splits on Death)",
        "tech": "T1", "type": "LAND", "motion": "RULEUMT_Amphibious",
        "s3o": "objects3d/raptors/s_raptor_white.s3o",
        "tex": "unittextures/chicken_blue_s_color.dds",
        "scale": 0.06, "hp": 230, "regen": 2.0, "speed": 4.5,
        "mass": 75, "energy": 850, "buildtime": 260,
        "shared_sca": "XRA0101", "is_flying": False,
        "categories": ["LAND", "MOBILE", "DIRECTFIRE", "TECH1", "BUILTBYRAPTORHIVE", "RAPTOR"],
        "abilities": ["Amphibious", "Brood Split (Hatches 1 Larva upon death)", "Regenerates (+2 hp/s)"],
        "weapons": [{
            "name": "Brood Spike Claws",
            "type": "Kinetic", "damage": 48, "rof": 1.0, "salvo": 1, "range": 14,
            "target": "LAND", "proj": "/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp"
        }]
    }
]

print(f"Defined {len(NEW_UNITS)} new units to port.")

# ---------------------------------------------------------------------------
# Execution Pipeline: Generate SCM, SCA, DDS, BP, Script for all 25 units
# ---------------------------------------------------------------------------
ref_xra0101 = os.path.join(units_root, "XRA0101")
ref_normals = os.path.join(ref_xra0101, "XRA0101_NormalsTS.dds")
ref_specteam = os.path.join(ref_xra0101, "XRA0101_SpecTeam.dds")
ref_icon = os.path.join(ref_xra0101, "XRA0101_icon.dds")

for u in NEW_UNITS:
    uid = u["id"]
    u_dir = os.path.join(units_root, uid)
    os.makedirs(u_dir, exist_ok=True)
    print(f"\n>>> Porting [{uid}] {u['name']} ({u['desc']})...")

    # 1. S3O -> SCM
    scm_path = os.path.join(u_dir, f"{uid}_lod0.scm")
    s3o_bytes = get_bar_file(u["s3o"])
    if not s3o_bytes:
        print(f"ERROR: Could not find BAR model: {u['s3o']}")
        continue
    pieces = convert_s3o_to_scm(s3o_bytes, scm_path)

    # 2. Textures
    albedo_path = os.path.join(u_dir, f"{uid}_Albedo.dds")
    tex_bytes = get_bar_file(u["tex"])
    if tex_bytes:
        with open(albedo_path, "wb") as f:
            f.write(tex_bytes)
    else:
        # Fallback to ref albedo if not found
        shutil.copyfile(os.path.join(ref_xra0101, "XRA0101_Albedo.dds"), albedo_path)

    shutil.copyfile(ref_normals, os.path.join(u_dir, f"{uid}_NormalsTS.dds"))
    shutil.copyfile(ref_specteam, os.path.join(u_dir, f"{uid}_SpecTeam.dds"))

    # 3. Icon
    icon_path = os.path.join(u_dir, f"{uid}_icon.dds")
    shared_icon_src = os.path.join(units_root, u["shared_sca"], f"{u['shared_sca']}_icon.dds") if u.get("shared_sca") else ref_icon
    if os.path.exists(shared_icon_src):
        shutil.copyfile(shared_icon_src, icon_path)
    else:
        shutil.copyfile(ref_icon, icon_path)
    # Also save to icons/units/
    shutil.copyfile(icon_path, os.path.join(icons_dir, f"{uid}_icon.dds"))

    # 4. SCA Animations
    anim_walk_key = "AnimationFly" if u["is_flying"] else "AnimationWalk"
    anim_walk_name = f"{uid}_Afly.sca" if u["is_flying"] else f"{uid}_Awalk.sca"
    anim_death_name = f"{uid}_Adeath01.sca"
    anim_walk_path = os.path.join(u_dir, anim_walk_name)
    anim_death_path = os.path.join(u_dir, anim_death_name)

    if u.get("shared_sca"):
        src_dir = os.path.join(units_root, u["shared_sca"])
        src_walk = os.path.join(src_dir, f"{u['shared_sca']}_Afly.sca" if u["is_flying"] else f"{u['shared_sca']}_Awalk.sca")
        src_death = os.path.join(src_dir, f"{u['shared_sca']}_Adeath01.sca")
        if os.path.exists(src_walk):
            shutil.copyfile(src_walk, anim_walk_path)
        else:
            generate_procedural_anims(pieces, anim_walk_path, anim_death_path, u["is_flying"])
        if os.path.exists(src_death):
            shutil.copyfile(src_death, anim_death_path)
    else:
        generate_procedural_anims(pieces, anim_walk_path, anim_death_path, u["is_flying"])

    # 5. Blueprint Generation
    weapons_bp_list = []
    if u.get("is_kamikaze"):
        k_dmg = u.get("kamikaze_dmg", 1000)
        k_rad = u.get("kamikaze_radius", 4.0)
        weapons_bp_list.append(f"""        {{
            AboveWaterTargetsOnly = true,
            CollideFriendly = false,
            Damage = {k_dmg},
            DamageFriendly = false,
            DamageRadius = {k_rad},
            DamageType = 'Kamikaze',
            DisplayName = 'Suicide Bio Detonation',
            FireTargetLayerCapsTable = {{
                Air = 'Land|Water|Seabed',
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            }},
            FiringTolerance = 2,
            Label = 'KamikazeWeapon',
            MaxRadius = 3,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            MuzzleVelocity = 0,
            NeedPrep = true,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1,
            TargetCheckInterval = 0.1,
            TargetPriorities = {{
                'COMMAND',
                'TECH3 STRUCTURE',
                'TECH2 STRUCTURE',
                'TECH1 STRUCTURE',
                'ALLUNITS',
            }},
            TargetRestrictDisallow = 'UNTARGETABLE',
            Turreted = false,
            WeaponCategory = 'Kamikaze',
        }},""")
    elif u.get("weapons"):
        for widx, w in enumerate(u["weapons"]):
            w_name = w["name"]
            w_dmg = w["damage"]
            w_rof = w["rof"]
            w_range = w["range"]
            min_r = w.get("min_range", 0)
            w_salvo = w.get("salvo", 1)
            proj = w["proj"]
            if w.get("type") == "Bomb" or "BOMBER" in u["categories"]:
                weapons_bp_list.append(f"""        {{
            AboveWaterTargetsOnly = true,
            Audio = {{
                Fire = Sound {{
                    Bank = 'Raptor_Attack',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                }},
            }},
            AutoInitiateAttackCommand = true,
            BallisticArc = 'RULEUBA_None',
            BombDropThreshold = 3.5,
            CollideFriendly = false,
            Damage = {w_dmg},
            DamageRadius = {w.get('radius', 3.5)},
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
            MuzzleSalvoDelay = 0.15,
            MuzzleSalvoSize = {w_salvo},
            MuzzleVelocity = 0,
            NeedToComputeBombDrop = true,
            ProjectileId = '{proj}',
            ProjectilesPerOnFire = {w_salvo},
            RackBones = {{
                {{
                    MuzzleBones = {{
                        'body',
                    }},
                    RackBone = 'body',
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

            is_aa = w["target"] == "AIR"
            target_caps = "Air = 'Air'" if is_aa else "Air = 'Land|Water', Land = 'Land|Water', Water = 'Land|Water'"
            rcat = 'UWRC_AntiAir' if is_aa else ('UWRC_IndirectFire' if min_r > 0 else 'UWRC_DirectFire')
            wcat = 'Anti Air' if is_aa else 'Direct Fire'
            cannot_attack_ground = "\n            CannotAttackGround = true," if is_aa else ""
            firing_tol = 60 if is_aa else 2
            turret_p_speed = 360 if is_aa else 60
            turret_y_speed = 360 if is_aa else 90
            turret_p_range = 90 if is_aa else 45
            ballistic_arc = 'RULEUBA_None' if is_aa else ("RULEUBA_HighArc" if min_r > 0 else "RULEUBA_LowArc")
            target_priorities_block = """            TargetPriorities = {
                'SPECIALHIGHPRI',
                'AIR MOBILE EXPERIMENTAL',
                'AIR MOBILE TECH3 ANTAIR',
                'AIR MOBILE HIGHPRIAIR',
                'AIR MOBILE TECH2',
                'AIR MOBILE TECH1',
                'ALLUNITS',
            },""" if is_aa else """            TargetPriorities = {
                'COMMAND',
                'EXPERIMENTAL',
                'TECH3',
                'TECH2',
                'TECH1',
                'ALLUNITS',
            },"""

            weapons_bp_list.append(f"""        {{
            AboveWaterTargetsOnly = true,
            Audio = {{
                Fire = Sound {{
                    Bank = 'Raptor_Attack',
                    Cue = 'Attack',
                    LodCutoff = 'Weapon_LodCutoff',
                }},
            }},
            BallisticArc = '{ballistic_arc}',{cannot_attack_ground}
            CollideFriendly = false,
            Damage = {w_dmg},
            DamageRadius = {3.0 if min_r > 0 else 1.0},
            DamageType = 'Normal',
            DisplayName = '{w_name}',
            FireTargetLayerCapsTable = {{
                {target_caps}
            }},
            FiringTolerance = {firing_tol},
            Label = 'MainGun{widx+1}',
            MaxRadius = {w_range},
            MinRadius = {min_r},
            MuzzleSalvoDelay = 0.1,
            MuzzleSalvoSize = {w_salvo},
            MuzzleVelocity = {25 if min_r > 0 else 40},
            ProjectileId = '{proj}',
            ProjectileLifetimeUsesMultiplier = 1.15,
            ProjectilesPerOnFire = {w_salvo},
            RackBones = {{
                {{
                    MuzzleBones = {{
                        'body',
                    }},
                    RackBone = 'body',
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
{target_priorities_block}
            TargetRestrictDisallow = 'UNTARGETABLE',
            TrackingRadius = 1.25,
            TurretBoneMuzzle = 'body',
            TurretBonePitch = 'body',
            TurretBoneYaw = 'body',
            TurretDualManipulators = false,
            TurretPitch = 0,
            TurretPitchRange = {turret_p_range},
            TurretPitchSpeed = {turret_p_speed},
            TurretYaw = 0,
            TurretYawRange = 180,
            TurretYawSpeed = {turret_y_speed},
            Turreted = true,
            WeaponCategory = '{wcat}',
        }},""")

    weapons_str = "\n".join(weapons_bp_list)
    unit_cats = list(u["categories"])
    for req in ['PRODUCTSC1', 'SELECTABLE', 'VISIBLETORECON', 'RECLAIMABLE']:
        if req not in unit_cats:
            unit_cats.insert(0, req)
    if 'DIRECTFIRE' in unit_cats and 'OVERLAYDIRECTFIRE' not in unit_cats:
        unit_cats.append('OVERLAYDIRECTFIRE')
    if 'ANTIAIR' in unit_cats and 'OVERLAYANTIAIR' not in unit_cats:
        unit_cats.append('OVERLAYANTIAIR')
    cats_str = ",\n".join(f"        '{c}'" for c in unit_cats)
    abilities_str = ",\n".join(f"            '<LOC ability_{a.lower().replace(' ', '_')}> {a}'" for a in u["abilities"])

    intel_str = ""
    if u.get("is_cloaked"):
        intel_str = """        Cloak = true,
        RadarStealth = true,
        SonarStealth = true,
        CloakFieldRadius = 0,
        InitialCloakDelay = 2,
        StealthWaitTime = 1,"""

    motion_type = u["motion"]
    air_physics = ""
    air_block = ""
    if u["is_flying"]:
        air_physics = f"""        Elevation = 8,
        FuelRechargeRate = 150,
        FuelUseTime = 1500,
        GroundElevation = 8,
        MaxSpeedSizeControl = 0.3,"""

        cats = u["categories"]
        if "ANTIAIR" in cats and "BOMBER" not in cats:
            if u.get("tech") == "T3":
                air_block = f"""    Air = {{
        AutoLandTime = 1,
        BankFactor = 4.0,
        BankForward = false,
        BreakOffDistance = 10,
        BreakOffTrigger = 15,
        CanFly = true,
        CombatTurnSpeed = 3.6,
        EngageDistance = 50,
        KLift = 3,
        KLiftDamping = 2.5,
        KMove = 1.8,
        KMoveDamping = 1,
        KRoll = 2.5,
        KRollDamping = 1,
        KTurn = 3.0,
        KTurnDamping = 1.6,
        LiftFactor = 7,
        MaxAirspeed = {u['speed']},
        MinAirspeed = 8,
        StartTurnDistance = 5,
        TightTurnMultiplier = 1.3,
        TurnSpeed = 3.6,
        Winged = true,
    }},
"""
            else:
                air_block = f"""    Air = {{
        AutoLandTime = 1,
        BankFactor = 0.4,
        BankForward = false,
        CanFly = true,
        CirclingDirChangeFrequencySec = 1,
        CirclingElevationChangeRatio = 0.25,
        CirclingFlight = true,
        CirclingRadiusChangeMaxRatio = 0.8,
        CirclingRadiusChangeMinRatio = 0.5,
        CirclingRadiusVsAirMult = 0.66,
        CirclingTurnMult = 4,
        CombatTurnSpeed = 4.0,
        KLift = 3,
        KLiftDamping = 2.5,
        KMove = 1.2,
        KMoveDamping = 1.5,
        KRoll = 1.5,
        KRollDamping = 1.0,
        KTurn = 2.8,
        KTurnDamping = 1.5,
        LiftFactor = 7,
        MaxAirspeed = {u['speed']},
        MinAirspeed = 3,
        StartTurnDistance = 5,
        TurnSpeed = 4.0,
        Winged = false,
    }},
"""
        elif "BOMBER" in cats:
            air_block = f"""    Air = {{
        AutoLandTime = 1,
        BankFactor = 3,
        BankForward = false,
        BreakOffDistance = 36,
        BreakOffIfNearNewTarget = true,
        BreakOffTrigger = 20,
        CanFly = true,
        CombatTurnSpeed = 1.5,
        EngageDistance = 50,
        KLift = 3,
        KLiftDamping = 2.5,
        KMove = 1,
        KMoveDamping = 2,
        KRoll = 2,
        KRollDamping = 2,
        KTurn = 0.8,
        KTurnDamping = 1,
        LiftFactor = 10,
        MaxAirspeed = {u['speed']},
        MinAirspeed = {u['speed']},
        PredictAheadForBombDrop = 3,
        RandomBreakOffDistanceMult = 1.5,
        StartTurnDistance = 1.4,
        TightTurnMultiplier = 0,
        TurnSpeed = 1.5,
        Winged = true,
    }},
"""
        elif "KAMIKAZE" in cats:
            air_block = f"""    Air = {{
        AutoLandTime = 1,
        BankFactor = 3.5,
        BankForward = false,
        BreakOffDistance = 5,
        BreakOffTrigger = 10,
        CanFly = true,
        CombatTurnSpeed = 4.2,
        EngageDistance = 50,
        KLift = 3,
        KLiftDamping = 2.5,
        KMove = 2.0,
        KMoveDamping = 1,
        KRoll = 2.5,
        KRollDamping = 1,
        KTurn = 3.2,
        KTurnDamping = 1.4,
        LiftFactor = 7,
        MaxAirspeed = {u['speed']},
        MinAirspeed = 8,
        StartTurnDistance = 5,
        TightTurnMultiplier = 1.3,
        TurnSpeed = 4.2,
        Winged = true,
    }},
"""
        else:
            air_block = f"""    Air = {{
        AutoLandTime = 1,
        BankFactor = 0.4,
        BankForward = false,
        CanFly = true,
        CirclingDirChangeFrequencySec = 1,
        CirclingElevationChangeRatio = 0.25,
        CirclingFlight = true,
        CirclingRadiusChangeMaxRatio = 0.8,
        CirclingRadiusChangeMinRatio = 0.5,
        CirclingRadiusVsAirMult = 0.66,
        CirclingTurnMult = 4,
        CombatTurnSpeed = 3.6,
        KLift = 3,
        KLiftDamping = 2.5,
        KMove = 1.1,
        KMoveDamping = 1.5,
        KRoll = 1.5,
        KRollDamping = 1.0,
        KTurn = 2.6,
        KTurnDamping = 1.5,
        LiftFactor = 7,
        MaxAirspeed = {u['speed']},
        MinAirspeed = 3,
        StartTurnDistance = 5,
        TurnSpeed = 3.6,
        Winged = false,
    }},
"""

    if u["is_flying"]:
        build_layer_caps = """            LAYER_Air = true,
            LAYER_Land = false,
            LAYER_Orbit = false,
            LAYER_Seabed = false,
            LAYER_Sub = false,
            LAYER_Water = false,"""
        physics_banking = 0.5
        turn_rate = 240
        turn_radius = 2 if "BOMBER" in u["categories"] else 0
        steer_force = 50
    else:
        build_layer_caps = """            LAYER_Air = false,
            LAYER_Land = true,
            LAYER_Orbit = false,
            LAYER_Seabed = true,
            LAYER_Sub = false,
            LAYER_Water = false,"""
        physics_banking = 0
        turn_rate = 90
        turn_radius = 0
        steer_force = 10

    bp_content = f"""UnitBlueprint {{
    AI = {{
        TargetBones = {{
            'body',
        }},
    }},
{air_block}    Audio = {{
        Destroyed = Sound {{
            Bank = 'Raptor_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        }},
        Killed = Sound {{
            Bank = 'Raptor_Death',
            Cue = 'Death',
            LodCutoff = 'UnitMove_LodCutoff',
        }},
    }},
    Buffs = {{
        Regen = {{
            Level1 = 1,
            Level2 = 2,
            Level3 = 3,
            Level4 = 4,
            Level5 = 5,
        }},
    }},
    BuildIconSortPriority = 20,
    Categories = {{
{cats_str},
    }},
    Defense = {{
        AirThreatLevel = 0,
        ArmorType = 'Normal',
        EconomyThreatLevel = 0,
        Health = {u['hp']},
        MaxHealth = {u['hp']},
        RegenRate = {u['regen']},
        SubThreatLevel = 0,
        SurfaceThreatLevel = 5,
    }},
    Description = '<LOC {uid.lower()}_desc>{u['desc']}',
    Display = {{
        Abilities = {{
{abilities_str},
        }},
        AnimationDeath = {{
            {{
                Animation = '/mods/RaptorFaction/units/{uid}/{anim_death_name}',
                AnimationRateMax = 1.2,
                AnimationRateMin = 0.8,
                Weight = 100,
            }},
        }},
        {anim_walk_key} = '/mods/RaptorFaction/units/{uid}/{anim_walk_name}',
        Mesh = {{
            IconFadeInZoom = 130,
            LODs = {{
                {{
                    AlbedoName = '/mods/RaptorFaction/units/{uid}/{uid}_Albedo.dds',
                    LODCutoff = 215,
                    MeshName = '/mods/RaptorFaction/units/{uid}/{uid}_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/{uid}/{uid}_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/{uid}/{uid}_SpecTeam.dds',
                    ShaderName = 'Insect',
                }},
            }},
        }},
        MovementEffects = {{
        }},
        PlaceholderMeshName = 'UXL0001',
        SpawnRandomRotation = true,
        UniformScale = {u['scale']},
    }},
    Economy = {{
        BuildCostEnergy = {u['energy']},
        BuildCostMass = {u['mass']},
        BuildTime = {u['buildtime']},
    }},
    General = {{
        Category = '{u['type'].capitalize()}',
        Classification = 'RULEUC_MilitaryVehicle',
        CommandCaps = {{
            RULEUCC_Attack = true,
            RULEUCC_CallTransport = false,
            RULEUCC_Capture = false,
            RULEUCC_Guard = true,
            RULEUCC_Move = true,
            RULEUCC_Nuke = false,
            RULEUCC_Patrol = true,
            RULEUCC_Reclaim = false,
            RULEUCC_Repair = {str(u.get('is_healer', False)).lower()},
            RULEUCC_RetaliateToggle = true,
            RULEUCC_Stop = true,
            RULEUCC_Transport = false,
        }},
        FactionName = 'Cybran',
        Icon = '{"air" if u["is_flying"] else "amph"}',
        TechLevel = 'RULEUTL_Advanced',
        UnitName = '<LOC {uid.lower()}_name>{u['name']}',
        UnitWeight = 1,
    }},
    Intel = {{
        VisionRadius = 24,
{intel_str}
    }},
    Interface = {{
        HelpText = '<LOC {uid.lower()}_help>{u['desc']}',
    }},
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.5,
    Physics = {{
        BankingSlope = {physics_banking},
        BuildOnLayerCaps = {{
{build_layer_caps}
        }},
        DragCoefficient = 0.2,
{air_physics}
        MaxAcceleration = 3.5,
        MaxBrake = 3.5,
        MaxSpeed = {u['speed']},
        MaxSpeedReverse = 0,
        MaxSteerForce = {steer_force},
        MeshExtentsX = 1.0,
        MeshExtentsY = 0.8,
        MeshExtentsZ = 1.2,
        MinSpeedPercent = 0,
        MotionType = '{motion_type}',
        TurnRadius = {turn_radius},
        TurnRate = {turn_rate},
    }},
    SelectionSizeX = 0.6,
    SelectionSizeZ = 0.8,
    SelectionThickness = 0.6,
    SizeX = 0.8,
    SizeY = 0.6,
    SizeZ = 1.0,
    StrategicIconName = 'icon_{"commander" if "SUBCOMMANDER" in u["categories"] else ("land" if not u["is_flying"] else "air")}{u["tech"][1]}_{"bomb" if "BOMBER" in u["categories"] else ("antiair" if "ANTIAIR" in u["categories"] else ("artillery" if "ARTILLERY" in u["categories"] else "directfire"))}',
    StrategicIconSortPriority = 115,
    Veteran = {{
        Level1 = 5,
        Level2 = 10,
        Level3 = 15,
        Level4 = 20,
        Level5 = 25,
    }},
    Weapon = {{
{weapons_str}
    }},
    Wreckage = {{
        Blueprint = '/props/DefaultWreckage/DefaultWreckage_prop.bp',
        EnergyMult = 0,
        HealthMult = 0.9,
        MassMult = 0.9,
        ReclaimTimeMultiplier = 1,
        WreckageLayers = {{
            Air = false,
            Land = true,
            Seabed = true,
            Sub = false,
            Water = false,
        }},
    }},
}}
"""
    with open(os.path.join(u_dir, f"{uid}_unit.bp"), "w") as f:
        f.write(bp_content)

    # 6. Script Generation
    script_class = "CAirUnit" if u["is_flying"] else "CWalkingLandUnit"
    base_import = "from '/lua/cybranunits.lua' import CAirUnit" if u["is_flying"] else "from '/lua/cybranunits.lua' import CWalkingLandUnit"
    weapon_import = "from '/lua/cybranweapons.lua' import CDFLaserHeavyWeapon"
    weapon_class = "CDFLaserHeavyWeapon"
    weapon_table = f"""        MainGun1 = ClassWeapon({weapon_class}) {{}},
        MainGun2 = ClassWeapon({weapon_class}) {{}},
        KamikazeWeapon = ClassWeapon({weapon_class}) {{}},"""

    if "BOMBER" in u["categories"]:
        weapon_import = "from '/lua/sim/defaultweapons.lua' import DefaultProjectileWeapon"
        weapon_class = "DefaultProjectileWeapon"
        weapon_table = """        Bomb = ClassWeapon(DefaultProjectileWeapon) {},"""

    kamikaze_code = ""
    if u.get("is_kamikaze"):
        kamikaze_code = f"""
    OnKilled = function(self, instigator, type, overkillRatio)
        local pos = self:GetPosition()
        DamageArea(self, pos, {u.get('kamikaze_radius', 4.0)}, {u.get('kamikaze_dmg', 1000)}, 'Kamikaze', true, false)
        {script_class}.OnKilled(self, instigator, type, overkillRatio)
    end,
"""
    healer_code = ""
    if u.get("is_healer"):
        healer_code = """
    OnStopBeingBuilt = function(self, builder, layer)
        """ + script_class + """.OnStopBeingBuilt(self, builder, layer)
        self:ForkThread(self.HealerAuraThread)
    end,

    HealerAuraThread = function(self)
        while not self.Dead do
            local pos = self:GetPosition()
            local units = GetUnitsInRect(Rect(pos[1] - 15, pos[3] - 15, pos[1] + 15, pos[3] + 15))
            if units then
                for _, u in units do
                    if u and not u.Dead and u:GetArmy() == self:GetArmy() and u != self then
                        local curHp = u:GetHealth()
                        local maxHp = u:GetMaxHealth()
                        if curHp < maxHp then
                            u:AdjustHealth(self, 25)
                        end
                    end
                end
            end
            WaitSeconds(1)
        end
    end,
"""

    script_content = f"""local {script_class} = {base_import}
local {weapon_class} = {weapon_import}

---@class {uid} : {script_class}
{uid} = ClassUnit({script_class}) {{
    Weapons = {{
{weapon_table}
    }},
{kamikaze_code}
{healer_code}
}}

TypeClass = {uid}
"""
    with open(os.path.join(u_dir, f"{uid}_script.lua"), "w") as f:
        f.write(script_content)

    print(f"Successfully ported [{uid}] {u['name']}.")

print("\nAll 25 units generated successfully!")
