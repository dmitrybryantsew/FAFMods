import os
import struct
import math
import shutil

# Target mod directory
mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
units_root = os.path.join(mod_dir, "units")
workspace_units = r"E:\Games\FAFMods\units"

def pad(size):
    val = 16 - (size % 16)
    return val + 16 if (val < 4) else val

def pad_file(f, s4comment):
    n = pad(f.tell()) - 4
    fill = b'\xC5' * n
    f.write(struct.pack(f'{n}s4s', fill, s4comment))
    return f.tell()

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
        # 28-byte dummy root pose required by Supreme Commander CAnimData loader
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

def get_scm_bones(scm_path):
    with open(scm_path, 'rb') as f:
        data = f.read()
    magic, version, bone_offset, bone_count = struct.unpack('<4sIII', data[:16])
    skel_idx = data.find(b'SKEL')
    name_idx = data.find(b'NAME')
    names_raw = data[name_idx+4:skel_idx-4]
    names = [n.decode('ascii', 'ignore') for n in names_raw.split(b'\x00') if n][:bone_count]
    positions = {}
    parents = []
    for i in range(bone_count):
        off = bone_offset + i * 108
        vals = struct.unpack('<16f3f4f4i', data[off:off + 108])
        pos = vals[16:19]
        parents.append(vals[24])
        positions[names[i]] = pos
    return names, parents, positions

def main():
    scm_path = os.path.join(units_root, "XRA0303", "XRA0303_lod0.scm")
    names, parents, pos = get_scm_bones(scm_path)
    print(f"Loaded {len(names)} bones from {scm_path}")

    dir_xra0303 = os.path.join(units_root, "XRA0303")

    # 1. Walk Animation
    num_frames_walk = 32
    dur_walk = 1.2
    walk_frames = []
    for f_idx in range(num_frames_walk):
        t = f_idx / num_frames_walk
        phase_A = 2.0 * math.pi * t
        phase_B = phase_A + math.pi
        rot = {}

        # Front-Left & Back-Right (A)
        rot['lthighf'] = (math.sin(phase_A) * math.radians(22.0), 0, 0)
        rot['lkneef'] = (-max(0.0, -math.sin(phase_A)) * math.radians(28.0), 0, 0)
        rot['rthighb'] = (math.sin(phase_A) * math.radians(22.0), 0, 0)
        rot['rkneeb'] = (-max(0.0, -math.sin(phase_A)) * math.radians(28.0), 0, 0)

        # Front-Right & Back-Left (B)
        rot['rthighf'] = (math.sin(phase_B) * math.radians(22.0), 0, 0)
        rot['rkneef'] = (-max(0.0, -math.sin(phase_B)) * math.radians(28.0), 0, 0)
        rot['lthighb'] = (math.sin(phase_B) * math.radians(22.0), 0, 0)
        rot['lkneeb'] = (-max(0.0, -math.sin(phase_B)) * math.radians(28.0), 0, 0)

        # Body roll, pitch & bounce
        rot['body'] = (math.sin(phase_A * 2.0) * math.radians(3.5), 0, math.cos(phase_A) * math.radians(2.5))
        rot['tail'] = (-math.sin(phase_A * 2.0) * math.radians(6.0), math.sin(phase_A) * math.radians(14.0), 0)

        # Scythe arm movement
        rot['rforearmu'] = (math.sin(phase_A) * math.radians(12.0), 0, 0)
        rot['lforearmu'] = (-math.sin(phase_A) * math.radians(12.0), 0, 0)
        rot['rforearml'] = (math.sin(phase_A) * math.radians(10.0), 0, 0)
        rot['lforearml'] = (-math.sin(phase_A) * math.radians(10.0), 0, 0)

        time_sec = t * dur_walk
        walk_frames.extend([time_sec, 0])
        for b_idx, b_name in enumerate(names):
            rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
            qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
            if b_idx == 0:
                px, py, pz = 0.0, 0.0, 0.0
                qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
            else:
                px, py, pz = pos[b_name]
            walk_frames.extend([px, py, pz, qw, qx, qy, qz])

    walk_path = os.path.join(dir_xra0303, "XRA0303_Awalk.sca")
    save_sca_file(walk_path, num_frames_walk, dur_walk, names, parents, walk_frames)

    # 2. Roar Animation
    num_frames_roar = 24
    dur_roar = 1.1
    roar_frames = []
    for f_idx in range(num_frames_roar):
        t = f_idx / num_frames_roar
        time_sec = t * dur_roar
        rot = {}
        roar = math.sin(math.pi * t)
        rot['body'] = (roar * math.radians(18.0), 0, 0)
        rot['head'] = (roar * math.radians(22.0), 0, 0)
        rot['rforearmu'] = (0, roar * math.radians(30.0), 0)
        rot['lforearmu'] = (0, -roar * math.radians(30.0), 0)
        rot['rforearml'] = (roar * math.radians(20.0), 0, 0)
        rot['lforearml'] = (roar * math.radians(20.0), 0, 0)

        roar_frames.extend([time_sec, 0])
        for b_idx, b_name in enumerate(names):
            rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
            qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
            if b_idx == 0:
                px, py, pz = 0.0, 0.0, 0.0
                qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
            else:
                px, py, pz = pos[b_name]
            roar_frames.extend([px, py, pz, qw, qx, qy, qz])

    roar_path = os.path.join(dir_xra0303, "XRA0303_Aroar.sca")
    save_sca_file(roar_path, num_frames_roar, dur_roar, names, parents, roar_frames)

    # 3. Death Animation
    num_frames_death = 36
    dur_death = 1.5
    death_frames = []
    for f_idx in range(num_frames_death):
        t = f_idx / (num_frames_death - 1)
        time_sec = t * dur_death
        rot = {}
        rot['body'] = (math.radians(-30.0) * t, 0, math.radians(8.0) * t)
        rot['head'] = (math.radians(-20.0) * t, 0, 0)
        rot['lthighf'] = (math.radians(25.0) * t, 0, math.radians(20.0) * t)
        rot['rthighf'] = (math.radians(25.0) * t, 0, -math.radians(20.0) * t)
        rot['lthighb'] = (-math.radians(20.0) * t, 0, math.radians(25.0) * t)
        rot['rthighb'] = (-math.radians(20.0) * t, 0, -math.radians(25.0) * t)

        death_frames.extend([time_sec, 0])
        for b_idx, b_name in enumerate(names):
            rx, ry, rz = rot.get(b_name, (0.0, 0.0, 0.0))
            qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
            if b_idx == 0:
                px, py, pz = 0.0, 0.0, 0.0
                qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
            else:
                px, py, pz = pos[b_name]
            death_frames.extend([px, py, pz, qw, qx, qy, qz])

    death_path = os.path.join(dir_xra0303, "XRA0303_Adeath01.sca")
    save_sca_file(death_path, num_frames_death, dur_death, names, parents, death_frames)

    # Distribute to elemental variants XRA0331 .. XRA0335
    elementals = ["XRA0331", "XRA0332", "XRA0333", "XRA0334", "XRA0335"]
    for elem_id in elementals:
        elem_dir = os.path.join(units_root, elem_id)
        if os.path.exists(elem_dir):
            elem_walk = os.path.join(elem_dir, f"{elem_id}_Awalk.sca")
            elem_death = os.path.join(elem_dir, f"{elem_id}_Adeath01.sca")
            shutil.copyfile(walk_path, elem_walk)
            shutil.copyfile(death_path, elem_death)
            print(f"Updated {elem_id} animations from corrected XRA0303.")

    # Also sync XRA0303 to E:\Games\FAFMods\units\XRA0303
    ws_xra0303 = os.path.join(workspace_units, "XRA0303")
    os.makedirs(ws_xra0303, exist_ok=True)
    for fname in os.listdir(dir_xra0303):
        src_file = os.path.join(dir_xra0303, fname)
        if os.path.isfile(src_file):
            shutil.copyfile(src_file, os.path.join(ws_xra0303, fname))
    print(f"Synced XRA0303 to {ws_xra0303}")

if __name__ == "__main__":
    main()
