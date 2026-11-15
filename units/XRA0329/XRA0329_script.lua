local Eggs = import('/mods/RaptorFaction/lua/RaptorEggs.lua')
local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon
local EffectTemplate = import('/lua/EffectTemplates.lua')

---@class DragonCleaveWeapon : DefaultProjectileWeapon
local DragonCleaveWeapon = ClassWeapon(DefaultProjectileWeapon) {
    FxMuzzleFlash = EffectTemplate.PhasicAutoGunMuzzleFlash,
}

---@class DragonMagmaWeapon : DefaultProjectileWeapon
local DragonMagmaWeapon = ClassWeapon(DefaultProjectileWeapon) {
    FxMuzzleFlash = EffectTemplate.CLaserMuzzleFlash01,
}

---@class DragonSporeWeapon : DefaultProjectileWeapon
local DragonSporeWeapon = ClassWeapon(DefaultProjectileWeapon) {
    FxMuzzleFlash = EffectTemplate.CElectronBolterMuzzleFlash01,
}

---@class XRA0329 : CWalkingLandUnit
XRA0329 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Weapon1 = ClassWeapon(DragonCleaveWeapon) {},
        Weapon2 = ClassWeapon(DragonMagmaWeapon) {},
        Weapon3 = ClassWeapon(DragonSporeWeapon) {},
    },

    CreateWreckage = function(self, overkillRatio)
        Eggs.SpawnRaptorEgg(self)
        return nil
    end,

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        -- Massive blood rupture upon Herald death
        local army = self.Army
        CreateEmitterAtEntity(self, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp'):ScaleEmitter(3.5)
        CreateEmitterAtEntity(self, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp'):ScaleEmitter(3.0)
        CreateEmitterAtEntity(self, army, '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp'):ScaleEmitter(2.5)
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}

TypeClass = XRA0329
