-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/lua/RaptorPlatoonAI.lua
-- **  Author   :  Ported from Beyond All Reason to FAF
-- **  Summary  :  Platoon squad formation, pack centroid cohesion regrouping,
-- **              and individual behavioral traits (Skirmish, Berserk, Coward,
-- **              Spectre Blink, Healer Aura, Kamikaze).
-- **
-- ****************************************************************************

local Targeting = import('/mods/RaptorFaction/lua/RaptorTargeting.lua')

-- ---------------------------------------------------------------------------
-- 1. PLATOON SQUAD CENTROID & REGROUPING ENGINE
-- ---------------------------------------------------------------------------

---Evaluates squad cohesion and issues Pack Regroup or Assault commands
---@param platoon Platoon
---@param targetPos Vector3
function ManageRaptorSquad(platoon, targetPos)
    platoon:ForkThread(PlatoonCohesionThread, targetPos)
end

function PlatoonCohesionThread(platoon, targetPos)
    local planArmy = nil
    while platoon do
        local units = platoon:GetPlatoonUnits()
        if not units or table.empty(units) then break end

        -- Identify army if not set
        if not planArmy then
            for _, u in units do
                if u and not u.Dead then
                    planArmy = u:GetArmy()
                    break
                end
            end
        end

        -- Retarget if targetPos is nil or periodic reassessment
        if not targetPos and planArmy then
            targetPos = Targeting.GetWeightedRandomEnemyTarget(planArmy)
        end

        if targetPos then
            local xmin, xmax = 999999, -999999
            local zmin, zmax = 999999, -999999
            local xsum, zsum = 0, 0
            local count = 0

            for _, u in units do
                if u and not u.Dead and not u:BeenDestroyed() then
                    local p = u:GetPosition()
                    if p[1] < xmin then xmin = p[1] end
                    if p[1] > xmax then xmax = p[1] end
                    if p[3] < zmin then zmin = p[3] end
                    if p[3] > zmax then zmax = p[3] end
                    xsum = xsum + p[1]
                    zsum = zsum + p[3]
                    count = count + 1
                end
            end

            if count == 0 then break end

            local xavg = xsum / count
            local zavg = zsum / count
            local maxSpread = 32.0 -- Equivalent to BAR's 512 elmos in FAF grid coordinates

            local isDispersed = (xmin < xavg - maxSpread) or (xmax > xavg + maxSpread)
                             or (zmin < zavg - maxSpread) or (zmax > zavg + maxSpread)

            if isDispersed then
                -- 1. Regrouping: Platoon members are scattered; order them to pack centroid
                platoon:Stop()
                local centroidY = GetSurfaceHeight(xavg, zavg)
                platoon:MoveToLocation(Vector(xavg, centroidY, zavg), false)
                platoon.IsRegrouping = true
            else
                -- 2. Cohesive Assault: Platoon is dense; order aggressive move toward eco target
                if platoon.IsRegrouping or not platoon.HasAssaultOrder then
                    platoon:Stop()
                    local scatterX = targetPos[1] + math.random(-15, 15)
                    local scatterZ = targetPos[3] + math.random(-15, 15)
                    local scatterY = GetSurfaceHeight(scatterX, scatterZ)
                    platoon:AggressiveMoveToLocation(Vector(scatterX, scatterY, scatterZ))
                    platoon.IsRegrouping = false
                    platoon.HasAssaultOrder = true
                end
            end
        end

        WaitSeconds(4.0)
    end
end

-- ---------------------------------------------------------------------------
-- 2. BEHAVIORAL TRAIT ACTIONS
-- ---------------------------------------------------------------------------

---SKIRMISH: Ranged spikers and bio-artillery backpedal to keep distance
---@param unit Unit
---@param targetPos Vector3
function TriggerSkirmishKite(unit, targetPos)
    if not unit or unit.Dead or not targetPos then return end
    local curPos = unit:GetPosition()
    local angle = math.atan2(targetPos[1] - curPos[1], targetPos[3] - curPos[3])

    -- Move backward along the vector away from target (15 - 22 units)
    local kiteDist = 18.0
    local kx = curPos[1] - math.sin(angle) * kiteDist
    local kz = curPos[3] - math.cos(angle) * kiteDist
    local ky = GetSurfaceHeight(kx, kz)

    IssueStop({unit})
    IssueMove({unit}, Vector(kx, ky, kz))
end

---COWARD / DODGE: Damaged units flee from damage source when HP < 80%
---@param unit Unit
---@param instigator Unit
function TriggerCowardFlee(unit, instigator)
    if not unit or unit.Dead or not instigator or instigator.Dead then return end
    local curPos = unit:GetPosition()
    local instPos = instigator:GetPosition()
    local angle = math.atan2(instPos[1] - curPos[1], instPos[3] - curPos[3])

    local fleeDist = 22.0
    local fx = curPos[1] - math.sin(angle) * fleeDist
    local fz = curPos[3] - math.cos(angle) * fleeDist
    local fy = GetSurfaceHeight(fx, fz)

    IssueStop({unit})
    IssueMove({unit}, Vector(fx, fy, fz))
end

---BERSERK: Assault behemoths enrage upon taking fire, gaining speed and charging
---@param unit Unit
---@param instigator Unit
function TriggerBerserkCharge(unit, instigator)
    if not unit or unit.Dead or not instigator or instigator.Dead then return end
    if unit.IsBerserk then return end

    unit.IsBerserk = true
    local oldSpeed = unit:GetBlueprint().Physics.MaxSpeed or 3.5

    -- Boost speed by +35% for 4.5 seconds
    if unit.SetSpeedMult then unit:SetSpeedMult(1.35) end

    IssueStop({unit})
    IssueAttack({unit}, instigator)

    unit:ForkThread(function()
        WaitSeconds(4.5)
        if unit and not unit.Dead then
            if unit.SetSpeedMult then unit:SetSpeedMult(1.0) end
            unit.IsBerserk = false
        end
    end)
end

---SPECTRE BLINK: Short-range teleportation burst on a 2-second cooldown
---@param unit Unit
---@param targetPos Vector3
function TriggerSpectreBlink(unit, targetPos)
    if not unit or unit.Dead or not targetPos then return end
    if unit.BlinkCooldown and unit.BlinkCooldown > GetGameTimeSeconds() then return end

    unit.BlinkCooldown = GetGameTimeSeconds() + 2.0
    local curPos = unit:GetPosition()
    local angle = math.atan2(targetPos[1] - curPos[1], targetPos[3] - curPos[3])

    -- Lateral offset perpendicular to line of fire
    local side = (math.random() > 0.5) and 1 or -1
    local blinkDist = 16.0
    local bx = curPos[1] + (math.cos(angle) * blinkDist * side)
    local bz = curPos[3] - (math.sin(angle) * blinkDist * side)
    local by = GetSurfaceHeight(bx, bz)

    -- Teleport particles & warp
    local army = unit:GetArmy()
    CreateEmitterAtEntity(unit, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp')
    Warp(unit, Vector(bx, by, bz))
    CreateEmitterAtEntity(unit, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp')
end

---WEAVER HEAL AURA: Continuous biological regeneration targeting injured allies
---@param unit Unit
function StartWeaverHealThread(unit)
    unit:ForkThread(function()
        local brain = unit:GetAIBrain()
        local army = unit:GetArmy()
        while unit and not unit.Dead and not unit:BeenDestroyed() do
            WaitSeconds(1.5)
            local pos = unit:GetPosition()
            -- Scan 22-unit radius for damaged raptors
            local allies = brain:GetUnitsAroundPoint(categories.RAPTOR, pos, 22.0, 'Ally')
            for _, ally in allies do
                -- Exclude self and other healers (prevents infinite mutual healing)
                if ally and not ally.Dead and ally:GetEntityId() ~= unit:GetEntityId() then
                    local bp = ally:GetBlueprint()
                    if not (bp and bp.CategoriesHash and bp.CategoriesHash['HEALER']) then
                        local curHp = ally:GetHealth()
                        local maxHp = ally:GetMaxHealth()
                        if curHp < maxHp then
                            local healAmt = math.min(60, maxHp - curHp)
                            ally:SetHealth(ally, curHp + healAmt)
                            CreateEmitterAtEntity(ally, army, '/mods/RaptorFaction/effects/emitters/raptor_bio_heal_burst_01_emit.bp'):ScaleEmitter(0.5)
                        end
                    end
                end
            end
        end
    end)
end
