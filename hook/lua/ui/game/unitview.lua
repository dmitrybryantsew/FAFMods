-- ****************************************************************************
-- **
-- **  Hook     :  /lua/ui/game/unitview.lua
-- **  Author   :  Raptor Swarm Faction & BAR Telemetry Port
-- **  Summary  :  Ensures that Raptor Swarm units and structures always display
-- **              the authentic Raptor race icon and Hivemind name instead
-- **              of placeholder faction icons or generic AI names.
-- **
-- ****************************************************************************

local OldUpdateWindow = UpdateWindow

function UpdateWindow(info)
    OldUpdateWindow(info)

    if info and info.blueprintId and info.blueprintId ~= 'unknown' then
        local bp = __blueprints[info.blueprintId]
        local isRaptor = false
        if bp and bp.CategoriesHash and bp.CategoriesHash['RAPTOR'] then
            isRaptor = true
        elseif bp and bp.General and string.lower(bp.General.FactionName or '') == 'raptor' then
            isRaptor = true
        elseif Sync and Sync.RaptorUI and Sync.RaptorUI.RaptorArmy and (info.armyIndex + 1 == Sync.RaptorUI.RaptorArmy) then
            isRaptor = true
        end

        if isRaptor and info.armyIndex + 1 ~= GetFocusArmy() and info.kills == 0 and info.shieldRatio <= 0 then
            local armyData = GetArmiesTable().armiesTable[info.armyIndex + 1]
            local raptorIcon = "/mods/RaptorFaction/textures/ui/common/widgets/faction-icons-alpha_bmp/raptor_ico.dds"
            local nick = (Sync and Sync.RaptorUI and Sync.RaptorUI.HivemindName) 
                or (armyData and armyData.nickname) 
                or "The Overmind"
            
            -- Sanitize any Seraphim/Cybran/generic AI name
            local lowerNick = string.lower(nick)
            if string.find(lowerNick, 'ahn%-') or string.find(lowerNick, 'ai:') or string.find(lowerNick, 'harms') or string.find(lowerNick, 'priscilla') or string.find(lowerNick, 'ronald') then
                nick = (Sync and Sync.RaptorUI and Sync.RaptorUI.HivemindName) or "The Overmind"
            end

            local color = (armyData and armyData.color) or 'ffff0000'
            if controls and controls.statGroups and controls.statGroups[1] then
                controls.statGroups[1].color:SetSolidColor(color)
                controls.statGroups[1].icon:SetTexture(UIUtil.UIFile(raptorIcon))
                controls.statGroups[1].value:SetText(string.sub(nick, 1, 16))
                controls.statGroups[1].icon:Show()
            end
        end
    end
end
