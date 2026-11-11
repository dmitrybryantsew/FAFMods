# Raptor Creep (Scum) & Biomass Egg Mechanics Specification

This document evaluates the porting of Beyond All Reason's **Biological Scum / Creep Engine** (`gfx_raptor_scum_gl4.lua`) into Supreme Commander: Forged Alliance Forever (`/mods/RaptorFaction/lua/RaptorCreep.lua`) and specifies the **Biomass Raptor Egg Reclamation System**.

---

## 1. Port Evaluation: Biological Scum in FAF

### A. What Has Been Successfully Implemented
The FAF port in `/mods/RaptorFaction/lua/RaptorCreep.lua` successfully replicates the core behaviors of BAR's OpenGL 4 Scum shader:

1. **Terrain Decal Projection:**
   * Utilizes `CreateDecal(pos, heading, CreepAlbedo, CreepNormals, 'Albedo', width, height, lod, duration, army)` to project pulsating biological tendrils onto terrain heightmaps.
   * Two-layer blending: Main organic membrane (`raptor_creep_albedo.dds`) overlaid with secondary cellular veins (`raptor_creep_sub_albedo.dds`).
2. **Global Node Registry:**
   * Centralized `ActiveNodes` table tracking every live Hive and Spire.
   * Provides the global interface `IsPositionOnCreep(Vector3)` (the direct equivalent of BAR's `GG.IsPosInRaptorScum`).
3. **Stat Modifiers (Creep Buffs & Debuffs):**
   * **Raptor Ally Buff (`RaptorCreepBuff`):** $+25\%$ Movement Speed, $+20\text{ HP/s}$ biological regeneration while traversing native creep.
   * **Hostile Intruder Debuff (`RaptorCreepDebuff`):** $-20\%$ Movement Speed penalty as enemy mechanical chassis churn through acidic sludge.
4. **Decay on Hive Death:**
   * When a parent Hive or Spire is destroyed, the growth rate flips into a negative multiplier at **$10\times$ speed**, dissolving the decal and shrinking the coverage zone rapidly.

### B. Technical Engine Nuances & FAF Optimizations
While BAR handles creep in a dedicated deferred GPU compute pass, FAF runs simulation logic on the CPU. The following optimizations are enforced:

| Challenge | BAR Solution | FAF Implementation Strategy |
| :--- | :--- | :--- |
| **Steep Cliff Stretch** | GL4 tri-planar parallax shader | Decal normal rejection: Check `GetTerrainSlope(x, z) < 0.65`; if steep cliff, suppress decal projection to prevent ugly vertical stretching. |
| **Collision Query Overhead** | 2D Spatial Hashing Bins (`scumBins`) | For $> 30$ active creep nodes, bucket nodes into an $8 \times 8$ grid (`math.floor(x / 64) * 100 + math.floor(z / 64)`) to keep `IsPositionOnCreep` $O(1)$. |
| **Particle Persistence** | Continuous GPU compute emitters | Spawn biological spore and bubbling acidic vapor emitters (`raptor_creep_spores_01_emit.bp`) attached directly to the base entity rather than floating in space. |

### C. The Creep Turret Rule
> [!IMPORTANT]
> In both BAR and the FAF Raptor mod, **Spire Turrets (`XRA0108`, `XRA0208`, `XRA0304`, etc.) CANNOT be spawned on bare ground**.
> When the AI spawner issues an order to plant a defensive spire, it must query `IsPositionOnCreep(candidatePos)`. If `false`, the spawn command is aborted. Destroying a Hive permanently cleanses that sector of the map from further spire growth.

---

## 2. Biomass Raptor Eggs (Reclaim & Decay)

In Beyond All Reason, raptors do not leave twisted metal wreckage; they drop **biological egg sacs** that decay rapidly. This mechanic is fully ported into FAF.

```
       [Raptor Killed]
              │
              ▼
    [Spawn Biological Egg]
     (Small, Medium, Large)
              │
              ├── Contains 50% Mass & Energy of Unit Cost
              ├── High Reclaim Rate for Engineers
              │
              ▼
    [90-Second Decay Thread]
     (Loses 40 HP every 5s)
              │
              ├── [Reclaimed by Player] ──► Instant Resource Surge for Defenses
              │
              ▼
     [Unclaimed Egg Rot]       ──► Dissolves into Ash (Zero Residue)
```

### A. Egg Size & Value Classification

| Egg Tier | Source Unit Cost | Drop Chance | Mass Reclaim Value | Energy Value | Feature Asset |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **Small Egg** | $\le 1,500$ Mass | $33\%$ | $100\%$ of Unit Mass | Equal to Mass | `/env/props/raptor_egg_s.bp` |
| **Medium Egg**| $1,501 - 7,500$ Mass | $66\%$ | $66\%$ of Unit Mass | Equal to Mass | `/env/props/raptor_egg_m.bp` |
| **Large Egg** | $> 7,500$ Mass | $100\%$ | $33\%$ of Unit Mass | Equal to Mass | `/env/props/raptor_egg_l.bp` |

### B. Lua Egg Spawner & Decay Thread Implementation

Integrated into unit death scripts (`OnKilled`):

```lua
---Spawns a biological egg feature upon raptor death with a 90-second decay timer
---@param unit Unit
function SpawnRaptorEgg(unit)
    local bp = unit:GetBlueprint()
    local massCost = bp.Economy.BuildCostMass or 100
    local size = 's'
    local chance = 0.33
    local reclaimMass = massCost

    if massCost > 7500 then
        size = 'l'
        chance = 1.0
        reclaimMass = massCost * 0.33
    elseif massCost > 1500 then
        size = 'm'
        chance = 0.66
        reclaimMass = massCost * 0.66
    end

    if math.random() > chance then return end

    local pos = unit:GetPosition()
    local eggBp = string.format('/mods/RaptorFaction/env/props/raptor_egg_%s_prop.bp', size)
    local eggProp = CreatePropAtWorldTimes(eggBp, pos[1], pos[2], pos[3])

    if eggProp then
        eggProp:SetMaxReclaimValues(reclaimMass, reclaimMass, 1.0)
        eggProp:SetHealth(eggProp, 1000)

        -- Fork Decay Thread: Dissolves egg in ~90 seconds
        ForkThread(function()
            local hp = 1000
            while hp > 0 and not eggProp:BeenDestroyed() do
                WaitSeconds(5.0)
                hp = hp - 55 -- 55 HP every 5 seconds = ~90 seconds total lifespan
                if hp <= 0 then
                    -- Dissolve particle FX
                    CreateEmitterAtEntity(eggProp, -1, '/mods/RaptorFaction/effects/emitters/raptor_egg_dissolve_01_emit.bp')
                    eggProp:Destroy()
                    break
                else
                    eggProp:SetHealth(eggProp, hp)
                end
            end
        end)
    end
end
```

### C. Strategic Impact on Player Economy
The egg decay timer creates a compelling gameplay loop:
- **Turtling Deficit:** Players who hide behind shields never collect biomass; their economy starves.
- **Aggressive Sweeping:** Players who push forward with fast engineers, combat scouts, or ACUs to harvest fresh egg fields between waves gain massive resource surges, accelerating their tech race against the Queen.
