local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon
local Eggs = import('/mods/RaptorFaction/lua/RaptorEggs.lua')

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class XRA0303 : CWalkingLandUnit
XRA0303 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        PlasmaBlob = ClassWeapon(DefaultProjectileWeapon) {},
        MeleeCleave = ClassWeapon(DefaultProjectileWeapon) {},
        AASpores = ClassWeapon(DefaultProjectileWeapon) {},
    },

    CreateWreckage = function(self, overkillRatio)
        return nil
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(3.5)
        end
        Eggs.SpawnRaptorEgg(self)
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}

TypeClass = XRA0303
