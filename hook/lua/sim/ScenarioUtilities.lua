-- ****************************************************************************
-- **
-- **  Hook     :  /lua/sim/ScenarioUtilities.lua
-- **  Author   :  Raptor Swarm Faction Port from BAR
-- **  Summary  :  Intercepts initial army spawning for Raptor Swarm armies.
-- **              Directly spawns the primary Raptor Gestation Hive (XRA0107)
-- **              with COMMAND category instead of a humanoid ACU, preventing
-- **              instant demoralization defeat and commander warp crashes.
-- **
-- ****************************************************************************

local OldCreateInitialArmyGroup = CreateInitialArmyGroup

function CreateInitialArmyGroup(strArmy, createCommander)
    local brain = GetArmyBrain(strArmy)
    local per = ScenarioInfo.ArmySetup[strArmy] and ScenarioInfo.ArmySetup[strArmy].AIPersonality
    local name = string.lower(brain.Nickname or '')

    local isRaptor = brain.IsRaptorSwarm 
        or (brain.GetFactionIndex and brain:GetFactionIndex() == 5)
        or (per and string.find(string.lower(per), 'raptor')) 
        or string.find(name, 'raptor') 
        or string.find(name, 'swarm')

    if isRaptor and createCommander then
        brain.IsRaptorSwarm = true
        local tblGroup = CreateArmyGroup(strArmy, 'INITIAL')
        local cdrUnit = CreateInitialArmyUnit(strArmy, 'XRA0107')
        return tblGroup, cdrUnit
    end

    return OldCreateInitialArmyGroup(strArmy, createCommander)
end
