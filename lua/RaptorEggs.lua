-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/lua/RaptorEggs.lua
-- **  Author   :  Ported from Beyond All Reason (features/raptor_egg.lua) to FAF
-- **  Summary  :  Biomass Raptor Egg drops with metal/energy reclaim and
-- **              a 90-second rotting decay thread.
-- **
-- ****************************************************************************

local CreatePropHPR = CreatePropHPR

---Spawns a biological egg feature upon raptor death with dynamic reclaim and a 90s decay timer
---@param unit Unit
function SpawnRaptorEgg(unit)
    if not unit or unit:BeenDestroyed() then return end
    local bp = unit:GetBlueprint()
    local massCost = (bp.Economy and bp.Economy.BuildCostMass) or 100
    local pos = unit:GetPosition()
    if not pos then return end

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

    if math.random() > chance then return end

    local propBp = '/mods/RaptorFaction/env/props/raptor_egg_prop.bp'
    local heading = math.random() * 6.28
    local eggProp = CreatePropHPR(propBp, pos[1], pos[2], pos[3], heading, 0, 0)

    if eggProp then
        eggProp:SetScale(scale)
        eggProp:SetMaxReclaimValues(reclaimMass, reclaimEnergy, 1.0)
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
