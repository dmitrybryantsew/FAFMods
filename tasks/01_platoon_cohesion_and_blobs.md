# Task 01: Fix Platoon Cohesion & Eliminate Regrouping Blobs

## 1. Goal
Completely eliminate the combat-halting stutter, rubberbanding, and dense single-point clumping ("blobs") of Raptor platoons. Ensure that Raptors advance aggressively in wide combat formations, maintain weapon fire during maneuvers, and never stop dead or turn their backs to the enemy when engaged in battle.

---

## 2. What We Have Now (Current Code & Root Cause)

### The Issues in `lua/RaptorPlatoonAI.lua`:
Inside `PlatoonCohesionThread` (lines 24–95):
1. **The Extrema 32-Unit Trap:**
   ```lua
   local maxSpread = 32.0
   local isDispersed = (xmin < xavg - maxSpread) or (xmax > xavg + maxSpread)
                    or (zmin < zavg - maxSpread) or (zmax > zavg + maxSpread)
   ```
   If a single unit gets hung up on a prop, tree, or hill, or moves slightly slower, `isDispersed` triggers for the *entire platoon*.
2. **Combat Interruption via `platoon:Stop()` & Passive Move:**
   ```lua
   if isDispersed then
       platoon:Stop()
       local centroidY = GetSurfaceHeight(xavg, zavg)
       platoon:MoveToLocation(Vector(xavg, centroidY, zavg), false)
       platoon.IsRegrouping = true
   ```
   - `platoon:Stop()` cancels active weapon target acquisition and clears combat attack orders.
   - `MoveToLocation` is a **passive** move, not an aggressive attack order.
   - Forward units engaged with Point Defenses or ACUs suddenly stop shooting, turn around, and walk backward toward slow stragglers, absorbing 100% free enemy fire without retaliation.
3. **Zero-Radius Centroid Convergence:**
   - Ordering 15–30 units to converge on the single coordinate `Vector(xavg, centroidY, zavg)` causes severe physical collision, unit pushing, and body-blocking in SupCom's pathing engine.
   - The resulting giant ball is effortlessly wiped out by a single Overcharge, bomb, or artillery shell.

---

## 3. What Is Required

1. **Combat Safety Lock:**
   - If *any* unit in the platoon is actively firing, has an active target (`unit:GetTargetEntity() ~= nil`), or took damage in the last 6 seconds, **skip cohesion regrouping entirely**. Combat takes 100% precedence.
2. **Eliminate Platoon-Wide `Stop()` on Vanguard:**
   - The forward assault units must **never be ordered to stop or turn around**.
   - Instead, only units that are lagging behind the front line should receive a boost or catch-up movement command toward the vanguard.
3. **Adopt FAF Native Formations (`AttackFormation` / `GrowthFormation`):**
   - Use `platoon:SetFormation('AttackFormation')` or assign platoons with `'AttackFormation'` upon creation.
   - When moving, use `platoon:AggressiveMoveToLocation` or `ScenarioFramework.PlatoonPatrolRoute` with formation spacing to ensure units spread out laterally.
4. **Staggered Cohesion Sleep Cycles:**
   - Replace fixed `WaitSeconds(4.0)` with randomized/jittered intervals (`WaitSeconds(3.5 + math.random() * 1.5)`) to prevent multiple platoons from executing heavy math in the exact same simulation tick.

---

## 4. Where to Find What

- **Target Code File:** [`lua/RaptorPlatoonAI.lua`](file:///e:/Games/FAFMods/lua/RaptorPlatoonAI.lua)
  - `ManageRaptorSquad(platoon, targetPos)` (Line 20)
  - `PlatoonCohesionThread(platoon, targetPos)` (Lines 24–95)
- **Platoon Creation in Spawner:** [`lua/RaptorSpawner.lua`](file:///e:/Games/FAFMods/lua/RaptorSpawner.lua)
  - `SpawnWave(brain)` (Lines 395–401)
- **Blockade Reference:** [`FAF_Coop_Operation_Blockade_CustomFunctions.lua`](file:///C:/Users/User/Documents/My%20Games/Gas%20Powered%20Games/Supreme%20Commander%20Forged%20Alliance/maps/FAF_Coop_Operation_Blockade.v0004/FAF_Coop_Operation_Blockade_CustomFunctions.lua)
  - Patrol and formation handling: Lines 181–185, 465–467.

---

## 5. Step-by-Step Implementation Workflow

1. **Add Combat Detection Helper to `RaptorPlatoonAI.lua`:**
   - Create `IsPlatoonInCombat(platoon)`:
     ```lua
     function IsPlatoonInCombat(platoon)
         local units = platoon:GetPlatoonUnits()
         local currentTime = GetGameTimeSeconds()
         for _, u in units do
             if u and not u.Dead then
                 -- Check if unit has active target or recent damage timestamp
                 if u:GetTargetEntity() or (u.LastDamagedTime and (currentTime - u.LastDamagedTime) < 6.0) then
                     return true
                 end
             end
         end
         return false
     end
     ```
2. **Hook Damage Timestamp in `RaptorBaseUnit.lua`:**
   - In `OnDamage`, set `self.LastDamagedTime = GetGameTimeSeconds()`.
3. **Refactor `PlatoonCohesionThread`:**
   - Check `IsPlatoonInCombat(platoon)`: If `true`, do NOT issue stop or regroup orders; let units fight.
   - Increase `maxSpread` from `32.0` to `75.0` to accommodate normal FAF map spacing and movement delays.
   - If spread exceeds threshold, do **not** call `platoon:Stop()`. Instead, identify the 20% slowest/trailing units and issue them an `AggressiveMove` toward the lead unit's position.
   - When issuing assault moves, use `platoon:AggressiveMoveToLocation(targetPos)` or assign `'AttackFormation'` so units spread across a combat line rather than stacking into a point.
4. **Jitter the Thread Loop:**
   - Change `WaitSeconds(4.0)` to `WaitSeconds(3.5 + Random() * 1.5)`.

---

## 6. Desired End Goal & Verification Criteria

- **No Combat Freezes:** In-combat raptors never turn their backs to enemy turrets or stop shooting to regroup.
- **No Dense Blobs:** Units advance spread out across an attack line, eliminating mass body-blocking and single-shot AoE wipeouts.
- **Fluid Assault:** Raptors advance steadily toward enemy structures without rubberbanding backward.
