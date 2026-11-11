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
