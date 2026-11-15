# Task 02: Platoon Domain Separation (Air vs. Land)

## 1. Goal
Segregate spawned ground swarmers and flying raptors into separate, specialized platoons. Flying raptors must execute dynamic aerial combat passes and base strafing without being anchored to crawling ground units, preventing speed-mismatch deadlocks and formation failures.

---

## 2. What We Have Now (Current Code & Root Cause)

### The Issue in `lua/RaptorSpawner.lua`:
In `SpawnWave(brain)` (lines 358–403):
```lua
local pool = UnitRoster.T1_Basic
-- pool contains ground AND air units:
-- 'XRA0100', 'XRA0101', 'XRA0103' (Land)
-- 'XRA0104' (Acid Carpet Bomber), 'XRA0115' (Air Swarm Fighter), 'XRA0111' (Air Scout)

for i = 1, waveSize do
    local unitBp = pool[math.random(1, table.getn(pool))]
    local u = brain:CreateUnitNearSpot(unitBp, pos[1] + math.random(-8, 8), pos[3] + math.random(-8, 8))
    table.insert(spawnedUnits, u)
end

-- Everything is bundled into one single platoon:
local platoon = brain:MakePlatoon('RaptorSwarmWave', '')
brain:AssignUnitsToPlatoon(platoon, spawnedUnits, 'Attack', 'None')
PlatoonAI.ManageRaptorSquad(platoon, targetPos)
```

### Why This Breaks Combat:
1. **Speed & Pathing Discrepancy:**
   - Flying units (`XRA0104`, `XRA0115`) fly in straight lines over cliffs and water at speeds of 12.0–15.0.
   - Ground swarmers (`XRA0100`, `XRA0101`) crawl at speed 3.5, pathing around terrain geometry.
2. **Permanent Cohesion Breakdown:**
   - Within 5 seconds, aircraft are 80+ units ahead of the ground swarm.
   - The bounding-box spread calculation in `PlatoonCohesionThread` triggers `isDispersed = true` immediately.
   - Ground units stop and wait for aircraft; aircraft are ordered to `Stop()` and fly backward to ground units, leaving them vulnerable to player flak while hovering helplessly.

---

## 3. What Is Required

1. **Partitioning at Spawn Time:**
   - When spawning a wave from a Hive, divide units into two distinct arrays: `landUnits` and `airUnits`.
2. **Independent Platoon Creation:**
   - Create a dedicated Land Platoon for ground forces and assign `PlatoonAI.ManageRaptorSquad(landPlatoon, targetPos)`.
   - Create a dedicated Air Platoon for air forces and assign `PlatoonAI.ManageRaptorAirSquad(airPlatoon, targetPos)`.
3. **Dedicated Aerial Swarm AI (`ManageRaptorAirSquad`):**
   - Flyers should not use ground centroid cohesion.
   - Air platoons should execute strafing runs, patrol loops over enemy economic sectors, or hunt enemy air units/bombers using `PlatoonPatrolRoute` or `AggressiveMoveToLocation`.

---

## 4. Where to Find What

- **Spawning Logic:** [`lua/RaptorSpawner.lua`](file:///e:/Games/FAFMods/lua/RaptorSpawner.lua)
  - `SpawnWave(brain)` (Lines 358–403)
  - `UnitRoster` definitions (Lines 62–87)
- **Platoon Controller:** [`lua/RaptorPlatoonAI.lua`](file:///e:/Games/FAFMods/lua/RaptorPlatoonAI.lua)
  - Needs a new function: `ManageRaptorAirSquad(platoon, targetPos)`
- **Blockade Air Platoon Reference:** [`SeraphimaiP1.lua`](file:///C:/Users/User/Documents/My%20Games/Gas%20Powered%20Games/Supreme%20Commander%20Forged%20Alliance/maps/FAF_Coop_Operation_Blockade.v0004/SeraphimaiP1.lua)
  - Air patrol chains: Lines 550–590 (`PlatoonPatrolChain(platoon, 'P2IntAirattack' .. Random(1, 5))`)

---

## 5. Step-by-Step Implementation Workflow

1. **Update `lua/RaptorSpawner.lua` (`SpawnWave`):**
   - Separate spawned units by checking categories:
     ```lua
     local landUnits = {}
     local airUnits = {}
     for _, u in spawnedUnits do
         if EntityCategoryContains(categories.AIR, u) then
             table.insert(airUnits, u)
         else
             table.insert(landUnits, u)
         end
     end
     ```
   - Spawn two distinct platoons:
     ```lua
     if table.getn(landUnits) > 0 then
         local landPlatoon = brain:MakePlatoon('RaptorLandWave', '')
         brain:AssignUnitsToPlatoon(landPlatoon, landUnits, 'Attack', 'AttackFormation')
         PlatoonAI.ManageRaptorSquad(landPlatoon, targetPos)
     end

     if table.getn(airUnits) > 0 then
         local airPlatoon = brain:MakePlatoon('RaptorAirWave', '')
         brain:AssignUnitsToPlatoon(airPlatoon, airUnits, 'Attack', 'GrowthFormation')
         PlatoonAI.ManageRaptorAirSquad(airPlatoon, targetPos)
     end
     ```
2. **Implement `ManageRaptorAirSquad` in `lua/RaptorPlatoonAI.lua`:**
   - Define a non-blocking aerial combat thread:
     ```lua
     function ManageRaptorAirSquad(platoon, targetPos)
         platoon:ForkThread(AirAssaultThread, targetPos)
     end

     function AirAssaultThread(platoon, targetPos)
         while platoon do
             local units = platoon:GetPlatoonUnits()
             if not units or table.empty(units) then break end
             
             -- Generate a wide aerial attack/patrol diamond around targetPos
             local offset = 35.0
             local p1 = Vector(targetPos[1] + offset, targetPos[2], targetPos[3])
             local p2 = Vector(targetPos[1], targetPos[2], targetPos[3] + offset)
             local p3 = Vector(targetPos[1] - offset, targetPos[2], targetPos[3])
             local p4 = Vector(targetPos[1], targetPos[2], targetPos[3] - offset)

             platoon:Patrol(p1)
             platoon:Patrol(p2)
             platoon:Patrol(p3)
             platoon:Patrol(p4)
             
             -- Re-evaluate target every 30-45 seconds
             WaitSeconds(35.0)
             targetPos = Targeting.GetWeightedRandomEnemyTarget(platoon:GetBrain():GetArmyIndex())
         end
     end
     ```

---

## 6. Desired End Goal & Verification Criteria

- **Ground Pack Velocity:** Ground swarms move continuously without stopping to wait for distant flyers.
- **Fluid Aerial Attacks:** Bombers and swarm fighters fly directly to target zones, engaging player air and bombing power/mass clusters in continuous circular patrol runs.
- **Zero Cross-Domain Tug-of-War:** Air units never trigger ground dispersion checks or vice-versa.
