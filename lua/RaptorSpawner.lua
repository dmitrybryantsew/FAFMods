-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/lua/RaptorSpawner.lua
-- **  Author   :  Ported from Beyond All Reason (raptor_spawner_defense.lua) to FAF
-- **  Summary  :  Master Dual-Anger Engine, Wave Generator, Hive Spawner,
-- **              and Queen Titan sequence coordinator.
-- **
-- ****************************************************************************

local Creep = import('/mods/RaptorFaction/lua/RaptorCreep.lua')
local Stats = import('/mods/RaptorFaction/lua/RaptorStats.lua')
local PlatoonAI = import('/mods/RaptorFaction/lua/RaptorPlatoonAI.lua')
local Targeting = import('/mods/RaptorFaction/lua/RaptorTargeting.lua')

local function GetBrainStartVector(brain)
    if not brain then return { 0, 0, 0 } end
    local units = brain:GetListOfUnits(categories.COMMAND + categories.BURROW, false)
    if units and units[1] and not units[1].Dead then
        local p = units[1]:GetPosition()
        return { p[1], p[2], p[3] }
    end
    if brain.GetArmyStartPos then
        local x, z = brain:GetArmyStartPos()
        if x and z and (x ~= 0 or z ~= 0) then
            return { x, GetSurfaceHeight(x, z), z }
        end
    end
    if ScenarioInfo and ScenarioInfo.size then
        local cx = ScenarioInfo.size[1] / 2
        local cz = ScenarioInfo.size[2] / 2
        return { cx, GetSurfaceHeight(cx, cz), cz }
    end
    return { 0, 0, 0 }
end

-- State
local RaptorArmy = nil
local ActiveBurrows = {}
local TechAnger = 0
local QueenAnger = 0
local PlayerAggression = 0
local QueenSpawned = false
local GameOver = false
local RaptorKills = 0
local QueensKilled = 0
local ActiveQueen = nil

-- Configuration Presets
local DifficultyParams = {
    veryeasy = { GracePeriod = 540, QueenTime = 3300, WaveInterval = 120, BurrowInterval = 240, TurretInterval = 120, AngerBonus = 0.10, SpawnMult = 1.0 },
    easy     = { GracePeriod = 480, QueenTime = 3000, WaveInterval = 90,  BurrowInterval = 210, TurretInterval = 100, AngerBonus = 0.15, SpawnMult = 1.0 },
    normal   = { GracePeriod = 420, QueenTime = 2700, WaveInterval = 60,  BurrowInterval = 180, TurretInterval = 80,  AngerBonus = 0.20, SpawnMult = 1.0 },
    hard     = { GracePeriod = 360, QueenTime = 2400, WaveInterval = 50,  BurrowInterval = 150, TurretInterval = 60,  AngerBonus = 0.25, SpawnMult = 1.0 },
    veryhard = { GracePeriod = 300, QueenTime = 2100, WaveInterval = 40,  BurrowInterval = 120, TurretInterval = 40,  AngerBonus = 0.30, SpawnMult = 1.0 },
    epic     = { GracePeriod = 240, QueenTime = 1800, WaveInterval = 30,  BurrowInterval = 90,   TurretInterval = 20,  AngerBonus = 0.35, SpawnMult = 1.0 },
}

local CurrentDifficulty = 'normal'
local Config = DifficultyParams['normal']

-- Unit Tiers mapped by TechAnger (Mobile Pack Attackers)
local UnitRoster = {
    T1_Basic = {
        'XRA0100', -- Mini Raptor Larva (Small Raider)
        'XRA0101', -- Biological T1 Swarmer
        'XRA0103', -- Suicide Kamikaze Acid Bomb (Acid Tick)
        'XRA0104', -- Biological Acid Carpet Bomber
        'XRA0115', -- Biological T1 Air Swarm Fighter
        'XRA0109', -- Mobile Engineer & Biological Weaver (Healer)
        'XRA0111', -- High-Speed Biological Air Scout
    },
    T2_Special = {
        'XRA0201', -- Biological T2 All-Terrain Heavy Crawler
        'XRA0202', -- Mobile Bio-Artillery
        'XRA0203', -- Bio-EMP Shock Kamikaze & Shield Breaker
        'XRA0204', -- Brood Cluster Bomber (Living Swarm Salvos)
        'XRA0205', -- Hovering Predator Gunship
        'XRA0206', -- All-Terrain Bio-Flamethrower
        'XRA0109', -- Biological Weaver (Healer support)
    },
    T3_Heavy = {
        'XRA0301', -- Armored Heavy Assault Bruiser (Apex Behemoth)
        'XRA0302', -- Psychic Overseer (Omni-Radar & Stealth Jammer)
        'XRA0303', -- Raptor Matriarch (Sub-Boss Commander)
        'XRA0310', -- Behemoth Heavy Acid Dodo (Cratering Bomb)
    },
}

-- Defensive Spires & Stationary Weapon Structures (Spawned only on Creep territory)
local SpireRoster = {
    T1 = {
        'XRA0102', -- Basic Kinetic Spine Spire
        'XRA0106', -- Biological Spore Anti-Air Defense Spire
        'XRA0108', -- Biological Acid Point Defense Spire
        'XRA0110', -- Subterranean Burrowing Ambush Spire
    },
    T2 = {
        'XRA0208', -- Heavy Subterranean Bio-Worm Defense
        'XRA0209', -- Heavy Volcanic Magma Worm Defense
    },
    T3 = {
        'XRA0304', -- Strategic Bio-Nuke Silo
        'XRA0315', -- Strategic Anti-Nuke Interceptor Silo
        'XRA0306', -- Long-Range Biological Artillery (Brood Arty)
        'XRA0307', -- Long-Range EMP Artillery
        'XRA0308', -- Long-Range Acid Artillery
        'XRA0309', -- Extreme-Range Planetary Artillery (Meteor Spire)
    },
}

---Initializes and launches the Raptor Swarm Defense engine
---@param armyIndex number
---@param difficulty string
function StartRaptorDefense(armyIndex, difficulty)
    RaptorArmy = armyIndex
    CurrentDifficulty = difficulty or 'normal'
    local baseConfig = DifficultyParams[CurrentDifficulty] or DifficultyParams['normal']

    -- Read lobby options overrides
    local opts = ScenarioInfo.Options or {}
    local spawnMult = tonumber(opts.RaptorSpawnCountMult) or 1.0
    local queenMult = tonumber(opts.RaptorQueenHatchMult) or 1.0
    local graceMult = tonumber(opts.RaptorGracePeriodMult) or 1.0

    Config = {
        GracePeriod = math.floor(baseConfig.GracePeriod * graceMult),
        QueenTime = math.floor(baseConfig.QueenTime * queenMult),
        WaveInterval = baseConfig.WaveInterval,
        BurrowInterval = baseConfig.BurrowInterval,
        TurretInterval = baseConfig.TurretInterval,
        AngerBonus = baseConfig.AngerBonus,
        SpawnMult = baseConfig.SpawnMult * spawnMult,
    }

    local baseGain = 0.0
    if Config.QueenTime > Config.GracePeriod then
        baseGain = 100.0 / (Config.QueenTime - Config.GracePeriod)
    end

    Sync.RaptorAnger = { Tech = 0, Queen = 0 }
    Sync.RaptorUI = {
        Active = true,
        InGracePeriod = true,
        GraceSeconds = Config.GracePeriod,
        Difficulty = CurrentDifficulty,
        Kills = 0,
        QueenAnger = 0,
        TechAnger = 0,
        BaseAngerGain = baseGain,
        PlayerAggression = 0,
        QueenSpawned = false,
        QueenHealth = 100,
        QueensKilled = 0,
        ActiveBurrows = 1,
    }

    ForkThread(MainPacingLoop)
end

---Called when a Raptor Hive or Spire is destroyed by players
---@param structure Unit
---@param instigator Unit
function OnRaptorStructureKilled(structure, instigator)
    if not instigator or instigator:GetArmy() == RaptorArmy then return end
    local bp = structure:GetBlueprint()
    local cats = bp.CategoriesHash or {}

    if cats['BURROW'] then
        -- Big aggression spike for killing a hive
        PlayerAggression = PlayerAggression + (Config.AngerBonus / Config.SpawnMult)
        ActiveBurrows[structure:GetEntityId()] = nil
        Sync.RaptorAnnounce = { Text = "A Raptor Hive was destroyed! The Swarm enrages!", Color = 'orange' }
    else
        -- Turret / Spire kill adds 10%
        PlayerAggression = PlayerAggression + ((Config.AngerBonus / Config.SpawnMult) * 0.10)
    end
end

---Called when any biological Raptor unit is killed
---@param unit Unit
---@param instigator Unit
function OnRaptorKilled(unit, instigator)
    if not unit then return end
    if instigator and instigator:GetArmy() == RaptorArmy then return end

    RaptorKills = RaptorKills + 1

    local bp = unit:GetBlueprint()
    local cats = bp.CategoriesHash or {}
    if cats['COMMAND'] or (bp.BlueprintId and string.lower(bp.BlueprintId) == 'xra0401') then
        QueensKilled = QueensKilled + 1
        ActiveQueen = nil
        Sync.RaptorAnnounce = { Text = "THE RAPTOR QUEEN TITAN HAS BEEN SLAIN!", Color = 'green' }
    end
end

---The main 1-second simulation pacing thread
function MainPacingLoop()
    local nextWave = Config.GracePeriod
    local nextBurrow = Config.GracePeriod * 0.5
    local nextTurret = Config.GracePeriod + Config.TurretInterval
    local brain = ArmyBrains[RaptorArmy]

    -- Spawn initial seed hives during grace period
    SpawnInitialHives(brain, 3)

    while not GameOver do
        WaitSeconds(1.0)
        local t = GetGameTimeSeconds()
        local burrowCount = table.getsize(ActiveBurrows)

        -- 1. Passive Aggression Decay
        PlayerAggression = PlayerAggression * 0.995

        -- 2. Tech Anger Formula (0 - 999)
        if t >= Config.GracePeriod then
            TechAnger = math.floor(((t - Config.GracePeriod) / (Config.QueenTime - Config.GracePeriod)) * 100)
            TechAnger = math.clamp(TechAnger, 0, 999)

            -- 3. Queen Anger Formula (0 - 100%)
            if not QueenSpawned then
                QueenAnger = math.floor(((t - Config.GracePeriod) / (Config.QueenTime - Config.GracePeriod)) * 100) + math.floor(PlayerAggression)
                QueenAnger = math.clamp(QueenAnger, 0, 100)
            end
        else
            TechAnger = 0
            QueenAnger = 0
        end

        local queenHp = 100
        if ActiveQueen and not ActiveQueen.Dead then
            queenHp = math.floor((ActiveQueen:GetHealth() / ActiveQueen:GetMaxHealth()) * 100)
        end

        local baseGain = 0.0
        if Config.QueenTime > Config.GracePeriod then
            baseGain = 100.0 / (Config.QueenTime - Config.GracePeriod)
        end

        Sync.RaptorAnger = { Tech = TechAnger, Queen = QueenAnger }
        Sync.RaptorUI = {
            Active = true,
            InGracePeriod = (t < Config.GracePeriod),
            GraceSeconds = math.max(0, math.floor(Config.GracePeriod - t)),
            Difficulty = CurrentDifficulty,
            Kills = RaptorKills,
            QueenAnger = QueenAnger,
            TechAnger = TechAnger,
            BaseAngerGain = baseGain,
            PlayerAggression = PlayerAggression,
            QueenSpawned = QueenSpawned,
            QueenHealth = queenHp,
            QueensKilled = QueensKilled,
            ActiveBurrows = burrowCount,
        }
        if not QueenSpawned then
            if QueenAnger >= 100 or (burrowCount <= 0) or (t > Config.GracePeriod and burrowCount <= 1) then
                QueenSpawned = true
                QueenAnger = 100
                SpawnQueenTitan(brain)
            end
        end

        -- 5. Hive Spawning Interval
        if t >= nextBurrow and burrowCount < 12 and not QueenSpawned then
            SpawnBurrow(brain)
            nextBurrow = t + Config.BurrowInterval
        end

        -- 6. Spire Turret Spawning Interval (ONLY on native Creep!)
        if t >= nextTurret and burrowCount > 0 then
            SpawnSpireTurret(brain)
            nextTurret = t + Config.TurretInterval
        end

        -- 7. Wave Spawning Interval
        if t >= nextWave and burrowCount > 0 then
            SpawnWave(brain)
            nextWave = t + Config.WaveInterval
        end
    end
end

---Spawns initial seed hives in the raptor sector
function SpawnInitialHives(brain, count)
    -- 1. Register any existing hives on the field (e.g. converted from start spot)
    local existingHives = brain:GetListOfUnits(categories.BURROW, false)
    if existingHives then
        for _, h in existingHives do
            if h and not h.Dead then
                ActiveBurrows[h:GetEntityId()] = h
                Creep.StartCreepNode(h, 45.0, 0.9)
            end
        end
    end

    -- 2. Spawn seed hives around start spot
    local startPos = GetBrainStartVector(brain)
    for i = 1, count do
        local ox = (i - 2) * 45
        local oz = math.random(-25, 25)
        local hx = startPos[1] + ox
        local hz = startPos[3] + oz
        local hy = GetSurfaceHeight(hx, hz)
        local hive = brain:CreateUnitNearSpot('XRA0107', hx, hz)
        if hive then
            ActiveBurrows[hive:GetEntityId()] = hive
            Creep.StartCreepNode(hive, 42.0, 0.8)
        end
    end
end

---Spawns a new Hive (Burrow) and starts its biological creep expansion
function SpawnBurrow(brain)
    local targetPos = Targeting.GetWeightedRandomEnemyTarget(RaptorArmy)
    local startPos = GetBrainStartVector(brain)
    -- Growing Spawn Box: expand vector from start toward map center as TechAnger grows
    local progress = math.min(1.0, TechAnger * 0.015)
    local bx = startPos[1] + (targetPos[1] - startPos[1]) * progress + math.random(-30, 30)
    local bz = startPos[3] + (targetPos[3] - startPos[3]) * progress + math.random(-30, 30)
    local by = GetSurfaceHeight(bx, bz)

    local hive = brain:CreateUnitNearSpot('XRA0107', bx, bz)
    if hive then
        ActiveBurrows[hive:GetEntityId()] = hive
        Creep.StartCreepNode(hive, 45.0, 0.9)
    end
end

---Spawns a defensive spire (Enforces the Creep Spire Rule: MUST be on Creep)
function SpawnSpireTurret(brain)
    for _, hive in ActiveBurrows do
        if hive and not hive.Dead then
            local pos = hive:GetPosition()
            local sx = pos[1] + math.random(-28, 28)
            local sz = pos[3] + math.random(-28, 28)
            local sy = GetSurfaceHeight(sx, sz)

            -- RULE: Turrets CANNOT spawn outside Creep territory
            if Creep.IsPositionOnCreep(Vector(sx, sy, sz)) then
                local tierList = SpireRoster.T1
                if TechAnger > 60 then
                    tierList = SpireRoster.T3
                elseif TechAnger > 25 then
                    tierList = SpireRoster.T2
                end
                local turretBp = tierList[math.random(1, table.getn(tierList))]
                local turret = brain:CreateUnitNearSpot(turretBp, sx, sz)
                if turret then
                    Creep.StartCreepNode(turret, 20.0, 0.4)
                    break
                end
            end
        end
    end
end

---Spawns an offensive swarm wave from all operational Hives
function SpawnWave(brain)
    local targetPos = Targeting.GetWeightedRandomEnemyTarget(RaptorArmy)
    local waveSize = math.floor((6 + (TechAnger * 0.15)) * Config.SpawnMult)

    -- Pick available unit pool based on TechAnger
    local pool = UnitRoster.T1_Basic
    if TechAnger > 60 then
        -- Late game: heavy assault bruisers, psychic overseers, matriarch sub-bosses, dodos
        pool = {
            'XRA0301', 'XRA0302', 'XRA0303', 'XRA0310',
            'XRA0201', 'XRA0202', 'XRA0204', 'XRA0205', 'XRA0206',
            'XRA0101', 'XRA0103', 'XRA0109'
        }
    elseif TechAnger > 25 then
        -- Mid game: T2 crawlers, mobile artillery, EMP ticks, flamer packs, gunships, bombers
        pool = {
            'XRA0201', 'XRA0202', 'XRA0203', 'XRA0204', 'XRA0205', 'XRA0206',
            'XRA0100', 'XRA0101', 'XRA0103', 'XRA0104', 'XRA0115', 'XRA0109'
        }
    end

    for _, hive in ActiveBurrows do
        if hive and not hive.Dead then
            local pos = hive:GetPosition()
            local spawnedUnits = {}

            for i = 1, waveSize do
                local unitBp = pool[math.random(1, table.getn(pool))]
                local u = brain:CreateUnitNearSpot(unitBp, pos[1] + math.random(-8, 8), pos[3] + math.random(-8, 8))
                if u then
                    -- Apply FAF Master Overhaul stat modification based on Anger
                    Stats.RecomputeRaptorStats(u, TechAnger, QueenAnger, CurrentDifficulty)
                    table.insert(spawnedUnits, u)
                end
            end

            -- Form Platoon and issue pack attack
            if table.getn(spawnedUnits) > 0 then
                local platoon = brain:MakePlatoon('RaptorSwarmWave', '')
                brain:AssignUnitsToPlatoon(platoon, spawnedUnits, 'Attack', 'None')
                PlatoonAI.ManageRaptorSquad(platoon, targetPos)
            end
        end
    end
end

---Awakens the Matriarch Queen Titan (XRA0401)
function SpawnQueenTitan(brain)
    local bestPos = nil
    for _, hive in ActiveBurrows do
        if hive and not hive.Dead then
            bestPos = hive:GetPosition()
            break
        end
    end
    if not bestPos then
        bestPos = GetBrainStartVector(brain)
    end

    Sync.RaptorAnnounce = {
        Text = "CRITICAL WARNING: THE MATRIARCH QUEEN TITAN HAS HATCHED!",
        Color = 'red'
    }

    local queen = brain:CreateUnitNearSpot('XRA0401', bestPos[1], bestPos[3])
    if queen then
        ActiveQueen = queen
        Stats.RecomputeRaptorStats(queen, TechAnger, QueenAnger, CurrentDifficulty)
        -- Order Queen directly into combat
        local target = Targeting.GetWeightedRandomEnemyTarget(RaptorArmy)
        IssueAggressiveMove({queen}, target)
    end
end
