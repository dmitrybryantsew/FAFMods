import os
import gzip
import struct
import math
import shutil
import zipfile
from scm_io import pad, pad_file, write_scm

mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
icons_dir = os.path.join(mod_dir, "icons", "units")
units_root = os.path.join(mod_dir, "units")

dir_xra0101 = os.path.join(units_root, "XRA0101")
dir_xra0102 = os.path.join(units_root, "XRA0102") # Basic Kinetic Spine Spire
dir_xra0110 = os.path.join(units_root, "XRA0110") # Burrowing Ambush Spire
dir_xra0209 = os.path.join(units_root, "XRA0209") # Volcanic Magma Worm
dir_xra_magmaproj = os.path.join(mod_dir, "projectiles", "XRA_MagmaShell01")

for d in [dir_xra0102, dir_xra0110, dir_xra0209, dir_xra_magmaproj]:
    os.makedirs(d, exist_ok=True)

# BAR Pool Reader
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
        p = os.path.join(r'P:\Games\Beyond-All-Reason\data\pool', md5_hex[:2], md5_hex[2:] + '.gz')
        with gzip.open(p, 'rb') as gz:
            return gz.read()
    return None

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

# 1. BUILD XRA0102: KINETIC CHITIN SPINE SPIRE (BASIC PD)
print("\nBuilding XRA0102: Kinetic Chitin Spine Spire...")
shutil.copyfile(os.path.join(units_root, "XRA0108", "XRA0108_lod0.scm"), os.path.join(dir_xra0102, "XRA0102_lod0.scm"))
shutil.copyfile(os.path.join(units_root, "XRA0108", "XRA0108_Aidle.sca"), os.path.join(dir_xra0102, "XRA0102_Aidle.sca"))
shutil.copyfile(os.path.join(units_root, "XRA0108", "XRA0108_Adeath01.sca"), os.path.join(dir_xra0102, "XRA0102_Adeath01.sca"))
albedo_basic = get_bar_file('unittextures/chicken_darkgreen_m_color.dds')
if not albedo_basic:
    albedo_basic = get_bar_file('unittextures/chicken_darkgreen_l_color.dds')
with open(os.path.join(dir_xra0102, "XRA0102_Albedo.dds"), "wb") as f:
    f.write(albedo_basic)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0102, "XRA0102_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0102, "XRA0102_SpecTeam.dds"))

icon_basic = get_bar_file('unitpics/raptors/raptor_turrets.dds')
if icon_basic:
    with open(os.path.join(dir_xra0102, "XRA0102_icon.dds"), "wb") as f:
        f.write(icon_basic)
    with open(os.path.join(icons_dir, "xra0102_icon.dds"), "wb") as f:
        f.write(icon_basic)

bp_xra0102 = """UnitBlueprint {
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
    },
    BuildIconSortPriority = 55,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
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
        ArmorType = 'Structure',
        Health = 1450,
        MaxHealth = 1450,
        RegenRate = 3,
    },
    Description = '<LOC xra0102_desc>Basic Kinetic Spine Spire',
    Display = {
        Abilities = {
            '<LOC ability_pointdefense>Point Defense',
            'Rapid Kinetic Needles',
            'Living Bio-Carapace Regen',
        },
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0102/XRA0102_Adeath01.sca',
                Weight = 100,
            },
        },
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0102/XRA0102_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0102/XRA0102_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0102/XRA0102_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0102/XRA0102_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 1.0,
    },
    Economy = {
        BuildCostEnergy = 1750,
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
            RULEUCC_RetaliateToggle = true,
            RULEUCC_Stop = true,
        },
        FactionName = 'Raptor',
        Icon = 'land',
        SelectionPriority = 5,
        TechLevel = 'RULEUTL_Basic',
        UnitName = '<LOC xra0102_name>Chitin Spine Spire',
        UnitWeight = 1,
    },
    Intel = {
        VisionRadius = 26,
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
            Damage = 35,
            DamageType = 'Normal',
            DisplayName = 'Kinetic Chitin Needler',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 2,
            Label = 'MainGun',
            MaxRadius = 26,
            MuzzleVelocity = 40,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_proj.bp',
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
            RackReloadTimeout = 10,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 2.5,
            TargetCheckInterval = 0.2,
            TargetPriorities = {
                'MOBILE TECH1',
                'MOBILE TECH2',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            TurretBoneMuzzle = 'flare',
            TurretBonePitch = 'head',
            TurretBoneYaw = 'aimy',
            TurretPitch = 0,
            TurretPitchRange = 60,
            TurretPitchSpeed = 90,
            TurretYaw = 0,
            TurretYawRange = 180,
            TurretYawSpeed = 90,
            Turreted = true,
            WeaponCategory = 'Direct Fire',
        },
    },
}
"""
with open(os.path.join(dir_xra0102, "XRA0102_unit.bp"), "w") as f:
    f.write(bp_xra0102)

script_xra0102 = """local CStructureUnit = import('/lua/cybranunits.lua').CStructureUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

XRA0102 = Class(CStructureUnit) {
    Weapons = {
        MainGun = Class(DefaultProjectileWeapon) {},
    },

    OnCreate = function(self)
        CStructureUnit.OnCreate(self)
        self.IdleAnim = CreateAnimator(self)
        self.IdleAnim:PlayAnim('/mods/RaptorFaction/units/XRA0102/XRA0102_Aidle.sca', true)
        self.Trash:Add(self.IdleAnim)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.0)
        end
        CStructureUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}

TypeClass = XRA0102
"""
with open(os.path.join(dir_xra0102, "XRA0102_script.lua"), "w") as f:
    f.write(script_xra0102)

# 2. BUILD XRA0110: BURROWING BIO-AMBUSH SPIRE (SUBMERGED CLOAKED MINE/TRAP)
print("\nBuilding XRA0110: Burrowing Bio-Ambush Spire...")
shutil.copyfile(os.path.join(units_root, "XRA0108", "XRA0108_lod0.scm"), os.path.join(dir_xra0110, "XRA0110_lod0.scm"))
shutil.copyfile(os.path.join(units_root, "XRA0108", "XRA0108_Aidle.sca"), os.path.join(dir_xra0110, "XRA0110_Aidle.sca"))
shutil.copyfile(os.path.join(units_root, "XRA0108", "XRA0108_Adeath01.sca"), os.path.join(dir_xra0110, "XRA0110_Adeath01.sca"))
albedo_burrow = get_bar_file('unittextures/chicken_darkgreen_s_color.dds')
if not albedo_burrow:
    albedo_burrow = get_bar_file('unittextures/chicken_darkgreen_l_color.dds')
with open(os.path.join(dir_xra0110, "XRA0110_Albedo.dds"), "wb") as f:
    f.write(albedo_burrow)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0110, "XRA0110_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0110, "XRA0110_SpecTeam.dds"))

icon_burrow = get_bar_file('unitpics/raptors/raptor_turrets.dds')
if icon_burrow:
    with open(os.path.join(dir_xra0110, "XRA0110_icon.dds"), "wb") as f:
        f.write(icon_burrow)
    with open(os.path.join(icons_dir, "xra0110_icon.dds"), "wb") as f:
        f.write(icon_burrow)

bp_xra0110 = """UnitBlueprint {
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
    },
    BuildIconSortPriority = 58,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'RAPTOR',
        'STRUCTURE',
        'DEFENSE',
        'DIRECTFIRE',
        'TECH1',
        'CLOAK',
        'STEALTH',
        'VISIBLETORECON',
        'RECLAIMABLE',
        'OVERLAYDIRECTFIRE',
        'SORTDEFENSE',
    },
    CollisionOffsetY = 0.2,
    Defense = {
        ArmorType = 'Structure',
        Health = 1100,
        MaxHealth = 1100,
        RegenRate = 4,
    },
    Description = '<LOC xra0110_desc>Subterranean Burrowing Ambush Spire',
    Display = {
        Abilities = {
            '<LOC ability_stealthfield>Subterranean Cloak',
            'Burst Bio-Spew Ambush (500 DMG)',
            'Living Bio-Carapace Regen',
        },
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0110/XRA0110_Adeath01.sca',
                Weight = 100,
            },
        },
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0110/XRA0110_Albedo.dds',
                    LODCutoff = 250,
                    MeshName = '/mods/RaptorFaction/units/XRA0110/XRA0110_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0110/XRA0110_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0110/XRA0110_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.9,
    },
    Economy = {
        BuildCostEnergy = 1400,
        BuildCostMass = 160,
        BuildTime = 180,
    },
    Footprint = {
        SizeX = 1,
        SizeZ = 1,
    },
    General = {
        Category = 'Defense',
        Classification = 'RULEUC_Weapon',
        CommandCaps = {
            RULEUCC_Attack = true,
            RULEUCC_RetaliateToggle = true,
            RULEUCC_Stop = true,
        },
        FactionName = 'Raptor',
        Icon = 'land',
        SelectionPriority = 5,
        TechLevel = 'RULEUTL_Basic',
        UnitName = '<LOC xra0110_name>Burrowing Ambush Spire',
        UnitWeight = 1,
    },
    Intel = {
        Cloak = true,
        RadarStealth = true,
        SonarStealth = true,
        VisionRadius = 18,
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.35,
    LifeBarSize = 0.8,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        FlattenSkirt = true,
        MotionType = 'RULEUMT_None',
        OccupyGround = true,
        SkirtOffsetX = 0,
        SkirtOffsetZ = 0,
        SkirtSizeX = 1,
        SkirtSizeZ = 1,
        TurnRate = 0,
    },
    SelectionSizeX = 0.8,
    SelectionSizeZ = 0.8,
    SelectionThickness = 0.6,
    SizeX = 0.9,
    SizeY = 1.6,
    SizeZ = 0.9,
    StrategicIconName = 'icon_structure1_directfire',
    StrategicIconSortPriority = 210,
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
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            Damage = 500,
            DamageRadius = 2.0,
            DamageType = 'Normal',
            DisplayName = 'Burrow Spew Ambush Burst',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 4,
            Label = 'MainGun',
            MaxRadius = 16,
            MuzzleVelocity = 35,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_BioMortar01/XRA_BioMortar01_proj.bp',
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
            RackReloadTimeout = 10,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 0.3,
            TargetCheckInterval = 0.1,
            TargetPriorities = {
                'COMMAND',
                'MOBILE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            TurretBoneMuzzle = 'flare',
            TurretBonePitch = 'head',
            TurretBoneYaw = 'aimy',
            TurretPitch = 0,
            TurretPitchRange = 80,
            TurretPitchSpeed = 120,
            TurretYaw = 0,
            TurretYawRange = 180,
            TurretYawSpeed = 120,
            Turreted = true,
            WeaponCategory = 'Direct Fire',
        },
    },
}
"""
with open(os.path.join(dir_xra0110, "XRA0110_unit.bp"), "w") as f:
    f.write(bp_xra0110)

script_xra0110 = """local CStructureUnit = import('/lua/cybranunits.lua').CStructureUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

XRA0110 = Class(CStructureUnit) {
    Weapons = {
        MainGun = Class(DefaultProjectileWeapon) {},
    },

    OnCreate = function(self)
        CStructureUnit.OnCreate(self)
        self:SetMaintenanceConsumptionActive()
        self:EnableUnitIntel('Cloak')
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.0)
        end
        CStructureUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}

TypeClass = XRA0110
"""
with open(os.path.join(dir_xra0110, "XRA0110_script.lua"), "w") as f:
    f.write(script_xra0110)

# 3. BUILD XRA0209: VOLCANIC MAGMA WORM (HEAVY AMPHIBIOUS / DEEP WORM)
print("\nBuilding XRA0209: Volcanic Magma Worm...")
s3o_bworm = get_bar_file('objects3d/raptors/raptor_worm_brown.s3o')
assert s3o_bworm, "raptor_worm_brown.s3o not found!"
convert_s3o_to_scm(s3o_bworm, os.path.join(dir_xra0209, "XRA0209_lod0.scm"))
shutil.copyfile(os.path.join(units_root, "XRA0208", "XRA0208_Aidle.sca"), os.path.join(dir_xra0209, "XRA0209_Aidle.sca"))
shutil.copyfile(os.path.join(units_root, "XRA0208", "XRA0208_Adeath01.sca"), os.path.join(dir_xra0209, "XRA0209_Adeath01.sca"))

albedo_bworm = get_bar_file('unittextures/chicken_brown_l_color.dds')
with open(os.path.join(dir_xra0209, "XRA0209_Albedo.dds"), "wb") as f:
    f.write(albedo_bworm)
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_NormalsTS.dds"), os.path.join(dir_xra0209, "XRA0209_NormalsTS.dds"))
shutil.copyfile(os.path.join(dir_xra0101, "XRA0101_SpecTeam.dds"), os.path.join(dir_xra0209, "XRA0209_SpecTeam.dds"))

icon_bworm = get_bar_file('unitpics/raptors/raptor_turrets.dds')
if icon_bworm:
    with open(os.path.join(dir_xra0209, "XRA0209_icon.dds"), "wb") as f:
        f.write(icon_bworm)
    with open(os.path.join(icons_dir, "xra0209_icon.dds"), "wb") as f:
        f.write(icon_bworm)

bp_xra0209 = """UnitBlueprint {
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
    },
    Buffs = {
        Regen = {
            Level1 = 6,
            Level2 = 12,
            Level3 = 18,
            Level4 = 24,
            Level5 = 30,
        },
    },
    BuildIconSortPriority = 63,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
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
        ArmorType = 'Structure',
        EconomyThreatLevel = 3,
        Health = 6200,
        MaxHealth = 6200,
        RegenRate = 10,
        SurfaceThreatLevel = 18,
    },
    Description = '<LOC xra0209_desc>Heavy Volcanic Magma Worm Defense',
    Display = {
        Abilities = {
            '<LOC ability_pointdefense>Heavy Point Defense',
            'High-Heat Magma Bile Mortar',
            'Living Bio-Carapace Regen',
        },
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0209/XRA0209_Adeath01.sca',
                Weight = 100,
            },
        },
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0209/XRA0209_Albedo.dds',
                    LODCutoff = 280,
                    MeshName = '/mods/RaptorFaction/units/XRA0209/XRA0209_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0209/XRA0209_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0209/XRA0209_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 1.05,
    },
    Economy = {
        BuildCostEnergy = 7500,
        BuildCostMass = 820,
        BuildTime = 880,
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
            RULEUCC_RetaliateToggle = true,
            RULEUCC_Stop = true,
        },
        FactionName = 'Raptor',
        Icon = 'land',
        SelectionPriority = 5,
        TechLevel = 'RULEUTL_Advanced',
        UnitName = '<LOC xra0209_name>Volcanic Magma Worm',
        UnitWeight = 1,
    },
    Intel = {
        VisionRadius = 36,
    },
    LifeBarHeight = 0.08,
    LifeBarOffset = 0.8,
    LifeBarSize = 1.8,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
            LAYER_Seabed = true,
        },
        DragCoefficient = 0.2,
        FlattenSkirt = true,
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
            Damage = 320,
            DamageRadius = 3.0,
            DamageType = 'Normal',
            DisplayName = 'Volcanic Magma Bile Mortar',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
                Seabed = 'Land|Water|Seabed',
            },
            FiringTolerance = 2,
            Label = 'MainGun',
            MaxRadius = 48,
            MinRadius = 5,
            MuzzleVelocity = 32,
            ProjectileId = '/mods/RaptorFaction/projectiles/XRA_MagmaShell01/XRA_MagmaShell01_proj.bp',
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
            RackReloadTimeout = 10,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1.0,
            TargetCheckInterval = 0.4,
            TargetPriorities = {
                'TECH3 MOBILE',
                'TECH2 MOBILE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            TurretBoneMuzzle = 'flare',
            TurretBonePitch = 'head',
            TurretBoneYaw = 'aimy',
            TurretPitch = 0,
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
with open(os.path.join(dir_xra0209, "XRA0209_unit.bp"), "w") as f:
    f.write(bp_xra0209)

script_xra0209 = """local CStructureUnit = import('/lua/cybranunits.lua').CStructureUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

XRA0209 = Class(CStructureUnit) {
    Weapons = {
        MainGun = Class(DefaultProjectileWeapon) {
            FxMuzzleFlash = {
                '/mods/RaptorFaction/effects/emitters/raptor_bio_flame_muzzle_01_emit.bp',
                '/effects/emitters/default_muzzle_flash_01_emit.bp',
            },
            FxMuzzleFlashScale = 0.8,
        },
    },

    OnCreate = function(self)
        CStructureUnit.OnCreate(self)
        self.IdleAnim = CreateAnimator(self)
        self.IdleAnim:PlayAnim('/mods/RaptorFaction/units/XRA0209/XRA0209_Aidle.sca', true)
        self.Trash:Add(self.IdleAnim)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(3.5)
        end
        CStructureUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}

TypeClass = XRA0209
"""
with open(os.path.join(dir_xra0209, "XRA0209_script.lua"), "w") as f:
    f.write(script_xra0209)

# Write Projectile for Magma Worm: XRA_MagmaShell01
bp_magmaproj = """ProjectileBlueprint {
    Audio = {
        Impact = Sound {
            Bank = 'Impacts',
            Cue = 'Cybran_Expl_Med_Impact',
            LodCutoff = 'Weapon_LodCutoff',
        },
        ImpactTerrain = Sound {
            Bank = 'Impacts',
            Cue = 'Cybran_Expl_Med_Impact',
            LodCutoff = 'Weapon_LodCutoff',
        },
        ImpactWater = Sound {
            Bank = 'Impacts',
            Cue = 'Impact_Water_Splash_CYBRAN',
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
                    AlbedoName = '/mods/RaptorFaction/units/XRA0209/XRA0209_Albedo.dds',
                    LODCutoff = 150,
                    MeshName = '/mods/RaptorFaction/projectiles/XRA_Spike01/XRA_Spike01_lod0.scm',
                    ShaderName = 'TMeshNoLighting',
                },
            },
        },
        StrategicIconSize = 1,
        UniformScale = 1.6,
    },
    General = {
        Category = 'Direct Fire',
        EntityCategory = {
            'RAPTOR',
            'PROJECTILE',
            'DIRECTFIRE',
        },
        Faction = 'Raptor',
    },
    Physics = {
        Acceleration = 0,
        DestroyOnWater = false,
        InitialSpeed = 32,
        LeadTarget = true,
        Lifetime = 5,
        MaxSpeed = 38,
        RotationalVelocity = 120,
        UseGravity = true,
        VelocityAlign = true,
    },
}
"""
with open(os.path.join(dir_xra_magmaproj, "XRA_MagmaShell01_proj.bp"), "w") as f:
    f.write(bp_magmaproj)

script_magmaproj = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile

---@class XRA_MagmaShell01 : SinglePolyTrailProjectile
XRA_MagmaShell01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/plasma_cannon_polytrail_04_emit.bp',
    PolyTrailOffset = 0,
    FxTrails = {
        '/effects/emitters/flamethrower_02_emit.bp',
    },
    FxTrailScale = 0.7,
    FxTrailOffset = 0,

    FxImpactTrajectoryAligned = false,

    FxImpactUnit = {
        '/effects/emitters/flash_01_emit.bp',
        '/effects/emitters/Small_test_fire.bp',
        '/effects/emitters/plasma_cannon_hit_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
        '/effects/emitters/destruction_land_hit_puff_01_emit.bp',
    },
    FxImpactProp = {
        '/effects/emitters/flash_01_emit.bp',
        '/effects/emitters/Small_test_fire.bp',
        '/effects/emitters/plasma_cannon_hit_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
        '/effects/emitters/destruction_land_hit_puff_01_emit.bp',
    },
    FxImpactLand = {
        '/effects/emitters/flash_01_emit.bp',
        '/effects/emitters/Small_test_fire.bp',
        '/effects/emitters/plasma_cannon_hit_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
        '/effects/emitters/destruction_land_hit_puff_01_emit.bp',
    },
    FxImpactWater = {
        '/effects/emitters/napalm_hvy_waterflash_emit.bp',
        '/effects/emitters/napalm_hvy_water_smoke_emit.bp',
    },
    FxImpactUnderWater = {
        '/effects/emitters/napalm_hvy_waterflash_emit.bp',
    },

    FxLandHitScale = 1.0,
    FxUnitHitScale = 1.0,
    FxPropHitScale = 1.0,
    FxWaterHitScale = 1.0,
}

TypeClass = XRA_MagmaShell01
"""
with open(os.path.join(dir_xra_magmaproj, "XRA_MagmaShell01_script.lua"), "w") as f:
    f.write(script_magmaproj)

# Repackage Mod
export_zip = os.path.join(os.path.dirname(__file__), "exports", "RaptorFaction.zip")
print(f"\nRepackaging full mod to {export_zip}...")
with zipfile.ZipFile(export_zip, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(mod_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(mod_dir))
            z.write(full_path, rel_path)

print("ALL BAR STRUCTURES ARE NOW 100% PORTED!")
