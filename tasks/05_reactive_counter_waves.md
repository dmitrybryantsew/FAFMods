# Task 05: Reactive Counter-Waves (Anti-Turtle & Anti-Air Triggers)

## 1. Goal
Implement Blockade-style dynamic composition triggers in the Raptor wave generator. When human players mass-produce specific tech classes (e.g. static Point Defense turtles, massive Gunship clouds, or T4 Experimentals), the Hive must automatically adapt its spawn composition to field hard counters.

---

## 2. What We Have Now (Current Code & Root Cause)

### The Issue in `lua/RaptorSpawner.lua`:
In `SpawnWave(brain)` (lines 363–379):
```lua
local pool = UnitRoster.T1_Basic
if TechAnger > 60 then
    pool = { 'XRA0301', 'XRA0302', 'XRA0303', 'XRA0310', ... }
elseif TechAnger > 25 then
    pool = { 'XRA0201', 'XRA0202', 'XRA0203', 'XRA0204', ... }
end
```
- Spawn rosters are purely hardcoded functions of elapsed time and Tech Anger.
- If a player builds 40 Point Defenses and 10 Shields to turtle, the Hive continues to send T1 melee swarmers to die uselessly on the perimeter.
- If a player builds 50 heavy Gunships to bypass ground defenses, the Hive does not increase Spore Anti-Air flyers, allowing the player to steamroll the game.

---

## 3. What Is Required

Adopt Blockade's player-state inspection pattern (`FAF_Coop_Operation_Blockade_script.lua` lines 550–640):
1. **Anti-Turtle Trigger (Heavy Static Defense & Shields):**
   - Query: `numPD = ScenarioFramework.GetNumOfHumanUnits(categories.STRUCTURE * categories.DEFENSE - categories.TECH1)`
   - Response: Weight spawn pool heavily toward **Long-Range Mobile Bio-Artillery (`XRA0202`)**, **Acid Carpet Bombers (`XRA0104`)**, and **Bio-EMP Shield Breakers (`XRA0203`)**.
2. **Anti-Air Dominance Trigger (Player Air Superiority):**
   - Query: `numAir = ScenarioFramework.GetNumOfHumanUnits(categories.AIR * categories.MOBILE)`
   - Response: Spawn dedicated wings of **Spore Anti-Air Fighters (`XRA0115`)** and awaken **Anti-Air Defense Spires (`XRA0106`)** on Creep territory.
3. **Anti-Experimental Hunter Trigger (Player Experimentals):**
   - Query: `numExp = ScenarioFramework.GetNumOfHumanUnits(categories.EXPERIMENTAL)`
   - Response: Spawn **Armored Apex Behemoths (`XRA0301`)** and **Raptor Matriarchs (`XRA0303`)** armed with armor-piercing melee weapons.

---

## 4. Where to Find What

- **Wave Spawner Engine:** [`lua/RaptorSpawner.lua`](file:///e:/Games/FAFMods/lua/RaptorSpawner.lua)
  - `SpawnWave(brain)` (Lines 358–403)
  - `UnitRoster` (Lines 62–87)
- **Blockade Reference:** [`FAF_Coop_Operation_Blockade_script.lua`](file:///C:/Users/User/Documents/My%20Games/Gas%20Powered%20Games/Supreme%20Commander%20Forged%20Alliance/maps/FAF_Coop_Operation_Blockade.v0004/FAF_Coop_Operation_Blockade_script.lua)
  - `P2Intattacks()` (Lines 541–640)
- **FAF ScenarioFramework Functions:** `/lua/ScenarioFramework.lua`
  - `GetNumOfHumanUnits(categories)`

---

## 5. Step-by-Step Implementation Workflow

1. **Add Player Intelligence Scanner in `lua/RaptorSpawner.lua`:**
   ```lua
   local ScenarioFramework = import('/lua/ScenarioFramework.lua')

   function EvaluatePlayerThreatProfile()
       local profile = {
           AirThreat = false,
           TurtleThreat = false,
           ExpThreat = false,
       }

       if ScenarioFramework.GetNumOfHumanUnits then
           local airCount = ScenarioFramework.GetNumOfHumanUnits(categories.AIR * categories.MOBILE)
           local defenseCount = ScenarioFramework.GetNumOfHumanUnits(categories.STRUCTURE * (categories.DEFENSE + categories.SHIELD) - categories.TECH1)
           local expCount = ScenarioFramework.GetNumOfHumanUnits(categories.EXPERIMENTAL)

           if airCount >= 20 then profile.AirThreat = true end
           if defenseCount >= 15 then profile.TurtleThreat = true end
           if expCount >= 1 then profile.ExpThreat = true end
       end

       return profile
   end
   ```
2. **Inject Dynamic Counter Units into `SpawnWave`:**
   - Before picking unit blueprints, inspect `EvaluatePlayerThreatProfile()`:
     ```lua
     local threatProfile = EvaluatePlayerThreatProfile()

     -- If player is turtling with Point Defense & Shields:
     if threatProfile.TurtleThreat then
         -- Guarantee 30% of the wave is Artillery & EMP shield breakers
         table.insert(pool, 'XRA0202') -- Bio Artillery
         table.insert(pool, 'XRA0203') -- EMP Tick
         table.insert(pool, 'XRA0204') -- Brood Cluster Bomber
     end

     -- If player is massing Gunships or Bombers:
     if threatProfile.AirThreat then
         -- Guarantee Anti-Air flyers spawn
         table.insert(pool, 'XRA0115') -- Spore AA Fighter
         table.insert(pool, 'XRA0115')
     end

     -- If player deploys an Experimental:
     if threatProfile.ExpThreat then
         table.insert(pool, 'XRA0301') -- Heavy Bruiser
         table.insert(pool, 'XRA0303') -- Matriarch Sub-Boss
     end
     ```

---

## 6. Desired End Goal & Verification Criteria

- **Adaptive Combat:** If a player turtles behind heavy shields and Cerberus turrets, long-range Bio-Artillery and EMP shock ticks immediately appear in subsequent waves to break the defensive perimeter.
- **No Cheese Dominance:** Mass gunship rushes are met by biological Spore Interceptors, denying the player effortless victory.
- **Dynamic Difficulty:** The game organically escalates in tactical complexity as the player expands tech tiers.
