# Task 04: Threat-Aware Eco Targeting ("Where It Hurts Most")

## 1. Goal
Upgrade the economic targeting engine so raptors intelligently prioritize vulnerable, high-value assets and exposed expansions over fortified fortresses. Incorporate distance-discounted economic weighting and priority asset hunting adapted from Operation Blockade.

---

## 2. What We Have Now (Current Code & Root Cause)

### The Issue in `lua/RaptorTargeting.lua`:
In `CalculateUnitEcoWeight` & `GetWeightedRandomEnemyTarget`:
```lua
function CalculateUnitEcoWeight(unit, bp)
    if cats['EXPERIMENTAL'] and cats['ECONOMIC'] then return 10000 end
    if cats['STRATEGIC'] and cats['ARTILLERY'] then return 3000 end
    if cats['ENERGYPRODUCTION'] and cats['TECH3'] then return 1500 end
    if cats['MASSEXTRACTION'] and cats['TECH1'] then return 30 end
    return 1
end
```
- **The Blind Global Scent Bug:**
  - Weights are completely agnostic of distance and defensive threat.
  - A single T3 Power Generator in the farthest, most heavily fortified corner of the player's main base has 50x higher weight than an exposed, unfortified mass extractor 50 units away from the hive.
  - Raptors consistently bypass easy, game-winning economic kills to embark on suicidal marathons straight into the teeth of 20 Point Defenses.

---

## 3. What Is Required

1. **Distance-Discounted Target Scoring:**
   - Incorporate distance from the launching Hive / Platoon into the target weight:
     $$\text{EffectiveScore} = \frac{\text{BaseWeight}}{\max(1.0, (\text{Distance} \times 0.02)^{1.2})}$$
   - Nearby mass extractors, hydro plants, and radar towers naturally score high, motivating the swarm to devour the player's perimeter before breaching the core base.
2. **Priority Decapitation Sniping (Blockade Pattern):**
   - Direct integration of Blockade's `PlatoonAttackClosestPriorityUnit`:
     - If game-ending units exist (Paragons, Mavors, Salvation, Mobile T4 Experimentals), nearby heavy assault behemoths (`XRA0301`) and Matriarchs (`XRA0303`) receive direct attack orders to eliminate them.
3. **Threat-Aware Vulnerability Filter:**
   - Use FAF's engine function `aiBrain:GetThreatAtPosition(pos, 1, true, 'AntiSurface')`.
   - If two targets have similar economic value, favor the target with lower defensive threat to inflict maximum economic damage with minimal swarm casualties.

---

## 4. Where to Find What

- **Target Scoring Engine:** [`lua/RaptorTargeting.lua`](file:///e:/Games/FAFMods/lua/RaptorTargeting.lua)
  - `CalculateUnitEcoWeight(unit, bp)` (Lines 18–102)
  - `GetWeightedRandomEnemyTarget(raptorArmy)` (Lines 137–168)
- **Platoon Execution:** [`lua/RaptorPlatoonAI.lua`](file:///e:/Games/FAFMods/lua/RaptorPlatoonAI.lua)
- **Blockade Reference:** [`FAF_Coop_Operation_Blockade_CustomFunctions.lua`](file:///C:/Users/User/Documents/My%20Games/Gas%20Powered%20Games/Supreme%20Commander%20Forged%20Alliance/maps/FAF_Coop_Operation_Blockade.v0004/FAF_Coop_Operation_Blockade_CustomFunctions.lua)
  - `PlatoonAttackClosestPriorityUnit` (Lines 40–65)
  - `BrainChooseLowestThreatLocation` (Lines 929–950)

---

## 5. Step-by-Step Implementation Workflow

1. **Refactor `GetWeightedRandomEnemyTarget` in `lua/RaptorTargeting.lua`:**
   - Accept origin position: `GetWeightedEnemyTarget(raptorArmy, originPos)`:
     ```lua
     function GetWeightedEnemyTarget(raptorArmy, originPos)
         if TotalEcoWeight <= 0 or table.empty(TargetRegistry) then
             return GetFallbackEnemyTarget(raptorArmy)
         end

         local bestTarget = nil
         local highestScore = -1
         local count = 0

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

                     -- Distance attenuation formula
                     local distFactor = math.max(1.0, (dist * 0.015))
                     local score = (data.weight / (distFactor * distFactor)) * (0.8 + math.random() * 0.4)

                     if score > highestScore then
                         highestScore = score
                         bestTarget = uPos
                     end
                 end
             end
         end

         if bestTarget then
             -- Add slight random scatter to prevent exact stack-up
             bestTarget[1] = bestTarget[1] + math.random(-15, 15)
             bestTarget[3] = bestTarget[3] + math.random(-15, 15)
             bestTarget[2] = GetSurfaceHeight(bestTarget[1], bestTarget[3])
             return bestTarget
         end

         return GetFallbackEnemyTarget(raptorArmy)
     end
     ```
2. **Add Priority Hunting Thread in `lua/RaptorPlatoonAI.lua`:**
   - Create `PlatoonHuntPriorityThreat(platoon)` for heavy T3/T4 assault packs:
     ```lua
     function PlatoonHuntPriorityThreat(platoon)
         local aiBrain = platoon:GetBrain()
         local target = platoon:FindClosestUnit('Attack', 'Enemy', true,
             categories.EXPERIMENTAL + categories.STRATEGIC * categories.ARTILLERY + categories.PARAGON
         )
         if target and not target.Dead then
             platoon:Stop()
             platoon:AggressiveMoveToLocation(target:GetPosition())
         end
     end
     ```

---

## 6. Desired End Goal & Verification Criteria

- **Peripheral Starvation:** Early and mid-game raptor waves target and demolish the player's outer mass extractors, energy storage, and radar stations first.
- **Realistic Economic Pressure:** The player feels constant economic attrition ("they attack where it hurts most") rather than watching the AI mindlessly march into heavily fortified static defense walls.
- **Priority Sniping:** If the player starts building a game-ending experimental (e.g. Mavor or Megalith), the AI actively shifts heavy assault platoons to intercept and destroy it.
