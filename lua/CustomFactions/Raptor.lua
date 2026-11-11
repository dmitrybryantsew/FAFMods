-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/lua/CustomFactions/Raptor.lua
-- **  Author   :  FAF Community & BAR Team
-- **  Summary  :  Registers the Raptor Swarm as a full playable & AI faction
-- **              with custom faction icons, colors, and building prefixes.
-- **
-- ****************************************************************************

FactionList = {
    {
        Key = 'raptor',
        Category = 'RAPTOR',
        FactionInUnitBp = 'Raptor',
        IsCustomFaction = true,
        DisplayName = "<LOC _Raptor>Raptor Swarm",
        SoundPrefix = 'Cybran',
        InitialUnit = 'xra0107',
        CampaignFileDesignator = 'P',
        TransmissionLogColor = 'ffff3300',
        Icon = "/mods/RaptorFaction/textures/ui/common/widgets/faction-icons-alpha_bmp/raptor_ico.dds",
        VeteranIcon = "/mods/RaptorFaction/textures/ui/common/game/veteran-logo_bmp/raptor-veteran_bmp.dds",
        SmallIcon = "/mods/RaptorFaction/textures/ui/common/faction_icon-sm/raptor_ico.dds",
        LargeIcon = "/mods/RaptorFaction/textures/ui/common/faction_icon-lg/raptor_ico.dds",
        TooltipID = 'lob_raptor',
        DefaultSkin = 'cybran',
        loadingMovie = '/movies/cybran_load.sfd',
        loadingColor = 'FFff3300',
        loadingTexture = '/cybran_load.dds',
        IdleEngTextures = {
            T1 = '/mods/RaptorFaction/icons/units/xra0109_icon.dds',
            T2 = '/mods/RaptorFaction/icons/units/xra0109_icon.dds',
            T2F = '/mods/RaptorFaction/icons/units/xra0109_icon.dds',
            T3 = '/mods/RaptorFaction/icons/units/xra0109_icon.dds',
            SCU = '/mods/RaptorFaction/icons/units/xra0109_icon.dds',
        },
        IdleFactoryTextures = {
            LAND = {
                '/mods/RaptorFaction/icons/units/xra0107_icon.dds',
                '/mods/RaptorFaction/icons/units/xra0107_icon.dds',
                '/mods/RaptorFaction/icons/units/xra0107_icon.dds',
            },
            AIR = {
                '/mods/RaptorFaction/icons/units/xra0107_icon.dds',
                '/mods/RaptorFaction/icons/units/xra0107_icon.dds',
                '/mods/RaptorFaction/icons/units/xra0107_icon.dds',
            },
            NAVAL = {
                '/mods/RaptorFaction/icons/units/xra0107_icon.dds',
                '/mods/RaptorFaction/icons/units/xra0107_icon.dds',
                '/mods/RaptorFaction/icons/units/xra0107_icon.dds',
            },
        },
        GAZ_UI_Info = {
            BuildingIdPrefixes = {
                'xra',
            },
        },
    }
}
