# Raptor Lobby Options & Configuration Settings Specification

This document defines the custom lobby options, game rule flags, and difficulty presets for the FAF Raptor Defense mod.

---

## 1. Mod Configuration Options (`options.lua`)

These settings are selectable in the FAF game lobby before launch:

```lua
-- /mods/RaptorFaction/options.lua
options = {
    {
        key = 'RaptorDifficulty',
        name = 'Raptor Difficulty',
        help = 'Controls wave intervals, tech progression speed, unit health/damage, and Queen timing.',
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
    {
        key = 'RaptorQueenCount',
        name = 'Queen Titan Count',
        help = 'Number of Queen Titans that awaken when Queen Anger reaches 100%.',
        values = {
            { text = '1 Queen', key = 1, default = true },
            { text = '2 Queens', key = 2 },
            { text = '3 Queens', key = 3 },
            { text = '4 Queens (Chaos)', key = 4 },
        },
    },
}
```

---

## 2. Baseline Difficulty Presets Table

The table below contrasts the baseline mathematical configuration for each difficulty preset (before player count or custom multipliers):

| Parameter | Very Easy | Easy | Normal | Hard | Very Hard | Epic |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Grace Period** | 9 min ($540\text{s}$) | 8 min ($480\text{s}$) | **7 min ($420\text{s}$)** | 6 min ($360\text{s}$) | 5 min ($300\text{s}$) | 4 min ($240\text{s}$) |
| **Queen Hatch Time** | 55 min | 50 min | **45 min** | 40 min | 35 min | 30 min |
| **Wave Interval** | 120s | 90s | **60s** | 50s | 40s | 30s |
| **Hive Spawn Interval**| 240s | 210s | **180s** | 150s | 120s | 90s |
| **Turret Spawn Interval**| 120s | 100s | **80s** | 60s | 40s | 20s |
| **Damage Multiplier** | $0.40\times$ | $0.60\times$ | **$0.80\times$** | $1.00\times$ | $1.20\times$ | $1.40\times$ |
| **Health Multiplier** | $0.50\times$ | $0.75\times$ | **$1.00\times$** | $1.10\times$ | $1.25\times$ | $1.50\times$ |
| **Anger Bonus / Hive**| $+0.10$ | $+0.15$ | **$+0.20$** | $+0.25$ | $+0.30$ | $+0.35$ |
| **Max Veterancy Rank**| Rank 1 | Rank 2 | **Rank 3** | Rank 4 | Rank 5 | Rank 5 (Elite) |
| **Queen Armor Resist**| $0.50\times$ | $0.75\times$ | **$1.00\times$** | $1.33\times$ | $1.67\times$ | $2.00\times$ |
| **Queen Stagger Stun** | 40s | 35s | **30s** | 30s | 30s | 25s |

---

## 3. Player Count Scaling Formula

To ensure equal challenge across solo games, small 2v2s, and 8-player mega-matches, wave caps and burrows scale dynamically with human player count:

$$\text{MaxWaveSize} = \left(\text{BaseMax} \times 0.75 + \text{BaseMax} \times 0.25 \times \text{HumanTeamCount}\right) \times \text{RaptorSpawnMultiplier}$$

$$\text{MaxBurrows} = \left(\text{BaseBurrows} \times 0.75 + \text{BaseBurrows} \times 0.25 \times \min(\text{HumanTeamCount}, 8)\right) \times \text{RaptorSpawnMultiplier}$$

* Each additional human player in the game increases wave sizes and maximum concurrent hives on the map by **$+25\%$ of baseline**.
