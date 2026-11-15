-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/lua/QueenBossAI.lua
-- **  Author   :  Ported from Beyond All Reason to FAF
-- **  Summary  :  Matriarch Queen Titan (XRA0401) boss encounter logic:
-- **              adaptive damage resistance (anti-spam up to 95%),
-- **              5-stage health phase multipliers, stagger posture break,
-- **              and anti-cheese protections.
-- **
-- ****************************************************************************

local Targeting = import('/mods/RaptorFaction/lua/RaptorTargeting.lua')

local QueenAdaptiveTable = {}

---Processes incoming damage on the Queen Titan with adaptive resistance, phases, and stagger
---@param queen Unit
---@param instigator Unit
---@param amount number
---@param damageType string
---@return number modifiedAmount
function ProcessQueenIncomingDamage(queen, instigator, amount, damageType)
    if not queen or queen.Dead or amount <= 0 then return amount end

    local amt = amount

    -- 1. Anti-Cheese Protections
    -- Capping Commander Overcharge (OC) / D-Gun to prevent one-shot cheese
    if damageType == 'Overcharge' or damageType == 'Direct' and amt > 4000 then
        amt = math.min(amt, 4000)
    end
    -- Clamping aircraft crash collision ramming to 1 damage
    if damageType == 'AirCrash' or damageType == 'Crash' then
        amt = 1.0
    end

    local curHp = queen:GetHealth()
    local maxHp = queen:GetMaxHealth()
    local hpPct = (curHp / maxHp) * 100

    -- 2. Health Phase Damage Scaling
    if hpPct > 50 then
        amt = amt * 2.00      -- Vulnerable Phase (Double incoming damage)
        queen.QueenOutboundDmgMult = 0.25
    elseif hpPct > 25 then
        amt = amt * 1.00      -- Standard Phase
        queen.QueenOutboundDmgMult = 0.50
    elseif hpPct > 10 then
        amt = amt * 0.75      -- Hardened Phase
        queen.QueenOutboundDmgMult = 0.75
    elseif hpPct > 5 then
        amt = amt * 0.50      -- Armored Shell
        queen.QueenOutboundDmgMult = 1.00
    else
        amt = amt * 0.25      -- Desperation Shell (75% damage reduction)
        queen.QueenOutboundDmgMult = 2.00 -- Lethal Outbound Enrage!
    end

    -- 3. Dynamic Adaptive Resistance (Anti-Spam)
    if instigator and not instigator.Dead then
        local bp = instigator:GetBlueprint()
        local bpId = bp.BlueprintId or 'Unknown'

        if not QueenAdaptiveTable[bpId] then
            QueenAdaptiveTable[bpId] = { accumulated = 0, notified = false }
        end

        local entry = QueenAdaptiveTable[bpId]
        local resistCap = 0.95
        local resistPercent = math.min(resistCap, entry.accumulated / (maxHp * 0.75))

        if resistPercent >= 0.50 and not entry.notified then
            Sync.RaptorAnnounce = {
                Text = "WARNING: The Queen is biologically adapting to " .. bpId .. "! Diversify weapons!",
                Color = 'red'
            }
            entry.notified = true
        end

        -- If Queen is currently Staggered, all adaptive resistances are halved!
        if queen.IsStaggered then
            resistPercent = resistPercent * 0.50
        end

        amt = amt * (1.0 - resistPercent)
        entry.accumulated = entry.accumulated + (amount * 3.5)
    end

    -- 4. Stagger Posture Meter
    queen.StaggerCurrentHealth = (queen.StaggerCurrentHealth or math.ceil(maxHp * 0.33)) - amt
    if queen.StaggerCurrentHealth <= 0 and not queen.IsStaggered then
        TriggerQueenStagger(queen)
    end

    -- If already staggered, heavy burst damage slowly reduces the stun duration
    if queen.IsStaggered and queen.StaggerDurationRemaining then
        queen.StaggerDurationRemaining = queen.StaggerDurationRemaining - (amt * 0.0002)
    end

    return amt
end

---Triggers Posture Stagger / Vulnerability Stun on the Queen Titan
---@param queen Unit
function TriggerQueenStagger(queen)
    queen.IsStaggered = true
    queen.StaggerDurationRemaining = 32.0 -- 32-second stun window
    IssueStop({queen})

    local army = queen:GetArmy()
    Sync.RaptorAnnounce = {
        Text = "THE QUEEN HAS BEEN STAGGERED! ATTACK NOW WITH ALL WEAPONS!",
        Color = 'yellow'
    }

    queen:ForkThread(function()
        while queen and not queen.Dead and queen.StaggerDurationRemaining > 0 do
            WaitSeconds(1.0)
            queen.StaggerDurationRemaining = queen.StaggerDurationRemaining - 1.0
            -- Atmospheric bio-electric lightning around staggered Queen
            local p = queen:GetPosition()
            CreateEmitterAtEntity(queen, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp'):ScaleEmitter(2.0)
        end

        if queen and not queen.Dead then
            queen.IsStaggered = false
            local maxHp = queen:GetMaxHealth()
            queen.StaggerCurrentHealth = math.ceil(maxHp * 0.33) -- Reset posture bar
            Sync.RaptorAnnounce = {
                Text = "The Queen has recovered from her stagger!",
                Color = 'red'
            }
        end
    end)
end

---Queen Minion Gestation Thread: Continuously births Broodlings and Weaver Healers
---@param queen Unit
function StartQueenGestationThread(queen)
    queen:ForkThread(function()
        local brain = queen:GetAIBrain()
        local army = queen:GetArmy()
        while queen and not queen.Dead do
            WaitSeconds(18.0)
            -- Minions only spawn when the Queen is NOT staggered
            if not queen.IsStaggered and not queen.Dead then
                local pos = queen:GetPosition()
                -- Spawn 4 living Raptor Larvae/Swarmers and 1 Weaver Healer
                for i = 1, 4 do
                    local ox = (math.random() - 0.5) * 8
                    local oz = (math.random() - 0.5) * 8
                    local unit = brain:CreateUnitNearSpot('XRA0100', pos[1] + ox, pos[3] + oz)
                    if unit then
                        CreateEmitterAtEntity(unit, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp')
                    end
                end
                -- Spawn Weaver Healer
                local hx = (math.random() - 0.5) * 6
                local hz = (math.random() - 0.5) * 6
                local healer = brain:CreateUnitNearSpot('XRA0109', pos[1] + hx, pos[3] + hz)
                if healer then
                    CreateEmitterAtEntity(healer, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp')
                end
            end
        end
    end)
end

---Fires apocalyptic meteor bombardment targeting highest threat cluster (player base core)
---@param queen Unit
function FireQueenMeteorStrike(queen)
    if not queen or queen.Dead or queen.IsStaggered then return end
    local aiBrain = queen:GetAIBrain()
    local targetPos = Targeting.GetWeightedEnemyTarget(queen:GetArmy(), queen:GetPosition())

    if targetPos then
        Sync.RaptorAnnounce = {
            Text = "DANGER: QUEEN TITAN METEOR BOMBARDMENT DETECTED!",
            Color = 'red'
        }

        local weapon = queen:GetWeaponByLabel('RoarCannon') or queen:GetWeapon(1)
        if weapon and weapon.SetTargetGround then
            weapon:SetTargetGround(targetPos)
        end
    end
end

---Starts continuous Queen Titan meteor bombardment thread
---@param queen Unit
function StartQueenBombardmentThread(queen)
    queen:ForkThread(function()
        -- Initial grace period after hatching
        WaitSeconds(40.0)
        while queen and not queen.Dead do
            if not queen.IsStaggered then
                FireQueenMeteorStrike(queen)
            end
            WaitSeconds(50.0 + math.random() * 20.0)
        end
    end)
end

---Starts continuous Kinetic Stomp Shockwave thread on the Land Matriarch Queen Titan
---Flings T1-T3 units into the air and applies safe Kinetic Stagger (pitch tilt + stun) to Experimentals and ACUs
---@param queen Unit
function StartQueenKineticStompThread(queen)
    queen:ForkThread(function()
        local brain = queen:GetAIBrain()
        local army = queen:GetArmy()

        -- Initial grace delay after hatching
        WaitSeconds(15.0)

        while queen and not queen.Dead do
            WaitSeconds(16.0 + math.random() * 8.0)

            -- Stomp only occurs if queen is active and not staggered
            if queen and not queen.Dead and not queen.IsStaggered then
                local qPos = queen:GetPosition()

                -- Scan 22 radius around Queen for enemy units
                local enemies = brain:GetUnitsAroundPoint(categories.SELECTABLE - categories.STRUCTURE, qPos, 22.0, 'Enemy')

                if enemies and table.getn(enemies) > 0 then
                    -- 1. Stomp Roar Animation & Camera Earthquake
                    local roarAnim = CreateAnimator(queen)
                    roarAnim:PlayAnim('/mods/RaptorFaction/units/XRA0401/XRA0401_Aroar.sca', false)
                    roarAnim:SetRate(1.5)

                    queen:ShakeCamera(45, 3.0, 0, 1.5)

                    -- 2. Massive Shockwave & Blood Smoke FX
                    CreateEmitterAtEntity(queen, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp'):ScaleEmitter(4.5)
                    CreateEmitterAtEntity(queen, army, '/mods/RaptorFaction/effects/emitters/raptor_bio_smoke_01_emit.bp'):ScaleEmitter(5.5)

                    -- 3. Kinetic Stagger & Toss Mechanics
                    for _, target in enemies do
                        if target and not target.Dead and not target:BeenDestroyed() then
                            local tPos = target:GetPosition()
                            local dX = tPos[1] - qPos[1]
                            local dZ = tPos[3] - qPos[3]
                            local dist = math.sqrt(dX * dX + dZ * dZ)
                            if dist < 0.1 then dist = 1.0 end
                            local normX = dX / dist
                            local normZ = dZ / dist

                            local bp = target:GetBlueprint()
                            local cats = bp.CategoriesHash or {}

                            -- A. T4 EXPERIMENTALS & ACUS (Galactic Colossus, Fatboy, Megalith, ACU)
                            -- Safe Kinetic Stagger: Screen rumble + bone pitch tilt + C++ engine stun (ZERO desyncs!)
                            if cats['EXPERIMENTAL'] or cats['COMMAND'] then
                                Damage(queen, qPos, target, 2200, 'Normal')
                                target:SetStunned(2.5)

                                -- Slams the Colossus backward 18 degrees on its heels!
                                local staggerRot = CreateRotator(target, 0, 'x', -18, 45, 90)
                                target:ForkThread(function()
                                    WaitSeconds(1.0)
                                    if target and not target.Dead and not target:BeenDestroyed() then
                                        staggerRot:SetGoal(0)
                                        WaitSeconds(1.0)
                                        staggerRot:Destroy()
                                    end
                                end)
                            -- B. T1, T2, T3 UNITS (Tanks, Bots, Walkers)
                            -- Violent Radial Fling / Toss through the air
                            else
                                Damage(queen, qPos, target, 950, 'TreeForce')
                                target:SetStunned(2.0)

                                local flingDist = 16.0
                                local fx = normX * flingDist
                                local fz = normZ * flingDist
                                local slider = CreateSlider(target, 0, fx, 3.5, fz, 30, true)
                                target:ForkThread(function()
                                    WaitSeconds(0.6)
                                    if target and not target.Dead and not target:BeenDestroyed() then
                                        slider:SetGoal(0, 0, 0)
                                        slider:SetSpeed(15)
                                        WaitSeconds(0.6)
                                        slider:Destroy()
                                    end
                                end)
                            end
                        end
                    end
                end
            end
        end
    end)
end

---Transitions from Phase 1 (Apex Sky Queen XRA0402) to Phase 2 (Land Matriarch Queen Titan XRA0401)
---Detonates apocalyptic crash bio-nuke and summons the Land Titan out of the crater
---@param skyQueen Unit
function TransitionToLandQueen(skyQueen)
    if not skyQueen then return end

    local brain = skyQueen:GetAIBrain()
    local army = skyQueen.Army
    local pos = skyQueen:GetPosition()
    local cx = pos[1]
    local cz = pos[3]
    local cy = GetSurfaceHeight(cx, cz)
    local crashPos = Vector(cx, cy, cz)

    -- Apocalyptic screen earthquake
    skyQueen:ShakeCamera(55, 4.5, 0, 3.0)

    Sync.RaptorAnnounce = {
        Text = "CRITICAL ALERT: THE SKY QUEEN HAS CRASHED! APOCALYPTIC BIO-NUKE IMPACT!",
        Color = 'red'
    }

    -- 1. Cataclysmic Crater Detonation (12,000 Damage + TreeForce)
    DamageArea(skyQueen, crashPos, 26, 12000, 'TreeForce', true, false)
    DamageArea(skyQueen, crashPos, 30, 4500, 'TreeFire', true, false)

    -- 2. Massive Death Emitters at Crash Site
    CreateEmitterAtBone(skyQueen, -1, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp'):ScaleEmitter(8.0)
    CreateEmitterAtBone(skyQueen, -1, army, '/mods/RaptorFaction/effects/emitters/raptor_bio_smoke_01_emit.bp'):ScaleEmitter(10.0)

    -- 3. Sprout permanent Creep node at crash site
    local Creep = import('/mods/RaptorFaction/lua/RaptorCreep.lua')
    if Creep and Creep.StartCreepNode then
        local tube = brain:CreateUnitNearSpot('XRA0121', cx, cz)
        if tube then
            Creep.StartCreepNode(tube, 60.0, 1.0)
        end
    end

    -- 4. Awaken Phase 2: Land Matriarch Queen Titan (XRA0401)
    local landQueen = brain:CreateUnitNearSpot('XRA0401', cx, cz)
    if landQueen then
        local Spawner = import('/mods/RaptorFaction/lua/RaptorSpawner.lua')
        local Stats = import('/mods/RaptorFaction/lua/RaptorStats.lua')

        if Spawner and Stats then
            local tAnger = (Spawner.GetTechAnger and Spawner.GetTechAnger()) or 50
            local qAnger = (Spawner.GetQueenAnger and Spawner.GetQueenAnger()) or 100
            local diff = (Spawner.GetCurrentDifficulty and Spawner.GetCurrentDifficulty()) or 'normal'
            Stats.RecomputeRaptorStats(landQueen, tAnger, qAnger, diff)
            if Spawner.SetActiveQueen then
                Spawner.SetActiveQueen(landQueen)
            end
        end

        Sync.RaptorAnnounce = {
            Text = "BEHOLD: THE LAND MATRIARCH QUEEN TITAN RISES FROM THE BIO-CRATER!",
            Color = 'red'
        }

        -- Start Phase 2 Boss Threads
        StartQueenGestationThread(landQueen)
        StartQueenBombardmentThread(landQueen)
        StartQueenKineticStompThread(landQueen)

        -- Order Land Queen directly into combat
        local target = Targeting.GetWeightedEnemyTarget(army, crashPos)
        IssueAggressiveMove({landQueen}, target)
    end
end

