import os
import re
import struct
import math
from scm_io import pad, pad_file

MOD_DIR = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
WORKSPACE_DIR = r"E:\Games\FAFMods"

print("=================================================================")
print("Applying Bio-Mortar Artillery Salvo, Targeting & T3 Range Fixes")
print("=================================================================")

# ---------------------------------------------------------------------------
# 1. Update Projectile Blueprint: XRA_BioMortar01_proj.bp
# ---------------------------------------------------------------------------
proj_bp_path = os.path.join(MOD_DIR, "projectiles", "XRA_BioMortar01", "XRA_BioMortar01_proj.bp")
new_proj_bp = """ProjectileBlueprint {
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
        DestroyOnWater = false,
        LeadTarget = false,
        TurnRate = 360,
        VelocityAlign = true,
    },
}
"""

with open(proj_bp_path, "w", encoding="utf-8") as f:
    f.write(new_proj_bp)
print(f"[1/5] Updated {proj_bp_path}: fixed physics, removed 6s mid-air despawn, removed MaxSpeed clamp, added LeadTarget=false and TurnRate=360.")

# ---------------------------------------------------------------------------
# 2. Re-synthesize Recoil Animation: XRA0202_Afire.sca
#    (Keep wing flutter, remove pitch rotation on mortar barrel thor bones)
# ---------------------------------------------------------------------------
def euler_to_quat(rot_x, rot_y, rot_z):
    cx = math.cos(rot_x * 0.5)
    sx = math.sin(rot_x * 0.5)
    cy = math.cos(rot_y * 0.5)
    sy = math.sin(rot_y * 0.5)
    cz = math.cos(rot_z * 0.5)
    sz = math.sin(rot_z * 0.5)
    qw = cx * cy * cz + sx * cy * sz
    qx = sx * cy * cz - cx * sy * sz
    qy = cx * sy * cz + sx * cy * sz
    qz = cx * cy * sz - sx * math.cos(rot_x * 0.5) * 0 # standard quat
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
    print(f"[2/5] Created SCA: {filepath} ({num_frames} frames, {duration:.2f}s, size={file_size} bytes - OK, barrel pitch distortion removed)")

sca_path = os.path.join(MOD_DIR, "units", "XRA0202", "XRA0202_Afire.sca")
with open(sca_path, 'rb') as f:
    magic, ver, num_frames, dur, num_bones, names_off, links_off, data_off, frame_size = struct.unpack('<4s2If5I', f.read(36))
    f.seek(names_off)
    names_raw = f.read(links_off - names_off)
    names = [n.decode('ascii') for n in names_raw.split(b'\x00')[:num_bones]]
    f.seek(links_off)
    links = list(struct.unpack(f'<{num_bones}i', f.read(num_bones*4)))
    f.seek(data_off + 28 + 8)
    pos = {}
    for i in range(num_bones):
        px, py, pz, qw, qx, qy, qz = struct.unpack('<7f', f.read(28))
        pos[names[i]] = (px, py, pz)

num_frames = 16
dur = 0.8
frames = []
for f_idx in range(num_frames):
    t = f_idx / num_frames
    time_sec = t * dur
    rot = {}
    curve = math.sin(math.pi * t)
    # Flutter side wings only - thorax mortar bones are completely left to TurretManipulator
    rot['wingl'] = (0, curve * math.radians(25.0), 0)
    rot['wingr'] = (0, -curve * math.radians(25.0), 0)
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

save_sca_file(sca_path, num_frames, dur, names, links, frames)

# ---------------------------------------------------------------------------
# 3. Update Unit Script: XRA0202_script.lua
#    (Play recoil anim once on first shot of salvo, not 4x in 0.5s)
# ---------------------------------------------------------------------------
script_path = os.path.join(MOD_DIR, "units", "XRA0202", "XRA0202_script.lua")
new_script = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
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
        -- Play wing flutter recoil animation smoothly on the initial shot of each salvo
        if self.CurrentSalvoNumber == 1 and not unit.Dead then
            if not unit.FireAnim then
                unit.FireAnim = CreateAnimator(unit)
                unit.Trash:Add(unit.FireAnim)
            end
            unit.FireAnim:PlayAnim('/mods/RaptorFaction/units/XRA0202/XRA0202_Afire.sca', false)
            unit.FireAnim:SetRate(1.2)
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

with open(script_path, "w", encoding="utf-8") as f:
    f.write(new_script)
print(f"[3/5] Updated {script_path}: animation trigger now synchronized with salvo start.")

# ---------------------------------------------------------------------------
# 4. Update Unit Blueprint: XRA0202_unit.bp
#    (Give T3 Mobile Artillery Range: MaxRadius = 90, MinRadius = 15,
#     MuzzleVelocity = 26, MuzzleVelocityReduceDistance = 90,
#     ProjectileLifetime = 20, DamageRadius = 3.0, DamageToShields = 500,
#     FiringRandomness = 0.75, FiringTolerance = 1, LeadTarget = false)
# ---------------------------------------------------------------------------
bp_path = os.path.join(MOD_DIR, "units", "XRA0202", "XRA0202_unit.bp")
with open(bp_path, "r", encoding="utf-8") as f:
    bp_content = f.read()

# Replace weapon section in XRA0202_unit.bp
weapon_pattern = r"(Weapon\s*=\s*\{[\s\S]*?\n\s*\},?\n\})"
new_weapon = """Weapon = {
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
            DamageRadius = 3.0,
            DamageToShields = 500,
            DamageType = 'Normal',
            DisplayName = 'Bio-Acid Mortar',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water',
                Water = 'Land|Water|Seabed',
            },
            FiringRandomness = 0.75,
            FiringTolerance = 1,
            Label = 'MainGun',
            LeadTarget = false,
            MaxRadius = 90,
            MinRadius = 15,
            MuzzleSalvoDelay = 0.18,
            MuzzleSalvoSize = 4,
            MuzzleVelocity = 26,
            MuzzleVelocityReduceDistance = 90,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_BioMortar01/XRA_BioMortar01_proj.bp',
            ProjectileLifetime = 20,
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
            RackReloadTimeout = 0,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RackSlavedToTurret = false,
            RangeCategory = 'UWRC_IndirectFire',
            RateOfFire = 0.2,
            RenderFireClock = true,
            TargetCheckInterval = 1,
            TargetPriorities = {
                'ANTISHIELD',
                'SNIPER',
                '(ARTILLERY - TECH1)',
                'SHIELD',
                '(STRUCTURE * DEFENSE - ANTIMISSILE)',
                'STRUCTURE DEFENSE ANTIMISSILE',
                'TECH3 MOBILE',
                'TECH2 MOBILE',
                'TECH1 MOBILE',
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
}"""

bp_content_fixed = re.sub(weapon_pattern, new_weapon, bp_content)
with open(bp_path, "w", encoding="utf-8") as f:
    f.write(bp_content_fixed)
print(f"[4/5] Updated {bp_path}: T3 mobile artillery range 90, MinRadius 15, MuzzleVelocity 26, tolerance 1, LeadTarget=false.")

# ---------------------------------------------------------------------------
# 5. Keep Workspace Generators & Unit Database in Sync
# ---------------------------------------------------------------------------
# Update build_raptor_expansion_complete.py
build_script_path = os.path.join(WORKSPACE_DIR, "build_raptor_expansion_complete.py")
if os.path.exists(build_script_path):
    with open(build_script_path, "r", encoding="utf-8") as f:
        b_content = f.read()

    # Disable thor_recoil in build_raptor_expansion_complete.py
    old_thor = """thor_recoil = {
    'thor1': 16.0,
    'thor2': 10.0,
    'thor3': 6.0,
    'thor4': -3.0,
    'thor5': -6.0,
    'thor6': -4.0,
    'thor7': -5.0,
}"""
    new_thor = """thor_recoil = {} # Thorax bones left unrotated so turret manipulator has 100% targeting stability"""
    if old_thor in b_content:
        b_content = b_content.replace(old_thor, new_thor)

    # Update XRA0202 script in generator
    b_content = b_content.replace(
        "if not unit.Dead then\n            if not unit.FireAnim then",
        "if self.CurrentSalvoNumber == 1 and not unit.Dead then\n            if not unit.FireAnim then"
    )

    # Update XRA0202 blueprint in generator
    b_content = b_content.replace("MaxRadius = 64,\n            MinRadius = 8,", "MaxRadius = 90,\n            MinRadius = 15,")
    b_content = b_content.replace("MuzzleVelocity = 22,\n            MuzzleVelocityReduceDistance = 64,", "MuzzleVelocity = 26,\n            MuzzleVelocityReduceDistance = 90,\n            ProjectileLifetime = 20,\n            LeadTarget = false,")
    b_content = b_content.replace("FiringTolerance = 3,", "FiringTolerance = 1,")
    b_content = b_content.replace("DamageRadius = 2.5,", "DamageRadius = 3.0,\n            DamageToShields = 500,")

    with open(build_script_path, "w", encoding="utf-8") as f:
        f.write(b_content)
    print(f"[5/5] Synced build_raptor_expansion_complete.py generator script.")

print("\nAll Bio-Mortar Artillery fixes applied successfully!")
