-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/hook/lua/aibrain.lua
-- **  Author   :  Raptor Swarm Faction Port from BAR
-- **  Summary  :  Intercepts AI skirmish initialization for Raptor AI slots
-- **              so standard base builder threads are suppressed in favor of
-- **              the RaptorSpawner wave engine.
-- **
-- ****************************************************************************

local OldAIBrain = AIBrain

AIBrain = Class(OldAIBrain) {

    InitializeSkirmishSystems = function(self)
        local per = ScenarioInfo.ArmySetup[self.Name] and ScenarioInfo.ArmySetup[self.Name].AIPersonality
        local name = string.lower(self.Nickname or '')

        if (per and string.find(string.lower(per), 'raptor')) or string.find(name, 'raptor') or string.find(name, 'swarm') then
            self.IsRaptorSwarm = true

            -- Turn off default army pool builder AI so it doesn't build standard factories/mexes
            local poolPlatoon = self:GetPlatoonUniquelyNamed('ArmyPool')
            if poolPlatoon then
                poolPlatoon:TurnOffPoolAI()
            end
            return
        end

        return OldAIBrain.InitializeSkirmishSystems(self)
    end,
}
