import os, struct, math
from scm_io import pad, pad_file

piece_names = [
    "base", "body", "aimy1", "head",
    "lupperarm", "lforearm", "lblade",
    "rupperarm", "rforearm", "rblade",
    "lthigh", "lknee", "lshin", "lfoot",
    "rthigh", "rknee", "rshin", "rfoot",
    "tail"
]

parent_indices = [
    -1, 0, 1, 2,
    3, 4, 5,
    3, 7, 8,
    1, 10, 11, 12,
    1, 14, 15, 16,
    1
]

SCALE = 0.06
local_rest_positions = {
    "base": (0.0, 0.0, 0.0),
    "body": (-0.00, 19.00 * SCALE, -7.68 * SCALE),
    "aimy1": (-0.00, 0.94 * SCALE, 6.55 * SCALE),
    "head": (-0.00, 0.00, 0.00),
    "lupperarm": (5.61 * SCALE, 0.94 * SCALE, 7.25 * SCALE),
    "lforearm": (-1.12 * SCALE, 0.00, 7.48 * SCALE),
    "lblade": (6.46 * SCALE, 0.00, -10.06 * SCALE),
    "rupperarm": (-5.61 * SCALE, 0.94 * SCALE, 7.25 * SCALE),
    "rforearm": (1.12 * SCALE, 0.00, 7.48 * SCALE),
    "rblade": (-6.46 * SCALE, 0.00, -10.06 * SCALE),
    "lthigh": (5.85 * SCALE, 0.47 * SCALE, 0.70 * SCALE),
    "lknee": (-0.00, -4.68 * SCALE, 5.38 * SCALE),
    "lshin": (-0.00, -2.57 * SCALE, -5.62 * SCALE),
    "lfoot": (-0.00, -8.59 * SCALE, 1.40 * SCALE),
    "rthigh": (-5.85 * SCALE, 0.47 * SCALE, 0.70 * SCALE),
    "rknee": (-0.00, -4.68 * SCALE, 5.38 * SCALE),
    "rshin": (-0.00, -2.57 * SCALE, -5.62 * SCALE),
    "rfoot": (-0.00, -8.59 * SCALE, 1.40 * SCALE),
    "tail": (-0.00, 1.64 * SCALE, -7.25 * SCALE),
}

def euler_to_quat(rot_x, rot_y, rot_z):
    # Returns (qw, qx, qy, qz) for Supreme Commander SCA format
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

def save_sca(filepath, num_frames, duration, piece_names, parent_indices, frames_data):
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

# ==================== WALK ANIMATION (HIGH ENERGY SPRINT) ====================
num_walk_frames = 24
walk_duration = 0.8
walk_frames = []

for f_idx in range(num_walk_frames):
    t_ratio = f_idx / num_walk_frames
    time_sec = t_ratio * walk_duration
    phase = 2.0 * math.pi * t_ratio

    walk_frames.append(time_sec)
    walk_frames.append(0)

    for b_idx, b_name in enumerate(piece_names):
        rx, ry, rz = 0.0, 0.0, 0.0
        lx, ly, lz = local_rest_positions[b_name]

        if b_name == "body":
            ly += math.sin(2.0 * phase) * 0.06
            rx = math.sin(2.0 * phase) * math.radians(5.0)
            rz = math.sin(phase) * math.radians(3.0)
        elif b_name == "tail":
            ry = -math.sin(phase) * math.radians(25.0)
            rx = -math.sin(2.0 * phase) * math.radians(8.0)
        elif b_name == "head":
            rx = -math.sin(2.0 * phase) * math.radians(3.0)
        elif b_name == "lthigh":
            rx = math.sin(phase) * math.radians(45.0)
        elif b_name == "rthigh":
            rx = -math.sin(phase) * math.radians(45.0)
        elif b_name == "lknee":
            rx = -max(0.0, -math.sin(phase)) * math.radians(55.0)
        elif b_name == "rknee":
            rx = -max(0.0, math.sin(phase)) * math.radians(55.0)
        elif b_name == "lshin":
            rx = math.sin(phase) * math.radians(25.0)
        elif b_name == "rshin":
            rx = -math.sin(phase) * math.radians(25.0)
        elif b_name == "lfoot":
            rx = -math.sin(phase) * math.radians(18.0)
        elif b_name == "rfoot":
            rx = math.sin(phase) * math.radians(18.0)
        elif b_name in ("lupperarm", "lblade"):
            rx = -math.sin(phase) * math.radians(28.0)
        elif b_name in ("rupperarm", "rblade"):
            rx = math.sin(phase) * math.radians(28.0)

        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        walk_frames.extend([lx, ly, lz, qw, qx, qy, qz])

# ==================== DEATH ANIMATION ====================
num_death_frames = 20
death_duration = 1.0
death_frames = []

for f_idx in range(num_death_frames):
    t_ratio = f_idx / (num_death_frames - 1)
    time_sec = t_ratio * death_duration

    death_frames.append(time_sec)
    death_frames.append(0)

    for b_idx, b_name in enumerate(piece_names):
        rx, ry, rz = 0.0, 0.0, 0.0
        lx, ly, lz = local_rest_positions[b_name]

        fall = min(1.0, t_ratio * 1.5)
        if b_name == "body":
            ly -= fall * 0.7
            rx = fall * math.radians(20.0)
            rz = fall * math.radians(35.0)
        elif b_name == "head":
            rx = fall * math.radians(30.0)
        elif b_name == "tail":
            rz = fall * math.radians(-25.0)
        elif b_name in ("lthigh", "rthigh"):
            rx = -fall * math.radians(45.0)
        elif b_name in ("lknee", "rknee"):
            rx = -fall * math.radians(50.0)
        elif b_name in ("lupperarm", "rupperarm"):
            rx = fall * math.radians(40.0)

        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        death_frames.extend([lx, ly, lz, qw, qx, qy, qz])

mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
walk_path = os.path.join(mod_dir, "units", "XRA0101", "XRA0101_Awalk.sca")
death_path = os.path.join(mod_dir, "units", "XRA0101", "XRA0101_Adeath01.sca")
death2_path = os.path.join(mod_dir, "units", "XRA0101", "XRA0101_Adeath02.sca")

save_sca(walk_path, num_walk_frames, walk_duration, piece_names, parent_indices, walk_frames)
save_sca(death_path, num_death_frames, death_duration, piece_names, parent_indices, death_frames)
save_sca(death2_path, num_death_frames, death_duration, piece_names, parent_indices, death_frames)

print("Generated high-amplitude walk and death animations!")
