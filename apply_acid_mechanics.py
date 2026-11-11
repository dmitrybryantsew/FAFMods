import os
import re
import zipfile

mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
units_dir = os.path.join(mod_dir, "units")
proj_dir = os.path.join(mod_dir, "projectiles")
effects_dir = os.path.join(mod_dir, "effects", "emitters")
export_zip = r"E:\Games\FAFMods\exports\RaptorFaction.zip"

print("--- Applying UEF Napalm-Style Acid Mechanics to Raptor Faction ---")

# ===========================================================================
# 1. NEW PROJECTILE: XRA_AcidSpike01
# ===========================================================================
dir_acid_spike = os.path.join(proj_dir, "XRA_AcidSpike01")
os.makedirs(dir_acid_spike, exist_ok=True)

bp_acid_spike = """ProjectileBlueprint {
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
    },
    Display = {
        ImpactEffects = {
            Type = 'Small01',
        },
        Mesh = {
            LODs = {
                {
                    AlbedoName = '/mods/RaptorFaction/units/XRA0108/XRA0108_Albedo.dds',
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
        Weapon = 'Bio Acid Spikes',
    },
    Interface = {
        HelpText = 0,
    },
    Physics = {
        Acceleration = 0,
        DestroyOnWater = true,
        InitialSpeed = 35,
        Lifetime = 2.5,
        MaxSpeed = 35,
        UseGravity = true,
        VelocityAlign = true,
    },
}
"""
with open(os.path.join(dir_acid_spike, "XRA_AcidSpike01_proj.bp"), "w", encoding="utf-8") as f:
    f.write(bp_acid_spike)

script_acid_spike = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile
local CreateEmitterAtEntity = CreateEmitterAtEntity

local AcidSpikeHitEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_acid_splash_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_puddle_01_emit.bp',
}

---@class XRA_AcidSpike01 : SinglePolyTrailProjectile
XRA_AcidSpike01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/default_polytrail_07_emit.bp',
    PolyTrailOffset = 0,

    OnImpact = function(self, targetType, targetEntity)
        local army = self:GetArmy()
        for _, emit in AcidSpikeHitEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(0.5)
        end
        SinglePolyTrailProjectile.OnImpact(self, targetType, targetEntity)
    end,
}

TypeClass = XRA_AcidSpike01
"""
with open(os.path.join(dir_acid_spike, "XRA_AcidSpike01_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_acid_spike)

print("Created projectile XRA_AcidSpike01.")

# ===========================================================================
# 2. UPDATE PROJECTILE: XRA_BioBomb01 (XRA0104 Carpet Bomber)
# ===========================================================================
script_bio_bomb = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile
local CreateEmitterAtEntity = CreateEmitterAtEntity

local AcidBombHitEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_acid_splash_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_puddle_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_bubbles_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_steam_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
}

---@class XRA_BioBomb01 : SinglePolyTrailProjectile
XRA_BioBomb01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/default_polytrail_07_emit.bp',
    PolyTrailOffset = 0,

    OnImpact = function(self, targetType, targetEntity)
        local army = self:GetArmy()
        for _, emit in AcidBombHitEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.2)
        end
        SinglePolyTrailProjectile.OnImpact(self, targetType, targetEntity)
    end,
}

TypeClass = XRA_BioBomb01
"""
with open(os.path.join(proj_dir, "XRA_BioBomb01", "XRA_BioBomb01_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_bio_bomb)

print("Updated projectile XRA_BioBomb01.")

# ===========================================================================
# 3. UPDATE PROJECTILE: XRA_BioMortar01 (XRA0202 & XRA0208)
# ===========================================================================
script_bio_mortar = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile
local CreateEmitterAtEntity = CreateEmitterAtEntity

local AcidMortarHitEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_acid_splash_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_puddle_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_bubbles_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_steam_01_emit.bp',
}

---@class XRA_BioMortar01 : SinglePolyTrailProjectile
XRA_BioMortar01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/default_polytrail_07_emit.bp',
    PolyTrailOffset = 0,

    OnImpact = function(self, targetType, targetEntity)
        local army = self:GetArmy()
        for _, emit in AcidMortarHitEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.4)
        end
        SinglePolyTrailProjectile.OnImpact(self, targetType, targetEntity)
    end,
}

TypeClass = XRA_BioMortar01
"""
with open(os.path.join(proj_dir, "XRA_BioMortar01", "XRA_BioMortar01_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_bio_mortar)

print("Updated projectile XRA_BioMortar01.")

# ===========================================================================
# 4. UPDATE PROJECTILE: XRA_AcidShell01 (XRA0308 Acid Artillery Spire)
# ===========================================================================
script_acid_shell = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile
local CreateEmitterAtEntity = CreateEmitterAtEntity

local AcidArtilleryHitEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_acid_splash_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_puddle_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_bubbles_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_steam_01_emit.bp',
    '/effects/emitters/electron_burst_cloud_gas_01_emit.bp',
}

---@class XRA_AcidShell01 : SinglePolyTrailProjectile
XRA_AcidShell01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/default_polytrail_07_emit.bp',
    PolyTrailOffset = 0,

    OnImpact = function(self, targetType, targetEntity)
        local army = self:GetArmy()
        for _, emit in AcidArtilleryHitEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.8)
        end
        SinglePolyTrailProjectile.OnImpact(self, targetType, targetEntity)
    end,
}

TypeClass = XRA_AcidShell01
"""
with open(os.path.join(proj_dir, "XRA_AcidShell01", "XRA_AcidShell01_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_acid_shell)

print("Updated projectile XRA_AcidShell01.")

# ===========================================================================
# 5. UPDATE SUICIDE SCRIPTS: XRA0103 & XRA0310
# ===========================================================================
script_xra0103 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local Weapon = import('/lua/sim/weapon.lua').Weapon
local DefaultDamage = import('/lua/sim/DefaultDamage.lua')
local AreaDoTThread = DefaultDamage.AreaDoTThread
local DamageArea = DamageArea
local CreateEmitterAtEntity = CreateEmitterAtEntity
local ForkThread = ForkThread

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
        local myUnit = self.unit
        if not myUnit.Detonated then
            myUnit:DetonateAcid()
        end
    end,
}

---@class XRA0103 : CWalkingLandUnit
XRA0103 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Suicide = ClassWeapon(KamikazeAcidWeapon) {},
    },

    DetonateAcid = function(self)
        if self.Detonated then return end
        self.Detonated = true
        local army = self.Army
        local pos = self:GetPosition()

        -- Initial direct explosion damage
        DamageArea(self, pos, 3.5, 500, 'Normal', false, false)

        -- Lingering corrosive acid DoT pool (5 pulses of 50 damage over 3.0s, radius 4.0)
        ForkThread(AreaDoTThread, self, pos, 5, 0.6, 4.0, 50, 'Normal', false, false)

        -- Visual green acid pool + organic splatter
        for _, emit in AcidKamikazeEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.5)
        end

        self:Kill()
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        if not self.Detonated then
            self:DetonateAcid()
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        -- DetonateAcid handles destruction visuals
    end,
}

TypeClass = XRA0103
"""
with open(os.path.join(units_dir, "XRA0103", "XRA0103_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_xra0103)

print("Updated script for XRA0103 (Volatile Acid Tick).")

script_xra0310 = """local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local Weapon = import('/lua/sim/weapon.lua').Weapon
local DefaultDamage = import('/lua/sim/DefaultDamage.lua')
local AreaDoTThread = DefaultDamage.AreaDoTThread
local DamageArea = DamageArea
local CreateEmitterAtEntity = CreateEmitterAtEntity
local ForkThread = ForkThread

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
        local myUnit = self.unit
        if not myUnit.Detonated then
            myUnit:DetonateHeavyAcid()
        end
    end,
}

---@class XRA0310 : CWalkingLandUnit
XRA0310 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Suicide = ClassWeapon(BigDodoSuicideWeapon) {},
    },

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

        self:Kill()
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        if not self.Detonated then
            self:DetonateHeavyAcid()
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}

TypeClass = XRA0310
"""
with open(os.path.join(units_dir, "XRA0310", "XRA0310_script.lua"), "w", encoding="utf-8") as f:
    f.write(script_xra0310)

print("Updated script for XRA0310 (Behemoth Heavy Acid Dodo).")

# ===========================================================================
# 6. UPDATE BLUEPRINTS WITH NAPALM/DOT PARAMETERS
# ===========================================================================
def update_blueprint_weapon(bp_path, updates):
    with open(bp_path, "r", encoding="utf-8") as f:
        content = f.read()

    for key, val in updates.items():
        if isinstance(val, str):
            val_str = f"'{val}'"
        elif isinstance(val, bool):
            val_str = "true" if val else "false"
        else:
            val_str = str(val)

        # If key already exists in Weapon table, replace it
        pattern = rf"({key}\s*=\s*)([^,\n]+)"
        if re.search(pattern, content):
            content = re.sub(pattern, rf"\g<1>{val_str}", content, count=1)
        else:
            # Insert after DisplayName or Damage
            insert_marker = re.search(r"(DisplayName\s*=\s*[^,\n]+,)", content)
            if insert_marker:
                content = content[:insert_marker.end()] + f"\n            {key} = {val_str}," + content[insert_marker.end():]
            else:
                insert_marker2 = re.search(r"(Damage\s*=\s*[^,\n]+,)", content)
                if insert_marker2:
                    content = content[:insert_marker2.end()] + f"\n            {key} = {val_str}," + content[insert_marker2.end():]

    with open(bp_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated blueprint {os.path.basename(bp_path)}")

# XRA0104: Bio-Acid Bomber
update_blueprint_weapon(os.path.join(units_dir, "XRA0104", "XRA0104_unit.bp"), {
    "Damage": 20,
    "InitialDamage": 120,
    "DoTPulses": 6,
    "DoTTime": 3.0,
    "DamageRadius": 3.0,
})

# XRA0103: Volatile Acid Tick
update_blueprint_weapon(os.path.join(units_dir, "XRA0103", "XRA0103_unit.bp"), {
    "Damage": 50,
    "InitialDamage": 500,
    "DoTPulses": 5,
    "DoTTime": 3.0,
    "DamageRadius": 4.0,
})

# XRA0202: Bio-Mortar Bug
update_blueprint_weapon(os.path.join(units_dir, "XRA0202", "XRA0202_unit.bp"), {
    "Damage": 10,
    "InitialDamage": 35,
    "DoTPulses": 5,
    "DoTTime": 2.5,
    "DamageRadius": 3.0,
})

# XRA0208: Burrowing Bio-Worm Heavy Acid Mortar
update_blueprint_weapon(os.path.join(units_dir, "XRA0208", "XRA0208_unit.bp"), {
    "Damage": 25,
    "InitialDamage": 100,
    "DoTPulses": 6,
    "DoTTime": 3.0,
    "DamageRadius": 3.5,
})

# XRA0308: Corrosive Acid Artillery Spire
update_blueprint_weapon(os.path.join(units_dir, "XRA0308", "XRA0308_unit.bp"), {
    "Damage": 30,
    "InitialDamage": 110,
    "DoTPulses": 8,
    "DoTTime": 4.5,
    "DamageRadius": 6.5,
})

# XRA0310: Behemoth Heavy Acid Dodo
update_blueprint_weapon(os.path.join(units_dir, "XRA0310", "XRA0310_unit.bp"), {
    "Damage": 200,
    "InitialDamage": 2500,
    "DoTPulses": 5,
    "DoTTime": 4.0,
    "DamageRadius": 7.0,
})

# XRA0108: Bio-Acid Point Defense Spire
update_blueprint_weapon(os.path.join(units_dir, "XRA0108", "XRA0108_unit.bp"), {
    "ProjectileId": "/mods/RaptorFaction/projectiles/XRA_AcidSpike01/XRA_AcidSpike01_proj.bp",
    "Damage": 10,
    "InitialDamage": 30,
    "DoTPulses": 3,
    "DoTTime": 1.0,
    "DamageRadius": 1.2,
})

# XRA0201: Heavy Raptor Crawler (Acid Stinger Spines)
update_blueprint_weapon(os.path.join(units_dir, "XRA0201", "XRA0201_unit.bp"), {
    "ProjectileId": "/mods/RaptorFaction/projectiles/XRA_AcidSpike01/XRA_AcidSpike01_proj.bp",
    "Damage": 25,
    "InitialDamage": 75,
    "DoTPulses": 4,
    "DoTTime": 1.5,
    "DamageRadius": 1.5,
})

# ===========================================================================
# 7. RE-PACKAGE MOD ARCHIVE
# ===========================================================================
print(f"\nPackaging updated standalone mod to {export_zip}...")
os.makedirs(os.path.dirname(export_zip), exist_ok=True)
with zipfile.ZipFile(export_zip, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(mod_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(mod_dir))
            z.write(full_path, rel_path)

print(f"Mod successfully packaged! Archive size: {os.path.getsize(export_zip) / (1024*1024):.2f} MB")
