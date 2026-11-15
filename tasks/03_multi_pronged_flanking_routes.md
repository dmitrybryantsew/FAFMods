# Task 03: Multi-Pronged Flanking Routes & Approach Corridors

## 1. Goal
Replace the predictable single-file march of raptor waves with Blockade-style multi-pronged attack vectors. Swarm platoons must fan out across divergent approach corridors (Left Flank, Center Assault, Right Flank), bypassing central chokepoints and forcing players to defend a multi-directional frontline.

---

## 2. What We Have Now (Current Code & Root Cause)

### The Issue in `lua/RaptorPlatoonAI.lua` & `lua/RaptorSpawner.lua`:
Currently, in `SpawnWave`:
```lua
local targetPos = Targeting.GetWeightedRandomEnemyTarget(RaptorArmy)
-- Every hive issues an AggressiveMove directly toward that single point:
platoon:AggressiveMoveToLocation(targetPos)
```
- Every spawned platoon traces the exact same Euclidean shortest-path vector from the hive to the target.
- On maps with central chokepoints, bridges, or passes, 100% of the raptors cram into the exact same narrow corridor.
- A player who places 2–3 Point Defenses and walls in the center chokepoint effortlessly neutralizes all waves, while player flank expansions remain completely untouched.

---

## 3. What Is Required

1. **Procedural Multi-Vector Corridors:**
   - Instead of heading directly from $\vec{P}_{\text{start}}$ to $\vec{P}_{\text{target}}$, calculate intermediate flanking waypoints perpendicular to the direct assault vector:
     $$\vec{V}_{\text{direct}} = \vec{P}_{\text{target}} - \vec{P}_{\text{start}}$$
     $$\vec{V}_{\text{perp}} = \begin{pmatrix} -V_z \\ 0 \\ V_x \end{pmatrix}$$
   - Generate three tactical approach corridors:
     - **Corridor 1 (Direct Assault):** $\vec{P}_{\text{start}} \rightarrow \vec{P}_{\text{target}}$
     - **Corridor 2 (Left Flank):** $\vec{P}_{\text{start}} \rightarrow (\vec{P}_{\text{mid}} + \vec{V}_{\text{perp}} \times \text{offset}) \rightarrow \vec{P}_{\text{target}}$
     - **Corridor 3 (Right Flank):** $\vec{P}_{\text{start}} \rightarrow (\vec{P}_{\text{mid}} - \vec{V}_{\text{perp}} \times \text{offset}) \rightarrow \vec{P}_{\text{target}}$
2. **Platoon Distribution Across Vectors:**
   - In `SpawnWave`, assign each wave or platoon to one of the three corridors randomly (e.g. 50% Center, 25% Left Flank, 25% Right Flank).
3. **Continuous Route Execution (`PlatoonPatrolRoute` or Sequential Aggressive Moves):**
   - Issue waypoints sequentially using `ScenarioFramework.PlatoonMoveRoute` or queue `platoon:AggressiveMoveToLocation` without clearing commands, ensuring smooth corner rounding without stopping.

---

## 4. Where to Find What

- **Target Platoon Controller:** [`lua/RaptorPlatoonAI.lua`](file:///e:/Games/FAFMods/lua/RaptorPlatoonAI.lua)
- **Wave Dispatcher:** [`lua/RaptorSpawner.lua`](file:///e:/Games/FAFMods/lua/RaptorSpawner.lua)
- **Blockade Attack Route Patterns:** [`FAF_Coop_Operation_Blockade_CustomFunctions.lua`](file:///C:/Users/User/Documents/My%20Games/Gas%20Powered%20Games/Supreme%20Commander%20Forged%20Alliance/maps/FAF_Coop_Operation_Blockade.v0004/FAF_Coop_Operation_Blockade_CustomFunctions.lua)
  - `MoveChainPickerThread` (Lines 25–38)
  - `BrainChooseHighestAttackRoute` (Lines 987–1006)
- **FAF Scenario Framework Reference:** `/lua/ScenarioFramework.lua`
  - `PlatoonPatrolRoute(platoon, route)`
  - `PlatoonMoveRoute(platoon, route)`

---

## 5. Step-by-Step Implementation Workflow

1. **Implement Flank Route Generator in `lua/RaptorPlatoonAI.lua`:**
   ```lua
   function GenerateFlankingRoute(startPos, targetPos, flankMode)
       local route = {}
       local dx = targetPos[1] - startPos[1]
       local dz = targetPos[3] - startPos[3]
       local dist = math.sqrt(dx * dx + dz * dz)
       
       if dist < 60.0 or flankMode == 'center' then
           table.insert(route, targetPos)
           return route
       end

       -- Normalize direct vector
       local nx = dx / dist
       local nz = dz / dist

       -- Perpendicular normal vector
       local px = -nz
       local pz = nx

       local sideMult = (flankMode == 'left') and 1 or -1
       local flankOffset = math.min(120.0, dist * 0.35) * sideMult

       -- Midpoint waypoint offset to the flank
       local mx = startPos[1] + (dx * 0.5) + (px * flankOffset)
       local mz = startPos[3] + (dz * 0.5) + (pz * flankOffset)
       
       -- Clamp within map boundaries
       local mapW = ScenarioInfo.size[1]
       local mapH = ScenarioInfo.size[2]
       mx = math.max(16, math.min(mapW - 16, mx))
       mz = math.max(16, math.min(mapH - 16, mz))
       local my = GetSurfaceHeight(mx, mz)

       table.insert(route, Vector(mx, my, mz))
       table.insert(route, targetPos)
       return route
   end
   ```
2. **Execute Multi-Waypoint Route in `PlatoonCohesionThread`:**
   - In `ManageRaptorSquad(platoon, targetPos, flankMode)`:
     - Generate route with `GenerateFlankingRoute(startPos, targetPos, flankMode)`.
     - Issue sequential moves:
       ```lua
       platoon:Stop()
       for i, wp in route do
           platoon:AggressiveMoveToLocation(wp)
       end
       ```
3. **Dispatch Diverse Flank Modes in `lua/RaptorSpawner.lua`:**
   - When spawning from multiple hives:
     ```lua
     local modes = {'center', 'left', 'right'}
     local chosenMode = modes[math.random(1, 3)]
     PlatoonAI.ManageRaptorSquad(landPlatoon, targetPos, chosenMode)
     ```

---

## 6. Desired End Goal & Verification Criteria

- **No Chokepoint Funneling:** Flanking packs navigate around mountain ranges and central chokepoints, striking player peripheral bases.
- **Pincer Engagements:** Players experience simultaneous assaults from multiple directions, breaking static turtle lines.
- **Smooth Traversal:** Platoons round intermediate flank waypoints fluidly without stopping or getting stuck on map boundaries.
