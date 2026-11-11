-- ****************************************************************************
-- **
-- **  Hook     :  /lua/ui/game/gamemain.lua
-- **  Author   :  Raptor Swarm Faction & BAR Telemetry Engine
-- **  Summary  :  Initializes the Raptor Telemetry HUD Monitor when the game
-- **              UI is constructed.
-- **
-- ****************************************************************************

local OldCreateUI = CreateUI
function CreateUI(isReplay)
    OldCreateUI(isReplay)

    local RaptorStatusPanel = import('/mods/RaptorFaction/lua/ui/game/RaptorStatusPanel.lua')
    if RaptorStatusPanel and RaptorStatusPanel.CreatePanel then
        RaptorStatusPanel.CreatePanel(GetFrame(0))
    end
end
