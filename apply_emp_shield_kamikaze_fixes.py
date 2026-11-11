import os
import re
import zipfile

mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
units_dir = os.path.join(mod_dir, "units")
proj_dir = os.path.join(mod_dir, "projectiles")
export_zip = r"E:\Games\FAFMods\exports\RaptorFaction.zip"

print("--- Applying EMP, Shield Disruption, Worm, & Kamikaze Smart Targeting Fixes ---")

# ===========================================================================
# 1. HELPER FUNCTIONS FOR BLUEPRINT EDITING
# ===========================================================================
def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# ===========================================================================
# 2. FIX KAMIKAZE UNITS (XRA0103, XRA0203, XRA0310)
#    - Disabled during Move commands (no accidental blowing on outer perimeter/walls)
#    - Speeds through goal on Attack commands
#    - Attack only detonates when reaching the commanded target (ignores obstacles)
#    - Death Weapon on death (FireOnDeath = true, never dies in vain if shot down)
#    - Manual Detonate button in UI (RULEUTC_ProductionToggle)
# ===========================================================================

# ---------------------------------------------------------------------------
# 2.1 XRA0103: Volatile Acid Tick
# ---------------------------------------------------------------------------
print("\n[1/7] Updating XRA0103 (Volatile Acid Tick)...")
bp_xra0103 = read_file(os.path.join(units_dir, "XRA0103", "XRA0103_unit.bp"))

# Add BOMB category if not present
if "'BOMB'" not in bp_xra0103:
    bp_xra0103 = bp_xra0103.replace("'KAMIKAZE',", "'KAMIKAZE',\n        'BOMB',")

# Add ProductionToggle & InstantDeath in General
if "RULEUTC_ProductionToggle" not in bp_xra0103:
    general_marker = "UnitName = '<LOC xra0103_name>Volatile Acid Tick',"
    toggle_code = """UnitName = '<LOC xra0103_name>Volatile Acid Tick',
        InstantDeathOnSelfDestruct = true,
        OrderOverrides = {
            RULEUTC_ProductionToggle = {
                bitmapId = 'overcharge',
                helpText = 'Detonate',
            },
        },
        ToggleCaps = {
            RULEUTC_ProductionToggle = true,
        },"""
    bp_xra0103 = bp_xra0103.replace(general_marker, toggle_code)

# Add DeathWeapon if not present
if "Label = 'DeathWeapon'" not in bp_xra0103:
    death_weapon_code = """        {
            AboveWaterTargetsOnly = true,
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            Damage = 50,
            DamageFriendly = true,
            DamageRadius = 4.0,
            DamageType = 'Normal',
            DisplayName = 'Death Acid Detonation',
            DoTTime = 3.0,
            DoTPulses = 5,
            InitialDamage = 500,
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
            MaxRadius = 4.0,
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
}"""
    # Replace end of Weapon table
    bp_xra0103 = re.sub(r'(\s+Turreted = false,\s+WeaponCategory = \'Kamikaze\',\s+\},\s+)(\},\s+\})', r'\1' + death_weapon_code, bp_xra0103)

write_file(os.path.join(units_dir, "XRA0103", "XRA0103_unit.bp"), bp_xra0103)

script_xra0103 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local Weapon = import('/lua/sim/weapon.lua').Weapon
local DefaultDamage = import('/lua/sim/DefaultDamage.lua')
local AreaDoTThread = DefaultDamage.AreaDoTThread
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

---@class KamikazeAcidWeapon : Weapon
local KamikazeAcidWeapon = ClassWeapon(Weapon) {
    OnFire = function(self)
        local unit = self.unit
        if unit.Dead or unit.Detonated then return end

        local cmd = unit:GetCommandQueue()[1]
        -- If player ordered an attack on a specific unit, only detonate on that unit or when in touch range
        if cmd and cmd.commandType == 10 and cmd.target and not cmd.target.Dead then
            local currentTarget = self:GetCurrentTarget()
            if currentTarget ~= cmd.target then
                local myPos = unit:GetPosition()
                local tPos = cmd.target:GetPosition()
                local dx = myPos[1] - tPos[1]
                local dz = myPos[3] - tPos[3]
                -- If we have not reached the assigned target yet, ignore perimeter distractions
                if (dx*dx + dz*dz) > 9.0 then
                    return
                end
            end
        end

        unit:DetonateAcid()
    end,
}

---@class DeathAcidWeapon : Weapon
local DeathAcidWeapon = ClassWeapon(Weapon) {
    OnCreate = function(self)
        Weapon.OnCreate(self)
        self:SetWeaponEnabled(false)
    end,

    Fire = function(self)
        local unit = self.unit
        if not unit.Detonated then
            unit:DetonateAcid()
        end
    end,
}

---@class XRA0103 : CWalkingLandUnit
XRA0103 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Suicide = ClassWeapon(KamikazeAcidWeapon) {},
        DeathWeapon = ClassWeapon(DeathAcidWeapon) {},
    },

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
        self.Trash:Add(ForkThread(self.TrackTargetThread, self))
    end,

    TrackTargetThread = function(self)
        local navigator = self:GetNavigator()
        local weapon = self:GetWeaponByLabel('Suicide')

        while not IsDestroyed(self) do
            -- Disable weapon when simply moving so ticks don't blow up prematurely on base perimeters
            if weapon then
                if self:IsUnitState('Attacking') or self:IsUnitState('BeingCaptured') or self:IsUnitState('BeingReclaimed') then
                    weapon:SetEnabled(true)
                else
                    weapon:SetEnabled(false)
                end
            end

            -- Speed through goal straight into the enemy target
            local cmd = self:GetCommandQueue()[1]
            if cmd and cmd.commandType == 10 then
                local target = cmd.target
                if target and not target.Dead then
                    navigator:SetDestUnit(target)
                    navigator:SetSpeedThroughGoal(true)
                end
            end

            WaitTicks(3)
        end
    end,

    OnProductionPaused = function(self)
        -- Manual Detonate UI Button
        self:DetonateAcid()
    end,

    DetonateAcid = function(self)
        if self.Detonated then return end
        self.Detonated = true
        local army = self.Army
        local pos = self:GetPosition()

        -- Initial direct explosion damage
        DamageArea(self, pos, 4.0, 500, 'Normal', false, false)

        -- Lingering corrosive acid DoT pool (5 pulses of 50 damage over 3.0s, radius 4.0)
        ForkThread(AreaDoTThread, self, pos, 5, 0.6, 4.0, 50, 'Normal', false, false)

        -- Visual green acid pool + organic splatter
        for _, emit in AcidKamikazeEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.5)
        end

        self:PlayUnitSound('Destroyed')
        if not self.Dead then
            self:Kill()
        end
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        if not self.Detonated then
            self:DetonateAcid()
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    DoDeathWeapon = function(self)
        if self:IsBeingBuilt() then return end
        if not self.Detonated then
            self:DetonateAcid()
        end
        CWalkingLandUnit.DoDeathWeapon(self)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        -- Handled by DetonateAcid visuals
    end,
}

TypeClass = XRA0103
"""
write_file(os.path.join(units_dir, "XRA0103", "XRA0103_script.lua"), script_xra0103)


# ---------------------------------------------------------------------------
# 2.2 XRA0203: Bio-EMP Shock Tick
# ---------------------------------------------------------------------------
print("\n[2/7] Updating XRA0203 (Bio-EMP Shock Tick)...")
bp_xra0203 = read_file(os.path.join(units_dir, "XRA0203", "XRA0203_unit.bp"))

# Add BOMB category if not present
if "'BOMB'" not in bp_xra0203:
    bp_xra0203 = bp_xra0203.replace("'KAMIKAZE',", "'KAMIKAZE',\n        'BOMB',")

# Add ProductionToggle & InstantDeath in General
if "RULEUTC_ProductionToggle" not in bp_xra0203:
    general_marker = "UnitName = '<LOC xra0203_name>Bio-EMP Shock Tick',"
    toggle_code = """UnitName = '<LOC xra0203_name>Bio-EMP Shock Tick',
        InstantDeathOnSelfDestruct = true,
        OrderOverrides = {
            RULEUTC_ProductionToggle = {
                bitmapId = 'overcharge',
                helpText = 'Detonate',
            },
        },
        ToggleCaps = {
            RULEUTC_ProductionToggle = true,
        },"""
    bp_xra0203 = bp_xra0203.replace(general_marker, toggle_code)

# Add Standard FAF STUN Buff to Blueprint
if "Buffs = {" not in bp_xra0203:
    buff_code = """    Buffs = {
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
    BuildIconSortPriority = 35,"""
    bp_xra0203 = bp_xra0203.replace("BuildIconSortPriority = 35,", buff_code)

# Add DeathWeapon if not present
if "Label = 'DeathWeapon'" not in bp_xra0203:
    death_weapon_emp = """        {
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
}"""
    bp_xra0203 = re.sub(r'(\s+Turreted = false,\s+WeaponCategory = \'Kamikaze\',\s+\},\s+)(\},\s+\})', r'\1' + death_weapon_emp, bp_xra0203)

write_file(os.path.join(units_dir, "XRA0203", "XRA0203_unit.bp"), bp_xra0203)

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

---@class EMPSuicideWeapon : Weapon
local EMPSuicideWeapon = ClassWeapon(Weapon) {
    OnFire = function(self)
        local unit = self.unit
        if unit.Dead or unit.Detonated then return end

        local cmd = unit:GetCommandQueue()[1]
        -- If player ordered an attack on a specific unit, only detonate on that unit or in touch range
        if cmd and cmd.commandType == 10 and cmd.target and not cmd.target.Dead then
            local currentTarget = self:GetCurrentTarget()
            if currentTarget ~= cmd.target then
                local myPos = unit:GetPosition()
                local tPos = cmd.target:GetPosition()
                local dx = myPos[1] - tPos[1]
                local dz = myPos[3] - tPos[3]
                if (dx*dx + dz*dz) > 9.0 then
                    return
                end
            end
        end

        unit:DetonateEMP()
    end,
}

---@class DeathEMPWeapon : Weapon
local DeathEMPWeapon = ClassWeapon(Weapon) {
    OnCreate = function(self)
        Weapon.OnCreate(self)
        self:SetWeaponEnabled(false)
    end,

    Fire = function(self)
        local unit = self.unit
        if not unit.Detonated then
            unit:DetonateEMP()
        end
    end,
}

---@class XRA0203 : CWalkingLandUnit
XRA0203 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Suicide = ClassWeapon(EMPSuicideWeapon) {},
        DeathWeapon = ClassWeapon(DeathEMPWeapon) {},
    },

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
        self.Trash:Add(ForkThread(self.TrackTargetThread, self))
    end,

    TrackTargetThread = function(self)
        local navigator = self:GetNavigator()
        local weapon = self:GetWeaponByLabel('Suicide')

        while not IsDestroyed(self) do
            -- Disable weapon when simply moving so EMP ticks can sneak deep into base
            if weapon then
                if self:IsUnitState('Attacking') or self:IsUnitState('BeingCaptured') or self:IsUnitState('BeingReclaimed') then
                    weapon:SetEnabled(true)
                else
                    weapon:SetEnabled(false)
                end
            end

            -- Speed through goal straight into enemy target
            local cmd = self:GetCommandQueue()[1]
            if cmd and cmd.commandType == 10 then
                local target = cmd.target
                if target and not target.Dead then
                    navigator:SetDestUnit(target)
                    navigator:SetSpeedThroughGoal(true)
                end
            end

            WaitTicks(3)
        end
    end,

    OnProductionPaused = function(self)
        -- Manual Detonate UI Button
        self:DetonateEMP()
    end,

    DetonateEMP = function(self)
        if self.Detonated then return end
        self.Detonated = true
        local army = self.Army
        local pos = self:GetPosition()

        -- Direct blast damage
        DamageArea(self, pos, 5.0, 450, 'Normal', false, false)

        -- Shield disruption damage (collapses shields in 5.0m blast radius)
        DamageArea(self, pos, 5.0, 2500, 'FAF_AntiShield', false, false)

        -- Stun all enemy mobile and structure units
        local brain = self:GetAIBrain()
        if brain then
            local targets = brain:GetUnitsAroundPoint(categories.MOBILE + categories.STRUCTURE, pos, 5.0, 'Enemy')
            for _, t in targets do
                if not t.Dead then
                    t:SetStunned(6.0)
                    if t.MyShield and t.MyShield:IsOn() then
                        t.MyShield:ApplyDamage(2500)
                    end
                end
            end
        end

        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.5)
        end

        self:PlayUnitSound('Destroyed')
        if not self.Dead then
            self:Kill()
        end
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        if not self.Detonated then
            self:DetonateEMP()
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    DoDeathWeapon = function(self)
        if self:IsBeingBuilt() then return end
        if not self.Detonated then
            self:DetonateEMP()
        end
        CWalkingLandUnit.DoDeathWeapon(self)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        -- Handled by DetonateEMP visuals
    end,
}

TypeClass = XRA0203
"""
write_file(os.path.join(units_dir, "XRA0203", "XRA0203_script.lua"), script_xra0203)


# ---------------------------------------------------------------------------
# 2.3 XRA0310: Behemoth Heavy Dodo
# ---------------------------------------------------------------------------
print("\n[3/7] Updating XRA0310 (Behemoth Heavy Dodo)...")
bp_xra0310 = read_file(os.path.join(units_dir, "XRA0310", "XRA0310_unit.bp"))

# Add BOMB category if not present
if "'BOMB'" not in bp_xra0310:
    bp_xra0310 = bp_xra0310.replace("'KAMIKAZE',", "'KAMIKAZE',\n        'BOMB',")

# Add ProductionToggle & InstantDeath in General
if "RULEUTC_ProductionToggle" not in bp_xra0310:
    general_marker = "UnitName = '<LOC xra0310_name>Behemoth Heavy Dodo',"
    toggle_code = """UnitName = '<LOC xra0310_name>Behemoth Heavy Dodo',
        InstantDeathOnSelfDestruct = true,
        OrderOverrides = {
            RULEUTC_ProductionToggle = {
                bitmapId = 'overcharge',
                helpText = 'Detonate',
            },
        },
        ToggleCaps = {
            RULEUTC_ProductionToggle = true,
        },"""
    bp_xra0310 = bp_xra0310.replace(general_marker, toggle_code)

# Add DeathWeapon if not present
if "Label = 'DeathWeapon'" not in bp_xra0310:
    death_weapon_heavy = """        {
            AboveWaterTargetsOnly = true,
            BallisticArc = 'RULEUBA_None',
            CollideFriendly = false,
            Damage = 200,
            DamageFriendly = true,
            DamageRadius = 7.0,
            DamageType = 'Normal',
            DisplayName = 'Death Acid Crater Detonation',
            DoTTime = 4.0,
            DoTPulses = 5,
            InitialDamage = 2500,
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
}"""
    bp_xra0310 = re.sub(r'(\s+Turreted = false,\s+WeaponCategory = \'Kamikaze\',\s+\},\s+)(\},\s+\})', r'\1' + death_weapon_heavy, bp_xra0310)

write_file(os.path.join(units_dir, "XRA0310", "XRA0310_unit.bp"), bp_xra0310)

script_xra0310 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local Weapon = import('/lua/sim/weapon.lua').Weapon
local DefaultDamage = import('/lua/sim/DefaultDamage.lua')
local AreaDoTThread = DefaultDamage.AreaDoTThread
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

---@class BigDodoSuicideWeapon : Weapon
local BigDodoSuicideWeapon = ClassWeapon(Weapon) {
    OnFire = function(self)
        local unit = self.unit
        if unit.Dead or unit.Detonated then return end

        local cmd = unit:GetCommandQueue()[1]
        -- If player ordered an attack on a specific unit, only detonate on that unit or in touch range
        if cmd and cmd.commandType == 10 and cmd.target and not cmd.target.Dead then
            local currentTarget = self:GetCurrentTarget()
            if currentTarget ~= cmd.target then
                local myPos = unit:GetPosition()
                local tPos = cmd.target:GetPosition()
                local dx = myPos[1] - tPos[1]
                local dz = myPos[3] - tPos[3]
                if (dx*dx + dz*dz) > 12.0 then
                    return
                end
            end
        end

        unit:DetonateHeavyAcid()
    end,
}

---@class DeathHeavyAcidWeapon : Weapon
local DeathHeavyAcidWeapon = ClassWeapon(Weapon) {
    OnCreate = function(self)
        Weapon.OnCreate(self)
        self:SetWeaponEnabled(false)
    end,

    Fire = function(self)
        local unit = self.unit
        if not unit.Detonated then
            unit:DetonateHeavyAcid()
        end
    end,
}

---@class XRA0310 : CWalkingLandUnit
XRA0310 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Suicide = ClassWeapon(BigDodoSuicideWeapon) {},
        DeathWeapon = ClassWeapon(DeathHeavyAcidWeapon) {},
    },

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
        self.Trash:Add(ForkThread(self.TrackTargetThread, self))
    end,

    TrackTargetThread = function(self)
        local navigator = self:GetNavigator()
        local weapon = self:GetWeaponByLabel('Suicide')

        while not IsDestroyed(self) do
            -- Disable weapon when simply moving so Behemoth Dodo can reach deep target inside base
            if weapon then
                if self:IsUnitState('Attacking') or self:IsUnitState('BeingCaptured') or self:IsUnitState('BeingReclaimed') then
                    weapon:SetEnabled(true)
                else
                    weapon:SetEnabled(false)
                end
            end

            -- Speed through goal straight into enemy target
            local cmd = self:GetCommandQueue()[1]
            if cmd and cmd.commandType == 10 then
                local target = cmd.target
                if target and not target.Dead then
                    navigator:SetDestUnit(target)
                    navigator:SetSpeedThroughGoal(true)
                end
            end

            WaitTicks(3)
        end
    end,

    OnProductionPaused = function(self)
        -- Manual Detonate UI Button
        self:DetonateHeavyAcid()
    end,

    DetonateHeavyAcid = function(self)
        if self.Detonated then return end
        self.Detonated = true
        local army = self.Army
        local pos = self:GetPosition()

        -- Cataclysmic initial explosion damage
        DamageArea(self, pos, 6.0, 2500, 'Normal', false, false)

        -- Massive lingering corrosive acid lake (5 pulses of 200 damage over 4.0s, radius 7.0)
        ForkThread(AreaDoTThread, self, pos, 5, 0.8, 7.0, 200, 'Normal', false, false)

        -- Visual huge green acid crater
        for _, emit in HeavyAcidKamikazeEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(3.5)
        end

        self:PlayUnitSound('Destroyed')
        if not self.Dead then
            self:Kill()
        end
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        if not self.Detonated then
            self:DetonateHeavyAcid()
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    DoDeathWeapon = function(self)
        if self:IsBeingBuilt() then return end
        if not self.Detonated then
            self:DetonateHeavyAcid()
        end
        CWalkingLandUnit.DoDeathWeapon(self)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        -- Handled by DetonateHeavyAcid visuals
    end,
}

TypeClass = XRA0310
"""
write_file(os.path.join(units_dir, "XRA0310", "XRA0310_script.lua"), script_xra0310)


# ===========================================================================
# 3. FIX EMP PLASMA ARTILLERY (XRA0307)
#    - Add massive DamageToShields = 7000 (Aeon Absolver style shield collapse)
#    - Add standard FAF Buffs with STUN (10s duration, 7.0 radius)
#    - Update projectile script to handle direct shield impact damage
# ===========================================================================
print("\n[4/7] Updating XRA0307 (Bio-EMP Artillery Spire & Projectile)...")
bp_xra0307 = read_file(os.path.join(units_dir, "XRA0307", "XRA0307_unit.bp"))

# Update Display Abilities
if "ability_custom_shielddisrupt" not in bp_xra0307:
    ability_marker = "Display = {"
    abilities_code = """Display = {
        Abilities = {
            '<LOC ability_artillery>Artillery',
            '<LOC ability_stun>EMP Weapon',
            '<LOC ability_custom_shielddisrupt>Shield Disruptor',
        },"""
    bp_xra0307 = bp_xra0307.replace(ability_marker, abilities_code)

# Add DamageToShields and Buffs to Weapon
if "DamageToShields" not in bp_xra0307:
    old_dmg = """            Damage = 350,
            DamageFriendly = false,
            DamageRadius = 6.0,
            DamageType = 'Normal',"""
    new_dmg = """            Damage = 450,
            DamageToShields = 7000,
            DamageFriendly = false,
            DamageRadius = 7.0,
            DamageType = 'Normal',
            Buffs = {
                {
                    Add = { OnImpact = true },
                    AppliedToTarget = true,
                    BuffType = 'STUN',
                    Duration = 10,
                    Radius = 7.0,
                    TargetAllow = 'ALLUNITS',
                    TargetDisallow = 'WALL',
                },
            },"""
    bp_xra0307 = bp_xra0307.replace(old_dmg, new_dmg)

write_file(os.path.join(units_dir, "XRA0307", "XRA0307_unit.bp"), bp_xra0307)

# Update XRA_ElectroShell01_script.lua
script_emp_proj = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile
local CreateEmitterAtEntity = CreateEmitterAtEntity
local DamageArea = DamageArea

local EMPHitEffects = {
    '/effects/emitters/cybran_empgrenade_hit_01_emit.bp',
    '/effects/emitters/cybran_empgrenade_hit_02_emit.bp',
    '/effects/emitters/build_sparks_blue_02_emit.bp',
}

XRA_ElectroShell01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/seraphim_aireau_autocannon_polytrail_01_emit.bp',

    OnImpact = function(self, targetType, targetEntity)
        local army = self:GetArmy()
        local pos = self:GetPosition()
        local launcher = self:GetLauncher()

        for _, emit in EMPHitEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.5)
        end

        -- If impacting a shield dome directly, apply massive 7000 collapse damage
        if targetType == 'Shield' and targetEntity and targetEntity.ApplyDamage then
            targetEntity:ApplyDamage(launcher or self, 7000, pos, 'FAF_AntiShield', false)
        end

        -- Blast wave EMP paralysis & shield collapse in 8.0 radius
        local brain = self:GetAIBrain()
        if brain then
            local targets = brain:GetUnitsAroundPoint(categories.MOBILE + categories.STRUCTURE, pos, 8.0, 'Enemy')
            for _, t in targets do
                if not t.Dead then
                    t:SetStunned(10.0)
                    if t.MyShield and t.MyShield:IsOn() then
                        t.MyShield:ApplyDamage(7000)
                    end
                end
            end
        end

        SinglePolyTrailProjectile.OnImpact(self, targetType, targetEntity)
    end,
}

TypeClass = XRA_ElectroShell01
"""
write_file(os.path.join(proj_dir, "XRA_ElectroShell01", "XRA_ElectroShell01_script.lua"), script_emp_proj)


# ===========================================================================
# 4. FIX VOLCANIC MAGMA WORM (XRA0209)
#    - Add DamageToShields = 850 (plasma shield melting)
#    - Add STUN Buffs (1.5s micro-stun)
#    - Update Magma Shell projectile script for direct shield damage
# ===========================================================================
print("\n[5/7] Updating XRA0209 (Volcanic Magma Worm & Magma Shell)...")
bp_xra0209 = read_file(os.path.join(units_dir, "XRA0209", "XRA0209_unit.bp"))

# Add Abilities
if "ability_stun" not in bp_xra0209:
    bp_xra0209 = bp_xra0209.replace("Display = {", """Display = {
        Abilities = {
            '<LOC ability_amphibious>Amphibious',
            '<LOC ability_stun>EMP Weapon',
        },""")

# Add DamageToShields and Buffs
if "DamageToShields" not in bp_xra0209:
    old_magma_dmg = """            Damage = 320,
            DamageRadius = 3.0,
            DamageType = 'Normal',"""
    new_magma_dmg = """            Damage = 350,
            DamageToShields = 850,
            DamageRadius = 3.5,
            DamageType = 'Normal',
            Buffs = {
                {
                    Add = { OnImpact = true },
                    AppliedToTarget = true,
                    BuffType = 'STUN',
                    Duration = 1.5,
                    Radius = 3.5,
                    TargetAllow = 'MOBILE',
                    TargetDisallow = 'EXPERIMENTAL,COMMAND,WALL',
                },
            },"""
    bp_xra0209 = bp_xra0209.replace(old_magma_dmg, new_magma_dmg)

write_file(os.path.join(units_dir, "XRA0209", "XRA0209_unit.bp"), bp_xra0209)

# Update XRA_MagmaShell01_script.lua
script_magma_proj = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile

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

    OnImpact = function(self, targetType, targetEntity)
        local launcher = self:GetLauncher()
        local pos = self:GetPosition()

        -- Direct impact shield bonus damage
        if targetType == 'Shield' and targetEntity and targetEntity.ApplyDamage then
            targetEntity:ApplyDamage(launcher or self, 850, pos, 'FAF_AntiShield', false)
        end

        -- Magma plasma micro-stun on mobile targets in 3.5 radius
        local brain = self:GetAIBrain()
        if brain then
            local targets = brain:GetUnitsAroundPoint(categories.MOBILE - categories.EXPERIMENTAL - categories.COMMAND, pos, 3.5, 'Enemy')
            for _, t in targets do
                if not t.Dead then
                    t:SetStunned(1.5)
                end
            end
        end

        SinglePolyTrailProjectile.OnImpact(self, targetType, targetEntity)
    end,
}

TypeClass = XRA_MagmaShell01
"""
write_file(os.path.join(proj_dir, "XRA_MagmaShell01", "XRA_MagmaShell01_script.lua"), script_magma_proj)


# ===========================================================================
# 5. FIX OTHER WORMS & ARTILLERY (XRA0208, XRA0202, XRA0309, XRA0302)
# ===========================================================================
print("\n[6/7] Updating XRA0208, XRA0202, XRA0309, & XRA0302 Shield Damage...")

# XRA0208: Burrowing Bio-Worm (Acid Mortar eats shields)
bp_xra0208 = read_file(os.path.join(units_dir, "XRA0208", "XRA0208_unit.bp"))
if "DamageToShields" not in bp_xra0208:
    bp_xra0208 = bp_xra0208.replace("DamageRadius = 3.5,\n            DamageType = 'Normal',",
                                    "DamageRadius = 3.5,\n            DamageToShields = 400,\n            DamageType = 'Normal',")
    write_file(os.path.join(units_dir, "XRA0208", "XRA0208_unit.bp"), bp_xra0208)

# XRA0202: Bio-Mortar Bug (Mobile Artillery shield breaker)
bp_xra0202 = read_file(os.path.join(units_dir, "XRA0202", "XRA0202_unit.bp"))
if "DamageToShields" not in bp_xra0202:
    bp_xra0202 = bp_xra0202.replace("DamageRadius = 3.0,\n            DamageType = 'Normal',",
                                    "DamageRadius = 3.0,\n            DamageToShields = 500,\n            DamageType = 'Normal',")
    write_file(os.path.join(units_dir, "XRA0202", "XRA0202_unit.bp"), bp_xra0202)

# XRA0309: Meteor Cataclysm Spire (Extreme-Range Planetary Artillery)
bp_xra0309 = read_file(os.path.join(units_dir, "XRA0309", "XRA0309_unit.bp"))
if "DamageToShields" not in bp_xra0309:
    bp_xra0309 = bp_xra0309.replace("DamageRadius = 9.0,\n            DamageType = 'Normal',",
                                    "DamageRadius = 9.0,\n            DamageToShields = 8500,\n            DamageType = 'Normal',")
    write_file(os.path.join(units_dir, "XRA0309", "XRA0309_unit.bp"), bp_xra0309)

# XRA0302: Brain Bug Overseer (Psionic Neuro-Disruption)
bp_xra0302 = read_file(os.path.join(units_dir, "XRA0302", "XRA0302_unit.bp"))
if "DamageToShields" not in bp_xra0302:
    bp_xra0302 = bp_xra0302.replace("DamageRadius = 4.0,\n            DamageType = 'Normal',",
                                    "DamageRadius = 4.0,\n            DamageToShields = 1000,\n            DamageType = 'Normal',")
    write_file(os.path.join(units_dir, "XRA0302", "XRA0302_unit.bp"), bp_xra0302)


# ===========================================================================
# 6. RE-PACKAGE MOD ARCHIVE
# ===========================================================================
print(f"\n[7/7] Re-packaging updated mod archive to {export_zip}...")
os.makedirs(os.path.dirname(export_zip), exist_ok=True)
with zipfile.ZipFile(export_zip, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(mod_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(mod_dir))
            z.write(full_path, rel_path)

print(f"\nSUCCESS: All EMP, Shield Disruption, Worm, & Kamikaze Smart Targeting updates applied!")
print(f"Export zip updated: {os.path.getsize(export_zip) / (1024*1024):.2f} MB")
