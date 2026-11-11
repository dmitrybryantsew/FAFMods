"""
FAF Mod Forge - Local Web Server
Interactive UI for filtering units, editing unit-specific stats,
and exporting packaged FAF mods directly into the game's mods folder.
"""

import http.server
import json
import os
import shutil
import socketserver
import urllib.parse
import uuid
import zipfile
import webbrowser
from pathlib import Path

PORT = 5055
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "units.json"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
EXPORTS_DIR = BASE_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Supreme Commander mods path on Windows
DOCUMENTS_MODS_DIR = Path(os.path.expanduser("~")) / "Documents" / "My Games" / "Gas Powered Games" / "Supreme Commander Forged Alliance" / "mods"


def load_processed_units():
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f).get("units", [])

    processed = []
    for u in raw:
        uid = u.get("Id", "")
        cats = u.get("Categories", []) or []
        
        # Determine tech
        tech = "OTHER"
        if "TECH1" in cats:
            tech = "T1"
        elif "TECH2" in cats:
            tech = "T2"
        elif "TECH3" in cats:
            tech = "T3"
        elif "EXPERIMENTAL" in cats:
            tech = "EXP"

        # Determine type
        utype = "OTHER"
        if "LAND" in cats:
            utype = "LAND"
        elif "AIR" in cats:
            utype = "AIR"
        elif "NAVAL" in cats:
            utype = "NAVAL"
        elif "DEFENSE" in cats:
            utype = "DEFENSE"
        elif "STRUCTURE" in cats:
            utype = "STRUCTURE"
        elif "COMMAND" in cats:
            utype = "COMMAND"

        general = u.get("General", {}) or {}
        defense = u.get("Defense", {}) or {}
        economy = u.get("Economy", {}) or {}
        physics = u.get("Physics", {}) or {}
        intel = u.get("Intel", {}) or {}
        weapons = u.get("Weapon", []) or []

        faction = general.get("FactionName", "Unknown")
        name = general.get("UnitName")
        desc = u.get("Description", "")
        
        display_name = f"{name} ({desc})" if name else desc or uid

        # Find best primary weapon
        weapon_name = ""
        weapon_damage = 0
        weapon_rof = 0
        weapon_range = 0
        weapon_aoe = 0
        weapon_muzzle_vel = 0
        if weapons:
            non_death = [w for w in weapons if w.get("WeaponCategory") != "Death" and w.get("DamageType") not in ("DeathExplosion", "Deathnuke")]
            best_w = max(non_death, key=lambda w: (w.get("Damage", 0), w.get("MaxRadius", 0))) if non_death else weapons[0]
            weapon_name = best_w.get("DisplayName", "")
            weapon_damage = best_w.get("Damage", 0)
            if not weapon_damage and best_w.get("NukeInnerRingDamage"):
                weapon_damage = best_w.get("NukeInnerRingDamage", 0)
            weapon_rof = round(best_w.get("RateOfFire", 0), 2)
            weapon_range = best_w.get("MaxRadius", 0)
            weapon_aoe = round(best_w.get("DamageRadius", 0), 2)
            if not weapon_aoe and best_w.get("NukeOuterRingRadius"):
                weapon_aoe = best_w.get("NukeOuterRingRadius", 0)
            weapon_muzzle_vel = best_w.get("MuzzleVelocity", 0)

        shield = defense.get("Shield", {}) or {}
        shield_hp = shield.get("ShieldMaxHealth", 0)
        shield_regen = shield.get("ShieldRegenRate", 0)

        regen = defense.get("RegenRate", 0)
        turn_rate = round(physics.get("TurnRate", 0), 1)
        speed = round(physics.get("MaxSpeed", 0), 2)

        vision = intel.get("VisionRadius", 0)
        radar = intel.get("RadarRadius", 0) or intel.get("SonarRadius", 0) or intel.get("OmniRadius", 0)

        mass_prod = economy.get("ProductionPerSecondMass", 0)
        energy_prod = economy.get("ProductionPerSecondEnergy", 0)

        processed.append({
            "id": uid,
            "name": display_name,
            "unitName": name or "",
            "desc": desc or "",
            "faction": faction,
            "tech": tech,
            "type": utype,
            "categories": cats,
            "hp": defense.get("Health", 0),
            "regen": regen,
            "shield": shield_hp,
            "shieldRegen": shield_regen,
            "hasShield": shield_hp > 0,
            "mass": economy.get("BuildCostMass", 0),
            "energy": economy.get("BuildCostEnergy", 0),
            "buildTime": economy.get("BuildTime", 0),
            "buildRate": economy.get("BuildRate", 0),
            "massProd": mass_prod,
            "energyProd": energy_prod,
            "hasEcoProd": (mass_prod > 0 or energy_prod > 0),
            "speed": speed,
            "turnRate": turn_rate,
            "vision": vision,
            "radar": radar,
            "hasRadar": radar > 0,
            "hasWeapons": len(weapons) > 0 and (weapon_damage > 0 or weapon_range > 0),
            "weaponName": weapon_name,
            "weaponDamage": weapon_damage,
            "weaponRof": weapon_rof,
            "weaponRange": weapon_range,
            "weaponAoe": weapon_aoe,
            "weaponMuzzleVel": weapon_muzzle_vel,
        })

    return processed


PROCESSED_UNITS = load_processed_units()


def generate_ui_unitview_detail_lua(unit_table_lua, target_mode, player_name):
    return f"""-- Auto-generated by FAF Mod Forge - Unit View Detail UI Hook
-- Displays comparison stats (new_value vs base: old_value) and buff breakdown by source
local UIUtil = import('/lua/ui/uiutil.lua')
local LayoutHelpers = import('/lua/maui/layouthelpers.lua')
local OldShow = Show
local OldCreateLines = CreateLines

local TargetScope = "{target_mode}"
local TargetPlayer = "{player_name}"

local UnitConfigs = {{
{unit_table_lua}
}}

local function MatchesPlayerName(actualName, targetName)
    if not actualName or not targetName or targetName == "" then return false end
    local a = string.lower(actualName)
    local t = string.lower(targetName)
    if a == t then return true end
    if string.find(a, t, 1, true) then return true end
    local stripped = string.gsub(a, "%b[]", "")
    stripped = string.gsub(stripped, "%b()", "")
    stripped = string.gsub(stripped, "^%s*(.-)%s*$", "%1")
    if stripped == t or string.find(stripped, t, 1, true) then return true end
    return false
end

local function IsBuffsActiveForFocusArmy()
    if TargetScope == "global" then return true end
    local focusArmy = GetFocusArmy()
    if not focusArmy or focusArmy < 1 then return true end
    local armies = GetArmiesTable()
    local myName = armies and armies.armiesTable and armies.armiesTable[focusArmy] and armies.armiesTable[focusArmy].nickname
    if myName and MatchesPlayerName(myName, TargetPlayer) then
        return true
    end
    return false
end

local function GetActiveBuffSourcesForUnit(bp, bpId)
    local sources = {{}}
    local id = string.lower(bpId or (bp and bp.BlueprintId) or "")

    if IsBuffsActiveForFocusArmy() and UnitConfigs[id] then
        table.insert(sources, {{
            name = "Base Mod",
            cfg = UnitConfigs[id],
        }})
    end

    local focusArmy = GetFocusArmy()
    if focusArmy and focusArmy > 0 and _G.ModForgeActiveRelics and _G.ModForgeActiveRelics[focusArmy] then
        for rId, rData in pairs(_G.ModForgeActiveRelics[focusArmy]) do
            local matches = false
            if rData.targetType == "unit" then
                if rData.targetUnitId and string.lower(rData.targetUnitId) == id then
                    matches = true
                end
            elseif bp and bp.Categories then
                local cats = {{}}
                for _, c in ipairs(bp.Categories) do cats[c] = true end
                local tName = string.lower(rData.targetCategoryName or rData.targetName or "")
                if rData.id == "preset_center_beacon" or string.find(tName, "t1") then
                    if cats.LAND and cats.TECH1 and (cats.DIRECTFIRE or cats.INDIRECTFIRE or cats.ANTIAIR or cats.ARTILLERY) then
                        matches = true
                    end
                elseif rData.id == "preset_ancient_monolith" or string.find(tName, "commander") then
                    if cats.COMMAND then matches = true end
                elseif rData.id == "preset_quantum_core" or string.find(tName, "experimental") then
                    if cats.EXPERIMENTAL then matches = true end
                elseif rData.id == "preset_supply_cache" or string.find(tName, "artillery") then
                    if cats.ARTILLERY or cats.SILO then matches = true end
                else
                    matches = true
                end
            end

            if matches and rData.buffs then
                table.insert(sources, {{
                    name = "Relic: " .. tostring(rData.name or "Objective"),
                    cfg = rData.buffs,
                    duration = rData.duration,
                }})
            end
        end
    end

    return sources
end

local activeSources = nil
local activeBp = nil

function CreateLines(control, blocks)
    if activeSources and activeBp and blocks then
        local bp = activeBp
        local buffLines = {{"⚡ ACTIVE BUFFS & SOURCES:"}}

        local totalHpMult = 1.0
        local totalDmgMult = 1.0
        local totalRngMult = 1.0
        local totalSpdMult = 1.0
        local totalShdMult = 1.0
        local totalRgnMult = 1.0

        for _, s in ipairs(activeSources) do
            local parts = {{}}
            if s.cfg.hpMult and s.cfg.hpMult ~= 1.0 then
                totalHpMult = totalHpMult * s.cfg.hpMult
                table.insert(parts, string.format("+%d%% HP", math.floor((s.cfg.hpMult - 1.0) * 100)))
            end
            if s.cfg.damageMult and s.cfg.damageMult ~= 1.0 then
                totalDmgMult = totalDmgMult * s.cfg.damageMult
                table.insert(parts, string.format("+%d%% Dmg", math.floor((s.cfg.damageMult - 1.0) * 100)))
            end
            if s.cfg.rangeMult and s.cfg.rangeMult ~= 1.0 then
                totalRngMult = totalRngMult * s.cfg.rangeMult
                table.insert(parts, string.format("+%d%% Rng", math.floor((s.cfg.rangeMult - 1.0) * 100)))
            end
            if s.cfg.speedMult and s.cfg.speedMult ~= 1.0 then
                totalSpdMult = totalSpdMult * s.cfg.speedMult
                table.insert(parts, string.format("+%d%% Spd", math.floor((s.cfg.speedMult - 1.0) * 100)))
            end
            if s.cfg.shieldMult and s.cfg.shieldMult ~= 1.0 then
                totalShdMult = totalShdMult * s.cfg.shieldMult
                table.insert(parts, string.format("+%d%% Shield", math.floor((s.cfg.shieldMult - 1.0) * 100)))
            end
            if s.cfg.regenMult and s.cfg.regenMult ~= 1.0 then
                totalRgnMult = totalRgnMult * s.cfg.regenMult
                table.insert(parts, string.format("+%d%% Regen", math.floor((s.cfg.regenMult - 1.0) * 100)))
            end
            local durStr = (s.duration and s.duration > 0) and string.format(" [Temporal: %ds]", s.duration) or ""
            table.insert(buffLines, string.format("  • %s: %s%s", s.name, table.concat(parts, ", "), durStr))
        end

        local bestWep = nil
        if bp.Weapon then
            for _, w in bp.Weapon do
                local isDeath = (w.WeaponCategory == "Death" or w.DamageType == "DeathExplosion" or w.DamageType == "Deathnuke")
                if not isDeath and (w.Damage or 0) > 0 then
                    if not bestWep or (w.Damage or 0) > (bestWep.Damage or 0) then
                        bestWep = w
                    end
                end
            end
        end

        if table.getn(activeSources) >= 1 then
            table.insert(buffLines, "  ──────────────────────")
            if totalHpMult ~= 1.0 and bp.Defense and bp.Defense.MaxHealth then
                local baseHp = bp.Defense.MaxHealth
                local finalHp = math.floor(baseHp * totalHpMult)
                table.insert(buffLines, string.format("  Total Health: %d (base: %d, +%d%%)", finalHp, baseHp, math.floor((totalHpMult - 1.0) * 100)))
            end
            if bestWep then
                if totalDmgMult ~= 1.0 and bestWep.Damage then
                    local baseDmg = bestWep.Damage
                    local finalDmg = math.floor(baseDmg * totalDmgMult)
                    table.insert(buffLines, string.format("  Total Damage: %d (base: %d, +%d%%)", finalDmg, baseDmg, math.floor((totalDmgMult - 1.0) * 100)))
                end
                if totalRngMult ~= 1.0 and bestWep.MaxRadius then
                    local baseRng = bestWep.MaxRadius
                    local finalRng = math.floor(baseRng * totalRngMult)
                    table.insert(buffLines, string.format("  Total Range: %d (base: %d, +%d%%)", finalRng, baseRng, math.floor((totalRngMult - 1.0) * 100)))
                end
            end
            if totalSpdMult ~= 1.0 and bp.Physics and bp.Physics.MaxSpeed then
                local baseSpd = bp.Physics.MaxSpeed
                local finalSpd = baseSpd * totalSpdMult
                table.insert(buffLines, string.format("  Total Speed: %.1f (base: %.1f, +%d%%)", finalSpd, baseSpd, math.floor((totalSpdMult - 1.0) * 100)))
            end
        end

        if table.getn(buffLines) > 1 then
            table.insert(blocks, {{ color = 'FF50F050', lines = buffLines }})
        end
    end

    OldCreateLines(control, blocks)
end

function Show(bp, builderUnit, bpID)
    local id = string.lower(bpID or (bp and bp.BlueprintId) or "")
    local sources = GetActiveBuffSourcesForUnit(bp, id)
    if table.getn(sources) > 0 then
        activeSources = sources
        activeBp = bp
    else
        activeSources = nil
        activeBp = nil
    end

    OldShow(bp, builderUnit, bpID)

    if View and View.HealthStat then
        local isPortraitHover = (builderUnit == nil) or (View.BuildCostGroup and View.BuildCostGroup:IsHidden())
        if isPortraitHover and View.UnitImg then
            LayoutHelpers.RightOf(View.HealthStat, View.UnitImg, 10)
            LayoutHelpers.AtTopIn(View.HealthStat, View.UnitImg, 12)
            if View.ShieldStat then
                LayoutHelpers.Below(View.ShieldStat, View.HealthStat, 2)
                LayoutHelpers.AtLeftIn(View.ShieldStat, View.HealthStat)
            end
        else
            if View.UpkeepGroup and not View.UpkeepGroup:IsHidden() then
                LayoutHelpers.RightOf(View.HealthStat, View.UpkeepGroup, 2)
                LayoutHelpers.AtTopIn(View.HealthStat, View.UpkeepGroup, 22)
                if View.ShieldStat then
                    LayoutHelpers.RightOf(View.ShieldStat, View.UpkeepGroup, -2)
                    LayoutHelpers.AtTopIn(View.ShieldStat, View.UpkeepGroup, 42)
                end
            elseif View.BuildCostGroup and not View.BuildCostGroup:IsHidden() then
                LayoutHelpers.RightOf(View.HealthStat, View.BuildCostGroup, 10)
                LayoutHelpers.AtTopIn(View.HealthStat, View.BuildCostGroup, 22)
                if View.ShieldStat then
                    LayoutHelpers.Below(View.ShieldStat, View.HealthStat, 2)
                    LayoutHelpers.AtLeftIn(View.ShieldStat, View.HealthStat)
                end
            end
        end
    end

    if activeSources and activeBp then
        local totalHpMult = 1.0
        local totalShdMult = 1.0
        for _, s in ipairs(activeSources) do
            if s.cfg.hpMult then totalHpMult = totalHpMult * s.cfg.hpMult end
            if s.cfg.shieldMult then totalShdMult = totalShdMult * s.cfg.shieldMult end
        end
        if totalHpMult ~= 1.0 and activeBp.Defense and activeBp.Defense.MaxHealth then
            local baseHp = activeBp.Defense.MaxHealth
            local buffHp = math.floor(baseHp * totalHpMult)
            if View and View.HealthStat and View.HealthStat.Value then
                View.HealthStat.Value:SetText(string.format("%d (base: %d)", buffHp, baseHp))
                View.HealthStat.Value:SetColor("FF50F050")
            end
        end
        if totalShdMult ~= 1.0 and activeBp.Defense and activeBp.Defense.Shield and activeBp.Defense.Shield.ShieldMaxHealth then
            local baseShield = activeBp.Defense.Shield.ShieldMaxHealth
            local buffShield = math.floor(baseShield * totalShdMult)
            if View and View.ShieldStat and View.ShieldStat.Value then
                View.ShieldStat.Value:SetText(string.format("%d (base: %d)", buffShield, baseShield))
                View.ShieldStat.Value:SetColor("FF50F050")
            end
        end
    else
        if View and View.HealthStat and View.HealthStat.Value then
            View.HealthStat.Value:SetColor("FF00F000")
        end
        if View and View.ShieldStat and View.ShieldStat.Value then
            View.ShieldStat.Value:SetColor("FF00F000")
        end
    end

    activeSources = nil
    activeBp = nil
end
"""


def generate_ui_unitview_lua(unit_table_lua, target_mode, player_name):
    return f"""-- Auto-generated by FAF Mod Forge - Unit View (Rollover) UI Hook
local OldUpdateWindow = UpdateWindow
local UIUtil = import('/lua/ui/uiutil.lua')
local LayoutHelpers = import('/lua/maui/layouthelpers.lua')

local TargetScope = "{target_mode}"
local TargetPlayer = "{player_name}"

local UnitConfigs = {{
{unit_table_lua}
}}

local function MatchesPlayerName(actualName, targetName)
    if not actualName or not targetName or targetName == "" then return false end
    local a = string.lower(actualName)
    local t = string.lower(targetName)
    if a == t then return true end
    if string.find(a, t, 1, true) then return true end
    local stripped = string.gsub(a, "%b[]", "")
    stripped = string.gsub(stripped, "%b()", "")
    stripped = string.gsub(stripped, "^%s*(.-)%s*$", "%1")
    if stripped == t or string.find(stripped, t, 1, true) then return true end
    return false
end

local function IsBuffsActiveForFocusArmy()
    if TargetScope == "global" then return true end
    local focusArmy = GetFocusArmy()
    if not focusArmy or focusArmy < 1 then return true end
    local armies = GetArmiesTable()
    local myName = armies and armies.armiesTable and armies.armiesTable[focusArmy] and armies.armiesTable[focusArmy].nickname
    if myName and MatchesPlayerName(myName, TargetPlayer) then
        return true
    end
    return false
end

local function GetActiveBuffSourcesForUnit(bp, bpId)
    local sources = {{}}
    local id = string.lower(bpId or (bp and bp.BlueprintId) or "")

    if IsBuffsActiveForFocusArmy() and UnitConfigs[id] then
        table.insert(sources, {{
            name = "Base Mod",
            cfg = UnitConfigs[id],
        }})
    end

    local focusArmy = GetFocusArmy()
    if focusArmy and focusArmy > 0 and _G.ModForgeActiveRelics and _G.ModForgeActiveRelics[focusArmy] then
        for rId, rData in pairs(_G.ModForgeActiveRelics[focusArmy]) do
            local matches = false
            if rData.targetType == "unit" then
                if rData.targetUnitId and string.lower(rData.targetUnitId) == id then
                    matches = true
                end
            elseif bp and bp.Categories then
                local cats = {{}}
                for _, c in ipairs(bp.Categories) do cats[c] = true end
                local tName = string.lower(rData.targetCategoryName or rData.targetName or "")
                if rData.id == "preset_center_beacon" or string.find(tName, "t1") then
                    if cats.LAND and cats.TECH1 and (cats.DIRECTFIRE or cats.INDIRECTFIRE or cats.ANTIAIR or cats.ARTILLERY) then
                        matches = true
                    end
                elseif rData.id == "preset_ancient_monolith" or string.find(tName, "commander") then
                    if cats.COMMAND then matches = true end
                elseif rData.id == "preset_quantum_core" or string.find(tName, "experimental") then
                    if cats.EXPERIMENTAL then matches = true end
                elseif rData.id == "preset_supply_cache" or string.find(tName, "artillery") then
                    if cats.ARTILLERY or cats.SILO then matches = true end
                else
                    matches = true
                end
            end

            if matches and rData.buffs then
                table.insert(sources, {{
                    name = tostring(rData.name or "Objective"),
                    cfg = rData.buffs,
                }})
            end
        end
    end

    return sources
end

function UpdateWindow(info)
    OldUpdateWindow(info)
    if not info or not info.blueprintId or not controls.health then return end
    local id = string.lower(info.blueprintId)
    local bp = __blueprints and __blueprints[info.blueprintId]
    local sources = GetActiveBuffSourcesForUnit(bp, id)

    if table.getn(sources) > 0 then
        local totalHpMult = 1.0
        for _, s in ipairs(sources) do
            if s.cfg.hpMult then totalHpMult = totalHpMult * s.cfg.hpMult end
        end
        local baseHp = (bp and bp.Defense and bp.Defense.MaxHealth) or math.floor(info.maxHealth / totalHpMult)
        local regenText = ""
        if info.userUnit then
            local regen = info.userUnit:GetStat("HitpointsRegeneration", 0).Value or 0
            if regen > 0 then
                regenText = string.format(" +%d/s", regen)
            end
        end
        controls.health:SetText(string.format("%d / %d%s (base: %d)", info.health, info.maxHealth, regenText, baseHp))

        if not controls.modForgeBuffText then
            controls.modForgeBuffText = UIUtil.CreateText(controls.bg, '', 9, UIUtil.bodyFont)
            controls.modForgeBuffText:SetColor('FF00E5FF')
            controls.modForgeBuffText:SetDropShadow(true)
            LayoutHelpers.Below(controls.modForgeBuffText, controls.health, 1)
            LayoutHelpers.AtLeftIn(controls.modForgeBuffText, controls.health)
        end

        local sourceNames = {{}}
        for _, s in ipairs(sources) do
            table.insert(sourceNames, s.name)
        end
        controls.modForgeBuffText:SetText("⚡ " .. table.concat(sourceNames, " + "))
        controls.modForgeBuffText:Show()
    else
        if controls.modForgeBuffText then
            controls.modForgeBuffText:Hide()
        end
    end
end
"""


def generate_ui_gamemain_lua(has_lootbox=False, lootbox_model="uec1904", spin_cost_energy=500, observer_gm_name="DrReed", allow_observer_placement=True):
    casino_ui_section = ""
    sync_hashed_casino = ""
    sync_cb_casino = ""

    if has_lootbox:
        target_bp = (lootbox_model or "uec1904").lower()
        cost_txt = f" ({spin_cost_energy}E)" if spin_cost_energy > 0 else ""
        casino_ui_section = f"""
-- --- Surprise Casino Lootbox Selection & Spin UI ---
local casinoPlayBtn = nil
local activeLootboxUnit = nil

local function UpdateCasinoPlayButton()
    local selectedUnits = GetSelectedUnits()
    local validLootbox = nil
    if selectedUnits and table.getn(selectedUnits) == 1 then
        local u = selectedUnits[1]
        local bp = u:GetBlueprint()
        local bpId = bp and bp.BlueprintId and string.lower(bp.BlueprintId)
        local targetBp = "{target_bp}"
        if bpId == targetBp and u:GetArmy() == GetFocusArmy() and not u:IsDead() then
            validLootbox = u
        end
    end

    if validLootbox then
        activeLootboxUnit = validLootbox
        if not casinoPlayBtn then
            local parent = GetFrame(0)
            if not parent then return end
            casinoPlayBtn = UIUtil.CreateButtonStd(parent, '/BUTTON/medium/', "🎰 PLAY CASINO{cost_txt}", 11)
            LayoutHelpers.SetDimensions(casinoPlayBtn, 175, 36)
            LayoutHelpers.AtBottomIn(casinoPlayBtn, parent, 115)
            LayoutHelpers.AtHorizontalCenterIn(casinoPlayBtn, parent)
            casinoPlayBtn.Depth:Set(parent:GetTopmostDepth() + 25)

            casinoPlayBtn.OnClick = function(self)
                if activeLootboxUnit and not activeLootboxUnit:IsDead() then
                    PlaySound(Sound({{Cue = 'UI_Opt_Affirmative', Bank = 'Interface'}}))
                    SimCallback({{
                        Func = 'ModForgeLootboxSpin',
                        Args = {{
                            EntityId = activeLootboxUnit:GetEntityId(),
                            Army = GetFocusArmy()
                        }}
                    }}, true)
                end
            end
        end
        casinoPlayBtn:Show()
    else
        activeLootboxUnit = nil
        if casinoPlayBtn then
            casinoPlayBtn:Hide()
        end
    end
end

ForkThread(function()
    while true do
        pcall(UpdateCasinoPlayButton)
        WaitSeconds(0.25)
    end
end)

local activeCasinoModal = nil

local function ShowCasinoSpinModal(spinData)
    local focusArmy = GetFocusArmy()
    if spinData.army and spinData.army ~= focusArmy then
        return
    end

    local parent = GetFrame(0)
    if not parent then return end

    if activeCasinoModal then
        pcall(function() activeCasinoModal:Destroy() end)
        activeCasinoModal = nil
    end

    local modal = MauiGroup(parent)
    activeCasinoModal = modal
    LayoutHelpers.SetDimensions(modal, 460, 260)
    LayoutHelpers.AtCenterIn(modal, parent)
    modal.Depth:Set(parent:GetTopmostDepth() + 50)

    local bg = MauiBitmap(modal)
    bg:SetSolidColor('F00B0F17')
    LayoutHelpers.FillParent(bg, modal)

    local borderTop = MauiBitmap(modal)
    borderTop:SetSolidColor('FFFFD700')
    LayoutHelpers.SetDimensions(borderTop, 460, 4)
    LayoutHelpers.AtTopIn(borderTop, modal)

    local title = MauiText(modal)
    title:SetFont("Arial Bold", 15)
    title:SetColor('FFFFD700')
    title:SetText("🎰 QUANTUM CASINO VAULT 🎰")
    LayoutHelpers.AtTopIn(title, modal, 14)
    LayoutHelpers.AtHorizontalCenterIn(title, modal)

    local subtitle = MauiText(modal)
    subtitle:SetFont("Arial", 11)
    subtitle:SetColor('FFCBD5E1')
    subtitle:SetText("SPINNING DROP REELS...")
    LayoutHelpers.Below(subtitle, title, 4)
    LayoutHelpers.AtHorizontalCenterIn(subtitle, modal)

    local reelIcons = {{"🌟", "💎", "⚡", "💀", "🪙", "🛡️", "💸", "💥"}}
    local reelTexts = {{}}

    for i = 1, 3 do
        local rBox = MauiGroup(modal)
        LayoutHelpers.SetDimensions(rBox, 90, 85)
        LayoutHelpers.AtTopIn(rBox, modal, 65)
        LayoutHelpers.AtLeftIn(rBox, modal, 40 + (i - 1) * 135)

        local rBg = MauiBitmap(rBox)
        rBg:SetSolidColor('FF16102B')
        LayoutHelpers.FillParent(rBg, rBox)

        local rBorder = MauiBitmap(rBox)
        rBorder:SetSolidColor('FFA855F7')
        LayoutHelpers.SetDimensions(rBorder, 90, 2)
        LayoutHelpers.AtTopIn(rBorder, rBox)

        local rTxt = MauiText(rBox)
        rTxt:SetFont("Arial Bold", 26)
        rTxt:SetColor('FFFFFFFF')
        rTxt:SetText("🎰")
        LayoutHelpers.AtCenterIn(rTxt, rBox)

        table.insert(reelTexts, rTxt)
    end

    local resTitle = MauiText(modal)
    resTitle:SetFont("Arial Bold", 13)
    resTitle:SetColor('FFFFD700')
    resTitle:SetText("")
    LayoutHelpers.AtTopIn(resTitle, modal, 168)
    LayoutHelpers.AtHorizontalCenterIn(resTitle, modal)

    local resDesc = MauiText(modal)
    resDesc:SetFont("Arial", 10)
    resDesc:SetColor('FF94A3B8')
    resDesc:SetText("")
    LayoutHelpers.Below(resDesc, resTitle, 4)
    LayoutHelpers.AtHorizontalCenterIn(resDesc, modal)

    ForkThread(function()
        local outcome = spinData.outcome or {{}}
        local targetReels = outcome.reels or {{"🌟", "🌟", "🌟"}}

        local totalTicks = 20
        for tick = 1, totalTicks do
            if tick <= 8 then
                reelTexts[1]:SetText(reelIcons[math.random(1, table.getn(reelIcons))])
            elseif tick == 9 then
                reelTexts[1]:SetText(targetReels[1] or "🌟")
                pcall(function() PlaySound(Sound({{Cue = 'UI_Opt_Affirmative', Bank = 'Interface'}})) end)
            end

            if tick <= 14 then
                reelTexts[2]:SetText(reelIcons[math.random(1, table.getn(reelIcons))])
            elseif tick == 15 then
                reelTexts[2]:SetText(targetReels[2] or targetReels[1] or "🌟")
                pcall(function() PlaySound(Sound({{Cue = 'UI_Opt_Affirmative', Bank = 'Interface'}})) end)
            end

            if tick < 20 then
                reelTexts[3]:SetText(reelIcons[math.random(1, table.getn(reelIcons))])
            elseif tick == 20 then
                reelTexts[3]:SetText(targetReels[3] or targetReels[1] or "🌟")
                pcall(function() PlaySound(Sound({{Cue = 'UI_Score_Window_Open', Bank = 'Interface'}})) end)
            end

            pcall(function() PlaySound(Sound({{Cue = 'UI_Radar_Blip', Bank = 'Interface'}})) end)
            WaitSeconds(0.1)
        end

        local color = 'FFFFD700'
        if outcome.rarity == 'disaster' then
            color = 'FFEF4444'
        elseif outcome.rarity == 'unlucky' then
            color = 'FFF97316'
        elseif outcome.rarity == 'common' then
            color = 'FF22D3EE'
        end

        subtitle:SetText("🎉 SPIN COMPLETE!")
        resTitle:SetColor(color)
        resTitle:SetText(tostring(outcome.name or "Prize Unlocked!"))
        resDesc:SetText(tostring(outcome.desc or ""))

        WaitSeconds(4.5)
        pcall(function()
            if activeCasinoModal == modal then
                modal:Destroy()
                activeCasinoModal = nil
            end
        end)
    end)
end

local function HandleModForgeCasinoSpin(data)
    if not data or table.getn(data) == 0 then return end
    for _, spinData in ipairs(data) do
        ShowCasinoSpinModal(spinData)
    end
end
"""
        if allow_observer_placement:
            obs_name_clean = (observer_gm_name or "DrReed").replace('"', '\\"')
            casino_ui_section += f"""
-- --- Observer Game Master ({obs_name_clean}) In-Game Placement Tool ---
local observerGmBtn = nil
local activeGmWindow = nil

local function IsObserverAuthorized()
    local focusArmy = GetFocusArmy()
    if focusArmy ~= -1 then return false end
    local targetName = string.lower("{obs_name_clean}")
    if targetName == "all" then return true end

    local clients = GetSessionClients()
    if clients then
        for _, c in clients do
            if c.local then
                local myName = string.lower(c.name or "")
                if myName == targetName or string.find(myName, targetName, 1, true) then
                    return true
                end
            end
        end
    end
    return false
end

local function ToggleObserverGmWindow()
    if activeGmWindow then
        activeGmWindow:Destroy()
        activeGmWindow = nil
        return
    end

    local parent = GetFrame(0)
    if not parent then return end

    local w = MauiGroup(parent)
    activeGmWindow = w
    LayoutHelpers.SetDimensions(w, 290, 260)
    LayoutHelpers.AtTopIn(w, parent, 50)
    LayoutHelpers.AtRightIn(w, parent, 20)
    w.Depth:Set(parent:GetTopmostDepth() + 60)

    local bg = MauiBitmap(w)
    bg:SetSolidColor('F00F172A')
    LayoutHelpers.FillParent(bg, w)

    local borderTop = MauiBitmap(w)
    borderTop:SetSolidColor('FF38BDF8')
    LayoutHelpers.SetDimensions(borderTop, 290, 3)
    LayoutHelpers.AtTopIn(borderTop, w)

    local title = MauiText(w)
    title:SetFont("Arial Bold", 12)
    title:SetColor('FF38BDF8')
    title:SetText("📦 GM LOOTBOX SEEDER ({obs_name_clean})")
    LayoutHelpers.AtTopIn(title, w, 10)
    LayoutHelpers.AtHorizontalCenterIn(title, w)

    local sub = MauiText(w)
    sub:SetFont("Arial", 9)
    sub:SetColor('FF94A3B8')
    sub:SetText("Choose seed & drop at cursor / map center:")
    LayoutHelpers.Below(sub, title, 4)
    LayoutHelpers.AtHorizontalCenterIn(sub, w)

    local presets = {{
        {{ key = "prototype", name = "🏆 Experimental Prototype", col = "FF38BDF8" }},
        {{ key = "swarm", name = "🦖 Raptor Swarm Bio-Pod", col = "FF34D399" }},
        {{ key = "supply", name = "📦 Tactical Vanguard Armor", col = "FF60A5FA" }},
        {{ key = "motherlode", name = "💎 Resource Motherlode", col = "FFF59E0B" }},
        {{ key = "casino", name = "🎰 Interactive Casino", col = "FFFFD700" }},
    }}

    for i, p in ipairs(presets) do
        local btn = UIUtil.CreateButtonStd(w, '/BUTTON/medium/', p.name, 9)
        LayoutHelpers.SetDimensions(btn, 255, 26)
        LayoutHelpers.AtTopIn(btn, w, 44 + (i - 1) * 32)
        LayoutHelpers.AtHorizontalCenterIn(btn, w)

        btn.OnClick = function(self)
            local pos = GetMouseWorldPos()
            if not pos then return end
            SimCallback({{
                Func = 'ModForgeAdminPlaceLootbox',
                Args = {{
                    Pos = {{ pos[1], pos[2], pos[3] }},
                    Preset = p.key,
                }}
            }}, true)
            pcall(function() PlaySound(Sound({{Cue = 'UI_Opt_Affirmative', Bank = 'Interface'}})) end)
            PrintText("📦 Dropped " .. p.name .. " at cursor position!", 14, p.col, 3, "center")
        end
    end

    local closeBtn = UIUtil.CreateButtonStd(w, '/BUTTON/medium/', "CLOSE", 9)
    LayoutHelpers.SetDimensions(closeBtn, 100, 22)
    LayoutHelpers.AtBottomIn(closeBtn, w, 8)
    LayoutHelpers.AtHorizontalCenterIn(closeBtn, w)
    closeBtn.OnClick = function(self)
        if activeGmWindow then
            activeGmWindow:Destroy()
            activeGmWindow = nil
        end
    end
end

local function UpdateObserverGmButton()
    local isAuthorized = IsObserverAuthorized()
    if isAuthorized then
        if not observerGmBtn then
            local parent = GetFrame(0)
            if not parent then return end
            observerGmBtn = UIUtil.CreateButtonStd(parent, '/BUTTON/medium/', "📦 GM LOOTBOX", 10)
            LayoutHelpers.SetDimensions(observerGmBtn, 140, 28)
            LayoutHelpers.AtTopIn(observerGmBtn, parent, 12)
            LayoutHelpers.AtRightIn(observerGmBtn, parent, 280)
            observerGmBtn.Depth:Set(parent:GetTopmostDepth() + 40)
            observerGmBtn.OnClick = function(self)
                ToggleObserverGmWindow()
            end
        end
        observerGmBtn:Show()
    else
        if observerGmBtn then
            observerGmBtn:Hide()
        end
        if activeGmWindow then
            activeGmWindow:Destroy()
            activeGmWindow = nil
        end
    end
end

ForkThread(function()
    while true do
        pcall(UpdateObserverGmButton)
        WaitSeconds(1.0)
    end
end)
"""
        sync_hashed_casino = "    AddOnSyncHashedCallback(HandleModForgeCasinoSpin, 'ModForgeCasinoSpin', 'ModForgeCasinoSpinUI')\n"
        sync_cb_casino = """        if syncTable and syncTable.ModForgeCasinoSpin then
            HandleModForgeCasinoSpin(syncTable.ModForgeCasinoSpin)
        end
"""

    return f"""-- Auto-generated by FAF Mod Forge - Tactical Event Popups UI Handler
local UIUtil = import('/lua/ui/uiutil.lua')
local LayoutHelpers = import('/lua/maui/layouthelpers.lua')
local MauiGroup = import('/lua/maui/group.lua').Group
local MauiBitmap = import('/lua/maui/bitmap.lua').Bitmap
local MauiButton = import('/lua/maui/button.lua').Button
local MauiText = import('/lua/maui/text.lua').Text

local function CleanText(s)
    if not s then return "" end
    if LOC then
        s = LOC(tostring(s))
    end
    local res, _ = string.gsub(tostring(s), "<LOC [^>]*>", "")
    return tostring(res)
end

local function MatchesPlayerName(actualName, targetName)
    if not actualName or not targetName or targetName == "" then return false end
    local a = string.lower(actualName)
    local t = string.lower(targetName)
    if a == t then return true end
    if string.find(a, t, 1, true) then return true end
    local stripped = string.gsub(a, "%b[]", "")
    stripped = string.gsub(stripped, "%b()", "")
    stripped = string.gsub(stripped, "^%s*(.-)%s*$", "%1")
    if stripped == t or string.find(stripped, t, 1, true) then return true end
    return false
end

local activeAlertCards = {{}}

local function ShowTacticalPopup(data)
    local focusArmy = GetFocusArmy()
    if data.targetScope == "player" and data.targetPlayer and data.targetPlayer ~= "" then
        local armies = GetArmiesTable()
        local myName = armies and armies.armiesTable and armies.armiesTable[focusArmy] and armies.armiesTable[focusArmy].nickname
        if myName and not MatchesPlayerName(myName, data.targetPlayer) then
            return
        end
    end

    local parent = GetFrame(0)
    if not parent then return end

    local card = MauiGroup(parent)
    local function DismissAlert()
        for idx, c in ipairs(activeAlertCards) do
            if c == card then
                table.remove(activeAlertCards, idx)
                break
            end
        end
        pcall(function() card:Destroy() end)
    end

    local ok, err = pcall(function()
        LayoutHelpers.SetDimensions(card, 420, 125)
        LayoutHelpers.AtTopIn(card, parent, 115 + (table.getn(activeAlertCards) * 132))
        LayoutHelpers.AtHorizontalCenterIn(card, parent)
        card.Depth:Set(GetFrame(0):GetTopmostDepth() + 10)

        local bg = MauiBitmap(card)
        bg:SetSolidColor('F00B0F17')
        LayoutHelpers.FillParent(bg, card)
        bg:DisableHitTest(true)

        local themeColor = 'FF00D2FF'
        if data.theme == "danger" then
            themeColor = 'FFEF4444'
        elseif data.theme == "tactical" then
            themeColor = 'FFF59E0B'
        elseif data.theme == "ally" then
            themeColor = 'FF10B981'
        elseif data.theme == "quantum" then
            themeColor = 'FFA855F7'
        end

        local topBorder = MauiBitmap(card)
        topBorder:SetSolidColor(themeColor)
        LayoutHelpers.SetDimensions(topBorder, 420, 3)
        LayoutHelpers.AtTopIn(topBorder, card)
        topBorder:DisableHitTest(true)

        local title = MauiText(card)
        title:SetFont("Arial Bold", 13)
        title:SetColor('FFFFFFFF')
        title:SetText(CleanText(data.title or "TACTICAL ALERT"))
        LayoutHelpers.AtTopIn(title, card, 12)
        LayoutHelpers.AtHorizontalCenterIn(title, card)
        title:DisableHitTest(true)

        local msg = MauiText(card)
        msg:SetFont("Arial", 11)
        msg:SetColor('FFCBD5E1')
        msg:SetText(CleanText(data.text or ""))
        LayoutHelpers.Below(msg, title, 8)
        LayoutHelpers.AtHorizontalCenterIn(msg, card)
        msg:DisableHitTest(true)

        local btnRow = MauiGroup(card)
        LayoutHelpers.SetDimensions(btnRow, 380, 44)
        LayoutHelpers.AtBottomIn(btnRow, card, 8)
        LayoutHelpers.AtHorizontalCenterIn(btnRow, card)
        btnRow.Depth:Set(card.Depth() + 10)

        if data.hasPinpoint and data.pos then
            local pinBtn = UIUtil.CreateButtonStd(btnRow, '/BUTTON/medium/', "Pinpoint", 11)
            pinBtn.Depth:Set(btnRow.Depth() + 2)
            LayoutHelpers.AtLeftIn(pinBtn, btnRow, 20)
            LayoutHelpers.AtVerticalCenterIn(pinBtn, btnRow)

            pinBtn.OnClick = function(self)
                local cam = GetCamera("WorldCamera")
                if cam then
                    pcall(function()
                        local pos = Vector(data.pos[1], data.pos[2], data.pos[3])
                        local settings = cam:SaveSettings()
                        local hpr = (settings and {{ settings.Heading or 0, settings.Pitch or 1.28, 0 }}) or {{ 0, 1.28, 0 }}
                        local zoom = (settings and settings.Zoom) or 80
                        if zoom > 140 then zoom = 90 end
                        if zoom < 40 then zoom = 60 end
                        cam:MoveTo(pos, hpr, zoom, 0.5)
                    end)
                end
                if data.hasPing then
                    pcall(function()
                        local focusArmy = GetFocusArmy()
                        local owner = (focusArmy and focusArmy > 0) and (focusArmy - 1) or 0
                        local pos = Vector(data.pos[1], data.pos[2], data.pos[3])
                        local pingData = {{
                            Owner = owner,
                            Type = 'alert',
                            Location = pos,
                        }}
                        local Ping = import('/lua/ui/game/ping.lua')
                        if Ping and Ping.PingTypes and Ping.PingTypes['alert'] then
                            pingData = table.merged(pingData, Ping.PingTypes['alert'])
                        end
                        SimCallback({{ Func = 'SpawnPing', Args = pingData }})
                    end)
                end
                DismissAlert()
            end
        end

        if data.hasDismiss ~= false then
            local disBtn = UIUtil.CreateButtonStd(btnRow, '/BUTTON/medium/', "Dismiss", 11)
            disBtn.Depth:Set(btnRow.Depth() + 2)
            LayoutHelpers.AtRightIn(disBtn, btnRow, 20)
            LayoutHelpers.AtVerticalCenterIn(disBtn, btnRow)

            disBtn.OnClick = function(self)
                DismissAlert()
            end
        end

        if data.sound and data.sound ~= "None" then
            pcall(function()
                PlaySound(Sound({{Cue = data.sound, Bank = 'Interface'}}))
            end)
        end

        local sec = data.duration or 8
        if sec > 0 then
            ForkThread(function()
                WaitSeconds(sec)
                DismissAlert()
            end)
        end

        table.insert(activeAlertCards, card)
    end)

    if not ok then
        WARN("ShowTacticalPopup error: " .. tostring(err))
        DismissAlert()
    end
end

-- Register sync callback using FAF standard UserSync API
local function HandleModForgePopups(data)
    if not data or table.getn(data) == 0 then return end
    for _, alertData in ipairs(data) do
        ShowTacticalPopup(alertData)
    end
end

local function HandleModForgeRelics(data)
    if not data or table.getn(data) == 0 then return end
    _G.ModForgeActiveRelics = _G.ModForgeActiveRelics or {{}}
    for _, item in ipairs(data) do
        local army = item.army
        if item.action == "claim" then
            _G.ModForgeActiveRelics[army] = _G.ModForgeActiveRelics[army] or {{}}
            _G.ModForgeActiveRelics[army][item.id] = item
        elseif item.action == "expire" then
            if _G.ModForgeActiveRelics[army] then
                _G.ModForgeActiveRelics[army][item.id] = nil
            end
        end
    end
end
{casino_ui_section}
if AddOnSyncHashedCallback then
    AddOnSyncHashedCallback(HandleModForgePopups, 'ModForgePopups', 'ModForgePopupsUI')
    AddOnSyncHashedCallback(HandleModForgeRelics, 'ModForgeRelics', 'ModForgeRelicsUI')
{sync_hashed_casino}elseif AddOnSyncCallback then
    AddOnSyncCallback(function(syncTable)
        if syncTable and syncTable.ModForgePopups then
            HandleModForgePopups(syncTable.ModForgePopups)
        end
        if syncTable and syncTable.ModForgeRelics then
            HandleModForgeRelics(syncTable.ModForgeRelics)
        end
{sync_cb_casino}    end, 'ModForgeSync')
end
"""


def generate_mod_files(data):
    mod_name = data.get("modName", "").strip() or "Custom Buff Mod"
    author = data.get("author", "").strip() or "FAF Player"
    version = int(data.get("version", 1))
    target_mode = data.get("targetMode", "player")  # "player" or "global"
    player_name = data.get("playerName", "").strip()
    
    # Unit configs map: unitId -> { hpMult, massDiscount, energyDiscount, speedMult, damageMult, buildRateMult }
    unit_configs = data.get("unitConfigs", {})
    if not unit_configs:
        # Fallback to legacy flat list if provided
        fallback_units = data.get("units", [])
        fallback_cfg = {
            "hpMult": float(data.get("hpMult", 1.0)),
            "massDiscount": float(data.get("massDiscount", 0.0)) / 100.0,
            "energyDiscount": float(data.get("energyDiscount", 0.0)) / 100.0,
            "buildRateMult": float(data.get("buildRateMult", 1.0)),
            "speedMult": 1.0,
            "damageMult": 1.0,
        }
        unit_configs = {uid: fallback_cfg for uid in fallback_units}

    mod_uid = str(uuid.uuid4())
    safe_folder_name = "".join(c for c in mod_name if c.isalnum() or c in (" ", "-", "_")).strip()
    
    target_mod_dir = DOCUMENTS_MODS_DIR / safe_folder_name
    if target_mod_dir.exists():
        shutil.rmtree(target_mod_dir)
    target_mod_dir.mkdir(parents=True, exist_ok=True)

    # 1. mod_info.lua
    description_text = f"Modifies stats for {len(unit_configs)} units. "
    if target_mode == "player":
        description_text += f"Target player: {player_name} (Sim Hook)."
    else:
        description_text += "Global Blueprint modifications for all players."

    mod_info_content = f"""name = "{mod_name}"
version = {version}
copyright = "none"
description = "{description_text}"
author = "{author}"
uid = "{mod_uid}"
exclusive = false
ui_only = false
selectable = true
enabled = true
"""
    with open(target_mod_dir / "mod_info.lua", "w", encoding="utf-8") as f:
        f.write(mod_info_content)

    # Build Lua table of unit configs
    lua_entries = []
    for uid, cfg in unit_configs.items():
        hp_m = round(float(cfg.get("hpMult", 1.0)), 2)
        regen_m = round(float(cfg.get("regenMult", 1.0)), 2)
        shield_m = round(float(cfg.get("shieldMult", 1.0)), 2)
        shield_regen_m = round(float(cfg.get("shieldRegenMult", 1.0)), 2)

        md = float(cfg.get("massDiscount", 0.0))
        if md > 1.0:
            md = md / 100.0
        md = round(md, 2)

        ed = float(cfg.get("energyDiscount", 0.0))
        if ed > 1.0:
            ed = ed / 100.0
        ed = round(ed, 2)

        btd = float(cfg.get("buildTimeDiscount", 0.0))
        if btd > 1.0:
            btd = btd / 100.0
        btd = round(btd, 2)

        brm = round(float(cfg.get("buildRateMult", 1.0)), 2)
        prod_m = round(float(cfg.get("prodMult", 1.0)), 2)

        sm = round(float(cfg.get("speedMult", 1.0)), 2)
        trm = round(float(cfg.get("turnRateMult", 1.0)), 2)
        vm = round(float(cfg.get("visionMult", 1.0)), 2)
        rm = round(float(cfg.get("radarMult", 1.0)), 2)

        dm = round(float(cfg.get("damageMult", 1.0)), 2)
        range_m = round(float(cfg.get("rangeMult", 1.0)), 2)
        rof_m = round(float(cfg.get("rofMult", 1.0)), 2)
        aoe_m = round(float(cfg.get("aoeMult", 1.0)), 2)
        mv_m = round(float(cfg.get("muzzleVelMult", 1.0)), 2)

        entry = (
            f'    ["{uid.lower()}"] = {{ '
            f'hpMult = {hp_m}, regenMult = {regen_m}, shieldMult = {shield_m}, shieldRegenMult = {shield_regen_m}, '
            f'massDiscount = {md}, energyDiscount = {ed}, buildTimeDiscount = {btd}, buildRateMult = {brm}, prodMult = {prod_m}, '
            f'speedMult = {sm}, turnRateMult = {trm}, visionMult = {vm}, radarMult = {rm}, '
            f'damageMult = {dm}, rangeMult = {range_m}, rofMult = {rof_m}, aoeMult = {aoe_m}, muzzleVelMult = {mv_m} }}'
        )
        lua_entries.append(entry)

    unit_table_lua = ",\n".join(lua_entries)

    # 2. Hook generation
    if target_mode == "player":
        # Sim hook on Unit.lua
        hook_dir = target_mod_dir / "hook" / "lua" / "sim"
        hook_dir.mkdir(parents=True, exist_ok=True)

        unit_lua_content = f"""-- Auto-generated by FAF Mod Forge
-- Target player: {player_name}
-- Units configured: {len(unit_configs)}

local UnitConfigs = {{
{unit_table_lua}
}}

local TargetPlayer = "{player_name}"

local function MatchesPlayerName(actualName, targetName)
    if not actualName or not targetName or targetName == "" then return false end
    local a = string.lower(actualName)
    local t = string.lower(targetName)
    if a == t then return true end
    if string.find(a, t, 1, true) then return true end
    local stripped = string.gsub(a, "%b[]", "")
    stripped = string.gsub(stripped, "%b()", "")
    stripped = string.gsub(stripped, "^%s*(.-)%s*$", "%1")
    if stripped == t or string.find(stripped, t, 1, true) then return true end
    return false
end

local function IsTargetArmy(armyIndex)
    if not armyIndex or armyIndex < 1 then return false end
    local setup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[armyIndex]
    if setup and setup.PlayerName and MatchesPlayerName(setup.PlayerName, TargetPlayer) then
        return true
    end
    local brain = ArmyBrains and ArmyBrains[armyIndex]
    if brain and brain.Nickname and MatchesPlayerName(brain.Nickname, TargetPlayer) then
        return true
    end
    local focus = GetFocusArmy()
    if focus and focus == armyIndex then
        return true
    end
    return false
end

local OldUnit = Unit
Unit = Class(OldUnit) {{

    OnStopBeingBuilt = function(self, builder, layer)
        local result = OldUnit.OnStopBeingBuilt(self, builder, layer)

        local army = self:GetArmy()

        -- Verify if this unit belongs to the targeted player
        if IsTargetArmy(army) then
            local bp = self:GetBlueprint()
            local bpId = string.lower(bp.BlueprintId or self:GetUnitId() or "")
            local cfg = UnitConfigs[bpId]

            if cfg then
                -- 1. HP Multiplier (applied as Buff to survive veterancy recalculations)
                if cfg.hpMult and cfg.hpMult ~= 1.0 then
                    local buffName = 'ForgeOverhaul_Health_' .. bpId
                    if not Buffs[buffName] then
                        BuffBlueprint {{
                            Name = buffName,
                            DisplayName = buffName,
                            BuffType = 'FORGEOVERHAUL_HEALTH',
                            Stacks = 'REPLACE',
                            Duration = -1,
                            Affects = {{
                                MaxHealth = {{
                                    Add = 0,
                                    Mult = cfg.hpMult,
                                    DoNotFill = false,
                                }},
                            }},
                        }}
                    end
                    import('/lua/sim/buff.lua').ApplyBuff(self, buffName)
                    local newMax = self:GetMaxHealth()
                    self:SetHealth(self, newMax)
                end

                -- 2. Health Regen Multiplier
                if cfg.regenMult and cfg.regenMult ~= 1.0 then
                    self.ForgeOverhaulRegenMult = cfg.regenMult
                    local curRegen = (bp.Defense and bp.Defense.RegenRate) or 0
                    if curRegen == 0 then curRegen = 5 end
                    if self.SetRegenRate then
                        self:SetRegenRate(curRegen * cfg.regenMult)
                    end
                end

                -- 3. Shield Multipliers
                if self.MyShield then
                    if cfg.shieldMult and cfg.shieldMult ~= 1.0 then
                        local curShieldMax = self.MyShield:GetMaxHealth()
                        local newShieldMax = math.floor(curShieldMax * cfg.shieldMult)
                        self.MyShield:SetMaxHealth(newShieldMax)
                        self.MyShield:SetHealth(self.MyShield, newShieldMax)
                    end
                end

                -- 4. Cost Discount (Resource Refund)
                if bp.Economy then
                    local brain = self:GetAIBrain()
                    if cfg.massDiscount and cfg.massDiscount > 0 and bp.Economy.BuildCostMass then
                        local refundMass = math.floor(bp.Economy.BuildCostMass * cfg.massDiscount)
                        if refundMass > 0 then
                            brain:GiveResource('Mass', refundMass)
                        end
                    end
                    if cfg.energyDiscount and cfg.energyDiscount > 0 and bp.Economy.BuildCostEnergy then
                        local refundEnergy = math.floor(bp.Economy.BuildCostEnergy * cfg.energyDiscount)
                        if refundEnergy > 0 then
                            brain:GiveResource('Energy', refundEnergy)
                        end
                    end
                end

                -- 5. Resource Production Multiplier
                if cfg.prodMult and cfg.prodMult ~= 1.0 and bp.Economy then
                    if bp.Economy.ProductionPerSecondEnergy and bp.Economy.ProductionPerSecondEnergy > 0 and self.SetProductionPerSecondEnergy then
                        self:SetProductionPerSecondEnergy(math.floor(bp.Economy.ProductionPerSecondEnergy * cfg.prodMult))
                    end
                    if bp.Economy.ProductionPerSecondMass and bp.Economy.ProductionPerSecondMass > 0 and self.SetProductionPerSecondMass then
                        self:SetProductionPerSecondMass(math.floor(bp.Economy.ProductionPerSecondMass * cfg.prodMult))
                    end
                end

                -- 6. Build Rate Multiplier (factories & engineers)
                if cfg.buildRateMult and cfg.buildRateMult ~= 1.0 and self:GetBuildRate() > 0 then
                    self:SetBuildRate(self:GetBuildRate() * cfg.buildRateMult)
                end

                -- 7. Movement & Turn Speed Multipliers
                if cfg.speedMult and cfg.speedMult ~= 1.0 and self.SetSpeedMult then
                    self:SetSpeedMult(cfg.speedMult)
                    if self.SetAccMult then
                        self:SetAccMult(cfg.speedMult)
                    end
                end
                if cfg.turnRateMult and cfg.turnRateMult ~= 1.0 and self.SetTurnMult then
                    self:SetTurnMult(cfg.turnRateMult)
                end

                -- 8. Vision & Radar Intel Multipliers
                if self.SetIntelRadius then
                    if cfg.visionMult and cfg.visionMult ~= 1.0 and bp.Intel and bp.Intel.VisionRadius then
                        self:SetIntelRadius('Vision', math.floor(bp.Intel.VisionRadius * cfg.visionMult))
                        if bp.Intel.WaterVisionRadius then
                            self:SetIntelRadius('WaterVision', math.floor(bp.Intel.WaterVisionRadius * cfg.visionMult))
                        end
                    end
                    if cfg.radarMult and cfg.radarMult ~= 1.0 and bp.Intel then
                        if bp.Intel.RadarRadius and bp.Intel.RadarRadius > 0 then
                            self:SetIntelRadius('Radar', math.floor(bp.Intel.RadarRadius * cfg.radarMult))
                        end
                        if bp.Intel.SonarRadius and bp.Intel.SonarRadius > 0 then
                            self:SetIntelRadius('Sonar', math.floor(bp.Intel.SonarRadius * cfg.radarMult))
                        end
                        if bp.Intel.OmniRadius and bp.Intel.OmniRadius > 0 then
                            self:SetIntelRadius('Omni', math.floor(bp.Intel.OmniRadius * cfg.radarMult))
                        end
                    end
                end

                -- 9. Weapon Multipliers (Damage, Range, RoF, Splash)
                if cfg.damageMult and cfg.damageMult ~= 1.0 then
                    self.CustomDmgMult = cfg.damageMult
                end

                local wCount = self:GetWeaponCount()
                if wCount and wCount > 0 then
                    for i = 1, wCount do
                        local wep = self:GetWeapon(i)
                        if wep then
                            local wbp = wep:GetBlueprint()
                            if cfg.rangeMult and cfg.rangeMult ~= 1.0 and wbp and wbp.MaxRadius and wep.ChangeMaxRadius then
                                wep:ChangeMaxRadius(math.floor(wbp.MaxRadius * cfg.rangeMult))
                            end
                            if cfg.rofMult and cfg.rofMult ~= 1.0 and wbp and wbp.RateOfFire and wep.SetRateOfFire then
                                wep:SetRateOfFire(wbp.RateOfFire * cfg.rofMult)
                            end
                            if cfg.aoeMult and cfg.aoeMult ~= 1.0 and wbp and wbp.DamageRadius then
                                wep.DamageRadius = wbp.DamageRadius * cfg.aoeMult
                            end
                        end
                    end
                end
            end
        end
        return result
    end,

    -- Hook OnDamage to apply weapon damage multiplier when attacking
    OnDamage = function(self, instigator, amount, vector, damageType)
        local amt = amount
        if instigator and instigator.CustomDmgMult and amount and amount > 0 then
            amt = amount * instigator.CustomDmgMult
        end
        return OldUnit.OnDamage(self, instigator, amt, vector, damageType)
    end,
}}

local OldSetRegen = Unit.SetRegen
if OldSetRegen then
    Unit.SetRegen = function(self, value)
        if self.ForgeOverhaulRegenMult and self.ForgeOverhaulRegenMult ~= 1.0 then
            value = value * self.ForgeOverhaulRegenMult
        end
        return OldSetRegen(self, value)
    end
end
"""
        with open(hook_dir / "Unit.lua", "w", encoding="utf-8") as f:
            f.write(unit_lua_content)

    else:
        # Global Blueprint mod on Blueprints.lua
        hook_dir = target_mod_dir / "hook" / "lua" / "system"
        hook_dir.mkdir(parents=True, exist_ok=True)

        bp_lua_content = f"""-- Auto-generated by FAF Mod Forge
-- Global Blueprint modifications for all players
-- Units configured: {len(unit_configs)}

local UnitConfigs = {{
{unit_table_lua}
}}

local OldModBlueprints = ModBlueprints

function ModBlueprints(all_blueprints)
    OldModBlueprints(all_blueprints)

    for id, bp in all_blueprints.Unit do
        local lowerId = string.lower(id)
        local cfg = UnitConfigs[lowerId]

        if cfg then
            -- 1. HP, Regen & Shields
            if bp.Defense then
                if cfg.hpMult and cfg.hpMult ~= 1.0 and bp.Defense.MaxHealth then
                    bp.Defense.MaxHealth = math.floor(bp.Defense.MaxHealth * cfg.hpMult)
                    bp.Defense.Health = math.floor((bp.Defense.Health or bp.Defense.MaxHealth) * cfg.hpMult)
                end
                if cfg.regenMult and cfg.regenMult ~= 1.0 then
                    local baseRegen = bp.Defense.RegenRate or 0
                    if baseRegen == 0 then baseRegen = 5 end
                    bp.Defense.RegenRate = math.floor(baseRegen * cfg.regenMult)
                end
                if bp.Defense.Shield then
                    if cfg.shieldMult and cfg.shieldMult ~= 1.0 and bp.Defense.Shield.ShieldMaxHealth then
                        bp.Defense.Shield.ShieldMaxHealth = math.floor(bp.Defense.Shield.ShieldMaxHealth * cfg.shieldMult)
                    end
                    if cfg.shieldRegenMult and cfg.shieldRegenMult ~= 1.0 and bp.Defense.Shield.ShieldRegenRate then
                        bp.Defense.Shield.ShieldRegenRate = math.floor(bp.Defense.Shield.ShieldRegenRate * cfg.shieldRegenMult)
                    end
                end
            end

            -- 2. Economy & Build Time
            if bp.Economy then
                if cfg.massDiscount and cfg.massDiscount > 0 and bp.Economy.BuildCostMass then
                    bp.Economy.BuildCostMass = math.floor(bp.Economy.BuildCostMass * (1.0 - cfg.massDiscount))
                end
                if cfg.energyDiscount and cfg.energyDiscount > 0 and bp.Economy.BuildCostEnergy then
                    bp.Economy.BuildCostEnergy = math.floor(bp.Economy.BuildCostEnergy * (1.0 - cfg.energyDiscount))
                end
                if cfg.buildTimeDiscount and cfg.buildTimeDiscount > 0 and bp.Economy.BuildTime then
                    bp.Economy.BuildTime = math.floor(bp.Economy.BuildTime * (1.0 - cfg.buildTimeDiscount))
                end
                if cfg.buildRateMult and cfg.buildRateMult ~= 1.0 and bp.Economy.BuildRate then
                    bp.Economy.BuildRate = math.floor(bp.Economy.BuildRate * cfg.buildRateMult)
                end
                if cfg.prodMult and cfg.prodMult ~= 1.0 then
                    if bp.Economy.ProductionPerSecondMass and bp.Economy.ProductionPerSecondMass > 0 then
                        bp.Economy.ProductionPerSecondMass = math.floor(bp.Economy.ProductionPerSecondMass * cfg.prodMult)
                    end
                    if bp.Economy.ProductionPerSecondEnergy and bp.Economy.ProductionPerSecondEnergy > 0 then
                        bp.Economy.ProductionPerSecondEnergy = math.floor(bp.Economy.ProductionPerSecondEnergy * cfg.prodMult)
                    end
                end
            end

            -- 3. Movement & Turn Speed
            if bp.Physics then
                if cfg.speedMult and cfg.speedMult ~= 1.0 and bp.Physics.MaxSpeed then
                    bp.Physics.MaxSpeed = bp.Physics.MaxSpeed * cfg.speedMult
                    if bp.Physics.MaxAcceleration then
                        bp.Physics.MaxAcceleration = bp.Physics.MaxAcceleration * cfg.speedMult
                    end
                    if bp.Physics.MaxBrake then
                        bp.Physics.MaxBrake = bp.Physics.MaxBrake * cfg.speedMult
                    end
                end
                if cfg.turnRateMult and cfg.turnRateMult ~= 1.0 and bp.Physics.TurnRate then
                    bp.Physics.TurnRate = math.floor(bp.Physics.TurnRate * cfg.turnRateMult)
                end
            end

            -- 4. Intel (Vision, Radar, Sonar, Omni)
            if bp.Intel then
                if cfg.visionMult and cfg.visionMult ~= 1.0 and bp.Intel.VisionRadius then
                    bp.Intel.VisionRadius = math.floor(bp.Intel.VisionRadius * cfg.visionMult)
                    if bp.Intel.WaterVisionRadius then
                        bp.Intel.WaterVisionRadius = math.floor(bp.Intel.WaterVisionRadius * cfg.visionMult)
                    end
                end
                if cfg.radarMult and cfg.radarMult ~= 1.0 then
                    if bp.Intel.RadarRadius and bp.Intel.RadarRadius > 0 then
                        bp.Intel.RadarRadius = math.floor(bp.Intel.RadarRadius * cfg.radarMult)
                    end
                    if bp.Intel.SonarRadius and bp.Intel.SonarRadius > 0 then
                        bp.Intel.SonarRadius = math.floor(bp.Intel.SonarRadius * cfg.radarMult)
                    end
                    if bp.Intel.OmniRadius and bp.Intel.OmniRadius > 0 then
                        bp.Intel.OmniRadius = math.floor(bp.Intel.OmniRadius * cfg.radarMult)
                    end
                end
            end

            -- 5. Weapons (Damage, Range, RoF, Splash, Projectile Speed)
            if bp.Weapon then
                for _, w in bp.Weapon do
                    local isDeath = (w.WeaponCategory == "Death" or w.DamageType == "DeathExplosion" or w.DamageType == "Deathnuke")

                    if not isDeath then
                        if cfg.damageMult and cfg.damageMult ~= 1.0 and w.Damage and w.Damage > 0 then
                            w.Damage = math.floor(w.Damage * cfg.damageMult)
                        end
                        if cfg.rangeMult and cfg.rangeMult ~= 1.0 and w.MaxRadius and w.MaxRadius > 0 then
                            w.MaxRadius = math.floor(w.MaxRadius * cfg.rangeMult)
                        end
                        if cfg.rofMult and cfg.rofMult ~= 1.0 and w.RateOfFire and w.RateOfFire > 0 then
                            w.RateOfFire = w.RateOfFire * cfg.rofMult
                            if w.MuzzleSalvoDelay and w.MuzzleSalvoDelay > 0 then
                                w.MuzzleSalvoDelay = w.MuzzleSalvoDelay / cfg.rofMult
                            end
                            if w.RackSalvoReloadTime and w.RackSalvoReloadTime > 0 then
                                w.RackSalvoReloadTime = w.RackSalvoReloadTime / cfg.rofMult
                            end
                        end
                        if cfg.aoeMult and cfg.aoeMult ~= 1.0 and w.DamageRadius and w.DamageRadius > 0 then
                            w.DamageRadius = w.DamageRadius * cfg.aoeMult
                        end
                        if cfg.muzzleVelMult and cfg.muzzleVelMult ~= 1.0 and w.MuzzleVelocity and w.MuzzleVelocity > 0 then
                            w.MuzzleVelocity = math.floor(w.MuzzleVelocity * cfg.muzzleVelMult)
                        end
                    end

                    -- Strategic nukes
                    if cfg.damageMult and cfg.damageMult ~= 1.0 then
                        if w.NukeInnerRingDamage and w.NukeInnerRingDamage > 0 then
                            w.NukeInnerRingDamage = math.floor(w.NukeInnerRingDamage * cfg.damageMult)
                        end
                        if w.NukeOuterRingDamage and w.NukeOuterRingDamage > 0 then
                            w.NukeOuterRingDamage = math.floor(w.NukeOuterRingDamage * cfg.damageMult)
                        end
                    end
                    if cfg.aoeMult and cfg.aoeMult ~= 1.0 then
                        if w.NukeInnerRingRadius and w.NukeInnerRingRadius > 0 then
                            w.NukeInnerRingRadius = math.floor(w.NukeInnerRingRadius * cfg.aoeMult)
                        end
                        if w.NukeOuterRingRadius and w.NukeOuterRingRadius > 0 then
                            w.NukeOuterRingRadius = math.floor(w.NukeOuterRingRadius * cfg.aoeMult)
                        end
                    end
                end
            end
        end
    end
end
"""
        with open(hook_dir / "Blueprints.lua", "w", encoding="utf-8") as f:
            f.write(bp_lua_content)

    # UI hooks for unit view details and rollover
    hook_ui_dir = target_mod_dir / "hook" / "lua" / "ui" / "game"
    hook_ui_dir.mkdir(parents=True, exist_ok=True)
    detail_lua = generate_ui_unitview_detail_lua(unit_table_lua, target_mode, player_name)
    with open(hook_ui_dir / "unitviewDetail.lua", "w", encoding="utf-8") as f:
        f.write(detail_lua)
    unitview_lua = generate_ui_unitview_lua(unit_table_lua, target_mode, player_name)
    with open(hook_ui_dir / "unitview.lua", "w", encoding="utf-8") as f:
        f.write(unitview_lua)

    # 3. Create zip file in exports/
    zip_path = EXPORTS_DIR / f"{safe_folder_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(target_mod_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = Path(safe_folder_name) / file_path.relative_to(target_mod_dir)
                zipf.write(file_path, arcname)

    return {
        "success": True,
        "modName": mod_name,
        "folderName": safe_folder_name,
        "targetModDir": str(target_mod_dir),
        "zipPath": str(zip_path),
        "unitsCount": len(unit_configs),
        "targetMode": target_mode,
        "playerName": player_name,
    }
PRESET_LIMIT_CATEGORIES = {
    "preset_t3_mex": "categories.MASSEXTRACTION * categories.TECH3",
    "preset_t2_mex": "categories.MASSEXTRACTION * categories.TECH2",
    "preset_all_mex": "categories.MASSEXTRACTION",
    "preset_all_exp": "categories.EXPERIMENTAL",
    "preset_paragon": "categories.EXPERIMENTAL * categories.STRUCTURE * categories.ECONOMIC",
    "preset_nukes": "categories.STRATEGIC * categories.SILO",
    "preset_smd": "categories.ANTIMISSILE * categories.TECH3 * categories.STRUCTURE",
    "preset_t3_arty": "categories.TECH3 * categories.ARTILLERY * categories.STRUCTURE",
    "preset_t3_pgen": "categories.ENERGYPRODUCTION * categories.TECH3 * categories.STRUCTURE",
    "preset_t3_radar": "categories.TECH3 * categories.RADAR * categories.STRUCTURE",
    "preset_t3_shield": "categories.TECH3 * categories.SHIELD * categories.STRUCTURE",
    "preset_t3_ships": "categories.BATTLESHIP + categories.CARRIER + categories.DREADNOUGHT",
}

PRESET_POPUP_CATEGORIES = {
    "preset_all_exp": "categories.EXPERIMENTAL",
    "preset_nuke_silo": "categories.STRATEGIC * categories.SILO",
    "preset_acu_low": "categories.COMMAND",
    "preset_acu_kill": "categories.COMMAND",
    "preset_t3_mex_kill": "categories.MASSEXTRACTION * categories.TECH3",
    "preset_paragon": "categories.EXPERIMENTAL * categories.STRUCTURE * categories.ECONOMIC",
}

PRESET_RELIC_CATEGORIES = {
    "preset_center_beacon": "categories.LAND * categories.TECH1 * (categories.DIRECTFIRE + categories.INDIRECTFIRE + categories.ANTIAIR)",
    "preset_ancient_monolith": "categories.COMMAND",
    "preset_air_shrine": "categories.AIR",
    "preset_naval_buoy": "categories.NAVAL",
    "preset_quantum_core": "categories.EXPERIMENTAL",
    "preset_supply_cache": "categories.ARTILLERY + categories.SILO",
}


def generate_limits_mod_files(data):
    mod_name = data.get("modName", "").strip() or "Player Unit Limits"
    author = data.get("author", "").strip() or "FAF Player"
    version = int(data.get("version", 1))
    target_mode = data.get("targetMode", "player")  # "player" or "global"
    player_name = data.get("playerName", "").strip()
    rules = data.get("rules", [])

    if not rules:
        raise ValueError("At least one limit rule must be configured.")

    mod_uid = str(uuid.uuid4())
    safe_folder_name = "".join(c for c in mod_name if c.isalnum() or c in (" ", "-", "_")).strip()

    target_mod_dir = DOCUMENTS_MODS_DIR / safe_folder_name
    if target_mod_dir.exists():
        shutil.rmtree(target_mod_dir)
    target_mod_dir.mkdir(parents=True, exist_ok=True)

    # 1. mod_info.lua
    description_text = f"Enforces {len(rules)} unit limit rules. "
    if target_mode == "player":
        description_text += f"Target player: {player_name} (Sim Hook)."
    else:
        description_text += "Enforced globally for all players."

    mod_info_content = f"""name = "{mod_name}"
version = {version}
copyright = "none"
description = "{description_text}"
author = "{author}"
uid = "{mod_uid}"
exclusive = false
ui_only = false
selectable = true
enabled = true
"""
    with open(target_mod_dir / "mod_info.lua", "w", encoding="utf-8") as f:
        f.write(mod_info_content)

    # 2. Lua rules definitions
    rules_lua_entries = []
    for r in rules:
        rid = r.get("id", "rule")
        rname = r.get("name", "Custom Unit").replace('"', '\\"')
        rlimit = int(r.get("limit", 1))
        rcat = r.get("categoryLua") or r.get("category") or r.get("categoryTag") or PRESET_LIMIT_CATEGORIES.get(rid, "")
        unit_ids = r.get("unitIds", [])

        if not rcat:
            if unit_ids:
                rcat = " + ".join([f"categories.{uid.upper()}" for uid in unit_ids])
            else:
                continue

        rules_lua_entries.append(
            f'    {{\n'
            f'        id = "{rid}",\n'
            f'        name = "{rname}",\n'
            f'        limit = {rlimit},\n'
            f'        category = {rcat},\n'
            f'    }}'
        )

    rules_table_lua = ",\n".join(rules_lua_entries)

    # 3. Hook generation: Unit.lua
    hook_dir = target_mod_dir / "hook" / "lua" / "sim"
    hook_dir.mkdir(parents=True, exist_ok=True)

    unit_lua_content = f"""-- Auto-generated by FAF Mod Forge
-- Player Unit Limits System
-- Target Scope: {target_mode}
-- Target Player: {player_name}
-- Total Rules: {len(rules)}

local TargetScope = "{target_mode}"
local TargetPlayer = "{player_name}"

local LimitRules = {{
{rules_table_lua}
}}

local function MatchesPlayerName(actualName, targetName)
    if not actualName or not targetName or targetName == "" then return false end
    local a = string.lower(actualName)
    local t = string.lower(targetName)
    if a == t then return true end
    if string.find(a, t, 1, true) then return true end
    local stripped = string.gsub(a, "%b[]", "")
    stripped = string.gsub(stripped, "%b()", "")
    stripped = string.gsub(stripped, "^%s*(.-)%s*$", "%1")
    if stripped == t or string.find(stripped, t, 1, true) then return true end
    return false
end

local function IsTargetArmy(armyIndex)
    if not armyIndex or armyIndex < 1 then return false end
    if TargetScope == "global" then return true end
    local setup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[armyIndex]
    if setup and setup.PlayerName and MatchesPlayerName(setup.PlayerName, TargetPlayer) then
        return true
    end
    local brain = ArmyBrains and ArmyBrains[armyIndex]
    if brain and brain.Nickname and MatchesPlayerName(brain.Nickname, TargetPlayer) then
        return true
    end
    local focus = GetFocusArmy()
    if focus and focus == armyIndex then
        return true
    end
    return false
end

local function GetTotalCount(brain, category, extraUnit)
    if not brain or not category then return 0 end
    local list = brain:GetListOfUnits(category, false) or {{}}
    local count = 0
    local foundExtra = false
    for _, u in ipairs(list) do
        if not u:BeenDestroyed() and not u:IsDead() then
            count = count + 1
            if extraUnit and u == extraUnit then
                foundExtra = true
            end
        end
    end
    if extraUnit and not foundExtra and not extraUnit:BeenDestroyed() and not extraUnit:IsDead() then
        if EntityCategoryContains(category, extraUnit) then
            count = count + 1
        end
    end
    return count
end

local function RefreshRestrictions(armyIndex)
    local brain = ArmyBrains and ArmyBrains[armyIndex]
    if not brain then return end
    for _, rule in ipairs(LimitRules) do
        local total = GetTotalCount(brain, rule.category)
        if total >= rule.limit then
            AddBuildRestriction(armyIndex, rule.category)
        else
            RemoveBuildRestriction(armyIndex, rule.category)
        end
    end
end

-- Apply immediate restrictions at match start (especially for 0-limit bans)
ForkThread(function()
    WaitTicks(2)
    if ArmyBrains then
        for armyIndex, brain in ArmyBrains do
            if IsTargetArmy(armyIndex) then
                RefreshRestrictions(armyIndex)
            end
        end
    end
end)

local OldUnit = Unit
Unit = Class(OldUnit) {{

    -- 1. Intercept building & upgrading starts
    OnStartBuild = function(self, unitBeingBuilt, order)
        local army = self:GetArmy()
        if IsTargetArmy(army) and unitBeingBuilt then
            -- Allow assisting engineers without treating them as building an additional unit
            if unitBeingBuilt.LimitTrackingStarted then
                return OldUnit.OnStartBuild(self, unitBeingBuilt, order)
            end

            local brain = self:GetAIBrain()
            for _, rule in ipairs(LimitRules) do
                if EntityCategoryContains(rule.category, unitBeingBuilt) then
                    local count = GetTotalCount(brain, rule.category, unitBeingBuilt)

                    if count > rule.limit then
                        -- Limit reached: Cancel the build / upgrade order
                        PrintText("🛑 [LIMIT REACHED] " .. rule.name .. " limit reached (" .. tostring(rule.limit) .. " max)!", 18, "ffff3333", 4, "center")
                        AddBuildRestriction(army, rule.category)
                        unitBeingBuilt:Destroy()
                        if order == "Upgrade" then
                            self:OnFailedToBuild()
                            IssueClearCommands({{self}})
                        else
                            IssueStop({{self}})
                        end
                        return false
                    else
                        unitBeingBuilt.LimitTrackingStarted = true
                        unitBeingBuilt.TrackedRuleCategory = rule.category

                        if count >= rule.limit then
                            AddBuildRestriction(army, rule.category)
                        end
                    end
                end
            end
        end
        return OldUnit.OnStartBuild(self, unitBeingBuilt, order)
    end,

    OnStopBuild = function(self, unitBeingBuilt, order)
        local result = OldUnit.OnStopBuild(self, unitBeingBuilt, order)
        local army = self:GetArmy()
        if IsTargetArmy(army) then
            RefreshRestrictions(army)
        end
        return result
    end,

    OnFailedToBuild = function(self)
        local result = OldUnit.OnFailedToBuild(self)
        local army = self:GetArmy()
        if IsTargetArmy(army) then
            RefreshRestrictions(army)
        end
        return result
    end,

    -- 3. Unit completes construction
    OnStopBeingBuilt = function(self, builder, layer)
        local result = OldUnit.OnStopBeingBuilt(self, builder, layer)
        local army = self:GetArmy()
        if IsTargetArmy(army) then
            local brain = self:GetAIBrain()
            for _, rule in ipairs(LimitRules) do
                if EntityCategoryContains(rule.category, self) then
                    self.TrackedRuleCategory = rule.category
                    local count = GetTotalCount(brain, rule.category)
                    if count > rule.limit then
                        PrintText("🛑 [LIMIT EXCEEDED] " .. rule.name .. " cap is " .. tostring(rule.limit) .. "! Unit destroyed.", 18, "ffff2222", 5, "center")
                        self:Destroy()
                        return false
                    elseif count >= rule.limit then
                        AddBuildRestriction(army, rule.category)
                    end
                end
            end
        end
        return result
    end,

    -- 4. Unit destroyed or reclaimed: lift restrictions if below limit
    OnDestroy = function(self)
        local army = self:GetArmy()
        local isTarget = IsTargetArmy(army)
        local cat = self.TrackedRuleCategory
        local result = OldUnit.OnDestroy(self)

        if isTarget and cat then
            ForkThread(function()
                WaitTicks(1)
                RefreshRestrictions(army)
            end)
        end
        return result
    end,

    -- 5. Intercept unit transfer / gifts from allies
    OnGiven = function(self, newUnit)
        local result = OldUnit.OnGiven(self, newUnit)
        if newUnit and not newUnit:BeenDestroyed() then
            local army = newUnit:GetArmy()
            if IsTargetArmy(army) then
                local brain = newUnit:GetAIBrain()
                for _, rule in ipairs(LimitRules) do
                    if EntityCategoryContains(rule.category, newUnit) then
                        newUnit.TrackedRuleCategory = rule.category
                        local count = GetTotalCount(brain, rule.category)
                        if count > rule.limit then
                            PrintText("🛑 [LIMIT EXCEEDED] Gifted " .. rule.name .. " exceeds cap (" .. tostring(rule.limit) .. ")! Destroyed.", 18, "ffff2222", 5, "center")
                            newUnit:Destroy()
                            return false
                        elseif count >= rule.limit then
                            AddBuildRestriction(army, rule.category)
                        end
                    end
                end
            end
        end
        return result
    end,
}}
"""
    with open(hook_dir / "Unit.lua", "w", encoding="utf-8") as f:
        f.write(unit_lua_content)

    # 4. Create zip file in exports/
    zip_path = EXPORTS_DIR / f"{safe_folder_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(target_mod_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = Path(safe_folder_name) / file_path.relative_to(target_mod_dir)
                zipf.write(file_path, arcname)

    return {
        "success": True,
        "modName": mod_name,
        "folderName": safe_folder_name,
        "targetModDir": str(target_mod_dir),
        "zipPath": str(zip_path),
        "rulesCount": len(rules),
        "targetMode": target_mode,
        "playerName": player_name,
    }


def generate_relics_mod_files(data):
    mod_name = data.get("modName", "").strip() or "Commander Relic Objectives"
    author = data.get("author", "").strip() or "FAF Player"
    version = int(data.get("version", 1))
    target_mode = data.get("targetMode", "global")  # "global" or "player"
    player_name = data.get("playerName", "").strip()
    objectives = data.get("objectives", [])

    if not objectives:
        raise ValueError("At least one Relic Objective must be configured.")

    mod_uid = str(uuid.uuid4())
    safe_folder_name = "".join(c for c in mod_name if c.isalnum() or c in (" ", "-", "_")).strip()

    target_mod_dir = DOCUMENTS_MODS_DIR / safe_folder_name
    if target_mod_dir.exists():
        shutil.rmtree(target_mod_dir)
    target_mod_dir.mkdir(parents=True, exist_ok=True)

    # 1. mod_info.lua
    description_text = f"Spawns {len(objectives)} battlefield objectives. "
    if target_mode == "player":
        description_text += f"Rewards exclusive to {player_name}'s commander."
    else:
        description_text += "Contested by all players. Whoever collects/captures earns unit bonuses!"

    mod_info_content = f"""name = "{mod_name}"
version = {version}
copyright = "none"
description = "{description_text}"
author = "{author}"
uid = "{mod_uid}"
exclusive = false
ui_only = false
selectable = true
enabled = true
"""
    with open(target_mod_dir / "mod_info.lua", "w", encoding="utf-8") as f:
        f.write(mod_info_content)

    # 2. Lua objectives table
    obj_lua_entries = []
    for o in objectives:
        oid = o.get("id", "obj")
        oname = o.get("name", "Battlefield Relic").replace('"', '\\"')
        model_bp = o.get("modelBpId") or "uec1904"
        delay = int(o.get("spawnDelay", 0))
        loc_mode = o.get("locMode", "center")
        cx = float(o.get("customX", 256))
        cz = float(o.get("customZ", 256))
        trigger_type = o.get("triggerType", "both")
        pickup_radius = float(o.get("pickupRadius", 15.0))
        claimer_cat = o.get("claimerCategoryLua") or o.get("claimerCategory") or "categories.COMMAND"

        target_type = o.get("targetType", "category")
        target_name = o.get("targetName", "All Combat Units").replace('"', '\\"')
        target_uid = (o.get("targetUnitId") or "").strip()
        target_cat = o.get("targetCategoryLua") or o.get("targetCategory") or PRESET_RELIC_CATEGORIES.get(oid, "categories.COMMAND")

        buffs = o.get("buffs", {})
        hp_m = round(float(buffs.get("hpMult", 1.0)), 2)
        rng_m = round(float(buffs.get("rangeMult", 1.0)), 2)
        dmg_m = round(float(buffs.get("damageMult", 1.0)), 2)
        spd_m = round(float(buffs.get("speedMult", 1.0)), 2)
        shd_m = round(float(buffs.get("shieldMult", 1.0)), 2)
        rgn_m = round(float(buffs.get("regenMult", 1.0)), 2)

        buff_duration = int(o.get("buffDuration", 0))

        entry = f"""    {{
        id = "{oid}",
        name = "{oname}",
        modelBpId = "{model_bp}",
        spawnDelay = {delay},
        locMode = "{loc_mode}",
        customX = {cx},
        customZ = {cz},
        triggerType = "{trigger_type}",
        pickupRadius = {pickup_radius},
        claimerCategory = {claimer_cat},
        targetType = "{target_type}",
        targetName = "{target_name}",
        targetUnitId = "{target_uid}",
        targetCategory = {target_cat},
        buffDuration = {buff_duration},
        buffs = {{
            hpMult = {hp_m},
            rangeMult = {rng_m},
            damageMult = {dmg_m},
            speedMult = {spd_m},
            shieldMult = {shd_m},
            regenMult = {rgn_m},
        }},
    }}"""
        obj_lua_entries.append(entry)

    objectives_table_lua = ",\n".join(obj_lua_entries)

    # 3. Hook generation: Unit.lua
    hook_dir = target_mod_dir / "hook" / "lua" / "sim"
    hook_dir.mkdir(parents=True, exist_ok=True)

    unit_lua_content = f"""-- Auto-generated by FAF Mod Forge - Relic & Crate Objectives System
-- Target Scope: {target_mode}
-- Target Player: {player_name}
-- Total Objectives: {len(objectives)}

local TargetScope = "{target_mode}"
local TargetPlayer = "{player_name}"

local function MatchesPlayerName(actualName, targetName)
    if not actualName or not targetName or targetName == "" then return false end
    local a = string.lower(actualName)
    local t = string.lower(targetName)
    if a == t then return true end
    if string.find(a, t, 1, true) then return true end
    local stripped = string.gsub(a, "%b[]", "")
    stripped = string.gsub(stripped, "%b()", "")
    stripped = string.gsub(stripped, "^%s*(.-)%s*$", "%1")
    if stripped == t or string.find(stripped, t, 1, true) then return true end
    return false
end

local ObjectivesConfig = {{
{objectives_table_lua}
}}

-- Storage for active relic objectives per army:
-- ActiveRelicsByArmy[army] = {{ [relicId] = objConfig }}
local ActiveRelicsByArmy = {{}}

local function UnitMatchesRelic(unit, objConfig)
    if not unit or unit:BeenDestroyed() or unit:IsDead() then return false end
    if objConfig.targetType == "category" then
        if objConfig.targetCategory and EntityCategoryContains(objConfig.targetCategory, unit) then
            return true
        end
    else
        local uid = string.lower(objConfig.targetUnitId or "")
        if uid ~= "" then
            local bp = unit:GetBlueprint()
            local bpId = string.lower(bp.BlueprintId or unit:GetUnitId() or "")
            if bpId == uid then return true end
        end
    end
    return false
end

local function RecomputeUnitStats(unit)
    if not unit or unit:BeenDestroyed() or unit:IsDead() then return end
    local bp = unit:GetBlueprint()

    local totalHpMult = 1.0
    local totalSpeedMult = 1.0
    local totalRangeMult = 1.0
    local totalDmgMult = 1.0
    local totalShieldMult = 1.0
    local totalRegenMult = 1.0

    if unit.ActiveRelicBuffs then
        for _, buffs in pairs(unit.ActiveRelicBuffs) do
            if buffs.hpMult and buffs.hpMult > 0 then totalHpMult = totalHpMult * buffs.hpMult end
            if buffs.speedMult and buffs.speedMult > 0 then totalSpeedMult = totalSpeedMult * buffs.speedMult end
            if buffs.rangeMult and buffs.rangeMult > 0 then totalRangeMult = totalRangeMult * buffs.rangeMult end
            if buffs.damageMult and buffs.damageMult > 0 then totalDmgMult = totalDmgMult * buffs.damageMult end
            if buffs.shieldMult and buffs.shieldMult > 0 then totalShieldMult = totalShieldMult * buffs.shieldMult end
            if buffs.regenMult and buffs.regenMult > 0 then totalRegenMult = totalRegenMult * buffs.regenMult end
        end
    end

    -- 1. HP Buff Blueprint
    local buffName = 'Relic_Total_Health_' .. string.gsub(string.format("%.3f", totalHpMult), "%.", "_")
    if not Buffs[buffName] then
        BuffBlueprint {{
            Name = buffName,
            DisplayName = buffName,
            BuffType = 'RELIC_TOTAL_HEALTH',
            Stacks = 'REPLACE',
            Duration = -1,
            Affects = {{
                MaxHealth = {{
                    Add = 0,
                    Mult = totalHpMult,
                    DoNotFill = false,
                }},
            }},
        }}
    end
    import('/lua/sim/buff.lua').ApplyBuff(unit, buffName)
    if unit:GetHealth() > unit:GetMaxHealth() then
        unit:SetHealth(unit, unit:GetMaxHealth())
    end

    -- 2. Range
    local wCount = unit:GetWeaponCount() or 0
    if wCount > 0 then
        for i = 1, wCount do
            local wep = unit:GetWeapon(i)
            if wep then
                local wbp = wep:GetBlueprint()
                if wbp and wbp.MaxRadius and wep.ChangeMaxRadius then
                    wep:ChangeMaxRadius(math.floor(wbp.MaxRadius * totalRangeMult))
                end
            end
        end
    end

    -- 3. Speed
    if unit.SetSpeedMult then unit:SetSpeedMult(totalSpeedMult) end
    if unit.SetAccMult then unit:SetAccMult(totalSpeedMult) end

    -- 4. Damage
    unit.CustomRelicDmgMult = totalDmgMult

    -- 5. Shield
    if unit.MyShield then
        unit.OriginalShieldMaxHealth = unit.OriginalShieldMaxHealth or unit.MyShield:GetMaxHealth()
        local newMax = math.floor(unit.OriginalShieldMaxHealth * totalShieldMult)
        unit.MyShield:SetMaxHealth(newMax)
        if unit.MyShield:GetHealth() > newMax then
            unit.MyShield:SetHealth(unit.MyShield, newMax)
        end
    end

    -- 6. Regen
    local baseRegen = (bp.Defense and bp.Defense.RegenRate) or 0
    if baseRegen == 0 and totalRegenMult > 1.0 then baseRegen = 5 end
    if unit.SetRegenRate then
        unit:SetRegenRate(math.floor(baseRegen * totalRegenMult))
    end
end

local function RevertRelicBuffs(army, objConfig)
    if not ActiveRelicsByArmy or not ActiveRelicsByArmy[army] or not ActiveRelicsByArmy[army][objConfig.id] then
        return
    end
    ActiveRelicsByArmy[army][objConfig.id] = nil

    pcall(function()
        Sync.ModForgeRelics = Sync.ModForgeRelics or {{}}
        table.insert(Sync.ModForgeRelics, {{
            action = "expire",
            army = army,
            id = objConfig.id,
        }})
    end)

    local brain = ArmyBrains and ArmyBrains[army]
    local armySetup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[army]
    local playerName = (armySetup and armySetup.PlayerName) or (brain and brain.Nickname) or ("Player " .. tostring(army))
    PrintText("⏳ [BUFF EXPIRED] '" .. tostring(objConfig.name) .. "' bonus on " .. tostring(objConfig.targetName) .. " expired for " .. tostring(playerName) .. "!", 16, "ffffaa33", 5, "center")

    if brain then
        local allUnits = brain:GetListOfUnits(categories.ALLUNITS, false) or {{}}
        for _, u in ipairs(allUnits) do
            if u.ActiveRelicBuffs and u.ActiveRelicBuffs[objConfig.id] then
                u.ActiveRelicBuffs[objConfig.id] = nil
                RecomputeUnitStats(u)
            end
        end
    end
end

local function GetNeutralArmy()
    if ScenarioInfo.ArmySetup then
        for armyName, data in pairs(ScenarioInfo.ArmySetup) do
            local upperName = string.upper(armyName)
            if string.find(upperName, "CIVILIAN") or string.find(upperName, "NEUTRAL") then
                return data.ArmyIndex or armyName
            end
        end
    end
    if ArmyBrains then
        for idx, brain in ArmyBrains do
            if brain.Civilian or (brain.Name and (string.find(string.upper(brain.Name), "CIVILIAN") or string.find(string.upper(brain.Name), "NEUTRAL"))) then
                return brain:GetArmyIndex()
            end
        end
    end
    return nil
end

local function OnRelicClaimed(relic, claimer, objConfig)
    if not relic or relic.RelicClaimed then return end
    relic.RelicClaimed = true

    local army = claimer:GetArmy()
    local brain = ArmyBrains and ArmyBrains[army]
    local armySetup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[army]
    local playerName = (armySetup and armySetup.PlayerName) or (brain and brain.Nickname) or ("Player " .. tostring(army))

    if TargetScope == "player" and TargetPlayer ~= "" then
        if not MatchesPlayerName(playerName, TargetPlayer) then
            PrintText("⚠️ Only " .. TargetPlayer .. " can unlock this objective!", 16, "ffff5555", 3, "center")
            relic.RelicClaimed = false
            return
        end
    end

    ActiveRelicsByArmy[army] = ActiveRelicsByArmy[army] or {{}}
    ActiveRelicsByArmy[army][objConfig.id] = objConfig

    local buffSummary = {{}}
    if objConfig.buffs.hpMult and objConfig.buffs.hpMult ~= 1.0 then
        table.insert(buffSummary, string.format("+%d%% HP", math.floor((objConfig.buffs.hpMult - 1.0) * 100)))
    end
    if objConfig.buffs.rangeMult and objConfig.buffs.rangeMult ~= 1.0 then
        table.insert(buffSummary, string.format("+%d%% Range", math.floor((objConfig.buffs.rangeMult - 1.0) * 100)))
    end
    if objConfig.buffs.damageMult and objConfig.buffs.damageMult ~= 1.0 then
        table.insert(buffSummary, string.format("+%d%% Damage", math.floor((objConfig.buffs.damageMult - 1.0) * 100)))
    end
    if objConfig.buffs.speedMult and objConfig.buffs.speedMult ~= 1.0 then
        table.insert(buffSummary, string.format("+%d%% Speed", math.floor((objConfig.buffs.speedMult - 1.0) * 100)))
    end
    local buffText = table.concat(buffSummary, ", ")
    local durText = (objConfig.buffDuration and objConfig.buffDuration > 0) and (" [⏳ " .. tostring(objConfig.buffDuration) .. "s]") or " [Permanent]"

    local msg = string.format("🏆 [OBJECTIVE CLAIMED] %s claimed '%s'! %s awarded (%s)%s!", playerName, objConfig.name, objConfig.targetName, buffText, durText)
    PrintText(msg, 18, "ff00d2ff", 6, "center")

    -- Broadcast full-screen / UI Tactical Popup card to ALL players when claimed
    pcall(function()
        local rPos = relic:GetPosition()
        local posTable = (rPos and {{ rPos[1], rPos[2], rPos[3] }}) or nil
        Sync.ModForgePopups = Sync.ModForgePopups or {{}}
        table.insert(Sync.ModForgePopups, {{
            id = "relic_claim_" .. tostring(objConfig.id or "relic"),
            title = "🏆 OBJECTIVE SECURED",
            text = tostring(playerName) .. " claimed '" .. tostring(objConfig.name) .. "'! " .. tostring(objConfig.targetName) .. " awarded: " .. buffText .. "!" .. durText,
            pos = posTable,
            sound = "UI_Score_Window_Open",
            theme = "tactical",
            hasPinpoint = (posTable ~= nil),
            hasPing = true,
            hasDismiss = true,
            duration = 10,
            scope = "global",
            targetPlayer = "",
        }})
    end)

    -- Sync to UI for active buff breakdown
    pcall(function()
        Sync.ModForgeRelics = Sync.ModForgeRelics or {{}}
        table.insert(Sync.ModForgeRelics, {{
            action = "claim",
            army = army,
            id = objConfig.id,
            name = objConfig.name,
            targetName = objConfig.targetName,
            buffs = objConfig.buffs,
            duration = objConfig.buffDuration or 0,
            startTime = (GetGameTimeSeconds and GetGameTimeSeconds()) or 0,
        }})
    end)

    pcall(function()
        CreateEmitterAtEntity(relic, army, '/effects/emitters/flash_01_emit.bp')
    end)

    -- Apply to all alive units belonging to claiming army
    if brain then
        local allUnits = brain:GetListOfUnits(categories.ALLUNITS, false) or {{}}
        for _, u in ipairs(allUnits) do
            if UnitMatchesRelic(u, objConfig) then
                u.ActiveRelicBuffs = u.ActiveRelicBuffs or {{}}
                u.ActiveRelicBuffs[objConfig.id] = objConfig.buffs
                RecomputeUnitStats(u)
            end
        end
    end

    -- If temporal duration configured, fork expiration thread
    if objConfig.buffDuration and objConfig.buffDuration > 0 then
        ForkThread(function()
            WaitSeconds(objConfig.buffDuration)
            RevertRelicBuffs(army, objConfig)
        end)
    end

    relic:Destroy()
end

local function SpawnObjectiveInstance(objConfig)
    if not objConfig then return end
    local bpId = (objConfig.modelBpId and objConfig.modelBpId ~= "" and objConfig.modelBpId) or "uec1904"
    if objConfig.spawnDelay and objConfig.spawnDelay > 0 then
        WaitSeconds(objConfig.spawnDelay)
    end

    local sizeX = (ScenarioInfo.size and ScenarioInfo.size[1]) or 512
    local sizeZ = (ScenarioInfo.size and ScenarioInfo.size[2]) or 512
    local centerX = sizeX / 2
    local centerZ = sizeZ / 2

    local posX = centerX
    local posZ = centerZ
    if objConfig.locMode == "coords" and objConfig.customX and objConfig.customZ then
        posX = objConfig.customX
        posZ = objConfig.customZ
    elseif objConfig.locMode == "random_center" then
        local angle = Random(0, 360) * (math.pi / 180)
        local dist = Random(40, 90)
        posX = math.max(20, math.min(sizeX - 20, centerX + math.cos(angle) * dist))
        posZ = math.max(20, math.min(sizeZ - 20, centerZ + math.sin(angle) * dist))
    end

    local posY = GetSurfaceHeight(posX, posZ)
    local neutralArmy = GetNeutralArmy()

    if not neutralArmy then
        local focus = GetFocusArmy()
        if ArmyBrains then
            for idx, brain in ArmyBrains do
                if brain:GetArmyIndex() ~= focus then
                    neutralArmy = brain:GetArmyIndex()
                    break
                end
            end
        end
        if not neutralArmy then
            neutralArmy = (ArmyBrains and ArmyBrains[1] and ArmyBrains[1]:GetArmyIndex()) or 1
        end
    end

    local fallbackIdx = (ArmyBrains and ArmyBrains[1] and ArmyBrains[1]:GetArmyIndex()) or 1
    local relic = nil
    pcall(function()
        relic = CreateUnitHPR(bpId, neutralArmy, posX, posY, posZ, 0, 0, 0)
    end)
    if not relic then
        pcall(function()
            relic = CreateUnitHPR(bpId, fallbackIdx, posX, posY, posZ, 0, 0, 0)
            neutralArmy = fallbackIdx
        end)
    end
    if not relic then
        pcall(function()
            relic = CreateUnitHPR("uec1904", fallbackIdx, posX, posY, posZ, 0, 0, 0)
            neutralArmy = fallbackIdx
        end)
    end

    if not relic then
        WARN("FAF Mod Forge: Failed to spawn relic objective '" .. tostring(objConfig.name) .. "' with blueprint: " .. tostring(bpId))
        return
    end

    LOG("FAF Mod Forge: Spawned relic '" .. tostring(objConfig.name) .. "' (" .. tostring(bpId) .. ") at (" .. posX .. ", " .. posZ .. ")")

    relic.IsRelicObjective = true
    relic.RelicConfig = objConfig
    relic.RelicClaimerCategory = objConfig.claimerCategory or (categories.MOBILE)

    relic:SetCapturable(true)
    relic:SetReclaimable(false)
    relic:SetCanTakeDamage(false)
    if relic.SetCaptureTimeMultiplier then
        relic:SetCaptureTimeMultiplier(0.05)
    end

    -- Enforce two-way neutral diplomacy so all players can capture it
    if ArmyBrains then
        for idx, brain in ArmyBrains do
            SetAlliance(neutralArmy, brain:GetArmyIndex(), 'Neutral')
            SetAlliance(brain:GetArmyIndex(), neutralArmy, 'Neutral')
        end
    end

    -- Trigger tactical minimap alert ping
    pcall(function()
        Sync.CreatePing = Sync.CreatePing or {{}}
        table.insert(Sync.CreatePing, {{ Owner = 0, Type = 'alert', Location = {{posX, posY, posZ}} }})
    end)

    -- In-game broadcast text
    PrintText("🏆 [OBJECTIVE SPAWNED] " .. tostring(objConfig.name) .. " has appeared at (" .. math.floor(posX) .. ", " .. math.floor(posZ) .. ")! Capture or reach it with combat units/engineers for team buffs!", 18, "ffffff33", 8, "center")

    -- Broadcast full-screen / UI Tactical Popup card to ALL human players
    pcall(function()
        Sync.ModForgePopups = Sync.ModForgePopups or {{}}
        table.insert(Sync.ModForgePopups, {{
            id = "relic_spawn_" .. tostring(objConfig.id or "relic"),
            title = "👑 BATTLEFIELD OBJECTIVE ONLINE",
            text = tostring(objConfig.name or "Battlefield Objective") .. " is active at map center! Reach or capture it to award team buffs!",
            pos = {{ posX, posY, posZ }},
            sound = "UI_Score_Window_Open",
            theme = "quantum",
            hasPinpoint = true,
            hasPing = true,
            hasDismiss = true,
            duration = 14,
            scope = "global",
            targetPlayer = "",
        }})
    end)

    -- Proximity pickup polling thread
    if objConfig.triggerType == "walkover" or objConfig.triggerType == "both" then
        local radius = math.max(objConfig.pickupRadius or 12.0, 15.0)
        local claimerCat = objConfig.claimerCategory or (categories.MOBILE)
        ForkThread(function()
            while relic and not relic:BeenDestroyed() and not relic:IsDead() and not relic.RelicClaimed do
                local rPos = relic:GetPosition()
                if ArmyBrains then
                    for _, brain in ArmyBrains do
                        local checkUnits = brain:GetListOfUnits(claimerCat, false) or {{}}
                        for _, u in ipairs(checkUnits) do
                            if not u:BeenDestroyed() and not u:IsDead() and VDist3(u:GetPosition(), rPos) <= radius then
                                OnRelicClaimed(relic, u, objConfig)
                                return
                            end
                        end
                    end
                end
                WaitSeconds(0.4)
            end
        end)
    end
end

ForkThread(function()
    WaitSeconds(2)
    for _, obj in ipairs(ObjectivesConfig) do
        ForkThread(SpawnObjectiveInstance, obj)
    end
end)

local OldUnit = Unit
Unit = Class(OldUnit) {{

    -- 1. Apply active relic bonuses to newly built units and fill health
    OnStopBeingBuilt = function(self, builder, layer)
        local result = OldUnit.OnStopBeingBuilt(self, builder, layer)
        local army = self:GetArmy()

        if ActiveRelicsByArmy and ActiveRelicsByArmy[army] then
            for rId, rCfg in pairs(ActiveRelicsByArmy[army]) do
                if UnitMatchesRelic(self, rCfg) then
                    self.ActiveRelicBuffs = self.ActiveRelicBuffs or {{}}
                    self.ActiveRelicBuffs[rId] = rCfg.buffs
                end
            end
        end

        RecomputeUnitStats(self)
        self:SetHealth(self, self:GetMaxHealth())

        return result
    end,

    -- 2. Intercept capture of relic objectives
    OnCaptured = function(self, captor)
        local result = OldUnit.OnCaptured(self, captor)
        if self.IsRelicObjective and not self.RelicClaimed and captor and not captor:IsDead() then
            local claimerCat = self.RelicClaimerCategory or (categories.MOBILE)
            if EntityCategoryContains(claimerCat, captor) then
                OnRelicClaimed(self, captor, self.RelicConfig)
            end
        end
        return result
    end,

    -- 3. Damage Multiplier for boosted weapons
    OnDamage = function(self, instigator, amount, vector, damageType)
        local amt = amount
        if instigator and instigator.CustomRelicDmgMult and instigator.CustomRelicDmgMult ~= 1.0 and amount and amount > 0 then
            amt = amount * instigator.CustomRelicDmgMult
        end
        return OldUnit.OnDamage(self, instigator, amt, vector, damageType)
    end,
}}
"""
    with open(hook_dir / "Unit.lua", "w", encoding="utf-8") as f:
        f.write(unit_lua_content)

    hook_ui_dir = target_mod_dir / "hook" / "lua" / "ui" / "game"
    hook_ui_dir.mkdir(parents=True, exist_ok=True)
    with open(hook_ui_dir / "gamemain.lua", "w", encoding="utf-8") as f:
        f.write(generate_ui_gamemain_lua())
    with open(hook_ui_dir / "unitviewDetail.lua", "w", encoding="utf-8") as f:
        f.write(generate_ui_unitview_detail_lua("", target_mode, player_name))
    with open(hook_ui_dir / "unitview.lua", "w", encoding="utf-8") as f:
        f.write(generate_ui_unitview_lua("", target_mode, player_name))

    # 4. Create zip file in exports/
    zip_path = EXPORTS_DIR / f"{safe_folder_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(target_mod_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = Path(safe_folder_name) / file_path.relative_to(target_mod_dir)
                zipf.write(file_path, arcname)

    return {
        "success": True,
        "modName": mod_name,
        "folderName": safe_folder_name,
        "targetModDir": str(target_mod_dir),
        "zipPath": str(zip_path),
        "objectivesCount": len(objectives),
        "targetMode": target_mode,
        "playerName": player_name,
    }


def generate_popups_mod_files(data):
    mod_name = data.get("modName", "").strip() or "Tactical Event Popups"
    author = data.get("author", "").strip() or "FAF Player"
    version = int(data.get("version", 1))
    target_mode = data.get("targetMode", "global")  # "global" or "player"
    player_name = data.get("playerName", "").strip()
    rules = data.get("rules", [])

    if not rules:
        raise ValueError("At least one popup rule must be configured.")

    mod_uid = str(uuid.uuid4())
    safe_folder_name = "".join(c for c in mod_name if c.isalnum() or c in (" ", "-", "_")).strip()

    target_mod_dir = DOCUMENTS_MODS_DIR / safe_folder_name
    if target_mod_dir.exists():
        shutil.rmtree(target_mod_dir)
    target_mod_dir.mkdir(parents=True, exist_ok=True)

    # 1. mod_info.lua
    description_text = f"Adds {len(rules)} tactical event popups with pinpoint buttons. "
    if target_mode == "player":
        description_text += f"Target player: {player_name} (Sim & UI Hook)."
    else:
        description_text += "Active for all players."

    mod_info_content = f"""name = "{mod_name}"
version = {version}
copyright = "none"
description = "{description_text}"
author = "{author}"
uid = "{mod_uid}"
exclusive = false
ui_only = false
selectable = true
enabled = true
"""
    with open(target_mod_dir / "mod_info.lua", "w", encoding="utf-8") as f:
        f.write(mod_info_content)

    # Build Lua table of rules
    rules_lua_entries = []
    for r in rules:
        rid = r.get("id", "rule")
        rname = r.get("name", "Alert").replace('"', '\\"')
        trigger = r.get("trigger", "unit_built")
        rtitle = r.get("title", "TACTICAL ALERT").replace('"', '\\"')
        rtext = r.get("text", "Event occurred!").replace('"', '\\"')
        rtheme = r.get("theme", "intel")
        rsound = r.get("sound", "UI_Radar_Blip")
        has_pinpoint = "true" if r.get("hasPinpoint", True) else "false"
        has_ping = "true" if r.get("hasPing", True) else "false"
        has_dismiss = "true" if r.get("hasDismiss", True) else "false"
        duration = int(r.get("duration", 8))
        health_pct = float(r.get("healthPct", 35))
        timer_sec = int(r.get("timerSeconds", 600))
        scope = r.get("scope", "global")
        target_player = r.get("targetPlayer", "").replace('"', '\\"')

        unit_ids = r.get("unitIds", [])
        unit_ids_lua = "{" + ", ".join(f'"{uid.lower()}"' for uid in unit_ids) + "}"
        cat_lua = r.get("categoryLua") or r.get("category") or PRESET_POPUP_CATEGORIES.get(rid, "")
        if not cat_lua:
            if unit_ids:
                cat_lua = " + ".join(f"categories.{uid.upper()}" for uid in unit_ids)
            else:
                cat_lua = "nil"

        rules_lua_entries.append(
            f'    {{\n'
            f'        id = "{rid}",\n'
            f'        name = "{rname}",\n'
            f'        trigger = "{trigger}",\n'
            f'        title = "{rtitle}",\n'
            f'        text = "{rtext}",\n'
            f'        theme = "{rtheme}",\n'
            f'        sound = "{rsound}",\n'
            f'        hasPinpoint = {has_pinpoint},\n'
            f'        hasPing = {has_ping},\n'
            f'        hasDismiss = {has_dismiss},\n'
            f'        duration = {duration},\n'
            f'        healthPct = {health_pct},\n'
            f'        timerSeconds = {timer_sec},\n'
            f'        scope = "{scope}",\n'
            f'        targetPlayer = "{target_player}",\n'
            f'        unitIds = {unit_ids_lua},\n'
            f'        category = {cat_lua},\n'
            f'    }}'
        )

    rules_table_lua = ",\n".join(rules_lua_entries)

    # 2. Hook Sim Unit.lua
    hook_sim_dir = target_mod_dir / "hook" / "lua" / "sim"
    hook_sim_dir.mkdir(parents=True, exist_ok=True)

    sim_unit_lua_content = f"""-- Auto-generated by FAF Mod Forge
-- In-Game Tactical Event Popups & Alerts
-- Scope: {target_mode} | Target Player: {player_name}
-- Total Rules: {len(rules)}

local TargetScope = "{target_mode}"
local TargetPlayer = "{player_name}"

local PopupRules = {{
{rules_table_lua}
}}

local function MatchesPlayerName(actualName, targetName)
    if not actualName or not targetName or targetName == "" then return false end
    local a = string.lower(actualName)
    local t = string.lower(targetName)
    if a == t then return true end
    if string.find(a, t, 1, true) then return true end
    local stripped = string.gsub(a, "%b[]", "")
    stripped = string.gsub(stripped, "%b()", "")
    stripped = string.gsub(stripped, "^%s*(.-)%s*$", "%1")
    if stripped == t or string.find(stripped, t, 1, true) then return true end
    return false
end

local function IsTargetArmy(armyIndex)
    if not armyIndex or armyIndex < 1 then return false end
    if TargetScope == "global" then return true end
    local setup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[armyIndex]
    if setup and setup.PlayerName and MatchesPlayerName(setup.PlayerName, TargetPlayer) then
        return true
    end
    local brain = ArmyBrains and ArmyBrains[armyIndex]
    if brain and brain.Nickname and MatchesPlayerName(brain.Nickname, TargetPlayer) then
        return true
    end
    local focus = GetFocusArmy()
    if focus and focus == armyIndex then
        return true
    end
    return false
end

local function MatchesUnit(rule, unit)
    if not unit or unit:BeenDestroyed() or unit:IsDead() then return false end
    if rule.unitIds and table.getn(rule.unitIds) > 0 then
        local bpId = string.lower(unit:GetBlueprint().BlueprintId)
        for _, id in ipairs(rule.unitIds) do
            if string.lower(id) == bpId then
                return true
            end
        end
    end
    if rule.category and EntityCategoryContains(rule.category, unit) then
        return true
    end
    return false
end

local function FirePopupAlert(rule, unit, overridePos)
    Sync.ModForgePopups = Sync.ModForgePopups or {{}}
    local pos = overridePos
    if not pos and unit and not unit:BeenDestroyed() then
        local v = unit:GetPosition()
        if v then pos = {{v[1], v[2], v[3]}} end
    end

    local bpName = ""
    if unit and not unit:BeenDestroyed() then
        local bp = unit:GetBlueprint()
        if bp.General and bp.General.UnitName then
            bpName = bp.General.UnitName
        elseif bp.Description then
            bpName = bp.Description
        end
        bpName = string.gsub(bpName, "<LOC [^>]*>", "")
    end

    local msg = rule.text
    if bpName ~= "" then
        msg = string.gsub(msg, "{{{{UnitName}}}}", bpName)
        msg = string.gsub(msg, "{{UnitName}}", bpName)
    end

    table.insert(Sync.ModForgePopups, {{
        id = rule.id,
        title = rule.title,
        text = msg,
        pos = pos,
        sound = rule.sound,
        theme = rule.theme,
        hasPinpoint = rule.hasPinpoint,
        hasPing = rule.hasPing,
        hasDismiss = rule.hasDismiss,
        duration = rule.duration,
        targetScope = rule.scope or TargetScope,
        targetPlayer = (rule.targetPlayer ~= "" and rule.targetPlayer) or TargetPlayer,
        armyIndex = (unit and not unit:BeenDestroyed()) and unit:GetArmy() or -1,
    }})
end

-- Timer Triggers Thread
ForkThread(function()
    local timerRules = {{}}
    for _, r in ipairs(PopupRules) do
        if r.trigger == "match_timer" and r.timerSeconds and r.timerSeconds > 0 then
            table.insert(timerRules, r)
        end
    end
    if table.getn(timerRules) == 0 then return end

    table.sort(timerRules, function(a, b) return a.timerSeconds < b.timerSeconds end)
    local currentSec = 0
    for _, r in ipairs(timerRules) do
        local waitSec = r.timerSeconds - currentSec
        if waitSec > 0 then
            WaitSeconds(waitSec)
            currentSec = r.timerSeconds
        end
        FirePopupAlert(r, nil, nil)
    end
end)

local OldUnit = Unit
Unit = Class(OldUnit) {{

    OnStopBeingBuilt = function(self, builder, layer)
        local result = OldUnit.OnStopBeingBuilt(self, builder, layer)
        local army = self:GetArmy()
        for _, r in ipairs(PopupRules) do
            if r.trigger == "unit_built" then
                if r.scope == "global" or (r.scope == "player" and IsTargetArmy(army)) or r.scope == "allies" then
                    if MatchesUnit(r, self) then
                        FirePopupAlert(r, self)
                    end
                end
            end
        end
        return result
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self:GetArmy()
        local pos = self:GetPosition()
        local savedPos = pos and {{pos[1], pos[2], pos[3]}} or nil
        for _, r in ipairs(PopupRules) do
            if r.trigger == "unit_killed" then
                if r.scope == "global" or (r.scope == "player" and IsTargetArmy(army)) or r.scope == "allies" then
                    if MatchesUnit(r, self) then
                        FirePopupAlert(r, self, savedPos)
                    end
                end
            end
        end
        return OldUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    OnDamage = function(self, instigator, amount, vector, damageType)
        local army = self:GetArmy()
        if not self.AlertHealthFired and not self:BeenDestroyed() and not self:IsDead() then
            local maxHp = self:GetMaxHealth()
            local curHp = self:GetHealth()
            if maxHp and maxHp > 0 and curHp and curHp > 0 then
                local pct = (curHp / maxHp) * 100
                for _, r in ipairs(PopupRules) do
                    if r.trigger == "health_low" and r.healthPct and pct <= r.healthPct then
                        if r.scope == "global" or (r.scope == "player" and IsTargetArmy(army)) or r.scope == "allies" then
                            if MatchesUnit(r, self) then
                                self.AlertHealthFired = true
                                FirePopupAlert(r, self)
                                break
                            end
                        end
                    end
                end
            end
        end
        return OldUnit.OnDamage(self, instigator, amount, vector, damageType)
    end,
}}
"""
    with open(hook_sim_dir / "Unit.lua", "w", encoding="utf-8") as f:
        f.write(sim_unit_lua_content)

    # 3. Hook UI gamemain.lua
    hook_ui_dir = target_mod_dir / "hook" / "lua" / "ui" / "game"
    hook_ui_dir.mkdir(parents=True, exist_ok=True)

    ui_gamemain_lua_content = """-- Auto-generated by FAF Mod Forge
-- In-Game Tactical Event Popups UI Handler

local UIUtil = import('/lua/ui/uiutil.lua')
local LayoutHelpers = import('/lua/maui/layouthelpers.lua')
local MauiGroup = import('/lua/maui/group.lua').Group
local MauiBitmap = import('/lua/maui/bitmap.lua').Bitmap
local MauiButton = import('/lua/maui/button.lua').Button
local MauiText = import('/lua/maui/text.lua').Text

local function CleanText(s)
    if not s then return "" end
    if LOC then
        s = LOC(tostring(s))
    end
    local res, _ = string.gsub(tostring(s), "<LOC [^>]*>", "")
    return tostring(res)
end

local function MatchesPlayerName(actualName, targetName)
    if not actualName or not targetName or targetName == "" then return false end
    local a = string.lower(actualName)
    local t = string.lower(targetName)
    if a == t then return true end
    if string.find(a, t, 1, true) then return true end
    local stripped = string.gsub(a, "%b[]", "")
    stripped = string.gsub(stripped, "%b()", "")
    stripped = string.gsub(stripped, "^%s*(.-)%s*$", "%1")
    if stripped == t or string.find(stripped, t, 1, true) then return true end
    return false
end

local activeAlertCards = {}

local function ShowTacticalPopup(data)
    local focusArmy = GetFocusArmy()

    -- Filter check for player target scope
    if data.targetScope == "player" and data.targetPlayer and data.targetPlayer ~= "" then
        local armies = GetArmiesTable()
        local myName = armies and armies.armiesTable and armies.armiesTable[focusArmy] and armies.armiesTable[focusArmy].nickname
        if myName and not MatchesPlayerName(myName, data.targetPlayer) then
            return
        end
    end

    local parent = GetFrame(0)
    if not parent then return end

    -- Container card
    local card = MauiGroup(parent)

    local function DismissAlert()
        if not card then return end
        local c = card
        card = nil
        for i, activeCard in ipairs(activeAlertCards) do
            if activeCard == c then
                table.remove(activeAlertCards, i)
                break
            end
        end
        pcall(function() c:Destroy() end)
    end

    local ok, err = pcall(function()
        LayoutHelpers.SetDimensions(card, 420, 125)
        LayoutHelpers.AtTopIn(card, parent, 115 + (table.getn(activeAlertCards) * 132))
        LayoutHelpers.AtHorizontalCenterIn(card, parent)
        card.Depth:Set(GetFrame(0):GetTopmostDepth() + 10)

        -- Background glass (DisableHitTest so mouse clicks pass through to buttons)
        local bg = MauiBitmap(card)
        bg:SetSolidColor('F00B0F17')
        LayoutHelpers.FillParent(bg, card)
        bg:DisableHitTest(true)

        -- Border colors by theme
        local themeColor = 'FF00D2FF'
        if data.theme == "danger" then
            themeColor = 'FFEF4444'
        elseif data.theme == "tactical" then
            themeColor = 'FFF59E0B'
        elseif data.theme == "ally" then
            themeColor = 'FF10B981'
        elseif data.theme == "quantum" then
            themeColor = 'FFA855F7'
        end

        local topBorder = MauiBitmap(card)
        topBorder:SetSolidColor(themeColor)
        LayoutHelpers.SetDimensions(topBorder, 420, 3)
        LayoutHelpers.AtTopIn(topBorder, card)
        topBorder:DisableHitTest(true)

        -- Header / Title
        local title = MauiText(card)
        title:SetFont("Arial Bold", 13)
        title:SetColor('FFFFFFFF')
        title:SetText(CleanText(data.title or "TACTICAL ALERT"))
        LayoutHelpers.AtTopIn(title, card, 12)
        LayoutHelpers.AtHorizontalCenterIn(title, card)
        title:DisableHitTest(true)

        -- Body Message
        local msg = MauiText(card)
        msg:SetFont("Arial", 11)
        msg:SetColor('FFCBD5E1')
        msg:SetText(CleanText(data.text or ""))
        LayoutHelpers.Below(msg, title, 8)
        LayoutHelpers.AtHorizontalCenterIn(msg, card)
        msg:DisableHitTest(true)

        -- Buttons Group
        local btnRow = MauiGroup(card)
        LayoutHelpers.SetDimensions(btnRow, 380, 44)
        LayoutHelpers.AtBottomIn(btnRow, card, 8)
        LayoutHelpers.AtHorizontalCenterIn(btnRow, card)
        btnRow.Depth:Set(card.Depth() + 10)

        -- Button 1: Pinpoint Camera
        if data.hasPinpoint and data.pos then
            local pinBtn = UIUtil.CreateButtonStd(btnRow, '/BUTTON/medium/', "Pinpoint", 11)
            pinBtn.Depth:Set(btnRow.Depth() + 2)
            LayoutHelpers.AtLeftIn(pinBtn, btnRow, 20)
            LayoutHelpers.AtVerticalCenterIn(pinBtn, btnRow)

            pinBtn.OnClick = function(self)
                local cam = GetCamera("WorldCamera")
                if cam then
                    pcall(function()
                        local pos = Vector(data.pos[1], data.pos[2], data.pos[3])
                        local settings = cam:SaveSettings()
                        local hpr = (settings and { settings.Heading or 0, settings.Pitch or 1.28, 0 }) or { 0, 1.28, 0 }
                        local zoom = (settings and settings.Zoom) or 80
                        if zoom > 140 then zoom = 90 end
                        if zoom < 40 then zoom = 60 end
                        cam:MoveTo(pos, hpr, zoom, 0.5)
                    end)
                end
                if data.hasPing then
                    pcall(function()
                        local focusArmy = GetFocusArmy()
                        local owner = (focusArmy and focusArmy > 0) and (focusArmy - 1) or 0
                        local pos = Vector(data.pos[1], data.pos[2], data.pos[3])
                        local pingData = {
                            Owner = owner,
                            Type = 'alert',
                            Location = pos,
                        }
                        local Ping = import('/lua/ui/game/ping.lua')
                        if Ping and Ping.PingTypes and Ping.PingTypes['alert'] then
                            pingData = table.merged(pingData, Ping.PingTypes['alert'])
                        end
                        SimCallback({ Func = 'SpawnPing', Args = pingData })
                    end)
                end
                DismissAlert()
            end
        end

        -- Button 2: Dismiss
        if data.hasDismiss ~= false then
            local disBtn = UIUtil.CreateButtonStd(btnRow, '/BUTTON/medium/', "Dismiss", 11)
            disBtn.Depth:Set(btnRow.Depth() + 2)
            LayoutHelpers.AtRightIn(disBtn, btnRow, 20)
            LayoutHelpers.AtVerticalCenterIn(disBtn, btnRow)

            disBtn.OnClick = function(self)
                DismissAlert()
            end
        end

        -- Audio cue
        if data.sound and data.sound ~= "None" then
            pcall(function()
                PlaySound(Sound({Cue = data.sound, Bank = 'Interface'}))
            end)
        end

        -- Auto-dismiss timer
        local sec = data.duration or 8
        if sec > 0 then
            ForkThread(function()
                WaitSeconds(sec)
                DismissAlert()
            end)
        end

        table.insert(activeAlertCards, card)
    end)

    if not ok then
        WARN("ShowTacticalPopup error: " .. tostring(err))
        DismissAlert()
    end
end

-- Register sync callback using FAF standard UserSync API
local function HandleModForgePopups(data)
    if not data or table.getn(data) == 0 then return end
    for _, alertData in ipairs(data) do
        ShowTacticalPopup(alertData)
    end
end

if AddOnSyncHashedCallback then
    AddOnSyncHashedCallback(HandleModForgePopups, 'ModForgePopups', 'ModForgePopupsUI')
elseif AddOnSyncCallback then
    AddOnSyncCallback(function(syncTable)
        if syncTable and syncTable.ModForgePopups then
            HandleModForgePopups(syncTable.ModForgePopups)
        end
    end, 'ModForgePopupsSync')
end
"""
    with open(hook_ui_dir / "gamemain.lua", "w", encoding="utf-8") as f:
        f.write(ui_gamemain_lua_content)

    # 4. Create zip file in exports/
    zip_path = EXPORTS_DIR / f"{safe_folder_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(target_mod_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = Path(safe_folder_name) / file_path.relative_to(target_mod_dir)
                zipf.write(file_path, arcname)

    return {
        "success": True,
        "modName": mod_name,
        "folderName": safe_folder_name,
        "targetModDir": str(target_mod_dir),
        "zipPath": str(zip_path),
        "rulesCount": len(rules),
        "targetMode": target_mode,
        "playerName": player_name,
    }


def format_unit_configs_lua_entries(unit_configs, indent="    "):
    lua_entries = []
    for uid, cfg in (unit_configs or {}).items():
        hp_m = round(float(cfg.get("hpMult", 1.0)), 2)
        regen_m = round(float(cfg.get("regenMult", 1.0)), 2)
        shield_m = round(float(cfg.get("shieldMult", 1.0)), 2)
        shield_regen_m = round(float(cfg.get("shieldRegenMult", 1.0)), 2)

        md = float(cfg.get("massDiscount", 0.0))
        if md > 1.0: md = md / 100.0
        md = round(md, 2)

        ed = float(cfg.get("energyDiscount", 0.0))
        if ed > 1.0: ed = ed / 100.0
        ed = round(ed, 2)

        btd = float(cfg.get("buildTimeDiscount", 0.0))
        if btd > 1.0: btd = btd / 100.0
        btd = round(btd, 2)

        brm = round(float(cfg.get("buildRateMult", 1.0)), 2)
        prod_m = round(float(cfg.get("prodMult", 1.0)), 2)

        sm = round(float(cfg.get("speedMult", 1.0)), 2)
        trm = round(float(cfg.get("turnRateMult", 1.0)), 2)
        vm = round(float(cfg.get("visionMult", 1.0)), 2)
        rm = round(float(cfg.get("radarMult", 1.0)), 2)

        dm = round(float(cfg.get("damageMult", 1.0)), 2)
        range_m = round(float(cfg.get("rangeMult", 1.0)), 2)
        rof_m = round(float(cfg.get("rofMult", 1.0)), 2)
        aoe_m = round(float(cfg.get("aoeMult", 1.0)), 2)
        mv_m = round(float(cfg.get("muzzleVelMult", 1.0)), 2)

        entry = (
            f'{indent}["{uid.lower()}"] = {{ '
            f'hpMult = {hp_m}, regenMult = {regen_m}, shieldMult = {shield_m}, shieldRegenMult = {shield_regen_m}, '
            f'massDiscount = {md}, energyDiscount = {ed}, buildTimeDiscount = {btd}, buildRateMult = {brm}, prodMult = {prod_m}, '
            f'speedMult = {sm}, turnRateMult = {trm}, visionMult = {vm}, radarMult = {rm}, '
            f'damageMult = {dm}, rangeMult = {range_m}, rofMult = {rof_m}, aoeMult = {aoe_m}, muzzleVelMult = {mv_m} }}'
        )
        lua_entries.append(entry)
    return ",\n".join(lua_entries)


def format_limits_rules_lua_entries(limits_rules, indent="    "):
    rules_lua_entries = []
    for r in (limits_rules or []):
        rid = r.get("id", "rule")
        rname = r.get("name", "Custom Unit").replace('"', '\\"')
        rlimit = int(r.get("limit", 1))
        rcat = r.get("categoryLua") or r.get("category") or r.get("categoryTag") or PRESET_LIMIT_CATEGORIES.get(rid, "")
        unit_ids = r.get("unitIds", [])
        if not rcat:
            if unit_ids:
                rcat = " + ".join([f"categories.{uid.upper()}" for uid in unit_ids])
            else:
                continue
        rules_lua_entries.append(
            f'{indent}{{\n'
            f'{indent}    id = "{rid}",\n'
            f'{indent}    name = "{rname}",\n'
            f'{indent}    limit = {rlimit},\n'
            f'{indent}    category = {rcat},\n'
            f'{indent}}}'
        )
    return ",\n".join(rules_lua_entries)


def format_lootbox_lua_table(cfg, indent="    "):
    if not cfg:
        return f"{indent}enabled = false"

    enabled = "true" if cfg.get("enabled", True) else "false"
    name = (cfg.get("name") or "Quantum Surprise Vault").replace('"', '\\"')
    model_bp = cfg.get("modelBpId") or "uec1904"
    spawn_delay = int(cfg.get("spawnDelay", 30))
    spawn_count = int(cfg.get("spawnCount", 2))
    loc_mode = cfg.get("locMode", "center")
    cx = float(cfg.get("customX", 256))
    cz = float(cfg.get("customZ", 256))
    claim_mode = cfg.get("claimMode", "both")
    respawn_mode = cfg.get("respawnMode", "reusable")
    cooldown_sec = int(cfg.get("cooldownSec", 60))
    cost_energy = int(cfg.get("spinCostEnergy", 500))
    cost_mass = int(cfg.get("spinCostMass", 0))

    open_mode = cfg.get("openMode", "instant_crack")
    obs_name = (cfg.get("observerGmName") or "DrReed").replace('"', '\\"')
    obs_placement = "true" if cfg.get("observerGmPlacement", True) else "false"

    drop_table_entries = []
    for item in cfg.get("dropTable", []):
        iid = item.get("id", "drop")
        iname = item.get("name", "Prize").replace('"', '\\"')
        itype = item.get("type", "spawn_unit")
        irarity = item.get("rarity", "common")
        iweight = int(item.get("weight", 50))
        iunit_id = (item.get("unitId") or "").strip().lower()
        icount = int(item.get("unitCount", 1))
        imass = int(item.get("mass", 0))
        ienergy = int(item.get("energy", 0))
        imass_drain = int(item.get("massDrain", 0))
        ienergy_drain = int(item.get("energyDrain", 0))
        reels = item.get("reels", ["🌟", "🌟", "🌟"])
        reels_lua = "{" + ", ".join(f'"{r}"' for r in reels) + "}"
        idesc = (item.get("desc") or "").replace('"', '\\"')

        drop_table_entries.append(
            f'{indent}        {{\n'
            f'{indent}            id = "{iid}",\n'
            f'{indent}            name = "{iname}",\n'
            f'{indent}            type = "{itype}",\n'
            f'{indent}            rarity = "{irarity}",\n'
            f'{indent}            weight = {iweight},\n'
            f'{indent}            unitId = "{iunit_id}",\n'
            f'{indent}            unitCount = {icount},\n'
            f'{indent}            mass = {imass},\n'
            f'{indent}            energy = {ienergy},\n'
            f'{indent}            massDrain = {imass_drain},\n'
            f'{indent}            energyDrain = {ienergy_drain},\n'
            f'{indent}            reels = {reels_lua},\n'
            f'{indent}            desc = "{idesc}",\n'
            f'{indent}        }}'
        )

    drop_table_lua = ",\n".join(drop_table_entries)

    return f"""{indent}enabled = {enabled},
{indent}name = "{name}",
{indent}modelBpId = "{model_bp}",
{indent}openMode = "{open_mode}",
{indent}observerGmName = "{obs_name}",
{indent}allowObserverPlacement = {obs_placement},
{indent}spawnDelay = {spawn_delay},
{indent}spawnCount = {spawn_count},
{indent}locMode = "{loc_mode}",
{indent}customX = {cx},
{indent}customZ = {cz},
{indent}claimMode = "{claim_mode}",
{indent}respawnMode = "{respawn_mode}",
{indent}cooldownSec = {cooldown_sec},
{indent}spinCostEnergy = {cost_energy},
{indent}spinCostMass = {cost_mass},
{indent}dropTable = {{
{drop_table_lua}
{indent}}}"""


def generate_lootbox_mod_files(data):
    mod_name = data.get("modName", "").strip() or "Surprise Casino Lootbox"
    author = data.get("author", "").strip() or "User"
    version = int(data.get("version", 1))
    target_mode = data.get("targetMode", "player")  # "player" or "global"
    player_name = data.get("playerName", "").strip()
    lootbox_config = data.get("lootboxConfig", {})

    drop_table = lootbox_config.get("dropTable", [])
    if not drop_table:
        raise ValueError("At least one outcome must be configured in the Drop Table.")

    mod_uid = str(uuid.uuid4())
    safe_folder_name = "".join(c for c in mod_name if c.isalnum() or c in (" ", "-", "_")).strip()

    target_mod_dir = DOCUMENTS_MODS_DIR / safe_folder_name
    if target_mod_dir.exists():
        shutil.rmtree(target_mod_dir)
    target_mod_dir.mkdir(parents=True, exist_ok=True)

    # 1. mod_info.lua
    description_text = f"Spawns capturable Casino Lootboxes with interactive spin mechanic & {len(drop_table)} drop outcomes. Target: {player_name if target_mode == 'player' else 'Global'}."
    mod_info_content = f"""name = "{mod_name}"
version = {version}
copyright = "none"
description = "{description_text}"
author = "{author}"
uid = "{mod_uid}"
exclusive = false
ui_only = false
selectable = true
enabled = true
requires = {{}}
conflicts = {{}}
before = {{}}
after = {{}}
"""
    with open(target_mod_dir / "mod_info.lua", "w", encoding="utf-8") as f:
        f.write(mod_info_content)

    # 2. UI Hook: gamemain.lua
    hook_ui_dir = target_mod_dir / "hook" / "lua" / "ui" / "game"
    hook_ui_dir.mkdir(parents=True, exist_ok=True)
    lb_model = lootbox_config.get("modelBpId", "uec1904")
    lb_cost = int(lootbox_config.get("spinCostEnergy", 500))
    lb_obs_name = lootbox_config.get("observerGmName", "DrReed")
    lb_obs_placement = lootbox_config.get("observerGmPlacement", True)
    ui_gamemain_lua = generate_ui_gamemain_lua(
        has_lootbox=True,
        lootbox_model=lb_model,
        spin_cost_energy=lb_cost,
        observer_gm_name=lb_obs_name,
        allow_observer_placement=lb_obs_placement
    )
    with open(hook_ui_dir / "gamemain.lua", "w", encoding="utf-8") as f:
        f.write(ui_gamemain_lua)

    # 3. Sim Hook: Unit.lua
    hook_sim_dir = target_mod_dir / "hook" / "lua" / "sim"
    hook_sim_dir.mkdir(parents=True, exist_ok=True)

    lootbox_lua = format_lootbox_lua_table(lootbox_config, indent="    ")
    sim_unit_lua = f"""-- Auto-generated by FAF Mod Forge - Surprise Casino Lootbox Mod
local TargetScope = "{target_mode}"
local TargetPlayer = "{player_name}"

local function MatchesPlayerName(actualName, targetName)
    if not actualName or not targetName or targetName == "" then return false end
    local a = string.lower(actualName)
    local t = string.lower(targetName)
    if a == t then return true end
    if string.find(a, t, 1, true) then return true end
    local stripped = string.gsub(a, "%b[]", "")
    stripped = string.gsub(stripped, "%b()", "")
    stripped = string.gsub(stripped, "^%s*(.-)%s*$", "%1")
    if stripped == t or string.find(stripped, t, 1, true) then return true end
    return false
end

local function GetNeutralArmy()
    if ScenarioInfo.ArmySetup then
        for armyName, d in pairs(ScenarioInfo.ArmySetup) do
            local upperName = string.upper(armyName)
            if string.find(upperName, "CIVILIAN") or string.find(upperName, "NEUTRAL") then
                return d.ArmyIndex or armyName
            end
        end
    end
    if ArmyBrains then
        for idx, brain in ArmyBrains do
            if brain.Civilian or (brain.Name and (string.find(string.upper(brain.Name), "CIVILIAN") or string.find(string.upper(brain.Name), "NEUTRAL"))) then
                return brain:GetArmyIndex()
            end
        end
    end
    return nil
end

local LootboxConfig = {{
{lootbox_lua}
}}

local PresetDropTables = {{
    prototype = {{
        name = "Experimental Prototype Vault",
        openMode = "instant_crack",
        modelBpId = "uec1904",
        dropTable = {{
            {{ id = "drop_proto_cybran", name = "Experimental Cybran Megabot (Monkeylord)", desc = "High-tier experimental heavy assault bot ready for combat.", type = "spawn_unit", unitId = "url0402", unitCount = 1, weight = 35, rarity = "jackpot" }},
            {{ id = "drop_proto_uef", name = "UEF Fatboy Mobile Factory", desc = "Heavy amphibious siege platform and mobile factory.", type = "spawn_unit", unitId = "uel0401", unitCount = 1, weight = 35, rarity = "jackpot" }},
            {{ id = "drop_proto_aeon", name = "Aeon Galactic Colossus", desc = "Gigantic assault bot with tractor claws.", type = "spawn_unit", unitId = "ual0401", unitCount = 1, weight = 30, rarity = "jackpot" }},
        }}
    }},
    swarm = {{
        name = "Raptor Swarm Bio-Pod",
        openMode = "instant_crack",
        modelBpId = "uec1904",
        dropTable = {{
            {{ id = "drop_raptor_boss", name = "Apex Cybran Gunship (Soul Ripper)", desc = "Experimental heavy gunship bio-mech.", type = "spawn_unit", unitId = "ura0401", unitCount = 1, weight = 20, rarity = "jackpot" }},
            {{ id = "drop_raptor_pack", name = "Raptor Strike Pack (x8 Cybran Hunters)", desc = "A ravenous pack of fast-strike combat hunters.", type = "spawn_unit", unitId = "url0106", unitCount = 8, weight = 45, rarity = "rare" }},
            {{ id = "drop_raptor_ambush", name = "Frenzied Hive Ambush", desc = "Warning: The pod released an enraged swarm of 6 hostile assault bots!", type = "spawn_hostile", unitId = "url0303", unitCount = 6, weight = 35, rarity = "disaster" }},
        }}
    }},
    supply = {{
        name = "Tactical Vanguard Armor Vault",
        openMode = "instant_crack",
        modelBpId = "uec1904",
        dropTable = {{
            {{ id = "drop_vanguard_t3", name = "T3 Heavy Armor Squadron (x6 Titans)", desc = "6 heavily armored Tier 3 frontline assault mechs.", type = "spawn_unit", unitId = "uel0303", unitCount = 6, weight = 40, rarity = "rare" }},
            {{ id = "drop_vanguard_shield", name = "Mobile Shield & Flak Convoy (x4)", desc = "Support group with mobile shield generators and flak.", type = "spawn_unit", unitId = "uel0307", unitCount = 4, weight = 35, rarity = "common" }},
            {{ id = "drop_vanguard_eco", name = "Tactical Field Reserve (+3000M / +30000E)", desc = "Emergency supply cache to kickstart T3 production.", type = "give_resources", mass = 3000, energy = 30000, weight = 25, rarity = "jackpot" }},
        }}
    }},
    motherlode = {{
        name = "Resource Motherlode Vault",
        openMode = "instant_crack",
        modelBpId = "uec1904",
        dropTable = {{
            {{ id = "drop_motherlode_massive", name = "Planetary Core Extraction (+10000 Mass / +100000 Energy)", desc = "Massive injection of supreme commander strategic reserves.", type = "give_resources", mass = 10000, energy = 100000, weight = 35, rarity = "jackpot" }},
            {{ id = "drop_motherlode_regular", name = "Refined Mass Reservoir (+4000 Mass / +40000 Energy)", desc = "Substantial economic boost for rapid expansion.", type = "give_resources", mass = 4000, energy = 40000, weight = 45, rarity = "rare" }},
            {{ id = "drop_motherlode_trap", name = "Overloaded Capacitor Trap (Detonation)", desc = "Volatile containment rupture causing 3,000 area damage!", type = "explosion_trap", weight = 20, rarity = "disaster" }},
        }}
    }},
    casino = {{
        name = "High-Roller Casino Vault",
        openMode = "interactive",
        modelBpId = "uec1904",
        dropTable = {{
            {{ id = "drop_hr_jackpot", name = "Grand Jackpot (+8000 Mass / +80000 Energy)", desc = "The triple 7s aligned! Massive resource payout.", type = "give_resources", mass = 8000, energy = 80000, weight = 20, rarity = "jackpot" }},
            {{ id = "drop_hr_flak", name = "Cybran T3 Mobile Artillery (Trebuchet x2)", desc = "Heavy long-range siege artillery pieces.", type = "spawn_unit", unitId = "url0304", unitCount = 2, weight = 35, rarity = "rare" }},
            {{ id = "drop_hr_drain", name = "House Advantage (Resource Siphon)", desc = "The casino takes its cut: drained -2500 Mass and -20000 Energy!", type = "take_resources", massDrain = 2500, energyDrain = 20000, weight = 25, rarity = "unlucky" }},
            {{ id = "drop_hr_ambush", name = "Bouncer Ambush (Loyalist Hit Squad)", desc = "Security enforcers sent to terminate lucky winners!", type = "spawn_hostile", unitId = "url0303", unitCount = 4, weight = 20, rarity = "disaster" }},
        }}
    }}
}}

local function RollLootboxOutcome(cfg)
    local tableEntries = (cfg and cfg.dropTable) or {{}}
    if table.getn(tableEntries) == 0 then return nil end
    local totalWeight = 0
    for _, item in ipairs(tableEntries) do
        totalWeight = totalWeight + (item.weight or 10)
    end
    local roll = Random(1, math.max(1, totalWeight))
    local selected = tableEntries[1]
    for _, item in ipairs(tableEntries) do
        local w = item.weight or 10
        if roll <= w then
            selected = item
            break
        end
        roll = roll - w
    end
    return selected
end

local function ResolveLootboxOutcome(unit, army, outcome, cfg)
    if not unit or unit:BeenDestroyed() or unit:IsDead() then return end
    local brain = ArmyBrains and ArmyBrains[army]
    local armySetup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[army]
    local playerName = (armySetup and armySetup.PlayerName) or (brain and brain.Nickname) or ("Player " .. tostring(army))

    local pos = unit:GetPosition()
    local spawnX = pos[1] + 5
    local spawnZ = pos[3] + 5
    local spawnY = GetSurfaceHeight(spawnX, spawnZ)

    if outcome.type == "spawn_unit" or outcome.type == "spawn_structure" then
        local count = outcome.unitCount or 1
        local bpId = outcome.unitId or "uel0202"
        for i = 1, count do
            local offX = (i - 1) * 3
            local offZ = (i % 2 == 0) and 2 or -2
            pcall(function()
                local spawned = CreateUnitHPR(bpId, army, spawnX + offX, spawnY, spawnZ + offZ, 0, 0, 0)
                if spawned then
                    CreateEmitterAtEntity(spawned, army, '/effects/emitters/flash_01_emit.bp')
                end
            end)
        end
        PrintText("🎉 [LOOTBOX DROP] " .. playerName .. " won: " .. tostring(outcome.name) .. "!", 18, "ff34d399", 6, "center")

    elseif outcome.type == "give_resources" then
        if brain then
            if outcome.mass and outcome.mass > 0 then brain:GiveResource('Mass', outcome.mass) end
            if outcome.energy and outcome.energy > 0 then brain:GiveResource('Energy', outcome.energy) end
        end
        PrintText("🪙 [LOOTBOX JACKPOT] " .. playerName .. " won +" .. tostring(outcome.mass or 0) .. " Mass & +" .. tostring(outcome.energy or 0) .. " Energy!", 18, "ffffd700", 6, "center")

    elseif outcome.type == "take_resources" then
        if brain then
            if outcome.massDrain and outcome.massDrain > 0 then brain:TakeResource('Mass', outcome.massDrain) end
            if outcome.energyDrain and outcome.energyDrain > 0 then brain:TakeResource('Energy', outcome.energyDrain) end
        end
        PrintText("💸 [LOOTBOX SIPHON] " .. playerName .. " was siphoned: -" .. tostring(outcome.massDrain or 0) .. " Mass & -" .. tostring(outcome.energyDrain or 0) .. " Energy!", 18, "fff97316", 6, "center")

    elseif outcome.type == "spawn_hostile" then
        local neutralArmy = GetNeutralArmy()
        if not neutralArmy then
            if ArmyBrains then
                for idx, b in ArmyBrains do
                    if b:GetArmyIndex() ~= army then
                        neutralArmy = b:GetArmyIndex()
                        break
                    end
                end
            end
            if not neutralArmy then neutralArmy = 1 end
        end

        pcall(function()
            SetAlliance(neutralArmy, army, 'Enemy')
            SetAlliance(army, neutralArmy, 'Enemy')
        end)

        local count = outcome.unitCount or 3
        local bpId = outcome.unitId or "url0303"
        local spawnedHostiles = {{}}
        for i = 1, count do
            local offX = (i - 1) * 4
            local offZ = (i % 2 == 0) and 3 or -3
            pcall(function()
                local hUnit = CreateUnitHPR(bpId, neutralArmy, spawnX + offX, spawnY, spawnZ + offZ, 0, 0, 0)
                if hUnit then
                    hUnit:SetDoNotTarget(false)
                    hUnit:SetCanTakeDamage(true)
                    table.insert(spawnedHostiles, hUnit)
                    CreateEmitterAtEntity(hUnit, neutralArmy, '/effects/emitters/sparks_07_emit.bp')
                end
            end)
        end
        if table.getn(spawnedHostiles) > 0 then
            pcall(function()
                IssueAggressiveMove(spawnedHostiles, {{ pos[1], pos[2], pos[3] }})
            end)
        end
        PrintText("💀 [LOOTBOX AMBUSH] " .. playerName .. " triggered an AMBUSH! Hostile forces emerged!", 18, "ffef4444", 8, "center")

    elseif outcome.type == "explosion_trap" then
        pcall(function()
            DamageArea(unit, pos, 18, 2500, 'Normal', false)
            CreateEmitterAtEntity(unit, army, '/effects/emitters/destruction_explosion_concussion_ring_01_emit.bp')
        end)
        PrintText("💥 [LOOTBOX DETONATION] Vault booby trap detonated in a violent explosion!", 18, "ffff2222", 6, "center")
    end

    pcall(function()
        Sync.ModForgePopups = Sync.ModForgePopups or {{}}
        table.insert(Sync.ModForgePopups, {{
            id = "casino_result_" .. tostring(outcome.id or "prize"),
            title = (cfg and cfg.openMode == "instant_crack") and "📦 CRATE CRACKED" or "🎰 CASINO OUTCOME",
            text = playerName .. ": " .. tostring(outcome.name) .. "! (" .. tostring(outcome.desc or "") .. ")",
            pos = {{ pos[1], pos[2], pos[3] }},
            sound = (outcome.rarity == 'disaster') and "UI_Radar_Blip" or "UI_Score_Window_Open",
            theme = (outcome.rarity == 'disaster') and "danger" or ((outcome.rarity == 'jackpot') and "quantum" or "tactical"),
            hasPinpoint = true,
            hasPing = true,
            hasDismiss = true,
            duration = 10,
            scope = "global",
            targetPlayer = "",
        }})
    end)

    if (cfg and cfg.openMode == "instant_crack") or (cfg and cfg.respawnMode == "single_use") then
        pcall(function()
            CreateEmitterAtEntity(unit, army, '/effects/emitters/flash_01_emit.bp')
        end)
        unit:Destroy()
    else
        unit.IsSpinning = false
        local coolSec = (cfg and cfg.cooldownSec) or 60
        unit.CooldownUntil = ((GetGameTimeSeconds and GetGameTimeSeconds()) or 0) + coolSec
    end
end

SimCallbacks = SimCallbacks or {{}}
SimCallbacks.ModForgeAdminPlaceLootbox = function(data, cbArmy)
    local pos = data.Pos
    if not pos then return end
    local presetKey = data.Preset or "prototype"
    local cfgToUse = LootboxConfig
    if presetKey and PresetDropTables[presetKey] then
        local pDef = PresetDropTables[presetKey]
        cfgToUse = {{
            enabled = true,
            name = pDef.name or LootboxConfig.name or "Airdrop Lootbox",
            modelBpId = pDef.modelBpId or LootboxConfig.modelBpId or "uec1904",
            openMode = pDef.openMode or "instant_crack",
            claimMode = LootboxConfig.claimMode or "both",
            respawnMode = (pDef.openMode == "instant_crack") and "single_use" or (LootboxConfig.respawnMode or "single_use"),
            spinCostEnergy = (pDef.openMode == "instant_crack") and 0 or (LootboxConfig.spinCostEnergy or 500),
            spinCostMass = (pDef.openMode == "instant_crack") and 0 or (LootboxConfig.spinCostMass or 0),
            dropTable = pDef.dropTable,
        }}
    end
    ForkThread(SpawnLootboxInstance, cfgToUse, 1, pos)
end

SimCallbacks.ModForgeLootboxSpin = function(data, cbArmy)
    local entityId = data.EntityId
    local army = data.Army or cbArmy
    if not entityId or not army then return end

    local brain = ArmyBrains and ArmyBrains[army]
    local armySetup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[army]
    local playerName = (armySetup and armySetup.PlayerName) or (brain and brain.Nickname) or ("Player " .. tostring(army))

    if TargetScope == "player" and TargetPlayer ~= "" then
        if not MatchesPlayerName(playerName, TargetPlayer) then
            PrintText("⚠️ Only " .. TargetPlayer .. " can play this Casino Vault!", 16, "ffff5555", 3, "center")
            return
        end
    end

    local unit = nil
    if brain then
        local units = brain:GetListOfUnits(categories.ALLUNITS, false) or {{}}
        for _, u in ipairs(units) do
            if not u:BeenDestroyed() and not u:IsDead() and u:GetEntityId() == entityId then
                unit = u
                break
            end
        end
    end

    if not unit or not unit.IsCasinoLootbox then return end
    if unit.IsSpinning then
        PrintText("⏳ Casino Vault is already spinning!", 14, "ffffaa33", 2, "center")
        return
    end

    local curTime = (GetGameTimeSeconds and GetGameTimeSeconds()) or 0
    if unit.CooldownUntil and curTime < unit.CooldownUntil then
        local rem = math.ceil(unit.CooldownUntil - curTime)
        PrintText("⏳ Vault is recharging (" .. rem .. "s remaining)", 14, "ffff5555", 3, "center")
        return
    end

    local cfg = unit.LootboxConfig or LootboxConfig
    local costEnergy = cfg.spinCostEnergy or 0
    local costMass = cfg.spinCostMass or 0

    if brain and (costEnergy > 0 or costMass > 0) then
        local curE = brain:GetEconomyStored('ENERGY') or 0
        local curM = brain:GetEconomyStored('MASS') or 0
        if curE < costEnergy or curM < costMass then
            PrintText("⚠️ Insufficient resources! Requires " .. costEnergy .. " Energy / " .. costMass .. " Mass", 16, "ffff4444", 4, "center")
            return
        end
        if costEnergy > 0 then brain:TakeResource('ENERGY', costEnergy) end
        if costMass > 0 then brain:TakeResource('MASS', costMass) end
    end

    unit.IsSpinning = true

    local selected = RollLootboxOutcome(cfg)
    if not selected then return end

    pcall(function()
        CreateEmitterAtEntity(unit, army, '/effects/emitters/flash_01_emit.bp')
        CreateEmitterAtEntity(unit, army, '/effects/emitters/sparks_07_emit.bp')
    end)

    PrintText("🎰 [CASINO SPIN] " .. playerName .. " pulled the lever! Reels spinning...", 16, "ffffd700", 3, "center")

    pcall(function()
        Sync.ModForgeCasinoSpin = Sync.ModForgeCasinoSpin or {{}}
        table.insert(Sync.ModForgeCasinoSpin, {{
            entityId = entityId,
            army = army,
            outcome = selected,
            duration = 3.2,
        }})
    end)

    ForkThread(function()
        WaitSeconds(3.2)
        ResolveLootboxOutcome(unit, army, selected, cfg)
    end)
end

local function SpawnLootboxInstance(cfg, index, customPos)
    if not cfg or not cfg.enabled then return end
    if cfg.locMode == "observer_only" and not customPos then
        return
    end
    if not customPos and cfg.spawnDelay and cfg.spawnDelay > 0 then
        WaitSeconds(cfg.spawnDelay)
    end

    local bpId = (cfg.modelBpId and cfg.modelBpId ~= "" and cfg.modelBpId) or "uec1904"
    local sizeX = (ScenarioInfo.size and ScenarioInfo.size[1]) or 512
    local sizeZ = (ScenarioInfo.size and ScenarioInfo.size[2]) or 512
    local centerX = sizeX / 2
    local centerZ = sizeZ / 2

    local posX = centerX
    local posZ = centerZ
    if customPos then
        posX = customPos[1]
        posZ = customPos[3] or customPos[2]
    elseif cfg.locMode == "coords" and cfg.customX and cfg.customZ then
        posX = cfg.customX
        posZ = cfg.customZ
    elseif cfg.locMode == "random_center" or (index and index > 1) then
        local angle = Random(0, 360) * (math.pi / 180)
        local dist = Random(35, 80)
        posX = math.max(25, math.min(sizeX - 25, centerX + math.cos(angle) * dist))
        posZ = math.max(25, math.min(sizeZ - 25, centerZ + math.sin(angle) * dist))
    end
    local posY = GetSurfaceHeight(posX, posZ)

    local neutralArmy = GetNeutralArmy()
    if not neutralArmy then
        local focus = GetFocusArmy()
        if ArmyBrains then
            for idx, brain in ArmyBrains do
                if brain:GetArmyIndex() ~= focus then
                    neutralArmy = brain:GetArmyIndex()
                    break
                end
            end
        end
        if not neutralArmy then
            neutralArmy = (ArmyBrains and ArmyBrains[1] and ArmyBrains[1]:GetArmyIndex()) or 1
        end
    end

    local fallbackIdx = (ArmyBrains and ArmyBrains[1] and ArmyBrains[1]:GetArmyIndex()) or 1
    local vault = nil
    pcall(function()
        vault = CreateUnitHPR(bpId, neutralArmy, posX, posY, posZ, 0, 0, 0)
    end)
    if not vault then
        pcall(function()
            vault = CreateUnitHPR(bpId, fallbackIdx, posX, posY, posZ, 0, 0, 0)
            neutralArmy = fallbackIdx
        end)
    end
    if not vault then
        pcall(function()
            vault = CreateUnitHPR("uec1904", fallbackIdx, posX, posY, posZ, 0, 0, 0)
            neutralArmy = fallbackIdx
        end)
    end

    if not vault then
        WARN("FAF Mod Forge: Failed to spawn casino vault: " .. tostring(bpId))
        return
    end

    vault.IsCasinoLootbox = true
    vault.LootboxConfig = cfg

    vault:SetCapturable(true)
    vault:SetReclaimable(false)
    vault:SetCanTakeDamage(true)
    vault:SetMaxHealth(15000)
    vault:SetHealth(vault, 15000)
    if vault.SetCaptureTimeMultiplier then
        vault:SetCaptureTimeMultiplier(0.08)
    end

    if ArmyBrains then
        for idx, brain in ArmyBrains do
            SetAlliance(neutralArmy, brain:GetArmyIndex(), 'Neutral')
            SetAlliance(brain:GetArmyIndex(), neutralArmy, 'Neutral')
        end
    end

    pcall(function()
        vault:SetIntelRadius('Vision', 28)
        vault:SetIntelRadius('Omni', 35)
        vault:EnableIntel('Vision')
        vault:EnableIntel('Omni')
    end)

    pcall(function()
        Sync.CreatePing = Sync.CreatePing or {{}}
        table.insert(Sync.CreatePing, {{ Owner = 0, Type = 'alert', Location = {{posX, posY, posZ}} }})
    end)

    if customPos then
        PrintText("📦 [GM AIRDROP] " .. tostring(cfg.name or "Quantum Vault") .. " seeded at (" .. math.floor(posX) .. ", " .. math.floor(posZ) .. ")! Capture and claim it!", 18, "ff38bdf8", 8, "center")
    else
        PrintText("🎰 [CASINO VAULT ONLINE] " .. tostring(cfg.name or "Quantum Vault") .. " has appeared at (" .. math.floor(posX) .. ", " .. math.floor(posZ) .. ")! Capture and claim it!", 18, "ffffd700", 8, "center")
    end

    if cfg.claimMode == "proximity" or cfg.claimMode == "both" then
        ForkThread(function()
            while vault and not vault:BeenDestroyed() and not vault:IsDead() and (vault:GetArmy() == neutralArmy) do
                local vPos = vault:GetPosition()
                if ArmyBrains then
                    for _, brain in ArmyBrains do
                        local bArmy = brain:GetArmyIndex()
                        if bArmy ~= neutralArmy then
                            local checkUnits = brain:GetListOfUnits(categories.MOBILE + categories.COMMAND, false) or {{}}
                            for _, u in ipairs(checkUnits) do
                                if not u:BeenDestroyed() and not u:IsDead() and VDist3(u:GetPosition(), vPos) <= 15.0 then
                                    vault = ChangeUnitArmy(vault, bArmy)
                                    if vault then
                                        vault.IsCasinoLootbox = true
                                        vault.LootboxConfig = cfg
                                        local armySetup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[bArmy]
                                        local pName = (armySetup and armySetup.PlayerName) or brain.Nickname or ("Player " .. tostring(bArmy))
                                        
                                        if cfg.openMode == "instant_crack" then
                                            local outcome = RollLootboxOutcome(cfg)
                                            if outcome then
                                                PrintText("📦💥 [LOOTBOX CRACKED] " .. pName .. " reached & cracked the crate! RUN FOR IT!", 18, "ff34d399", 6, "center")
                                                pcall(function()
                                                    CreateEmitterAtEntity(vault, bArmy, '/effects/emitters/flash_01_emit.bp')
                                                    CreateEmitterAtEntity(vault, bArmy, '/effects/emitters/destruction_explosion_concussion_ring_01_emit.bp')
                                                end)
                                                ResolveLootboxOutcome(vault, bArmy, outcome, cfg)
                                            end
                                        else
                                            PrintText("🎰 [CASINO SECURED] " .. pName .. " reached the Vault! Select it and click PLAY CASINO!", 18, "ffffd700", 6, "center")
                                            CreateEmitterAtEntity(vault, bArmy, '/effects/emitters/flash_01_emit.bp')
                                        end
                                    end
                                    return
                                end
                            end
                        end
                    end
                end
                WaitSeconds(0.5)
            end
        end)
    end
end

ForkThread(function()
    WaitSeconds(2)
    if LootboxConfig and LootboxConfig.enabled then
        local count = LootboxConfig.spawnCount or 1
        for i = 1, count do
            ForkThread(SpawnLootboxInstance, LootboxConfig, i)
        end
    end
end)

local OldUnit = Unit
Unit = Class(OldUnit) {{
    OnCaptured = function(self, captor)
        local result = OldUnit.OnCaptured(self, captor)
        if self.IsCasinoLootbox and not self.LootboxCracked then
            self.IsCasinoLootbox = true
            local captorArmy = captor and captor:GetArmy()
            if captorArmy then
                local cfg = self.LootboxConfig or LootboxConfig
                local brain = ArmyBrains and ArmyBrains[captorArmy]
                local armySetup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[captorArmy]
                local pName = (armySetup and armySetup.PlayerName) or (brain and brain.Nickname) or ("Player " .. tostring(captorArmy))
                
                if cfg and cfg.openMode == "instant_crack" then
                    self.LootboxCracked = true
                    local outcome = RollLootboxOutcome(cfg)
                    if outcome then
                        PrintText("📦💥 [LOOTBOX CRACKED] " .. pName .. " captured & cracked the crate! RUN FOR IT!", 18, "ff34d399", 6, "center")
                        pcall(function()
                            CreateEmitterAtEntity(self, captorArmy, '/effects/emitters/flash_01_emit.bp')
                            CreateEmitterAtEntity(self, captorArmy, '/effects/emitters/destruction_explosion_concussion_ring_01_emit.bp')
                        end)
                        ResolveLootboxOutcome(self, captorArmy, outcome, cfg)
                    end
                else
                    PrintText("🎰 [CASINO CAPTURED] " .. pName .. " secured the Vault! Select it and click PLAY CASINO to spin!", 18, "ffffd700", 6, "center")
                end
            end
        end
        return result
    end,
}}
"""
    with open(hook_sim_dir / "Unit.lua", "w", encoding="utf-8") as f:
        f.write(sim_unit_lua)

    # 4. Create zip file in exports/
    zip_path = EXPORTS_DIR / f"{safe_folder_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(target_mod_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = Path(safe_folder_name) / file_path.relative_to(target_mod_dir)
                zipf.write(file_path, arcname)

    return {
        "success": True,
        "modName": mod_name,
        "folderName": safe_folder_name,
        "targetModDir": str(target_mod_dir),
        "zipPath": str(zip_path),
        "outcomesCount": len(drop_table),
        "targetMode": target_mode,
        "playerName": player_name,
    }


def generate_combined_mod_files(data):
    mod_name = data.get("modName", "").strip() or "FAF Master Overhaul"
    author = data.get("author", "").strip() or "User"
    version = int(data.get("version", 1))
    target_mode = data.get("targetMode", "player")  # "player", "global", or "multiplayer"
    player_name = data.get("playerName", "").strip()
    player_profiles = data.get("playerProfiles", []) if target_mode == "multiplayer" else []

    include_buffs = bool(data.get("includeBuffs", True))
    include_limits = bool(data.get("includeLimits", True))
    include_popups = bool(data.get("includePopups", True))
    include_relics = bool(data.get("includeRelics", True))
    include_lootbox = bool(data.get("includeLootbox", True))

    unit_configs = data.get("unitConfigs", {}) if include_buffs else {}
    limits_rules = data.get("limitsRules", []) if include_limits else []
    popup_rules = data.get("popupRules", []) if include_popups else []
    relic_objectives = data.get("relicObjectives", []) if include_relics else []
    lootbox_config = data.get("lootboxConfig", {}) if include_lootbox else {}

    has_buffs = len(unit_configs) > 0
    has_limits = len(limits_rules) > 0
    has_popups = len(popup_rules) > 0
    has_relics = len(relic_objectives) > 0
    has_lootbox = bool(lootbox_config and lootbox_config.get("enabled", True) and lootbox_config.get("dropTable"))
    has_profiles = len(player_profiles) > 0

    lb_count = 1 if has_lootbox else 0
    if target_mode == "multiplayer":
        if not has_profiles:
            raise ValueError("At least one player profile must be configured for Multiplayer mode.")
        total_rules = len(player_profiles) + len(popup_rules) + len(relic_objectives) + lb_count
    else:
        total_rules = len(unit_configs) + len(limits_rules) + len(popup_rules) + len(relic_objectives) + lb_count
        if total_rules == 0:
            raise ValueError("At least one rule must be configured across the selected modules.")

    mod_uid = str(uuid.uuid4())
    safe_folder_name = "".join(c for c in mod_name if c.isalnum() or c in (" ", "-", "_")).strip()

    target_mod_dir = DOCUMENTS_MODS_DIR / safe_folder_name
    if target_mod_dir.exists():
        shutil.rmtree(target_mod_dir)
    target_mod_dir.mkdir(parents=True, exist_ok=True)

    # 1. mod_info.lua
    breakdown_parts = []
    if target_mode == "multiplayer":
        breakdown_parts.append(f"{len(player_profiles)} Player Profiles")
    else:
        if has_buffs:
            breakdown_parts.append(f"{len(unit_configs)} Unit Stat Buffs")
        if has_limits:
            breakdown_parts.append(f"{len(limits_rules)} Unit Limits")
    if has_popups:
        breakdown_parts.append(f"{len(popup_rules)} Tactical Popups")
    if has_relics:
        breakdown_parts.append(f"{len(relic_objectives)} Relic Objectives")
    if has_lootbox:
        breakdown_parts.append(f"Surprise Casino ({len(lootbox_config.get('dropTable', []))} Outcomes)")

    breakdown_text = ", ".join(breakdown_parts)
    if target_mode == "multiplayer":
        p_names = [p.get("playerName", "Player") for p in player_profiles if p.get("playerName")]
        names_str = ", ".join(p_names[:3]) + (f" (+{len(p_names)-3} more)" if len(p_names) > 3 else "")
        scope_text = f"Target: Multiplayer Profiles ({names_str})"
    elif target_mode == "player":
        scope_text = f"Target: {player_name} (Sim Hook)"
    else:
        scope_text = "Target: Global (All Players)"

    description_text = f"Combined FAF Master Mod: {breakdown_text}. {scope_text}."

    mod_info_content = f"""name = "{mod_name}"
version = {version}
copyright = "none"
description = "{description_text}"
author = "{author}"
uid = "{mod_uid}"
exclusive = false
ui_only = false
selectable = true
enabled = true
requires = {{}}
conflicts = {{}}
before = {{}}
after = {{}}
"""
    with open(target_mod_dir / "mod_info.lua", "w", encoding="utf-8") as f:
        f.write(mod_info_content)

    # Lua tables generation
    unit_table_lua = format_unit_configs_lua_entries(unit_configs, indent="    ") if has_buffs else ""
    limits_table_lua = format_limits_rules_lua_entries(limits_rules, indent="    ") if has_limits else ""

    player_profiles_lua = ""
    if target_mode == "multiplayer":
        prof_entries = []
        has_default_fallback = False
        for p in player_profiles:
            p_name = p.get("playerName", "").strip()
            if not p_name:
                continue
            if p_name in ("*", "default"):
                has_default_fallback = True

            p_key = p_name.lower()
            role_name = p.get("roleName", "Custom Role").replace('"', '\\"')
            dmg_dealt = round(float(p.get("damageDealtMult", 1.0)), 2)
            dmg_taken = round(float(p.get("damageTakenMult", 1.0)), 2)
            br_mult = round(float(p.get("buildRateMult", 1.0)), 2)
            pr_mult = round(float(p.get("prodMult", 1.0)), 2)

            buffs_mode = p.get("buffsMode", "global")
            if buffs_mode == "global":
                p_unit_configs = unit_configs
            elif buffs_mode == "custom":
                p_unit_configs = p.get("customBuffs", {})
            else:
                p_unit_configs = {}

            limits_mode = p.get("limitsMode", "global")
            if limits_mode == "global":
                p_limits_rules = limits_rules
            elif limits_mode == "custom":
                p_limits_rules = p.get("customLimits", [])
            else:
                p_limits_rules = []

            p_units_lua = format_unit_configs_lua_entries(p_unit_configs, indent="            ")
            p_limits_lua = format_limits_rules_lua_entries(p_limits_rules, indent="            ")

            prof_entry = f"""    ["{p_key}"] = {{
        name = "{p_name}",
        role = "{role_name}",
        damageDealtMult = {dmg_dealt},
        damageTakenMult = {dmg_taken},
        buildRateMult = {br_mult},
        prodMult = {pr_mult},
        unitConfigs = {{
{p_units_lua}
        }},
        limitRules = {{
{p_limits_lua}
        }},
    }}"""
            prof_entries.append(prof_entry)

        if not has_default_fallback:
            prof_entries.append("""    ["*"] = {
        name = "Default",
        role = "Vanilla Standard",
        damageDealtMult = 1.0,
        damageTakenMult = 1.0,
        buildRateMult = 1.0,
        prodMult = 1.0,
        unitConfigs = {},
        limitRules = {},
    }""")
        player_profiles_lua = ",\n".join(prof_entries)

    relics_table_lua = ""
    if has_relics:
        obj_lua_entries = []
        for o in relic_objectives:
            oid = o.get("id", "obj")
            oname = o.get("name", "Battlefield Relic").replace('"', '\\"')
            model_bp = o.get("modelBpId") or "uec1904"
            delay = int(o.get("spawnDelay", 0))
            loc_mode = o.get("locMode", "center")
            cx = float(o.get("customX", 256))
            cz = float(o.get("customZ", 256))
            trigger_type = o.get("triggerType", "both")
            pickup_radius = float(o.get("pickupRadius", 15.0))
            claimer_cat = o.get("claimerCategoryLua") or o.get("claimerCategory") or "categories.COMMAND"

            target_type = o.get("targetType", "category")
            target_name = o.get("targetName", "All Combat Units").replace('"', '\\"')
            target_uid = (o.get("targetUnitId") or "").strip()
            target_cat = o.get("targetCategoryLua") or o.get("targetCategory") or PRESET_RELIC_CATEGORIES.get(oid, "categories.COMMAND")

            buffs = o.get("buffs", {})
            hp_m = round(float(buffs.get("hpMult", 1.0)), 2)
            rng_m = round(float(buffs.get("rangeMult", 1.0)), 2)
            dmg_m = round(float(buffs.get("damageMult", 1.0)), 2)
            spd_m = round(float(buffs.get("speedMult", 1.0)), 2)
            shd_m = round(float(buffs.get("shieldMult", 1.0)), 2)
            rgn_m = round(float(buffs.get("regenMult", 1.0)), 2)

            buff_duration = int(o.get("buffDuration", 0))

            entry = f"""    {{
        id = "{oid}",
        name = "{oname}",
        modelBpId = "{model_bp}",
        spawnDelay = {delay},
        locMode = "{loc_mode}",
        customX = {cx},
        customZ = {cz},
        triggerType = "{trigger_type}",
        pickupRadius = {pickup_radius},
        claimerCategory = {claimer_cat},
        targetType = "{target_type}",
        targetName = "{target_name}",
        targetUnitId = "{target_uid}",
        targetCategory = {target_cat},
        buffDuration = {buff_duration},
        buffs = {{
            hpMult = {hp_m},
            rangeMult = {rng_m},
            damageMult = {dmg_m},
            speedMult = {spd_m},
            shieldMult = {shd_m},
            regenMult = {rgn_m},
        }},
    }}"""
            obj_lua_entries.append(entry)
        relics_table_lua = ",\n".join(obj_lua_entries)

    popups_table_lua = ""
    if has_popups:
        popup_lua_entries = []
        for r in popup_rules:
            rid = r.get("id", "rule")
            rname = r.get("name", "Alert").replace('"', '\\"')
            trigger = r.get("trigger", "unit_built")
            rtitle = r.get("title", "TACTICAL ALERT").replace('"', '\\"')
            rtext = r.get("text", "Event occurred!").replace('"', '\\"')
            rtheme = r.get("theme", "intel")
            rsound = r.get("sound", "UI_Radar_Blip")
            has_pinpoint = "true" if r.get("hasPinpoint", True) else "false"
            has_ping = "true" if r.get("hasPing", True) else "false"
            has_dismiss = "true" if r.get("hasDismiss", True) else "false"
            duration = int(r.get("duration", 8))
            health_pct = float(r.get("healthPct", 35))
            timer_sec = int(r.get("timerSeconds", 600))
            scope = r.get("scope", "global")
            target_p = r.get("targetPlayer", "").replace('"', '\\"')

            unit_ids = r.get("unitIds", [])
            unit_ids_lua = "{" + ", ".join(f'"{uid.lower()}"' for uid in unit_ids) + "}"
            cat_lua = r.get("categoryLua") or r.get("category") or PRESET_POPUP_CATEGORIES.get(rid, "")
            if not cat_lua:
                if unit_ids:
                    cat_lua = " + ".join(f"categories.{uid.upper()}" for uid in unit_ids)
                else:
                    cat_lua = "nil"

            popup_lua_entries.append(
                f'    {{\n'
                f'        id = "{rid}",\n'
                f'        name = "{rname}",\n'
                f'        trigger = "{trigger}",\n'
                f'        title = "{rtitle}",\n'
                f'        text = "{rtext}",\n'
                f'        theme = "{rtheme}",\n'
                f'        sound = "{rsound}",\n'
                f'        hasPinpoint = {has_pinpoint},\n'
                f'        hasPing = {has_ping},\n'
                f'        hasDismiss = {has_dismiss},\n'
                f'        duration = {duration},\n'
                f'        healthPct = {health_pct},\n'
                f'        timerSeconds = {timer_sec},\n'
                f'        scope = "{scope}",\n'
                f'        targetPlayer = "{target_p}",\n'
                f'        unitIds = {unit_ids_lua},\n'
                f'        category = {cat_lua},\n'
                f'    }}'
            )
        popups_table_lua = ",\n".join(popup_lua_entries)

    lootbox_table_lua = format_lootbox_lua_table(lootbox_config, indent="    ") if has_lootbox else ""

    # 2. Global Blueprints Mod if global buffs enabled
    if has_buffs and target_mode == "global":
        hook_sys_dir = target_mod_dir / "hook" / "lua" / "system"
        hook_sys_dir.mkdir(parents=True, exist_ok=True)
        bp_lua_content = f"""-- Auto-generated by FAF Mod Forge - Global Blueprint Mod
local UnitConfigs = {{
{unit_table_lua}
}}

local OldModBlueprints = ModBlueprints

function ModBlueprints(all_blueprints)
    OldModBlueprints(all_blueprints)

    for id, bp in all_blueprints.Unit do
        local lowerId = string.lower(id)
        local cfg = UnitConfigs[lowerId]

        if cfg then
            if bp.Defense then
                if cfg.hpMult and cfg.hpMult ~= 1.0 and bp.Defense.MaxHealth then
                    bp.Defense.MaxHealth = math.floor(bp.Defense.MaxHealth * cfg.hpMult)
                    bp.Defense.Health = math.floor((bp.Defense.Health or bp.Defense.MaxHealth) * cfg.hpMult)
                end
                if cfg.regenMult and cfg.regenMult ~= 1.0 then
                    local baseRegen = bp.Defense.RegenRate or 0
                    if baseRegen == 0 then baseRegen = 5 end
                    bp.Defense.RegenRate = math.floor(baseRegen * cfg.regenMult)
                end
                if bp.Defense.Shield then
                    if cfg.shieldMult and cfg.shieldMult ~= 1.0 and bp.Defense.Shield.ShieldMaxHealth then
                        bp.Defense.Shield.ShieldMaxHealth = math.floor(bp.Defense.Shield.ShieldMaxHealth * cfg.shieldMult)
                    end
                    if cfg.shieldRegenMult and cfg.shieldRegenMult ~= 1.0 and bp.Defense.Shield.ShieldRegenRate then
                        bp.Defense.Shield.ShieldRegenRate = math.floor(bp.Defense.Shield.ShieldRegenRate * cfg.shieldRegenMult)
                    end
                end
            end

            if bp.Economy then
                if cfg.massDiscount and cfg.massDiscount > 0 and bp.Economy.BuildCostMass then
                    bp.Economy.BuildCostMass = math.floor(bp.Economy.BuildCostMass * (1.0 - cfg.massDiscount))
                end
                if cfg.energyDiscount and cfg.energyDiscount > 0 and bp.Economy.BuildCostEnergy then
                    bp.Economy.BuildCostEnergy = math.floor(bp.Economy.BuildCostEnergy * (1.0 - cfg.energyDiscount))
                end
                if cfg.buildTimeDiscount and cfg.buildTimeDiscount > 0 and bp.Economy.BuildTime then
                    bp.Economy.BuildTime = math.floor(bp.Economy.BuildTime * (1.0 - cfg.buildTimeDiscount))
                end
                if cfg.buildRateMult and cfg.buildRateMult ~= 1.0 and bp.Economy.BuildRate then
                    bp.Economy.BuildRate = math.floor(bp.Economy.BuildRate * cfg.buildRateMult)
                end
                if cfg.prodMult and cfg.prodMult ~= 1.0 then
                    if bp.Economy.ProductionPerSecondMass and bp.Economy.ProductionPerSecondMass > 0 then
                        bp.Economy.ProductionPerSecondMass = math.floor(bp.Economy.ProductionPerSecondMass * cfg.prodMult)
                    end
                    if bp.Economy.ProductionPerSecondEnergy and bp.Economy.ProductionPerSecondEnergy > 0 then
                        bp.Economy.ProductionPerSecondEnergy = math.floor(bp.Economy.ProductionPerSecondEnergy * cfg.prodMult)
                    end
                end
            end

            if bp.Physics then
                if cfg.speedMult and cfg.speedMult ~= 1.0 and bp.Physics.MaxSpeed then
                    bp.Physics.MaxSpeed = bp.Physics.MaxSpeed * cfg.speedMult
                    if bp.Physics.MaxAcceleration then
                        bp.Physics.MaxAcceleration = bp.Physics.MaxAcceleration * cfg.speedMult
                    end
                    if bp.Physics.MaxBrake then
                        bp.Physics.MaxBrake = bp.Physics.MaxBrake * cfg.speedMult
                    end
                end
                if cfg.turnRateMult and cfg.turnRateMult ~= 1.0 and bp.Physics.TurnRate then
                    bp.Physics.TurnRate = math.floor(bp.Physics.TurnRate * cfg.turnRateMult)
                end
            end

            if bp.Intel then
                if cfg.visionMult and cfg.visionMult ~= 1.0 and bp.Intel.VisionRadius then
                    bp.Intel.VisionRadius = math.floor(bp.Intel.VisionRadius * cfg.visionMult)
                    if bp.Intel.WaterVisionRadius then
                        bp.Intel.WaterVisionRadius = math.floor(bp.Intel.WaterVisionRadius * cfg.visionMult)
                    end
                end
                if cfg.radarMult and cfg.radarMult ~= 1.0 then
                    if bp.Intel.RadarRadius and bp.Intel.RadarRadius > 0 then
                        bp.Intel.RadarRadius = math.floor(bp.Intel.RadarRadius * cfg.radarMult)
                    end
                    if bp.Intel.SonarRadius and bp.Intel.SonarRadius > 0 then
                        bp.Intel.SonarRadius = math.floor(bp.Intel.SonarRadius * cfg.radarMult)
                    end
                    if bp.Intel.OmniRadius and bp.Intel.OmniRadius > 0 then
                        bp.Intel.OmniRadius = math.floor(bp.Intel.OmniRadius * cfg.radarMult)
                    end
                end
            end

            if bp.Weapon then
                for _, w in bp.Weapon do
                    local isDeath = (w.WeaponCategory == "Death" or w.DamageType == "DeathExplosion" or w.DamageType == "Deathnuke")
                    if not isDeath then
                        if cfg.damageMult and cfg.damageMult ~= 1.0 and w.Damage and w.Damage > 0 then
                            w.Damage = math.floor(w.Damage * cfg.damageMult)
                        end
                        if cfg.rangeMult and cfg.rangeMult ~= 1.0 and w.MaxRadius and w.MaxRadius > 0 then
                            w.MaxRadius = math.floor(w.MaxRadius * cfg.rangeMult)
                        end
                        if cfg.rofMult and cfg.rofMult ~= 1.0 and w.RateOfFire and w.RateOfFire > 0 then
                            w.RateOfFire = w.RateOfFire * cfg.rofMult
                            if w.MuzzleSalvoDelay and w.MuzzleSalvoDelay > 0 then
                                w.MuzzleSalvoDelay = w.MuzzleSalvoDelay / cfg.rofMult
                            end
                            if w.RackSalvoReloadTime and w.RackSalvoReloadTime > 0 then
                                w.RackSalvoReloadTime = w.RackSalvoReloadTime / cfg.rofMult
                            end
                        end
                        if cfg.aoeMult and cfg.aoeMult ~= 1.0 and w.DamageRadius and w.DamageRadius > 0 then
                            w.DamageRadius = w.DamageRadius * cfg.aoeMult
                        end
                        if cfg.muzzleVelMult and cfg.muzzleVelMult ~= 1.0 and w.MuzzleVelocity and w.MuzzleVelocity > 0 then
                            w.MuzzleVelocity = math.floor(w.MuzzleVelocity * cfg.muzzleVelMult)
                        end
                    end
                end
            end
        end
    end
end
"""
        with open(hook_sys_dir / "Blueprints.lua", "w", encoding="utf-8") as f:
            f.write(bp_lua_content)

    # 3. UI Hooks
    hook_ui_dir = target_mod_dir / "hook" / "lua" / "ui" / "game"

    if has_buffs or has_relics:
        hook_ui_dir.mkdir(parents=True, exist_ok=True)
        detail_lua = generate_ui_unitview_detail_lua(unit_table_lua, target_mode, player_name)
        with open(hook_ui_dir / "unitviewDetail.lua", "w", encoding="utf-8") as f:
            f.write(detail_lua)
        unitview_lua = generate_ui_unitview_lua(unit_table_lua, target_mode, player_name)
        with open(hook_ui_dir / "unitview.lua", "w", encoding="utf-8") as f:
            f.write(unitview_lua)

    if has_popups or has_relics or has_lootbox:
        hook_ui_dir.mkdir(parents=True, exist_ok=True)
        lb_model = lootbox_config.get("modelBpId", "uec1904") if has_lootbox else "uec1904"
        lb_cost = int(lootbox_config.get("spinCostEnergy", 500)) if has_lootbox else 500
        lb_obs_name = lootbox_config.get("observerGmName", "DrReed") if has_lootbox else "DrReed"
        lb_obs_placement = lootbox_config.get("observerGmPlacement", True) if has_lootbox else True
        ui_gamemain_lua_content = generate_ui_gamemain_lua(
            has_lootbox=has_lootbox,
            lootbox_model=lb_model,
            spin_cost_energy=lb_cost,
            observer_gm_name=lb_obs_name,
            allow_observer_placement=lb_obs_placement
        )
        with open(hook_ui_dir / "gamemain.lua", "w", encoding="utf-8") as f:
            f.write(ui_gamemain_lua_content)

    # 4. Sim Hook: Unit.lua (Unified Engine Hook)
    needs_sim_unit = (target_mode == "multiplayer") or (has_buffs and target_mode == "player") or has_limits or has_relics or has_popups or has_lootbox
    if needs_sim_unit:
        hook_sim_dir = target_mod_dir / "hook" / "lua" / "sim"
        hook_sim_dir.mkdir(parents=True, exist_ok=True)

        sim_sections = []
        sim_sections.append(f"""-- Auto-generated by FAF Mod Forge - Combined Master Mod
-- Target Scope: {target_mode} | Target Player: {player_name}
-- Integrated Modules: {breakdown_text}

local TargetScope = "{target_mode}"
local TargetPlayer = "{player_name}"

local function MatchesPlayerName(actualName, targetName)
    if not actualName or not targetName or targetName == "" then return false end
    local a = string.lower(actualName)
    local t = string.lower(targetName)
    if a == t then return true end
    if string.find(a, t, 1, true) then return true end
    local stripped = string.gsub(a, "%b[]", "")
    stripped = string.gsub(stripped, "%b()", "")
    stripped = string.gsub(stripped, "^%s*(.-)%s*$", "%1")
    if stripped == t or string.find(stripped, t, 1, true) then return true end
    return false
end

local function GetArmyPlayerName(armyIndex)
    if not armyIndex or armyIndex < 1 then return "" end
    local setup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[armyIndex]
    if setup and setup.PlayerName and setup.PlayerName ~= "" then
        return setup.PlayerName
    end
    local brain = ArmyBrains and ArmyBrains[armyIndex]
    if brain and brain.Nickname and brain.Nickname ~= "" then
        return brain.Nickname
    end
    return ""
end
""")

        if target_mode == "multiplayer":
            sim_sections.append(f"""local PlayerProfiles = {{
{player_profiles_lua}
}}

local function GetPlayerProfile(armyIndex)
    if not armyIndex or armyIndex < 1 then return nil end
    local actualName = GetArmyPlayerName(armyIndex)
    if actualName ~= "" then
        for pattern, prof in pairs(PlayerProfiles) do
            if pattern ~= "*" and pattern ~= "default" and MatchesPlayerName(actualName, pattern) then
                return prof
            end
        end
    end
    local focus = GetFocusArmy()
    if focus and focus == armyIndex then
        for pattern, prof in pairs(PlayerProfiles) do
            if pattern ~= "*" and pattern ~= "default" and MatchesPlayerName(actualName, pattern) then
                return prof
            end
        end
    end
    return PlayerProfiles["*"] or PlayerProfiles["default"] or nil
end
""")

        sim_sections.append("""local function IsTargetArmy(armyIndex)
    if not armyIndex or armyIndex < 1 then return false end
    if TargetScope == "global" then return true end
    if TargetScope == "multiplayer" then
        return GetPlayerProfile(armyIndex) ~= nil
    end
    local setup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[armyIndex]
    if setup and setup.PlayerName and MatchesPlayerName(setup.PlayerName, TargetPlayer) then
        return true
    end
    local brain = ArmyBrains and ArmyBrains[armyIndex]
    if brain and brain.Nickname and MatchesPlayerName(brain.Nickname, TargetPlayer) then
        return true
    end
    local focus = GetFocusArmy()
    if focus and focus == armyIndex then
        return true
    end
    return false
end

local function GetActiveLimitRules(armyIndex)
    if TargetScope == "multiplayer" then
        local prof = GetPlayerProfile(armyIndex)
        return (prof and prof.limitRules) or nil
    elseif IsTargetArmy(armyIndex) then
        return LimitRules
    end
    return nil
end
""")

        if has_buffs and target_mode == "player":
            sim_sections.append(f"""local UnitConfigs = {{
{unit_table_lua}
}}
""")
        else:
            sim_sections.append("""local UnitConfigs = {}
""")

        if has_buffs or has_relics or target_mode == "multiplayer":
            sim_sections.append(f"""local function RecomputeUnitStats(unit)
    if not unit or unit:BeenDestroyed() or unit:IsDead() then return end
    local army = unit:GetArmy()
    local bp = unit:GetBlueprint()
    local bpId = string.lower(bp.BlueprintId or unit:GetUnitId() or "")
    local isTarget = IsTargetArmy(army)
    local prof = (TargetScope == "multiplayer") and GetPlayerProfile(army) or nil

    local baseCfg = nil
    if TargetScope == "multiplayer" then
        if prof and prof.unitConfigs then
            baseCfg = prof.unitConfigs[bpId]
        end
    else
        baseCfg = (isTarget and UnitConfigs and UnitConfigs[bpId]) or nil
    end

    -- Multipliers start with base mod buffs
    local totalHpMult = (baseCfg and baseCfg.hpMult) or 1.0
    local totalSpeedMult = (baseCfg and baseCfg.speedMult) or 1.0
    local totalRangeMult = (baseCfg and baseCfg.rangeMult) or 1.0
    local totalDmgMult = (baseCfg and baseCfg.damageMult) or 1.0
    local totalShieldMult = (baseCfg and baseCfg.shieldMult) or 1.0
    local totalRegenMult = (baseCfg and baseCfg.regenMult) or 1.0
    local totalTurnMult = (baseCfg and baseCfg.turnRateMult) or 1.0

    if prof and prof.damageDealtMult and prof.damageDealtMult ~= 1.0 then
        totalDmgMult = totalDmgMult * prof.damageDealtMult
    end

    -- Stack multiplicatively with all active relic buffs
    if unit.ActiveRelicBuffs then
        for _, buffs in pairs(unit.ActiveRelicBuffs) do
            if buffs.hpMult and buffs.hpMult > 0 then totalHpMult = totalHpMult * buffs.hpMult end
            if buffs.speedMult and buffs.speedMult > 0 then totalSpeedMult = totalSpeedMult * buffs.speedMult end
            if buffs.rangeMult and buffs.rangeMult > 0 then totalRangeMult = totalRangeMult * buffs.rangeMult end
            if buffs.damageMult and buffs.damageMult > 0 then totalDmgMult = totalDmgMult * buffs.damageMult end
            if buffs.shieldMult and buffs.shieldMult > 0 then totalShieldMult = totalShieldMult * buffs.shieldMult end
            if buffs.regenMult and buffs.regenMult > 0 then totalRegenMult = totalRegenMult * buffs.regenMult end
        end
    end

    -- 1. Health Buff Blueprint
    local buffName = 'ForgeOverhaul_Total_Health_' .. string.gsub(string.format("%.3f", totalHpMult), "%.", "_")
    if not Buffs[buffName] then
        BuffBlueprint {{
            Name = buffName,
            DisplayName = buffName,
            BuffType = 'FORGEOVERHAUL_TOTAL_HEALTH',
            Stacks = 'REPLACE',
            Duration = -1,
            Affects = {{
                MaxHealth = {{
                    Add = 0,
                    Mult = totalHpMult,
                    DoNotFill = false,
                }},
            }},
        }}
    end
    import('/lua/sim/buff.lua').ApplyBuff(unit, buffName)
    if unit:GetHealth() > unit:GetMaxHealth() then
        unit:SetHealth(unit, unit:GetMaxHealth())
    end

    -- 2. Weapon Range, RoF, and Splash AoE
    local wCount = unit:GetWeaponCount() or 0
    if wCount > 0 then
        for i = 1, wCount do
            local wep = unit:GetWeapon(i)
            if wep then
                local wbp = wep:GetBlueprint()
                if wbp and wbp.MaxRadius and wep.ChangeMaxRadius then
                    wep:ChangeMaxRadius(math.floor(wbp.MaxRadius * totalRangeMult))
                end
                if baseCfg and baseCfg.rofMult and baseCfg.rofMult ~= 1.0 and wbp and wbp.RateOfFire and wep.SetRateOfFire then
                    wep:SetRateOfFire(wbp.RateOfFire * baseCfg.rofMult)
                end
                if baseCfg and baseCfg.aoeMult and baseCfg.aoeMult ~= 1.0 and wbp and wbp.DamageRadius then
                    wep.DamageRadius = wbp.DamageRadius * baseCfg.aoeMult
                end
            end
        end
    end

    -- 3. Movement & Turn Speed
    if unit.SetSpeedMult then unit:SetSpeedMult(totalSpeedMult) end
    if unit.SetAccMult then unit:SetAccMult(totalSpeedMult) end
    if unit.SetTurnMult then unit:SetTurnMult(totalTurnMult) end

    -- 4. Damage Multiplier (applied in OnDamage)
    unit.ForgeOverhaulTotalDmgMult = totalDmgMult

    -- 5. Shields
    if unit.MyShield then
        unit.OriginalShieldMaxHealth = unit.OriginalShieldMaxHealth or unit.MyShield:GetMaxHealth()
        local newShieldMax = math.floor(unit.OriginalShieldMaxHealth * totalShieldMult)
        unit.MyShield:SetMaxHealth(newShieldMax)
        if baseCfg and baseCfg.shieldRegenMult and baseCfg.shieldRegenMult ~= 1.0 and unit.MyShield.SetShieldRegenRate then
            local bpShield = bp.Defense and bp.Defense.Shield
            local baseSRegen = (bpShield and bpShield.ShieldRegenRate) or 10
            unit.MyShield:SetShieldRegenRate(math.floor(baseSRegen * baseCfg.shieldRegenMult))
        end
        if unit.MyShield:GetHealth() > newShieldMax then
            unit.MyShield:SetHealth(unit.MyShield, newShieldMax)
        end
    end

    -- 6. Health Regen
    unit.ForgeOverhaulRegenMult = totalRegenMult
    local baseRegen = (bp.Defense and bp.Defense.RegenRate) or 0
    if baseRegen == 0 and totalRegenMult > 1.0 then baseRegen = 5 end
    if unit.SetRegenRate then
        unit:SetRegenRate(math.floor(baseRegen * totalRegenMult))
    end

    -- 7. Intel (Vision & Radar from baseCfg)
    if baseCfg and unit.SetIntelRadius and bp.Intel then
        if baseCfg.visionMult and baseCfg.visionMult ~= 1.0 and bp.Intel.VisionRadius then
            unit:SetIntelRadius('Vision', math.floor(bp.Intel.VisionRadius * baseCfg.visionMult))
            if bp.Intel.WaterVisionRadius then
                unit:SetIntelRadius('WaterVision', math.floor(bp.Intel.WaterVisionRadius * baseCfg.visionMult))
            end
        end
        if baseCfg.radarMult and baseCfg.radarMult ~= 1.0 then
            if bp.Intel.RadarRadius and bp.Intel.RadarRadius > 0 then
                unit:SetIntelRadius('Radar', math.floor(bp.Intel.RadarRadius * baseCfg.radarMult))
            end
            if bp.Intel.SonarRadius and bp.Intel.SonarRadius > 0 then
                unit:SetIntelRadius('Sonar', math.floor(bp.Intel.SonarRadius * baseCfg.radarMult))
            end
            if bp.Intel.OmniRadius and bp.Intel.OmniRadius > 0 then
                unit:SetIntelRadius('Omni', math.floor(bp.Intel.OmniRadius * baseCfg.radarMult))
            end
        end
    end

    -- 8. Build Rate & Production
    local effBuildRate = (baseCfg and baseCfg.buildRateMult) or 1.0
    if prof and prof.buildRateMult and prof.buildRateMult ~= 1.0 then
        effBuildRate = effBuildRate * prof.buildRateMult
    end
    if effBuildRate ~= 1.0 and unit:GetBuildRate() > 0 then
        unit:SetBuildRate(unit:GetBuildRate() * effBuildRate)
    end

    local effProd = (baseCfg and baseCfg.prodMult) or 1.0
    if prof and prof.prodMult and prof.prodMult ~= 1.0 then
        effProd = effProd * prof.prodMult
    end
    if bp.Economy and effProd ~= 1.0 then
        if bp.Economy.ProductionPerSecondEnergy and bp.Economy.ProductionPerSecondEnergy > 0 and unit.SetProductionPerSecondEnergy then
            unit:SetProductionPerSecondEnergy(math.floor(bp.Economy.ProductionPerSecondEnergy * effProd))
        end
        if bp.Economy.ProductionPerSecondMass and bp.Economy.ProductionPerSecondMass > 0 and unit.SetProductionPerSecondMass then
            unit:SetProductionPerSecondMass(math.floor(bp.Economy.ProductionPerSecondMass * effProd))
        end
    end
end
""")

        if has_limits or target_mode == "multiplayer":
            if has_limits and target_mode != "multiplayer":
                sim_sections.append(f"""local LimitRules = {{
{limits_table_lua}
}}
""")
            else:
                sim_sections.append("""local LimitRules = {}
""")

            sim_sections.append(f"""local function GetTotalCount(brain, category, extraUnit)
    if not brain or not category then return 0 end
    local list = brain:GetListOfUnits(category, false) or {{}}
    local count = 0
    local foundExtra = false
    for _, u in ipairs(list) do
        if not u:BeenDestroyed() and not u:IsDead() then
            count = count + 1
            if extraUnit and u == extraUnit then
                foundExtra = true
            end
        end
    end
    if extraUnit and not foundExtra and not extraUnit:BeenDestroyed() and not extraUnit:IsDead() then
        if EntityCategoryContains(category, extraUnit) then
            count = count + 1
        end
    end
    return count
end

local function RefreshRestrictions(armyIndex)
    local brain = ArmyBrains and ArmyBrains[armyIndex]
    if not brain then return end
    local rules = GetActiveLimitRules(armyIndex)
    if not rules then return end
    for _, rule in ipairs(rules) do
        local total = GetTotalCount(brain, rule.category)
        if total >= rule.limit then
            AddBuildRestriction(armyIndex, rule.category)
        else
            RemoveBuildRestriction(armyIndex, rule.category)
        end
    end
end

ForkThread(function()
    WaitTicks(2)
    if ArmyBrains then
        for armyIndex, brain in ArmyBrains do
            if TargetScope == "multiplayer" then
                if GetPlayerProfile(armyIndex) then
                    RefreshRestrictions(armyIndex)
                end
            elseif IsTargetArmy(armyIndex) then
                RefreshRestrictions(armyIndex)
            end
        end
    end
end)
""")

        if has_relics or has_lootbox:
            sim_sections.append("""local function GetNeutralArmy()
    if ScenarioInfo.ArmySetup then
        for armyName, data in pairs(ScenarioInfo.ArmySetup) do
            local upperName = string.upper(armyName)
            if string.find(upperName, "CIVILIAN") or string.find(upperName, "NEUTRAL") then
                return data.ArmyIndex or armyName
            end
        end
    end
    if ArmyBrains then
        for idx, brain in ArmyBrains do
            if brain.Civilian or (brain.Name and (string.find(string.upper(brain.Name), "CIVILIAN") or string.find(string.upper(brain.Name), "NEUTRAL"))) then
                return brain:GetArmyIndex()
            end
        end
    end
    return nil
end
""")

        if has_relics:
            sim_sections.append(f"""local ObjectivesConfig = {{
{relics_table_lua}
}}

local ActiveRelicsByArmy = {{}}

local function UnitMatchesRelic(unit, objConfig)
    if not unit or unit:BeenDestroyed() or unit:IsDead() then return false end
    if objConfig.targetType == "category" then
        if objConfig.targetCategory and EntityCategoryContains(objConfig.targetCategory, unit) then
            return true
        end
    else
        local uid = string.lower(objConfig.targetUnitId or "")
        if uid ~= "" then
            local bp = unit:GetBlueprint()
            local bpId = string.lower(bp.BlueprintId or unit:GetUnitId() or "")
            if bpId == uid then return true end
        end
    end
    return false
end

local function RevertRelicBuffs(army, objConfig)
    if not ActiveRelicsByArmy or not ActiveRelicsByArmy[army] or not ActiveRelicsByArmy[army][objConfig.id] then
        return
    end
    ActiveRelicsByArmy[army][objConfig.id] = nil

    pcall(function()
        Sync.ModForgeRelics = Sync.ModForgeRelics or {{}}
        table.insert(Sync.ModForgeRelics, {{
            action = "expire",
            army = army,
            id = objConfig.id,
        }})
    end)

    local brain = ArmyBrains and ArmyBrains[army]
    local armySetup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[army]
    local playerName = (armySetup and armySetup.PlayerName) or (brain and brain.Nickname) or ("Player " .. tostring(army))
    PrintText("⏳ [BUFF EXPIRED] '" .. tostring(objConfig.name) .. "' bonus on " .. tostring(objConfig.targetName) .. " expired for " .. tostring(playerName) .. "!", 16, "ffffaa33", 5, "center")

    if brain then
        local allUnits = brain:GetListOfUnits(categories.ALLUNITS, false) or {{}}
        for _, u in ipairs(allUnits) do
            if u.ActiveRelicBuffs and u.ActiveRelicBuffs[objConfig.id] then
                u.ActiveRelicBuffs[objConfig.id] = nil
                RecomputeUnitStats(u)
            end
        end
    end
end

local function OnRelicClaimed(relic, claimer, objConfig)
    if not relic or relic.RelicClaimed then return end
    relic.RelicClaimed = true

    local army = claimer:GetArmy()
    local brain = ArmyBrains and ArmyBrains[army]
    local armySetup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[army]
    local playerName = (armySetup and armySetup.PlayerName) or (brain and brain.Nickname) or ("Player " .. tostring(army))

    if TargetScope == "player" and TargetPlayer ~= "" then
        if not MatchesPlayerName(playerName, TargetPlayer) then
            PrintText("⚠️ Only " .. TargetPlayer .. " can unlock this objective!", 16, "ffff5555", 3, "center")
            relic.RelicClaimed = false
            return
        end
    end

    ActiveRelicsByArmy[army] = ActiveRelicsByArmy[army] or {{}}
    ActiveRelicsByArmy[army][objConfig.id] = objConfig

    local buffSummary = {{}}
    if objConfig.buffs.hpMult and objConfig.buffs.hpMult ~= 1.0 then
        table.insert(buffSummary, string.format("+%d%% HP", math.floor((objConfig.buffs.hpMult - 1.0) * 100)))
    end
    if objConfig.buffs.rangeMult and objConfig.buffs.rangeMult ~= 1.0 then
        table.insert(buffSummary, string.format("+%d%% Range", math.floor((objConfig.buffs.rangeMult - 1.0) * 100)))
    end
    if objConfig.buffs.damageMult and objConfig.buffs.damageMult ~= 1.0 then
        table.insert(buffSummary, string.format("+%d%% Damage", math.floor((objConfig.buffs.damageMult - 1.0) * 100)))
    end
    if objConfig.buffs.speedMult and objConfig.buffs.speedMult ~= 1.0 then
        table.insert(buffSummary, string.format("+%d%% Speed", math.floor((objConfig.buffs.speedMult - 1.0) * 100)))
    end
    local buffText = table.concat(buffSummary, ", ")
    local durText = (objConfig.buffDuration and objConfig.buffDuration > 0) and (" [⏳ " .. tostring(objConfig.buffDuration) .. "s]") or " [Permanent]"

    local msg = string.format("🏆 [OBJECTIVE CLAIMED] %s claimed '%s'! %s awarded (%s)%s!", playerName, objConfig.name, objConfig.targetName, buffText, durText)
    PrintText(msg, 18, "ff00d2ff", 6, "center")

    -- Broadcast full-screen / UI Tactical Popup card to ALL players when claimed
    pcall(function()
        local rPos = relic:GetPosition()
        local posTable = (rPos and {{ rPos[1], rPos[2], rPos[3] }}) or nil
        Sync.ModForgePopups = Sync.ModForgePopups or {{}}
        table.insert(Sync.ModForgePopups, {{
            id = "relic_claim_" .. tostring(objConfig.id or "relic"),
            title = "🏆 OBJECTIVE SECURED",
            text = tostring(playerName) .. " claimed '" .. tostring(objConfig.name) .. "'! " .. tostring(objConfig.targetName) .. " awarded: " .. buffText .. "!" .. durText,
            pos = posTable,
            sound = "UI_Score_Window_Open",
            theme = "tactical",
            hasPinpoint = (posTable ~= nil),
            hasPing = true,
            hasDismiss = true,
            duration = 10,
            scope = "global",
            targetPlayer = "",
        }})
    end)

    -- Sync to UI for active buff breakdown
    pcall(function()
        Sync.ModForgeRelics = Sync.ModForgeRelics or {{}}
        table.insert(Sync.ModForgeRelics, {{
            action = "claim",
            army = army,
            id = objConfig.id,
            name = objConfig.name,
            targetName = objConfig.targetName,
            buffs = objConfig.buffs,
            duration = objConfig.buffDuration or 0,
            startTime = (GetGameTimeSeconds and GetGameTimeSeconds()) or 0,
        }})
    end)

    pcall(function()
        CreateEmitterAtEntity(relic, army, '/effects/emitters/flash_01_emit.bp')
    end)

    -- Apply to all alive units belonging to claiming army
    if brain then
        local allUnits = brain:GetListOfUnits(categories.ALLUNITS, false) or {{}}
        for _, u in ipairs(allUnits) do
            if UnitMatchesRelic(u, objConfig) then
                u.ActiveRelicBuffs = u.ActiveRelicBuffs or {{}}
                u.ActiveRelicBuffs[objConfig.id] = objConfig.buffs
                RecomputeUnitStats(u)
            end
        end
    end

    -- If temporal duration configured, fork expiration thread
    if objConfig.buffDuration and objConfig.buffDuration > 0 then
        ForkThread(function()
            WaitSeconds(objConfig.buffDuration)
            RevertRelicBuffs(army, objConfig)
        end)
    end

    relic:Destroy()
end

local function SpawnObjectiveInstance(objConfig)
    if not objConfig then return end
    local bpId = (objConfig.modelBpId and objConfig.modelBpId ~= "" and objConfig.modelBpId) or "uec1904"
    if objConfig.spawnDelay and objConfig.spawnDelay > 0 then
        WaitSeconds(objConfig.spawnDelay)
    end

    local sizeX = (ScenarioInfo.size and ScenarioInfo.size[1]) or 512
    local sizeZ = (ScenarioInfo.size and ScenarioInfo.size[2]) or 512
    local centerX = sizeX / 2
    local centerZ = sizeZ / 2

    local posX = centerX
    local posZ = centerZ
    if objConfig.locMode == "coords" and objConfig.customX and objConfig.customZ then
        posX = objConfig.customX
        posZ = objConfig.customZ
    elseif objConfig.locMode == "random_center" then
        local angle = Random(0, 360) * (math.pi / 180)
        local dist = Random(40, 90)
        posX = math.max(20, math.min(sizeX - 20, centerX + math.cos(angle) * dist))
        posZ = math.max(20, math.min(sizeZ - 20, centerZ + math.sin(angle) * dist))
    end
    local posY = GetSurfaceHeight(posX, posZ)
    local neutralArmy = GetNeutralArmy()

    if not neutralArmy then
        local focus = GetFocusArmy()
        if ArmyBrains then
            for idx, brain in ArmyBrains do
                if brain:GetArmyIndex() ~= focus then
                    neutralArmy = brain:GetArmyIndex()
                    break
                end
            end
        end
        if not neutralArmy then
            neutralArmy = (ArmyBrains and ArmyBrains[1] and ArmyBrains[1]:GetArmyIndex()) or 1
        end
    end

    local fallbackIdx = (ArmyBrains and ArmyBrains[1] and ArmyBrains[1]:GetArmyIndex()) or 1
    local relic = nil
    pcall(function()
        relic = CreateUnitHPR(bpId, neutralArmy, posX, posY, posZ, 0, 0, 0)
    end)
    if not relic then
        pcall(function()
            relic = CreateUnitHPR(bpId, fallbackIdx, posX, posY, posZ, 0, 0, 0)
            neutralArmy = fallbackIdx
        end)
    end
    if not relic then
        pcall(function()
            relic = CreateUnitHPR("uec1904", fallbackIdx, posX, posY, posZ, 0, 0, 0)
            neutralArmy = fallbackIdx
        end)
    end

    if not relic then
        WARN("FAF Mod Forge: Failed to spawn relic objective '" .. tostring(objConfig.name) .. "' with blueprint: " .. tostring(bpId))
        return
    end

    LOG("FAF Mod Forge: Spawned relic '" .. tostring(objConfig.name) .. "' (" .. tostring(bpId) .. ") at (" .. posX .. ", " .. posZ .. ")")

    relic.IsRelicObjective = true
    relic.RelicConfig = objConfig
    relic.RelicClaimerCategory = objConfig.claimerCategory or (categories.MOBILE)

    relic:SetCapturable(true)
    relic:SetReclaimable(false)
    relic:SetCanTakeDamage(false)
    if relic.SetCaptureTimeMultiplier then
        relic:SetCaptureTimeMultiplier(0.05)
    end

    -- Always enforce two-way neutral diplomacy so all players can capture it
    if ArmyBrains then
        for idx, brain in ArmyBrains do
            SetAlliance(neutralArmy, brain:GetArmyIndex(), 'Neutral')
            SetAlliance(brain:GetArmyIndex(), neutralArmy, 'Neutral')
        end
    end

    -- Trigger tactical minimap alert ping
    pcall(function()
        Sync.CreatePing = Sync.CreatePing or {{}}
        table.insert(Sync.CreatePing, {{ Owner = 0, Type = 'alert', Location = {{posX, posY, posZ}} }})
    end)

    -- In-game broadcast text
    PrintText("🏆 [OBJECTIVE SPAWNED] " .. tostring(objConfig.name) .. " has appeared at (" .. math.floor(posX) .. ", " .. math.floor(posZ) .. ")! Capture or reach it with combat units/engineers for team buffs!", 18, "ffffff33", 8, "center")

    -- Broadcast full-screen / UI Tactical Popup card to ALL human players (same as Paragon popup!)
    pcall(function()
        Sync.ModForgePopups = Sync.ModForgePopups or {{}}
        table.insert(Sync.ModForgePopups, {{
            id = "relic_spawn_" .. tostring(objConfig.id or "relic"),
            title = "👑 BATTLEFIELD OBJECTIVE ONLINE",
            text = tostring(objConfig.name or "Battlefield Objective") .. " is active at map center! Reach or capture it to award team buffs!",
            pos = {{ posX, posY, posZ }},
            sound = "UI_Score_Window_Open",
            theme = "quantum",
            hasPinpoint = true,
            hasPing = true,
            hasDismiss = true,
            duration = 14,
            scope = "global",
            targetPlayer = "",
        }})
    end)

    -- Proximity pickup polling thread
    if objConfig.triggerType == "walkover" or objConfig.triggerType == "both" then
        local radius = math.max(objConfig.pickupRadius or 12.0, 15.0)
        local claimerCat = objConfig.claimerCategory or (categories.MOBILE)
        ForkThread(function()
            while relic and not relic:BeenDestroyed() and not relic:IsDead() and not relic.RelicClaimed do
                local rPos = relic:GetPosition()
                if ArmyBrains then
                    for _, brain in ArmyBrains do
                        local checkUnits = brain:GetListOfUnits(claimerCat, false) or {{}}
                        for _, u in ipairs(checkUnits) do
                            if not u:BeenDestroyed() and not u:IsDead() and VDist3(u:GetPosition(), rPos) <= radius then
                                OnRelicClaimed(relic, u, objConfig)
                                return
                            end
                        end
                    end
                end
                WaitSeconds(0.4)
            end
        end)
    end
end

ForkThread(function()
    WaitSeconds(2)
    for _, obj in ipairs(ObjectivesConfig) do
        ForkThread(SpawnObjectiveInstance, obj)
    end
end)
""")

        if has_popups:
            sim_sections.append(f"""local PopupRules = {{
{popups_table_lua}
}}

local function MatchesUnit(rule, unit)
    if not unit or unit:BeenDestroyed() or unit:IsDead() then return false end
    if rule.unitIds and table.getn(rule.unitIds) > 0 then
        local bpId = string.lower(unit:GetBlueprint().BlueprintId)
        for _, id in ipairs(rule.unitIds) do
            if string.lower(id) == bpId then
                return true
            end
        end
    end
    if rule.category and EntityCategoryContains(rule.category, unit) then
        return true
    end
    return false
end

local function FirePopupAlert(rule, unit, overridePos)
    Sync.ModForgePopups = Sync.ModForgePopups or {{}}
    local pos = overridePos
    if not pos and unit and not unit:BeenDestroyed() then
        local v = unit:GetPosition()
        if v then pos = {{v[1], v[2], v[3]}} end
    end

    local bpName = ""
    if unit and not unit:BeenDestroyed() then
        local bp = unit:GetBlueprint()
        if bp.General and bp.General.UnitName then
            bpName = bp.General.UnitName
        elseif bp.Description then
            bpName = bp.Description
        end
        bpName = string.gsub(bpName, "<LOC [^>]*>", "")
    end

    local msg = rule.text
    if bpName ~= "" then
        msg = string.gsub(msg, "{{{{UnitName}}}}", bpName)
        msg = string.gsub(msg, "{{UnitName}}", bpName)
    end

    table.insert(Sync.ModForgePopups, {{
        id = rule.id,
        title = rule.title,
        text = msg,
        pos = pos,
        sound = rule.sound,
        theme = rule.theme,
        hasPinpoint = rule.hasPinpoint,
        hasPing = rule.hasPing,
        hasDismiss = rule.hasDismiss,
        duration = rule.duration,
        targetScope = rule.scope or TargetScope,
        targetPlayer = (rule.targetPlayer ~= "" and rule.targetPlayer) or TargetPlayer,
        armyIndex = (unit and not unit:BeenDestroyed()) and unit:GetArmy() or -1,
    }})
end

ForkThread(function()
    local timerRules = {{}}
    for _, r in ipairs(PopupRules) do
        if r.trigger == "match_timer" and r.timerSeconds and r.timerSeconds > 0 then
            table.insert(timerRules, r)
        end
    end
    if table.getn(timerRules) == 0 then return end
    table.sort(timerRules, function(a, b) return a.timerSeconds < b.timerSeconds end)
    local currentSec = 0
    for _, r in ipairs(timerRules) do
        local waitSec = r.timerSeconds - currentSec
        if waitSec > 0 then
            WaitSeconds(waitSec)
            currentSec = r.timerSeconds
        end
        FirePopupAlert(r, nil, nil)
    end
end)
""")

        if has_lootbox:
            sim_sections.append(f"""local LootboxConfig = {{
{lootbox_table_lua}
}}

local PresetDropTables = {{
    prototype = {{
        name = "Experimental Prototype Vault",
        openMode = "instant_crack",
        modelBpId = "uec1904",
        dropTable = {{
            {{ id = "drop_proto_cybran", name = "Experimental Cybran Megabot (Monkeylord)", desc = "High-tier experimental heavy assault bot ready for combat.", type = "spawn_unit", unitId = "url0402", unitCount = 1, weight = 35, rarity = "jackpot" }},
            {{ id = "drop_proto_uef", name = "UEF Fatboy Mobile Factory", desc = "Heavy amphibious siege platform and mobile factory.", type = "spawn_unit", unitId = "uel0401", unitCount = 1, weight = 35, rarity = "jackpot" }},
            {{ id = "drop_proto_aeon", name = "Aeon Galactic Colossus", desc = "Gigantic assault bot with tractor claws.", type = "spawn_unit", unitId = "ual0401", unitCount = 1, weight = 30, rarity = "jackpot" }},
        }}
    }},
    swarm = {{
        name = "Raptor Swarm Bio-Pod",
        openMode = "instant_crack",
        modelBpId = "uec1904",
        dropTable = {{
            {{ id = "drop_raptor_boss", name = "Apex Cybran Gunship (Soul Ripper)", desc = "Experimental heavy gunship bio-mech.", type = "spawn_unit", unitId = "ura0401", unitCount = 1, weight = 20, rarity = "jackpot" }},
            {{ id = "drop_raptor_pack", name = "Raptor Strike Pack (x8 Cybran Hunters)", desc = "A ravenous pack of fast-strike combat hunters.", type = "spawn_unit", unitId = "url0106", unitCount = 8, weight = 45, rarity = "rare" }},
            {{ id = "drop_raptor_ambush", name = "Frenzied Hive Ambush", desc = "Warning: The pod released an enraged swarm of 6 hostile assault bots!", type = "spawn_hostile", unitId = "url0303", unitCount = 6, weight = 35, rarity = "disaster" }},
        }}
    }},
    supply = {{
        name = "Tactical Vanguard Armor Vault",
        openMode = "instant_crack",
        modelBpId = "uec1904",
        dropTable = {{
            {{ id = "drop_vanguard_t3", name = "T3 Heavy Armor Squadron (x6 Titans)", desc = "6 heavily armored Tier 3 frontline assault mechs.", type = "spawn_unit", unitId = "uel0303", unitCount = 6, weight = 40, rarity = "rare" }},
            {{ id = "drop_vanguard_shield", name = "Mobile Shield & Flak Convoy (x4)", desc = "Support group with mobile shield generators and flak.", type = "spawn_unit", unitId = "uel0307", unitCount = 4, weight = 35, rarity = "common" }},
            {{ id = "drop_vanguard_eco", name = "Tactical Field Reserve (+3000M / +30000E)", desc = "Emergency supply cache to kickstart T3 production.", type = "give_resources", mass = 3000, energy = 30000, weight = 25, rarity = "jackpot" }},
        }}
    }},
    motherlode = {{
        name = "Resource Motherlode Vault",
        openMode = "instant_crack",
        modelBpId = "uec1904",
        dropTable = {{
            {{ id = "drop_motherlode_massive", name = "Planetary Core Extraction (+10000 Mass / +100000 Energy)", desc = "Massive injection of supreme commander strategic reserves.", type = "give_resources", mass = 10000, energy = 100000, weight = 35, rarity = "jackpot" }},
            {{ id = "drop_motherlode_regular", name = "Refined Mass Reservoir (+4000 Mass / +40000 Energy)", desc = "Substantial economic boost for rapid expansion.", type = "give_resources", mass = 4000, energy = 40000, weight = 45, rarity = "rare" }},
            {{ id = "drop_motherlode_trap", name = "Overloaded Capacitor Trap (Detonation)", desc = "Volatile containment rupture causing 3,000 area damage!", type = "explosion_trap", weight = 20, rarity = "disaster" }},
        }}
    }},
    casino = {{
        name = "High-Roller Casino Vault",
        openMode = "interactive",
        modelBpId = "uec1904",
        dropTable = {{
            {{ id = "drop_hr_jackpot", name = "Grand Jackpot (+8000 Mass / +80000 Energy)", desc = "The triple 7s aligned! Massive resource payout.", type = "give_resources", mass = 8000, energy = 80000, weight = 20, rarity = "jackpot" }},
            {{ id = "drop_hr_flak", name = "Cybran T3 Mobile Artillery (Trebuchet x2)", desc = "Heavy long-range siege artillery pieces.", type = "spawn_unit", unitId = "url0304", unitCount = 2, weight = 35, rarity = "rare" }},
            {{ id = "drop_hr_drain", name = "House Advantage (Resource Siphon)", desc = "The casino takes its cut: drained -2500 Mass and -20000 Energy!", type = "take_resources", massDrain = 2500, energyDrain = 20000, weight = 25, rarity = "unlucky" }},
            {{ id = "drop_hr_ambush", name = "Bouncer Ambush (Loyalist Hit Squad)", desc = "Security enforcers sent to terminate lucky winners!", type = "spawn_hostile", unitId = "url0303", unitCount = 4, weight = 20, rarity = "disaster" }},
        }}
    }}
}}

local function RollLootboxOutcome(cfg)
    local tableEntries = (cfg and cfg.dropTable) or {{}}
    if table.getn(tableEntries) == 0 then return nil end
    local totalWeight = 0
    for _, item in ipairs(tableEntries) do
        totalWeight = totalWeight + (item.weight or 10)
    end
    local roll = Random(1, math.max(1, totalWeight))
    local selected = tableEntries[1]
    for _, item in ipairs(tableEntries) do
        local w = item.weight or 10
        if roll <= w then
            selected = item
            break
        end
        roll = roll - w
    end
    return selected
end

local function ResolveLootboxOutcome(unit, army, outcome, cfg)
    if not unit or unit:BeenDestroyed() or unit:IsDead() then return end
    local brain = ArmyBrains and ArmyBrains[army]
    local armySetup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[army]
    local playerName = (armySetup and armySetup.PlayerName) or (brain and brain.Nickname) or ("Player " .. tostring(army))

    local pos = unit:GetPosition()
    local spawnX = pos[1] + 5
    local spawnZ = pos[3] + 5
    local spawnY = GetSurfaceHeight(spawnX, spawnZ)

    if outcome.type == "spawn_unit" or outcome.type == "spawn_structure" then
        local count = outcome.unitCount or 1
        local bpId = outcome.unitId or "uel0202"
        for i = 1, count do
            local offX = (i - 1) * 3
            local offZ = (i % 2 == 0) and 2 or -2
            pcall(function()
                local spawned = CreateUnitHPR(bpId, army, spawnX + offX, spawnY, spawnZ + offZ, 0, 0, 0)
                if spawned then
                    CreateEmitterAtEntity(spawned, army, '/effects/emitters/flash_01_emit.bp')
                end
            end)
        end
        PrintText("🎉 [LOOTBOX DROP] " .. playerName .. " won: " .. tostring(outcome.name) .. "!", 18, "ff34d399", 6, "center")

    elseif outcome.type == "give_resources" then
        if brain then
            if outcome.mass and outcome.mass > 0 then brain:GiveResource('Mass', outcome.mass) end
            if outcome.energy and outcome.energy > 0 then brain:GiveResource('Energy', outcome.energy) end
        end
        PrintText("🪙 [LOOTBOX JACKPOT] " .. playerName .. " won +" .. tostring(outcome.mass or 0) .. " Mass & +" .. tostring(outcome.energy or 0) .. " Energy!", 18, "ffffd700", 6, "center")

    elseif outcome.type == "take_resources" then
        if brain then
            if outcome.massDrain and outcome.massDrain > 0 then brain:TakeResource('Mass', outcome.massDrain) end
            if outcome.energyDrain and outcome.energyDrain > 0 then brain:TakeResource('Energy', outcome.energyDrain) end
        end
        PrintText("💸 [LOOTBOX SIPHON] " .. playerName .. " was siphoned: -" .. tostring(outcome.massDrain or 0) .. " Mass & -" .. tostring(outcome.energyDrain or 0) .. " Energy!", 18, "fff97316", 6, "center")

    elseif outcome.type == "spawn_hostile" then
        local neutralArmy = GetNeutralArmy()
        if not neutralArmy then
            if ArmyBrains then
                for idx, b in ArmyBrains do
                    if b:GetArmyIndex() ~= army then
                        neutralArmy = b:GetArmyIndex()
                        break
                    end
                end
            end
            if not neutralArmy then neutralArmy = 1 end
        end

        pcall(function()
            SetAlliance(neutralArmy, army, 'Enemy')
            SetAlliance(army, neutralArmy, 'Enemy')
        end)

        local count = outcome.unitCount or 3
        local bpId = outcome.unitId or "url0303"
        local spawnedHostiles = {{}}
        for i = 1, count do
            local offX = (i - 1) * 4
            local offZ = (i % 2 == 0) and 3 or -3
            pcall(function()
                local hUnit = CreateUnitHPR(bpId, neutralArmy, spawnX + offX, spawnY, spawnZ + offZ, 0, 0, 0)
                if hUnit then
                    hUnit:SetDoNotTarget(false)
                    hUnit:SetCanTakeDamage(true)
                    table.insert(spawnedHostiles, hUnit)
                    CreateEmitterAtEntity(hUnit, neutralArmy, '/effects/emitters/sparks_07_emit.bp')
                end
            end)
        end
        if table.getn(spawnedHostiles) > 0 then
            pcall(function()
                IssueAggressiveMove(spawnedHostiles, {{ pos[1], pos[2], pos[3] }})
            end)
        end
        PrintText("💀 [LOOTBOX AMBUSH] " .. playerName .. " triggered an AMBUSH! Hostile forces emerged!", 18, "ffef4444", 8, "center")

    elseif outcome.type == "explosion_trap" then
        pcall(function()
            DamageArea(unit, pos, 18, 2500, 'Normal', false)
            CreateEmitterAtEntity(unit, army, '/effects/emitters/destruction_explosion_concussion_ring_01_emit.bp')
        end)
        PrintText("💥 [LOOTBOX DETONATION] Vault booby trap detonated in a violent explosion!", 18, "ffff2222", 6, "center")
    end

    pcall(function()
        Sync.ModForgePopups = Sync.ModForgePopups or {{}}
        table.insert(Sync.ModForgePopups, {{
            id = "casino_result_" .. tostring(outcome.id or "prize"),
            title = (cfg and cfg.openMode == "instant_crack") and "📦 CRATE CRACKED" or "🎰 CASINO OUTCOME",
            text = playerName .. ": " .. tostring(outcome.name) .. "! (" .. tostring(outcome.desc or "") .. ")",
            pos = {{ pos[1], pos[2], pos[3] }},
            sound = (outcome.rarity == 'disaster') and "UI_Radar_Blip" or "UI_Score_Window_Open",
            theme = (outcome.rarity == 'disaster') and "danger" or ((outcome.rarity == 'jackpot') and "quantum" or "tactical"),
            hasPinpoint = true,
            hasPing = true,
            hasDismiss = true,
            duration = 10,
            scope = "global",
            targetPlayer = "",
        }})
    end)

    if (cfg and cfg.openMode == "instant_crack") or (cfg and cfg.respawnMode == "single_use") then
        pcall(function()
            CreateEmitterAtEntity(unit, army, '/effects/emitters/flash_01_emit.bp')
        end)
        unit:Destroy()
    else
        unit.IsSpinning = false
        local coolSec = (cfg and cfg.cooldownSec) or 60
        unit.CooldownUntil = ((GetGameTimeSeconds and GetGameTimeSeconds()) or 0) + coolSec
    end
end

SimCallbacks = SimCallbacks or {{}}
SimCallbacks.ModForgeAdminPlaceLootbox = function(data, cbArmy)
    local pos = data.Pos
    if not pos then return end
    local presetKey = data.Preset or "prototype"
    local cfgToUse = LootboxConfig
    if presetKey and PresetDropTables[presetKey] then
        local pDef = PresetDropTables[presetKey]
        cfgToUse = {{
            enabled = true,
            name = pDef.name or LootboxConfig.name or "Airdrop Lootbox",
            modelBpId = pDef.modelBpId or LootboxConfig.modelBpId or "uec1904",
            openMode = pDef.openMode or "instant_crack",
            claimMode = LootboxConfig.claimMode or "both",
            respawnMode = (pDef.openMode == "instant_crack") and "single_use" or (LootboxConfig.respawnMode or "single_use"),
            spinCostEnergy = (pDef.openMode == "instant_crack") and 0 or (LootboxConfig.spinCostEnergy or 500),
            spinCostMass = (pDef.openMode == "instant_crack") and 0 or (LootboxConfig.spinCostMass or 0),
            dropTable = pDef.dropTable,
        }}
    end
    ForkThread(SpawnLootboxInstance, cfgToUse, 1, pos)
end

SimCallbacks.ModForgeLootboxSpin = function(data, cbArmy)
    local entityId = data.EntityId
    local army = data.Army or cbArmy
    if not entityId or not army then return end

    local brain = ArmyBrains and ArmyBrains[army]
    local armySetup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[army]
    local playerName = (armySetup and armySetup.PlayerName) or (brain and brain.Nickname) or ("Player " .. tostring(army))

    if TargetScope == "player" and TargetPlayer ~= "" then
        if not MatchesPlayerName(playerName, TargetPlayer) then
            PrintText("⚠️ Only " .. TargetPlayer .. " can play this Casino Vault!", 16, "ffff5555", 3, "center")
            return
        end
    end

    local unit = nil
    if brain then
        local units = brain:GetListOfUnits(categories.ALLUNITS, false) or {{}}
        for _, u in ipairs(units) do
            if not u:BeenDestroyed() and not u:IsDead() and u:GetEntityId() == entityId then
                unit = u
                break
            end
        end
    end

    if not unit or not unit.IsCasinoLootbox then return end
    if unit.IsSpinning then
        PrintText("⏳ Casino Vault is already spinning!", 14, "ffffaa33", 2, "center")
        return
    end

    local curTime = (GetGameTimeSeconds and GetGameTimeSeconds()) or 0
    if unit.CooldownUntil and curTime < unit.CooldownUntil then
        local rem = math.ceil(unit.CooldownUntil - curTime)
        PrintText("⏳ Vault is recharging (" .. rem .. "s remaining)", 14, "ffff5555", 3, "center")
        return
    end

    local cfg = unit.LootboxConfig or LootboxConfig
    local costEnergy = cfg.spinCostEnergy or 0
    local costMass = cfg.spinCostMass or 0

    if brain and (costEnergy > 0 or costMass > 0) then
        local curE = brain:GetEconomyStored('ENERGY') or 0
        local curM = brain:GetEconomyStored('MASS') or 0
        if curE < costEnergy or curM < costMass then
            PrintText("⚠️ Insufficient resources! Requires " .. costEnergy .. " Energy / " .. costMass .. " Mass", 16, "ffff4444", 4, "center")
            return
        end
        if costEnergy > 0 then brain:TakeResource('ENERGY', costEnergy) end
        if costMass > 0 then brain:TakeResource('MASS', costMass) end
    end

    unit.IsSpinning = true

    local selected = RollLootboxOutcome(cfg)
    if not selected then return end

    pcall(function()
        CreateEmitterAtEntity(unit, army, '/effects/emitters/flash_01_emit.bp')
        CreateEmitterAtEntity(unit, army, '/effects/emitters/sparks_07_emit.bp')
    end)

    PrintText("🎰 [CASINO SPIN] " .. playerName .. " pulled the lever! Reels spinning...", 16, "ffffd700", 3, "center")

    pcall(function()
        Sync.ModForgeCasinoSpin = Sync.ModForgeCasinoSpin or {{}}
        table.insert(Sync.ModForgeCasinoSpin, {{
            entityId = entityId,
            army = army,
            outcome = selected,
            duration = 3.2,
        }})
    end)

    ForkThread(function()
        WaitSeconds(3.2)
        ResolveLootboxOutcome(unit, army, selected, cfg)
    end)
end

local function SpawnLootboxInstance(cfg, index, customPos)
    if not cfg or not cfg.enabled then return end
    if cfg.locMode == "observer_only" and not customPos then
        return
    end
    if not customPos and cfg.spawnDelay and cfg.spawnDelay > 0 then
        WaitSeconds(cfg.spawnDelay)
    end

    local bpId = (cfg.modelBpId and cfg.modelBpId ~= "" and cfg.modelBpId) or "uec1904"
    local sizeX = (ScenarioInfo.size and ScenarioInfo.size[1]) or 512
    local sizeZ = (ScenarioInfo.size and ScenarioInfo.size[2]) or 512
    local centerX = sizeX / 2
    local centerZ = sizeZ / 2

    local posX = centerX
    local posZ = centerZ
    if customPos then
        posX = customPos[1]
        posZ = customPos[3] or customPos[2]
    elseif cfg.locMode == "coords" and cfg.customX and cfg.customZ then
        posX = cfg.customX
        posZ = cfg.customZ
    elseif cfg.locMode == "random_center" or (index and index > 1) then
        local angle = Random(0, 360) * (math.pi / 180)
        local dist = Random(35, 80)
        posX = math.max(25, math.min(sizeX - 25, centerX + math.cos(angle) * dist))
        posZ = math.max(25, math.min(sizeZ - 25, centerZ + math.sin(angle) * dist))
    end
    local posY = GetSurfaceHeight(posX, posZ)

    local neutralArmy = GetNeutralArmy()
    if not neutralArmy then
        local focus = GetFocusArmy()
        if ArmyBrains then
            for idx, brain in ArmyBrains do
                if brain:GetArmyIndex() ~= focus then
                    neutralArmy = brain:GetArmyIndex()
                    break
                end
            end
        end
        if not neutralArmy then
            neutralArmy = (ArmyBrains and ArmyBrains[1] and ArmyBrains[1]:GetArmyIndex()) or 1
        end
    end

    local fallbackIdx = (ArmyBrains and ArmyBrains[1] and ArmyBrains[1]:GetArmyIndex()) or 1
    local vault = nil
    pcall(function()
        vault = CreateUnitHPR(bpId, neutralArmy, posX, posY, posZ, 0, 0, 0)
    end)
    if not vault then
        pcall(function()
            vault = CreateUnitHPR(bpId, fallbackIdx, posX, posY, posZ, 0, 0, 0)
            neutralArmy = fallbackIdx
        end)
    end
    if not vault then
        pcall(function()
            vault = CreateUnitHPR("uec1904", fallbackIdx, posX, posY, posZ, 0, 0, 0)
            neutralArmy = fallbackIdx
        end)
    end

    if not vault then
        WARN("FAF Mod Forge: Failed to spawn casino vault: " .. tostring(bpId))
        return
    end

    vault.IsCasinoLootbox = true
    vault.LootboxConfig = cfg

    vault:SetCapturable(true)
    vault:SetReclaimable(false)
    vault:SetCanTakeDamage(true)
    vault:SetMaxHealth(15000)
    vault:SetHealth(vault, 15000)
    if vault.SetCaptureTimeMultiplier then
        vault:SetCaptureTimeMultiplier(0.08)
    end

    if ArmyBrains then
        for idx, brain in ArmyBrains do
            SetAlliance(neutralArmy, brain:GetArmyIndex(), 'Neutral')
            SetAlliance(brain:GetArmyIndex(), neutralArmy, 'Neutral')
        end
    end

    pcall(function()
        vault:SetIntelRadius('Vision', 28)
        vault:SetIntelRadius('Omni', 35)
        vault:EnableIntel('Vision')
        vault:EnableIntel('Omni')
    end)

    pcall(function()
        Sync.CreatePing = Sync.CreatePing or {{}}
        table.insert(Sync.CreatePing, {{ Owner = 0, Type = 'alert', Location = {{posX, posY, posZ}} }})
    end)

    if customPos then
        PrintText("📦 [GM AIRDROP] " .. tostring(cfg.name or "Quantum Vault") .. " seeded at (" .. math.floor(posX) .. ", " .. math.floor(posZ) .. ")! Capture and claim it!", 18, "ff38bdf8", 8, "center")
    else
        PrintText("🎰 [CASINO VAULT ONLINE] " .. tostring(cfg.name or "Quantum Vault") .. " has appeared at (" .. math.floor(posX) .. ", " .. math.floor(posZ) .. ")! Capture and claim it!", 18, "ffffd700", 8, "center")
    end

    if cfg.claimMode == "proximity" or cfg.claimMode == "both" then
        ForkThread(function()
            while vault and not vault:BeenDestroyed() and not vault:IsDead() and (vault:GetArmy() == neutralArmy) do
                local vPos = vault:GetPosition()
                if ArmyBrains then
                    for _, brain in ArmyBrains do
                        local bArmy = brain:GetArmyIndex()
                        if bArmy ~= neutralArmy then
                            local checkUnits = brain:GetListOfUnits(categories.MOBILE + categories.COMMAND, false) or {{}}
                            for _, u in ipairs(checkUnits) do
                                if not u:BeenDestroyed() and not u:IsDead() and VDist3(u:GetPosition(), vPos) <= 15.0 then
                                    vault = ChangeUnitArmy(vault, bArmy)
                                    if vault then
                                        vault.IsCasinoLootbox = true
                                        vault.LootboxConfig = cfg
                                        local armySetup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[bArmy]
                                        local pName = (armySetup and armySetup.PlayerName) or brain.Nickname or ("Player " .. tostring(bArmy))
                                        
                                        if cfg.openMode == "instant_crack" then
                                            local outcome = RollLootboxOutcome(cfg)
                                            if outcome then
                                                PrintText("📦💥 [LOOTBOX CRACKED] " .. pName .. " reached & cracked the crate! RUN FOR IT!", 18, "ff34d399", 6, "center")
                                                pcall(function()
                                                    CreateEmitterAtEntity(vault, bArmy, '/effects/emitters/flash_01_emit.bp')
                                                    CreateEmitterAtEntity(vault, bArmy, '/effects/emitters/destruction_explosion_concussion_ring_01_emit.bp')
                                                end)
                                                ResolveLootboxOutcome(vault, bArmy, outcome, cfg)
                                            end
                                        else
                                            PrintText("🎰 [CASINO SECURED] " .. pName .. " reached the Vault! Select it and click PLAY CASINO!", 18, "ffffd700", 6, "center")
                                            CreateEmitterAtEntity(vault, bArmy, '/effects/emitters/flash_01_emit.bp')
                                        end
                                    end
                                    return
                                end
                            end
                        end
                    end
                end
                WaitSeconds(0.5)
            end
        end)
    end
end

ForkThread(function()
    WaitSeconds(2)
    if LootboxConfig and LootboxConfig.enabled then
        local count = LootboxConfig.spawnCount or 1
        for i = 1, count do
            ForkThread(SpawnLootboxInstance, LootboxConfig, i)
        end
    end
end)
""")

        # Build Unit Class Definition
        class_methods = []

        if has_limits or target_mode == "multiplayer":
            class_methods.append("""    OnStartBuild = function(self, unitBeingBuilt, order)
        local army = self:GetArmy()
        local activeLimitRules = GetActiveLimitRules(army)
        if activeLimitRules and unitBeingBuilt then
            -- Allow assisting engineers without treating them as building an additional unit
            if unitBeingBuilt.LimitTrackingStarted then
                return OldUnit.OnStartBuild(self, unitBeingBuilt, order)
            end

            local brain = self:GetAIBrain()
            for _, rule in ipairs(activeLimitRules) do
                if EntityCategoryContains(rule.category, unitBeingBuilt) then
                    local count = GetTotalCount(brain, rule.category, unitBeingBuilt)

                    if count > rule.limit then
                        -- Limit reached: Cancel the build / upgrade order
                        local pName = GetArmyPlayerName(army)
                        if pName == "" then pName = "Army " .. tostring(army) end
                        PrintText("🛑 [LIMIT REACHED] " .. pName .. ": " .. rule.name .. " limit reached (" .. tostring(rule.limit) .. " max)!", 18, "ffff3333", 4, "center")
                        AddBuildRestriction(army, rule.category)
                        unitBeingBuilt:Destroy()
                        if order == "Upgrade" then
                            self:OnFailedToBuild()
                            IssueClearCommands({self})
                        else
                            IssueStop({self})
                        end
                        return false
                    else
                        unitBeingBuilt.LimitTrackingStarted = true
                        unitBeingBuilt.TrackedRuleCategory = rule.category

                        if count >= rule.limit then
                            AddBuildRestriction(army, rule.category)
                        end
                    end
                end
            end
        end
        return OldUnit.OnStartBuild(self, unitBeingBuilt, order)
    end,

    OnStopBuild = function(self, unitBeingBuilt, order)
        local result = OldUnit.OnStopBuild(self, unitBeingBuilt, order)
        local army = self:GetArmy()
        if TargetScope == "multiplayer" or IsTargetArmy(army) then
            RefreshRestrictions(army)
        end
        return result
    end,

    OnFailedToBuild = function(self)
        local result = OldUnit.OnFailedToBuild(self)
        local army = self:GetArmy()
        if TargetScope == "multiplayer" or IsTargetArmy(army) then
            RefreshRestrictions(army)
        end
        return result
    end,""")

        # Method: OnStopBeingBuilt
        stop_being_built_body = ["        local result = OldUnit.OnStopBeingBuilt(self, builder, layer)", "        local army = self:GetArmy()"]
        
        if has_limits or target_mode == "multiplayer":
            stop_being_built_body.append("""        local activeLimitRules = GetActiveLimitRules(army)
        if activeLimitRules then
            local brain = self:GetAIBrain()
            for _, rule in ipairs(activeLimitRules) do
                if EntityCategoryContains(rule.category, self) then
                    self.TrackedRuleCategory = rule.category
                    local count = GetTotalCount(brain, rule.category)
                    if count > rule.limit then
                        local pName = GetArmyPlayerName(army)
                        if pName == "" then pName = "Army " .. tostring(army) end
                        PrintText("🛑 [LIMIT EXCEEDED] " .. pName .. ": " .. rule.name .. " cap is " .. tostring(rule.limit) .. "! Unit destroyed.", 18, "ffff2222", 5, "center")
                        self:Destroy()
                        return result
                    elseif count >= rule.limit then
                        AddBuildRestriction(army, rule.category)
                    end
                end
            end
        end""")

        if (has_buffs and target_mode == "player") or target_mode == "multiplayer":
            stop_being_built_body.append("""        local cfg = nil
        if TargetScope == "multiplayer" then
            local prof = GetPlayerProfile(army)
            if prof and prof.unitConfigs then
                local bp = self:GetBlueprint()
                local bpId = string.lower(bp.BlueprintId or self:GetUnitId() or "")
                cfg = prof.unitConfigs[bpId]
            end
        elseif IsTargetArmy(army) and UnitConfigs then
            local bp = self:GetBlueprint()
            local bpId = string.lower(bp.BlueprintId or self:GetUnitId() or "")
            cfg = UnitConfigs[bpId]
        end

        if cfg and self:GetBlueprint().Economy then
            local bp = self:GetBlueprint()
            local brain = self:GetAIBrain()
            if cfg.massDiscount and cfg.massDiscount > 0 and bp.Economy.BuildCostMass then
                local refundMass = math.floor(bp.Economy.BuildCostMass * cfg.massDiscount)
                if refundMass > 0 then brain:GiveResource('Mass', refundMass) end
            end
            if cfg.energyDiscount and cfg.energyDiscount > 0 and bp.Economy.BuildCostEnergy then
                local refundEnergy = math.floor(bp.Economy.BuildCostEnergy * cfg.energyDiscount)
                if refundEnergy > 0 then brain:GiveResource('Energy', refundEnergy) end
            end
        end""")

        if has_relics:
            stop_being_built_body.append("""        if ActiveRelicsByArmy and ActiveRelicsByArmy[army] then
            for rId, rCfg in pairs(ActiveRelicsByArmy[army]) do
                if UnitMatchesRelic(self, rCfg) then
                    self.ActiveRelicBuffs = self.ActiveRelicBuffs or {}
                    self.ActiveRelicBuffs[rId] = rCfg.buffs
                end
            end
        end""")

        if has_buffs or has_relics or target_mode == "multiplayer":
            stop_being_built_body.append("""        RecomputeUnitStats(self)
        self:SetHealth(self, self:GetMaxHealth())""")

        if has_popups:
            stop_being_built_body.append("""        for _, r in ipairs(PopupRules) do
            if r.trigger == "unit_built" then
                if r.scope == "global" or (r.scope == "player" and IsTargetArmy(army)) or r.scope == "allies" then
                    if MatchesUnit(r, self) then
                        FirePopupAlert(r, self)
                    end
                end
            end
        end""")

        class_methods.append("    OnStopBeingBuilt = function(self, builder, layer)\n" + "\n".join(stop_being_built_body) + "\n        return result\n    end,")

        # Method: OnDamage
        damage_body = ["        local amt = amount"]
        if has_popups:
            damage_body.append("""        local army = self:GetArmy()
        if not self.AlertHealthFired and not self:BeenDestroyed() and not self:IsDead() then
            local maxHp = self:GetMaxHealth()
            local curHp = self:GetHealth()
            if maxHp and maxHp > 0 and curHp and curHp > 0 then
                local pct = (curHp / maxHp) * 100
                for _, r in ipairs(PopupRules) do
                    if r.trigger == "health_low" and r.healthPct and pct <= r.healthPct then
                        if r.scope == "global" or (r.scope == "player" and IsTargetArmy(army)) or r.scope == "allies" then
                            if MatchesUnit(r, self) then
                                self.AlertHealthFired = true
                                FirePopupAlert(r, self)
                                break
                            end
                        end
                    end
                end
            end
        end""")

        if has_buffs or has_relics or target_mode == "multiplayer":
            damage_body.append("""        if instigator and not instigator:BeenDestroyed() and not instigator:IsDead() then
            if instigator.ForgeOverhaulTotalDmgMult and instigator.ForgeOverhaulTotalDmgMult ~= 1.0 and amount and amount > 0 then
                amt = amt * instigator.ForgeOverhaulTotalDmgMult
            elseif instigator.CustomDmgMult and amount and amount > 0 then
                amt = amt * instigator.CustomDmgMult
            elseif TargetScope == "multiplayer" and amount and amount > 0 then
                local instArmy = instigator:GetArmy()
                local instProf = GetPlayerProfile(instArmy)
                if instProf and instProf.damageDealtMult and instProf.damageDealtMult ~= 1.0 then
                    amt = amt * instProf.damageDealtMult
                end
            end
        end

        if TargetScope == "multiplayer" and amt and amt > 0 then
            local victimArmy = self:GetArmy()
            local victimProf = GetPlayerProfile(victimArmy)
            if victimProf and victimProf.damageTakenMult and victimProf.damageTakenMult ~= 1.0 then
                amt = amt * victimProf.damageTakenMult
            end
        end""")

        damage_body.append("        return OldUnit.OnDamage(self, instigator, amt, vector, damageType)")
        class_methods.append("    OnDamage = function(self, instigator, amount, vector, damageType)\n" + "\n".join(damage_body) + "\n    end,")

        if has_popups:
            class_methods.append("""    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self:GetArmy()
        local pos = self:GetPosition()
        local savedPos = pos and {pos[1], pos[2], pos[3]} or nil
        for _, r in ipairs(PopupRules) do
            if r.trigger == "unit_killed" then
                if r.scope == "global" or (r.scope == "player" and IsTargetArmy(army)) or r.scope == "allies" then
                    if MatchesUnit(r, self) then
                        FirePopupAlert(r, self, savedPos)
                    end
                end
            end
        end
        return OldUnit.OnKilled(self, instigator, type, overkillRatio)
    end,""")

        if has_limits or target_mode == "multiplayer":
            class_methods.append("""    OnDestroy = function(self)
        local army = self:GetArmy()
        local isTarget = (TargetScope == "multiplayer") or IsTargetArmy(army)
        local cat = self.TrackedRuleCategory
        local result = OldUnit.OnDestroy(self)
        if isTarget and cat then
            ForkThread(function()
                WaitTicks(1)
                RefreshRestrictions(army)
            end)
        end
        return result
    end,

    OnGiven = function(self, newUnit)
        local result = OldUnit.OnGiven(self, newUnit)
        if newUnit and not newUnit:BeenDestroyed() then
            local army = newUnit:GetArmy()
            local activeRules = GetActiveLimitRules(army)
            if activeRules then
                local brain = newUnit:GetAIBrain()
                for _, rule in ipairs(activeRules) do
                    if EntityCategoryContains(rule.category, newUnit) then
                        newUnit.TrackedRuleCategory = rule.category
                        local count = GetTotalCount(brain, rule.category)
                        if count > rule.limit then
                            local pName = GetArmyPlayerName(army)
                            if pName == "" then pName = "Army " .. tostring(army) end
                            PrintText("🛑 [LIMIT EXCEEDED] " .. pName .. ": Gifted " .. rule.name .. " exceeds cap (" .. tostring(rule.limit) .. ")! Destroyed.", 18, "ffff2222", 5, "center")
                            newUnit:Destroy()
                            return result
                        elseif count >= rule.limit then
                            AddBuildRestriction(army, rule.category)
                        end
                    end
                end
            end
        end
        return result
    end,""")

        if has_relics or has_lootbox:
            on_captured_lines = [
                "    OnCaptured = function(self, captor)",
                "        local result = OldUnit.OnCaptured(self, captor)"
            ]
            if has_relics:
                on_captured_lines.append("""        if self.IsRelicObjective and not self.RelicClaimed and captor and not captor:IsDead() then
            local claimerCat = self.RelicClaimerCategory or (categories.MOBILE)
            if claimerCat and not EntityCategoryContains(claimerCat, captor) then
                return result
            end
            OnRelicClaimed(self, captor, self.RelicConfig)
        end""")
            if has_lootbox:
                on_captured_lines.append("""        if self.IsCasinoLootbox and not self.LootboxCracked then
            self.IsCasinoLootbox = true
            local captorArmy = captor and captor:GetArmy()
            if captorArmy then
                local cfg = self.LootboxConfig or LootboxConfig
                local brain = ArmyBrains and ArmyBrains[captorArmy]
                local armySetup = ScenarioInfo.ArmySetup and ScenarioInfo.ArmySetup[captorArmy]
                local pName = (armySetup and armySetup.PlayerName) or (brain and brain.Nickname) or ("Player " .. tostring(captorArmy))

                if cfg and cfg.openMode == "instant_crack" then
                    self.LootboxCracked = true
                    local outcome = RollLootboxOutcome(cfg)
                    if outcome then
                        PrintText("📦💥 [LOOTBOX CRACKED] " .. pName .. " captured & cracked the crate! RUN FOR IT!", 18, "ff34d399", 6, "center")
                        pcall(function()
                            CreateEmitterAtEntity(self, captorArmy, '/effects/emitters/flash_01_emit.bp')
                            CreateEmitterAtEntity(self, captorArmy, '/effects/emitters/destruction_explosion_concussion_ring_01_emit.bp')
                        end)
                        ResolveLootboxOutcome(self, captorArmy, outcome, cfg)
                    end
                else
                    PrintText("🎰 [CASINO CAPTURED] " .. pName .. " secured the Vault! Select it and click PLAY CASINO to spin!", 18, "ffffd700", 6, "center")
                end
            end
        end""")
            on_captured_lines.append("        return result\n    end,")
            class_methods.append("\n".join(on_captured_lines))

        methods_joined = "\n\n".join(class_methods)
        sim_sections.append(f"""local OldUnit = Unit
Unit = Class(OldUnit) {{
{methods_joined}
}}

local OldSetRegen = Unit.SetRegen
if OldSetRegen then
    Unit.SetRegen = function(self, value)
        if self.ForgeOverhaulRegenMult and self.ForgeOverhaulRegenMult ~= 1.0 then
            value = value * self.ForgeOverhaulRegenMult
        end
        return OldSetRegen(self, value)
    end
end
""")

        sim_unit_full_lua = "\n".join(sim_sections)
        with open(hook_sim_dir / "Unit.lua", "w", encoding="utf-8") as f:
            f.write(sim_unit_full_lua)

    # 5. Create zip file in exports/
    zip_path = EXPORTS_DIR / f"{safe_folder_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(target_mod_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = Path(safe_folder_name) / file_path.relative_to(target_mod_dir)
                zipf.write(file_path, arcname)

    return {
        "success": True,
        "modName": mod_name,
        "folderName": safe_folder_name,
        "targetModDir": str(target_mod_dir),
        "zipPath": str(zip_path),
        "totalRules": total_rules,
        "targetMode": target_mode,
        "playerName": player_name,
        "playerProfilesCount": len(player_profiles) if target_mode == "multiplayer" else 0,
        "breakdownSummary": breakdown_text
    }


class ModForgeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(TEMPLATES_DIR / "index.html", "rb") as f:
                self.wfile.write(f.read())
            return
        elif parsed.path == "/combined" or parsed.path == "/combined.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(TEMPLATES_DIR / "combined.html", "rb") as f:
                self.wfile.write(f.read())
            return
        elif parsed.path == "/limits" or parsed.path == "/limits.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(TEMPLATES_DIR / "limits.html", "rb") as f:
                self.wfile.write(f.read())
            return
        elif parsed.path == "/popups" or parsed.path == "/popups.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(TEMPLATES_DIR / "popups.html", "rb") as f:
                self.wfile.write(f.read())
            return
        elif parsed.path == "/relics" or parsed.path == "/relics.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(TEMPLATES_DIR / "relics.html", "rb") as f:
                self.wfile.write(f.read())
            return
        elif parsed.path in ("/lootbox", "/lootbox.html", "/casino", "/casino.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(TEMPLATES_DIR / "lootbox.html", "rb") as f:
                self.wfile.write(f.read())
            return
        elif parsed.path in ("/animator", "/animator.html", "/preview", "/raptor"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(TEMPLATES_DIR / "animator.html", "rb") as f:
                self.wfile.write(f.read())
            return
        elif parsed.path == "/api/units":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(PROCESSED_UNITS).encode("utf-8"))
            return
        elif parsed.path.startswith("/static/"):
            file_rel = parsed.path[len("/static/"):]
            local_file = STATIC_DIR / file_rel
            if local_file.exists() and local_file.is_file():
                self.send_response(200)
                if local_file.suffix == ".css":
                    self.send_header("Content-Type", "text/css; charset=utf-8")
                elif local_file.suffix == ".js":
                    self.send_header("Content-Type", "application/javascript; charset=utf-8")
                elif local_file.suffix == ".png":
                    self.send_header("Content-Type", "image/png")
                elif local_file.suffix == ".json":
                    self.send_header("Content-Type", "application/json")
                elif local_file.suffix == ".wav":
                    self.send_header("Content-Type", "audio/wav")
                self.end_headers()
                with open(local_file, "rb") as f:
                    self.wfile.write(f.read())
                return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/export":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                result = generate_mod_files(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return
        elif parsed.path == "/api/export-limits":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                result = generate_limits_mod_files(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return
        elif parsed.path == "/api/export-popups":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                result = generate_popups_mod_files(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return
        elif parsed.path == "/api/export-relics":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                result = generate_relics_mod_files(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return
        elif parsed.path == "/api/export-lootbox":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                result = generate_lootbox_mod_files(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return
        elif parsed.path == "/api/export-combined":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                result = generate_combined_mod_files(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return
        elif parsed.path == "/api/open-folder":
            try:
                os.startfile(str(DOCUMENTS_MODS_DIR))
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return
        elif parsed.path == "/api/compile_raptor":
            try:
                import subprocess
                res = subprocess.run(["python", str(BASE_DIR / "build_raptor_v2.py")], capture_output=True, text=True, check=True)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "message": "Compiled RaptorFaction mod successfully", "log": res.stdout}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()


def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), ModForgeHandler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"\n=======================================================")
        print(f"  FAF Mod Forge is running at: {url}")
        print(f"  Mods will be saved to: {DOCUMENTS_MODS_DIR}")
        print(f"=======================================================\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")


if __name__ == "__main__":
    run_server()
