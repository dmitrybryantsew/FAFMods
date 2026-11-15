-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/lua/RaptorTargeting.lua
-- **  Author   :  Ported from Beyond All Reason to FAF
-- **  Summary  :  Economy-weighted targeting system ("Smelling Eco").
-- **              Directs raptor swarm platoons toward high-value power
-- **              generators, mass extractors, silos, and experimental weapons.
-- **
-- ****************************************************************************

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

---Picks an economy target weighted by value, discounted by distance, and filtered by defensive threat
---@param raptorArmy number Army index of the Raptor swarm
---@param originPos Vector3|nil Launching position (hive or platoon centroid)
---@return Vector3|nil TargetPosition
function GetWeightedEnemyTarget(raptorArmy, originPos)
    if TotalEcoWeight <= 0 or table.empty(TargetRegistry) then
        return GetFallbackEnemyTarget(raptorArmy)
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
                local uPos = u:GetPosition()
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
        -- Add slight random scatter to prevent exact point stack-up
        local sx = bestTarget[1] + math.random(-15, 15)
        local sz = bestTarget[3] + math.random(-15, 15)
        local sy = GetSurfaceHeight(sx, sz)
        return Vector(sx, sy, sz)
    end

    return GetFallbackEnemyTarget(raptorArmy)
end

---Backward-compatible wrapper for GetWeightedEnemyTarget
---@param raptorArmy number
---@param originPos Vector3|nil
---@return Vector3|nil
function GetWeightedRandomEnemyTarget(raptorArmy, originPos)
    return GetWeightedEnemyTarget(raptorArmy, originPos)
end

---Fallback targeting if no economy structures are currently registered
---@param raptorArmy number
---@return Vector3|nil
function GetFallbackEnemyTarget(raptorArmy)
    local mapW = (ScenarioInfo and ScenarioInfo.size and ScenarioInfo.size[1]) or 1024
    local mapH = (ScenarioInfo and ScenarioInfo.size and ScenarioInfo.size[2]) or 1024
    local allUnits = GetUnitsInRect(Rect(0, 0, mapW, mapH)) or {}
    for _, u in allUnits do
        if u and not u.Dead and (not raptorArmy or u:GetArmy() ~= raptorArmy) then
            local bp = u:GetBlueprint()
            if bp and bp.CategoriesHash and (bp.CategoriesHash['COMMAND'] or bp.CategoriesHash['STRUCTURE']) then
                local p = u:GetPosition()
                p[1] = p[1] + math.random(-20, 20)
                p[3] = p[3] + math.random(-20, 20)
                p[2] = GetSurfaceHeight(p[1], p[3])
                return p
            end
        end
    end
    -- Ultimate fallback: Center of map
    local mx = mapW * 0.5
    local mz = mapH * 0.5
    return Vector(mx, GetSurfaceHeight(mx, mz), mz)
end
