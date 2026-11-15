local CAirUnit = import('/lua/cybranunits.lua').CAirUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon
local EffectTemplate = import('/lua/EffectTemplates.lua')
local QueenAI = import('/mods/RaptorFaction/lua/QueenBossAI.lua')

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class AcidGooWeapon : DefaultProjectileWeapon
local AcidGooWeapon = ClassWeapon(DefaultProjectileWeapon) {
    FxMuzzleFlash = EffectTemplate.PhasicAutoGunMuzzleFlash,
}

---@class DorsalSporeWeapon : DefaultProjectileWeapon
local DorsalSporeWeapon = ClassWeapon(DefaultProjectileWeapon) {
    FxMuzzleFlash = EffectTemplate.DefaultMuzzleFlash01,
}

---@class BroodBombWeapon : DefaultProjectileWeapon
local BroodBombWeapon = ClassWeapon(DefaultProjectileWeapon) {
    FxMuzzleFlash = EffectTemplate.DefaultMuzzleFlash02,
}

---@class XRA0402 : CAirUnit
XRA0402 = ClassUnit(CAirUnit) {
    Weapons = {
        AcidGooCannon = ClassWeapon(AcidGooWeapon) {},
        DorsalSporeFlak = ClassWeapon(DorsalSporeWeapon) {},
        BroodBombDrop = ClassWeapon(BroodBombWeapon) {},
    },

    CreateWreckage = function(self, overkillRatio)
        return nil
    end,

    OnCreate = function(self)
        CAirUnit.OnCreate(self)
        self.TriggeredEmp75 = false
        self.TriggeredVanguard50 = false
        self.TriggeredFrenzy25 = false

        -- Start looping flight wing flap & body sway animation
        local flyAnim = CreateAnimator(self)
        flyAnim:PlayAnim('/mods/RaptorFaction/units/XRA0402/XRA0402_Afly01.sca', true)
        flyAnim:SetRate(1.0)
        self.Trash:Add(flyAnim)

        self:ForkThread(self.HealthPhaseMonitorThread)
    end,

    ---Monitors Sky Queen health thresholds for dynamic ability unlocks
    HealthPhaseMonitorThread = function(self)
        local brain = self:GetAIBrain()
        local army = self.Army

        while self and not self.Dead do
            WaitSeconds(1.0)

            if not self.Dead then
                local curHp = self:GetHealth()
                local maxHp = self:GetMaxHealth()
                local hpPct = (curHp / maxHp) * 100

                -- 1. 75% HP: Apocalyptic Bio-EMP Pulse (Disables shields and defenses)
                if hpPct <= 75 and not self.TriggeredEmp75 then
                    self.TriggeredEmp75 = true
                    Sync.RaptorAnnounce = {
                        Text = "WARNING: SKY QUEEN UNLEASHES AN APOCALYPTIC BIO-EMP SHOCKWAVE!",
                        Color = 'cyan'
                    }

                    local p = self:GetPosition()
                    CreateEmitterAtEntity(self, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp'):ScaleEmitter(4.0)

                    -- Stun all enemy units in 42-unit radius and overload shields
                    local targets = brain:GetUnitsAroundPoint(categories.ALLUNITS, p, 42.0, 'Enemy')
                    for _, u in targets do
                        if u and not u.Dead and not u:BeenDestroyed() then
                            u:SetStunned(8.0)
                            if u.MyShield then
                                u.MyShield:ApplyDamage(nil, 8000, Vector(0,0,0), 'EMP', false)
                            end
                        end
                    end
                end

                -- 2. 50% HP: Summons Brood Air Escort Flock (Blimpies + Spore Fighters)
                if hpPct <= 50 and not self.TriggeredVanguard50 then
                    self.TriggeredVanguard50 = true
                    Sync.RaptorAnnounce = {
                        Text = "WARNING: SKY QUEEN CALLS DOWN THE BROOD FLOCK ESCORT!",
                        Color = 'yellow'
                    }

                    local p = self:GetPosition()
                    -- Spawn 2x Bio-Zeppelin Blimpies (XRA0227)
                    for i = 1, 2 do
                        local bx = p[1] + (math.random() - 0.5) * 12
                        local bz = p[3] + (math.random() - 0.5) * 12
                        local blimpy = brain:CreateUnitNearSpot('XRA0227', bx, bz)
                        if blimpy then
                            IssueGuard({blimpy}, self)
                        end
                    end

                    -- Spawn 4x Spore Fighters (XRA0115)
                    for i = 1, 4 do
                        local fx = p[1] + (math.random() - 0.5) * 16
                        local fz = p[3] + (math.random() - 0.5) * 16
                        local fighter = brain:CreateUnitNearSpot('XRA0115', fx, fz)
                        if fighter then
                            IssueGuard({fighter}, self)
                        end
                    end
                end

                -- 3. 25% HP: Blood Frenzy Roar (+35% Flight Speed, Rapid Weapon Fire)
                if hpPct <= 25 and not self.TriggeredFrenzy25 then
                    self.TriggeredFrenzy25 = true
                    Sync.RaptorAnnounce = {
                        Text = "CRITICAL ALERT: SKY QUEEN ENTERS BLOOD FRENZY!",
                        Color = 'red'
                    }

                    if self.SetSpeedMult then
                        self:SetSpeedMult(1.35)
                    end
                end
            end
        end
    end,

    OnDamage = function(self, instigator, amount, vector, damageType)
        -- Process through Boss AI adaptive resistance and anti-cheese
        local modAmount = QueenAI.ProcessQueenIncomingDamage(self, instigator, amount, damageType)
        return CAirUnit.OnDamage(self, instigator, modAmount, vector, damageType)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army

        -- Visceral death gore emitters
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(6.0)
        end

        -- Catastrophic crash & transition to Phase 2 (Land Matriarch Queen Titan)
        QueenAI.TransitionToLandQueen(self)

        CAirUnit.OnKilled(self, instigator, type, overkillRatio)
    end,
}

TypeClass = XRA0402
