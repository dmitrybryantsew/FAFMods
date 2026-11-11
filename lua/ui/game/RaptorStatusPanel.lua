-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/lua/ui/game/RaptorStatusPanel.lua
-- **  Author   :  Ported from Beyond All Reason (BAR) to Supreme Commander / FAF
-- **  Summary  :  In-game HUD monitor showing Raptor Swarm telemetry:
-- **              Grace Period, Difficulty Mode, Raptor Kill Count,
-- **              Queen Incubation / Evolution, Base Rate, Aggression Rate,
-- **              and Queen Titan combat health.
-- **
-- ****************************************************************************

local UIUtil = import('/lua/ui/uiutil.lua')
local LayoutHelpers = import('/lua/maui/layouthelpers.lua')
local Group = import('/lua/maui/group.lua').Group
local Bitmap = import('/lua/maui/bitmap.lua').Bitmap
local Text = import('/lua/maui/text.lua').Text
local GameMain = import('/lua/ui/game/gamemain.lua')

local controls = {}
local isCollapsed = false
local currentLang = 'ru' -- Default to Russian matching BAR screenshots, toggleable to EN
local lastData = nil
local hasEverReceivedData = false

local Strings = {
    ru = {
        Grace = "Период затишья: %d:%02d",
        Incubation = "Инкубация Королевы: %d%%(Эволюция: %d%%)",
        RateBase = "База: +%.3f%%/с",
        RateAggro = "Агрессия игроков: +%.3f%%/с",
        Kills = "Убито Рапторов: %d",
        Mode = "Режим: %s",
        QueenHealth = "Здоровье Королевы: %d%%",
        QueensKilled = "Убито Королев: %d",
        ToggleTip = "Клик: Свернуть / Развернуть HUD",
        LangTip = "Клик: Переключить язык (RU/EN)",
        Difficulties = {
            veryeasy = "Очень легкая",
            easy     = "Легкая",
            normal   = "Нормальная",
            hard     = "Сложная",
            veryhard = "Очень сложная",
            epic     = "Эпическая",
        }
    },
    en = {
        Grace = "Grace Period: %d:%02d",
        Incubation = "Queen Incubation: %d%% (Evolution: %d%%)",
        RateBase = "Base: +%.3f%%/s",
        RateAggro = "Player Aggression: +%.3f%%/s",
        Kills = "Raptor Kills: %d",
        Mode = "Mode: %s",
        QueenHealth = "Queen Health: %d%%",
        QueensKilled = "Queens Slain: %d",
        ToggleTip = "Click: Collapse / Expand HUD",
        LangTip = "Click: Toggle Language (RU/EN)",
        Difficulties = {
            veryeasy = "Very Easy",
            easy     = "Easy",
            normal   = "Normal",
            hard     = "Hard",
            veryhard = "Very Hard",
            epic     = "Epic",
        }
    }
}

---Toggles language between Russian and English
function ToggleLanguage()
    if currentLang == 'ru' then
        currentLang = 'en'
    else
        currentLang = 'ru'
    end
    if controls.lblLang then
        controls.lblLang:SetText(string.upper(currentLang))
    end
    if lastData then
        UpdateData(lastData)
    end
end

---Toggles between Expanded Monitor and Compact Floating Badge
function ToggleCollapse()
    isCollapsed = not isCollapsed
    if isCollapsed then
        if controls.panel then controls.panel:Hide() end
        if controls.miniBadge then
            controls.miniBadge:Show()
            if controls.panel then
                controls.miniBadge.Left:Set(controls.panel.Left())
                controls.miniBadge.Top:Set(controls.panel.Top())
            end
        end
    else
        if controls.miniBadge then controls.miniBadge:Hide() end
        if controls.panel then controls.panel:Show() end
    end
end

---Updates UI labels with the latest telemetry from Sim
---@param data table
function UpdateData(data)
    if not data or not controls.panel then return end

    local dict = Strings[currentLang] or Strings['ru']
    local diffName = dict.Difficulties[data.Difficulty] or data.Difficulty or "Normal"

    -- 1. TITLE ROW: Grace Period or Queen Incubation / Queen Health
    if data.InGracePeriod then
        local m = math.floor(data.GraceSeconds / 60)
        local s = math.mod(data.GraceSeconds, 60)
        controls.lblTitle:SetText(string.format(dict.Grace, m, s))
        controls.lblTitle:SetColor('ffffffff')
        controls.lblRateBase:Hide()
        controls.lblRateAggro:Hide()
        controls.lblQueensKilled:Hide()
    else
        if data.QueenSpawned and data.QueenHealth and data.QueenHealth > 0 then
            controls.lblTitle:SetText(string.format(dict.QueenHealth, data.QueenHealth))
            controls.lblTitle:SetColor('ffff3333')
        else
            controls.lblTitle:SetText(string.format(dict.Incubation, data.QueenAnger or 0, data.TechAnger or 0))
            controls.lblTitle:SetColor('ffffdd88')
        end

        controls.lblRateBase:Show()
        controls.lblRateBase:SetText(string.format(dict.RateBase, data.BaseAngerGain or 0.037))

        controls.lblRateAggro:Show()
        controls.lblRateAggro:SetText(string.format(dict.RateAggro, (data.PlayerAggression or 0) * 0.01))

        if data.QueensKilled and data.QueensKilled > 0 then
            controls.lblQueensKilled:Show()
            controls.lblQueensKilled:SetText(string.format(dict.QueensKilled, data.QueensKilled))
        else
            controls.lblQueensKilled:Hide()
        end
    end

    -- 2. KILL COUNT
    controls.lblKills:SetText(string.format(dict.Kills, data.Kills or 0))

    -- 3. DIFFICULTY MODE
    controls.lblMode:SetText(string.format(dict.Mode, diffName))
end

---Receives telemetry directly from UserSync hook
---@param data table
function ReceiveData(data)
    if not data then return end
    lastData = data
    hasEverReceivedData = true

    if data.Active then
        if not isCollapsed then
            if controls.panel and controls.panel:IsHidden() then
                controls.panel:Show()
            end
            if controls.miniBadge and not controls.miniBadge:IsHidden() then
                controls.miniBadge:Hide()
            end
        else
            if controls.panel and not controls.panel:IsHidden() then
                controls.panel:Hide()
            end
            if controls.miniBadge and controls.miniBadge:IsHidden() then
                controls.miniBadge:Show()
            end
        end
    end

    UpdateData(data)
end

---Engine heartbeat callback checking UserSync every sim tick
function OnBeat()
    if Sync and Sync.RaptorUI then
        ReceiveData(Sync.RaptorUI)
    elseif lastData and hasEverReceivedData and lastData.Active then
        UpdateData(lastData)
    end
end

---Creates and attaches the Raptor Telemetry HUD Monitor
---@param parent Frame
function CreatePanel(parent)
    if controls.panel then return end
    parent = parent or GetFrame(0)

    -- 1. ROOT CONTAINER (Draggable Frame)
    controls.panel = Group(parent)
    controls.panel.Depth:Set(95)
    controls.panel.Width:Set(300)
    controls.panel.Height:Set(210)

    -- Default position: top-right under score
    LayoutHelpers.AtRightTopIn(controls.panel, parent, 18, 160)

    -- 2. MONITOR BACKGROUND TEXTURE (High-res 600x420 scaled to 300x210)
    controls.bg = Bitmap(controls.panel)
    controls.bg:SetTexture('/mods/RaptorFaction/textures/ui/common/raptors/raptorpanel.dds')
    LayoutHelpers.FillParent(controls.bg, controls.panel)
    controls.bg:DisableHitTest(true)

    -- 3. TEXT LABELS (Positioned precisely to match BAR HUD)
    -- Title / Grace Period / Queen Incubation
    controls.lblTitle = UIUtil.CreateText(controls.panel, '', 13, UIUtil.bodyFont)
    controls.lblTitle:SetColor('ffffffff')
    LayoutHelpers.AtLeftTopIn(controls.lblTitle, controls.panel, 34, 28)
    controls.lblTitle:DisableHitTest(true)

    -- Base Incubation Rate
    controls.lblRateBase = UIUtil.CreateText(controls.panel, '', 11, UIUtil.bodyFont)
    controls.lblRateBase:SetColor('ffd8d8d8')
    LayoutHelpers.AtLeftTopIn(controls.lblRateBase, controls.panel, 46, 52)
    controls.lblRateBase:DisableHitTest(true)

    -- Player Aggression Rate
    controls.lblRateAggro = UIUtil.CreateText(controls.panel, '', 11, UIUtil.bodyFont)
    controls.lblRateAggro:SetColor('ffd8d8d8')
    LayoutHelpers.AtLeftTopIn(controls.lblRateAggro, controls.panel, 46, 70)
    controls.lblRateAggro:DisableHitTest(true)

    -- Queens Slain Row
    controls.lblQueensKilled = UIUtil.CreateText(controls.panel, '', 11, UIUtil.bodyFont)
    controls.lblQueensKilled:SetColor('ffffaa33')
    LayoutHelpers.AtLeftTopIn(controls.lblQueensKilled, controls.panel, 46, 88)
    controls.lblQueensKilled:DisableHitTest(true)
    controls.lblQueensKilled:Hide()

    -- Raptor Kill Counter
    controls.lblKills = UIUtil.CreateText(controls.panel, '', 13, UIUtil.bodyFont)
    controls.lblKills:SetColor('ffffffff')
    LayoutHelpers.AtLeftTopIn(controls.lblKills, controls.panel, 34, 138)
    controls.lblKills:DisableHitTest(true)

    -- Difficulty Mode
    controls.lblMode = UIUtil.CreateText(controls.panel, '', 13, UIUtil.bodyFont)
    controls.lblMode:SetColor('ffffffff')
    LayoutHelpers.AtLeftTopIn(controls.lblMode, controls.panel, 90, 168)
    controls.lblMode:DisableHitTest(true)

    -- Language Indicator / Switcher (Top-right corner of HUD)
    controls.lblLang = UIUtil.CreateText(controls.panel, 'RU', 10, UIUtil.bodyFont)
    controls.lblLang:SetColor('88ffffff')
    LayoutHelpers.AtRightTopIn(controls.lblLang, controls.panel, 28, 14)
    controls.lblLang:DisableHitTest(true)

    -- 4. DRAG & CLICK EVENT HANDLING
    controls.panel.HandleEvent = function(self, event)
        if event.Type == 'ButtonPress' then
            if event.Modifiers.Left then
                local relX = event.MouseX - self.Left()
                local relY = event.MouseY - self.Top()

                -- Click on bottom-left badge (X: 10..55, Y: 155..205) -> Toggle Collapse
                if relX >= 10 and relX <= 55 and relY >= 155 and relY <= 205 then
                    ToggleCollapse()
                    return true
                end

                -- Click on top-right language area -> Toggle Language
                if relX >= 240 and relX <= 290 and relY >= 10 and relY <= 35 then
                    ToggleLanguage()
                    return true
                end

                -- Start window drag
                self.dragging = true
                self.dragStartX = event.MouseX - self.Left()
                self.dragStartY = event.MouseY - self.Top()
                return true
            end
        elseif event.Type == 'ButtonRelease' then
            if event.Modifiers.Left then
                self.dragging = false
                return true
            end
        elseif event.Type == 'MouseMove' then
            if self.dragging then
                local newLeft = event.MouseX - self.dragStartX
                local newTop = event.MouseY - self.dragStartY
                local frame = GetFrame(0)
                newLeft = math.max(0, math.min(frame.Right() - self.Width(), newLeft))
                newTop = math.max(0, math.min(frame.Bottom() - self.Height(), newTop))
                self.Left:Set(newLeft)
                self.Top:Set(newTop)
                return true
            end
        end
        return false
    end

    -- 5. COMPACT MINIMIZED FLOATING BADGE
    controls.miniBadge = Group(parent)
    controls.miniBadge.Depth:Set(96)
    controls.miniBadge.Width:Set(48)
    controls.miniBadge.Height:Set(48)
    LayoutHelpers.AtRightTopIn(controls.miniBadge, parent, 18, 160)
    controls.miniBadge:Hide()

    controls.miniIcon = Bitmap(controls.miniBadge)
    controls.miniIcon:SetTexture('/mods/RaptorFaction/textures/ui/common/faction_icon-lg/raptor_ico.dds')
    LayoutHelpers.FillParent(controls.miniIcon, controls.miniBadge)
    controls.miniIcon:DisableHitTest(true)

    controls.miniBadge.HandleEvent = function(self, event)
        if event.Type == 'ButtonPress' and event.Modifiers.Left then
            self.dragging = true
            self.dragStartX = event.MouseX - self.Left()
            self.dragStartY = event.MouseY - self.Top()
            self.hasMoved = false
            return true
        elseif event.Type == 'MouseMove' and self.dragging then
            self.hasMoved = true
            local newLeft = event.MouseX - self.dragStartX
            local newTop = event.MouseY - self.dragStartY
            local frame = GetFrame(0)
            newLeft = math.max(0, math.min(frame.Right() - self.Width(), newLeft))
            newTop = math.max(0, math.min(frame.Bottom() - self.Height(), newTop))
            self.Left:Set(newLeft)
            self.Top:Set(newTop)
            return true
        elseif event.Type == 'ButtonRelease' and event.Modifiers.Left then
            self.dragging = false
            if not self.hasMoved then
                ToggleCollapse()
            end
            return true
        end
        return false
    end

    -- 6. REGISTER ENGINE BEAT UPDATE
    GameMain.AddBeatFunction(OnBeat, true)
    controls.panel.OnDestroy = function(self)
        GameMain.RemoveBeatFunction(OnBeat)
    end

    -- Start hidden until Raptor telemetry arrives
    controls.panel:Hide()
end
