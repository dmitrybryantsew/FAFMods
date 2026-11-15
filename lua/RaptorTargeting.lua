-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/lua/RaptorTargeting.lua
-- **  Author   :  Ported from Beyond All Reason to FAF
-- **  Summary  :  Economy-weighted targeting system ("Smelling Eco").
-- **              Directs raptor swarm platoons toward high-value power
-- **              generators, mass extractors, silos, and experimental weapons.
-- **
-- ****************************************************************************

local okNav, NavUtils = pcall(import, '/lua/sim/NavUtils.lua')
local TargetRegistry = {}
local TotalEcoWeight = 0

---Calculates economic target weight for a given FAF unit
---@param unit Unit
---@param bp UnitBlueprint
---@return number weight
function CalculateUnitEcoWeight(unit, bp)
    if not bp then return 1 end
    local cats = bp.CategoriesHash or {}

    -- 1. Game-Ending Economic Experimentals (The Paragon)
    if cats['EXPERIMENTAL'] and cats['ECONOMIC'] then
        return 10000
    end

    -- 2. Strategic Artillery (Mavor, Scathis, Salvation, Disruptor)
    if cats['STRATEGIC'] and cats['ARTILLERY'] then
        return 3000
    end

    -- 3. Strategic Nuclear Silos & Anti-Nukes
    if cats['SILO'] then
        return cats['NUKE'] and 2000 or 1500
    end

    -- 4. T3 Power Generation (AFUS equivalent)
    if cats['ENERGYPRODUCTION'] and cats['TECH3'] then
        return 1500
    end

    -- 5. Decoys (Bait Traps)
    if cats['DECOY'] then
        return 1500
    end

    -- 6. Mobile Experimentals (Colossus, Monkeylord, Fatboy, Czar)
    if cats['EXPERIMENTAL'] and cats['MOBILE'] then
        return 1200
    end

    -- 7. T3 Mass Extraction & Fabrication
    if cats['MASSEXTRACTION'] and cats['TECH3'] then
        return 750
    end
    if cats['MASSFABRICATION'] and cats['TECH3'] then
        return 500
    end

    -- 8. T3 Factories / HQs
    if cats['FACTORY'] and cats['TECH3'] then
        return 400
    end

    -- 9. T2 Economy
    if cats['MASSEXTRACTION'] and cats['TECH2'] then
        return 250
    end
    if cats['ENERGYPRODUCTION'] and cats['TECH2'] then
        return 200
    end
    if cats['FACTORY'] and cats['TECH2'] then
        return 150
    end

    -- 10. Armored Command Unit (ACU)
    if cats['COMMAND'] then
        return 150
    end

    -- 11. T1 Economy & Factories
    if cats['MASSEXTRACTION'] and cats['TECH1'] then
        return 30
    end
    if cats['ENERGYPRODUCTION'] and cats['TECH1'] then
        return 25
    end
    if cats['FACTORY'] and cats['TECH1'] then
        return 35
    end

    -- 12. Defenses & Shield Generators
    if cats['DEFENSE'] then
        if cats['SHIELD'] then return 20 end
        if cats['TECH3'] then return 15 end
        if cats['TECH2'] then return 8 end
        return 3
    end

    -- 13. Default Combat Mobile Units
    return 1
end

---Registers an enemy unit into the targeting engine
---@param unit Unit
function RegisterUnitTarget(unit)
    if not unit or unit.Dead or unit:BeenDestroyed() then return end
    local entityId = unit:GetEntityId()
    if TargetRegistry[entityId] then return end

    local bp = unit:GetBlueprint()
    local weight = CalculateUnitEcoWeight(unit, bp)

    TargetRegistry[entityId] = {
        unit = unit,
        weight = weight,
        army = unit:GetArmy(),
    }
    TotalEcoWeight = TotalEcoWeight + weight
end

---Removes a unit from the targeting engine upon destruction
---@param unit Unit
function UnregisterUnitTarget(unit)
    if not unit then return end
    local entityId = unit:GetEntityId()
    local entry = TargetRegistry[entityId]
    if entry then
        TotalEcoWeight = math.max(0, TotalEcoWeight - entry.weight)
        TargetRegistry[entityId] = nil
    end
end

---Helper to determine if a target is submerged or on the seabed (underwater)
---Units without torpedoes or depth-charge/anti-sub weapons CANNOT attack these targets!
---@param unit Unit
---@return boolean isUnderwater
function IsTargetUnderwater(unit)
    if not unit or unit.Dead or (unit.BeenDestroyed and unit:BeenDestroyed()) then return false end
    local layer = unit:GetCurrentLayer()
    if layer == 'Sub' or layer == 'Seabed' then
        return true
    end

    local bp = unit:GetBlueprint()
    local cats = (bp and bp.CategoriesHash) or {}
    if cats['SUBMERSIBLE'] then
        return true
    end

    local uPos = unit:GetPosition()
    if uPos then
        local surfY = GetSurfaceHeight(uPos[1], uPos[3])
        -- Target is physically submerged below water surface
        if uPos[2] < (surfY - 0.5) then
            return true
        end
        local terrY = GetTerrainHeight(uPos[1], uPos[3])
        if surfY > (terrY + 1.2) and (cats['STRUCTURE'] or layer == 'Seabed') then
            return true
        end
    end

    return false
end

---Helper to determine if an enemy target is only reachable by air units (naval surface ships, water platforms)
---NOTE: Seabed and Submerged units are NOT reachable by air units and are handled by IsTargetUnderwater!
---@param unit Unit
---@return boolean isAirOnly
function IsTargetAirOnly(unit)
    if not unit or unit.Dead or (unit.BeenDestroyed and unit:BeenDestroyed()) then return false end
    local layer = unit:GetCurrentLayer()
    if layer == 'Water' then
        return true
    end

    local bp = unit:GetBlueprint()
    local cats = (bp and bp.CategoriesHash) or {}
    if cats['NAVAL'] and not cats['SUBMERSIBLE'] then
        return true
    end

    local uPos = unit:GetPosition()
    if uPos then
        local surfY = GetSurfaceHeight(uPos[1], uPos[3])
        local terrY = GetTerrainHeight(uPos[1], uPos[3])
        if surfY > (terrY + 1.2) and not IsTargetUnderwater(unit) then
            return true
        end
    end

    return false
end

---Gets the playable boundaries of the current map with safety margin
---@param margin number|nil Default 25
---@return number minX, number minZ, number maxX, number maxZ
function GetPlayableBounds(margin)
    margin = margin or 25
    local mapW = (ScenarioInfo and ScenarioInfo.size and ScenarioInfo.size[1]) or 1024
    local mapH = (ScenarioInfo and ScenarioInfo.size and ScenarioInfo.size[2]) or 1024
    local pa = ScenarioInfo and ScenarioInfo.PlayableArea
    local minX = (pa and pa[1]) or 0
    local minZ = (pa and pa[2]) or 0
    local maxX = (pa and pa[3]) or mapW
    local maxZ = (pa and pa[4]) or mapH

    if minX > maxX then minX, maxX = maxX, minX end
    if minZ > maxZ then minZ, maxZ = maxZ, minZ end

    minX = minX + margin
    minZ = minZ + margin
    maxX = math.max(minX + 1, maxX - margin)
    maxZ = math.max(minZ + 1, maxZ - margin)

    return minX, minZ, maxX, maxZ
end

---Clamps a target position to remain strictly inside the playable map bounds
---@param pos Vector3
---@param margin number|nil
---@return Vector3
function ClampPositionToMap(pos, margin)
    if not pos then return nil end
    local minX, minZ, maxX, maxZ = GetPlayableBounds(margin)
    local cx = math.max(minX, math.min(maxX, pos[1]))
    local cz = math.max(minZ, math.min(maxZ, pos[3]))
    local cy = GetSurfaceHeight(cx, cz)
    return Vector(cx, cy, cz)
end

---Checks whether a position is valid and lies strictly inside the playable map area
---@param pos Vector3
---@param margin number|nil
---@return boolean
function IsPositionValidAndOnMap(pos, margin)
    if not pos or not pos[1] or not pos[3] then return false end
    if pos[1] == 0 and pos[3] == 0 then return false end
    local minX, minZ, maxX, maxZ = GetPlayableBounds(margin)
    return (pos[1] >= minX and pos[1] <= maxX and pos[3] >= minZ and pos[3] <= maxZ)
end

---Picks an economy target weighted by value, discounted by distance, and filtered by defensive threat
---@param raptorArmy number Army index of the Raptor swarm
---@param originPos Vector3|nil Launching position (hive or platoon centroid)
---@param isAir boolean|nil If true, caller is an aerial squad and can engage water/surface targets
---@return Vector3|nil TargetPosition
function GetWeightedEnemyTarget(raptorArmy, originPos, isAir)
    if TotalEcoWeight <= 0 or table.empty(TargetRegistry) then
        return GetFallbackEnemyTarget(raptorArmy, isAir, originPos)
    end

    local aiBrain = nil
    if raptorArmy then
        if type(raptorArmy) == 'number' then
            aiBrain = GetArmyBrain(raptorArmy)
        elseif type(raptorArmy) == 'table' or type(raptorArmy) == 'userdata' then
            aiBrain = raptorArmy
        end
    end

    local bestTarget = nil
    local highestScore = -1

    for entityId, data in TargetRegistry do
        local u = data.unit
        if u and not u.Dead and not u:BeenDestroyed() then
            if not raptorArmy or u:GetArmy() ~= raptorArmy then
                -- Underwater & Seabed targets (submarines, seabed extractors):
                -- Raptors do NOT possess torpedoes or anti-sub/depth weapons.
                -- Both land and air units CANNOT attack underwater/seabed targets and MUST ignore them!
                if IsTargetUnderwater(u) then
                    continue
                end

                -- Land platoons MUST NOT target units floating in deep water or surface naval vessels
                local airOnly = IsTargetAirOnly(u)
                if not isAir and (airOnly or u:GetCurrentLayer() == 'Water') then
                    continue
                end

                -- Land reachability check: if originPos is provided and not isAir, verify path exists!
                local uPos = u:GetPosition()
                if not isAir and originPos and okNav and NavUtils and NavUtils.IsGenerated and NavUtils.IsGenerated() then
                    if not NavUtils.CanPathTo('Land', originPos, uPos) then
                        continue
                    end
                end

                local dist = 100.0
                if originPos then
                    local dx = uPos[1] - originPos[1]
                    local dz = uPos[3] - originPos[3]
                    dist = math.sqrt(dx * dx + dz * dz)
                end

                -- Distance attenuation: nearby targets score exponentially higher than distant ones
                local distFactor = math.max(1.0, dist * 0.015)

                -- Defensive threat discount: favor unfortified or lightly defended expansions
                local threatFactor = 1.0
                if aiBrain and aiBrain.GetThreatAtPosition then
                    local threat = aiBrain:GetThreatAtPosition(uPos, 1, true, 'AntiSurface') or 0
                    if threat > 0 then
                        threatFactor = 1.0 + (threat * 0.04)
                    end
                end

                -- Combined score with small random jitter (0.8 - 1.2) to prevent deterministic lock
                local score = (data.weight / (distFactor * distFactor * threatFactor)) * (0.8 + math.random() * 0.4)

                if score > highestScore then
                    highestScore = score
                    bestTarget = Vector(uPos[1], uPos[2], uPos[3])
                end
            end
        else
            -- Clean dead entry
            TotalEcoWeight = math.max(0, TotalEcoWeight - (data.weight or 0))
            TargetRegistry[entityId] = nil
        end
    end

    if bestTarget then
        -- Add slight random scatter to prevent exact point stack-up, clamped safely within map bounds
        local sx = bestTarget[1] + math.random(-15, 15)
        local sz = bestTarget[3] + math.random(-15, 15)
        return ClampPositionToMap(Vector(sx, 0, sz), 25)
    end

    return GetFallbackEnemyTarget(raptorArmy, isAir, originPos)
end

---Backward-compatible wrapper for GetWeightedEnemyTarget
---@param raptorArmy number
---@param originPos Vector3|nil
---@param isAir boolean|nil
---@return Vector3|nil
function GetWeightedRandomEnemyTarget(raptorArmy, originPos, isAir)
    return GetWeightedEnemyTarget(raptorArmy, originPos, isAir)
end

---Fallback targeting if no economy structures are currently registered
---@param raptorArmy number
---@param isAir boolean|nil
---@param originPos Vector3|nil
---@return Vector3|nil
function GetFallbackEnemyTarget(raptorArmy, isAir, originPos)
    local mapW = (ScenarioInfo and ScenarioInfo.size and ScenarioInfo.size[1]) or 1024
    local mapH = (ScenarioInfo and ScenarioInfo.size and ScenarioInfo.size[2]) or 1024
    local allUnits = GetUnitsInRect(Rect(0, 0, mapW, mapH)) or {}
    for _, u in allUnits do
        if u and not u.Dead and (not raptorArmy or u:GetArmy() ~= raptorArmy) then
            local bp = u:GetBlueprint()
            if bp and bp.CategoriesHash and (bp.CategoriesHash['COMMAND'] or bp.CategoriesHash['STRUCTURE']) then
                if IsTargetUnderwater(u) then
                    continue
                end
                if not isAir and (IsTargetAirOnly(u) or u:GetCurrentLayer() == 'Water') then
                    continue
                end
                local p = u:GetPosition()
                if not isAir and originPos and okNav and NavUtils and NavUtils.IsGenerated and NavUtils.IsGenerated() then
                    if not NavUtils.CanPathTo('Land', originPos, p) then
                        continue
                    end
                end
                p[1] = p[1] + math.random(-20, 20)
                p[3] = p[3] + math.random(-20, 20)
                return ClampPositionToMap(p, 25)
            end
        end
    end
    -- Ultimate fallback: Center of playable map
    local minX, minZ, maxX, maxZ = GetPlayableBounds(30)
    local mx = (minX + maxX) * 0.5
    local mz = (minZ + maxZ) * 0.5
    local center = Vector(mx, GetSurfaceHeight(mx, mz), mz)
    if not isAir and originPos and okNav and NavUtils and NavUtils.IsGenerated and NavUtils.IsGenerated() then
        if not NavUtils.CanPathTo('Land', originPos, center) then
            return nil
        end
    end
    return center
end
