-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/lua/RaptorEggs.lua
-- **  Author   :  Ported from Beyond All Reason (features/raptor_egg.lua) to FAF
-- **  Summary  :  Biomass Raptor Egg drops with metal/energy reclaim and
-- **              a 90-second rotting decay thread. Always grounds egg props.
-- **
-- ****************************************************************************

local CreatePropHPR = CreatePropHPR
local GetSurfaceHeight = GetSurfaceHeight

---Spawns biological egg feature(s) upon raptor death with dynamic reclaim and a 90s decay timer
---@param unit Unit
---@param forceDrop boolean
---@param eggCount number
function SpawnRaptorEgg(unit, forceDrop, eggCount)
    if not unit or unit:BeenDestroyed() or unit.EggsDropped then return end

    local bp = unit:GetBlueprint()
    local unitId = string.lower(unit:GetUnitId() or '')
    local massCost = (bp.Economy and bp.Economy.BuildCostMass) or 100
    local pos = unit:GetPosition()
    if not pos then return end

    local count = eggCount or 1
    local chance = 0.33
    -- Base mass drop reduced from 100% to 20% of unit mass for standard swarmers
    local reclaimMass = math.floor(massCost * 0.20)
    local scale = 0.10

    if massCost > 7500 then
        -- Large Egg (Bosses, T3 Apex, Matriarchs): reduced from 33% to 15% (e.g. 4,200 mass for Queen instead of 105,600)
        chance = 1.0
        reclaimMass = math.floor(massCost * 0.15)
        scale = 0.22
    elseif massCost > 1500 then
        -- Medium Egg (T2 Crawlers, Bio-Artillery, Gunships): reduced from 66% to 25%
        chance = 0.66
        reclaimMass = math.floor(massCost * 0.25)
        scale = 0.15
    end

    -- Bio-Zeppelin Blimpy (XRA0227): Dedicated living brood carrier always drops 2-3 eggs
    if unitId == 'xra0227' or (bp.CategoriesHash and bp.CategoriesHash['CARRIER']) then
        forceDrop = true
        count = eggCount or math.random(2, 3)
        scale = 0.14
        reclaimMass = math.floor(massCost * 0.25)
    end

    if forceDrop then
        chance = 1.0
        if scale < 0.14 then
            scale = 0.14
        end
    end

    if math.random() > chance then return end

    unit.EggsDropped = true

    local propBp = '/mods/RaptorFaction/env/props/raptor_egg_prop.bp'
    local perEggMass = math.max(5, math.floor(reclaimMass / count))
    -- Energy reclaim is matched to mass so engine reclaim duration is never bloated by huge energy costs
    local perEggEnergy = perEggMass

    for i = 1, count do
        local angle = math.random() * 6.283
        local dist = (count > 1) and (1.0 + math.random() * 2.5) or 0
        local x = pos[1] + math.cos(angle) * dist
        local z = pos[3] + math.sin(angle) * dist
        local y = GetSurfaceHeight(x, z)
        local heading = math.random() * 6.283
        local eggProp = CreatePropHPR(propBp, x, y, z, heading, 0, 0)

        if eggProp then
            eggProp:SetScale(scale)
            eggProp:SetMaxHealth(1000)
            eggProp:SetHealth(eggProp, 1000)

            -- FAF Prop:SetMaxReclaimValues signature: (timeMult, mass, energy)
            -- timeMult = 1.0 ensures standard, responsive FAF reclamation duration
            eggProp:SetMaxReclaimValues(1.0, perEggMass, perEggEnergy)

            -- 90-Second Rotting Decay Coroutine:
            -- Smoothly rots egg health down over 90 seconds (10 steps x 9 seconds).
            -- Uses AdjustHealth so active engineer reclamation progress is NEVER overwritten/reset.
            ForkThread(function()
                local totalSteps = 10
                local stepInterval = 9.0 -- 10 steps * 9.0s = 90.0s lifetime
                local decayDmg = math.ceil(1000 / totalSteps) -- 100 HP per interval

                for s = 1, totalSteps do
                    WaitSeconds(stepInterval)
                    if not eggProp or eggProp:BeenDestroyed() then return end

                    local curHp = eggProp:GetHealth()
                    if not curHp or curHp <= decayDmg then
                        -- Egg fully rotted away: dissolve effect and clean destruction
                        if not eggProp:BeenDestroyed() then
                            CreateEmitterAtEntity(eggProp, -1, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp'):ScaleEmitter(scale * 4.0)
                            eggProp:Destroy()
                        end
                        return
                    else
                        eggProp:AdjustHealth(eggProp, -decayDmg)
                        eggProp:UpdateReclaimLeft()
                    end
                end

                if eggProp and not eggProp:BeenDestroyed() then
                    CreateEmitterAtEntity(eggProp, -1, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp'):ScaleEmitter(scale * 4.0)
                    eggProp:Destroy()
                end
            end)
        end
    end
end
