# FAF Unit Categorization & Raptor Targeting Weights Specification

This document details how Supreme Commander: Forged Alliance Forever (FAF) units and structures map to the Beyond All Reason (BAR) **Economy-Weight Targeting System** (`squadTargetsByEcoWeight`).

---

## 1. The Design Philosophy: "Smelling the Reactor"

In BAR, Raptors do not mindless assault the nearest wall or point defense. Their hivemind is biologically drawn toward **high concentrations of energy and processed mass**.
- Standard combat units, point defenses, and perimeter walls generate minimal target interest ($0 - 5$ weight).
- Power generators, mass extractors, and strategic silos emit intense economic scent ($25 - 3,000+$ weight).
- Swarms actively bypass peripheral garrisons to breach perimeter gaps and detonate player power grids.

---

## 2. FAF Unit Categories & Targeting Weights Table

The table below classifies every standard FAF structure and unit into economic weight categories for the Raptor target selection algorithm.

| Tier | Category / Unit Types | FAF Categories / Blueprints | Target Weight | Behavioral Reaction & Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **T0 / Noise** | Wreckage, Trees, Projectiles | `PROP`, `PROJECTILE` | **0** | Filtered out completely. |
| **T1 Low** | Combat Units, Walls, Radars | `LAND MOBILE`, `WALL`, `INTELLIGENCE` | **1 - 5** | Incidental targets. Only attacked if blocking path or closest when no eco exists. |
| **T1 Defenses** | Point Defense, Anti-Air, Torpedo | `DEFENSE DIRECTFIRE`, `DEFENSE ANTIAIR` | **5 - 10** | Low priority. |
| **T1 Economy** | T1 Mex, T1 PGen, Hydrocarbon | `ECONOMIC MASSEXTRACTION TECH1`, `ECONOMIC ENERGYPRODUCTION TECH1` | **25 - 40** | Early-game primary targets. |
| **T1 Factories** | Land, Air, Naval Factories | `FACTORY TECH1` | **35** | Moderate early interest. |
| **T2 Economy** | T2 Mex, T2 PGen | `ECONOMIC MASSEXTRACTION TECH2`, `ECONOMIC ENERGYPRODUCTION TECH2` | **200 - 250** | Strong mid-game target attractor. |
| **T2 Factories** | T2 Factory / HQ | `FACTORY TECH2` | **150** | Moderate priority. |
| **T2 Heavy Def** | TMD, T2 Heavy PD, Shields | `DEFENSE ANTIMISSILE`, `DEFENSE SHIELD` | **25** | Low priority unless shielding an eco node. |
| **T3 Mass Ext** | T3 Mex, Mass Fabricator | `ECONOMIC MASSEXTRACTION TECH3`, `ECONOMIC MASSFABRICATION TECH3` | **600 - 750** | Extreme high-value target. |
| **T3 Heavy Power**| **T3 Power Generator (PGen)** | `ECONOMIC ENERGYPRODUCTION TECH3` | **1,500** | **Critical target.** Triggers intense raptor homing vectors. |
| **T3 Factories** | T3 Factory / HQ | `FACTORY TECH3` | **400** | High target interest. |
| **Strategic Silos**| **SMD (Anti-Nuke), SML (Nuke Silo)**| `SILO ANTIMISSILE`, `SILO NUKE` | **1,500 - 2,000** | Prevents passive turtle nuclear dominance. |
| **Strategic LRPC**| Mavor, Scathis, Salvation, Disruptor | `STRATEGIC ARTILLERY` | **2,500 - 4,000** | Extreme siege priority; swarm rushes to silence gun. |
| **Experimentals** | Colossus, Monkeylord, Fatboy, Czar | `EXPERIMENTAL MOBILE` | **1,000 - 1,500** | Significant battlefield threat. |
| **The Paragon** | Aeon Resource Generator | `EXPERIMENTAL ECONOMIC` (`xab1401`) | **10,000** | **Absolute Priority.** Overrides all other global targets. |
| **ACU** | Armored Command Unit | `COMMAND` | **150** | Protected base target, but not overwhelming. |
| **Decoy Commander**| Cybran / UEF Decoy ACU | `DECOY` | **1,500** | **Tactical Decoy Trapping:** Exploited by players to divert swarms. |

---

## 3. Lua Targeting Algorithm Implementation

In FAF, targeting is managed in `/lua/RaptorTargeting.lua`. The target selection matches BAR's weighted probability distribution:

```lua
---@class RaptorTargeting
local TargetRegistry = {}
local TotalEcoWeight = 0

---Registers a player unit into the weighted targeting registry
---@param unit Unit
function RegisterUnitTarget(unit)
    local bp = unit:GetBlueprint()
    local weight = CalculateUnitEcoWeight(unit, bp)
    if weight > 0 then
        TargetRegistry[unit:GetEntityId()] = {
            unit = unit,
            weight = weight,
        }
        TotalEcoWeight = TotalEcoWeight + weight
    end
end

---Calculates economic weight according to FAF blueprint parameters
---@param unit Unit
---@param bp UnitBlueprint
---@return number
function CalculateUnitEcoWeight(unit, bp)
    local cats = bp.CategoriesHash

    -- 1. Game-Ending Economic Experimentals
    if cats['EXPERIMENTAL'] and cats['ECONOMIC'] then
        return 10000
    end

    -- 2. Strategic Missile Defenses & Nuclear Launchers
    if cats['SILO'] then
        return cats['NUKE'] and 2000 or 1500
    end

    -- 3. Strategic Artillery
    if cats['STRATEGIC'] and cats['ARTILLERY'] then
        return 3000
    end

    -- 4. T3 Energy (AFUS Equivalent)
    if cats['ENERGYPRODUCTION'] and cats['TECH3'] then
        return 1500
    end

    -- 5. Decoy Commander / Decoy Structures
    if cats['DECOY'] then
        return 1500
    end

    -- 6. T3 Mass Extractors & Fabricators
    if cats['MASSEXTRACTION'] and cats['TECH3'] then
        return 750
    end
    if cats['MASSFABRICATION'] and cats['TECH3'] then
        return 500
    end

    -- 7. T2 Economy
    if cats['MASSEXTRACTION'] and cats['TECH2'] then
        return 250
    end
    if cats['ENERGYPRODUCTION'] and cats['TECH2'] then
        return 200
    end

    -- 8. T1 Economy
    if cats['MASSEXTRACTION'] and cats['TECH1'] then
        return 30
    end
    if cats['ENERGYPRODUCTION'] and cats['TECH1'] then
        return 25
    end

    -- 9. Factories
    if cats['FACTORY'] then
        if cats['TECH3'] then return 400 end
        if cats['TECH2'] then return 150 end
        return 35
    end

    -- 10. Default / Combat Units
    return 1
end

---Picks a weighted random target across all registered enemy structures
---@return Vector3|nil TargetPosition
function GetWeightedRandomEnemyTarget()
    if TotalEcoWeight <= 0 or table.empty(TargetRegistry) then
        return nil
    end

    local roll = math.random() * TotalEcoWeight
    local cumulative = 0

    for entityId, data in TargetRegistry do
        local u = data.unit
        if u and not u.Dead then
            cumulative = cumulative + data.weight
            if roll <= cumulative then
                local pos = u:GetPosition()
                -- Add scatter offset (+/- 32 units) to prevent exact single-point stacking
                pos[1] = pos[1] + (math.random(-32, 32))
                pos[3] = pos[3] + (math.random(-32, 32))
                return pos
            end
        else
            -- Cleanup dead units
            TotalEcoWeight = TotalEcoWeight - data.weight
            TargetRegistry[entityId] = nil
        end
    end

    return nil
end
```

---

## 4. The Decoy Exploitation Mechanic

In Beyond All Reason, the code explicitly grants Decoy Fusions `+1000` weight:
```lua
if unitDef.customParams and unitDef.customParams.decoyfor == "armfus" then
    ecoValue = ecoValue + 1000
end
```

In FAF, this mechanism translates to **Cybran and UEF Decoy Commanders (`URB0101` / `UEB0101` upgrades)** and custom decoy props.
- By assigning decoy units a weight of **1,500**, players who study the swarm's biology can intentionally build "bait stations" flanked by heavy point defenses, artillery, or shields to draw the main weight of each raptor wave into pre-sighted kill zones.
