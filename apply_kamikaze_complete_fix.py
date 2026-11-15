import os
import re
import shutil
import zipfile

mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
units_dir = os.path.join(mod_dir, "units")
export_zip = r"E:\Games\FAFMods\exports\RaptorFaction.zip"

print("=================================================================")
print("=== APPLYING COMPLETE CYBRAN BEETLE (XRL0302) KAMIKAZE FIXES ===")
print("=================================================================")

# ===========================================================================
# 1. XRA0103: VOLATILE ACID TICK (T1 Land Bio-Acid Suicide)
# ===========================================================================
print("\n[1/5] Updating XRA0103 (Volatile Acid Tick)...")

bp_xra0103 = """UnitBlueprint {
    Audio = {
        UISelection = Sound {
            Bank = 'Interface',
            Cue = 'Cybran_Select_Bot',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Destroyed = Sound {
            Bank = 'Raptor_Bio_Bomb',
            Cue = 'Attack',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Killed = Sound {
            Bank = 'Raptor_Bio_Bomb',
            Cue = 'Attack',
            LodCutoff = 'UnitMove_LodCutoff',
        },
    },
    Buffs = {
        Regen = {
            Level1 = 1,
            Level2 = 2,
            Level3 = 3,
        },
    },
    BuildIconSortPriority = 25,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYRAPTORHIVE',
        'RAPTOR',
        'MOBILE',
        'LAND',
        'TECH1',
        'KAMIKAZE',
        'BOMB',
        'DIRECTFIRE',
        'SHOWATTACKRETICLE',
        'AMPHIBIOUS',
        'VISIBLETORECON',
        'RECLAIMABLE',
    },
    CollisionOffsetY = 0,
    CollisionOffsetZ = 0,
    Defense = {
        ArmorType = 'Normal',
        Health = 110,
        MaxHealth = 110,
        RegenRate = 0.5,
    },
    Description = '<LOC xra0103_desc>Suicide Kamikaze Acid Bomb',
    Display = {
        Abilities = {
            '<LOC ability_suicideweapon>Suicide Weapon',
        },
        AnimationWalk = '/mods/RaptorFaction/units/XRA0103/XRA0103_Awalk.sca',
        AnimationWalkRate = 2.4,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0103/XRA0103_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0103/XRA0103_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0103/XRA0103_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0103/XRA0103_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.7,
    },
    Economy = {
        BuildCostEnergy = 350,
        BuildCostMass = 45,
        BuildTime = 160,
    },
    General = {
        Category = 'Direct Fire',
        Classification = 'RULEUC_MilitaryVehicle',
        CommandCaps = {
            RULEUCC_Attack = true,
            RULEUCC_CallCycle = false,
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
        FactionName = 'Raptor',
        Icon = 'land',
        InstantDeathOnSelfDestruct = true,
        OrderOverrides = {
            RULEUTC_ProductionToggle = {
                bitmapId = 'overcharge',
                helpText = 'Detonate',
            },
        },
        ToggleCaps = {
            RULEUTC_ProductionToggle = true,
        },
        UnitName = '<LOC xra0103_name>Volatile Acid Tick',
    },
    Intel = {
        VisionRadius = 18,
    },
    Interface = {
        HelpText = '<LOC xra0103_help>High-speed suicide kamikaze insect that detonates in a violent acid explosion on contact.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.55,
    LifeBarSize = 0.65,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 5.0,
        MaxBrake = 5.0,
        MaxSpeed = 5.2,
        MaxSpeedReverse = 0,
        MaxSteerForce = 15,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        RotateOnSpot = true,
        RotateOnSpotThreshold = 0.1,
        TurnRadius = 0,
        TurnRate = 220,
    },
    SelectionSizeX = 0.45,
    SelectionSizeZ = 0.6,
    SelectionThickness = 0.65,
    SizeX = 0.55,
    SizeY = 0.6,
    SizeZ = 0.85,
    StrategicIconName = 'raptorfaction/icon_raptor_kamikaze_t1',
    StrategicIconSortPriority = 135,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            CollideFriendly = false,
            Damage = 0,
            DamageFriendly = false,
            DamageRadius = 0,
            DamageType = 'Normal',
            DisplayName = 'Suicide Acid Detonation Trigger',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 180,
            Label = 'Suicide',
            MaxRadius = 4.0,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1,
            SlavedToBody = true,
            TargetCheckInterval = 0.1,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'MOBILE',
                'STRUCTURE DEFENSE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            Turreted = false,
            WeaponCategory = 'Kamikaze',
        },
        {
            AboveWaterTargetsOnly = true,
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            Damage = 750,
            DamageFriendly = true,
            DamageRadius = 3.5,
            DamageType = 'Normal',
            DisplayName = 'Death Acid Detonation',
            FireOnDeath = true,
            FireTargetLayerCapsTable = {
                Air = 'Air|Land|Seabed|Water',
                Land = 'Air|Land|Seabed|Water',
                Water = 'Air|Land|Water',
            },
            FiringTolerance = 2,
            IgnoreIfDisabled = true,
            Label = 'DeathWeapon',
            ManualFire = false,
            MaxRadius = 3.5,
            MuzzleVelocity = 0,
            RackBones = {
                {
                    MuzzleBones = { 0 },
                    RackBone = 0,
                },
            },
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1,
            SalvoSize = 1,
            SlavedToBody = true,
            TargetRestrictDisallow = 'UNTARGETABLE',
            Turreted = false,
            WeaponCategory = 'Direct Fire',
        },
    },
}
"""
with open(os.path.join(units_dir, "XRA0103", "XRA0103_unit.bp"), "w", encoding="utf-8") as f:
    f.write(bp_xra0103)

script_xra0103 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local Weapon = import('/lua/sim/weapon.lua').Weapon
local DamageArea = DamageArea
local CreateEmitterAtEntity = CreateEmitterAtEntity
local ForkThread = ForkThread
local WaitTicks = WaitTicks
local IsDestroyed = IsDestroyed

local AcidKamikazeEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_acid_splash_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_puddle_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_bubbles_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_steam_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
}

---@class XRA0103_SuicideWeapon : Weapon
local XRA0103_SuicideWeapon = ClassWeapon(Weapon) {
    OnFire = function(self)
        local unit = self.unit
        if not unit.Dead and not unit.Detonated then
            unit:Kill()
        end
    end,
}

---@class XRA0103_DeathAcidWeapon : Weapon
local XRA0103_DeathAcidWeapon = ClassWeapon(Weapon) {
    OnCreate = function(self)
        Weapon.OnCreate(self)
        self:SetWeaponEnabled(false)
        self:ChangeMaxRadius(self:GetDamageTable().DamageRadius)
    end,

    Fire = function(self)
        local unit = self.unit
        if not unit or unit.Detonated then return end
        unit.Detonated = true

        local position = unit:GetPosition()
        local damageTable = self:GetDamageTable()
        local radius = damageTable.DamageRadius
        local damage = damageTable.DamageAmount
        local dType = damageTable.DamageType or 'Normal'
        local dFriendly = damageTable.DamageFriendly or false

        -- 1. Direct blast damage
        DamageArea(unit, position, radius, damage, dType, dFriendly)

        -- 2. Visual green acid splatter effects
        local army = unit.Army
        for _, emit in AcidKamikazeEffects do
            CreateEmitterAtEntity(unit, army, emit):ScaleEmitter(2.0)
        end

        -- 3. Sound and instant destruction (prevents second death or delayed explosion)
        unit:PlayUnitSound('Destroyed')
        unit:Destroy()
    end,
}

---@class XRA0103 : CWalkingLandUnit
XRA0103 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Suicide = ClassWeapon(XRA0103_SuicideWeapon) {},
        DeathWeapon = ClassWeapon(XRA0103_DeathAcidWeapon) {},
    },

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
        self:StartTrackTargetThread()
    end,

    StartTrackTargetThread = function(self)
        local navigator = self:GetNavigator()
        if not navigator then return end
        local weapon = self:GetWeaponByLabel('Suicide')
        if not weapon then return end

        return self.Trash:Add(
            ForkThread(self.TrackTargetThread, self, navigator, weapon)
        )
    end,

    TrackTargetThread = function(self, navigator, weapon)
        local lastTarget
        while not IsDestroyed(self) and not IsDestroyed(weapon) do
            local command = self:GetCommandQueue()[1]
            local target
            if command and command.commandType == 10 then
                target = command.target
            end
            if not target then
                lastTarget = nil
                navigator:SetSpeedThroughGoal(false)
            elseif target ~= lastTarget then
                lastTarget = target
                navigator:SetSpeedThroughGoal(true)
            end

            WaitTicks(5)
        end
    end,

    OnProductionPaused = function(self)
        -- Manual Detonate UI Button
        local weapon = self:GetWeaponByLabel('Suicide')
        if weapon then
            weapon:FireWeapon()
        elseif not self.Dead then
            self:Kill()
        end
    end,

    DoDeathWeapon = function(self)
        if self:IsBeingBuilt() then return end
        CWalkingLandUnit.DoDeathWeapon(self)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        if not self.Detonated then
            local deathWeapon = self:GetWeaponByLabel('DeathWeapon')
            if deathWeapon then
                deathWeapon:Fire()
            end
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        -- Suppressed; bio-acid visuals handled by DeathWeapon
    end,
}

TypeClass = XRA0103
"""
with open(os.path.join(units_dir, "XRA0103", "XRA0103_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_xra0103)


# ===========================================================================
# 2. XRA0203: BIO-EMP SHOCK TICK (T2 Land Bio-EMP Suicide)
# ===========================================================================
print("\n[2/5] Updating XRA0203 (Bio-EMP Shock Tick)...")

bp_xra0203 = """UnitBlueprint {
    Audio = {
        UISelection = Sound {
            Bank = 'Interface',
            Cue = 'Cybran_Select_Bot',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Destroyed = Sound {
            Bank = 'Raptor_EMP_Launch',
            Cue = 'Attack',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Killed = Sound {
            Bank = 'Raptor_EMP_Launch',
            Cue = 'Attack',
            LodCutoff = 'UnitMove_LodCutoff',
        },
    },
    Buffs = {
        Stun = {
            Add = {
                OnDeath = true,
                OnImpact = true,
            },
            AppliedToTarget = false,
            BuffType = 'STUN',
            Duration = 6,
            Radius = 5.0,
            TargetAllow = 'ALLUNITS',
            TargetDisallow = 'WALL',
        },
    },
    BuildIconSortPriority = 35,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'BUILTBYRAPTORHIVE',
        'RAPTOR',
        'MOBILE',
        'LAND',
        'TECH2',
        'KAMIKAZE',
        'BOMB',
        'DIRECTFIRE',
        'SHOWATTACKRETICLE',
        'AMPHIBIOUS',
        'VISIBLETORECON',
        'RECLAIMABLE',
    },
    CollisionOffsetY = 0,
    CollisionOffsetZ = 0,
    Defense = {
        ArmorType = 'Normal',
        Health = 280,
        MaxHealth = 280,
        RegenRate = 1.0,
    },
    Description = '<LOC xra0203_desc>EMP Shock Kamikaze & Shield Breaker',
    Display = {
        Abilities = {
            '<LOC ability_suicideweapon>Suicide Weapon',
            '<LOC ability_stun>EMP Weapon',
        },
        AnimationWalk = '/mods/RaptorFaction/units/XRA0203/XRA0203_Awalk.sca',
        AnimationWalkRate = 2.4,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0203/XRA0203_Albedo.dds',
                    LODCutoff = 260,
                    MeshName = '/mods/RaptorFaction/units/XRA0203/XRA0203_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0203/XRA0203_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0203/XRA0203_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.8,
    },
    Economy = {
        BuildCostEnergy = 1400,
        BuildCostMass = 180,
        BuildTime = 600,
    },
    General = {
        Category = 'Direct Fire',
        Classification = 'RULEUC_MilitaryVehicle',
        CommandCaps = {
            RULEUCC_Attack = true,
            RULEUCC_CallCycle = false,
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
        FactionName = 'Raptor',
        Icon = 'land',
        InstantDeathOnSelfDestruct = true,
        OrderOverrides = {
            RULEUTC_ProductionToggle = {
                bitmapId = 'overcharge',
                helpText = 'Detonate',
            },
        },
        ToggleCaps = {
            RULEUTC_ProductionToggle = true,
        },
        UnitName = '<LOC xra0203_name>Bio-EMP Shock Tick',
    },
    Intel = {
        VisionRadius = 20,
    },
    Interface = {
        HelpText = '<LOC xra0203_help>EMP Kamikaze tick that discharges a high-voltage EMP shockwave collapsing shields and stunning enemy units.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.55,
    LifeBarSize = 0.75,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 4.8,
        MaxBrake = 4.8,
        MaxSpeed = 5.0,
        MaxSpeedReverse = 0,
        MaxSteerForce = 15,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        RotateOnSpot = true,
        RotateOnSpotThreshold = 0.1,
        TurnRadius = 0,
        TurnRate = 200,
    },
    SelectionSizeX = 0.5,
    SelectionSizeZ = 0.7,
    SelectionThickness = 0.65,
    SizeX = 0.6,
    SizeY = 0.65,
    SizeZ = 0.9,
    StrategicIconName = 'raptorfaction/icon_raptor_emp_kamikaze',
    StrategicIconSortPriority = 135,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            CollideFriendly = false,
            Damage = 0,
            DamageFriendly = false,
            DamageRadius = 0,
            DamageType = 'Normal',
            DisplayName = 'Bio-EMP Detonation Trigger',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 180,
            Label = 'Suicide',
            MaxRadius = 4.5,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1,
            SlavedToBody = true,
            TargetCheckInterval = 0.1,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'SHIELD',
                'TECH3 MOBILE',
                'TECH2 MOBILE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            Turreted = false,
            WeaponCategory = 'Kamikaze',
        },
        {
            AboveWaterTargetsOnly = true,
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            Damage = 450,
            DamageToShields = 2500,
            DamageFriendly = false,
            DamageRadius = 5.0,
            DamageType = 'EMP',
            DisplayName = 'Death EMP Detonation',
            FireOnDeath = true,
            FireTargetLayerCapsTable = {
                Air = 'Air|Land|Seabed|Water',
                Land = 'Air|Land|Seabed|Water',
                Water = 'Air|Land|Water',
            },
            FiringTolerance = 2,
            IgnoreIfDisabled = true,
            Label = 'DeathWeapon',
            ManualFire = false,
            MaxRadius = 5.0,
            MuzzleVelocity = 0,
            RackBones = {
                {
                    MuzzleBones = { 0 },
                    RackBone = 0,
                },
            },
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1,
            SalvoSize = 1,
            SlavedToBody = true,
            TargetRestrictDisallow = 'UNTARGETABLE',
            Turreted = false,
            WeaponCategory = 'Direct Fire',
        },
    },
}
"""
with open(os.path.join(units_dir, "XRA0203", "XRA0203_unit.bp"), "w", encoding="utf-8") as f:
    f.write(bp_xra0203)

script_xra0203 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local Weapon = import('/lua/sim/weapon.lua').Weapon
local DamageArea = DamageArea
local CreateEmitterAtEntity = CreateEmitterAtEntity
local ForkThread = ForkThread
local WaitTicks = WaitTicks
local IsDestroyed = IsDestroyed

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
    '/effects/emitters/cybran_empgrenade_hit_01_emit.bp',
    '/effects/emitters/cybran_empgrenade_hit_02_emit.bp',
    '/effects/emitters/build_sparks_blue_02_emit.bp',
}

---@class XRA0203_SuicideWeapon : Weapon
local XRA0203_SuicideWeapon = ClassWeapon(Weapon) {
    OnFire = function(self)
        local unit = self.unit
        if not unit.Dead and not unit.Detonated then
            unit:Kill()
        end
    end,
}

---@class XRA0203_DeathEMPWeapon : Weapon
local XRA0203_DeathEMPWeapon = ClassWeapon(Weapon) {
    OnCreate = function(self)
        Weapon.OnCreate(self)
        self:SetWeaponEnabled(false)
        self:ChangeMaxRadius(self:GetDamageTable().DamageRadius)
    end,

    Fire = function(self)
        local unit = self.unit
        if not unit or unit.Detonated then return end
        unit.Detonated = true

        local position = unit:GetPosition()
        local damageTable = self:GetDamageTable()
        local radius = damageTable.DamageRadius or 5.0
        local damage = damageTable.DamageAmount or 450

        -- 1. Direct blast damage
        DamageArea(unit, position, radius, damage, 'Normal', false)

        -- 2. Anti-shield EMP burst (collapses shields in 5.0m blast radius)
        DamageArea(unit, position, radius, 2500, 'FAF_AntiShield', false)

        -- 3. Stun all enemy mobile and structure units
        local brain = unit:GetAIBrain()
        if brain then
            local targets = brain:GetUnitsAroundPoint(categories.MOBILE + categories.STRUCTURE, position, radius, 'Enemy')
            for _, t in targets do
                if not t.Dead then
                    t:SetStunned(6.0)
                    if t.MyShield and t.MyShield:IsOn() then
                        t.MyShield:ApplyDamage(2500)
                    end
                end
            end
        end

        -- 4. Blue EMP sparks + bio gore explosion emitters
        local army = unit.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(unit, army, emit):ScaleEmitter(2.5)
        end

        -- 5. Sound and instant destruction
        unit:PlayUnitSound('Destroyed')
        unit:Destroy()
    end,
}

---@class XRA0203 : CWalkingLandUnit
XRA0203 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Suicide = ClassWeapon(XRA0203_SuicideWeapon) {},
        DeathWeapon = ClassWeapon(XRA0203_DeathEMPWeapon) {},
    },

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
        self:StartTrackTargetThread()
    end,

    StartTrackTargetThread = function(self)
        local navigator = self:GetNavigator()
        if not navigator then return end
        local weapon = self:GetWeaponByLabel('Suicide')
        if not weapon then return end

        return self.Trash:Add(
            ForkThread(self.TrackTargetThread, self, navigator, weapon)
        )
    end,

    TrackTargetThread = function(self, navigator, weapon)
        local lastTarget
        while not IsDestroyed(self) and not IsDestroyed(weapon) do
            local command = self:GetCommandQueue()[1]
            local target
            if command and command.commandType == 10 then
                target = command.target
            end
            if not target then
                lastTarget = nil
                navigator:SetSpeedThroughGoal(false)
            elseif target ~= lastTarget then
                lastTarget = target
                navigator:SetSpeedThroughGoal(true)
            end

            WaitTicks(5)
        end
    end,

    OnProductionPaused = function(self)
        -- Manual Detonate UI Button
        local weapon = self:GetWeaponByLabel('Suicide')
        if weapon then
            weapon:FireWeapon()
        elseif not self.Dead then
            self:Kill()
        end
    end,

    DoDeathWeapon = function(self)
        if self:IsBeingBuilt() then return end
        CWalkingLandUnit.DoDeathWeapon(self)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        if not self.Detonated then
            local deathWeapon = self:GetWeaponByLabel('DeathWeapon')
            if deathWeapon then
                deathWeapon:Fire()
            end
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        -- Handled by DeathWeapon
    end,
}

TypeClass = XRA0203
"""
with open(os.path.join(units_dir, "XRA0203", "XRA0203_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_xra0203)


# ===========================================================================
# 3. XRA0213: BIO-DIVE KAMIKAZE TICK (T2 Air Dive-Bomb Suicide)
# ===========================================================================
print("\n[3/5] Updating XRA0213 (Bio-Dive Kamikaze Tick)...")

bp_xra0213 = """UnitBlueprint {
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
            Level1 = 1,
            Level2 = 2,
            Level3 = 3,
            Level4 = 4,
            Level5 = 5,
        },
    },
    BuildIconSortPriority = 35,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'AIR',
        'MOBILE',
        'HIGHPRIAIR',
        'KAMIKAZE',
        'BOMB',
        'DIRECTFIRE',
        'SHOWATTACKRETICLE',
        'TECH2',
        'BUILTBYRAPTORHIVE',
        'RAPTOR',
        'VISIBLETORECON',
        'RECLAIMABLE',
    },
    Defense = {
        ArmorType = 'Light',
        Health = 480,
        MaxHealth = 480,
        RegenRate = 1.0,
    },
    Description = '<LOC xra0213_desc>Air Dive-Bomb Suicide Tick',
    Display = {
        Abilities = {
            '<LOC ability_suicideweapon>Suicide Weapon',
        },
        AnimationWalk = '/mods/RaptorFaction/units/XRA0213/XRA0213_Afly01.sca',
        AnimationWalkRate = 2.0,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0213/XRA0213_Albedo.dds',
                    LODCutoff = 215,
                    MeshName = '/mods/RaptorFaction/units/XRA0213/XRA0213_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0213/XRA0213_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0213/XRA0213_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.055,
    },
    Economy = {
        BuildCostEnergy = 2800,
        BuildCostMass = 140,
        BuildTime = 750,
    },
    General = {
        Category = 'Air',
        Classification = 'RULEUC_MilitaryVehicle',
        CommandCaps = {
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
        },
        FactionName = 'Raptor',
        Icon = 'air',
        InstantDeathOnSelfDestruct = true,
        OrderOverrides = {
            RULEUTC_ProductionToggle = {
                bitmapId = 'overcharge',
                helpText = 'Detonate',
            },
        },
        ToggleCaps = {
            RULEUTC_ProductionToggle = true,
        },
        TechLevel = 'RULEUTL_Advanced',
        UnitName = '<LOC xra0213_name>Bio-Dive Kamikaze Tick',
        UnitWeight = 1,
    },
    Intel = {
        VisionRadius = 24,
    },
    Interface = {
        HelpText = '<LOC xra0213_help>Air Dive-Bomb Suicide Tick that dives onto enemies at high speed, detonating in a massive biological burst.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.5,
    LifeBarSize = 0.6,
    Physics = {
        BankingSlope = 0.5,
        BuildOnLayerCaps = {
            LAYER_Air = true,
            LAYER_Land = false,
            LAYER_Orbit = false,
            LAYER_Seabed = false,
            LAYER_Sub = false,
            LAYER_Water = false,
        },
        DragCoefficient = 0.2,
        Elevation = 8,
        FuelRechargeRate = 150,
        FuelUseTime = 1500,
        GroundElevation = 8,
        MaxSpeedSizeControl = 0.3,
        MaxAcceleration = 3.5,
        MaxBrake = 3.5,
        MaxSpeed = 15.0,
        MaxSpeedReverse = 0,
        MaxSteerForce = 50,
        MeshExtentsX = 1.0,
        MeshExtentsY = 0.8,
        MeshExtentsZ = 1.2,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Air',
        TurnRadius = 0,
        TurnRate = 240,
    },
    SelectionSizeX = 0.6,
    SelectionSizeZ = 0.8,
    SelectionThickness = 0.6,
    SizeX = 0.8,
    SizeY = 0.6,
    SizeZ = 1.0,
    StrategicIconName = 'raptorfaction/icon_raptor_kamikaze_air',
    StrategicIconSortPriority = 115,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            CollideFriendly = false,
            Damage = 0,
            DamageFriendly = false,
            DamageRadius = 0,
            DamageType = 'Normal',
            DisplayName = 'Suicide Bio Detonation Trigger',
            FireTargetLayerCapsTable = {
                Air = 'Land|Water|Seabed',
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 180,
            Label = 'Suicide',
            MaxRadius = 4.0,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1,
            SlavedToBody = true,
            TargetCheckInterval = 0.1,
            TargetPriorities = {
                'COMMAND',
                'TECH3 STRUCTURE',
                'TECH2 STRUCTURE',
                'TECH1 STRUCTURE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            Turreted = false,
            WeaponCategory = 'Kamikaze',
        },
        {
            AboveWaterTargetsOnly = true,
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            Damage = 1400,
            DamageFriendly = false,
            DamageRadius = 3.5,
            DamageType = 'Normal',
            DisplayName = 'Air Dive Bio Detonation',
            FireOnDeath = true,
            FireTargetLayerCapsTable = {
                Air = 'Air|Land|Seabed|Water',
                Land = 'Air|Land|Seabed|Water',
                Water = 'Air|Land|Water',
            },
            FiringTolerance = 2,
            IgnoreIfDisabled = true,
            Label = 'DeathWeapon',
            ManualFire = false,
            MaxRadius = 3.5,
            MuzzleVelocity = 0,
            RackBones = {
                {
                    MuzzleBones = { 0 },
                    RackBone = 0,
                },
            },
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1,
            SalvoSize = 1,
            SlavedToBody = true,
            TargetRestrictDisallow = 'UNTARGETABLE',
            Turreted = false,
            WeaponCategory = 'Direct Fire',
        },
    },
}
"""
with open(os.path.join(units_dir, "XRA0213", "XRA0213_unit.bp"), "w", encoding="utf-8") as f:
    f.write(bp_xra0213)

script_xra0213 = """local CAirUnit = import('/lua/cybranunits.lua').CAirUnit
local Weapon = import('/lua/sim/weapon.lua').Weapon
local DamageArea = DamageArea
local CreateEmitterAtEntity = CreateEmitterAtEntity
local ForkThread = ForkThread
local WaitTicks = WaitTicks
local IsDestroyed = IsDestroyed

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class XRA0213_SuicideWeapon : Weapon
local XRA0213_SuicideWeapon = ClassWeapon(Weapon) {
    OnFire = function(self)
        local unit = self.unit
        if not unit.Dead and not unit.Detonated then
            unit:Kill()
        end
    end,
}

---@class XRA0213_DeathWeapon : Weapon
local XRA0213_DeathWeapon = ClassWeapon(Weapon) {
    OnCreate = function(self)
        Weapon.OnCreate(self)
        self:SetWeaponEnabled(false)
        self:ChangeMaxRadius(self:GetDamageTable().DamageRadius)
    end,

    Fire = function(self)
        local unit = self.unit
        if not unit or unit.Detonated then return end
        unit.Detonated = true

        local position = unit:GetPosition()
        local damageTable = self:GetDamageTable()
        local radius = damageTable.DamageRadius or 3.5
        local damage = damageTable.DamageAmount or 1400
        local dType = damageTable.DamageType or 'Normal'
        local dFriendly = damageTable.DamageFriendly or false

        -- 1. Direct biological burst damage
        DamageArea(unit, position, radius, damage, dType, dFriendly)

        -- 2. Visual blood explosion emitters
        local army = unit.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(unit, army, emit):ScaleEmitter(2.8)
        end

        -- 3. Sound and instant destruction
        unit:PlayUnitSound('Destroyed')
        unit:Destroy()
    end,
}

---@class XRA0213 : CAirUnit
XRA0213 = ClassUnit(CAirUnit) {
    Weapons = {
        Suicide = ClassWeapon(XRA0213_SuicideWeapon) {},
        DeathWeapon = ClassWeapon(XRA0213_DeathWeapon) {},
    },

    OnCreate = function(self)
        CAirUnit.OnCreate(self)
    end,

    OnProductionPaused = function(self)
        -- Manual Detonate UI Button
        local weapon = self:GetWeaponByLabel('Suicide')
        if weapon then
            weapon:FireWeapon()
        elseif not self.Dead then
            self:Kill()
        end
    end,

    DoDeathWeapon = function(self)
        if self:IsBeingBuilt() then return end
        CAirUnit.DoDeathWeapon(self)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        if not self.Detonated then
            local deathWeapon = self:GetWeaponByLabel('DeathWeapon')
            if deathWeapon then
                deathWeapon:Fire()
            end
        end
        CAirUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        -- Handled by DeathWeapon
    end,
}

TypeClass = XRA0213
"""
with open(os.path.join(units_dir, "XRA0213", "XRA0213_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_xra0213)


# ===========================================================================
# 4. XRA0310: BEHEMOTH HEAVY DODO (T3 Land Heavy Bio-Acid Suicide)
# ===========================================================================
print("\n[4/5] Updating XRA0310 (Behemoth Heavy Dodo)...")

bp_xra0310 = """UnitBlueprint {
    Audio = {
        UISelection = Sound {
            Bank = 'Interface',
            Cue = 'Cybran_Select_Bot',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Destroyed = Sound {
            Bank = 'Raptor_Bio_Bomb',
            Cue = 'Attack',
            LodCutoff = 'UnitMove_LodCutoff',
        },
        Killed = Sound {
            Bank = 'Raptor_Bio_Bomb',
            Cue = 'Attack',
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
        'BUILTBYRAPTORHIVE',
        'RAPTOR',
        'MOBILE',
        'LAND',
        'TECH3',
        'KAMIKAZE',
        'BOMB',
        'DIRECTFIRE',
        'SHOWATTACKRETICLE',
        'AMPHIBIOUS',
        'VISIBLETORECON',
        'RECLAIMABLE',
    },
    CollisionOffsetY = 0,
    CollisionOffsetZ = 0,
    Defense = {
        ArmorType = 'Normal',
        Health = 3400,
        MaxHealth = 3400,
        RegenRate = 5.0,
    },
    Description = '<LOC xra0310_desc>Behemoth Heavy Acid Dodo',
    Display = {
        Abilities = {
            '<LOC ability_suicideweapon>Suicide Weapon',
        },
        AnimationWalk = '/mods/RaptorFaction/units/XRA0310/XRA0310_Awalk.sca',
        AnimationWalkRate = 1.8,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0310/XRA0310_Albedo.dds',
                    LODCutoff = 300,
                    MeshName = '/mods/RaptorFaction/units/XRA0310/XRA0310_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0310/XRA0310_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0310/XRA0310_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 1.35,
    },
    Economy = {
        BuildCostEnergy = 12000,
        BuildCostMass = 1200,
        BuildTime = 3200,
    },
    General = {
        Category = 'Direct Fire',
        Classification = 'RULEUC_MilitaryVehicle',
        CommandCaps = {
            RULEUCC_Attack = true,
            RULEUCC_CallCycle = false,
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
        FactionName = 'Raptor',
        Icon = 'land',
        InstantDeathOnSelfDestruct = true,
        OrderOverrides = {
            RULEUTC_ProductionToggle = {
                bitmapId = 'overcharge',
                helpText = 'Detonate',
            },
        },
        ToggleCaps = {
            RULEUTC_ProductionToggle = true,
        },
        UnitName = '<LOC xra0310_name>Behemoth Heavy Dodo',
    },
    Intel = {
        VisionRadius = 24,
    },
    Interface = {
        HelpText = '<LOC xra0310_help>Gargantuan bio-acid suicide monstrosity that triggers a cataclysmic acid blast vaporizing entire armies.',
    },
    LifeBarHeight = 0.08,
    LifeBarOffset = 0.8,
    LifeBarSize = 1.1,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 3.6,
        MaxBrake = 3.6,
        MaxSpeed = 3.8,
        MaxSpeedReverse = 0,
        MaxSteerForce = 20,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        RotateOnSpot = true,
        RotateOnSpotThreshold = 0.1,
        TurnRadius = 0,
        TurnRate = 160,
    },
    SelectionSizeX = 0.9,
    SelectionSizeZ = 1.2,
    SelectionThickness = 0.6,
    SizeX = 1.1,
    SizeY = 1.2,
    SizeZ = 1.5,
    StrategicIconName = 'raptorfaction/icon_raptor_heavy_dodo',
    StrategicIconSortPriority = 135,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            CollideFriendly = false,
            Damage = 0,
            DamageFriendly = false,
            DamageRadius = 0,
            DamageType = 'Normal',
            DisplayName = 'Cataclysmic Acid Detonation Trigger',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 180,
            Label = 'Suicide',
            MaxRadius = 4.5,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1,
            SlavedToBody = true,
            TargetCheckInterval = 0.1,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'EXPERIMENTAL',
                'TECH3 MOBILE',
                'STRUCTURE DEFENSE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            Turreted = false,
            WeaponCategory = 'Kamikaze',
        },
        {
            AboveWaterTargetsOnly = true,
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            Damage = 2500,
            DamageFriendly = true,
            DamageRadius = 7.0,
            DamageType = 'Normal',
            DisplayName = 'Death Acid Crater Detonation',
            FireOnDeath = true,
            FireTargetLayerCapsTable = {
                Air = 'Air|Land|Seabed|Water',
                Land = 'Air|Land|Seabed|Water',
                Water = 'Air|Land|Water',
            },
            FiringTolerance = 2,
            IgnoreIfDisabled = true,
            Label = 'DeathWeapon',
            ManualFire = false,
            MaxRadius = 7.0,
            MuzzleVelocity = 0,
            RackBones = {
                {
                    MuzzleBones = { 0 },
                    RackBone = 0,
                },
            },
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1,
            SalvoSize = 1,
            SlavedToBody = true,
            TargetRestrictDisallow = 'UNTARGETABLE',
            Turreted = false,
            WeaponCategory = 'Direct Fire',
        },
    },
}
"""
with open(os.path.join(units_dir, "XRA0310", "XRA0310_unit.bp"), "w", encoding="utf-8") as f:
    f.write(bp_xra0310)

script_xra0310 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local Weapon = import('/lua/sim/weapon.lua').Weapon
local DamageArea = DamageArea
local CreateEmitterAtEntity = CreateEmitterAtEntity
local ForkThread = ForkThread
local WaitTicks = WaitTicks
local IsDestroyed = IsDestroyed

local HeavyAcidKamikazeEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_acid_splash_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_puddle_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_bubbles_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_steam_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
}

---@class XRA0310_SuicideWeapon : Weapon
local XRA0310_SuicideWeapon = ClassWeapon(Weapon) {
    OnFire = function(self)
        local unit = self.unit
        if not unit.Dead and not unit.Detonated then
            unit:Kill()
        end
    end,
}

---@class XRA0310_DeathWeapon : Weapon
local XRA0310_DeathWeapon = ClassWeapon(Weapon) {
    OnCreate = function(self)
        Weapon.OnCreate(self)
        self:SetWeaponEnabled(false)
        self:ChangeMaxRadius(self:GetDamageTable().DamageRadius)
    end,

    Fire = function(self)
        local unit = self.unit
        if not unit or unit.Detonated then return end
        unit.Detonated = true

        local position = unit:GetPosition()
        local damageTable = self:GetDamageTable()
        local radius = damageTable.DamageRadius or 7.0
        local damage = damageTable.DamageAmount or 2500
        local dType = damageTable.DamageType or 'Normal'
        local dFriendly = damageTable.DamageFriendly or false

        -- 1. Cataclysmic direct acid blast damage
        DamageArea(unit, position, radius, damage, dType, dFriendly)

        -- 2. Massive green acid explosion crater emitters
        local army = unit.Army
        for _, emit in HeavyAcidKamikazeEffects do
            CreateEmitterAtEntity(unit, army, emit):ScaleEmitter(3.5)
        end

        -- 3. Sound and instant destruction
        unit:PlayUnitSound('Destroyed')
        unit:Destroy()
    end,
}

---@class XRA0310 : CWalkingLandUnit
XRA0310 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Suicide = ClassWeapon(XRA0310_SuicideWeapon) {},
        DeathWeapon = ClassWeapon(XRA0310_DeathWeapon) {},
    },

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
        self:StartTrackTargetThread()
    end,

    StartTrackTargetThread = function(self)
        local navigator = self:GetNavigator()
        if not navigator then return end
        local weapon = self:GetWeaponByLabel('Suicide')
        if not weapon then return end

        return self.Trash:Add(
            ForkThread(self.TrackTargetThread, self, navigator, weapon)
        )
    end,

    TrackTargetThread = function(self, navigator, weapon)
        local lastTarget
        while not IsDestroyed(self) and not IsDestroyed(weapon) do
            local command = self:GetCommandQueue()[1]
            local target
            if command and command.commandType == 10 then
                target = command.target
            end
            if not target then
                lastTarget = nil
                navigator:SetSpeedThroughGoal(false)
            elseif target ~= lastTarget then
                lastTarget = target
                navigator:SetSpeedThroughGoal(true)
            end

            WaitTicks(5)
        end
    end,

    OnProductionPaused = function(self)
        -- Manual Detonate UI Button
        local weapon = self:GetWeaponByLabel('Suicide')
        if weapon then
            weapon:FireWeapon()
        elseif not self.Dead then
            self:Kill()
        end
    end,

    DoDeathWeapon = function(self)
        if self:IsBeingBuilt() then return end
        CWalkingLandUnit.DoDeathWeapon(self)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        if not self.Detonated then
            local deathWeapon = self:GetWeaponByLabel('DeathWeapon')
            if deathWeapon then
                deathWeapon:Fire()
            end
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        -- Handled by DeathWeapon
    end,
}

TypeClass = XRA0310
"""
with open(os.path.join(units_dir, "XRA0310", "XRA0310_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_xra0310)


# ===========================================================================
# 5. XRA0320: BEHEMOTH EMP SHOCK DODO (T3 Land Heavy EMP Suicide)
# ===========================================================================
print("\n[5/5] Updating XRA0320 (Behemoth EMP Shock Dodo)...")

bp_xra0320 = """UnitBlueprint {
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
        Stun = {
            Add = {
                OnDeath = true,
                OnImpact = true,
            },
            AppliedToTarget = false,
            BuffType = 'STUN',
            Duration = 8,
            Radius = 7.0,
            TargetAllow = 'ALLUNITS',
            TargetDisallow = 'WALL',
        },
    },
    BuildIconSortPriority = 35,
    Categories = {
        'PRODUCTSC1',
        'SELECTABLE',
        'LAND',
        'MOBILE',
        'KAMIKAZE',
        'BOMB',
        'DIRECTFIRE',
        'SHOWATTACKRETICLE',
        'TECH3',
        'BUILTBYRAPTORHIVE',
        'RAPTOR',
        'VISIBLETORECON',
        'RECLAIMABLE',
    },
    Defense = {
        ArmorType = 'Normal',
        Health = 3200,
        MaxHealth = 3200,
        RegenRate = 5.0,
    },
    Description = '<LOC xra0320_desc>Heavy EMP Blackout Kamikaze',
    Display = {
        Abilities = {
            '<LOC ability_suicideweapon>Suicide Weapon',
            '<LOC ability_stun>EMP Weapon',
        },
        AnimationWalk = '/mods/RaptorFaction/units/XRA0320/XRA0320_Awalk.sca',
        AnimationWalkRate = 1.8,
        Mesh = {
            IconFadeInZoom = 130,
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0320/XRA0320_Albedo.dds',
                    LODCutoff = 215,
                    MeshName = '/mods/RaptorFaction/units/XRA0320/XRA0320_lod0.scm',
                    NormalsName = '/mods/RaptorFaction/units/XRA0320/XRA0320_NormalsTS.dds',
                    SpecularName = '/mods/RaptorFaction/units/XRA0320/XRA0320_SpecTeam.dds',
                    ShaderName = 'Insect',
                },
            },
        },
        UniformScale = 0.08,
    },
    Economy = {
        BuildCostEnergy = 11000,
        BuildCostMass = 1100,
        BuildTime = 3000,
    },
    General = {
        Category = 'Land',
        Classification = 'RULEUC_MilitaryVehicle',
        CommandCaps = {
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
        },
        FactionName = 'Raptor',
        Icon = 'amph',
        InstantDeathOnSelfDestruct = true,
        OrderOverrides = {
            RULEUTC_ProductionToggle = {
                bitmapId = 'overcharge',
                helpText = 'Detonate',
            },
        },
        ToggleCaps = {
            RULEUTC_ProductionToggle = true,
        },
        TechLevel = 'RULEUTL_Advanced',
        UnitName = '<LOC xra0320_name>Behemoth EMP Shock Dodo',
        UnitWeight = 1,
    },
    Intel = {
        VisionRadius = 24,
    },
    Interface = {
        HelpText = '<LOC xra0320_help>Colossal EMP shock kamikaze that detonates in a high-voltage blackout shockwave collapsing all enemy shields and disabling armies.',
    },
    LifeBarHeight = 0.075,
    LifeBarOffset = 0.5,
    LifeBarSize = 0.6,
    Physics = {
        BankingSlope = 0,
        BuildOnLayerCaps = {
            LAYER_Land = true,
            LAYER_Water = true,
        },
        DragCoefficient = 0.2,
        MaxAcceleration = 3.6,
        MaxBrake = 3.6,
        MaxSpeed = 3.8,
        MaxSpeedReverse = 0,
        MaxSteerForce = 20,
        MinSpeedPercent = 0,
        MotionType = 'RULEUMT_Amphibious',
        RotateOnSpot = true,
        RotateOnSpotThreshold = 0.1,
        TurnRadius = 0,
        TurnRate = 160,
    },
    SelectionSizeX = 0.8,
    SelectionSizeZ = 1.1,
    SelectionThickness = 0.6,
    SizeX = 1.0,
    SizeY = 1.1,
    SizeZ = 1.4,
    StrategicIconName = 'raptorfaction/icon_raptor_emp_kamikaze',
    StrategicIconSortPriority = 115,
    Weapon = {
        {
            AboveWaterTargetsOnly = true,
            CollideFriendly = false,
            Damage = 0,
            DamageFriendly = false,
            DamageRadius = 0,
            DamageType = 'Normal',
            DisplayName = 'Heavy EMP Detonation Trigger',
            FireTargetLayerCapsTable = {
                Land = 'Land|Water|Seabed',
                Water = 'Land|Water|Seabed',
            },
            FiringTolerance = 180,
            Label = 'Suicide',
            MaxRadius = 4.5,
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1,
            SlavedToBody = true,
            TargetCheckInterval = 0.1,
            TargetPriorities = {
                'SPECIALHIGHPRI',
                'EXPERIMENTAL',
                'TECH3 MOBILE',
                'STRUCTURE DEFENSE',
                'ALLUNITS',
            },
            TargetRestrictDisallow = 'UNTARGETABLE',
            Turreted = false,
            WeaponCategory = 'Kamikaze',
        },
        {
            AboveWaterTargetsOnly = true,
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            Damage = 2200,
            DamageToShields = 6000,
            DamageFriendly = false,
            DamageRadius = 7.0,
            DamageType = 'EMP',
            DisplayName = 'Heavy EMP Blackout Detonation',
            FireOnDeath = true,
            FireTargetLayerCapsTable = {
                Air = 'Air|Land|Seabed|Water',
                Land = 'Air|Land|Seabed|Water',
                Water = 'Air|Land|Water',
            },
            FiringTolerance = 2,
            IgnoreIfDisabled = true,
            Label = 'DeathWeapon',
            ManualFire = false,
            MaxRadius = 7.0,
            MuzzleVelocity = 0,
            RackBones = {
                {
                    MuzzleBones = { 0 },
                    RackBone = 0,
                },
            },
            RangeCategory = 'UWRC_DirectFire',
            RateOfFire = 1,
            SalvoSize = 1,
            SlavedToBody = true,
            TargetRestrictDisallow = 'UNTARGETABLE',
            Turreted = false,
            WeaponCategory = 'Direct Fire',
        },
    },
}
"""
with open(os.path.join(units_dir, "XRA0320", "XRA0320_unit.bp"), "w", encoding="utf-8") as f:
    f.write(bp_xra0320)

script_xra0320 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local Weapon = import('/lua/sim/weapon.lua').Weapon
local DamageArea = DamageArea
local CreateEmitterAtEntity = CreateEmitterAtEntity
local ForkThread = ForkThread
local WaitTicks = WaitTicks
local IsDestroyed = IsDestroyed

local HeavyEMPDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
    '/effects/emitters/cybran_empgrenade_hit_01_emit.bp',
    '/effects/emitters/cybran_empgrenade_hit_02_emit.bp',
    '/effects/emitters/build_sparks_blue_02_emit.bp',
}

---@class XRA0320_SuicideWeapon : Weapon
local XRA0320_SuicideWeapon = ClassWeapon(Weapon) {
    OnFire = function(self)
        local unit = self.unit
        if not unit.Dead and not unit.Detonated then
            unit:Kill()
        end
    end,
}

---@class XRA0320_DeathWeapon : Weapon
local XRA0320_DeathWeapon = ClassWeapon(Weapon) {
    OnCreate = function(self)
        Weapon.OnCreate(self)
        self:SetWeaponEnabled(false)
        self:ChangeMaxRadius(self:GetDamageTable().DamageRadius)
    end,

    Fire = function(self)
        local unit = self.unit
        if not unit or unit.Detonated then return end
        unit.Detonated = true

        local position = unit:GetPosition()
        local damageTable = self:GetDamageTable()
        local radius = damageTable.DamageRadius or 7.0
        local damage = damageTable.DamageAmount or 2200

        -- 1. Direct blast damage
        DamageArea(unit, position, radius, damage, 'Normal', false)

        -- 2. Heavy anti-shield collapse (6000 damage)
        DamageArea(unit, position, radius, 6000, 'FAF_AntiShield', false)

        -- 3. Stun all enemy units in 7.0m blast radius for 8.0 seconds
        local brain = unit:GetAIBrain()
        if brain then
            local targets = brain:GetUnitsAroundPoint(categories.MOBILE + categories.STRUCTURE, position, radius, 'Enemy')
            for _, t in targets do
                if not t.Dead then
                    t:SetStunned(8.0)
                    if t.MyShield and t.MyShield:IsOn() then
                        t.MyShield:ApplyDamage(6000)
                    end
                end
            end
        end

        -- 4. Heavy EMP explosion & gore emitters
        local army = unit.Army
        for _, emit in HeavyEMPDeathEffects do
            CreateEmitterAtEntity(unit, army, emit):ScaleEmitter(3.5)
        end

        -- 5. Sound and instant destruction
        unit:PlayUnitSound('Destroyed')
        unit:Destroy()
    end,
}

---@class XRA0320 : CWalkingLandUnit
XRA0320 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Suicide = ClassWeapon(XRA0320_SuicideWeapon) {},
        DeathWeapon = ClassWeapon(XRA0320_DeathWeapon) {},
    },

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
        self:StartTrackTargetThread()
    end,

    StartTrackTargetThread = function(self)
        local navigator = self:GetNavigator()
        if not navigator then return end
        local weapon = self:GetWeaponByLabel('Suicide')
        if not weapon then return end

        return self.Trash:Add(
            ForkThread(self.TrackTargetThread, self, navigator, weapon)
        )
    end,

    TrackTargetThread = function(self, navigator, weapon)
        local lastTarget
        while not IsDestroyed(self) and not IsDestroyed(weapon) do
            local command = self:GetCommandQueue()[1]
            local target
            if command and command.commandType == 10 then
                target = command.target
            end
            if not target then
                lastTarget = nil
                navigator:SetSpeedThroughGoal(false)
            elseif target ~= lastTarget then
                lastTarget = target
                navigator:SetSpeedThroughGoal(true)
            end

            WaitTicks(5)
        end
    end,

    OnProductionPaused = function(self)
        -- Manual Detonate UI Button
        local weapon = self:GetWeaponByLabel('Suicide')
        if weapon then
            weapon:FireWeapon()
        elseif not self.Dead then
            self:Kill()
        end
    end,

    DoDeathWeapon = function(self)
        if self:IsBeingBuilt() then return end
        CWalkingLandUnit.DoDeathWeapon(self)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        if not self.Detonated then
            local deathWeapon = self:GetWeaponByLabel('DeathWeapon')
            if deathWeapon then
                deathWeapon:Fire()
            end
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        -- Handled by DeathWeapon
    end,
}

TypeClass = XRA0320
"""
with open(os.path.join(units_dir, "XRA0320", "XRA0320_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_xra0320)

print("\n--- All 5 unit files written to mod directory successfully! ---")

# ===========================================================================
# 6. RE-PACKAGE MOD ARCHIVE
# ===========================================================================
print(f"\nRe-packaging updated mod archive to {export_zip}...")
os.makedirs(os.path.dirname(export_zip), exist_ok=True)
with zipfile.ZipFile(export_zip, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(mod_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(mod_dir))
            z.write(full_path, rel_path)

print(f"Export zip updated: {os.path.getsize(export_zip) / (1024*1024):.2f} MB")
print("\nSUCCESS: All 5 Raptor Kamikaze units fixed and packaged!")
