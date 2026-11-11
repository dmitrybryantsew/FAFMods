# Raptor Anger Modeling & Stat Scaling Specification (FAF Port)

This document formalizes the **Dual-Anger Engine** (Tech Anger vs. Queen Anger) and explains how to replace Beyond All Reason's (BAR) unit XP veterancy with a **FAF Dynamic Mutation & Stat Scaling System**.

---

## 1. The Dual-Anger System Architecture

The game pacing does not rely on a fixed linear mission script. Instead, two synchronized meters govern the swarm:

```
                    ┌───────────────────────────────────────────────┐
                    │               GAME SIMULATION                │
                    └──────────────────────┬────────────────────────┘
                                           │
                    ┌──────────────────────┴────────────────────────┐
                    │                                               │
                    ▼                                               ▼
         ┌─────────────────────┐                         ┌─────────────────────┐
         │     TECH ANGER      │                         │     QUEEN ANGER     │
         │     (0 - 999+)      │                         │      (0 - 100%)     │
         └──────────┬──────────┘                         └──────────┬──────────┘
                    │                                               │
          • Squad Tech Level (T1-T4)                       • Queen Gestation
          • Spire Defense Evolution                        • Wave Veteran Tier (0-5)
          • Wave Size Cap Scaling                          • Minion Production Rate
          • Unlocks Air & Artillery                        • Extinction Retaliation
```

---

## 2. Mathematical Anger Formulas for FAF

### A. Tech Anger (`TechAnger`)
Governs the **technological threat level** of the swarm (unit blueprints, weapon types, and wave volume).

$$\text{TechAnger} = \max\left(0, \min\left(999, \left\lfloor \frac{t - \text{GracePeriod}}{\text{QueenTime} - \text{GracePeriod}} \times 100 \times \left(0.5 + 0.5 \times \text{EconomyScale}\right) \right\rfloor\right)\right)$$

Where:
- $t$: Current game time in seconds.
- $\text{GracePeriod}$: Peacetime buffer before first wave (e.g. $420\text{s} = 7\text{ min}$ on Normal).
- $\text{QueenTime}$: Scheduled time for queen emergence (e.g. $2700\text{s} = 45\text{ min}$ on Normal).
- $\text{EconomyScale}$: Player resource factor (calculated from match starting resources & multipliers):
  $$\text{EconomyScale} = \min\left(5.0, \; 0.33 \times \text{IncomeMult} + 0.67\right)$$

#### Tech Anger Milestones:
* **$0 - 20$ (T1 Swarm):** Basic 4-legged swarmers (`XRA0101`), Kamikaze ticks (`XRA0103`), T1 Acid Spires (`XRA0108`).
* **$20 - 45$ (T2 Infiltration):** All-Terrain 6-legged crawlers (`XRA0201`), Bio Artillery (`XRA0202`), Air Bombers (`XRA0104`), Weaver Healers (`XRA0109`).
* **$45 - 75$ (T3 Heavy Infestation):** Armored Behemoths (`XRA0301`), Flying Hunter Gunships (`XRA0205`), Brood Spires (`XRA0208`), EMP Spires (`XRA0209`).
* **$75 - 100+$ (T4 Apex & Siege):** Meteor Launchers (`XRA0309`), Anti-Nuke Spires (`XRA0307`), Spectre Infiltrators (`XRA0306`).

---

### B. Queen Anger (`QueenAnger`) & Player Aggression
Governs the **hatching countdown** of the Matriarch Queen Titan.

$$\text{QueenAnger} = \text{clamp}\left(0, 100, \left\lfloor \frac{t - \text{GracePeriod}}{\text{QueenTime} - \text{GracePeriod}} \times 100 \right\rfloor + \text{QueenAngerAggressionLevel}\right)$$

#### Player Aggression Spikes
When players strike aggressively at the swarm's infrastructure, the hive mind accelerates Queen maturation:

1. **Hive (Burrow) Destroyed:**
   $$\Delta \text{Aggression} = \frac{\text{AngerBonus}}{\text{RaptorSpawnMultiplier}}$$
   *(On Normal difficulty, $\text{AngerBonus} = 0.20$; destroying 5 hives inflicts $+1.0$ permanent aggression pressure).*
2. **Turret / Spire Destroyed:**
   $$\Delta \text{Aggression} = 0.10 \times \left(\frac{\text{AngerBonus}}{\text{RaptorSpawnMultiplier}}\right)$$
3. **Passive Aggression Decay:**
   Every second ($1.0\text{s}$), aggression dissipates slightly:
   $$\text{PlayerAggression} = \text{PlayerAggression} \times 0.995$$
4. **Economic Greed Penalty:**
   Each operational T3 Power Generator or AFUS on the map injects a persistent rate of anger:
   $$\Delta \text{Anger}_{\text{eco}} = +0.0005 \times \frac{3600}{\text{QueenTime}} \quad \text{per second}$$

#### The Extinction Retaliation Trigger
> [!CAUTION]
> If players manage to kill nearly all hives ($\text{BurrowCount} \le 1$) after the Grace Period has elapsed, **Queen Anger is instantly locked to 100%**, forcing the Queen to hatch immediately regardless of match clock!

---

## 3. Offsetting BAR Unit XP with FAF Dynamic Stat Scaling

In BAR's Spring engine, `SetUnitExperience(unitID, xp)` dynamically scales HP, weapon reload speed, and accuracy by up to $300\%$.

In Supreme Commander / FAF, we replace this with a **Dual-Layer Stat Upgrade System**:
1. **Engine Veterancy Tiers (Levels 1 to 5)**
2. **Dynamic Blueprint Buffs (`Buff.lua`)** applied at spawn time.

### A. Veterancy Tier Assignment on Spawn
Every raptor unit spawned reads the global `QueenAnger` and is immediately granted veteran ranks via `unit:SetVeterancy(level)`:

| Queen Anger Range | FAF Veterancy Rank | Max HP Bonus | Biological Health Regen | Visual Indicator |
| :---: | :---: | :---: | :---: | :---: |
| **$0\% - 20\%$** | Rank 0 (Standard) | $+0\%$ | Standard ($+1 - 5\text{ HP/s}$) | Normal Skin |
| **$21\% - 40\%$** | **Rank 1 (Mutated)** | $+10\%$ | $+10\text{ HP/s}$ | 1 Chevron |
| **$41\% - 60\%$** | **Rank 2 (Hardened)** | $+20\%$ | $+20\text{ HP/s}$ | 2 Chevrons |
| **$61\% - 80\%$** | **Rank 3 (Apex)** | $+30\%$ | $+30\text{ HP/s}$ | 3 Chevrons |
| **$81\% - 99\%$** | **Rank 4 (Frenzied)**| $+40\%$ | $+40\text{ HP/s}$ | 4 Chevrons |
| **$100\%$ (Boss Phase)**| **Rank 5 (Transcendent)**| $+50\%$ | $+50\text{ HP/s}$ | 5 Chevrons / Glow |

### B. The FAF Master Overhaul In-Game Stat Modifying Engine
Modifying unit stats in Supreme Commander: Forged Alliance has historically been tricky because unit blueprints (`UnitBlueprint`) and weapon blueprints (`WeaponBlueprint`) are read-only C++ structures—mutating them directly either desyncs the simulation or affects all units globally.

The **FAF Master Overhaul** (`/mods/FAF Master Overhaul/hook/lua/sim/Unit.lua`) proved that stats can be cleanly modified in-game on live unit instances using a unified hooked architecture. We adopt this exact battle-tested engine:

```lua
-- /mods/RaptorFaction/lua/RaptorStats.lua
local Buff = import('/lua/sim/buff.lua')
local BuffBlueprint = BuffBlueprint

---Recomputes and applies all dynamic Raptor stats based on Anger & Difficulty
---Adopts the FAF Master Overhaul in-game stat modification engine
---@param unit Unit
---@param techAnger number (0 - 999)
---@param queenAnger number (0 - 100)
---@param difficulty string
function RecomputeRaptorStats(unit, techAnger, queenAnger, difficulty)
    if not unit or unit:BeenDestroyed() or unit:IsDead() then return end

    local diffMods = {
        veryeasy = { Health = 0.50, Damage = 0.40, Speed = 0.85, Regen = 0.5 },
        easy     = { Health = 0.75, Damage = 0.60, Speed = 0.90, Regen = 0.75 },
        normal   = { Health = 1.00, Damage = 0.80, Speed = 1.00, Regen = 1.0 },
        hard     = { Health = 1.10, Damage = 1.00, Speed = 1.05, Regen = 1.25 },
        veryhard = { Health = 1.25, Damage = 1.20, Speed = 1.10, Regen = 1.5 },
        epic     = { Health = 1.50, Damage = 1.40, Speed = 1.15, Regen = 2.0 },
    }
    local d = diffMods[difficulty] or diffMods['normal']

    -- Scale multipliers with Tech & Queen Anger
    local angerNorm = math.min(100, techAnger)
    local totalHpMult    = d.Health * (1.0 + angerNorm * 0.003)
    local totalDmgMult   = d.Damage * (1.0 + angerNorm * 0.003)
    local totalSpeedMult = d.Speed  * (1.0 + angerNorm * 0.001)
    local totalRegenMult = d.Regen  * (1.0 + (queenAnger * 0.01))

    -- 1. HEALTH: Master Overhaul Dynamic Buff Pattern
    -- Generates unique BuffBlueprint on the fly and applies it cleanly
    local buffName = 'Raptor_HP_' .. string.gsub(string.format("%.3f", totalHpMult), "%.", "_")
    if not Buffs[buffName] then
        BuffBlueprint {
            Name = buffName,
            DisplayName = buffName,
            BuffType = 'RAPTOR_TOTAL_HEALTH',
            Stacks = 'REPLACE',
            Duration = -1,
            Affects = {
                MaxHealth = {
                    Add = 0,
                    Mult = totalHpMult,
                    DoNotFill = false,
                },
            },
        }
    end
    Buff.ApplyBuff(unit, buffName)
    unit:SetHealth(unit, unit:GetMaxHealth())

    -- 2. OUTBOUND DAMAGE: Master Overhaul OnDamage Hook
    -- Avoids C++ blueprint mutation; multiplies in OnDamage via unit property
    unit.RaptorTotalDmgMult = totalDmgMult

    -- 3. MOBILITY: Engine Acceleration, Speed, and Turn Multipliers
    if unit.SetSpeedMult then unit:SetSpeedMult(totalSpeedMult) end
    if unit.SetAccMult   then unit:SetAccMult(totalSpeedMult) end
    if unit.SetTurnMult  then unit:SetTurnMult(totalSpeedMult) end

    -- 4. WEAPONS: Range, Rate of Fire, and Splash Radius
    local wCount = unit:GetWeaponCount() or 0
    for i = 1, wCount do
        local wep = unit:GetWeapon(i)
        if wep then
            local wbp = wep:GetBlueprint()
            -- Range scaling (up to +15% at 100 anger for artillery/spikers)
            if wbp and wbp.MaxRadius and wep.ChangeMaxRadius then
                local rangeMult = 1.0 + (angerNorm * 0.0015)
                wep:ChangeMaxRadius(math.floor(wbp.MaxRadius * rangeMult))
            end
            -- Rate of fire scaling
            if wbp and wbp.RateOfFire and wep.SetRateOfFire then
                local rofMult = 1.0 + (angerNorm * 0.001)
                wep:SetRateOfFire(wbp.RateOfFire * rofMult)
            end
        end
    end

    -- 5. REGENERATION
    local bp = unit:GetBlueprint()
    local baseRegen = (bp.Defense and bp.Defense.RegenRate) or 5
    if unit.SetRegenRate then
        unit:SetRegenRate(math.floor(baseRegen * totalRegenMult))
    end
end
```

### C. Integrating the OnDamage Hook
In `/mods/RaptorFaction/units/` scripts or base class:
```lua
OnDamage = function(self, instigator, amount, vector, damageType)
    local amt = amount
    -- Apply Master Overhaul outbound damage multiplier
    if instigator and instigator.RaptorTotalDmgMult and instigator.RaptorTotalDmgMult ~= 1.0 and amt > 0 then
        amt = amt * instigator.RaptorTotalDmgMult
    end
    return BaseClass.OnDamage(self, instigator, amt, vector, damageType)
end
```

