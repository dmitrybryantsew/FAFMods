# Raptor Queen Titan Boss Fight & Sequences Specification

This document details the multi-phase climactic boss encounter of the **Matriarch Queen Titan (`XRA0401`)** in FAF, including her awakening sequence, adaptive damage resistance, stagger mechanics, phase modifiers, and anti-cheese protections.

---

## 1. Queen Awakening Sequence

When Queen Anger reaches $100\%$ (or all hives are destroyed prematurely), the encounter transitions into the **Titan Boss Phase**:

```
      [Queen Anger Reaches 100%]
                 │
                 ├── Global Audio Cue: Titanic Bio-Roar & Map-Wide Ping
                 ├── Camera Shake & HUD Warning Banner
                 ├── Permanent Omniscience: Queen is permanently visible to all players
                 │
                 ▼
      [Escort Matriarch Mini-Bosses]
                 │
                 ├── Electric Matriarch (EMP Spores & Disruption)
                 ├── Acid Matriarch (Lingering Toxic Pools)
                 ├── Healer Matriarch (Bio-Stream Restoration)
                 ├── Spectre Matriarch (Blinking Stealth Infiltrator)
                 └── Pyro Matriarch (Flamethrower Incineration)
                 │
                 ▼
      [Wave Dynamics Shift]
                 ├── Background Swarm Waves reduced to 10% volume
                 └── Queen & Matriarchs continuously birth Broodlings & Healers
```

---

## 2. Dynamic Adaptive Resistance (Anti-Spam System)

If a team attempts to defeat the Queen by mass-producing a single unit type (such as 100 T3 Sniper Bots, Gunships, or heavy artillery), the Queen's alien physiology rapidly evolves immunity.

### Mathematical Model
1. The damage engine tracks cumulative damage dealt by each unique unit blueprint:
   $$\text{ResistanceDamage}[\text{BlueprintID}] = \text{ResistanceDamage}[\text{BlueprintID}] + \text{Damage} \times 5 \times \text{ResistanceMult}$$
2. The percentage resistance is computed against the Queen's maximum health pool:
   $$\text{ResistPercent} = \min\left(0.95, \; \frac{\text{ResistanceDamage}[\text{BlueprintID}]}{\text{QueenMaxHP}}\right)$$
3. Final damage applied to the Queen:
   $$\text{FinalDamage} = \text{Damage} \times (1.0 - \text{ResistPercent})$$

> [!WARNING]
> When resistance against a unit blueprint exceeds **$50\%$**, the UI broadcasts:
> *"WARNING: The Queen is biologically adapting to your weapons! Diversify your forces!"*
> Single-unit spam quickly drops to dealing only **$5\%$ of nominal damage**.

### Lua Implementation (`QueenAdaptiveResistance.lua`)
```lua
local QueenResistance = {}

---Filters incoming damage through the Queen's adaptive immune system
---@param queen Unit
---@param instigator Unit
---@param damage number
---@return number modifiedDamage
function ProcessQueenDamage(queen, instigator, damage)
    if not instigator or instigator.Dead then return damage end

    local bpId = instigator:GetBlueprint().BlueprintId
    local maxHp = queen:GetMaxHealth()

    if not QueenResistance[bpId] then
        QueenResistance[bpId] = { accumulated = 0, notified = false }
    end

    local entry = QueenResistance[bpId]
    local resistPercent = math.min(0.95, entry.accumulated / (maxHp * 0.8))

    -- Notify players at 50% adaptation
    if resistPercent >= 0.50 and not entry.notified then
        Sync.RaptorAnnounce = { Text = "Queen is adapting to " .. bpId .. "!", Color = 'red' }
        entry.notified = true
    end

    -- If Queen is currently Staggered, resistance is halved!
    if queen.IsStaggered then
        resistPercent = resistPercent * 0.50
    end

    local finalDamage = damage * (1.0 - resistPercent)
    entry.accumulated = entry.accumulated + (damage * 3.5)

    return finalDamage
end
```

---

## 3. Health Phase Damage Multipliers

As the Queen sustains damage, her biological behavior shifts across 5 distinct phases:

```
100% HP ─────────────────────────────────────────────────────────────► 0% HP
│      VULNERABLE PHASE      │    STANDARD    │    HARDENED    │ ENRAGED SHELL │
│   Incoming: 2.0x (Double!) │ Incoming: 1.0x │ Incoming: 0.75x│ Incoming: 0.25x│
│   Outbound: 0.25x          │ Outbound: 0.50x│ Outbound: 0.75x│ Outbound: 2.0x!│
└────────────────────────────┴────────────────┴────────────────┴───────────────┘
  100%                     50%              25%              10%   5%         0%
```

| Queen Current HP | Incoming Damage Multiplier | Queen Outbound Damage Multiplier | Tactical Behavior |
| :---: | :---: | :---: | :--- |
| **$> 50\%$** | **$2.0\times$ (Double)** | **$0.25\times$** | Easy to burst; Queen tests defenses with probe attacks. |
| **$25\% - 50\%$** | **$1.0\times$** | **$0.50\times$** | Standard combat; begins active minion births. |
| **$10\% - 25\%$** | **$0.75\times$** | **$0.75\times$** | Chitinous carapace hardens; begins short-range blinking. |
| **$5\% - 10\%$** | **$0.50\times$** | **$1.00\times$** | Spawns emergency Weaver Healer escorts. |
| **$< 5\%$** | **$0.25\times$ (Armored Shell)** | **$2.00\times$ (Lethal Enrage)** | Desperation state; titanic roar deals double damage! |

---

## 4. The Stagger Mechanic (Posture Break)

To reward coordinated burst damage, the Queen features a **Stagger Meter**:
- **Stagger Threshold:** Approximately $33\%$ of Queen Max HP.
- High-damage kinetic impacts, nuclear strikes, and experimental artillery fill the stagger meter.
- **When Staggered:**
  1. The Queen collapses, playing an incapacitated writhing animation for **$30 - 40\text{ seconds}$**.
  2. Movement and all weapon firing cease completely.
  3. **Adaptive resistances are cut in half** ($50\%$ reduction), creating the ultimate DPS damage window.
  4. Atmospheric bio-radiation lightning sparks wildly around her model.
  5. Dealing sustained massive damage while staggered slowly shaves time off the stun, eventually waking her up.

---

## 5. Anti-Cheese Rules & Engine Protections

To preserve the tactical challenge of the boss encounter, the following engine exploits are strictly mitigated in `XRA0401_script.lua`:

1. **Commander Overcharge (OC) / D-Gun:**
   * Direct Overcharge hits against the Queen are capped at **$4,000\text{ damage}$** (instead of instant one-shot annihilation).
2. **Aircraft Crash Ramming:**
   * Falling aircraft that collide with the Queen deal a hard-clamped maximum of **$1\text{ damage}$**.
3. **Commander Self-Destruct:**
   * A Commander exploding next to the Queen deals fixed structural explosion damage rather than percentage vaporization.
4. **Permanent Radar Blip & Omniscience:**
   * `SetUnitAlwaysVisible(queen, true)` is enabled; the Queen cannot be hidden by terrain stealth or cloaking jammers.
