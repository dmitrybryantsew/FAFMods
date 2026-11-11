-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/lua/RaptorStats.lua
-- **  Author   :  Adapted from FAF Master Overhaul for Raptor Swarm Faction
-- **  Summary  :  Dynamic in-game unit stat modifier engine scaling unit health,
-- **              damage, speed, range, rate of fire, and regeneration with
-- **              Tech Anger and Queen Anger.
-- **
-- ****************************************************************************

local Buff = import('/lua/sim/buff.lua')
local BuffBlueprint = BuffBlueprint

---Difficulty baseline multipliers
local DifficultyModifiers = {
    veryeasy = { Health = 0.50, Damage = 0.40, Speed = 0.85, Regen = 0.50 },
    easy     = { Health = 0.75, Damage = 0.60, Speed = 0.90, Regen = 0.75 },
    normal   = { Health = 1.00, Damage = 0.80, Speed = 1.00, Regen = 1.00 },
    hard     = { Health = 1.10, Damage = 1.00, Speed = 1.05, Regen = 1.25 },
    veryhard = { Health = 1.25, Damage = 1.20, Speed = 1.10, Regen = 1.50 },
    epic     = { Health = 1.50, Damage = 1.40, Speed = 1.15, Regen = 2.00 },
}

---Recomputes and applies all dynamic Raptor stats based on Tech/Queen Anger and Difficulty
---Uses the FAF Master Overhaul in-game stat modification engine.
---@param unit Unit
---@param techAnger number (0 - 999)
---@param queenAnger number (0 - 100)
---@param difficulty string ('veryeasy', 'easy', 'normal', 'hard', 'veryhard', 'epic')
function RecomputeRaptorStats(unit, techAnger, queenAnger, difficulty)
    if not unit or unit:BeenDestroyed() or unit:IsDead() then return end

    techAnger = techAnger or 0
    queenAnger = queenAnger or 0
    difficulty = difficulty or 'normal'

    local d = DifficultyModifiers[difficulty] or DifficultyModifiers['normal']

    -- Multipliers scale smoothly with Tech Anger (up to +30%) and Queen Anger (Regen)
    local angerNorm = math.min(100, techAnger)
    local totalHpMult    = d.Health * (1.0 + angerNorm * 0.003)
    local totalDmgMult   = d.Damage * (1.0 + angerNorm * 0.003)
    local totalSpeedMult = d.Speed  * (1.0 + angerNorm * 0.001)
    local totalRegenMult = d.Regen  * (1.0 + (queenAnger * 0.01))

    -- 1. HEALTH: Master Overhaul Dynamic Buff Pattern
    -- Generates unique BuffBlueprint on the fly and applies it cleanly without C++ blueprint mutation
    local buffName = 'Raptor_HP_' .. string.gsub(string.format("%.3f", totalHpMult), "%.", "_")
    if not Buffs[buffName] then
        BuffBlueprint {
            Name = buffName,
            DisplayName = buffName,
            BuffType = 'RAPTOR_TOTAL_HEALTH',
            Stacks = 'REPLACE',
            Duration = -1,
            Affects = {
                MaxHealth = {
                    Add = 0,
                    Mult = totalHpMult,
                    DoNotFill = false,
                },
            },
        }
    end
    Buff.ApplyBuff(unit, buffName)
    unit:SetHealth(unit, unit:GetMaxHealth())

    -- 2. OUTBOUND DAMAGE: Stored on unit and multiplied inside OnDamage
    unit.RaptorTotalDmgMult = totalDmgMult

    -- 3. MOBILITY: Engine Acceleration, Speed, and Turn Multipliers
    if unit.SetSpeedMult then unit:SetSpeedMult(totalSpeedMult) end
    if unit.SetAccMult   then unit:SetAccMult(totalSpeedMult) end
    if unit.SetTurnMult  then unit:SetTurnMult(totalSpeedMult) end

    -- 4. WEAPONS: Range, Rate of Fire, and Splash Radius
    local wCount = unit:GetWeaponCount() or 0
    for i = 1, wCount do
        local wep = unit:GetWeapon(i)
        if wep then
            local wbp = wep:GetBlueprint()
            -- Range scaling (up to +15% at 100 anger for artillery/spikers)
            if wbp and wbp.MaxRadius and wep.ChangeMaxRadius then
                local rangeMult = 1.0 + (angerNorm * 0.0015)
                wep:ChangeMaxRadius(math.floor(wbp.MaxRadius * rangeMult))
            end
            -- Rate of fire scaling
            if wbp and wbp.RateOfFire and wep.SetRateOfFire then
                local rofMult = 1.0 + (angerNorm * 0.001)
                wep:SetRateOfFire(wbp.RateOfFire * rofMult)
            end
        end
    end

    -- 5. REGENERATION
    local bp = unit:GetBlueprint()
    local baseRegen = (bp.Defense and bp.Defense.RegenRate) or 5
    if unit.SetRegenRate then
        unit:SetRegenRate(math.floor(baseRegen * totalRegenMult))
    end

    -- 6. SHIELDS (For Bosses / Spire Nests if equipped)
    if unit.MyShield then
        unit.OriginalShieldMaxHealth = unit.OriginalShieldMaxHealth or unit.MyShield:GetMaxHealth()
        local newShieldMax = math.floor(unit.OriginalShieldMaxHealth * totalHpMult)
        unit.MyShield:SetMaxHealth(newShieldMax)
        unit.MyShield:SetHealth(unit.MyShield, newShieldMax)
    end
end
