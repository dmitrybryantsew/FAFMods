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
local CurrentHivemindName = nil

local HivemindNames = {
    "The Overmind",
    "Cerebrate Daggoth",
    "Cerebrate Zasz",
    "Cerebrate Araq",
    "Cerebrate Nargil",
    "Cerebrate Gorn",
    "Cerebrate Kagg",
    "Hive Mind Grendel",
    "Broodmother Tiamat",
    "Synapse Cluster Primus",
    "Chittering Swarm Nexu",
    "Apex Matriarch Voraz",
    "Hive Fleet Behemoth",
    "Hive Fleet Leviathan",
    "Hive Fleet Kraken",
    "Hive Fleet Gorgon",
    "Hive Fleet Jormungandr",
    "Bio-Nexus Hydra",
    "Devourer Brood",
    "Scourge Hivemind",
    "Anub'Arak Swarm",
    "Khepri Nest Mind",
    "Chitinous Swarm",
    "Primordial Brood",
    "Ravenous Nexus",
    "Swarmlord Kaldir",
    "Matriarch Xir'Kresh",
    "Brood Lord Mor'Gath",
    "Nydus Core Mind",
    "Abyssal Bio-Swarm",
    "Corrosive Swarm",
    "Bio-Titan Dread",
}

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

---Public getters and setters for cross-module coordination
function GetTechAnger()
    return TechAnger
end

function GetQueenAnger()
    return QueenAnger
end

function GetCurrentDifficulty()
    return CurrentDifficulty
end

function SetActiveQueen(queen)
    ActiveQueen = queen
end

function GetActiveQueen()
    return ActiveQueen
end

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
        'XRA0116', -- Subterranean Digger (Burrowing Infiltrator Raider)
    },
    T2_Special = {
        'XRA0201', -- Biological T2 All-Terrain Heavy Crawler
        'XRA0202', -- Mobile Bio-Artillery
        'XRA0203', -- Bio-EMP Shock Kamikaze & Shield Breaker
        'XRA0204', -- Brood Cluster Bomber (Living Swarm Salvos)
        'XRA0205', -- Hovering Predator Gunship
        'XRA0206', -- All-Terrain Bio-Flamethrower
        'XRA0225', -- Bio-Shield Beetle (Mobile Carapace Shield & AA)
        'XRA0227', -- Bio-Zeppelin Blimpy (Living Brood Dodo Bomber)
        'XRA0109', -- Biological Weaver (Healer support)
        'XRA0111', -- High-Speed Biological Air Scout (Recon Vanguard)
    },
    T3_Heavy = {
        'XRA0301', -- Armored Heavy Assault Bruiser (Apex Behemoth)
        'XRA0302', -- Psychic Overseer (Omni-Radar & Stealth Jammer)
        'XRA0303', -- Raptor Matriarch (Sub-Boss Commander)
        'XRA0310', -- Behemoth Heavy Acid Dodo (Cratering Bomb)
        'XRA0328', -- Tiamat Bio-Juggernaut (Heavy Assault Shield Bruiser)
        'XRA0111', -- High-Speed Biological Air Scout (Recon Vanguard)
    },
}

-- Defensive Spires & Stationary Weapon Structures (Spawned only on Creep territory)
local SpireRoster = {
    T1 = {
        'XRA0102', -- Basic Kinetic Spine Spire
        'XRA0106', -- Biological Spore Anti-Air Defense Spire
        'XRA0108', -- Biological Acid Point Defense Spire
        'XRA0110', -- Subterranean Burrowing Ambush Spire
        'XRA0121', -- Chitin Spore Tube (Biological Creep Defense Tube)
    },
    T2 = {
        'XRA0208', -- Heavy Subterranean Bio-Worm Defense
        'XRA0209', -- Heavy Volcanic Magma Worm Defense
        'XRA0226', -- Rafflesia Shield Bloom (Static Bio-Shield Canopy Dome)
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

    local brain = GetArmyBrain(armyIndex)
    local curNick = (brain and brain.Nickname) or ""
    local lowerNick = string.lower(curNick)
    local needsHiveName = (curNick == "")
        or string.find(lowerNick, 'ahn%-')
        or string.find(lowerNick, 'shun%-')
        or string.find(lowerNick, 'zan%-')
        or string.find(lowerNick, 'oum%-')
        or string.find(lowerNick, 'thel%-')
        or string.find(lowerNick, 'seth%-')
        or string.find(lowerNick, 'ai:')
        or string.find(lowerNick, 'player')
        or string.find(lowerNick, 'harms')
        or string.find(lowerNick, 'priscilla')
        or string.find(lowerNick, 'ronald')

    if needsHiveName or not CurrentHivemindName then
        CurrentHivemindName = HivemindNames[math.random(1, table.getn(HivemindNames))]
    end

    if brain then
        brain.Nickname = CurrentHivemindName
        brain.RaptorHivemindName = CurrentHivemindName
    end

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
        RaptorArmy = RaptorArmy,
        HivemindName = CurrentHivemindName,
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
    local nextDiggerAmbush = Config.GracePeriod + 70
    local DragonHeraldSpawned = false
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
            RaptorArmy = RaptorArmy,
            HivemindName = CurrentHivemindName,
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
            CreepCoverage = Creep.GetMapCoveragePercent(),
            InfestedMexes = Creep.GetInfestedMexCount(),
            Biomass = Creep.GetSwarmBiomass(),
        }
        if not QueenSpawned then
            if QueenAnger >= 100 or (burrowCount <= 0) or (t > Config.GracePeriod and burrowCount <= 1) then
                QueenSpawned = true
                QueenAnger = 100
                SpawnQueenTitan(brain)
            end
        end

        -- 4. Herald White Dragon Event (Mid-Boss at 50% Tech or Queen Anger)
        if not DragonHeraldSpawned and (TechAnger >= 50 or QueenAnger >= 50) and burrowCount > 0 then
            DragonHeraldSpawned = true
            SpawnDragonHerald(brain)
        end

        -- 5. Subterranean Digger Infiltration Ambush
        if t >= nextDiggerAmbush and TechAnger >= 15 and burrowCount > 0 then
            local ok, err = pcall(TriggerDiggerAmbush, brain)
            if not ok then
                WARN("* RAPTOR FACTION: Error in TriggerDiggerAmbush: " .. tostring(err))
            end
            local threatProfile = EvaluatePlayerThreatProfile()
            local interval = threatProfile.TurtleThreat and 65 or 95
            nextDiggerAmbush = t + interval
        end

        -- 6. Hive Spawning Interval
        if t >= nextBurrow and burrowCount < 12 and not QueenSpawned then
            local ok, err = pcall(SpawnBurrow, brain)
            if not ok then
                WARN("* RAPTOR FACTION: Error in SpawnBurrow: " .. tostring(err))
            end
            nextBurrow = t + Config.BurrowInterval
        end

        -- 7. Spire Turret Spawning Interval (ONLY on native Creep!)
        if t >= nextTurret and burrowCount > 0 then
            local ok, err = pcall(SpawnSpireTurret, brain)
            if not ok then
                WARN("* RAPTOR FACTION: Error in SpawnSpireTurret: " .. tostring(err))
            end
            nextTurret = t + Config.TurretInterval
        end

        -- 8. Wave Spawning Interval
        if t >= nextWave and burrowCount > 0 then
            local ok, err = pcall(SpawnWave, brain)
            if not ok then
                WARN("* RAPTOR FACTION: Error in SpawnWave: " .. tostring(err))
            end
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
            -- Sprout 2 defensive Chitin Spore Tubes (XRA0121) along hive Creep
            for s = 1, 2 do
                local sAngle = s * math.pi + (math.random() * 0.5)
                local sDist = 18.0 + math.random() * 4.0
                local tx = hx + math.cos(sAngle) * sDist
                local tz = hz + math.sin(sAngle) * sDist
                local ok, tube = pcall(function() return brain:CreateUnitNearSpot('XRA0121', tx, tz) end)
                if ok and tube then
                    Creep.StartCreepNode(tube, 15.0, 0.3)
                end
            end
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
        -- Sprout a defensive Chitin Spore Tube (XRA0121)
        local tx = bx + math.random(-18, 18)
        local tz = bz + math.random(-18, 18)
        local ok, tube = pcall(function() return brain:CreateUnitNearSpot('XRA0121', tx, tz) end)
        if ok and tube then
            Creep.StartCreepNode(tube, 15.0, 0.3)
        end
    end
end

---Evaluates human and enemy player technological profiles to deploy reactive counter-waves
---@return table profile
function EvaluatePlayerThreatProfile()
    local profile = {
        AirThreat = false,
        TurtleThreat = false,
        ExpThreat = false,
    }

    local airCount = 0
    local defenseCount = 0
    local expCount = 0

    if ArmyBrains then
        for armyIndex, b in ArmyBrains do
            if b and not b:IsDefeated() and (not RaptorArmy or armyIndex ~= RaptorArmy) then
                local armyName = b.Name or ''
                if armyName ~= 'NEUTRAL_CIVILIAN' and armyName ~= 'CIVILIAN' and armyName ~= 'Raptor' then
                    local airUnits = b:GetListOfUnits(categories.AIR * categories.MOBILE, false)
                    if airUnits then airCount = airCount + table.getn(airUnits) end

                    local defUnits = b:GetListOfUnits(categories.STRUCTURE * (categories.DEFENSE + categories.SHIELD) - categories.TECH1, false)
                    if defUnits then defenseCount = defenseCount + table.getn(defUnits) end

                    local expUnits = b:GetListOfUnits(categories.EXPERIMENTAL, false)
                    if expUnits then expCount = expCount + table.getn(expUnits) end
                end
            end
        end
    end

    if airCount >= 20 then profile.AirThreat = true end
    if defenseCount >= 15 then profile.TurtleThreat = true end
    if expCount >= 1 then profile.ExpThreat = true end

    return profile
end

---Automates strategic bio-nuke silo targeting using high-threat base clusters
---@param siloUnit Unit
---@param brain AIBrain
function StartBioNukeThread(siloUnit, brain)
    siloUnit:ForkThread(function()
        while siloUnit and not siloUnit.Dead do
            -- Wait until missile is loaded
            while siloUnit:GetNukeSiloAmmoCount() < 1 do
                WaitSeconds(15)
                if not siloUnit or siloUnit.Dead then return end
            end

            local targetPos = Targeting.GetWeightedEnemyTarget(siloUnit:GetArmy(), siloUnit:GetPosition())
            if targetPos then
                IssueNuke({siloUnit}, targetPos)
                WaitSeconds(20)
                IssueClearCommands({siloUnit})
            end
            WaitSeconds(30)
        end
    end)
end

---Spawns a defensive spire (Enforces the Creep Spire Rule: MUST be on Creep)
---Prioritizes shielding high-value structures (Hives, Silos, Artillery) with Rafflesia Shield Blooms
function SpawnSpireTurret(brain)
    local threatProfile = EvaluatePlayerThreatProfile()

    -- 1. VALUABLE STRUCTURE SHIELD PROTECTION (Rafflesia Bio-Shield Bloom)
    -- Ensure every Hive, Bio-Nuke Silo, and Artillery Spire is covered by a static shield dome
    if TechAnger >= 25 then
        local valuableCats = categories.BURROW + (categories.STRUCTURE * (categories.SILO + (categories.STRATEGIC * categories.ARTILLERY)))
        local valuableStructures = brain:GetListOfUnits(valuableCats, false)
        if valuableStructures then
            for _, struct in valuableStructures do
                if struct and not struct.Dead then
                    local sPos = struct:GetPosition()
                    local shieldsNearby = brain:GetUnitsAroundPoint(categories.SHIELD * categories.STRUCTURE, sPos, 24.0, 'Ally')
                    if not shieldsNearby or table.empty(shieldsNearby) then
                        local angle = math.random() * 2 * math.pi
                        local dist = 12.0
                        local rx = sPos[1] + math.cos(angle) * dist
                        local rz = sPos[3] + math.sin(angle) * dist
                        local ry = GetSurfaceHeight(rx, rz)
                        if Creep.IsPositionOnCreep(Vector(rx, ry, rz)) then
                            local shieldBloom = brain:CreateUnitNearSpot('XRA0226', rx, rz)
                            if shieldBloom then
                                Creep.StartCreepNode(shieldBloom, 25.0, 0.5)
                                return -- Successfully deployed shield coverage
                            end
                        end
                    end
                end
            end
        end
    end

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

                local turretBp
                -- Awaken Anti-Air Defense Spires on Creep if player has massed air
                if threatProfile.AirThreat and math.random() > 0.4 then
                    turretBp = 'XRA0106' -- Spore AA Defense Spire
                else
                    turretBp = tierList[math.random(1, table.getn(tierList))]
                end

                local turret = brain:CreateUnitNearSpot(turretBp, sx, sz)
                if turret then
                    Creep.StartCreepNode(turret, 20.0, 0.4)
                    -- If Strategic Bio-Nuke Silo, automate cluster devastation targeting
                    if turretBp == 'XRA0304' then
                        StartBioNukeThread(turret, brain)
                    end
                    break
                end
            end
        end
    end
end

---Spawns an offensive swarm wave from all operational Hives
function SpawnWave(brain)
    local coverage = Creep.GetMapCoveragePercent()
    local territoryMult = 1.0 + (coverage * 0.008) -- Up to +40% wave size at 50% map coverage
    local waveSize = math.floor((6 + (TechAnger * 0.15)) * Config.SpawnMult * territoryMult)

    -- Siphon digested biomass into bonus wave units
    if Creep.ConsumeBiomass(300) then
        waveSize = waveSize + 2
    end
    if Creep.ConsumeBiomass(600) then
        waveSize = waveSize + 2
    end

    -- Pick available unit pool based on TechAnger
    local basePool = UnitRoster.T1_Basic
    if TechAnger > 60 then
        -- Late game: heavy assault bruisers, psychic overseers, matriarch sub-bosses, dodos
        basePool = {
            'XRA0301', 'XRA0302', 'XRA0303', 'XRA0310',
            'XRA0201', 'XRA0202', 'XRA0204', 'XRA0205', 'XRA0206',
            'XRA0101', 'XRA0103', 'XRA0111', 'XRA0109'
        }
    elseif TechAnger > 25 then
        -- Mid game: T2 crawlers, mobile artillery, EMP ticks, flamer packs, gunships, bombers
        basePool = {
            'XRA0201', 'XRA0202', 'XRA0203', 'XRA0204', 'XRA0205', 'XRA0206',
            'XRA0100', 'XRA0101', 'XRA0103', 'XRA0104', 'XRA0111', 'XRA0115', 'XRA0109'
        }
    end

    -- Clone base pool and dynamically inject hard-counter compositions
    local currentPool = {}
    for _, bp in basePool do
        table.insert(currentPool, bp)
    end

    local threatProfile = EvaluatePlayerThreatProfile()

    -- 1. Anti-Turtle Trigger (Heavy Static Defense & Shields)
    if threatProfile.TurtleThreat then
        table.insert(currentPool, 'XRA0202') -- Mobile Bio-Artillery
        table.insert(currentPool, 'XRA0203') -- Bio-EMP Shock Kamikaze / Shield Breaker
        table.insert(currentPool, 'XRA0204') -- Brood Cluster Bomber
    end

    -- 2. Anti-Air Dominance Trigger (Player Air Superiority)
    if threatProfile.AirThreat then
        table.insert(currentPool, 'XRA0115') -- Spore Anti-Air Fighter
        table.insert(currentPool, 'XRA0115')
    end

    -- 3. Anti-Experimental Hunter Trigger (Player Experimentals)
    if threatProfile.ExpThreat then
        table.insert(currentPool, 'XRA0301') -- Heavy Assault Bruiser / Behemoth
        table.insert(currentPool, 'XRA0303') -- Raptor Matriarch Sub-Boss
    end

    for _, hive in ActiveBurrows do
        if hive and not hive.Dead then
            local pos = hive:GetPosition()
            -- Distance-discounted and threat-aware target selection relative to this hive
            local targetPos = Targeting.GetWeightedEnemyTarget(RaptorArmy, pos)
            local spawnedUnits = {}

            for i = 1, waveSize do
                local unitBp = currentPool[math.random(1, table.getn(currentPool))]
                local u = brain:CreateUnitNearSpot(unitBp, pos[1] + math.random(-8, 8), pos[3] + math.random(-8, 8))
                if u then
                    -- Apply FAF Master Overhaul stat modification based on Anger
                    Stats.RecomputeRaptorStats(u, TechAnger, QueenAnger, CurrentDifficulty)
                    table.insert(spawnedUnits, u)
                end
            end

            -- Separate land and air units, and segregate high-speed air scouts (XRA0111)
            local landUnits = {}
            local combatAirUnits = {}
            local scoutUnits = {}
            for _, u in spawnedUnits do
                if u and not u.Dead then
                    if EntityCategoryContains(categories.SCOUT * categories.AIR, u) then
                        table.insert(scoutUnits, u)
                    elseif EntityCategoryContains(categories.AIR, u) then
                        table.insert(combatAirUnits, u)
                    else
                        table.insert(landUnits, u)
                    end
                end
            end

            -- Guarantee formation escort protection:
            -- Mobile Shield Beetles (XRA0225) protect land formations from incoming artillery/point defense
            if TechAnger >= 20 and table.getn(landUnits) >= 3 then
                local shieldBeetle = brain:CreateUnitNearSpot('XRA0225', pos[1] + math.random(-4, 4), pos[3] + math.random(-4, 4))
                if shieldBeetle then
                    Stats.RecomputeRaptorStats(shieldBeetle, TechAnger, QueenAnger, CurrentDifficulty)
                    shieldBeetle:EnableShield()
                    table.insert(landUnits, shieldBeetle)
                end
            end

            -- Heavy Assault Juggernauts (XRA0328 Tiamat) spearhead late-game land waves
            if TechAnger >= 60 and table.getn(landUnits) >= 4 and math.random() > 0.4 then
                local tiamat = brain:CreateUnitNearSpot('XRA0328', pos[1] + math.random(-5, 5), pos[3] + math.random(-5, 5))
                if tiamat then
                    Stats.RecomputeRaptorStats(tiamat, TechAnger, QueenAnger, CurrentDifficulty)
                    tiamat:EnableShield()
                    table.insert(landUnits, tiamat)
                end
            end

            -- Bio-Zeppelin Blimpy (XRA0227) drops living kamikaze dodo bombs in air assault waves
            if TechAnger >= 25 and (table.getn(combatAirUnits) > 0 or math.random() > 0.5) then
                local blimpy = brain:CreateUnitNearSpot('XRA0227', pos[1] + math.random(-6, 6), pos[3] + math.random(-6, 6))
                if blimpy then
                    Stats.RecomputeRaptorStats(blimpy, TechAnger, QueenAnger, CurrentDifficulty)
                    table.insert(combatAirUnits, blimpy)
                end
            end

            -- High-Speed Recon Vanguard (XRA0111 Bio-Recon Scout):
            -- Flies ahead of bombers and strike waves to illuminate enemy targets & defenses
            local hasBombers = false
            for _, u in combatAirUnits do
                if EntityCategoryContains(categories.BOMBER, u) then
                    hasBombers = true
                    break
                end
            end

            if (hasBombers or table.getn(combatAirUnits) >= 2 or (table.getn(landUnits) >= 4 and math.random() > 0.4)) and table.getn(scoutUnits) == 0 then
                local scoutCount = hasBombers and 2 or 1
                for s = 1, scoutCount do
                    local scout = brain:CreateUnitNearSpot('XRA0111', pos[1] + math.random(-5, 5), pos[3] + math.random(-5, 5))
                    if scout then
                        Stats.RecomputeRaptorStats(scout, TechAnger, QueenAnger, CurrentDifficulty)
                        table.insert(scoutUnits, scout)
                    end
                end
            end

            -- Separate land units into Fast Raider Wolfpacks vs Heavy Siege/Support Squads
            local raiderUnits = {}
            local siegeUnits = {}
            for _, u in landUnits do
                local bp = u:GetBlueprint()
                local bId = string.upper(bp.BlueprintId or '')
                -- Check if siege/heavy/artillery/support
                local isSiege = (bId == 'XRA0202' or -- Mobile Bio-Artillery
                   bId == 'XRA0301' or -- Armored Heavy Assault Behemoth
                   bId == 'XRA0303' or -- Matriarch Sub-Boss
                   bId == 'XRA0109' or -- Weaver Healer
                   bId == 'XRA0225' or -- Mobile Shield Beetle
                   bId == 'XRA0328' or -- Tiamat Juggernaut
                   bId == 'XRA0310')   -- Acid Dodo
                if not isSiege then
                    if categories.ARTILLERY and EntityCategoryContains(categories.ARTILLERY, u) then
                        isSiege = true
                    elseif categories.EXPERIMENTAL and EntityCategoryContains(categories.EXPERIMENTAL, u) then
                        isSiege = true
                    elseif categories.SHIELD and EntityCategoryContains(categories.SHIELD, u) then
                        isSiege = true
                    end
                end
                if isSiege then
                    table.insert(siegeUnits, u)
                else
                    table.insert(raiderUnits, u)
                end
            end

            local flankModes = {'center', 'center', 'left', 'right'}
            local chosenMode = flankModes[math.random(1, 4)]

            -- 1. Fast Raider Wolfpack: Runs in 'NoFormation' to unlock 100% native physics speed.
            -- Stalks at enemy-weapon-range + respectable buffer, and executes 360-degree overwhelm charge!
            if table.getn(raiderUnits) > 0 then
                local raiderPlatoon = brain:MakePlatoon('RaptorRaiderWolfpack', '')
                brain:AssignUnitsToPlatoon(raiderPlatoon, raiderUnits, 'Attack', 'NoFormation')
                PlatoonAI.ManageRaptorWolfpack(raiderPlatoon, targetPos, chosenMode)
            end

            -- 2. Heavy Siege / Support Squad: Advances in coordinated combat line
            if table.getn(siegeUnits) > 0 then
                local siegePlatoon = brain:MakePlatoon('RaptorSiegeWave', '')
                brain:AssignUnitsToPlatoon(siegePlatoon, siegeUnits, 'Attack', 'AttackFormation')
                PlatoonAI.ManageRaptorSquad(siegePlatoon, targetPos, chosenMode)
            end

            -- Form Air Recon Platoon in NoFormation so scouts fly ahead at full top speed (28.0)
            if table.getn(scoutUnits) > 0 then
                local scoutPlatoon = brain:MakePlatoon('RaptorAirScout', '')
                brain:AssignUnitsToPlatoon(scoutPlatoon, scoutUnits, 'Scout', 'NoFormation')
                PlatoonAI.ManageRaptorScoutSquad(scoutPlatoon, targetPos)
            end

            -- Form Air Combat Platoon in GrowthFormation with dedicated aerial combat AI
            if table.getn(combatAirUnits) > 0 then
                local airPlatoon = brain:MakePlatoon('RaptorAirWave', '')
                brain:AssignUnitsToPlatoon(airPlatoon, combatAirUnits, 'Attack', 'GrowthFormation')
                PlatoonAI.ManageRaptorAirSquad(airPlatoon, targetPos)
            end
        end
    end
end

---Triggers a surprise subterranean breach behind player defensive lines
---Spawns cloaked Diggers (XRA0116) that bypass shields/walls to strike rear economy
---@param brain AIBrain
function TriggerDiggerAmbush(brain)
    local targetPos = Targeting.GetWeightedEnemyTarget(RaptorArmy)
    if not targetPos then return end

    -- Offset breach location 18-24 units behind/adjacent to the target
    local angle = math.random() * 2 * math.pi
    local dist = 18.0 + math.random() * 6.0
    local bx = targetPos[1] + math.cos(angle) * dist
    local bz = targetPos[3] + math.sin(angle) * dist
    local by = GetSurfaceHeight(bx, bz)

    Sync.RaptorAnnounce = { Text = "WARNING: Subterranean breach detected! Burrowing Diggers emerging!", Color = 'yellow' }

    local diggerCount = math.min(8, math.floor(3 + (TechAnger * 0.06)))
    local spawnedDiggers = {}
    local army = brain:GetArmyIndex()

    for i = 1, diggerCount do
        local dx = bx + math.random(-4, 4)
        local dz = bz + math.random(-4, 4)
        local u = brain:CreateUnitNearSpot('XRA0116', dx, dz)
        if u then
            Stats.RecomputeRaptorStats(u, TechAnger, QueenAnger, CurrentDifficulty)
            u:EnableUnitIntel('Cloak')
            u:EnableUnitIntel('RadarStealth')
            CreateEmitterAtEntity(u, army, '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp'):ScaleEmitter(1.5)
            CreateEmitterAtEntity(u, army, '/mods/RaptorFaction/effects/emitters/raptor_bio_smoke_01_emit.bp'):ScaleEmitter(1.8)
            table.insert(spawnedDiggers, u)
        end
    end

    if table.getn(spawnedDiggers) > 0 then
        local diggerPlatoon = brain:MakePlatoon('RaptorDiggerAmbush', '')
        brain:AssignUnitsToPlatoon(diggerPlatoon, spawnedDiggers, 'Attack', 'AttackFormation')
        PlatoonAI.ManageDiggerAmbushSquad(diggerPlatoon, targetPos)
    end
end

---Awakens the Apex White Dragon Herald (XRA0329) as a mid-game herald boss
---Accompanied by a royal vanguard of Tiamats and Bio-Shield Beetles
---@param brain AIBrain
function SpawnDragonHerald(brain)
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
        Text = "CRITICAL WARNING: AN APEX WHITE DRAGON HERALD HAS RISEN!",
        Color = 'cyan'
    }

    local dragon = brain:CreateUnitNearSpot('XRA0329', bestPos[1], bestPos[3])
    if dragon then
        Stats.RecomputeRaptorStats(dragon, TechAnger, QueenAnger, CurrentDifficulty)

        local escortUnits = { dragon }

        -- Spawn 2x Tiamat Juggernauts (XRA0328)
        for i = 1, 2 do
            local tiamat = brain:CreateUnitNearSpot('XRA0328', bestPos[1] + math.random(-6, 6), bestPos[3] + math.random(-6, 6))
            if tiamat then
                Stats.RecomputeRaptorStats(tiamat, TechAnger, QueenAnger, CurrentDifficulty)
                tiamat:EnableShield()
                table.insert(escortUnits, tiamat)
            end
        end

        -- Spawn 2x Bio-Shield Beetles (XRA0225) to shield the Herald
        for i = 1, 2 do
            local shield = brain:CreateUnitNearSpot('XRA0225', bestPos[1] + math.random(-8, 8), bestPos[3] + math.random(-8, 8))
            if shield then
                Stats.RecomputeRaptorStats(shield, TechAnger, QueenAnger, CurrentDifficulty)
                shield:EnableShield()
                table.insert(escortUnits, shield)
            end
        end

        local heraldPlatoon = brain:MakePlatoon('RaptorHeraldStrike', '')
        brain:AssignUnitsToPlatoon(heraldPlatoon, escortUnits, 'Attack', 'AttackFormation')

        local target = Targeting.GetWeightedEnemyTarget(RaptorArmy, bestPos)
        PlatoonAI.ManageRaptorSquad(heraldPlatoon, target, 'center')
    end
end

---Awakens Phase 1: Apex Sky Matriarch Queen Titan (XRA0402)
---Her death detonates an apocalyptic Bio-Nuke crater explosion and summons Phase 2: Land Matriarch Titan (XRA0401)
---@param brain AIBrain
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
        Text = "CRITICAL WARNING: THE APEX SKY MATRIARCH QUEEN HAS TAKEN FLIGHT!",
        Color = 'red'
    }

    local skyQueen = brain:CreateUnitNearSpot('XRA0402', bestPos[1], bestPos[3])
    if skyQueen then
        ActiveQueen = skyQueen
        Stats.RecomputeRaptorStats(skyQueen, TechAnger, QueenAnger, CurrentDifficulty)

        -- Order Sky Queen directly into combat targeting highest-value vulnerable threat
        local target = Targeting.GetWeightedEnemyTarget(RaptorArmy, bestPos)
        IssueAggressiveMove({skyQueen}, target)
    end
end

