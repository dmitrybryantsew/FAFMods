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
    local unitId = unit:GetUnitId()
    local massCost = (bp.Economy and bp.Economy.BuildCostMass) or 100
    local pos = unit:GetPosition()
    if not pos then return end

    local count = eggCount or 1
    local chance = 0.33
    local reclaimMass = massCost
    local reclaimEnergy = (bp.Economy and bp.Economy.BuildCostEnergy) or massCost
    local scale = 0.10

    if massCost > 7500 then
        -- Large Egg (Bosses, T3 Apex, Matriarchs)
        chance = 1.0
        reclaimMass = math.floor(massCost * 0.33)
        reclaimEnergy = math.floor(reclaimEnergy * 0.33)
        scale = 0.22
    elseif massCost > 1500 then
        -- Medium Egg (T2 Crawlers, Bio-Artillery, Gunships)
        chance = 0.66
        reclaimMass = math.floor(massCost * 0.66)
        reclaimEnergy = math.floor(reclaimEnergy * 0.66)
        scale = 0.15
    end

    -- Bio-Zeppelin Blimpy (XRA0227): Dedicated living brood carrier always drops 2-3 eggs
    if unitId == 'xra0227' or (bp.CategoriesHash and bp.CategoriesHash['CARRIER']) then
        forceDrop = true
        count = eggCount or math.random(2, 3)
        scale = 0.14
        reclaimMass = math.floor(massCost * 0.75)
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
    local perEggMass = math.max(10, math.floor(reclaimMass / count))
    local perEggEnergy = math.max(20, math.floor(reclaimEnergy / count))

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
            eggProp:SetMaxReclaimValues(perEggMass, perEggEnergy, 1.0)
            eggProp:SetHealth(eggProp, 1000)

            -- 90-Second Rotting Decay Coroutine
            ForkThread(function()
                local hp = 1000
                while hp > 0 and not eggProp:BeenDestroyed() do
                    WaitSeconds(5.0)
                    if not eggProp or eggProp:BeenDestroyed() then break end
                    hp = hp - 55 -- Loses 55 HP every 5 seconds (~90 seconds total lifetime)
                    if hp <= 0 then
                        CreateEmitterAtEntity(eggProp, -1, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp'):ScaleEmitter(0.8)
                        eggProp:Destroy()
                        break
                    else
                        eggProp:SetHealth(eggProp, hp)
                    end
                end
            end)
        end
    end
end
