import os
import re
import shutil

MOD_DIR = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
WORKSPACE_DIR = r"E:\Games\FAFMods"

print("=================================================================")
print("Applying Raptor Nuke Off-Map Firing & Flight Fixes")
print("=================================================================")

# ---------------------------------------------------------------------------
# 1. Sync Lua targeting & spawner from Workspace to active mod dir
# ---------------------------------------------------------------------------
lua_files = ["RaptorTargeting.lua", "RaptorSpawner.lua"]
for lf in lua_files:
    src = os.path.join(WORKSPACE_DIR, "lua", lf)
    dst = os.path.join(MOD_DIR, "lua", lf)
    if os.path.exists(src):
        shutil.copyfile(src, dst)
        print(f"Synced {lf} -> {dst}")
    else:
        print(f"ERROR: {src} not found!")

# ---------------------------------------------------------------------------
# 2. Update XRA_BioNuke01_proj.bp (TurnRate = 0)
# ---------------------------------------------------------------------------
nuke_bp_path = os.path.join(MOD_DIR, "projectiles", "XRA_BioNuke01", "XRA_BioNuke01_proj.bp")
if os.path.exists(nuke_bp_path):
    with open(nuke_bp_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Ensure TurnRate in Physics is 0 (matching standard strategic ICBM nukes)
    content = re.sub(r'TurnRate\s*=\s*\d+', 'TurnRate = 0', content)
    with open(nuke_bp_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated XRA_BioNuke01_proj.bp: TurnRate = 0 (prevents premature unguided curvature)")
else:
    print(f"WARNING: {nuke_bp_path} not found!")

# ---------------------------------------------------------------------------
# 3. Update XRA_BioNuke01_script.lua (Robust FAF Nuke MovementThread & Boundary Watchdog)
# ---------------------------------------------------------------------------
nuke_script_path = os.path.join(MOD_DIR, "projectiles", "XRA_BioNuke01", "XRA_BioNuke01_script.lua")
nuke_script_content = """local NukeProjectile = import('/lua/sim/DefaultProjectiles.lua').NukeProjectile

---@class XRA_BioNuke01 : NukeProjectile
XRA_BioNuke01 = ClassProjectile(NukeProjectile) {
    BeamName = '/effects/emitters/missile_exhaust_fire_beam_06_emit.bp',
    PolyTrail = '/mods/RaptorFaction/effects/emitters/raptor_spore_polytrail_01_emit.bp',

    InitialEffects = {
        '/mods/RaptorFaction/effects/emitters/raptor_acid_steam_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_creep_spores_01_emit.bp',
        '/effects/emitters/nuke_munition_launch_trail_02_emit.bp',
    },
    LaunchEffects = {
        '/mods/RaptorFaction/effects/emitters/raptor_acid_steam_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_bio_smoke_01_emit.bp',
        '/effects/emitters/nuke_munition_launch_trail_03_emit.bp',
        '/effects/emitters/nuke_munition_launch_trail_05_emit.bp',
    },
    ThrustEffects = {
        '/mods/RaptorFaction/effects/emitters/raptor_spore_polytrail_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_creep_spores_01_emit.bp',
        '/effects/emitters/nuke_munition_launch_trail_04_emit.bp',
    },

    OnCreate = function(self)
        NukeProjectile.OnCreate(self)
        self.effectEntityPath = '/mods/RaptorFaction/effects/entities/XRA_BioNukeEffect01/XRA_BioNukeEffect01_proj.bp'
        self:LauncherCallbacks()
    end,

    ---Robust strategic nuclear missile movement thread:
    ---1. Climbs vertically to stratosphere altitude (7.8s)
    ---2. Pitches horizontally to target heading (2.1s @ 45 deg/s)
    ---3. Cruises flat at high altitude (TurnRate = 0)
    ---4. Dives steeply (TurnRate = 65+) straight down into target upon arrival (dist <= 32)
    ---5. Hard boundary and ground watchdog: detonates immediately if reaching map border or terrain
    MovementThread = function(self)
        self.Nuke = true
        self:CreateEffects(self.InitialEffects, self.Army, 1)

        -- Initial vertical ascent to gain altitude clear of terrain
        self:TrackTarget(false)
        WaitTicks(26)
        self:SetCollision(true)
        self:CreateEffects(self.LaunchEffects, self.Army, 1)
        WaitTicks(26)
        self:CreateEffects(self.ThrustEffects, self.Army, 3)
        WaitTicks(26)

        -- Turn towards target heading and level out to horizontal cruise
        self:TrackTarget(true)
        self:SetDestroyOnWater(true)
        self:SetTurnRate(45)
        WaitTicks(21)

        -- Freeze turn rate for flat high-altitude cruise towards target
        self:SetTurnRate(0)
        self:SetAcceleration(0.001)
        self.WaitTime = 6

        local lastDist = 999999
        local turningDown = false

        while not self:BeenDestroyed() do
            local dist = self:GetDistanceToTarget()
            local mpos = self:GetPosition()

            -- 1. HARD BOUNDARY WATCHDOG: Detonate immediately if approaching map edges
            local mapW = (ScenarioInfo and ScenarioInfo.size and ScenarioInfo.size[1]) or 1024
            local mapH = (ScenarioInfo and ScenarioInfo.size and ScenarioInfo.size[2]) or 1024
            local pa = ScenarioInfo and ScenarioInfo.PlayableArea
            local minX = (pa and pa[1]) or 0
            local minZ = (pa and pa[2]) or 0
            local maxX = (pa and pa[3]) or mapW
            local maxZ = (pa and pa[4]) or mapH
            local margin = 15

            if mpos[1] <= (minX + margin) or mpos[1] >= (maxX - margin) or
               mpos[3] <= (minZ + margin) or mpos[3] >= (maxZ - margin) then
                self:OnImpact('Terrain', nil)
                return
            end

            -- 2. HARD TERRAIN WATCHDOG: Detonate if hitting or clipping terrain
            local terrY = GetSurfaceHeight(mpos[1], mpos[3])
            if mpos[2] <= (terrY + 1.5) then
                self:OnImpact('Terrain', nil)
                return
            end

            -- 3. DISTANCE PHASING (standard FAF NukeProjectile profile)
            if dist > 150 then
                if not turningDown then
                    self:SetTurnRate(0)
                end
                self.WaitTime = 4
            elseif dist > 75 and dist <= 150 then
                if not turningDown then
                    self:SetTurnRate(0)
                end
                self.WaitTime = 3
            elseif dist > 32 and dist <= 75 then
                self.WaitTime = 2
            elseif dist <= 32 then
                -- Target arrival: pitch down steeply to plunge vertically into target
                turningDown = true
                self:SetTurnRate(65)
                self.WaitTime = 1
            end

            -- 4. OVERSHOOT WATCHDOG: If closest approach passed, plunge vertically down
            if dist > lastDist and (lastDist < 65 or turningDown) then
                turningDown = true
                self:SetTurnRate(90)
                self.WaitTime = 1
            end

            lastDist = dist
            WaitTicks(self.WaitTime)
        end
    end,

    ---Gets the horizontal distance from the nuke to the target position
    GetDistanceToTarget = function(self)
        local tpos = self:GetCurrentTargetPosition()
        if not tpos or (tpos[1] == 0 and tpos[3] == 0) then
            return 999999
        end
        local mpos = self:GetPosition()
        return VDist2(mpos[1], mpos[3], tpos[1], tpos[3])
    end,

    OnImpact = function(self, targetType, targetEntity)
        local ok, err = pcall(NukeProjectile.OnImpact, self, targetType, targetEntity)
        if not ok then
            WARN("XRA_BioNuke01 OnImpact error: " .. tostring(err))
        end
        self:Destroy()
    end,

    DoTakeDamage = function(self, instigator, amount, vector, damageType)
        if damageType == 'AntiNuke' then
            self:Destroy()
        else
            NukeProjectile.DoTakeDamage(self, instigator, amount, vector, damageType)
        end
    end,
}

TypeClass = XRA_BioNuke01
"""

with open(nuke_script_path, "w", encoding="utf-8") as f:
    f.write(nuke_script_content)
print(f"Updated {nuke_script_path} with robust trajectory and boundary watchdog")

# ---------------------------------------------------------------------------
# 4. Update XRA0304_script.lua (Autonomous silo targeting & clearing)
# ---------------------------------------------------------------------------
silo_script_path = os.path.join(MOD_DIR, "units", "XRA0304", "XRA0304_script.lua")
silo_script_content = """local RaptorCreep = import('/mods/RaptorFaction/lua/RaptorCreep.lua')
local Targeting = import('/mods/RaptorFaction/lua/RaptorTargeting.lua')
local CStructureUnit = import('/lua/cybranunits.lua').CStructureUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class XRA0304 : CStructureUnit
XRA0304 = ClassUnit(CStructureUnit) {
    Weapons = {
        NukeMissiles = ClassWeapon(DefaultProjectileWeapon) {},
    },

    OnCreate = function(self)
        CStructureUnit.OnCreate(self)
        self.IdleAnim = CreateAnimator(self)
        self.IdleAnim:PlayAnim('/mods/RaptorFaction/units/XRA0304/XRA0304_Aidle.sca', true)
        self.Trash:Add(self.IdleAnim)

        if self:GetFractionComplete() == 1.0 then
            RaptorCreep.StartCreepNode(self, 36, 1.0)
            self:StartAutoBuildThread()
        end
    end,

    OnStopBeingBuilt = function(self, builder, layer)
        CStructureUnit.OnStopBeingBuilt(self, builder, layer)
        if not self.CreepNode then
            RaptorCreep.StartCreepNode(self, 36, 1.0)
        end
        self:StartAutoBuildThread()
    end,

    StartAutoBuildThread = function(self)
        if self.AutoBuildThreadActive then return end
        self.AutoBuildThreadActive = true
        self:ForkThread(self.AutoBuildTimerThread)
    end,

    AutoBuildTimerThread = function(self)
        local AIBehaviors = import('/lua/ai/aibehaviors.lua')
        local brain = self:GetAIBrain()
        local isHuman = brain and brain.BrainType == 'Human'

        -- Initial grace period before timer ticks
        WaitSeconds(60)

        while not self.Dead do
            WaitSeconds(300) -- 5 minutes standard build timer
            if not self.Dead then
                local currentAmmo = self:GetNukeSiloAmmoCount()
                local maxAmmo = (self.Blueprint.Weapon and self.Blueprint.Weapon[1].MaxProjectileStorage) or 5

                -- If not currently building via UI queue, auto-replenish on timer
                if currentAmmo < maxAmmo and not self:IsUnitState('Building') then
                    self:GiveNukeSiloAmmo(1)
                    currentAmmo = currentAmmo + 1
                end

                -- Autonomous targeting for AI armies (if not already managed by RaptorSpawner)
                if not self.BioNukeThreadRunning and not isHuman and currentAmmo >= 1 then
                    -- Pass isAir = true because ICBM missile flies over any terrain/water
                    local targetPos = Targeting.GetWeightedEnemyTarget(self:GetArmy(), self:GetPosition(), true)
                    if not targetPos or not Targeting.IsPositionValidAndOnMap(targetPos, 25) then
                        if AIBehaviors and AIBehaviors.GetHighestThreatClusterLocation then
                            local threatPos = AIBehaviors.GetHighestThreatClusterLocation(brain, self)
                            if threatPos and Targeting.IsPositionValidAndOnMap(threatPos, 25) then
                                targetPos = threatPos
                            end
                        end
                    end
                    if not targetPos or not Targeting.IsPositionValidAndOnMap(targetPos, 25) then
                        targetPos = Targeting.GetFallbackEnemyTarget(self:GetArmy(), true)
                    end

                    if targetPos and Targeting.IsPositionValidAndOnMap(targetPos, 25) then
                        IssueNuke({self}, targetPos)
                        WaitSeconds(12)
                        if not self.Dead then
                            IssueClearCommands({self})
                        end
                    end
                end
            end
        end
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(5.0)
        end
        CStructureUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        local scale = 5.0 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}

TypeClass = XRA0304
"""

with open(silo_script_path, "w", encoding="utf-8") as f:
    f.write(silo_script_content)
print(f"Updated {silo_script_path} with isAir=true, boundary validation, and post-launch command clear")

print("\nAll Raptor Nuke fixes applied and synced successfully!")
