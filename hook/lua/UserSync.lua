-- ****************************************************************************
-- **
-- **  Hook     :  /lua/UserSync.lua
-- **  Author   :  Raptor Swarm Faction & BAR Telemetry Engine
-- **  Summary  :  Intercepts sim-to-ui Sync data for Raptor HUD telemetry & announcements
-- **
-- ****************************************************************************

local OldOnSync = OnSync
function OnSync()
    OldOnSync()

    if Sync.RaptorUI then
        local RaptorStatusPanel = import('/mods/RaptorFaction/lua/ui/game/RaptorStatusPanel.lua')
        if RaptorStatusPanel and RaptorStatusPanel.ReceiveData then
            RaptorStatusPanel.ReceiveData(Sync.RaptorUI)
        end
    end

    if Sync.RaptorAnnounce then
        local printText = {
            text = Sync.RaptorAnnounce.Text or "Raptor Event",
            size = 18,
            color = Sync.RaptorAnnounce.Color == 'red' and 'ffff3333' or (Sync.RaptorAnnounce.Color == 'orange' and 'ffffaa33' or 'ff33ff33'),
            duration = 6,
            location = 'center',
        }
        import('/lua/ui/game/textdisplay.lua').PrintToScreen(printText)
    end
end
