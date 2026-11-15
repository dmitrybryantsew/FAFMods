-- ****************************************************************************
-- **
-- **  Hook     :  /lua/sim/VictoryCondition/DecapitationCondition.lua
-- **  Author   :  Raptor Swarm Faction Port
-- **  Summary  :  Ensures Raptor Swarm army victory condition is tied to the
-- **              actual Queen Titan and not triggered prematurely by hives
-- **              or sub-boss command units.
-- **
-- ****************************************************************************

local OldDecapitationCondition = DecapitationCondition

DecapitationCondition = Class(OldDecapitationCondition) {

    BrainHasEligibleUnits = function(self, aiBrain, categories)
        if aiBrain.IsRaptorSwarm then
            local Spawner = import('/mods/RaptorFaction/lua/RaptorSpawner.lua')
            if Spawner then
                if Spawner.GetQueensKilled and Spawner.GetQueensKilled() > 0 then
                    -- If Endless Mode is enabled, the swarm keeps fighting
                    if Spawner.IsEndlessMode and Spawner.IsEndlessMode() then
                        return true
                    end
                    -- Queen slain and Endless Mode disabled: Raptor Swarm defeated!
                    return false
                end
                -- Queen Titan has not been slain yet: Swarm is still active
                return true
            end
        end

        return OldDecapitationCondition.BrainHasEligibleUnits(self, aiBrain, categories)
    end,
}
