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

-- ---------------------------------------------------------------------------
-- 1. PLATOON SQUAD CENTROID & REGROUPING ENGINE
-- ---------------------------------------------------------------------------

---Checks if any unit in the platoon is actively firing, targeting an enemy, or recently took damage
---@param platoon Platoon
---@return boolean
function IsPlatoonInCombat(platoon)
    local units = platoon:GetPlatoonUnits()
    if not units or table.empty(units) then return false end
    local currentTime = GetGameTimeSeconds()
    for _, u in units do
        if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
            -- Check if unit has active target or recent damage timestamp (< 6s)
            local hasTarget = false
            if u.GetTargetEntity and u:GetTargetEntity() then
                hasTarget = true
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

---Priority Decapitation Sniping: Hunts down game-ending Experimentals, Strategic Artillery, and Paragons
---@param platoon Platoon
---@return boolean wasPriorityFound
function PlatoonHuntPriorityThreat(platoon)
    if not platoon or not platoon.FindClosestUnit then return false end
    local targetCategory = categories.EXPERIMENTAL + (categories.STRATEGIC * categories.ARTILLERY)
    local ok, target = pcall(function()
        return platoon:FindClosestUnit('Attack', 'Enemy', true, targetCategory)
    end)
    if ok and target and not target.Dead and (not target.BeenDestroyed or not target:BeenDestroyed()) then
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
    platoon:ForkThread(WolfpackProwlThread, targetPos, flankMode)
end

function WolfpackProwlThread(platoon, targetPos, flankMode)
    local brain = platoon:GetBrain()
    local army = brain:GetArmyIndex()
    if platoon and platoon.SetFormation then
        platoon:SetFormation('NoFormation')
    end

    local prowlTimer = 0
    local orbitAngle = math.random() * 2 * math.pi
    local state = 'SPRINT' -- 'SPRINT' | 'PROWL' | 'OVERWHELM'
    local initialSprintDone = false

    while platoon and brain:PlatoonExists(platoon) do
        local units = platoon:GetPlatoonUnits()
        if not units or table.empty(units) then break end

        -- Retarget if targetPos is nil or destroyed
        if not targetPos then
            targetPos = Targeting.GetWeightedEnemyTarget(army)
            state = 'SPRINT'
            initialSprintDone = false
            prowlTimer = 0
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

            -- If in active combat (taking damage or shooting), fight to the death!
            if IsPlatoonInCombat(platoon) then
                state = 'OVERWHELM'
            end

            -- -------------------------------------------------------------
            -- STATE 1: SPRINT (Fast approach along flanking corridor)
            -- -------------------------------------------------------------
            if state == 'SPRINT' then
                if not initialSprintDone then
                    local startPos = Vector(packX, GetSurfaceHeight(packX, packZ), packZ)
                    local route = GenerateFlankingRoute(startPos, targetPos, flankMode)
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
                        IssueClearCommands(units)
                        IssueAggressiveMove(units, targetPos)
                    else
                        -- Fortified target -> Transition to Prowl & Stalk!
                        state = 'PROWL'
                        prowlTimer = 0
                        IssueClearCommands(units)
                    end
                else
                    -- If units stalled or became idle en route, re-issue sprint orders
                    local allIdle = true
                    for _, u in units do
                        if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
                            if not u:IsIdle() then
                                allIdle = false
                                break
                            end
                        end
                    end
                    if allIdle then
                        initialSprintDone = false
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
                    -- Critical mass reached! UNLEASH THE OVERWHELM CHARGE!
                    state = 'OVERWHELM'
                    IssueClearCommands(units)
                    IssueAggressiveMove(units, targetPos)
                elseif prowlTimer >= 22.0 then
                    -- Timeout: Target is too dangerous and reinforcements failed to arrive
                    -- Smart predator fallback: Don't suicide! Hunt an unfortified target!
                    local currentPos = Vector(packX, GetSurfaceHeight(packX, packZ), packZ)
                    targetPos = Targeting.GetWeightedEnemyTarget(army, currentPos)
                    state = 'SPRINT'
                    initialSprintDone = false
                    prowlTimer = 0
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
                local allOrdersDone = true
                for _, u in units do
                    if u and not u.Dead and (not u.BeenDestroyed or not u:BeenDestroyed()) then
                        if not u:IsIdle() then
                            allOrdersDone = false
                        end
                    end
                end

                if allOrdersDone or distToTarget > 60.0 then
                    IssueClearCommands(units)
                    IssueAggressiveMove(units, targetPos)
                end

                -- If target area is cleared (no enemies remaining), retarget
                local remainingEnemies = brain:GetUnitsAroundPoint(categories.ALLUNITS - categories.WALL, targetPos, 22.0, 'Enemy')
                if not remainingEnemies or table.empty(remainingEnemies) then
                    local currentPos = Vector(packX, GetSurfaceHeight(packX, packZ), packZ)
                    targetPos = Targeting.GetWeightedEnemyTarget(army, currentPos)
                    state = 'SPRINT'
                    initialSprintDone = false
                    prowlTimer = 0
                end
            end
        end

        WaitSeconds(3.0 + math.random() * 0.8)
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
        platoon:SetFormation('AttackFormation')
    end
    platoon:ForkThread(PlatoonCohesionThread, targetPos, flankMode)
end

function PlatoonCohesionThread(platoon, targetPos, flankMode)
    local planArmy = nil
    if platoon and platoon.SetFormation then
        platoon:SetFormation('AttackFormation')
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

        -- Check for priority superweapon decapitation targets
        if PlatoonHuntPriorityThreat(platoon) then
            platoon.HasAssaultOrder = true
            platoon.IsRegrouping = false
        end

        -- Retarget if targetPos is nil
        if not targetPos and planArmy then
            targetPos = Targeting.GetWeightedEnemyTarget(planArmy)
            platoon.HasAssaultOrder = false
        end

        if targetPos then
            platoon.CurrentAssaultPos = targetPos

            -- Combat Safety Lock:
            -- If any unit is fighting or recently damaged, skip cohesion regrouping entirely.
            if IsPlatoonInCombat(platoon) then
                platoon.IsRegrouping = false
            else
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

                -- Check if platoon reached target area, retarget to nearest high-value vulnerable eco
                local distToTargetSq = (xavg - targetPos[1]) * (xavg - targetPos[1]) + (zavg - targetPos[3]) * (zavg - targetPos[3])
                if distToTargetSq < 25 * 25 and planArmy then
                    local currentPos = Vector(xavg, GetSurfaceHeight(xavg, zavg), zavg)
                    targetPos = Targeting.GetWeightedEnemyTarget(planArmy, currentPos)
                    platoon.HasAssaultOrder = false
                    platoon.CurrentAssaultPos = targetPos
                    flankMode = 'center'
                else
                    -- Check if units completed orders or became idle en route
                    local allIdle = true
                    for _, u in units do
                        if u and not u.Dead and not u:BeenDestroyed() then
                            if not u:IsIdle() then
                                allIdle = false
                                break
                            end
                        end
                    end
                    if allIdle then
                        platoon.HasAssaultOrder = false
                    end
                end

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

                -- Issue multi-pronged approach corridor attack orders
                if not platoon.HasAssaultOrder then
                    local startPos = Vector(xavg, GetSurfaceHeight(xavg, zavg), zavg)
                    local route = GenerateFlankingRoute(startPos, targetPos, flankMode)
                    platoon:Stop()
                    local routeLen = table.getn(route)
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
        platoon:SetFormation('GrowthFormation')
    end
    platoon:ForkThread(AirAssaultThread, targetPos)
end

function AirAssaultThread(platoon, targetPos)
    local planArmy = nil
    if platoon and platoon.SetFormation then
        platoon:SetFormation('GrowthFormation')
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
            targetPos = Targeting.GetWeightedRandomEnemyTarget(planArmy)
        end

        local allIdle = true
        for _, u in units do
            if u and not u.Dead and not u:BeenDestroyed() then
                if not u:IsIdle() then
                    allIdle = false
                    break
                end
            end
        end

        if targetPos and (allIdle or not currentAssignedPos or currentAssignedPos[1] ~= targetPos[1] or currentAssignedPos[3] ~= targetPos[3]) then
            currentAssignedPos = targetPos

            -- Generate a wide aerial attack/patrol diamond around targetPos
            local offset = 35.0
            local y1 = GetSurfaceHeight(targetPos[1] + offset, targetPos[3])
            local y2 = GetSurfaceHeight(targetPos[1], targetPos[3] + offset)
            local y3 = GetSurfaceHeight(targetPos[1] - offset, targetPos[3])
            local y4 = GetSurfaceHeight(targetPos[1], targetPos[3] - offset)

            local p1 = Vector(targetPos[1] + offset, y1, targetPos[3])
            local p2 = Vector(targetPos[1], y2, targetPos[3] + offset)
            local p3 = Vector(targetPos[1] - offset, y3, targetPos[3])
            local p4 = Vector(targetPos[1], y4, targetPos[3] - offset)

            platoon:Stop()
            platoon:AggressiveMoveToLocation(targetPos)
            platoon:Patrol(p1)
            platoon:Patrol(p2)
            platoon:Patrol(p3)
            platoon:Patrol(p4)
        end

        -- Re-evaluate target every 15-25 seconds with jitter
        WaitSeconds(15.0 + math.random() * 10.0)
        if planArmy and not IsPlatoonInCombat(platoon) then
            local brain = platoon:GetBrain()
            if brain and targetPos then
                local enemies = brain:GetUnitsAroundPoint(categories.ALLUNITS - categories.WALL, targetPos, 30.0, 'Enemy')
                if not enemies or table.empty(enemies) then
                    local airPos = platoon:GetPlatoonPosition()
                    targetPos = Targeting.GetWeightedEnemyTarget(planArmy, airPos)
                end
            end
        end
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
            targetPos = Targeting.GetWeightedEnemyTarget(planArmy)
        end

        local allIdle = true
        for _, u in units do
            if u and not u.Dead and not u:BeenDestroyed() then
                if not u:IsIdle() then
                    allIdle = false
                    break
                end
            end
        end

        if targetPos and (allIdle or not currentAssignedPos or currentAssignedPos[1] ~= targetPos[1] or currentAssignedPos[3] ~= targetPos[3]) then
            currentAssignedPos = targetPos

            -- High-speed recon flight: sprint directly to the target location first to scout ahead immediately!
            platoon:Stop()
            platoon:MoveToLocation(targetPos, false)

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

            platoon:Patrol(p1)
            platoon:Patrol(p2)
            platoon:Patrol(p3)
            platoon:Patrol(p4)
        end

        -- Re-evaluate and scout fresh targets every 20-30 seconds
        WaitSeconds(20.0 + math.random() * 10.0)
        if planArmy then
            local scoutPos = platoon:GetPlatoonPosition()
            targetPos = Targeting.GetWeightedEnemyTarget(planArmy, scoutPos)
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
            elseif instigator and not instigator.Dead then
                IssueAggressiveMove({unit}, instigator:GetPosition())
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
                if u and not u.Dead and not u:BeenDestroyed() then
                    if not u:IsIdle() then
                        allIdle = false
                        break
                    end
                end
            end

            -- If target is missing, destroyed, or squad is idle, locate next rear eco/radar/artillery target
            if not targetPos or allIdle then
                local bestTarget = platoon:FindClosestUnit('Attack', 'Enemy', true,
                    categories.STRUCTURE * (categories.MASSEXTRACTION + categories.ENERGYPRODUCTION + categories.RADAR + categories.INDIRECTFIRE)
                )
                if bestTarget and not bestTarget.Dead then
                    targetPos = bestTarget:GetPosition()
                else
                    targetPos = Targeting.GetWeightedEnemyTarget(army)
                end
            end

            if targetPos then
                local tPos = targetPos
                if tPos and not tPos[1] and tPos.GetPosition then
                    tPos = tPos:GetPosition()
                end

                if allIdle or not currentAssignedPos or currentAssignedPos[1] ~= tPos[1] or currentAssignedPos[3] ~= tPos[3] then
                    currentAssignedPos = tPos
                    platoon:Stop()
                    platoon:AggressiveMoveToLocation(tPos)
                end
            end

            WaitSeconds(6.0 + math.random() * 2.0)
        end
    end)
end

