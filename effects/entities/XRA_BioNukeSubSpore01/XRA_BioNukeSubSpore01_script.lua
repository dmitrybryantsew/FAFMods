local SinglePolyTrailProjectile = import('/lua/sim/DefaultProjectiles.lua').SinglePolyTrailProjectile

---@class XRA_BioNukeSubSpore01 : SinglePolyTrailProjectile
XRA_BioNukeSubSpore01 = ClassProjectile(SinglePolyTrailProjectile) {
    PolyTrail = '/mods/RaptorFaction/effects/emitters/raptor_spore_polytrail_01_emit.bp',
    PolyTrailOffset = 0,

    FxTrails = {
        '/mods/RaptorFaction/effects/emitters/raptor_acid_steam_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_creep_spores_01_emit.bp',
    },

    FxImpactLand = {
        '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_acid_splash_01_emit.bp',
        '/effects/emitters/destruction_land_hit_puff_05_emit.bp',
    },
    FxImpactWater = {
        '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_acid_splash_01_emit.bp',
    },
    FxImpactUnit = {
        '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_acid_splash_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    },
    FxImpactProp = {
        '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
        '/mods/RaptorFaction/effects/emitters/raptor_acid_splash_01_emit.bp',
    },

    FxLandHitScale = 2.0,
    FxUnitHitScale = 2.0,
    FxWaterHitScale = 2.0,
    FxPropHitScale = 2.0,
}

TypeClass = XRA_BioNukeSubSpore01
