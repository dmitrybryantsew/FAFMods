-- ****************************************************************************
-- **
-- **  Hook     :  /lua/shared/formations/categorizeUnits.lua
-- **  Author   :  Raptor Swarm Faction Formation Fix
-- **  Summary  :  Integrates mobile shield units (such as XRA0225 Bio-Shield Beetle)
-- **              into the Land formation Shields category, preventing fallthrough
-- **              to RemainingCategory which flooded the log with thousands of
-- **              synchronous *FORMATION DEBUG disk writes causing 1-second stutter.
-- **
-- ****************************************************************************

if ShieldCategory and LandCategories then
    ShieldCategory = ShieldCategory + categories.xra0225 + (categories.SHIELD * categories.LAND * categories.MOBILE)
    LandCategories.Shields = ShieldCategory
    if NonShieldCategory then
        NonShieldCategory = categories.ALLUNITS - ShieldCategory
    end
    if LandCategories.RemainingCategory then
        LandCategories.RemainingCategory = LandCategories.RemainingCategory - (categories.SHIELD * categories.LAND * categories.MOBILE) - categories.xra0225
    end
end
