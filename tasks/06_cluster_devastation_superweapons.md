# Task 06: Cluster Devastation & Superweapon Targeting

## 1. Goal
Direct the Matriarch Queen Titan's cataclysmic meteor bombardment and the Strategic Bio-Nuke Silo (`XRA0304`) strikes into high-density player base infrastructure clusters using FAF's Influence Map cluster locator, rather than firing blindly at isolated units.

---

## 2. What We Have Now (Current Code & Root Cause)

### The Issue in `lua/QueenBossAI.lua` & `lua/RaptorSpawner.lua`:
In `QueenBossAI.lua` and `SpawnQueenTitan`:
- The Queen Titan (`XRA0401`) and Strategic Bio-Nuke Silos (`XRA0304`) use basic target points or random enemy units picked via `GetWeightedRandomEnemyTarget`.
- If an isolated engineer or scout is selected, high-value orbital bombardments and strategic nuclear payloads detonate in empty fields.
- The player rarely suffers existential base damage from boss abilities because weapon impacts fail to hit core power generator complexes or factory hubs.

---

## 3. What Is Required

Adopt Blockade's nuclear and high-threat cluster targeting pattern:
1. **Influence Map Cluster Analysis:**
   In Blockade's `NukeAI`:
   ```lua
   local AIBehaviors = import('/lua/ai/aibehaviors.lua')
   nukePos = AIBehaviors.GetHighestThreatClusterLocation(aiBrain, unit)
   ```
   - `GetHighestThreatClusterLocation` scans the engine's 2D grid and returns the exact centroid of the densest cluster of enemy structures and high-threat assets (typically the player's primary factory grid and T3 power farms).
2. **Queen Meteor Bombardment Targeting:**
   - When the Queen Titan charges her special Meteor Strike or Bio-Shockwave, resolve the target via `AIBehaviors.GetHighestThreatClusterLocation(aiBrain, queen)` so the strike lands directly in the player's economic heartland.
3. **Strategic Bio-Nuke Silo Automation:**
   - Assign constructed Bio-Nuke Silos (`XRA0304`) to a dedicated platoon running `NukeAI` with cluster detection.

---

## 4. Where to Find What

- **Queen Boss Script:** [`lua/QueenBossAI.lua`](file:///e:/Games/FAFMods/lua/QueenBossAI.lua)
- **Spawner & Silo Logic:** [`lua/RaptorSpawner.lua`](file:///e:/Games/FAFMods/lua/RaptorSpawner.lua)
- **Blockade Nuke Script Reference:** [`FAF_Coop_Operation_Blockade_CustomFunctions.lua`](file:///C:/Users/User/Documents/My%20Games/Gas%20Powered%20Games/Supreme%20Commander%20Forged%20Alliance/maps/FAF_Coop_Operation_Blockade.v0004/FAF_Coop_Operation_Blockade_CustomFunctions.lua)
  - `NukePlatoon` & `NukeAI` (Lines 1035–1079)
- **FAF AI Engine Behaviors:** `/lua/ai/aibehaviors.lua`
  - `GetHighestThreatClusterLocation(aiBrain, unit)`

---

## 5. Step-by-Step Implementation Workflow

1. **Import `AIBehaviors` into `lua/QueenBossAI.lua`:**
   ```lua
   local AIBehaviors = import('/lua/ai/aibehaviors.lua')
   ```
2. **Update Queen Bombardment Function:**
   - In the Queen Titan's special weapon firing coroutine:
     ```lua
     function FireQueenMeteorStrike(queen)
         local aiBrain = queen:GetAIBrain()
         local targetPos = AIBehaviors.GetHighestThreatClusterLocation(aiBrain, queen)
         
         if not targetPos then
             local Targeting = import('/mods/RaptorFaction/lua/RaptorTargeting.lua')
             targetPos = Targeting.GetFallbackEnemyTarget(queen:GetArmy())
         end

         if targetPos then
             -- Announce apocalyptic incoming strike to player UI
             Sync.RaptorAnnounce = {
                 Text = "DANGER: QUEEN TITAN METEOR BOMBARDMENT DETECTED!",
                 Color = 'red'
             }
             -- Issue special weapon or ability strike at targetPos
             queen:GetWeaponByLabel('MeteorWeapon'):SetTargetGround(targetPos)
         end
     end
     ```
3. **Automate Bio-Nuke Silo Spire AI in `lua/RaptorSpawner.lua`:**
   - When a T3 Bio-Nuke Silo (`XRA0304`) is spawned on Creep territory, fork a dedicated launch monitor:
     ```lua
     function StartBioNukeThread(siloUnit, brain)
         siloUnit:ForkThread(function()
             local AIBehaviors = import('/lua/ai/aibehaviors.lua')
             while siloUnit and not siloUnit.Dead do
                 -- Wait until missile is loaded
                 while siloUnit:GetNukeSiloAmmoCount() < 1 do
                     WaitSeconds(15)
                     if not siloUnit or siloUnit.Dead then return end
                 end

                 local targetPos = AIBehaviors.GetHighestThreatClusterLocation(brain, siloUnit)
                 if targetPos then
                     IssueNuke({siloUnit}, targetPos)
                     WaitSeconds(20)
                     IssueClearCommands({siloUnit})
                 end
                 WaitSeconds(30)
             end
         end)
     end
     ```

---

## 6. Desired End Goal & Verification Criteria

- **Devastating Late-Game Pressure:** Strategic missiles and Queen Titan bombardments hit the highest-value structural concentrations (e.g. factory rows, T3 power generators, Shield arrays).
- **Zero Wasted Ammo:** Weapons no longer detonate harmlessly in remote corners or empty fields.
- **Cinematic Tension:** Players must construct and defend Strategic Missile Defenses (SMD) to survive late-game anger levels.
