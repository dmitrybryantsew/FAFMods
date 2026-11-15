local NullShell = import('/lua/sim/DefaultProjectiles.lua').NullShell
local EffectTemplate = import('/lua/effecttemplates.lua')
local RandomFloat = import('/lua/utilities.lua').GetRandomFloat

local SubSporeProjectile = '/mods/RaptorFaction/effects/entities/XRA_BioNukeSubSpore01/XRA_BioNukeSubSpore01_proj.bp'

local MainBlastEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_bio_smoke_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_acid_splash_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/effects/emitters/seraphim_expnuke_concussion_01_emit.bp',
    '/effects/emitters/seraphim_inaino_concussion_02_emit.bp',
    '/effects/emitters/shockwave_smoke_01_emit.bp',
    '/effects/emitters/miasma_cloud_01_emit.bp',
}

---@class XRA_BioNukeEffect01 : NullShell
XRA_BioNukeEffect01 = Class(NullShell) {

    EffectThread = function(self)
        local army = self.Army
        local position = self:GetPosition()

        -- Initial thunderous sound and violent camera rumble
        local bp = self.Blueprint
        if bp.Audio and bp.Audio.NukeExplosion then
            self:PlaySound(bp.Audio.NukeExplosion)
        end
        self:ShakeCamera(80, 5, 0, 25)

        -- Knockdown shockwave ring for trees and props
        DamageRing(self, position, 0.1, 45, 1, 'Force', true)
        WaitSeconds(0.1)
        DamageRing(self, position, 0.1, 45, 1, 'Force', true)

        -- Blinding dual-phase toxic flash (viridian core + crimson flare)
        CreateLightParticle(self, -1, army, 240, 20, 'glow_03', 'ramp_green_01')
        WaitSeconds(0.15)
        CreateLightParticle(self, -1, army, 130, 28, 'glow_02', 'ramp_red_02')

        -- Massive biological detonation blast cloud & concussion rings
        for _, emit in MainBlastEffects do
            local em = CreateEmitterAtEntity(self, army, emit)
            if string.find(emit, 'cloud') or string.find(emit, 'smoke') then
                em:ScaleEmitter(12.0)
            elseif string.find(emit, 'splash') then
                em:ScaleEmitter(10.0)
            elseif string.find(emit, 'chunks') then
                em:ScaleEmitter(8.0)
            else
                em:ScaleEmitter(5.0)
            end
        end

        -- Scorch decals on the ground
        local orientation = RandomFloat(0, 2 * math.pi)
        CreateDecal(position, orientation, 'Scorch_012_albedo', '', 'Albedo', 180, 180, 1200, 0, army)
        CreateDecal(position, orientation, 'Crater01_normals', '', 'Normals', 120, 120, 1200, 0, army)

        -- Launch radial salvo of living biological sub-spores
        self:ForkThread(self.CreateChildSporeSalvo)

        -- Spawn persistent bio-fallout (lingering acid mists and creeping spores)
        self:ForkThread(self.FalloutThread)

        WaitSeconds(35)
        self:Destroy()
    end,

    CreateChildSporeSalvo = function(self)
        local num_spores = 16
        local horizontal_angle = (2 * math.pi) / num_spores
        local angleInitial = RandomFloat(0, horizontal_angle)
        local angleVariation = 0.25

        for i = 0, (num_spores - 1) do
            local angle = angleInitial + (i * horizontal_angle) + RandomFloat(-angleVariation, angleVariation)
            local xVec = math.sin(angle)
            local yVec = RandomFloat(0.8, 1.8)
            local zVec = math.cos(angle)
            local velocity = RandomFloat(22, 36)

            local proj = self:CreateProjectile(SubSporeProjectile, 0, 1.5, 0, xVec, yVec, zVec)
            proj:SetVelocity(velocity)
            proj:SetBallisticAcceleration(-14.0)
            proj:SetLifetime(6.0)
        end
    end,

    FalloutThread = function(self)
        local army = self.Army
        local position = self:GetPosition()

        -- Persistent toxic fallout puddles and spore clouds
        local falloutEffects = {
            '/mods/RaptorFaction/effects/emitters/raptor_acid_puddle_01_emit.bp',
            '/mods/RaptorFaction/effects/emitters/raptor_creep_spores_01_emit.bp',
            '/effects/emitters/miasma_cloud_02_emit.bp',
        }

        local emitters = {}
        for _, emit in falloutEffects do
            local em = CreateEmitterAtEntity(self, army, emit)
            if string.find(emit, 'puddle') then
                em:ScaleEmitter(8.0)
            else
                em:ScaleEmitter(6.0)
            end
            table.insert(emitters, em)
        end

        -- Disperse a few extra acid puddles in the inner crater
        for i = 1, 4 do
            local angle = RandomFloat(0, 2 * math.pi)
            local dist = RandomFloat(6, 18)
            local ox = math.sin(angle) * dist
            local oz = math.cos(angle) * dist
            local pud = CreateAttachedEmitter(self, -1, army, '/mods/RaptorFaction/effects/emitters/raptor_acid_puddle_01_emit.bp')
            if pud then
                pud:OffsetEmitter(ox, 0, oz)
                pud:ScaleEmitter(5.0)
                table.insert(emitters, pud)
            end
        end

        WaitSeconds(25)
        for _, em in emitters do
            if em then
                em:Destroy()
            end
        end
    end,
}

TypeClass = XRA_BioNukeEffect01
