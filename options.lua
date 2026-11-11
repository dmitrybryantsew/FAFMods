-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/options.lua
-- **  Author   :  Raptor Swarm Faction Lobby Options
-- **  Summary  :  Lobby options for Raptor Difficulty, Placement, and Waves.
-- **
-- ****************************************************************************

options = {
    {
        key = 'RaptorDifficulty',
        name = 'Raptor Difficulty',
        help = 'Controls wave intervals, tech anger speed, unit health/damage, and Queen timing.',
        values = {
            { text = 'Very Easy', help = 'Relaxed game for testing or beginners', key = 'veryeasy' },
            { text = 'Easy', help = 'Gentle progression with longer grace period', key = 'easy' },
            { text = 'Normal', help = 'Standard balanced Raptor experience', key = 'normal', default = true },
            { text = 'Hard', help = 'Aggressive swarms and faster teching', key = 'hard' },
            { text = 'Very Hard', help = 'Relentless onslaught; requires tight teamwork', key = 'veryhard' },
            { text = 'Epic', help = 'Brutal challenge for master commanders', key = 'epic' },
        },
    },
    {
        key = 'RaptorPlacement',
        name = 'Hive Placement Mode',
        help = 'Controls where Hives (Burrows) are allowed to germinate across the map.',
        values = {
            { text = 'Growing Spawn Box', help = 'Hives spawn in an expanding radius that covers more map as Tech Anger rises', key = 'initialbox', default = true },
            { text = 'Enemy Start Box Only', help = 'Hives are strictly confined inside the assigned enemy start box', key = 'alwaysbox' },
            { text = 'Spawn Anywhere (Avoid Vision)', help = 'Hives can burrow up anywhere on the map outside player line of sight', key = 'avoid' },
        },
    },
    {
        key = 'RaptorEndless',
        name = 'Endless Survival Mode',
        help = 'When the Queen is slain, the match does not end. Difficulty loops infinitely with higher stats and multipliers.',
        values = {
            { text = 'Disabled', help = 'Killing the Queen achieves victory', key = 'disabled', default = true },
            { text = 'Enabled', help = 'Infinitely looping escalating survival waves', key = 'enabled' },
        },
    },
    {
        key = 'RaptorQueenHatchMult',
        name = 'Queen Hatching Time Multiplier',
        help = 'Scales how quickly Queen Anger climbs from 0 to 100 percent.',
        values = {
            { text = '0.5x (Super Fast Queen)', key = 0.5 },
            { text = '0.75x (Fast Queen)', key = 0.75 },
            { text = '1.0x (Standard Time)', key = 1.0, default = true },
            { text = '1.5x (Long Match)', key = 1.5 },
            { text = '2.0x (Double Time)', key = 2.0 },
        },
    },
    {
        key = 'RaptorSpawnCountMult',
        name = 'Wave Size Multiplier',
        help = 'Multiplies the total number of units spawned in every wave.',
        values = {
            { text = '1.0x (Standard Waves)', key = 1.0, default = true },
            { text = '1.5x (Heavy Waves)', key = 1.5 },
            { text = '2.0x (Double Swarms)', key = 2.0 },
            { text = '3.0x (Triple Swarms)', key = 3.0 },
            { text = '5.0x (Apocalyptic)', key = 5.0 },
        },
    },
    {
        key = 'RaptorGracePeriodMult',
        name = 'Grace Period Multiplier',
        help = 'Scales the initial peacetime before the first wave begins.',
        values = {
            { text = '0.5x (Short Peacetime)', key = 0.5 },
            { text = '1.0x (Standard Grace Period)', key = 1.0, default = true },
            { text = '1.5x (Extended Buildup)', key = 1.5 },
            { text = '2.0x (Double Buildup Time)', key = 2.0 },
        },
    },
}
