local Eggs = import('/mods/RaptorFaction/lua/RaptorEggs.lua')
local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon
local EffectTemplate = import('/lua/EffectTemplates.lua')

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class TiamatCleaveWeapon : DefaultProjectileWeapon
local TiamatCleaveWeapon = ClassWeapon(DefaultProjectileWeapon) {
    FxMuzzleFlash = EffectTemplate.PhasicAutoGunMuzzleFlash,

    CreateProjectileAtMuzzle = function(self, muzzle)
        local proj = DefaultProjectileWeapon.CreateProjectileAtMuzzle(self, muzzle)
        if self.unit and self.unit.PlayScytheCleaveAttack then
            self.unit:PlayScytheCleaveAttack()
        end
        return proj
    end,
}

---@class TiamatFlamerWeapon : DefaultProjectileWeapon
local TiamatFlamerWeapon = ClassWeapon(DefaultProjectileWeapon) {
    FxMuzzleFlash = {
        '/mods/RaptorFaction/effects/emitters/raptor_bio_flame_muzzle_01_emit.bp',
        '/effects/emitters/default_muzzle_flash_01_emit.bp',
    },
    FxMuzzleFlashScale = 0.9,
}

---@class XRA0328 : CWalkingLandUnit
XRA0328 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Weapon1 = ClassWeapon(TiamatCleaveWeapon) {},
        Weapon2 = ClassWeapon(TiamatFlamerWeapon) {},
    },

    CreateWreckage = function(self, overkillRatio)
        Eggs.SpawnRaptorEgg(self)
        return nil
    end,

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)

        -- Initialize rotators for the 4 scythe cleavers on the head
        self.Rotators = {
            lforearmu = CreateRotator(self, 'lforearmu', 'y', 0, 700, 1200),
            lbladeu   = CreateRotator(self, 'lbladeu',   'y', 0, 700, 1200),
            rforearmu = CreateRotator(self, 'rforearmu', 'y', 0, 700, 1200),
            rbladeu   = CreateRotator(self, 'rbladeu',   'y', 0, 700, 1200),

            lforearml = CreateRotator(self, 'lforearml', 'y', 0, 700, 1200),
            lbladel   = CreateRotator(self, 'lbladel',   'y', 0, 700, 1200),
            rforearml = CreateRotator(self, 'rforearml', 'y', 0, 700, 1200),
            rbladel   = CreateRotator(self, 'rbladel',   'y', 0, 700, 1200),
        }
    end,

    OnStopBeingBuilt = function(self, builder, layer)
        CWalkingLandUnit.OnStopBeingBuilt(self, builder, layer)
        -- Energize personal carapace shield
        self:EnableShield()
    end,

    PlayScytheCleaveAttack = function(self)
        if self.ScytheThread then
            KillThread(self.ScytheThread)
        end
        self.ScytheThread = self:ForkThread(self.ScytheCleaveThread)
    end,

    ScytheCleaveThread = function(self)
        local rot = self.Rotators
        if not rot then return end

        -- Snap mandibles/scythes inward with high force
        rot.lforearmu:SetGoal(-75)
        rot.lforearmu:SetSpeed(700)
        rot.lbladeu:SetGoal(75)
        rot.lbladeu:SetSpeed(700)

        rot.rforearmu:SetGoal(75)
        rot.rforearmu:SetSpeed(700)
        rot.rbladeu:SetGoal(-75)
        rot.rbladeu:SetSpeed(700)

        rot.lforearml:SetGoal(-60)
        rot.lforearml:SetSpeed(650)
        rot.lbladel:SetGoal(60)
        rot.lbladel:SetSpeed(650)

        rot.rforearml:SetGoal(60)
        rot.rforearml:SetSpeed(650)
        rot.rbladel:SetGoal(-60)
        rot.rbladel:SetSpeed(650)

        WaitFor(rot.rbladeu)

        -- Smoothly open back to ready stance
        rot.lforearmu:SetGoal(0)
        rot.lforearmu:SetSpeed(220)
        rot.lbladeu:SetGoal(0)
        rot.lbladeu:SetSpeed(220)

        rot.rforearmu:SetGoal(0)
        rot.rforearmu:SetSpeed(220)
        rot.rbladeu:SetGoal(0)
        rot.rbladeu:SetSpeed(220)

        rot.lforearml:SetGoal(0)
        rot.lforearml:SetSpeed(220)
        rot.lbladel:SetGoal(0)
        rot.lbladel:SetSpeed(220)

        rot.rforearml:SetGoal(0)
        rot.rforearml:SetSpeed(220)
        rot.rbladel:SetGoal(0)
        rot.rbladel:SetSpeed(220)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        Eggs.SpawnRaptorEgg(self)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.2)
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}

TypeClass = XRA0328
