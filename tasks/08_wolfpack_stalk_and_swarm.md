# Task 08: Wolfpack Raider AI (Stalk, Standoff & 360-Degree Overwhelm)

## 1. Goal
Unleash the full natural speed of raider raptors and eliminate rigid column/parade formations. Fast raiders move in `NoFormation` at 100% native physics speed, calculate enemy weapon range in the target sector, hold a safe orbital standoff distance (weapon range + 16 units) to prevent kiting, accumulate critical mass, and execute a simultaneous 360-degree pincer overwhelm charge.

---

## 2. What We Had (Root Cause of Robotic Marching)

### Formation Speed Throttling:
- When all land units were bundled into a single `AttackFormation` platoon:
  - The SupCom engine snapped units into a rigid 2D grid matrix.
  - Fast raiders (speed 4.8–5.5) were hard-throttled to crawl at the speed of the slowest unit (e.g. Healers/Artillery at 2.5).
  - Units marched in straight geometric lines looking like clockwork toy soldiers rather than an organic predatory swarm.

### Suicidal Frontal Feeding:
- Raiders approached in a single line directly into enemy Point Defense fire, dying one by one before slower siege support could arrive.

---

## 3. What Was Implemented

### 1. Role-Dedicated Land Platoon Partitioning
In `lua/RaptorSpawner.lua` (`SpawnWave`):
- Land units are partitioned into two distinct squads:
  1. **Fast Raider Wolfpack (`XRA0100`, `XRA0101`, `XRA0103`, `XRA0201`, `XRA0203`, `XRA0206`):**
     - Assigned in `'NoFormation'` $\rightarrow$ **100% unthrottled sprint!**
     - Controlled by `PlatoonAI.ManageRaptorWolfpack`.
  2. **Heavy Siege / Support Squad (`XRA0202`, `XRA0301`, `XRA0303`, `XRA0109`, `XRA0225`, `XRA0328`):**
     - Assigned in `'AttackFormation'` to maintain combat coverage and protective shield bubbles.
     - Controlled by `PlatoonAI.ManageRaptorSquad`.

### 2. Weapon Range + Respectable Distance Standoff
In `lua/RaptorPlatoonAI.lua`:
```lua
function GetStandoffDistance(brain, targetPos)
    local maxRange = GetTargetAreaMaxWeaponRange(brain, targetPos, 50.0)
    if maxRange <= 0 then
        return 0 -- Soft target (mex/radar/engie): No standoff, pounce immediately!
    end

    -- Weapon range + respectable distance buffer:
    local respectableBuffer = 16.0
    return math.max(42.0, maxRange + respectableBuffer)
end
```
- Scans direct fire/defenses in the target zone (e.g. T1 PD range 30 $\rightarrow$ standoff 46; T2 Cerberus range 30 $\rightarrow$ standoff 46; Gun ACU range 32 $\rightarrow$ standoff 48).
- **Prevents Enemy Kiting:** Because the buffer is +16 units outside weapon range, enemy mobile units and commanders cannot step forward to kite or aggro the raptors before the swarm is ready to attack.

### 3. Dynamic Dangerousness & Power Assessment
- **Target Dangerousness ($D_{\text{target}}$):**
  - Point Defenses: $(\text{HP} \times 0.08) + 40$
  - ACU: $(\text{HP} \times 0.05) + 90$
  - Mobile Combat: $(\text{HP} \times 0.04) + 15$
  - Economy/Civilians: Negligible ($+2$)
- **Local Swarm Power ($S_{\text{swarm}}$):**
  - Evaluates all allied raptors within a 65-unit bubble around the target.

### 4. The 3-State Wolfpack Engine (`WolfpackProwlThread`)
1. **`SPRINT`:** Fast raiders sprint at full velocity along multi-pronged flanking corridors.
2. **`PROWL` (If $S_{\text{swarm}} < 1.2 \times D_{\text{target}}$):**
   - Raptors orbit the target along the safe standoff radius circle.
   - Prowl/orbit waypoints jitter slightly for organic pack movement.
   - Snipes any stray engineers or builders attempting to repair or expand.
   - Waits for critical mass or slower siege artillery/bruisers to close in.
3. **`OVERWHELM` (If $S_{\text{swarm}} \ge 1.2 \times D_{\text{target}}$ or target is soft):**
   - The entire orbital ring dives simultaneously straight through `targetPos`!
   - Creates a devastating 360-degree pincer overwhelm from all directions at once.
4. **Smart Predator Bailout (Timeout 22s):**
   - If after 22 seconds the target is still heavily fortified and no reinforcements arrive, the pack breaks off, retargets to an unfortified mass extractor or expansion, and sprints away.

---

## 4. Modified Files

- [`lua/RaptorPlatoonAI.lua`](file:///e:/Games/FAFMods/lua/RaptorPlatoonAI.lua)
- [`lua/RaptorSpawner.lua`](file:///e:/Games/FAFMods/lua/RaptorSpawner.lua)
- Live copy synced to: `C:/Users/User/Documents/My Games/Gas Powered Games/Supreme Commander Forged Alliance/mods/RaptorFaction/lua/`
