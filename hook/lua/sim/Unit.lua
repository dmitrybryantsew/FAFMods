-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/hook/lua/sim/Unit.lua
-- **  Author   :  Raptor Swarm Faction & Master Overhaul Hook
-- **  Summary  :  Integrates Raptor targeting registration, egg drops, and
-- **              FAF Master Overhaul outbound damage scaling.
-- **
-- ****************************************************************************

local Targeting = import('/mods/RaptorFaction/lua/RaptorTargeting.lua')
local Eggs = import('/mods/RaptorFaction/lua/RaptorEggs.lua')
local Spawner = import('/mods/RaptorFaction/lua/RaptorSpawner.lua')

local OldUnit = Unit
Unit = Class(OldUnit) {
    OnStopBeingBuilt = function(self, builder, layer)
        local result = OldUnit.OnStopBeingBuilt(self, builder, layer)
        local bp = self:GetBlueprint()
        local cats = bp.CategoriesHash or {}

        -- If not a biological raptor, register as an economic target for swarms
        if not cats['RAPTOR'] then
            Targeting.RegisterUnitTarget(self)
        end

        return result
    end,

    OnDamage = function(self, instigator, amount, vector, damageType)
        local amt = amount
        -- FAF Master Overhaul outbound damage multiplier integration
        if instigator and instigator.RaptorTotalDmgMult and instigator.RaptorTotalDmgMult ~= 1.0 and amt > 0 then
            amt = amt * instigator.RaptorTotalDmgMult
        end
        return OldUnit.OnDamage(self, instigator, amt, vector, damageType)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local bp = self:GetBlueprint()
        local cats = bp.CategoriesHash or {}

        if cats['RAPTOR'] then
            -- 1. Spawn Biomass Egg Sac with 90s decay
            Eggs.SpawnRaptorEgg(self)

            -- 2. Notify Spawner of kill for UI Kill Counter & Queen tracking
            Spawner.OnRaptorKilled(self, instigator)

            -- 3. Check Hive / Spire destruction to spike Player Aggression
            if cats['BURROW'] or cats['SPIRE'] then
                Spawner.OnRaptorStructureKilled(self, instigator)
            end
        else
            -- Non-raptor killed: remove from target registry
            Targeting.UnregisterUnitTarget(self)
        end

        return OldUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}
