import os
import gzip
import struct
import math
import wave
import io
import shutil
import zipfile
from scm_io import pad, pad_file, write_scm, write_sca

# Paths
mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
units_dir = os.path.join(mod_dir, "units", "XRA0101")
proj_dir = os.path.join(mod_dir, "projectiles", "XRA_Spike01")
sounds_dir = os.path.join(mod_dir, "sounds")

os.makedirs(units_dir, exist_ok=True)
os.makedirs(proj_dir, exist_ok=True)
os.makedirs(sounds_dir, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. READ BAR POOL & GET FILES
# ---------------------------------------------------------------------------
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
    md5_hex = md5_bytes.hex()
    entries[name.lower()] = (md5_hex, size)

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

print("BAR package indexed.")

# ---------------------------------------------------------------------------
# 2. CONVERT SPIKE.S3O TO SCM PROJECTILE
# ---------------------------------------------------------------------------
print("Converting spike.s3o to SCM projectile...")
spike_s3o = get_bar_file('objects3d/raptors/spike.s3o')
assert spike_s3o, "Could not find spike.s3o!"

SCALE = 0.06

# Root piece header in S3O is at offset 52
name_off, n_child, child_off, n_verts, v_off, v_type, prim_type, idx_cnt, idx_off, col_data, ox, oy, oz = struct.unpack('<10I3f', spike_s3o[52:104])
spike_piece_name = "spike"

spike_verts = []
for v in range(n_verts):
    v_data = spike_s3o[v_off + v*32 : v_off + (v+1)*32]
    vx, vy, vz, nx, ny, nz, tu, tv = struct.unpack('<8f', v_data)
    wx = (ox + vx) * SCALE
    wy = (oy + vy) * SCALE
    wz = (oz + vz) * SCALE
    
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
    v_uv = 1.0 - tv
    # Vertex data in SCM:
    # 3f pos, 3f norm, 3f tang, 3f binorm, 2f uv0, 2f uv1, 4B bone_idx
    spike_verts.extend((wx, wy, wz, nx, ny, nz, tx, ty, tz, bx, by, bz, u, v_uv, u, v_uv, 0, 0, 0, 0))

idx_data = spike_s3o[idx_off : idx_off + idx_cnt*4]
spike_faces = list(struct.unpack(f'<{idx_cnt}I', idx_data))

# 1 root bone
bone_name_offset = 48 + pad(48)
inv_mat = [
    1.0, 0.0, 0.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 1.0, 0.0,
    0.0, 0.0, 0.0, 1.0
]
rot = (1.0, 0.0, 0.0, 0.0) # Identity quat
bone_data = [*inv_mat, 0.0, 0.0, 0.0, *rot, bone_name_offset, -1, 0, 0]
bone_names = [bytearray(spike_piece_name.encode('ascii'))]

off_after_names = bone_name_offset + len(spike_piece_name) + 1
bone_offset = off_after_names + pad(off_after_names)
off_after_bones = bone_offset + 108
vert_offset = off_after_bones + pad(off_after_bones)
off_after_verts = vert_offset + n_verts * 68
face_offset = off_after_verts + pad(off_after_verts)

modl = [
    b'MODL', 5,
    bone_offset, 1,
    vert_offset, 0, n_verts,
    face_offset, len(spike_faces),
    0, 0, 1
]

spike_scm_path = os.path.join(proj_dir, "XRA_Spike01_lod0.scm")
write_scm(spike_scm_path, modl, bone_data, bone_names, spike_verts, spike_faces)
print(f"Created spike SCM projectile at: {spike_scm_path}")

# ---------------------------------------------------------------------------
# 3. WRITE PROJECTILE BLUEPRINT AND SCRIPT
# ---------------------------------------------------------------------------
proj_bp_content = """ProjectileBlueprint {
    Audio = {
        Impact = Sound {
            Bank = 'Impacts',
            Cue = 'X_Impact_Land_Gen_Seraphim',
            LodCutoff = 'Weapon_LodCutoff',
        },
        ImpactTerrain = Sound {
            Bank = 'Impacts',
            Cue = 'X_Impact_Land_Gen_Seraphim',
            LodCutoff = 'Weapon_LodCutoff',
        },
        ImpactWater = Sound {
            Bank = 'Impacts',
            Cue = 'Impact_Water_Splash_AEON',
            LodCutoff = 'Weapon_LodCutoff',
        },
    },
    Categories = {
        'RAPTOR',
        'PROJECTILE',
        'DIRECTFIRE',
        'SERAPHIM',
    },
    Display = {
        ImpactEffects = {
            Type = 'Small01',
        },
        Mesh = {
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0101/XRA0101_Albedo.dds',
                    LODCutoff = 150,
                    MeshName = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_lod0.scm',
                    ShaderName = 'TMeshNoLighting',
                },
            },
        },
        StrategicIconSize = 1,
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
        Weapon = 'Bio Acid Spike',
    },
    Interface = {
        HelpText = 0,
    },
    Physics = {
        Acceleration = 0,
        DestroyOnWater = true,
        InitialSpeed = 26,
        Lifetime = 2.5,
        MaxSpeed = 26,
        UseGravity = true,
        VelocityAlign = true,
    },
}
"""

with open(os.path.join(proj_dir, "XRA_Spike01_proj.bp"), "w", encoding="utf-8") as f:
    f.write(proj_bp_content)

proj_script_content = """local SinglePolyTrailProjectile = import('/lua/sim/DefaultProjectiles.lua').SinglePolyTrailProjectile
local EffectTemplate = import('/lua/EffectTemplates.lua')

---@class XRA_Spike01 : SinglePolyTrailProjectile
XRA_Spike01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/default_polytrail_01_emit.bp',
    PolyTrailOffset = 0,
    FxImpactUnit = EffectTemplate.PhasicAutoGunHitUnit,
    FxImpactProp = EffectTemplate.PhasicAutoGunHitUnit,
    FxImpactLand = EffectTemplate.PhasicAutoGunHit,
}

TypeClass = XRA_Spike01
"""

with open(os.path.join(proj_dir, "XRA_Spike01_script.lua"), "w", encoding="utf-8") as f:
    f.write(proj_script_content)

print("Created XRA_Spike01 projectile blueprints and script.")

# ---------------------------------------------------------------------------
# 4. BUILD MICROSOFT XACT SOUND BANKS (.xsb and .xwb) FROM BAR SOUNDS
# ---------------------------------------------------------------------------
print("Generating Microsoft XACT sound banks for BAR sounds...")

raptor_sounds_dir = os.path.join(sounds_dir, "raptors")
os.makedirs(raptor_sounds_dir, exist_ok=True)

atk_wav_raw = get_bar_file('sounds/raptors/smallraptorattack.wav')
atk_wav_path = os.path.join(raptor_sounds_dir, 'smallraptorattack.wav')
if atk_wav_raw:
    with open(atk_wav_path, 'wb') as f:
        f.write(atk_wav_raw)

d_wav_raw = get_bar_file('sounds/raptors/smallraptordead.wav')
d_wav_path = os.path.join(raptor_sounds_dir, 'smallraptordead.wav')
if d_wav_raw:
    with open(d_wav_path, 'wb') as f:
        f.write(d_wav_raw)

def build_xact_bank(soundbank_name, wavebank_name, cue_name, wav_path):
    p_xsb = r'C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\ExperimentalsExpanded\sounds\PSB1301SB.xsb'
    with open(p_xsb, 'rb') as f:
        sb_tmpl = bytearray(f.read())
        
    with wave.open(wav_path, 'rb') as w:
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
    cue_bytes = cue_name.encode('ascii') + b'\x00'
    sb.extend(cue_bytes)
    struct.pack_into('<H', sb, 0x1e, len(cue_bytes))
    return bytes(xwb_bytes), bytes(sb)

# Generate Attack Bank
atk_xwb, atk_xsb = build_xact_bank('Raptor_Attack', 'Raptor_Attack', 'Attack', atk_wav_path)
with open(os.path.join(sounds_dir, 'Raptor_Attack.xwb'), 'wb') as f:
    f.write(atk_xwb)
with open(os.path.join(sounds_dir, 'Raptor_Attack.xsb'), 'wb') as f:
    f.write(atk_xsb)

# Generate Death Bank
d_xwb, d_xsb = build_xact_bank('Raptor_Death', 'Raptor_Death', 'Death', d_wav_path)
with open(os.path.join(sounds_dir, 'Raptor_Death.xwb'), 'wb') as f:
    f.write(d_xwb)
with open(os.path.join(sounds_dir, 'Raptor_Death.xsb'), 'wb') as f:
    f.write(d_xsb)

print("Generated native XACT sound banks: Raptor_Attack and Raptor_Death.")

# ---------------------------------------------------------------------------
# 5. GENERATE STABLE ANIMATIONS (NO HEAD BREAKING / DISLOCATION)
# ---------------------------------------------------------------------------
print("Generating refined walk and death animations...")

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

local_rest_positions = {
    "base": (0.0, 0.0, 0.0),
    "body": (-0.0, 1.140, -0.4608),
    "aimy1": (-0.0, 0.0562, 0.3931),
    "head": (-0.0, 0.0, 0.0),
    "lupperarm": (0.3369, 0.0562, 0.4351),
    "lforearm": (-0.0674, 0.0, 0.4491),
    "lblade": (0.3875, 0.0, -0.6037),
    "rupperarm": (-0.3369, 0.0562, 0.4351),
    "rforearm": (0.0674, 0.0, 0.4491),
    "rblade": (-0.3875, 0.0, -0.6037),
    "lthigh": (0.3509, 0.0280, 0.0422),
    "lknee": (-0.0, -0.2807, 0.3229),
    "lshin": (-0.0, -0.1544, -0.3369),
    "lfoot": (-0.0, -0.5153, 0.0842),
    "rthigh": (-0.3509, 0.0280, 0.0422),
    "rknee": (-0.0, -0.2807, 0.3229),
    "rshin": (-0.0, -0.1544, -0.3369),
    "rfoot": (-0.0, -0.5153, 0.0842),
    "tail": (-0.0, 0.0982, -0.4351),
}

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

# Walk Animation
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
            ly += math.sin(2.0 * phase) * 0.04
            rx = math.sin(2.0 * phase) * math.radians(4.0)
            rz = math.sin(phase) * math.radians(2.0)
        elif b_name == "tail":
            ry = -math.sin(phase) * math.radians(22.0)
            rx = -math.sin(2.0 * phase) * math.radians(6.0)
        # KEEP aimy1 and head at identity so turret aim manipulator operates cleanly without breaking
        elif b_name in ("aimy1", "head"):
            rx, ry, rz = 0.0, 0.0, 0.0
        # Gentle predatory claw tuck (matching BAR walk)
        elif b_name == "lupperarm":
            rz = -math.sin(phase) * math.radians(4.0)
        elif b_name == "rupperarm":
            rz = math.sin(phase) * math.radians(4.0)
        # Energetic bipedal running stride
        elif b_name == "lthigh":
            rx = math.sin(phase) * math.radians(42.0)
        elif b_name == "rthigh":
            rx = -math.sin(phase) * math.radians(42.0)
        elif b_name == "lknee":
            rx = -max(0.0, -math.sin(phase)) * math.radians(52.0)
        elif b_name == "rknee":
            rx = -max(0.0, math.sin(phase)) * math.radians(52.0)
        elif b_name == "lshin":
            rx = math.sin(phase) * math.radians(22.0)
        elif b_name == "rshin":
            rx = -math.sin(phase) * math.radians(22.0)
        elif b_name == "lfoot":
            rx = -math.sin(phase) * math.radians(16.0)
        elif b_name == "rfoot":
            rx = math.sin(phase) * math.radians(16.0)

        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        walk_frames.extend([lx, ly, lz, qw, qx, qy, qz])

# Death Animation
num_death_frames = 20
death_duration = 0.9
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
            rx = fall * math.radians(25.0)
        elif b_name == "tail":
            rz = fall * math.radians(-25.0)
        elif b_name in ("lthigh", "rthigh"):
            rx = -fall * math.radians(45.0)
        elif b_name in ("lknee", "rknee"):
            rx = -fall * math.radians(50.0)

        qw, qx, qy, qz = euler_to_quat(rx, ry, rz)
        death_frames.extend([lx, ly, lz, qw, qx, qy, qz])

walk_path = os.path.join(units_dir, "XRA0101_Awalk.sca")
death_path = os.path.join(units_dir, "XRA0101_Adeath01.sca")
death2_path = os.path.join(units_dir, "XRA0101_Adeath02.sca")

save_sca_file(walk_path, num_walk_frames, walk_duration, piece_names, parent_indices, walk_frames)
save_sca_file(death_path, num_death_frames, death_duration, piece_names, parent_indices, death_frames)
save_sca_file(death2_path, num_death_frames, death_duration, piece_names, parent_indices, death_frames)

print("Generated refined SCA walk and death animations!")

# ---------------------------------------------------------------------------
# 6. WRITE UPDATED UNIT BLUEPRINT (XRA0101_unit.bp)
# ---------------------------------------------------------------------------
print("Writing updated XRA0101_unit.bp with head restrictions and BAR sound...")

bp_content = """UnitBlueprint {
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
            Level1 = 2,
            Level2 = 4,
            Level3 = 6,
            Level4 = 8,
            Level5 = 10,
        },
    },
    BuildIconSortPriority = 40,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYTIER1FACTORY',
        'BUILTBYTIER2FACTORY',
        'BUILTBYTIER3FACTORY',
        'CYBRAN',
        'SERAPHIM',
        'RAPTOR',
        'MOBILE',
        'LAND',
        'TECH1',
        'DIRECTFIRE',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'BOT',
        'OVERLAYDIRECTFIRE',
    },
    CollisionOffsetY = 0.5,
    Defense = {
        AirThreatLevel = 0,
        ArmorType = 'Normal',
        EconomyThreatLevel = 0,
        Health = 180,
        MaxHealth = 180,
        RegenRate = 2,
        SubThreatLevel = 0,
        SurfaceThreatLevel = 1,
    },
    Description = '<LOC xra0101_desc>Biological T1 Swarmer',
    Display = {
        Abilities = {
            '<LOC ability_amphibious>Amphibious',
            'Biological Swarmer',
        },
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0101/XRA0101_Adeath01.sca',
                AnimationRateMax = 1.2,
                AnimationRateMin = 0.9,
                Weight = 100,
            },
        },
        AnimationWalk = '/mods/RaptorFaction/units/XRA0101/XRA0101_Awalk.sca',
        AnimationWalkRate = 2.0,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0101/XRA0101_Albedo.dds',
                    LODCutoff = 175,
                    MeshName = '/mods/RaptorFaction/units/XRA0101/XRA0101_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0101/XRA0101_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0101/XRA0101_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        PlaceholderMeshName = 'UXL0021',
        SpawnRandomRotation = true,
        UniformScale = 1.0,
    },
    Economy = {
        BuildCostEnergy = 280,
        BuildCostMass = 55,
        BuildTime = 250,
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
        TechLevel = 'RULEUTL_Basic',
        UnitName = 'Raptor Swarmer',
        UnitWeight = 1,
    },
    Intel = {
        VisionRadius = 22,
    },
    Interface = {
        HelpText = '<LOC xra0101_help>Biological T1 Swarmer',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.5,
    LifeBarSize = 0.65,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Air = false,
            LAYER_Land = true,
            LAYER_Orbit = false,
            LAYER_Seabed = true,
            LAYER_Sub = false,
            LAYER_Water = false,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 4.5,
        MaxBrake = 4.5,
        MaxSpeed = 4.5,
        MaxSpeedReverse = 0,
        MaxSteerForce = 10,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        TurnRadius = 0,
        TurnRate = 220,
    },
    SelectionCenterOffsetX = 0,
    SelectionCenterOffsetZ = -0.1,
    SelectionSizeX = 0.50,
    SelectionSizeZ = 0.60,
    SelectionThickness = 0.65,
    SizeX = 0.6,
    SizeY = 0.9,
    SizeZ = 0.9,
    StrategicIconName = 'icon_bot1_directfire',
    StrategicIconSortPriority = 135,
    Transport = {
        CanFireFromTransport = false,
    },
    Veteran = {
        Level1 = 3,
        Level2 = 6,
        Level3 = 9,
        Level4 = 12,
        Level5 = 15,
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
            BallisticArc = 'RULEUBA_LowArc',
            CollideFriendly = false,
            Damage = 25,
            DamageRadius = 0,
            DamageType = 'Normal',
            DisplayName = 'BAR Raptor Spike Claws',
            FireTargetLayerCapsTable = {
                Air = 'Land|Water|Seabed',
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringRandomnessWhileMoving = 0,
            FiringTolerance = 3,
            Label = 'Claws',
            MaxRadius = 14,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            MuzzleVelocity = 26,
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
            RackRecoilDistance = 0.0,
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

with open(os.path.join(units_dir, "XRA0101_unit.bp"), "w", encoding="utf-8") as f:
    f.write(bp_content)

print("Updated XRA0101_unit.bp.")

# Copy texture to projectile folder
shutil.copyfile(
    os.path.join(units_dir, "XRA0101_Albedo.dds"),
    os.path.join(proj_dir, "XRA_Spike01_albedo.dds")
)

# ---------------------------------------------------------------------------
# 7. UPDATE SCRIPT (XRA0101_script.lua) WITH MANDIBLADES ATTACK
# ---------------------------------------------------------------------------
script_content = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon
local EffectTemplate = import('/lua/EffectTemplates.lua')

---@class RaptorWeapon : DefaultProjectileWeapon
local RaptorWeapon = ClassWeapon(DefaultProjectileWeapon) {
    FxMuzzleFlash = EffectTemplate.PhasicAutoGunMuzzleFlash,

    CreateProjectileAtMuzzle = function(self, muzzle)
        local proj = DefaultProjectileWeapon.CreateProjectileAtMuzzle(self, muzzle)
        self.unit:PlayMandibladesAttack()
        return proj
    end,
}

---@class XRA0101 : CWalkingLandUnit
XRA0101 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Claws = ClassWeapon(RaptorWeapon) {},
    },

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
        self.Rotators = {
            lforearm = CreateRotator(self, 'lforearm', 'y', 0, 600, 1000),
            rforearm = CreateRotator(self, 'rforearm', 'y', 0, 600, 1000),
            lblade = CreateRotator(self, 'lblade', 'y', 0, 600, 1000),
            rblade = CreateRotator(self, 'rblade', 'y', 0, 600, 1000),
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
        rot.lforearm:SetSpeed(600)
        rot.rforearm:SetGoal(140)
        rot.rforearm:SetSpeed(600)
        rot.lblade:SetGoal(140)
        rot.lblade:SetSpeed(600)
        rot.rblade:SetGoal(-140)
        rot.rblade:SetSpeed(600)

        WaitFor(rot.rblade)

        -- Smoothly open back up
        rot.lforearm:SetGoal(0)
        rot.lforearm:SetSpeed(140)
        rot.rforearm:SetGoal(0)
        rot.rforearm:SetSpeed(140)
        rot.lblade:SetGoal(0)
        rot.lblade:SetSpeed(140)
        rot.rblade:SetGoal(0)
        rot.rblade:SetSpeed(140)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        local bloodEmitters = {
            '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
            '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
            '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
        }
        for _, emit in bloodEmitters do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.0)
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
        local scale = 1.0 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in bloodEmitters do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}

TypeClass = XRA0101
"""

with open(os.path.join(units_dir, "XRA0101_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_content)

print("Updated XRA0101_script.lua with mandiblades attack animation.")

# ---------------------------------------------------------------------------
# 8. EXPORT ARCHIVE
# ---------------------------------------------------------------------------
zip_path = r"E:\Games\FAFMods\exports\RaptorFaction.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(mod_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(mod_dir))
            zipf.write(full_path, rel_path)

print(f"Mod successfully packaged and exported to: {zip_path}")
print("ALL TASKS COMPLETED!")
