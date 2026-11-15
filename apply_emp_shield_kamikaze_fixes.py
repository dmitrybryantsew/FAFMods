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
# 2. FIX KAMIKAZE UNITS (XRA0103, XRA0203, XRA0213, XRA0310, XRA0320)
#    - Standard Cybran Fire Beetle (XRL0302) architecture
#    - Suicide trigger weapon (Label = 'Suicide') calls unit:Kill()
#    - DeathWeapon (Label = 'DeathWeapon', FireOnDeath = true) handles area damage, effects, and unit:Destroy()
#    - Eliminates double-death glitches, target-check lockouts, and missing damage
# ===========================================================================
import apply_kamikaze_complete_fix



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
