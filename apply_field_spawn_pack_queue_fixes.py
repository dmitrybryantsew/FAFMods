import os
import shutil
import zipfile

MOD_DIR = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
WORKSPACE_DIR = r"E:\Games\FAFMods"
PROJ_DIR = os.path.join(MOD_DIR, "projectiles")

print("=================================================================")
print("Applying Pack Queue & Order Registration Fixes for Spawned Units")
print("=================================================================")

# ---------------------------------------------------------------------------
# 1. Update XRA_BroodShell01_script.lua in MOD_DIR
# ---------------------------------------------------------------------------
script_shell_path = os.path.join(PROJ_DIR, "XRA_BroodShell01", "XRA_BroodShell01_script.lua")
script_shell_content = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile
local CreateEmitterAtEntity = CreateEmitterAtEntity
local PlatoonAI = import('/mods/RaptorFaction/lua/RaptorPlatoonAI.lua')

local BroodHatchEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
}

---@class XRA_BroodShell01 : SinglePolyTrailProjectile
XRA_BroodShell01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/effects/emitters/seraphim_aireau_autocannon_polytrail_01_emit.bp',

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

        if self.DamageData then
            self.DamageData.DamageFriendly = false
            self.DamageData.CollideFriendly = false
        end

        -- First let projectile impact damage and entity cleanup resolve
        SinglePolyTrailProjectile.OnImpact(self, targetType, targetEntity)

        -- Hatch birth effects
        if pos then
            for _, emit in BroodHatchEffects do
                CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.5)
            end
        end

        -- Check army unit cap before spawning
        local brain = GetArmyBrain(army)
        local canSpawn = true
        if brain and brain.GetCurrentUnits and brain.GetUnitCap then
            if brain:GetCurrentUnits() >= brain:GetUnitCap() then
                canSpawn = false
            end
        end

        -- Spawn living Swarmers from the egg shell safely with pcall
        if canSpawn and pos then
            local count = math.random(1, 2)
            local spawned = {}
            for i = 1, count do
                local angle = math.random() * 2 * math.pi
                local dist = 1.2 + math.random() * 2.0
                local x = pos[1] + math.cos(angle) * dist
                local z = pos[3] + math.sin(angle) * dist
                local y = GetSurfaceHeight(x, z)
                local ok, unit = pcall(CreateUnitHPR, 'XRA0101', army, x, y, z, 0, math.random(0, 360), 0)
                if ok and unit and not unit.Dead then
                    table.insert(spawned, unit)
                end
            end
            if not table.empty(spawned) and brain then
                PlatoonAI.RegisterFieldSpawnedUnits(spawned, brain, pos)
            end
        end
    end,
}

TypeClass = XRA_BroodShell01
"""

os.makedirs(os.path.dirname(script_shell_path), exist_ok=True)
with open(script_shell_path, "w", encoding="utf-8") as f:
    f.write(script_shell_content)
print(f"Updated {script_shell_path} (PlatoonAI.RegisterFieldSpawnedUnits)")

# ---------------------------------------------------------------------------
# 2. Update XRA_BroodEggBomb01_script.lua in MOD_DIR
# ---------------------------------------------------------------------------
script_egg_path = os.path.join(PROJ_DIR, "XRA_BroodEggBomb01", "XRA_BroodEggBomb01_script.lua")
script_egg_content = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile
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

os.makedirs(os.path.dirname(script_egg_path), exist_ok=True)
with open(script_egg_path, "w", encoding="utf-8") as f:
    f.write(script_egg_content)
print(f"Updated {script_egg_path} (PlatoonAI.RegisterFieldSpawnedUnits)")

# ---------------------------------------------------------------------------
# 3. Update XRA_DodoBomb01_script.lua in MOD_DIR
# ---------------------------------------------------------------------------
script_dodo_path = os.path.join(PROJ_DIR, "XRA_DodoBomb01", "XRA_DodoBomb01_script.lua")
script_dodo_content = """local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile
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

os.makedirs(os.path.dirname(script_dodo_path), exist_ok=True)
with open(script_dodo_path, "w", encoding="utf-8") as f:
    f.write(script_dodo_content)
print(f"Updated {script_dodo_path} (PlatoonAI.RegisterFieldSpawnedUnits)")

# ---------------------------------------------------------------------------
# 4. Sync Workspace Lua to MOD_DIR
# ---------------------------------------------------------------------------
for fname in ["RaptorPlatoonAI.lua", "RaptorSpawner.lua", "QueenBossAI.lua", "RaptorTargeting.lua", "RaptorStats.lua"]:
    src = os.path.join(WORKSPACE_DIR, "lua", fname)
    dst = os.path.join(MOD_DIR, "lua", fname)
    if os.path.exists(src):
        shutil.copyfile(src, dst)
        print(f"Synced {fname} to active mod directory: {dst}")

# ---------------------------------------------------------------------------
# 5. Update Generator Scripts (apply_friendly_fire_fixes.py, etc.)
# ---------------------------------------------------------------------------
ff_path = os.path.join(WORKSPACE_DIR, "apply_friendly_fire_fixes.py")
if os.path.exists(ff_path):
    with open(ff_path, "r", encoding="utf-8") as f:
        ff_content = f.read()

    # Ensure PlatoonAI is imported and RegisterFieldSpawnedUnits is called in apply_friendly_fire_fixes.py
    if "PlatoonAI.RegisterFieldSpawnedUnits" not in ff_content:
        # Update new_script_brood
        old_brood_snip = """                local ok, unit = pcall(CreateUnitHPR, 'XRA0101', army, x, y, z, 0, math.random(0, 360), 0)
                if ok and unit and not unit.Dead then
                    CreateEmitterAtEntity(unit, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp'):ScaleEmitter(1.5)
                    CreateEmitterAtEntity(unit, army, '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp'):ScaleEmitter(1.2)
                end
            end
        end"""
        new_brood_snip = """                local ok, unit = pcall(CreateUnitHPR, 'XRA0101', army, x, y, z, 0, math.random(0, 360), 0)
                if ok and unit and not unit.Dead then
                    CreateEmitterAtEntity(unit, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp'):ScaleEmitter(1.5)
                    CreateEmitterAtEntity(unit, army, '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp'):ScaleEmitter(1.2)
                    table.insert(spawned, unit)
                end
            end
            if not table.empty(spawned) and brain then
                PlatoonAI.RegisterFieldSpawnedUnits(spawned, brain, pos)
            end
        end"""
        ff_content = ff_content.replace(
            "local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile",
            "local SinglePolyTrailProjectile = import('/lua/sim/defaultprojectiles.lua').SinglePolyTrailProjectile\nlocal PlatoonAI = import('/mods/RaptorFaction/lua/RaptorPlatoonAI.lua')"
        )
        ff_content = ff_content.replace(
            "        if canSpawn and pos then\n            for i = 1, 2 do",
            "        if canSpawn and pos then\n            local spawned = {}\n            for i = 1, 2 do"
        )
        ff_content = ff_content.replace(old_brood_snip, new_brood_snip)

        old_dodo_snip = """            local ok, raptor = pcall(CreateUnitHPR, 'XRA0101', army, x, y, z, 0, math.random(0, 360), 0)
            if ok and raptor and not raptor.Dead then
                CreateEmitterAtEntity(raptor, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp'):ScaleEmitter(1.6)
                CreateEmitterAtEntity(raptor, army, '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp'):ScaleEmitter(1.4)
                IssueAggressiveMove({raptor}, {pos[1] + math.random(-20, 20), pos[2], pos[3] + math.random(-20, 20)})
            end"""
        new_dodo_snip = """            local ok, raptor = pcall(CreateUnitHPR, 'XRA0101', army, x, y, z, 0, math.random(0, 360), 0)
            if ok and raptor and not raptor.Dead then
                CreateEmitterAtEntity(raptor, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp'):ScaleEmitter(1.6)
                CreateEmitterAtEntity(raptor, army, '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp'):ScaleEmitter(1.4)
                if brain then
                    PlatoonAI.RegisterFieldSpawnedUnits({raptor}, brain, pos)
                end
            end"""
        ff_content = ff_content.replace(old_dodo_snip, new_dodo_snip)

        with open(ff_path, "w", encoding="utf-8") as f:
            f.write(ff_content)
        print("Updated apply_friendly_fire_fixes.py")

# ---------------------------------------------------------------------------
# 6. Repack exports/RaptorFaction.zip
# ---------------------------------------------------------------------------
zip_path = os.path.join(WORKSPACE_DIR, "exports", "RaptorFaction.zip")
if os.path.exists(zip_path):
    print("Re-packing updated files into exports/RaptorFaction.zip...")
    temp_zip = zip_path + ".tmp"
    files_to_replace = {
        "raptorfaction/lua/raptorplatoonai.lua": os.path.join(WORKSPACE_DIR, "lua", "RaptorPlatoonAI.lua"),
        "raptorfaction/lua/raptorspawner.lua": os.path.join(WORKSPACE_DIR, "lua", "RaptorSpawner.lua"),
        "raptorfaction/lua/queenbossai.lua": os.path.join(WORKSPACE_DIR, "lua", "QueenBossAI.lua"),
        "raptorfaction/projectiles/xra_broodshell01/xra_broodshell01_script.lua": script_shell_path,
        "raptorfaction/projectiles/xra_broodeggbomb01/xra_broodeggbomb01_script.lua": script_egg_path,
        "raptorfaction/projectiles/xra_dodobomb01/xra_dodobomb01_script.lua": script_dodo_path,
    }

    replaced_count = 0
    with zipfile.ZipFile(zip_path, 'r') as zin, zipfile.ZipFile(temp_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            item_lower = item.filename.lower()
            if item_lower in files_to_replace:
                src_path = files_to_replace[item_lower]
                with open(src_path, "rb") as f_in:
                    zout.writestr(item, f_in.read())
                replaced_count += 1
            else:
                zout.writestr(item, zin.read(item.filename))

    os.replace(temp_zip, zip_path)
    print(f"Successfully re-packed exports/RaptorFaction.zip (replaced {replaced_count} files)")

print("\nAll pack queue and field spawning fixes applied successfully!")
