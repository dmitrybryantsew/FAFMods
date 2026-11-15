-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/lua/RaptorCreep.lua
-- **  Author   :  Ported from Beyond All Reason to FAF — Organic Macro-Decal Architecture
-- **  Summary  :  Continuous organic creep carpet, cluster deduplication,
-- **              zero-flicker staged growth, parasitic Mex siphoning,
-- **              wreckage/structure bio-digestion, speed/regen buffs for Raptors.
-- **
-- ****************************************************************************

local Buff = import('/lua/sim/Buff.lua')
local BuffBlueprint = BuffBlueprint
local CreateDecal = CreateDecal
local Damage = Damage
local ScenarioUtils = import('/lua/sim/ScenarioUtilities.lua')

-- ---------------------------------------------------------------------------
-- 1. BUFF DEFINITIONS (Speed & Regeneration on Creep)
-- ---------------------------------------------------------------------------
if not Buffs['RaptorCreepBuff'] then
    BuffBlueprint {
        Name = 'RaptorCreepBuff',
        DisplayName = 'RaptorCreepBuff',
        BuffType = 'RAPTOR_CREEP_BUFF',
        Stacks = 'REPLACE',
        Duration = 2.0,
        Affects = {
            MoveMult = {
                Mult = 1.25, -- +25% Speed on native Creep
            },
            Regen = {
                Add = 20,   -- +20 HP/s biological regeneration
            },
        },
    }
end

if not Buffs['RaptorCreepDebuff'] then
    BuffBlueprint {
        Name = 'RaptorCreepDebuff',
        DisplayName = 'RaptorCreepDebuff',
        BuffType = 'RAPTOR_CREEP_DEBUFF',
        Stacks = 'REPLACE',
        Duration = 2.0,
        Affects = {
            MoveMult = {
                Mult = 0.80, -- -20% Slow in hostile creep sludge
            },
        },
    }
end

-- ---------------------------------------------------------------------------
-- 2. ASSETS & TEXTURES
-- ---------------------------------------------------------------------------
local CreepAlbedo     = '/mods/RaptorFaction/env/decals/raptor_creep_albedo.dds'
local CreepNormals    = '/mods/RaptorFaction/env/decals/raptor_creep_normals.dds'

local SporeEmitter    = '/mods/RaptorFaction/effects/emitters/raptor_creep_spores_01_emit.bp'
local BubbleEmitter   = '/mods/RaptorFaction/effects/emitters/raptor_creep_bubbles_01_emit.bp'

-- ---------------------------------------------------------------------------
-- 3. MACRO-DECAL CLUSTER CONFIGURATION (Continuous Organic Carpet)
-- ---------------------------------------------------------------------------
-- Each macro-decal covers 82m in diameter with an expansive organic starburst.
-- Setting MIN_DECAL_SPACING to 34m guarantees that neighboring macro-decals
-- overlap by 48m (over 50% overlap), seamlessly fusing their solid red cores
-- into an unbroken fleshy carpet with ZERO green grass holes and NO grid lines!
local MACRO_DECAL_MATURE_SIZE = 82.0
local MACRO_DECAL_MID_SIZE    = 60.0
local MACRO_DECAL_SPROUT_SIZE = 42.0

local MIN_DECAL_SPACING       = 34.0
local LOD_CUTOFF_ALBEDO       = 8000 -- Visible across full strategic orbital zoom
local LOD_CUTOFF_NORMAL       = 800  -- Close-up bump normals; culled at distance for GPU perf

-- Active Macro-Decal Registry:
-- entry = {
--     id = number,
--     pos = Vector,
--     heading = number,
--     currentSize = number,
--     currentRadius = number,
--     decals = { dAlb, dNorm },
--     supporters = table<Unit, boolean>,
--     army = number,
-- }
local MacroDecals = {}
local NextDecalId = 1

-- Active Creep Nodes Registry (Hives, Spires, Tubes)
local ActiveNodes = {}

-- Swarm Biomass Economy & Infestation
local SwarmBiomassBank = 0
local InfestedMexes = {}
local CachedMassMarkers = nil

-- ---------------------------------------------------------------------------
-- 4. ZERO-FLICKER DECAL RENDERER (Safe Swap: Create First, Destroy After)
-- ---------------------------------------------------------------------------

---Safely swaps a macro-decal to a new size without an empty-frame gap (Zero-Flicker)
---@param entry table Macro-decal entry
---@param newSize number Diameter of the decal quad in world units
local function SwapDecalSize(entry, newSize)
    if not entry or not entry.pos then return end
    local pos = entry.pos
    local heading = entry.heading or 0
    local army = (entry.army and entry.army >= 0 and entry.army) or 0

    -- Ensure pos is a valid Vector
    local decalPos = Vector(pos[1], pos[2], pos[3])

    -- 1. Create NEW decals FIRST in the DirectX 9 buffer:
    local dAlb = CreateDecal(decalPos, heading, CreepAlbedo, '', 'Albedo', newSize, newSize, LOD_CUTOFF_ALBEDO, 0, army)
    local dNorm = CreateDecal(decalPos, heading, CreepNormals, '', 'Alpha Normals', newSize, newSize, LOD_CUTOFF_NORMAL, 0, army)
    local newDecals = { dAlb, dNorm }

    -- 2. Destroy OLD decals AFTER new ones exist (Zero empty frames -> ZERO FLICKER):
    local oldDecals = entry.decals
    entry.decals = newDecals
    entry.currentSize = newSize
    entry.currentRadius = newSize * 0.45 -- 90% of quad half-width is active creep

    if oldDecals then
        for _, d in oldDecals do
            if d then
                d:Destroy()
            end
        end
    end
end

---Destroys all decals for a macro-decal entry cleanly
---@param entry table
local function DestroyDecalEntry(entry)
    if entry.decals then
        for _, d in entry.decals do
            if d then
                d:Destroy()
            end
        end
        entry.decals = {}
    end
    entry.currentSize = 0
    entry.currentRadius = 0
end

---Smooth 3-stage growth thread for a macro-decal patch
---Reaches full maturity in 25 seconds with only 2 smooth, zero-gap swaps!
---@param arg1 any unit or entry
---@param arg2 table|nil entry if called via unit:ForkThread
local function MacroDecalGrowthThread(arg1, arg2)
    local entry = arg2 or arg1
    if not entry or not entry.pos then return end

    -- Stage 1: Sprout (42m diameter)
    SwapDecalSize(entry, MACRO_DECAL_SPROUT_SIZE)
    WaitSeconds(10.0)

    -- If no living supporters remain, abort
    if not entry.supporters or table.empty(entry.supporters) then return end

    -- Stage 2: Spreading (60m diameter)
    SwapDecalSize(entry, MACRO_DECAL_MID_SIZE)
    WaitSeconds(15.0)

    if not entry.supporters or table.empty(entry.supporters) then return end

    -- Stage 3: Full Mature Carpet (82m diameter)
    SwapDecalSize(entry, MACRO_DECAL_MATURE_SIZE)
end

---Requests a macro-decal for a Raptor structure.
---If an existing macro-decal already covers this location (within MIN_DECAL_SPACING),
---registers the structure as a supporter with ZERO duplicate decals (Zero Z-Fighting).
---Otherwise, spawns a new continuous macro-decal patch!
---@param unit Unit
---@param pos Vector
---@return table entry
local function RequestMacroDecal(unit, pos)
    -- 1. Check if an existing macro-decal already covers this position
    for _, entry in MacroDecals do
        local dx = pos[1] - entry.pos[1]
        local dz = pos[3] - entry.pos[3]
        if (dx * dx + dz * dz) <= (MIN_DECAL_SPACING * MIN_DECAL_SPACING) then
            entry.supporters[unit] = true
            return entry
        end
    end

    -- 2. New territory! Spawn a new macro-decal patch
    local heading = math.random() * 6.2831853
    local army = 0
    if unit and not unit.Dead and unit.GetArmy then
        army = unit:GetArmy() or 0
    end

    local entry = {
        id = NextDecalId,
        pos = Vector(pos[1], pos[2], pos[3]),
        heading = heading,
        currentSize = MACRO_DECAL_SPROUT_SIZE,
        currentRadius = MACRO_DECAL_SPROUT_SIZE * 0.45,
        decals = {},
        supporters = { [unit] = true },
        army = army,
    }
    NextDecalId = NextDecalId + 1
    table.insert(MacroDecals, entry)

    -- Launch smooth staged growth thread
    ForkThread(MacroDecalGrowthThread, entry)
    return entry
end

---Called when a Raptor structure dies to update macro-decal supporter lifecycles
---@param unit Unit
local function ReleaseMacroDecal(unit)
    for i = table.getn(MacroDecals), 1, -1 do
        local entry = MacroDecals[i]
        entry.supporters[unit] = nil

        -- Count remaining living supporters
        local aliveCount = 0
        for sup in entry.supporters do
            if sup and not sup.Dead then
                aliveCount = aliveCount + 1
            else
                entry.supporters[sup] = nil
            end
        end

        -- If ALL structures supporting this patch are dead, smoothly decay and remove
        if aliveCount == 0 then
            table.remove(MacroDecals, i)
            ForkThread(function()
                -- Smooth 2-step contraction on death
                SwapDecalSize(entry, MACRO_DECAL_MID_SIZE)
                WaitSeconds(2.0)
                SwapDecalSize(entry, MACRO_DECAL_SPROUT_SIZE)
                WaitSeconds(2.0)
                DestroyDecalEntry(entry)
            end)
        end
    end
end

-- ---------------------------------------------------------------------------
-- 5. PUBLIC QUERY API
-- ---------------------------------------------------------------------------

---Tests whether a 3D position is covered by active Raptor creep
---@param position Vector [x, y, z]
---@return boolean
function IsPositionOnCreep(position)
    if not position then return false end
    local px = position[1]
    local pz = position[3]

    -- Test against macro-decal active coverage radii
    for _, entry in MacroDecals do
        if entry.currentRadius and entry.currentRadius > 0 then
            local dx = px - entry.pos[1]
            local dz = pz - entry.pos[3]
            if (dx * dx + dz * dz) <= (entry.currentRadius * entry.currentRadius) then
                return true
            end
        end
    end

    -- Fallback check against living active nodes
    for node in ActiveNodes do
        if node.unit and not node.unit.Dead and node.currentRadius > 0 then
            local dx = px - node.pos[1]
            local dz = pz - node.pos[3]
            if (dx * dx + dz * dz) <= (node.currentRadius * node.currentRadius) then
                return true
            end
        end
    end

    return false
end

---Calculates the percentage of the playable map currently covered by Creep
---@return number percentage (0.0 to 100.0)
function GetMapCoveragePercent()
    local mapW = (ScenarioInfo.size and ScenarioInfo.size[1]) or 512
    local mapH = (ScenarioInfo.size and ScenarioInfo.size[2]) or 512
    local totalMapArea = mapW * mapH

    local coveredArea = 0
    for _, entry in MacroDecals do
        if entry.currentRadius and entry.currentRadius > 0 then
            coveredArea = coveredArea + (math.pi * entry.currentRadius * entry.currentRadius * 0.70) -- Discount for overlaps
        end
    end

    local pct = (coveredArea / totalMapArea) * 100.0
    return math.clamp(pct, 0.0, 100.0)
end

---Returns the total accumulated Biomass from digested wreckages and infested Mexes
---@return number
function GetSwarmBiomass()
    return math.floor(SwarmBiomassBank)
end

---Consumes Biomass for wave reinforcements or unit mutations
---@param amount number
---@return boolean success
function ConsumeBiomass(amount)
    if SwarmBiomassBank >= amount then
        SwarmBiomassBank = SwarmBiomassBank - amount
        return true
    end
    return false
end

---Returns the number of currently infested mass deposits
---@return number
function GetInfestedMexCount()
    return table.getsize(InfestedMexes)
end

function RegisterNode(node)
    ActiveNodes[node] = true
end

function UnregisterNode(node)
    ActiveNodes[node] = nil
end

-- ---------------------------------------------------------------------------
-- 6. PARASITIC MEX INFESTATION & HARVESTING
-- ---------------------------------------------------------------------------

local function EnsureMassMarkers()
    if CachedMassMarkers then return CachedMassMarkers end
    CachedMassMarkers = {}
    if ScenarioUtils and ScenarioUtils.GetMarkers then
        local markers = ScenarioUtils.GetMarkers() or {}
        for name, data in markers do
            if data and data.type == 'Mass' and data.position then
                table.insert(CachedMassMarkers, {
                    name = name,
                    pos = data.position,
                })
            end
        end
    end
    return CachedMassMarkers
end

---Ticks all Mass deposits covered by creep, upgrading output from T1 -> T3 over time
---@param dt number Seconds elapsed
local function TickMexInfestation(dt)
    local markers = EnsureMassMarkers()
    local t = GetGameTimeSeconds()

    for _, m in markers do
        local onCreep = IsPositionOnCreep(m.pos)
        local entry = InfestedMexes[m.name]

        if onCreep then
            if not entry then
                entry = {
                    name = m.name,
                    pos = m.pos,
                    startTime = t,
                    tier = 1,
                    output = 2.0, -- T1: +2 Mass/sec
                }
                InfestedMexes[m.name] = entry
            else
                local duration = t - entry.startTime
                if duration >= 300 then
                    entry.tier = 3
                    entry.output = 18.0 -- T3: +18 Mass/sec
                elseif duration >= 120 then
                    entry.tier = 2
                    entry.output = 6.0  -- T2: +6 Mass/sec
                else
                    entry.tier = 1
                    entry.output = 2.0
                end
            end

            -- Accumulate harvested mass directly into Swarm Biomass
            SwarmBiomassBank = SwarmBiomassBank + (entry.output * dt)
        else
            -- Creep was cleared or receded! The parasitic siphon collapses immediately
            if entry then
                InfestedMexes[m.name] = nil
            end
        end
    end
end

-- ---------------------------------------------------------------------------
-- 7. CORROSIVE WRECKAGE & HOSTILE STRUCTURE DIGESTION
-- ---------------------------------------------------------------------------

---Dissolves battlefield wreckages and burns hostile structures caught on creep
---@param node table
---@param unit Unit
---@param dt number
local function DigestSurroundings(node, unit, dt)
    local pos = node.pos
    local r = node.currentRadius
    local brain = unit:GetAIBrain()
    if not brain then return end

    local age = math.max(0, GetGameTimeSeconds() - (node.spawnTime or GetGameTimeSeconds()))
    local ageMult = 1.0 + math.min(1.5, age * 0.003)
    local baseAcidDps = node.baseAcidDps or 8.0
    local totalAcidDmg = math.floor(baseAcidDps * ageMult * dt)

    -- 1. Digest battlefield wreckages (Props) into Biomass
    local minX = pos[1] - r
    local maxX = pos[1] + r
    local minZ = pos[3] - r
    local maxZ = pos[3] + r

    if GetReclaimablesInRect then
        local wrecks = GetReclaimablesInRect(Rect(minX, minZ, maxX, maxZ))
        if wrecks then
            for _, prop in wrecks do
                if prop and not prop:BeenDestroyed() then
                    local pPos = prop.CachePosition or prop:GetPosition()
                    if pPos and IsPositionOnCreep(pPos) then
                        local maxMass = prop.MaxMassReclaim or 0
                        local reclaimLeft = prop.ReclaimLeft or 1.0
                        local currentMass = maxMass * reclaimLeft

                        if currentMass > 0 then
                            local siphoned = math.min(currentMass, 15.0 * dt)
                            SwarmBiomassBank = SwarmBiomassBank + siphoned

                            local newLeft = math.max(0, reclaimLeft - (siphoned / math.max(1, maxMass)))
                            prop.ReclaimLeft = newLeft

                            if prop.AdjustHealth then
                                prop:AdjustHealth(unit, -totalAcidDmg * 2)
                            end

                            if newLeft <= 0.05 or (prop.GetHealth and prop:GetHealth() <= 0) then
                                CreateEmitterAtEntity(prop, node.army, BubbleEmitter):ScaleEmitter(0.7)
                                prop:Destroy()
                            end
                        end
                    end
                end
            end
        end
    end

    -- 2. Hostile Land Units: Slow + Caustic Damage
    local enemies = brain:GetUnitsAroundPoint(categories.MOBILE * (categories.LAND + categories.AMPHIBIOUS) - categories.AIR, pos, r, 'Enemy')
    if enemies then
        for _, enemy in enemies do
            if enemy and not enemy.Dead then
                Buff.ApplyBuff(enemy, 'RaptorCreepDebuff')
                Damage(unit, enemy:GetPosition(), enemy, totalAcidDmg, 'Normal')
            end
        end
    end

    -- 3. Hostile Structures: Caustic Dissolve Damage (Creep burns away enemy bases)
    local hostileStructures = brain:GetUnitsAroundPoint(categories.STRUCTURE - categories.WALL, pos, r, 'Enemy')
    if hostileStructures then
        for _, struct in hostileStructures do
            if struct and not struct.Dead then
                Damage(unit, struct:GetPosition(), struct, totalAcidDmg * 1.5, 'Normal')
            end
        end
    end
end

-- ---------------------------------------------------------------------------
-- 8. CREEP NODE COROUTINE (Spreading, Life, & Supporter Cleanup)
-- ---------------------------------------------------------------------------

---Initializes creep spreading from a Raptor structure
---@param unit Unit
---@param maxRadius number Maximum radius of creep spread in game units
---@param growthRate number Growth rate in units per second
function StartCreepNode(unit, maxRadius, growthRate)
    maxRadius = maxRadius or 36
    growthRate = growthRate or 1.0

    local bp = unit:GetBlueprint()
    local bpid = bp.BlueprintId or ''
    local cats = bp.CategoriesHash or {}
    local baseAcidDps = 8.0

    if cats['BURROW'] or bpid == 'xra0107' then
        baseAcidDps = 16.0
    elseif cats['TECH3'] or cats['STRATEGIC'] then
        baseAcidDps = 24.0
    elseif bpid == 'xra0121' then
        baseAcidDps = 6.0
    end

    local pos = unit:GetPosition()
    local army = -1
    if unit and not unit.Dead and unit.GetArmy then
        army = unit:GetArmy()
    end

    local node = {
        unit = unit,
        pos = pos,
        maxRadius = maxRadius,
        growthRate = growthRate,
        currentRadius = math.min(12, maxRadius * 0.35),
        army = army,
        spawnTime = GetGameTimeSeconds(),
        baseAcidDps = baseAcidDps,
    }

    RegisterNode(node)
    unit.CreepNode = node

    -- Request organic macro-decal coverage for this structure's cluster
    node.macroDecal = RequestMacroDecal(unit, pos)

    -- Ambient Creep Emitters
    node.ambientEmitters = {
        CreateEmitterAtEntity(unit, node.army, SporeEmitter),
        CreateEmitterAtEntity(unit, node.army, BubbleEmitter),
    }
    if unit.Trash then
        for _, emit in node.ambientEmitters do
            if emit then
                unit.Trash:Add(emit)
            end
        end
    end

    -- Launch Creep Life Coroutine
    unit:ForkThread(CreepLifeThread, node)
end

function CreepLifeThread(unit, node)
    local maxRadius = node.maxRadius
    local growthRate = node.growthRate
    local dt = 1.0

    -- Growth & Active Life Loop
    while unit and not unit.Dead do
        -- 1. Grow node biological aura radius
        if node.currentRadius < maxRadius then
            node.currentRadius = math.min(maxRadius, node.currentRadius + (growthRate * dt))
        end

        -- 2. Creep Aura Buff (Friendly Raptors on Creep: Speed + Regen)
        local brain = unit:GetAIBrain()
        if brain then
            local raptorAllies = brain:GetUnitsAroundPoint(categories.RAPTOR * categories.MOBILE, node.pos, node.currentRadius, 'Ally')
            if raptorAllies then
                for _, ally in raptorAllies do
                    if ally and not ally.Dead then
                        Buff.ApplyBuff(ally, 'RaptorCreepBuff')
                    end
                end
            end
        end

        -- 3. Digestion of Wreckages & Hostile Entities
        DigestSurroundings(node, unit, dt)

        -- 4. Tick Parasitic Mex Siphoning
        TickMexInfestation(dt)

        WaitSeconds(dt)
    end

    -- -----------------------------------------------------------------------
    -- CLEANUP ON DEATH
    -- -----------------------------------------------------------------------
    if node.ambientEmitters then
        for _, emit in node.ambientEmitters do
            if emit then
                emit:Destroy()
            end
        end
        node.ambientEmitters = nil
    end

    -- Release macro-decal supporter reference
    ReleaseMacroDecal(unit)

    node.currentRadius = 0
    UnregisterNode(node)
end
