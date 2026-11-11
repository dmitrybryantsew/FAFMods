# Raptor Squad Tactics & Biological Behaviors Specification

This document details the squad-level AI platoon coordinator, pack regrouping algorithms, and individual behavioral traits (Skirmish, Berserk, Teleportation, Healer Auras, Kamikaze) ported from Beyond All Reason to FAF.

---

## 1. Pack Regrouping & Platoon Coordination

In standard FAF, units ordered across the map string out into long, single-file lines where fast units arrive and die piecemeal. BAR Raptors prevent this via **Pack Centroid Cohesion**.

```
    [Scattered Units]                   [Regroup Order]                   [Cohesive Strike]
   Unit A                                                                   
            Unit B                         Centroid                         [A B C D E]
   Unit C                                  (Average)                            │
            Unit D             ───────►        ●        ───────►                ▼
                                                                         Aggressive Move
                  Unit E                                                  Toward Target
```

### Platoon Centroid Algorithm (`RaptorPlatoonAI.lua`)
Every $2.0\text{ seconds}$, each active Raptor Platoon calculates its bounding box:

```lua
---Evaluates platoon cohesion and issues regroup or assault orders
---@param platoon Platoon
---@param targetPos Vector3
function ManageRaptorSquadOrders(platoon, targetPos)
    local units = platoon:GetPlatoonUnits()
    if table.empty(units) or not targetPos then return end

    local xmin, xmax = 999999, -999999
    local zmin, zmax = 999999, -999999
    local xsum, zsum = 0, 0
    local count = 0

    for _, u in units do
        if u and not u.Dead then
            local pos = u:GetPosition()
            if pos[1] < xmin then xmin = pos[1] end
            if pos[1] > xmax then xmax = pos[1] end
            if pos[3] < zmin then zmin = pos[3] end
            if pos[3] > zmax then zmax = pos[3] end
            xsum = xsum + pos[1]
            zsum = zsum + pos[3]
            count = count + 1
        end
    end

    if count == 0 then return end

    local xavg = xsum / count
    local zavg = zsum / count
    local maxSpread = 32 -- Equivalent to BAR's 512 elmos in FAF grid units

    -- Check if platoon is excessively strung out
    local isDispersed = (xmin < xavg - maxSpread) or (xmax > xavg + maxSpread)
                     or (zmin < zavg - maxSpread) or (zmax > zavg + maxSpread)

    if isDispersed then
        -- 1. Regroup phase: Issue Move order to Centroid to reform the pack
        platoon:Stop()
        platoon:MoveToLocation(Vector(xavg, GetSurfaceHeight(xavg, zavg), zavg), false)
        platoon.IsRegrouping = true
    else
        -- 2. Attack phase: Platoon is dense and cohesive -> Aggressive Move to Target
        if platoon.IsRegrouping or not platoon.HasAssaultOrder then
            platoon:Stop()
            -- Add scatter offset to target to prevent unit clump collisions
            local scatterX = targetPos[1] + math.random(-15, 15)
            local scatterZ = targetPos[3] + math.random(-15, 15)
            platoon:AggressiveMoveToLocation(Vector(scatterX, targetPos[2], scatterZ))
            platoon.IsRegrouping = false
            platoon.HasAssaultOrder = true
        end
    end
end
```

---

## 2. Individual Unit Behavioral Archetypes

### A. The SKIRMISH Trait (Kiting)
* **Used by:** Mobile Spikers (`XRA0201`), Bio Artillery (`XRA0202`).
* **Behavior:** When the unit successfully fires upon an enemy, it triggers a check. With a $50\%$ chance, it immediately issues a backward move command away from the target for $15 - 25\text{ units}$ before re-engaging.
* **Effect:** Prevents ranged fire-support raptors from blindly running into point defenses or commander Overcharge range.

### B. The COWARD / DODGE Trait
* **Used by:** Light swarmers, Scout flyers, and damaged Matriarchs.
* **Trigger:** When current health falls below **$80\%$** of max HP upon taking damage.
* **Behavior:** Flee directly along the reverse vector away from the damage instigator for $2.5\text{ seconds}$.

### C. The BERSERK Trait
* **Used by:** Heavy Assault Behemoths (`XRA0301`), Fire Crawlers, Bosses.
* **Trigger:** Taking damage from enemy weapons at medium-to-long range.
* **Behavior:** Enrages the unit:
  - Movement speed temporarily boosted by $+35\%$ for 4 seconds.
  - Clears all retreat commands.
  - Issues direct `IssueAttack` order against the damage instigator entity.

### D. The SPECTRE Trait (Blink / Teleportation)
* **Used by:** Spectre Stalkers, Cloaked Infiltrators, Queen Titan.
* **Cooldown:** $2.0\text{ seconds}$ (Ground Spectres), $10 - 60\text{ seconds}$ (Queen).
* **Behavior:** When taking damage or attempting to dodge:
  1. Spawns purple void biological warp particle burst at current position.
  2. Teleports entity $15 - 25\text{ units}$ laterally or behind the target line.
  3. Spawns arrival warp particle burst and instantly resumes attacking.

```lua
function TriggerSpectreBlink(unit, targetPos)
    local curPos = unit:GetPosition()
    local angle = math.atan2(targetPos[1] - curPos[1], targetPos[3] - curPos[3])
    -- Lateral offset perpendicular to attack angle
    local blinkDist = 18.0
    local blinkX = curPos[1] + math.cos(angle) * blinkDist
    local blinkZ = curPos[3] - math.sin(angle) * blinkDist
    local blinkY = GetSurfaceHeight(blinkX, blinkZ)

    -- Particle FX
    CreateEmitterAtEntity(unit, unit:GetArmy(), '/mods/RaptorFaction/effects/emitters/raptor_warp_01_emit.bp')

    -- Engine Teleportation
    Warp(unit, Vector(blinkX, blinkY, blinkZ))

    CreateEmitterAtEntity(unit, unit:GetArmy(), '/mods/RaptorFaction/effects/emitters/raptor_warp_01_emit.bp')
end
```

### E. The HEALER Trait (Weaver Swarm Sustain)
* **Used by:** Weaver Healers (`XRA0109`).
* **Behavior:**
  - Emits a passive healing aura ($+40\text{ HP/s}$ within $22\text{ units}$).
  - Active Bio-Stream beam locks onto the lowest percentage HP friendly unit within range.
  - **Rule:** Healers **never heal other Healers** (prevents infinite mutual invulnerability loops).

### F. The KAMIKAZE Trait (Acid Ticks / Dodos)
* **Used by:** Kamikaze Ticks (`XRA0103`), Air Dodo Bombs.
* **Behavior:**
  - High acceleration, low HP.
  - Bypasses weapon cooldowns; triggers `OnDamage` or `OnCollision` explosion.
  - Self-destruct releases a lethal $8\text{m}$ splash of boiling acid ($1,200\text{ dmg}$ at T1, $4,500\text{ dmg}$ at T2).

---

## 3. Weapon Trait Matrix

| Unit ID | Archetype | Primary Behavior | Reaction Chance | Special Weapon Trait |
| :--- | :--- | :--- | :---: | :--- |
| `XRA0101` | Swarmer | Skirmish / Swarm | 25% | Low-damage high-volume kinetic bite. |
| `XRA0102` | All-Terrain | Berserk | 20% | Ignores terrain slope penalties. |
| `XRA0103` | Kamikaze Tick | Suicide Charge | 100% | High-yield area acid detonation on death. |
| `XRA0104` | Acid Bomber | Air Strike | 100% | Carpet-bomb acid cloud lingering damage. |
| `XRA0105` | Air Hunter | Coward (Low HP) | 35% | High-agility dogfighting & strafing. |
| `XRA0109` | Weaver Healer | Healer Aura | 100% | Bio-repair stream (excludes healers). |
| `XRA0201` | 6-Leg Crawler | Skirmish | 50% | 360° Gatling quill spine salvo. |
| `XRA0202` | Bio Artillery | Skirmish / Artil | 100% | High-arc acid mortar with friendly fire. |
| `XRA0205` | Hunter Gunship | Strafing Hover | 40% | Rotary bio-spike cannon. |
| `XRA0301` | Apex Behemoth | Berserk | 50% | Dual heavy scythes + anti-air spore pods. |
| `XRA0401` | Matriarch Queen | Adaptive Titan | Special | Roaring plasma, minion birth, blink dodge. |
