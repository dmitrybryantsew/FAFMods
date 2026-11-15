-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/lua/RaptorPlatoonAI.lua
-- **  Author   :  Ported from Beyond All Reason to FAF
-- **  Summary  :  Platoon squad formation, pack centroid cohesion regrouping,
-- **              and individual behavioral traits (Skirmish, Berserk, Coward,
-- **              Spectre Blink, Healer Aura, Kamikaze).
-- **
-- ****************************************************************************

local Targeting = import('/mods/RaptorFaction/lua/RaptorTargeting.lua')
local okNav, NavUtils = pcall(import, '/lua/sim/NavUtils.lua')

---Safely checks if a unit is idle without throwing on non-existent methods
---@param u Unit
---@return boolean
local function IsUnitIdle(u)
    if not u or u.Dead or (u.BeenDestroyed and u:BeenDestroyed()) then return false end
    if u.IsIdleState then
        return u:IsIdleState()
    end
    if u.GetCommandQueue then
        local q = u:GetCommandQueue()
        return not q or table.empty(q)
    end
    return false
end

-- ---------------------------------------------------------------------------
-- 1. PLATOON SQUAD CENTROID & REGROUPING ENGINE
-- ---------------------------------------------------------------------------

---Checks if any unit in the platoon is actively firing, targeting a valid reachable enemy, or recently took damage
---@param platoon Platoon
---@param isAir boolean|nil If true, caller is an aerial squad and can engage water/seabed targets
---@return boolean
function IsPlatoonInCombat(platoon, isAir)
    local units = platoon:GetPlatoonUnits()
    if not units or table.empty(units) then return false end
    local currentTime = GetGameTimeSeconds()
    for _, u in units do
        if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
            -- Check if unit has active target or recent damage timestamp (< 6s)
            local hasTarget = false
            if u.GetTargetEntity and u:GetTargetEntity() then
                local tgt = u:GetTargetEntity()
                if tgt and not tgt.Dead and (not tgt.BeenDestroyed or not tgt:BeenDestroyed()) then
                    -- If target is underwater on seabed or submerged, raptors cannot attack it
                    if Targeting.IsTargetUnderwater(tgt) then
                        hasTarget = false
                    elseif not isAir and Targeting.IsTargetAirOnly(tgt) then
                        hasTarget = false
                    else
                        hasTarget = true
                    end
                end
            end
            if hasTarget or (u.LastDamagedTime and (currentTime - u.LastDamagedTime) < 6.0) then
                return true
            end
        end
    end
    return false
end

---Generates a multi-vector approach corridor (Center, Left Flank, Right Flank)
---@param startPos Vector3
---@param targetPos Vector3
---@param flankMode string 'center' | 'left' | 'right'
---@return table route Array of Vector waypoints
function GenerateFlankingRoute(startPos, targetPos, flankMode)
    local route = {}
    if not startPos or not targetPos then return route end

    local dx = targetPos[1] - startPos[1]
    local dz = targetPos[3] - startPos[3]
    local dist = math.sqrt(dx * dx + dz * dz)

    if dist < 60.0 or not flankMode or flankMode == 'center' then
        table.insert(route, targetPos)
        return route
    end

    -- Normalize direct vector
    local nx = dx / dist
    local nz = dz / dist

    -- Perpendicular normal vector (-nz, nx)
    local px = -nz
    local pz = nx

    local sideMult = (flankMode == 'left') and 1 or -1
    local flankOffset = math.min(120.0, dist * 0.35) * sideMult

    -- Midpoint waypoint offset to the flank
    local mx = startPos[1] + (dx * 0.5) + (px * flankOffset)
    local mz = startPos[3] + (dz * 0.5) + (pz * flankOffset)

    -- Clamp within playable map boundaries with margin
    local mapW = (ScenarioInfo and ScenarioInfo.size and ScenarioInfo.size[1]) or 1024
    local mapH = (ScenarioInfo and ScenarioInfo.size and ScenarioInfo.size[2]) or 1024
    mx = math.max(16, math.min(mapW - 16, mx))
    mz = math.max(16, math.min(mapH - 16, mz))
    local my = GetSurfaceHeight(mx, mz)

    table.insert(route, Vector(mx, my, mz))
    table.insert(route, targetPos)
    return route
end

---Generates a high-speed approach corridor across the FAF NavMesh.
---Decomposes long-distance moves into coarse waypoints (35-70 units apart)
---so the C++ engine pathfinder solves local line-of-sight hops in <0.01ms with zero queue freeze.
---@param startPos Vector3
---@param targetPos Vector3
---@param layer string|nil 'Land' | 'Amphibious' | 'Air'
---@param flankMode string|nil 'center' | 'left' | 'right'
---@return table route Array of Vector waypoints
function GetNavCorridor(startPos, targetPos, layer, flankMode)
    local route = {}
    if not startPos or not targetPos then return route end

    layer = layer or 'Land'

    -- Air units fly straight across terrain; standard flanking route works best
    if layer == 'Air' then
        return GenerateFlankingRoute(startPos, targetPos, flankMode)
    end

    if okNav and NavUtils then
        if not NavUtils.IsGenerated() then
            pcall(NavUtils.Generate)
        end

        if NavUtils.IsGenerated() and NavUtils.CanPathTo(layer, startPos, targetPos) then
            local positions, posCount = NavUtils.PathTo(layer, startPos, targetPos)
            if positions and posCount and posCount > 0 then
                local lastPos = startPos
                for i = 1, posCount do
                    local pt = positions[i]
                    if pt then
                        local px = pt[1]
                        local pz = pt[3]
                        local dx = px - lastPos[1]
                        local dz = pz - lastPos[3]
                        local dist = math.sqrt(dx * dx + dz * dz)

                        -- Keep waypoints spaced at least 35 units apart (or final waypoint)
                        if dist >= 35.0 or i == posCount then
                            -- Add slight organic lateral jitter (±4m) to intermediate points
                            -- so swarms form a broad front instead of a single-file conga line
                            if i < posCount then
                                px = px + (math.random() * 8.0 - 4.0)
                                pz = pz + (math.random() * 8.0 - 4.0)
                            end
                            local py = GetSurfaceHeight(px, pz)
                            table.insert(route, Vector(px, py, pz))
                            lastPos = { px, py, pz }
                        end
                    end
                end

                if table.getn(route) > 0 then
                    -- Append the final destination if far from the last waypoint
                    local lastWp = route[table.getn(route)]
                    local fdx = targetPos[1] - lastWp[1]
                    local fdz = targetPos[3] - lastWp[3]
                    if (fdx * fdx + fdz * fdz) > (16.0 * 16.0) then
                        table.insert(route, targetPos)
                    end
                    return route
                end
            end
        end
    end

    -- Fallback to flanking route if NavMesh unavailable or off-mesh
    return GenerateFlankingRoute(startPos, targetPos, flankMode)
end

---Priority Decapitation Sniping: Hunts down game-ending Experimentals, Strategic Artillery, and Paragons
---@param platoon Platoon
---@param isAir boolean|nil
---@return boolean wasPriorityFound
function PlatoonHuntPriorityThreat(platoon, isAir)
    if not platoon or not platoon.FindClosestUnit then return false end
    local targetCategory = categories.EXPERIMENTAL + (categories.STRATEGIC * categories.ARTILLERY)
    if not isAir then
        targetCategory = targetCategory - categories.NAVAL - categories.SUBMERSIBLE
    end
    local ok, target = pcall(function()
        return platoon:FindClosestUnit('Attack', 'Enemy', true, targetCategory)
    end)
    if ok and target and not target.Dead and (not target.BeenDestroyed or not target:BeenDestroyed()) then
        if Targeting.IsTargetUnderwater(target) then
            return false
        end
        if not isAir and Targeting.IsTargetAirOnly(target) then
            return false
        end
        local tPos = target:GetPosition()
        platoon:Stop()
        platoon:AggressiveMoveToLocation(tPos)
        return true
    end
    return false
end

-- ---------------------------------------------------------------------------
-- 1. WOLFPACK SQUAD ENGINE (RAIDERS & FAST SWARMERS: STALK, STANDOFF & OVERWHELM)
-- ---------------------------------------------------------------------------

---Calculates the maximum direct-fire / defensive weapon range present in the target area
---Excludes strategic nukes and extreme-range planetary artillery to preserve tactical standoff
---@param brain AIBrain
---@param targetPos Vector3
---@param scanRadius number
---@return number maxRange
function GetTargetAreaMaxWeaponRange(brain, targetPos, scanRadius)
    if not brain or not targetPos then return 0 end
    local r = scanRadius or 50.0
    local enemies = brain:GetUnitsAroundPoint(categories.ALLUNITS - categories.WALL, targetPos, r, 'Enemy')
    if not enemies or table.empty(enemies) then return 0 end

    local maxRange = 0
    for _, e in enemies do
        if e and not e.Dead and (not e.BeenDestroyed or not e:BeenDestroyed()) then
            local bp = e:GetBlueprint()
            if bp and bp.Weapon then
                for _, w in bp.Weapon do
                    if w.MaxRadius and w.MaxRadius > maxRange then
                        -- Exclude strategic artillery, nukes, and anti-nukes from local standoff calculations
                        local isStrategic = w.Artillery or w.NukeWeapon or (bp.CategoriesHash and (bp.CategoriesHash['STRATEGIC'] or bp.CategoriesHash['SILO']))
                        if not isStrategic and w.MaxRadius <= 85.0 then
                            maxRange = w.MaxRadius
                        end
                    end
                end
            end
        end
    end
    return maxRange
end

---Calculates the defensive threat / dangerousness of the target area
---@param brain AIBrain
---@param targetPos Vector3
---@param scanRadius number
---@return number targetDanger
function CalculateTargetDangerousness(brain, targetPos, scanRadius)
    if not brain or not targetPos then return 0 end
    local r = scanRadius or 50.0
    local enemies = brain:GetUnitsAroundPoint(categories.ALLUNITS - categories.WALL, targetPos, r, 'Enemy')
    if not enemies or table.empty(enemies) then return 0 end

    local danger = 0
    for _, e in enemies do
        if e and not e.Dead and (not e.BeenDestroyed or not e:BeenDestroyed()) then
            local hp = e:GetHealth() or 500
            local bp = e:GetBlueprint()
            local cats = (bp and bp.CategoriesHash) or {}

            if cats['DEFENSE'] and cats['STRUCTURE'] then
                -- Static Point Defense / Torpedo / Anti-Surface
                danger = danger + (hp * 0.08) + 40
            elseif cats['COMMAND'] then
                -- Armored Commander (Dangerous Overcharge / Gun)
                danger = danger + (hp * 0.05) + 90
            elseif cats['EXPERIMENTAL'] then
                -- Mobile or Static Experimental
                danger = danger + (hp * 0.06) + 160
            elseif cats['DIRECTFIRE'] or cats['GROUNDATTACK'] then
                -- Mobile Combat Tanks / Bots
                danger = danger + (hp * 0.04) + 15
            else
                -- Pure civilian / unfortified economy (mex, hydro, radar, engineer)
                danger = danger + 2
            end
        end
    end
    return danger
end

---Calculates total allied raptor combat power within the staging / combat zone
---@param brain AIBrain
---@param targetPos Vector3
---@param scanRadius number
---@return number swarmPower
function CalculateLocalSwarmPower(brain, targetPos, scanRadius)
    if not brain or not targetPos then return 0 end
    local r = scanRadius or 65.0
    local raptors = brain:GetUnitsAroundPoint(categories.RAPTOR * categories.MOBILE, targetPos, r, 'Ally')
    if not raptors or table.empty(raptors) then return 0 end

    local power = 0
    for _, u in raptors do
        if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
            local hp = u:GetHealth() or 300
            local bp = u:GetBlueprint()
            local cats = (bp and bp.CategoriesHash) or {}

            if cats['EXPERIMENTAL'] then
                power = power + (hp * 0.06) + 160
            elseif cats['HEAVYASSAULT'] or cats['TECH3'] then
                power = power + (hp * 0.05) + 60
            elseif cats['ARTILLERY'] then
                power = power + 45 + (hp * 0.02)
            else
                -- Fast swarmer / larva / tick / crawler
                power = power + (hp * 0.04) + 15
            end
        end
    end
    return power
end

---Determines safe standoff distance: enemy weapon range + respectable buffer
---Ensures raptors circle outside range so enemy units will NOT try to kite or aggro
---@param brain AIBrain
---@param targetPos Vector3
---@return number standoffDist
function GetStandoffDistance(brain, targetPos)
    local maxRange = GetTargetAreaMaxWeaponRange(brain, targetPos, 50.0)
    if maxRange <= 0 then
        return 0 -- Soft unfortified target! Direct pounce immediately!
    end

    -- Respectable distance buffer: +16 units ensures mobile units cannot kite/step-fire
    local respectableBuffer = 16.0
    local standoffDist = math.max(42.0, maxRange + respectableBuffer)
    return standoffDist
end

local ActiveWolfpacks = {}

---WOLFPACK SQUAD AI (Raiders & Fast Swarmers):
---Runs in 'NoFormation' to unlock 100% native physics speed.
---Sprints to target, checks danger, stalks/circles at weapon-range + respectable buffer,
---and executes simultaneous 360-degree overwhelm attack once critical mass assembles.
---@param platoon Platoon
---@param targetPos Vector3
---@param flankMode string|nil 'center' | 'left' | 'right'
function ManageRaptorWolfpack(platoon, targetPos, flankMode)
    if platoon and platoon.SetFormation then
        platoon:SetFormation('NoFormation')
    end
    if platoon then
        ActiveWolfpacks[platoon] = true
    end
    platoon:ForkThread(WolfpackProwlThread, targetPos, flankMode)
end

function WolfpackProwlThread(platoon, targetPos, flankMode)
    local brain = platoon:GetBrain()
    local army = brain:GetArmyIndex()
    if platoon and platoon.SetFormation then
        platoon:SetFormation('NoFormation')
    end

    local prowlTimer = 0
    local overwhelmTimer = 0
    local orbitAngle = math.random() * 2 * math.pi
    local state = 'SPRINT' -- 'SPRINT' | 'PROWL' | 'OVERWHELM'
    local initialSprintDone = false
    local justRetargeted = false  -- Prevents combat-lock from overriding a fresh SPRINT after retarget

    while platoon and brain:PlatoonExists(platoon) do
        local units = platoon:GetPlatoonUnits()
        if not units or table.empty(units) then break end

        -- Retarget if targetPos is nil or destroyed (land-only target)
        if not targetPos then
            targetPos = Targeting.GetWeightedEnemyTarget(army, nil, false)
            state = 'SPRINT'
            initialSprintDone = false
            prowlTimer = 0
            overwhelmTimer = 0
            justRetargeted = true
        end

        if targetPos then
            platoon.CurrentAssaultPos = targetPos

            -- Calculate standoff distance: enemy weapon range + respectable distance
            local standoffDist = GetStandoffDistance(brain, targetPos)

            -- Compute centroid of active pack
            local px, pz, count = 0, 0, 0
            for _, u in units do
                if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
                    local p = u:GetPosition()
                    px = px + p[1]
                    pz = pz + p[3]
                    count = count + 1
                end
            end
            if count == 0 then break end
            local packX = px / count
            local packZ = pz / count
            local distToTarget = math.sqrt((packX - targetPos[1])^2 + (packZ - targetPos[3])^2)

            -- Centroid Stuck Detection: If pack centroid moved < 4.5 units in 12s while far from target,
            -- pack is blocked by cliff edge, canyon, or water! Force retarget to another land expansion!
            if not platoon.LastCentroidPos then
                platoon.LastCentroidPos = { packX, packZ }
                platoon.StuckTime = 0
            else
                local cdx = packX - platoon.LastCentroidPos[1]
                local cdz = packZ - platoon.LastCentroidPos[2]
                local movedDist = math.sqrt(cdx * cdx + cdz * cdz)
                if movedDist < 4.5 and distToTarget > 20.0 then
                    platoon.StuckTime = (platoon.StuckTime or 0) + 3.0
                    if platoon.StuckTime >= 12.0 then
                        local currentPos = Vector(packX, GetSurfaceHeight(packX, packZ), packZ)
                        targetPos = Targeting.GetWeightedEnemyTarget(army, currentPos, false)
                        IssueClearCommands(units)
                        state = 'SPRINT'
                        initialSprintDone = false
                        prowlTimer = 0
                        overwhelmTimer = 0
                        justRetargeted = true
                        platoon.StuckTime = 0
                        platoon.LastCentroidPos = { packX, packZ }
                    end
                else
                    platoon.LastCentroidPos = { packX, packZ }
                    platoon.StuckTime = 0
                end
            end

            -- If in active combat (taking damage or shooting), fight to the death!
            -- BUT skip this override if we just retargeted — let SPRINT initialize first
            if IsPlatoonInCombat(platoon, false) and not justRetargeted then
                if state ~= 'OVERWHELM' then
                    state = 'OVERWHELM'
                    overwhelmTimer = 0
                end
            end

            -- Clear the retarget guard once we've had a chance to process the new state
            justRetargeted = false

            -- -------------------------------------------------------------
            -- STATE 1: SPRINT (Fast approach along flanking corridor)
            -- -------------------------------------------------------------
            if state == 'SPRINT' then
                if not initialSprintDone then
                    local startPos = Vector(packX, GetSurfaceHeight(packX, packZ), packZ)
                    local route = GetNavCorridor(startPos, targetPos, 'Land', flankMode)
                    platoon.CurrentCorridorRoute = route
                    IssueClearCommands(units)
                    for _, wp in route do
                        IssueAggressiveMove(units, wp)
                    end
                    initialSprintDone = true
                end

                -- Check if arrived at staging threshold
                local triggerDist = (standoffDist > 0) and (standoffDist + 14.0) or 22.0
                if distToTarget <= triggerDist then
                    if standoffDist <= 0 then
                        -- Soft target (unfortified mex, radar, engineers) -> Immediate Overwhelm!
                        state = 'OVERWHELM'
                        overwhelmTimer = 0
                        IssueClearCommands(units)
                        for _, u in units do
                            if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
                                local jx = targetPos[1] + math.random(-12, 12)
                                local jz = targetPos[3] + math.random(-12, 12)
                                IssueAggressiveMove({u}, Vector(jx, GetSurfaceHeight(jx, jz), jz))
                            end
                        end
                    else
                        -- Fortified target -> Transition to Prowl & Stalk!
                        state = 'PROWL'
                        prowlTimer = 0
                        IssueClearCommands(units)
                    end
                else
                    -- For any trailing stragglers or newly joined units that have an empty command queue:
                    -- Guide them to the pack centroid / lead position rather than far-away target!
                    local leadPos = Vector(packX, GetSurfaceHeight(packX, packZ), packZ)
                    for _, u in units do
                        if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
                            local q = u.GetCommandQueue and u:GetCommandQueue()
                            if not q or table.empty(q) then
                                IssueAggressiveMove({u}, leadPos)
                            end
                        end
                    end
                end

            -- -------------------------------------------------------------
            -- STATE 2: PROWL (Circle at safe standoff distance, accumulate mass)
            -- -------------------------------------------------------------
            elseif state == 'PROWL' then
                prowlTimer = prowlTimer + 3.0

                local targetDanger = CalculateTargetDangerousness(brain, targetPos, 50.0)
                local swarmPower = CalculateLocalSwarmPower(brain, targetPos, standoffDist + 20.0)

                -- Check if critical mass is reached or artillery has arrived
                if targetDanger <= 0 or swarmPower >= (targetDanger * 1.20) then
                    -- Critical mass reached! UNLEASH THE OVERWHELM CHARGE WITH SCATTER!
                    state = 'OVERWHELM'
                    overwhelmTimer = 0
                    IssueClearCommands(units)
                    for _, u in units do
                        if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
                            local jx = targetPos[1] + math.random(-12, 12)
                            local jz = targetPos[3] + math.random(-12, 12)
                            IssueAggressiveMove({u}, Vector(jx, GetSurfaceHeight(jx, jz), jz))
                        end
                    end
                elseif prowlTimer >= 22.0 then
                    -- Timeout: Target is too dangerous and reinforcements failed to arrive
                    -- Smart predator fallback: Don't suicide! Hunt an unfortified land target!
                    local currentPos = Vector(packX, GetSurfaceHeight(packX, packZ), packZ)
                    targetPos = Targeting.GetWeightedEnemyTarget(army, currentPos, false)
                    state = 'SPRINT'
                    initialSprintDone = false
                    prowlTimer = 0
                    overwhelmTimer = 0
                    justRetargeted = true
                else
                    -- Prowl & Orbit along the perimeter at safe standoff distance
                    orbitAngle = orbitAngle + 0.35 -- Rotate orbital positions
                    local activeUnits = {}
                    for _, u in units do
                        if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
                            if not u.IsFleeing and not u.IsKiting and not u.IsBerserk then
                                table.insert(activeUnits, u)
                            end
                        end
                    end

                    local nUnits = table.getn(activeUnits)
                    if nUnits > 0 then
                        for i, u in activeUnits do
                            local angle_i = orbitAngle + (i * (2 * math.pi / nUnits))
                            -- Add slight radial jitter (±3 units) for organic swarm movement
                            local rJitter = standoffDist + (math.sin(i * 1.7) * 3.0)
                            local wx = targetPos[1] + math.cos(angle_i) * rJitter
                            local wz = targetPos[3] + math.sin(angle_i) * rJitter
                            local wy = GetSurfaceHeight(wx, wz)
                            IssueClearCommands({u})
                            IssueAggressiveMove({u}, Vector(wx, wy, wz))
                        end
                    end
                end

            -- -------------------------------------------------------------
            -- STATE 3: OVERWHELM (Synchronized 360-degree all-out charge)
            -- -------------------------------------------------------------
            elseif state == 'OVERWHELM' then
                overwhelmTimer = overwhelmTimer + 3.0

                local allOrdersDone = true
                for _, u in units do
                    if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
                        if IsUnitIdle(u) then
                            IssueAggressiveMove({u}, targetPos)
                        else
                            allOrdersDone = false
                        end
                    end
                end

                if allOrdersDone or distToTarget > 60.0 then
                    IssueClearCommands(units)
                    IssueAggressiveMove(units, targetPos)
                end

                -- If target area is cleared (no enemies remaining), retarget
                -- Use 40-unit scan radius to account for ±15 target scatter and unit spread
                local remainingEnemies = brain:GetUnitsAroundPoint(categories.ALLUNITS - categories.WALL, targetPos, 40.0, 'Enemy')
                local areaCleared = (not remainingEnemies or table.empty(remainingEnemies))

                -- Staleness safety: if stuck in OVERWHELM for 25s+ and cannot finish target,
                -- break off and retarget to another enemy sector!
                if not areaCleared and overwhelmTimer >= 25.0 then
                    areaCleared = true
                end

                if areaCleared then
                    local currentPos = Vector(packX, GetSurfaceHeight(packX, packZ), packZ)
                    targetPos = Targeting.GetWeightedEnemyTarget(army, currentPos, false)
                    state = 'SPRINT'
                    initialSprintDone = false
                    prowlTimer = 0
                    overwhelmTimer = 0
                    justRetargeted = true
                end
            end
        end

        WaitSeconds(3.0 + math.random() * 0.8)
    end

    if platoon and ActiveWolfpacks then
        ActiveWolfpacks[platoon] = nil
    end
end

---Registers living raptors spawned dynamically in the field (from artillery shells,
---bomber eggs, dodo carriers, queen gestation, etc.), scales their stats to match current game anger,
---and merges them into a nearby active pack platoon or creates a new wolfpack.
---@param units table Array of Unit objects
---@param brain AIBrain
---@param spawnPos Vector3|table {x, y, z}
function RegisterFieldSpawnedUnits(units, brain, spawnPos)
    if not units or table.empty(units) or not brain then return end

    local army = brain:GetArmyIndex()
    local Spawner = import('/mods/RaptorFaction/lua/RaptorSpawner.lua')
    local Stats = import('/mods/RaptorFaction/lua/RaptorStats.lua')
    local techAnger = (Spawner and Spawner.GetTechAnger and Spawner.GetTechAnger()) or 0
    local queenAnger = (Spawner and Spawner.GetQueenAnger and Spawner.GetQueenAnger()) or 0
    local difficulty = (Spawner and Spawner.GetCurrentDifficulty and Spawner.GetCurrentDifficulty()) or 'normal'

    local validUnits = {}
    for _, u in units do
        if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
            u.RaptorSpawnTime = GetGameTimeSeconds()
            if Stats and Stats.RecomputeRaptorStats then
                Stats.RecomputeRaptorStats(u, techAnger, queenAnger, difficulty)
            end
            u:SetHealth(u, u:GetMaxHealth())
            table.insert(validUnits, u)
        end
    end

    if table.empty(validUnits) then return end

    -- Check if there is an active RaptorRaiderWolfpack nearby (within 60 units) to merge into
    local bestPlatoon = nil
    local bestDistSq = 60 * 60

    if ActiveWolfpacks then
        for plat, _ in ActiveWolfpacks do
            if plat and brain:PlatoonExists(plat) then
                local platUnits = plat:GetPlatoonUnits()
                if platUnits and table.getn(platUnits) > 0 then
                    local pPos = plat:GetPlatoonPosition()
                    if pPos and spawnPos then
                        local dx = pPos[1] - spawnPos[1]
                        local dz = pPos[3] - spawnPos[3]
                        local dSq = dx * dx + dz * dz
                        if dSq < bestDistSq then
                            bestDistSq = dSq
                            bestPlatoon = plat
                        end
                    end
                end
            else
                ActiveWolfpacks[plat] = nil
            end
        end
    end

    if bestPlatoon then
        brain:AssignUnitsToPlatoon(bestPlatoon, validUnits, 'Attack', 'NoFormation')
        local pPos = bestPlatoon:GetPlatoonPosition()
        if pPos then
            IssueClearCommands(validUnits)
            IssueAggressiveMove(validUnits, pPos)
        end
    else
        -- Create a dedicated Wolfpack platoon for these spawned raiders
        local targetPos = Targeting.GetWeightedEnemyTarget(army, spawnPos, false)
        local newPlatoon = brain:MakePlatoon('RaptorRaiderWolfpack', '')
        brain:AssignUnitsToPlatoon(newPlatoon, validUnits, 'Attack', 'NoFormation')
        ManageRaptorWolfpack(newPlatoon, targetPos, 'center')
    end
end

-- ---------------------------------------------------------------------------
-- 2. SIEGE & HEAVY SUPPORT SQUAD ENGINE (COORDINATED ADVANCE)
-- ---------------------------------------------------------------------------

---Evaluates squad cohesion and issues Pack Regroup or Assault commands
---@param platoon Platoon
---@param targetPos Vector3
---@param flankMode string|nil 'center' | 'left' | 'right'
function ManageRaptorSquad(platoon, targetPos, flankMode)
    if platoon and platoon.SetFormation then
        platoon:SetFormation('NoFormation')
    end
    platoon:ForkThread(PlatoonCohesionThread, targetPos, flankMode)
end

function PlatoonCohesionThread(platoon, targetPos, flankMode)
    local planArmy = nil
    if platoon and platoon.SetFormation then
        platoon:SetFormation('NoFormation')
    end

    while platoon do
        local units = platoon:GetPlatoonUnits()
        if not units or table.empty(units) then break end

        -- Identify army if not set
        if not planArmy then
            for _, u in units do
                if u and not u.Dead then
                    planArmy = u:GetArmy()
                    break
                end
            end
        end

        -- Ensure Mobile Shield Beetles (XRA0225) keep protective carapace active
        for _, u in units do
            if u and not u.Dead and not u:BeenDestroyed() then
                if EntityCategoryContains(categories.SHIELD * categories.MOBILE, u) then
                    if not u:ShieldIsOn() then
                        u:EnableShield()
                    end
                end
            end
        end

        -- Check for priority superweapon decapitation targets (land only)
        if PlatoonHuntPriorityThreat(platoon, false) then
            platoon.HasAssaultOrder = true
            platoon.IsRegrouping = false
        end

        -- Retarget if targetPos is nil
        if not targetPos and planArmy then
            targetPos = Targeting.GetWeightedEnemyTarget(planArmy, nil, false)
            platoon.HasAssaultOrder = false
        end

        if targetPos then
            platoon.CurrentAssaultPos = targetPos

            local xmin, xmax = 999999, -999999
            local zmin, zmax = 999999, -999999
            local xsum, zsum = 0, 0
            local count = 0

            for _, u in units do
                if u and not u.Dead and not u:BeenDestroyed() then
                    -- Cohesion Exemption: Exclude units currently executing individual tactical micro
                    if not u.IsFleeing and not u.IsKiting and not u.IsBerserk then
                        local p = u:GetPosition()
                        if p[1] < xmin then xmin = p[1] end
                        if p[1] > xmax then xmax = p[1] end
                        if p[3] < zmin then zmin = p[3] end
                        if p[3] > zmax then zmax = p[3] end
                        xsum = xsum + p[1]
                        zsum = zsum + p[3]
                        count = count + 1
                    end
                end
            end

            if count == 0 then
                -- If all active units are currently performing micro, calculate across all active units
                for _, u in units do
                    if u and not u.Dead and not u:BeenDestroyed() then
                        local p = u:GetPosition()
                        xsum = xsum + p[1]
                        zsum = zsum + p[3]
                        count = count + 1
                    end
                end
            end

            if count == 0 then break end

            local xavg = xsum / count
            local zavg = zsum / count
            local distToTargetSq = (xavg - targetPos[1]) * (xavg - targetPos[1]) + (zavg - targetPos[3]) * (zavg - targetPos[3])

            -- Centroid Stuck Detection: If siege platoon moved < 4.0 in 12s while far from target,
            -- it is blocked by cliff edge or impassable terrain! Force retarget to reachable land base!
            if not platoon.LastCentroidPos then
                platoon.LastCentroidPos = { xavg, zavg }
                platoon.StuckTime = 0
            else
                local cdx = xavg - platoon.LastCentroidPos[1]
                local cdz = zavg - platoon.LastCentroidPos[2]
                local movedDist = math.sqrt(cdx * cdx + cdz * cdz)
                if movedDist < 4.0 and distToTargetSq > (25 * 25) then
                    platoon.StuckTime = (platoon.StuckTime or 0) + 4.0
                    if platoon.StuckTime >= 12.0 then
                        local currentPos = Vector(xavg, GetSurfaceHeight(xavg, zavg), zavg)
                        targetPos = Targeting.GetWeightedEnemyTarget(planArmy, currentPos, false)
                        platoon.HasAssaultOrder = false
                        platoon.CurrentAssaultPos = targetPos
                        platoon.AssaultDuration = 0
                        platoon.StuckTime = 0
                        platoon.LastCentroidPos = { xavg, zavg }
                        IssueClearCommands(units)
                    end
                else
                    platoon.LastCentroidPos = { xavg, zavg }
                    platoon.StuckTime = 0
                end
            end

            -- Check if platoon reached target area or exceeded maximum assault duration (35s)
            platoon.AssaultDuration = (platoon.AssaultDuration or 0) + 4.0
            if (distToTargetSq < 25 * 25 or platoon.AssaultDuration >= 35.0) and planArmy then
                local currentPos = Vector(xavg, GetSurfaceHeight(xavg, zavg), zavg)
                targetPos = Targeting.GetWeightedEnemyTarget(planArmy, currentPos, false)
                platoon.HasAssaultOrder = false
                platoon.CurrentAssaultPos = targetPos
                platoon.AssaultDuration = 0
                flankMode = 'center'
            else
                -- Check if any units lost their orders or detached en route
                local cPos = Vector(xavg, GetSurfaceHeight(xavg, zavg), zavg)
                local curTime = GetGameTimeSeconds()
                for _, u in units do
                    if u and not u.Dead and not u:BeenDestroyed() then
                        local busy = u.IsFleeing or u.IsKiting or u.IsBerserk
                            or (u.GetTargetEntity and u:GetTargetEntity())
                            or (u.LastDamagedTime and (curTime - u.LastDamagedTime) < 5.0)
                        if not busy then
                            local q = u.GetCommandQueue and u:GetCommandQueue()
                            if not q or table.empty(q) then
                                IssueAggressiveMove({u}, cPos)
                            end
                        end
                    end
                end
            end

            -- Combat Safety Lock:
            -- If any unit is fighting or recently damaged, skip cohesion regrouping entirely.
            if IsPlatoonInCombat(platoon, false) then
                platoon.IsRegrouping = false
            else

                -- Max spread threshold: 75 units allows natural combat movement without false-positive regrouping
                local maxSpread = 75.0
                local isDispersed = (xmin < xavg - maxSpread) or (xmax > xavg + maxSpread)
                                 or (zmin < zavg - maxSpread) or (zmax > zavg + maxSpread)

                if isDispersed then
                    -- Eliminate platoon-wide Stop() on vanguard!
                    -- Only identify trailing 20% stragglers and issue aggressive catch-up move toward lead unit.
                    local leadUnit = nil
                    local minTargetDistSq = 999999999
                    local unitDistList = {}

                    for _, u in units do
                        if u and not u.Dead and not u:BeenDestroyed() then
                            -- Only consider units not currently dodging/kiting/berserking
                            if not u.IsFleeing and not u.IsKiting and not u.IsBerserk then
                                local p = u:GetPosition()
                                local dX = p[1] - targetPos[1]
                                local dZ = p[3] - targetPos[3]
                                local dSq = dX * dX + dZ * dZ
                                if dSq < minTargetDistSq then
                                    minTargetDistSq = dSq
                                    leadUnit = u
                                end
                                table.insert(unitDistList, {unit = u, distSq = dSq, pos = p})
                            end
                        end
                    end

                    local totalUnits = table.getn(unitDistList)
                    if leadUnit and totalUnits > 1 then
                        local leadPos = leadUnit:GetPosition()
                        -- Sort trailing units furthest from targetPos first
                        table.sort(unitDistList, function(a, b) return a.distSq > b.distSq end)

                        local stragglerCount = math.max(1, math.floor(totalUnits * 0.20))
                        if stragglerCount >= totalUnits then
                            stragglerCount = totalUnits - 1
                        end

                        local trailingUnits = {}
                        local curTime = GetGameTimeSeconds()
                        for i = 1, stragglerCount do
                            local entry = unitDistList[i]
                            if entry and entry.unit and not entry.unit.Dead and not entry.unit:BeenDestroyed() then
                                local u = entry.unit
                                local stragglerBusy = u.IsFleeing or u.IsKiting or u.IsBerserk
                                    or (u.GetTargetEntity and u:GetTargetEntity())
                                    or (u.LastDamagedTime and (curTime - u.LastDamagedTime) < 6.0)
                                if not stragglerBusy then
                                    table.insert(trailingUnits, u)
                                end
                            end
                        end

                        if table.getn(trailingUnits) > 0 then
                            IssueClearCommands(trailingUnits)
                            IssueAggressiveMove(trailingUnits, leadPos)
                        end
                    end
                end

                -- Issue multi-pronged approach corridor attack orders using NavMesh corridor
                if not platoon.HasAssaultOrder then
                    local startPos = Vector(xavg, GetSurfaceHeight(xavg, zavg), zavg)
                    local route = GetNavCorridor(startPos, targetPos, 'Land', flankMode)
                    local routeLen = table.getn(route)
                    if routeLen > 0 then
                        platoon:Stop()
                        for i, wp in route do
                            local wx = wp[1]
                            local wz = wp[3]
                            if i == routeLen then
                                wx = wx + math.random(-15, 15)
                                wz = wz + math.random(-15, 15)
                            end
                            local wy = GetSurfaceHeight(wx, wz)
                            platoon:AggressiveMoveToLocation(Vector(wx, wy, wz))
                        end
                        platoon.HasAssaultOrder = true
                        platoon.IsRegrouping = false
                    end
                end
            end
        end

        -- Jittered sleep (3.5 - 5.0 seconds) to prevent synchronized CPU spikes
        WaitSeconds(3.5 + math.random() * 1.5)
    end
end

-- ---------------------------------------------------------------------------
-- 2. AERIAL SWARM AI ENGINE
-- ---------------------------------------------------------------------------

---Evaluates air squad maneuvers and issues continuous aerial patrol diamonds
---@param platoon Platoon
---@param targetPos Vector3
function ManageRaptorAirSquad(platoon, targetPos)
    if platoon and platoon.SetFormation then
        platoon:SetFormation('NoFormation')
    end
    platoon:ForkThread(AirAssaultThread, targetPos)
end

function AirAssaultThread(platoon, targetPos)
    local planArmy = nil
    if platoon and platoon.SetFormation then
        platoon:SetFormation('NoFormation')
    end

    local currentAssignedPos = nil

    while platoon do
        local units = platoon:GetPlatoonUnits()
        if not units or table.empty(units) then break end

        -- Identify army if not set
        if not planArmy then
            for _, u in units do
                if u and not u.Dead then
                    planArmy = u:GetArmy()
                    break
                end
            end
        end

        -- Verify targetPos is not underwater or on seabed
        if targetPos then
            local surfY = GetSurfaceHeight(targetPos[1], targetPos[3])
            local terrY = GetTerrainHeight(targetPos[1], targetPos[3])
            if (surfY > terrY + 1.2) and (targetPos[2] < surfY - 0.5) then
                targetPos = nil
                currentAssignedPos = nil
            end
        end

        -- Check if squad has bombers/gunships or is pure anti-air fighter wing
        local hasGroundAttack = false
        for _, u in units do
            if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
                if EntityCategoryContains((categories.BOMBER + categories.GROUNDATTACK) - categories.ANTIAIR, u) then
                    hasGroundAttack = true
                    break
                end
            end
        end

        if not hasGroundAttack then
            -- Pure fighter wing: hunt enemy air units across the map!
            local enemyAir = platoon:FindClosestUnit('Attack', 'Enemy', true, categories.AIR * categories.MOBILE)
            if enemyAir and not enemyAir.Dead and (not enemyAir.BeenDestroyed or not enemyAir:BeenDestroyed()) then
                targetPos = enemyAir:GetPosition()
            else
                -- If no enemy air active, patrol friendly base/hives instead of diving on ground targets!
                targetPos = nil
                local brain = platoon:GetBrain()
                if brain then
                    local pPos = platoon:GetPlatoonPosition() or Vector(512, 50, 512)
                    local hives = brain:GetUnitsAroundPoint(categories.RAPTOR * categories.STRUCTURE, pPos, 350.0, 'Ally')
                    if hives and not table.empty(hives) then
                        local h = hives[math.random(1, table.getn(hives))]
                        if h and not h.Dead then
                            targetPos = h:GetPosition()
                        end
                    end
                end
            end
        end

        if not targetPos and planArmy then
            targetPos = Targeting.GetWeightedEnemyTarget(planArmy, nil, true)
        end

        local allIdle = true
        for _, u in units do
            if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
                if not IsUnitIdle(u) then
                    allIdle = false
                    break
                end
            end
        end

        if targetPos and (allIdle or not currentAssignedPos or currentAssignedPos[1] ~= targetPos[1] or currentAssignedPos[3] ~= targetPos[3]) then
            currentAssignedPos = targetPos
            platoon.AirTargetTimer = 0

            -- Generate a wide aerial attack/patrol diamond around targetPos
            local offset = 40.0
            local y1 = GetSurfaceHeight(targetPos[1] + offset, targetPos[3])
            local y2 = GetSurfaceHeight(targetPos[1], targetPos[3] + offset)
            local y3 = GetSurfaceHeight(targetPos[1] - offset, targetPos[3])
            local y4 = GetSurfaceHeight(targetPos[1], targetPos[3] - offset)

            local p1 = Vector(targetPos[1] + offset, y1, targetPos[3])
            local p2 = Vector(targetPos[1], y2, targetPos[3] + offset)
            local p3 = Vector(targetPos[1] - offset, y3, targetPos[3])
            local p4 = Vector(targetPos[1], y4, targetPos[3] - offset)

            IssueClearCommands(units)
            IssueAggressiveMove(units, targetPos)
            IssuePatrol(units, p1)
            IssuePatrol(units, p2)
            IssuePatrol(units, p3)
            IssuePatrol(units, p4)
        end

        -- Re-evaluate target every 15-25 seconds with jitter
        WaitSeconds(15.0 + math.random() * 10.0)
        platoon.AirTargetTimer = (platoon.AirTargetTimer or 0) + 20.0
        if planArmy then
            local brain = platoon:GetBrain()
            if brain and targetPos then
                -- Exclude underwater/seabed units (which air units cannot damage) from clearance check
                local enemies = brain:GetUnitsAroundPoint(categories.ALLUNITS - categories.WALL, targetPos, 35.0, 'Enemy')
                local validEnemies = {}
                if enemies then
                    for _, e in enemies do
                        if e and not e.Dead and (not e.BeenDestroyed or not e:BeenDestroyed()) then
                            if not Targeting.IsTargetUnderwater(e) then
                                table.insert(validEnemies, e)
                            end
                        end
                    end
                end
                local areaCleared = table.empty(validEnemies)

                -- Force retarget if area cleared or if air squad has lingered over target for 35s+
                if areaCleared or platoon.AirTargetTimer >= 35.0 then
                    local airPos = platoon:GetPlatoonPosition()
                    targetPos = Targeting.GetWeightedEnemyTarget(planArmy, airPos, true)
                    platoon.AirTargetTimer = 0
                    currentAssignedPos = nil
                end
            end
        end
    end
end

---Dedicated Air Superiority AI for Raptor Fighter Wings (XRA0115, XRA0314, XRA0219):
---Aggressively hunts enemy aircraft across the map.
---If no enemy aircraft are detected, sweeps friendly airspace / hive perimeters at high altitude.
---NEVER patrols or hovers around seabed or ground structures!
---@param platoon Platoon
function ManageRaptorFighterWing(platoon)
    if platoon and platoon.SetFormation then
        platoon:SetFormation('NoFormation')
    end
    platoon:ForkThread(FighterWingThread)
end

function FighterWingThread(platoon)
    local brain = platoon:GetBrain()
    local army = brain:GetArmyIndex()
    if platoon and platoon.SetFormation then
        platoon:SetFormation('NoFormation')
    end

    while platoon and brain:PlatoonExists(platoon) do
        local units = platoon:GetPlatoonUnits()
        if not units or table.empty(units) then break end

        -- 1. Scan for closest enemy aircraft across the map
        local enemyAir = platoon:FindClosestUnit('Attack', 'Enemy', true, categories.AIR * categories.MOBILE)
        if enemyAir and not enemyAir.Dead and (not enemyAir.BeenDestroyed or not enemyAir:BeenDestroyed()) then
            IssueClearCommands(units)
            IssueAttack(units, enemyAir)
        else
            -- 2. No enemy aircraft active/visible: patrol high-altitude airspace around allied hives
            local myPos = platoon:GetPlatoonPosition() or Vector(512, 50, 512)
            local hives = brain:GetUnitsAroundPoint(categories.RAPTOR * categories.STRUCTURE, myPos, 350.0, 'Ally')
            local patrolCenter = myPos

            if hives and not table.empty(hives) then
                local chosenHive = hives[math.random(1, table.getn(hives))]
                if chosenHive and not chosenHive.Dead then
                    patrolCenter = chosenHive:GetPosition()
                end
            end

            local offset = 65.0
            local y1 = GetSurfaceHeight(patrolCenter[1] + offset, patrolCenter[3]) + 25
            local y2 = GetSurfaceHeight(patrolCenter[1], patrolCenter[3] + offset) + 25
            local y3 = GetSurfaceHeight(patrolCenter[1] - offset, patrolCenter[3]) + 25
            local y4 = GetSurfaceHeight(patrolCenter[1], patrolCenter[3] - offset) + 25

            local p1 = Vector(patrolCenter[1] + offset, y1, patrolCenter[3])
            local p2 = Vector(patrolCenter[1], y2, patrolCenter[3] + offset)
            local p3 = Vector(patrolCenter[1] - offset, y3, patrolCenter[3])
            local p4 = Vector(patrolCenter[1], y4, patrolCenter[3] - offset)

            IssueClearCommands(units)
            IssuePatrol(units, p1)
            IssuePatrol(units, p2)
            IssuePatrol(units, p3)
            IssuePatrol(units, p4)
        end

        WaitSeconds(10.0 + math.random() * 5.0)
    end
end

---Evaluates air scout recon runs, flying ahead of bombers and strike waves
---with high-speed evasion patrol diamonds over enemy sectors
---@param platoon Platoon
---@param targetPos Vector3
function ManageRaptorScoutSquad(platoon, targetPos)
    if platoon and platoon.SetFormation then
        platoon:SetFormation('NoFormation')
    end
    platoon:ForkThread(AirScoutThread, targetPos)
end

function AirScoutThread(platoon, targetPos)
    local planArmy = nil
    if platoon and platoon.SetFormation then
        platoon:SetFormation('NoFormation')
    end

    local currentAssignedPos = nil

    while platoon do
        local units = platoon:GetPlatoonUnits()
        if not units or table.empty(units) then break end

        -- Identify army if not set
        if not planArmy then
            for _, u in units do
                if u and not u.Dead then
                    planArmy = u:GetArmy()
                    break
                end
            end
        end

        if not targetPos and planArmy then
            targetPos = Targeting.GetWeightedEnemyTarget(planArmy, nil, true)
        end

        local allIdle = true
        for _, u in units do
            if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
                if not IsUnitIdle(u) then
                    allIdle = false
                    break
                end
            end
        end

        if targetPos and (allIdle or not currentAssignedPos or currentAssignedPos[1] ~= targetPos[1] or currentAssignedPos[3] ~= targetPos[3]) then
            currentAssignedPos = targetPos

            -- High-speed recon flight: sprint directly to the target location first to scout ahead immediately!
            IssueClearCommands(units)
            IssueMove(units, targetPos)

            -- Wide reconnaissance diamond patrol (radius 55) at high elevation to unveil fog of war
            local offset = 55.0
            local y1 = GetSurfaceHeight(targetPos[1] + offset, targetPos[3])
            local y2 = GetSurfaceHeight(targetPos[1], targetPos[3] + offset)
            local y3 = GetSurfaceHeight(targetPos[1] - offset, targetPos[3])
            local y4 = GetSurfaceHeight(targetPos[1], targetPos[3] - offset)

            local p1 = Vector(targetPos[1] + offset, y1, targetPos[3])
            local p2 = Vector(targetPos[1], y2, targetPos[3] + offset)
            local p3 = Vector(targetPos[1] - offset, y3, targetPos[3])
            local p4 = Vector(targetPos[1], y4, targetPos[3] - offset)

            IssuePatrol(units, p1)
            IssuePatrol(units, p2)
            IssuePatrol(units, p3)
            IssuePatrol(units, p4)
        end

        -- Re-evaluate and scout fresh targets every 20-30 seconds
        WaitSeconds(20.0 + math.random() * 10.0)
        if planArmy then
            local scoutPos = platoon:GetPlatoonPosition()
            targetPos = Targeting.GetWeightedEnemyTarget(planArmy, scoutPos, true)
        end
    end
end


-- ---------------------------------------------------------------------------
-- 3. BEHAVIORAL TRAIT ACTIONS
-- ---------------------------------------------------------------------------

---SKIRMISH: Ranged spikers and bio-artillery backpedal to keep distance
---@param unit Unit
---@param targetPos Vector3
function TriggerSkirmishKite(unit, targetPos)
    if not unit or unit.Dead or not targetPos or unit.IsKiting then return end
    if unit.KiteCooldown and unit.KiteCooldown > GetGameTimeSeconds() then return end

    unit.IsKiting = true
    unit.KiteCooldown = GetGameTimeSeconds() + 4.0

    local curPos = unit:GetPosition()
    local angle = math.atan2(targetPos[1] - curPos[1], targetPos[3] - curPos[3])

    -- Move backward along the vector away from target (15 - 20 units)
    local kiteDist = 18.0
    local kx = curPos[1] - math.sin(angle) * kiteDist
    local kz = curPos[3] - math.cos(angle) * kiteDist
    local ky = GetSurfaceHeight(kx, kz)

    IssueClearCommands({unit})
    IssueMove({unit}, Vector(kx, ky, kz))

    -- Rejoin platoon assault order after short kite maneuver
    unit:ForkThread(function()
        WaitSeconds(3.0)
        if unit and not unit.Dead then
            unit.IsKiting = false
            local plat = unit:GetPlatoon()
            if plat and plat.CurrentAssaultPos then
                IssueAggressiveMove({unit}, plat.CurrentAssaultPos)
            end
        end
    end)
end

---COWARD / DODGE: Damaged units flee from damage source when HP < 80%
---@param unit Unit
---@param instigator Unit
function TriggerCowardFlee(unit, instigator)
    if not unit or unit.Dead or unit.IsFleeing or not instigator or instigator.Dead then return end
    if unit.FleeCooldown and unit.FleeCooldown > GetGameTimeSeconds() then return end

    unit.IsFleeing = true
    unit.FleeCooldown = GetGameTimeSeconds() + 5.0

    local curPos = unit:GetPosition()
    local instPos = instigator:GetPosition()
    local angle = math.atan2(instPos[1] - curPos[1], instPos[3] - curPos[3])

    local fleeDist = 20.0
    local fx = curPos[1] - math.sin(angle) * fleeDist
    local fz = curPos[3] - math.cos(angle) * fleeDist
    local fy = GetSurfaceHeight(fx, fz)

    IssueClearCommands({unit})
    IssueMove({unit}, Vector(fx, fy, fz))

    -- Rejoin Platoon after 3.5 seconds
    unit:ForkThread(function()
        WaitSeconds(3.5)
        if unit and not unit.Dead then
            unit.IsFleeing = false
            local plat = unit:GetPlatoon()
            if plat and plat.CurrentAssaultPos then
                IssueAggressiveMove({unit}, plat.CurrentAssaultPos)
                if not Targeting.IsTargetUnderwater(instigator) then
                    local bp = unit:GetBlueprint()
                    local isAir = bp and bp.Physics and bp.Physics.MotionType == 'RULEUMT_Air'
                    if isAir or not Targeting.IsTargetAirOnly(instigator) then
                        IssueAggressiveMove({unit}, instigator:GetPosition())
                    end
                end
            end
        end
    end)
end

---BERSERK: Assault behemoths enrage upon taking fire, gaining speed and charging
---@param unit Unit
---@param instigator Unit
function TriggerBerserkCharge(unit, instigator)
    if not unit or unit.Dead or not instigator or instigator.Dead then return end
    if unit.IsBerserk then return end

    -- Check if instigator is unreachable (e.g. underwater or deep water)
    if Targeting.IsTargetUnderwater(instigator) then
        return
    end

    local bp = unit:GetBlueprint()
    local isAir = bp and bp.Physics and bp.Physics.MotionType == 'RULEUMT_Air'
    if not isAir and Targeting.IsTargetAirOnly(instigator) then
        return -- Do not pursue unreachable water targets into cliffs or rivers
    end

    unit.IsBerserk = true
    -- Boost speed by +35% for 4.5 seconds
    if unit.SetSpeedMult then unit:SetSpeedMult(1.35) end

    IssueClearCommands({unit})
    IssueAttack({unit}, instigator)

    unit:ForkThread(function()
        WaitSeconds(4.5)
        if unit and not unit.Dead then
            if unit.SetSpeedMult then unit:SetSpeedMult(1.0) end
            unit.IsBerserk = false
            local plat = unit:GetPlatoon()
            if plat and plat.CurrentAssaultPos then
                IssueAggressiveMove({unit}, plat.CurrentAssaultPos)
            end
        end
    end)
end

---SPECTRE BLINK: Short-range teleportation burst on a 2.5-second cooldown
---@param unit Unit
---@param targetPos Vector3
function TriggerSpectreBlink(unit, targetPos)
    if not unit or unit.Dead or not targetPos then return end
    if unit.BlinkCooldown and unit.BlinkCooldown > GetGameTimeSeconds() then return end

    unit.BlinkCooldown = GetGameTimeSeconds() + 2.5
    local curPos = unit:GetPosition()
    local angle = math.atan2(targetPos[1] - curPos[1], targetPos[3] - curPos[3])

    -- Lateral offset perpendicular to line of fire
    local side = (math.random() > 0.5) and 1 or -1
    local blinkDist = 16.0
    local bx = curPos[1] + (math.cos(angle) * blinkDist * side)
    local bz = curPos[3] - (math.sin(angle) * blinkDist * side)
    local by = GetSurfaceHeight(bx, bz)

    -- Teleport particles & warp
    local army = unit:GetArmy()
    CreateEmitterAtEntity(unit, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp')
    Warp(unit, Vector(bx, by, bz))
    CreateEmitterAtEntity(unit, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp')

    -- Resume platoon assault order
    local plat = unit:GetPlatoon()
    if plat and plat.CurrentAssaultPos then
        IssueAggressiveMove({unit}, plat.CurrentAssaultPos)
    end
end

---WEAVER HEAL AURA: Continuous biological regeneration targeting injured allies
---@param unit Unit
function StartWeaverHealThread(unit)
    unit:ForkThread(function()
        local brain = unit:GetAIBrain()
        local army = unit:GetArmy()
        while unit and not unit.Dead and not unit:BeenDestroyed() do
            WaitSeconds(1.5)
            local pos = unit:GetPosition()
            -- Scan 22-unit radius for damaged raptors
            local allies = brain:GetUnitsAroundPoint(categories.RAPTOR, pos, 22.0, 'Ally')
            for _, ally in allies do
                -- Exclude self and other healers (prevents infinite mutual healing)
                if ally and not ally.Dead and ally:GetEntityId() ~= unit:GetEntityId() then
                    local bp = ally:GetBlueprint()
                    if not (bp and bp.CategoriesHash and bp.CategoriesHash['HEALER']) then
                        local curHp = ally:GetHealth()
                        local maxHp = ally:GetMaxHealth()
                        if curHp < maxHp then
                            local healAmt = math.min(60, maxHp - curHp)
                            ally:SetHealth(ally, curHp + healAmt)
                            CreateEmitterAtEntity(ally, army, '/mods/RaptorFaction/effects/emitters/raptor_bio_heal_burst_01_emit.bp'):ScaleEmitter(0.5)
                        end
                    end
                end
            end
        end
    end)
end

-- ---------------------------------------------------------------------------
-- 5. SUBTERRANEAN DIGGER AMBUSH AI ENGINE
-- ---------------------------------------------------------------------------

---Dedicated AI for Subterranean Digger infiltration platoons
---Moves cloaked, bypasses frontline chokepoints, and strikes rear infrastructure
---@param platoon Platoon
---@param targetPos Vector3
function ManageDiggerAmbushSquad(platoon, targetPos)
    platoon:ForkThread(function()
        local brain = platoon:GetBrain()
        local army = brain:GetArmyIndex()
        local currentAssignedPos = nil

        while platoon and brain:PlatoonExists(platoon) do
            local units = platoon:GetPlatoonUnits()
            if not units or table.empty(units) then break end

            -- Maintain subterranean cloaking on all diggers when out of combat
            for _, u in units do
                if u and not u.Dead and not u:BeenDestroyed() then
                    if not u:IsIntelEnabled('Cloak') then
                        u:EnableUnitIntel('Cloak')
                        u:EnableUnitIntel('RadarStealth')
                    end
                end
            end

            local allIdle = true
            for _, u in units do
                if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
                    if not IsUnitIdle(u) then
                        allIdle = false
                        break
                    end
                end
            end

            -- If target is missing, destroyed, or squad is idle, locate next rear eco/radar/artillery target
            if not targetPos or allIdle then
                local bestTarget = platoon:FindClosestUnit('Attack', 'Enemy', true,
                    (categories.STRUCTURE * (categories.MASSEXTRACTION + categories.ENERGYPRODUCTION + categories.RADAR + categories.INDIRECTFIRE)) - categories.NAVAL - categories.SUBMERSIBLE
                )
                if bestTarget and not bestTarget.Dead and not Targeting.IsTargetAirOnly(bestTarget) then
                    targetPos = bestTarget:GetPosition()
                else
                    targetPos = Targeting.GetWeightedEnemyTarget(army, nil, false)
                end
            end

            if targetPos then
                local tPos = targetPos
                if tPos and not tPos[1] and tPos.GetPosition then
                    tPos = tPos:GetPosition()
                end

                if allIdle or not currentAssignedPos or currentAssignedPos[1] ~= tPos[1] or currentAssignedPos[3] ~= tPos[3] then
                    currentAssignedPos = tPos
                    local pPos = platoon:GetPlatoonPosition() or tPos
                    local route = GetNavCorridor(pPos, tPos, 'Land', 'center')
                    platoon:Stop()
                    for _, wp in route do
                        platoon:AggressiveMoveToLocation(wp)
                    end
                end
            end

            WaitSeconds(6.0 + math.random() * 2.0)
        end
    end)
end

