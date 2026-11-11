-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/lua/RaptorBaseUnit.lua
-- **  Author   :  Adapted from BAR for Supreme Commander: Forged Alliance
-- **  Summary  :  Unified base class/mixin for all biological Raptor units.
-- **              Provides Master Overhaul damage scaling, behavioral traits,
-- **              egg drops on death, and blood gore death effects.
-- **
-- ****************************************************************************

local Eggs = import('/mods/RaptorFaction/lua/RaptorEggs.lua')
local PlatoonAI = import('/mods/RaptorFaction/lua/RaptorPlatoonAI.lua')

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---Mixin class providing biological raptor behaviors
---@class RaptorUnitMixin
RaptorUnitMixin = {
    OnCreate = function(self)
        -- Initialize biological firestate and traits
        self.BloodScale = self.BloodScale or 1.0
    end,

    OnDamage = function(self, instigator, amount, vector, damageType)
        local amt = amount
        -- 1. Master Overhaul outbound damage multiplier (applied if attacker is a buffed Raptor)
        if instigator and instigator.RaptorTotalDmgMult and instigator.RaptorTotalDmgMult ~= 1.0 and amt > 0 then
            amt = amt * instigator.RaptorTotalDmgMult
        end

        -- 2. Behavioral Reactions on Taking Damage
        if not self.Dead and instigator and not instigator.Dead then
            local bp = self:GetBlueprint()
            local cats = bp.CategoriesHash or {}

            -- Berserk reaction for Assault Behemoths
            if cats['BERSERK'] and not self.IsBerserk then
                PlatoonAI.TriggerBerserkCharge(self, instigator)
            -- Coward retreat for light swarmers
            elseif cats['COWARD'] and (self:GetHealth() / self:GetMaxHealth()) < 0.80 then
                PlatoonAI.TriggerCowardFlee(self, instigator)
            -- Spectre blink teleport
            elseif cats['SPECTRE'] then
                PlatoonAI.TriggerSpectreBlink(self, instigator:GetPosition())
            end
        end

        return amt
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self:GetArmy()
        local scale = (self.BloodScale or 1.0)

        -- 1. Visceral Alien Blood Spray Effects
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end

        -- 2. Drop Biomass Raptor Egg Sac
        Eggs.SpawnRaptorEgg(self)

        -- 3. Notify Raptor Spawner of Hive / Spire destruction (Spikes Player Aggression)
        local bp = self:GetBlueprint()
        if bp and bp.CategoriesHash and (bp.CategoriesHash['BURROW'] or bp.CategoriesHash['SPIRE']) then
            local Spawner = import('/mods/RaptorFaction/lua/RaptorSpawner.lua')
            if Spawner and Spawner.OnRaptorStructureKilled then
                Spawner.OnRaptorStructureKilled(self, instigator)
            end
        end
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self:GetArmy()
        local scale = (self.BloodScale or 1.0) * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}
