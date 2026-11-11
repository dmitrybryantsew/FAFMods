import os, zipfile

mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
units_dir = os.path.join(mod_dir, "units", "XRA0101")

# 1. Update XRA0101_script.lua with arm slash rotators and valid FxMuzzleFlash
script_content = """--****************************************************************************
--**
--**  File     :  /mods/RaptorFaction/units/XRA0101/XRA0101_script.lua
--**  Summary  :  Beyond All Reason Raptor / Chicken T1 Swarmer
--**
--****************************************************************************

local WalkingLandUnit = import('/lua/defaultunits.lua').WalkingLandUnit
local SeraphimWeapons = import('/lua/seraphimweapons.lua')
local SDFOhCannon = SeraphimWeapons.SDFOhCannon
local EffectTemplate = import('/lua/EffectTemplates.lua')

XRA0101 = Class(WalkingLandUnit) {
    Weapons = {
        Claws = Class(SDFOhCannon) {
            FxMuzzleFlash = EffectTemplate.OhCannonMuzzleFlash,

            PlayFxMuzzleSequence = function(self, muzzle)
                SDFOhCannon.PlayFxMuzzleSequence(self, muzzle)
                -- Lunge both scythe arms forward when striking
                if self.unit.ArmRotL and self.unit.ArmRotR then
                    self.unit.ArmRotL:SetGoal(40)
                    self.unit.ArmRotR:SetGoal(40)
                end
            end,

            OnWeaponFired = function(self)
                SDFOhCannon.OnWeaponFired(self)
                -- Retract scythe arms back to ready position
                if self.unit.ArmRotL and self.unit.ArmRotR then
                    self.unit:ForkThread(function()
                        WaitSeconds(0.18)
                        if not self.unit:IsDead() then
                            self.unit.ArmRotL:SetGoal(0)
                            self.unit.ArmRotR:SetGoal(0)
                        end
                    end)
                end
            end,
        },
    },

    OnCreate = function(self)
        WalkingLandUnit.OnCreate(self)
        -- Create rotators for raptor scythe arms to lunge forward on each bite/slash
        self.ArmRotL = CreateRotator(self, 'lupperarm', 'x', 0, 360, 240)
        self.ArmRotR = CreateRotator(self, 'rupperarm', 'x', 0, 360, 240)
        self.Trash:Add(self.ArmRotL)
        self.Trash:Add(self.ArmRotR)
    end,
}

TypeClass = XRA0101
"""

with open(os.path.join(units_dir, "XRA0101_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_content)

# 2. Update XRA0101_unit.bp
bp_content = """UnitBlueprint {
    AI = {
        TargetBones = {
            'head',
            'body',
            'tail',
        },
    },
    Audio = {
        Destroyed = Sound {
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
                    NormalsName = '/mods/RaptorFaction/units/XRA0101/XRA0101_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0101/XRA0101_SpecTeam.dds',
                    LODCutoff = 300,
                    ShaderName = 'Insect',
                },
            },
        },
        PlaceholderMeshName = 'UXB0000',
        SpawnRandomRotation = true,
        UniformScale = 1.0,
    },
    Economy = {
        BuildCostEnergy = 220,
        BuildCostMass = 35,
        BuildRate = 1,
        BuildTime = 200,
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
        TurnRate = 180,
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
            DisplayName = 'Swarmer Acid Mandibles',
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
            MuzzleVelocity = 35,
            ProjectileId = '/projectiles/SDFOhCannon01/SDFOhCannon01_proj.bp',
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
            RackRecoilDistance = 0.45,
            RackReloadTimeout = 10,
            RackSalvoChargeTime = 0,
            RackSalvoReloadTime = 0,
            RackSalvoSize = 1,
            RackSlavedToTurret = false,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 2.0,
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
            TurretBonePitch = 'head',
            TurretBoneYaw = 'aimy1',
            TurretDualManipulators = false,
            TurretPitch = 0,
            TurretPitchRange = 55,
            TurretPitchSpeed = 160,
            TurretYaw = 0,
            TurretYawRange = 180,
            TurretYawSpeed = 160,
            Turreted = true,
            WeaponCategory = 'Direct Fire',
        },
    },
}
"""

with open(os.path.join(units_dir, "XRA0101_unit.bp"), "w", encoding="utf-8") as f:
    f.write(bp_content)

# Re-export zip archive
zip_path = r"E:\Games\FAFMods\exports\RaptorFaction.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(mod_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(mod_dir))
            zipf.write(full_path, rel_path)

print("Applied fixes to XRA0101_script.lua, XRA0101_unit.bp and re-exported RaptorFaction.zip!")
