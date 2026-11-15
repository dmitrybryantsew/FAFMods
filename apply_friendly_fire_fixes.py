import os
import re
import zipfile

MOD_DIR = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
UNITS_DIR = os.path.join(MOD_DIR, "units")
PROJ_DIR = os.path.join(MOD_DIR, "projectiles")
WORKSPACE_DIR = r"E:\Games\FAFMods"

print("=================================================================")
print("Applying Friendly Fire Fixes for Brood Swarm Bomber and Bio-Zeppelin")
print("=================================================================")

# ---------------------------------------------------------------------------
# 1. Update XRA0204 (Brood Swarm Bomber) unit blueprint in MOD_DIR
# ---------------------------------------------------------------------------
bp_xra0204 = os.path.join(UNITS_DIR, "XRA0204", "XRA0204_unit.bp")
if os.path.exists(bp_xra0204):
    with open(bp_xra0204, "r", encoding="utf-8") as f:
        content = f.read()

    # Ensure CollideFriendly = false and DamageFriendly = false in Weapon Bomb
    old_block = """            Damage = 150,
            DamageRadius = 3.0,"""
    new_block = """            CollideFriendly = false,
            Damage = 150,
            DamageFriendly = false,
            DamageRadius = 3.0,"""
    if "DamageFriendly = false" not in content:
        content = content.replace(old_block, new_block)
        with open(bp_xra0204, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated MOD_DIR XRA0204_unit.bp (DamageFriendly = false)")
    else:
        print("MOD_DIR XRA0204_unit.bp already has DamageFriendly = false")
else:
    print(f"Warning: {bp_xra0204} not found!")

# ---------------------------------------------------------------------------
# 2. Update XRA0227 (Bio-Zeppelin Blimpy) unit blueprint in MOD_DIR
# ---------------------------------------------------------------------------
bp_xra0227 = os.path.join(UNITS_DIR, "XRA0227", "XRA0227_unit.bp")
if os.path.exists(bp_xra0227):
    with open(bp_xra0227, "r", encoding="utf-8") as f:
        content = f.read()

    old_block = """            Damage = 220,
            DamageRadius = 3.5,"""
    new_block = """            Damage = 220,
            DamageFriendly = false,
            DamageRadius = 3.5,"""
    if "DamageFriendly = false" not in content:
        content = content.replace(old_block, new_block)
        with open(bp_xra0227, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated MOD_DIR XRA0227_unit.bp (DamageFriendly = false)")
    else:
        print("MOD_DIR XRA0227_unit.bp already has DamageFriendly = false")
else:
    print(f"Warning: {bp_xra0227} not found!")

# ---------------------------------------------------------------------------
# 3. Update XRA0402 (Aerial Dreadnought Titan) unit blueprint in MOD_DIR
# ---------------------------------------------------------------------------
bp_xra0402_mod = os.path.join(UNITS_DIR, "XRA0402", "XRA0402_unit.bp")
if os.path.exists(bp_xra0402_mod):
    with open(bp_xra0402_mod, "r", encoding="utf-8") as f:
        content = f.read()

    old_block = """            CollideFriendly = false,
            Damage = 100,
            DamageRadius = 4.0,"""
    new_block = """            CollideFriendly = false,
            Damage = 100,
            DamageFriendly = false,
            DamageRadius = 4.0,"""
    if "DamageFriendly = false,\n            DamageRadius = 4.0" not in content:
        content = content.replace(old_block, new_block)
        with open(bp_xra0402_mod, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated MOD_DIR XRA0402_unit.bp (DamageFriendly = false on BroodBombDrop)")
    else:
        print("MOD_DIR XRA0402_unit.bp already has DamageFriendly = false")

# ---------------------------------------------------------------------------
# 4. Update XRA0222 (Brood Mortar Bug) unit blueprint in MOD_DIR
# ---------------------------------------------------------------------------
bp_xra0222_mod = os.path.join(UNITS_DIR, "XRA0222", "XRA0222_unit.bp")
if os.path.exists(bp_xra0222_mod):
    with open(bp_xra0222_mod, "r", encoding="utf-8") as f:
        content = f.read()

    old_block = """              CollideFriendly = false,
              Damage = 50,
              DamageRadius = 3.0,"""
    new_block = """              CollideFriendly = false,
              Damage = 50,
              DamageFriendly = false,
              DamageRadius = 3.0,"""
    if "DamageFriendly = false" not in content:
        content = content.replace(old_block, new_block)
        with open(bp_xra0222_mod, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated MOD_DIR XRA0222_unit.bp (DamageFriendly = false)")
    else:
        print("MOD_DIR XRA0222_unit.bp already has DamageFriendly = false")

# ---------------------------------------------------------------------------
# 5. Update XRA_BroodEggBomb01_script.lua in MOD_DIR
# ---------------------------------------------------------------------------
script_brood_path = os.path.join(PROJ_DIR, "XRA_BroodEggBomb01", "XRA_BroodEggBomb01_script.lua")
new_script_brood = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile
local PlatoonAI = import('/mods/RaptorFaction/lua/RaptorPlatoonAI.lua')

---@class XRA_BroodEggBomb01 : SinglePolyTrailProjectile
XRA_BroodEggBomb01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/default_polytrail_01_emit.bp',
    PolyTrailOffset = 0,

    PassDamageData = function(self, damageData)
        SinglePolyTrailProjectile.PassDamageData(self, damageData)
        if self.DamageData then
            self.DamageData.DamageFriendly = false
            self.DamageData.CollideFriendly = false
        end
    end,

    OnImpact = function(self, targetType, targetEntity)
        local army = self:GetArmy()
        local pos = self:GetPosition()

        -- Enforce DamageFriendly false to never harm friendly or newly spawned units
        if self.DamageData then
            self.DamageData.DamageFriendly = false
            self.DamageData.CollideFriendly = false
        end

        -- Execute projectile explosion damage FIRST so impact detonation clears before units emerge
        SinglePolyTrailProjectile.OnImpact(self, targetType, targetEntity)

        if pos then
            CreateEmitterAtEntity(self, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp'):ScaleEmitter(2.5)
        end

        -- Check army unit cap before spawning
        local brain = GetArmyBrain(army)
        local canSpawn = true
        if brain and brain.GetCurrentUnits and brain.GetUnitCap then
            if brain:GetCurrentUnits() >= brain:GetUnitCap() then
                canSpawn = false
            end
        end

        -- Spawn 2 living Raptor Swarmers directly on bomb impact (protected by pcall)
        if canSpawn and pos then
            local spawned = {}
            for i = 1, 2 do
                local angle = math.random() * 2 * math.pi
                local dist = 1.0 + math.random() * 2.5
                local x = pos[1] + math.cos(angle) * dist
                local z = pos[3] + math.sin(angle) * dist
                local y = GetSurfaceHeight(x, z)
                local ok, unit = pcall(CreateUnitHPR, 'XRA0101', army, x, y, z, 0, math.random(0, 360), 0)
                if ok and unit and not unit.Dead then
                    CreateEmitterAtEntity(unit, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp'):ScaleEmitter(1.5)
                    CreateEmitterAtEntity(unit, army, '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp'):ScaleEmitter(1.2)
                    table.insert(spawned, unit)
                end
            end
            if not table.empty(spawned) and brain then
                PlatoonAI.RegisterFieldSpawnedUnits(spawned, brain, pos)
            end
        end
    end,
}

TypeClass = XRA_BroodEggBomb01
"""
with open(script_brood_path, "w", encoding="utf-8") as f:
    f.write(new_script_brood)
print("Updated MOD_DIR XRA_BroodEggBomb01_script.lua (PassDamageData & safe detonation order)")

# ---------------------------------------------------------------------------
# 6. Update XRA_DodoBomb01_script.lua in MOD_DIR
# ---------------------------------------------------------------------------
script_dodo_path = os.path.join(PROJ_DIR, "XRA_DodoBomb01", "XRA_DodoBomb01_script.lua")
new_script_dodo = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile
local PlatoonAI = import('/mods/RaptorFaction/lua/RaptorPlatoonAI.lua')

---@class XRA_DodoBomb01 : SinglePolyTrailProjectile
XRA_DodoBomb01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/default_polytrail_01_emit.bp',
    PolyTrailOffset = 0,

    PassDamageData = function(self, damageData)
        SinglePolyTrailProjectile.PassDamageData(self, damageData)
        if self.DamageData then
            self.DamageData.DamageFriendly = false
            self.DamageData.CollideFriendly = false
        end
    end,

    OnImpact = function(self, targetType, targetEntity)
        local army = self:GetArmy()
        local pos = self:GetPosition()

        -- Enforce DamageFriendly false to never harm friendly or newly spawned units
        if self.DamageData then
            self.DamageData.DamageFriendly = false
            self.DamageData.CollideFriendly = false
        end

        -- Execute projectile explosion damage FIRST so impact detonation clears before units emerge
        SinglePolyTrailProjectile.OnImpact(self, targetType, targetEntity)

        -- Blood cloud impact effect
        if pos then
            CreateEmitterAtEntity(self, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp'):ScaleEmitter(2.2)
        end

        -- Check army unit cap before attempting to hatch the carried raptor
        local brain = GetArmyBrain(army)
        local canSpawn = true
        if brain and brain.GetCurrentUnits and brain.GetUnitCap then
            if brain:GetCurrentUnits() >= brain:GetUnitCap() then
                canSpawn = false
            end
        end

        -- Hatch 1 living Raptor Swarmer (XRA0101 - the exact carried regular raptor) on impact
        if canSpawn and pos then
            local x = pos[1]
            local z = pos[3]
            local y = GetSurfaceHeight(x, z)
            local ok, raptor = pcall(CreateUnitHPR, 'XRA0101', army, x, y, z, 0, math.random(0, 360), 0)
            if ok and raptor and not raptor.Dead then
                CreateEmitterAtEntity(raptor, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp'):ScaleEmitter(1.6)
                CreateEmitterAtEntity(raptor, army, '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp'):ScaleEmitter(1.4)
                if brain then
                    PlatoonAI.RegisterFieldSpawnedUnits({raptor}, brain, pos)
                end
            end
        end
    end,
}

TypeClass = XRA_DodoBomb01
"""
with open(script_dodo_path, "w", encoding="utf-8") as f:
    f.write(new_script_dodo)
print("Updated MOD_DIR XRA_DodoBomb01_script.lua (PassDamageData & safe detonation order)")

# ---------------------------------------------------------------------------
# 7. Update exports/RaptorFaction.zip
# ---------------------------------------------------------------------------
zip_path = os.path.join(WORKSPACE_DIR, "exports", "RaptorFaction.zip")
if os.path.exists(zip_path):
    print("Re-packing updated files into exports/RaptorFaction.zip...")
    temp_zip = zip_path + ".tmp"
    files_to_replace = {
        "raptorfaction/units/xra0204/xra0204_unit.bp": bp_xra0204,
        "raptorfaction/units/xra0227/xra0227_unit.bp": bp_xra0227,
        "raptorfaction/units/xra0402/xra0402_unit.bp": bp_xra0402_mod,
        "raptorfaction/units/xra0222/xra0222_unit.bp": bp_xra0222_mod,
        "raptorfaction/projectiles/xra_broodeggbomb01/xra_broodeggbomb01_script.lua": script_brood_path,
        "raptorfaction/projectiles/xra_dodobomb01/xra_dodobomb01_script.lua": script_dodo_path,
    }

    replaced_count = 0
    with zipfile.ZipFile(zip_path, 'r') as zin, zipfile.ZipFile(temp_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            item_lower = item.filename.lower()
            if item_lower in files_to_replace:
                src_path = files_to_replace[item_lower]
                if os.path.exists(src_path):
                    with open(src_path, 'rb') as sf:
                        zout.writestr(item, sf.read())
                    replaced_count += 1
                    print(f"  Replaced in zip: {item.filename}")
                else:
                    zout.writestr(item, zin.read(item.filename))
            else:
                zout.writestr(item, zin.read(item.filename))
    os.replace(temp_zip, zip_path)
    print(f"Updated exports/RaptorFaction.zip successfully ({replaced_count} files updated).")

print("\n--- All friendly fire fixes applied successfully! ---")
