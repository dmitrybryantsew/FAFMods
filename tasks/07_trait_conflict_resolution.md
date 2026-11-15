# Task 07: Trait Conflict Resolution & Physics-Aware Micro

## 1. Goal
Harmonize individual unit behavioral traits (Skirmish, Coward, Berserk, Blink) with platoon movement commands. Prevent individual unit micro-orders (`IssueStop`/`IssueMove`) from breaking platoon cohesion, triggering rubberband loops, or causing collision stalls.

---

## 2. What We Have Now (Current Code & Root Cause)

### The Issue in `lua/RaptorBaseUnit.lua` & `lua/RaptorPlatoonAI.lua`:
In `RaptorBaseUnit.lua` (`OnDamage` lines 40–50):
```lua
if cats['BERSERK'] and not self.IsBerserk then
    PlatoonAI.TriggerBerserkCharge(self, instigator)
elseif cats['COWARD'] and (self:GetHealth() / self:GetMaxHealth()) < 0.80 then
    PlatoonAI.TriggerCowardFlee(self, instigator)
end
```
And inside `lua/RaptorPlatoonAI.lua`:
```lua
function TriggerCowardFlee(unit, instigator)
    ...
    IssueStop({unit})
    IssueMove({unit}, Vector(fx, fy, fz))
end

function TriggerSkirmishKite(unit, targetPos)
    ...
    IssueStop({unit})
    IssueMove({unit}, Vector(kx, ky, kz))
end
```

### Why This Breaks Platoon Cohesion:
1. **The Order Conflict:**
   - Calling `IssueStop({unit})` and `IssueMove({unit}, ...)` on a single unit overrides its platoon order.
   - The fleeing or kiting unit immediately falls behind the main platoon.
   - 4 seconds later, `PlatoonCohesionThread` notices that this unit is > 32 units away from the pack centroid, and issues a `platoon:Stop()` to the **entire platoon**, pulling all 20 units backward to wait for the fleeing unit!
2. **Missing Physics Awareness (M28 Insight):**
   - In SupCom FA, turning around 180 degrees takes 2.0–3.0 seconds due to unit rotational inertia and turn rate.
   - Kiting units turn their backs, take free fire, and frequently jam into units walking behind them.

---

## 3. What Is Required

1. **Platoon Cohesion Exemption:**
   - When a unit is in a trait state (`unit.IsKiting == true`, `unit.IsFleeing == true`, or `unit.IsBerserk == true`), exclude it from the platoon centroid spread calculation in `PlatoonCohesionThread`.
   - Trait micro must **never** drag the main pack backward.
2. **Transient Action Timers & Platoon Rejoin:**
   - Trait behaviors must have a short, deterministic lifespan (e.g., 3.0 seconds).
   - Once the kite or flee vector is completed, clear the trait flag and re-issue the current platoon assault order so the unit rejoins the attack line.
3. **M28-Style Reverse Movement Check:**
   - Inspect unit `Physics.BackUpDistance`. If `BackUpDistance >= 4.0`, move backward without rotating the torso/turret so weapons keep firing during the retreat.

---

## 4. Where to Find What

- **Trait Handlers:** [`lua/RaptorPlatoonAI.lua`](file:///e:/Games/FAFMods/lua/RaptorPlatoonAI.lua)
  - `TriggerSkirmishKite` (Lines 104–117)
  - `TriggerCowardFlee` (Lines 122–135)
  - `TriggerBerserkCharge` (Lines 140–160)
  - `TriggerSpectreBlink` (Lines 165–185)
- **Damage Hook:** [`lua/RaptorBaseUnit.lua`](file:///e:/Games/FAFMods/lua/RaptorBaseUnit.lua)
  - `OnDamage(self, instigator, amount, vector, damageType)` (Lines 28–53)
- **M28 Projectile & Reverse Reference:** [`M28Micro.lua`](file:///C:/Users/User/Documents/My%20Games/Gas%20Powered%20Games/Supreme%20Commander%20Forged%20Alliance/mods/M28AI/lua/AI/M28Micro.lua)
  - `MoveAwayFromTargetTemporarily` (Lines 31–85)

---

## 5. Step-by-Step Implementation Workflow

1. **Update `TriggerCowardFlee` in `lua/RaptorPlatoonAI.lua`:**
   ```lua
   function TriggerCowardFlee(unit, instigator)
       if not unit or unit.Dead or unit.IsFleeing or not instigator or instigator.Dead then return end
       unit.IsFleeing = true

       local curPos = unit:GetPosition()
       local instPos = instigator:GetPosition()
       local angle = math.atan2(instPos[1] - curPos[1], instPos[3] - curPos[3])

       local fleeDist = 18.0
       local fx = curPos[1] - math.sin(angle) * fleeDist
       local fz = curPos[3] - math.cos(angle) * fleeDist
       local fy = GetSurfaceHeight(fx, fz)

       IssueClearCommands({unit})
       IssueMove({unit}, Vector(fx, fy, fz))

       -- Rejoin Platoon after 3.5 seconds
       unit:ForkThread(function()
           WaitSeconds(3.5)
           if unit and not unit.Dead then
               unit.IsFleeing = false
               -- Re-issue platoon combat order if assigned to a platoon
               local plat = unit:GetPlatoon()
               if plat and plat.CurrentAssaultPos then
                   IssueAggressiveMove({unit}, plat.CurrentAssaultPos)
               end
           end
       end)
   end
   ```
2. **Update `PlatoonCohesionThread` to Exclude Micro-Units:**
   - In `PlatoonCohesionThread`, when calculating spread and centroids:
     ```lua
     for _, u in units do
         if u and not u.Dead and not u:BeenDestroyed() then
             -- Exclude units currently performing individual evasive micro
             if not u.IsFleeing and not u.IsKiting then
                 local p = u:GetPosition()
                 -- calculate bounding box only on main body...
             end
         end
     end
     ```
3. **Add Cooldowns to Prevent Infinite Micro Oscillation:**
   - Prevent units from spamming `TriggerCowardFlee` every tick upon taking rapid continuous machine-gun fire. Add a cooldown timestamp:
     `unit.FleeCooldown = GetGameTimeSeconds() + 5.0`.

---

## 6. Desired End Goal & Verification Criteria

- **No Platoon Cascading Freezes:** A damaged swarmer executing a dodge or flee maneuver does not cause the rest of the platoon to stop or turn around.
- **Fluid Re-Engagement:** Kiting/fleeing units briefly step back to escape high-damage zones, then seamlessly rejoin the assault line once the threat subsides.
- **Zero Command Clashing:** Units smoothly transition between platoon-level march orders and individual reactive micro without stuttering.
