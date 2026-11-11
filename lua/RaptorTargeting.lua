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

---Picks a weighted random enemy location across all registered targets
---@param raptorArmy number Army index of the Raptor swarm
---@return Vector3|nil TargetPosition
function GetWeightedRandomEnemyTarget(raptorArmy)
    if TotalEcoWeight <= 0 or table.empty(TargetRegistry) then
        return GetFallbackEnemyTarget(raptorArmy)
    end

    local roll = math.random() * TotalEcoWeight
    local cumulative = 0

    for entityId, data in TargetRegistry do
        local u = data.unit
        if u and not u.Dead and not u:BeenDestroyed() then
            -- Verify unit belongs to an enemy army
            if not raptorArmy or u:GetArmy() ~= raptorArmy then
                cumulative = cumulative + data.weight
                if roll <= cumulative then
                    local pos = u:GetPosition()
                    -- Add scatter offset (+/- 24 units) to prevent exact single-point stacking
                    pos[1] = pos[1] + (math.random(-24, 24))
                    pos[3] = pos[3] + (math.random(-24, 24))
                    pos[2] = GetSurfaceHeight(pos[1], pos[3])
                    return pos
                end
            end
        else
            -- Clean dead entry
            TotalEcoWeight = math.max(0, TotalEcoWeight - data.weight)
            TargetRegistry[entityId] = nil
        end
    end

    return GetFallbackEnemyTarget(raptorArmy)
end

---Fallback targeting if no economy structures are currently registered
---@param raptorArmy number
---@return Vector3|nil
function GetFallbackEnemyTarget(raptorArmy)
    local allUnits = GetUnitsInRect(Rect(0, 0, ScenarioInfo.size[1], ScenarioInfo.size[2])) or {}
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
    local mx = ScenarioInfo.size[1] * 0.5
    local mz = ScenarioInfo.size[2] * 0.5
    return Vector(mx, GetSurfaceHeight(mx, mz), mz)
end
