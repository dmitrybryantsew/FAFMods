local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon
local Eggs = import('/mods/RaptorFaction/lua/RaptorEggs.lua')
local QueenAI = import('/mods/RaptorFaction/lua/QueenBossAI.lua')

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class RoarWeapon : DefaultProjectileWeapon
local RoarWeapon = ClassWeapon(DefaultProjectileWeapon) {
    CreateProjectileAtMuzzle = function(self, muzzle)
        local proj = DefaultProjectileWeapon.CreateProjectileAtMuzzle(self, muzzle)
        if not self.unit.Dead then
            local roarAnim = CreateAnimator(self.unit)
            roarAnim:PlayAnim('/mods/RaptorFaction/units/XRA0401/XRA0401_Aroar.sca', false)
            roarAnim:SetRate(1.2)
        end
        return proj
    end,
}

---@class XRA0401 : CWalkingLandUnit
XRA0401 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        RoarCannon = ClassWeapon(RoarWeapon) {},
        MeleeCleave = ClassWeapon(DefaultProjectileWeapon) {},
        AAFlak = ClassWeapon(DefaultProjectileWeapon) {},
    },

    CreateWreckage = function(self, overkillRatio)
        return nil
    end,

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
        -- Start Queen Boss AI threads
        if QueenAI then
            if QueenAI.StartQueenGestationThread then
                QueenAI.StartQueenGestationThread(self)
            end
            if QueenAI.StartQueenBombardmentThread then
                QueenAI.StartQueenBombardmentThread(self)
            end
            if QueenAI.StartQueenKineticStompThread then
                QueenAI.StartQueenKineticStompThread(self)
            end
        end
    end,

    OnDamage = function(self, instigator, amount, vector, damageType)
        -- Process incoming damage through boss posture stagger, dynamic resistance, and anti-cheese
        local modAmount = amount
        if QueenAI and QueenAI.ProcessQueenIncomingDamage then
            modAmount = QueenAI.ProcessQueenIncomingDamage(self, instigator, amount, damageType)
        end
        return CWalkingLandUnit.OnDamage(self, instigator, modAmount, vector, damageType)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(8.0)
        end

        Eggs.SpawnRaptorEgg(self)
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(8.0)
        end
    end,
}

TypeClass = XRA0401
