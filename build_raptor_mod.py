import os, shutil, zipfile

mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
units_dir = os.path.join(mod_dir, "units", "XRA0101")
os.makedirs(units_dir, exist_ok=True)

# 1. mod_info.lua
mod_info_content = """name = "Raptor Swarm Faction (Test)"
version = 1
copyright = "Beyond All Reason & FAF Communities"
description = "Adds the biological Raptor/Chicken Swarm faction and the T1 Raptor Swarmer unit. Spawnable in F2 cheat menu under 'Raptor' or 'XRA0101'."
author = "BAR & FAF"
uid = "raptor-swarm-test-faf-0001"
selectable = true
enabled = true
exclusive = false
ui_only = false
requires = {}
"""

with open(os.path.join(mod_dir, "mod_info.lua"), "w", encoding="utf-8") as f:
    f.write(mod_info_content)

# 2. XRA0101_script.lua
script_content = """--****************************************************************************
--**
--**  File     :  /mods/RaptorFaction/units/XRA0101/XRA0101_script.lua
--**  Summary  :  Raptor / Chicken T1 Biological Swarmer
--**
--****************************************************************************

local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local CybranWeaponsFile = import('/lua/cybranweapons.lua')
local CDFLaserHeavyWeapon = CybranWeaponsFile.CDFLaserHeavyWeapon

XRA0101 = Class(CWalkingLandUnit) {
    Weapons = {
        LaserArms = Class(CDFLaserHeavyWeapon) {
        },
    },

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
    end,
}

TypeClass = XRA0101
"""

with open(os.path.join(units_dir, "XRA0101_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_content)

# 3. XRA0101_unit.bp
bp_content = """UnitBlueprint {
    AI = {
        TargetBones = {
            'Torso',
        },
    },
    Audio = {
        AmbientMove = Sound {
            Bank = 'URL',
            Cue = 'URL0107_Move_Loop',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Destroyed = Sound {
            Bank = 'URLDestroy',
            Cue = 'URL_Destroy_Land',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        StartMove = Sound {
            Bank = 'URL',
            Cue = 'URL0107_Move_Start',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        StopMove = Sound {
            Bank = 'URL',
            Cue = 'URL0107_Move_Stop',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        UISelection = Sound {
            Bank = 'Interface',
            Cue = 'Cybran_Select_Bot',
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
    CollisionOffsetY = 0.15,
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
            'Biological Swarm Beast',
        },
        AnimationDeath = {
            {
                Animation = '/mods/RaptorFaction/units/XRA0101/XRA0101_Adeath01.sca',
                AnimationRateMax = 1.3,
                AnimationRateMin = 0.9,
                Weight = 1,
            },
            {
                Animation = '/mods/RaptorFaction/units/XRA0101/XRA0101_Adeath02.sca',
                AnimationRateMax = 1.3,
                AnimationRateMin = 0.9,
                Weight = 1,
            },
        },
        AnimationWalk = '/mods/RaptorFaction/units/XRA0101/XRA0101_Awalk.sca',
        AnimationWalkRate = 8.5,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0101/XRA0101_Albedo.dds',
                    NormalsName = '/mods/RaptorFaction/units/XRA0101/XRA0101_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0101/XRA0101_SpecTeam.dds',
                    LODCutoff = 250,
                    ShaderName = 'Insect',
                },
            },
        },
        MovementEffects = {
            Land = {
                Effects = {
                    {
                        Bones = {
                            'URL0107',
                        },
                        Type = 'GroundKickup01',
                    },
                },
            },
        },
        PlaceholderMeshName = 'UXB0000',
        SpawnRandomRotation = true,
        UniformScale = 0.135,
    },
    Economy = {
        BuildCostEnergy = 220,
        BuildCostMass = 35,
        BuildRate = 1,
        BuildTime = 200,
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
    LifeBarOffset = 0.35,
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
        MaxAcceleration = 4.2,
        MaxBrake = 4.2,
        MaxSpeed = 4.2,
        MaxSpeedReverse = 0,
        MaxSteerForce = 10,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        TurnRadius = 1,
        TurnRate = 140,
    },
    SelectionCenterOffsetX = 0,
    SelectionCenterOffsetZ = 0,
    SelectionSizeX = 0.50,
    SelectionSizeZ = 0.55,
    SelectionThickness = 0.65,
    SizeX = 0.6,
    SizeY = 0.45,
    SizeZ = 0.7,
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
                    Bank = 'URLWeapon',
                    Cue = 'URL0107_Laser_Auto',
                    LodCutoff = 'Weapon_LodCutoff',
                },
            },
            BallisticArc = 'RULEUBA_LowArc',
            CollideFriendly = false,
            Damage = 16,
            DamageRadius = 0,
            DamageType = 'Normal',
            DisplayName = 'Swarmer Claws',
            FireTargetLayerCapsTable = {
                Air = 'Land|Water|Seabed',
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringRandomnessWhileMoving = 0,
            FiringTolerance = 2,
            Label = 'LaserArms',
            MaxRadius = 16,
            MuzzleSalvoDelay = 0,
            MuzzleSalvoSize = 1,
            MuzzleVelocity = 35,
            ProjectileId = '/projectiles/CDFLaserHeavy01/CDFLaserHeavy01_proj.bp',
            ProjectileLifetimeUsesMultiplier = 1.15,
            ProjectilesPerOnFire = 1,
            RackBones = {
                {
                    MuzzleBones = {
                        'Turret_Muzzle_01',
                    },
                    RackBone = 'Turret_Barrel',
                },
                {
                    MuzzleBones = {
                        'Turret_Muzzle_02',
                    },
                    RackBone = 'Turret_Barrel',
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
            RateOfFire = 2.5,
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
            TurretBoneMuzzle = 'Turret_Muzzle_01',
            TurretBonePitch = 'Turret_Barrel',
            TurretBoneYaw = 'Torso',
            TurretDualManipulators = false,
            TurretPitch = 0,
            TurretPitchRange = 40,
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

with open(os.path.join(units_dir, "XRA0101_unit.bp"), "w", encoding="utf-8") as f:
    f.write(bp_content)

# Also create export package in workspace
export_dir = r"E:\Games\FAFMods\exports"
os.makedirs(export_dir, exist_ok=True)
zip_path = os.path.join(export_dir, "RaptorFaction.zip")

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(mod_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(mod_dir))
            zipf.write(full_path, rel_path)

print(f"Mod files written to {mod_dir}")
print(f"Zip exported to {zip_path}")
