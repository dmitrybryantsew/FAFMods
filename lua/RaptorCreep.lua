-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/lua/RaptorCreep.lua
-- **  Author   :  Ported from Beyond All Reason (gfx_raptor_scum_gl4.lua) to FAF
-- **  Summary  :  Raptor Creep (Scum) territory management, organic terrain decals,
-- **              speed/regen buffs for Raptors, and enemy corrosive slow.
-- **
-- ****************************************************************************

local Buff = import('/lua/sim/Buff.lua')
local BuffBlueprint = BuffBlueprint
local CreateDecal = CreateDecal
local Damage = Damage

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
local CreepSubAlbedo  = '/mods/RaptorFaction/env/decals/raptor_creep_sub_albedo.dds'
local CreepSubNormals = '/mods/RaptorFaction/env/decals/raptor_creep_sub_normals.dds'

local SporeEmitter    = '/mods/RaptorFaction/effects/emitters/raptor_creep_spores_01_emit.bp'
local BubbleEmitter   = '/mods/RaptorFaction/effects/emitters/raptor_creep_bubbles_01_emit.bp'

-- ---------------------------------------------------------------------------
-- 3. GLOBAL NODE REGISTRY (Port of BAR's GG.IsPosInRaptorScum)
-- ---------------------------------------------------------------------------
local ActiveNodes = {}

function RegisterNode(node)
    ActiveNodes[node] = true
end

function UnregisterNode(node)
    ActiveNodes[node] = nil
end

---Tests whether a 3D position is covered by raptor creep
---@param position Vector [x, y, z]
---@return boolean
function IsPositionOnCreep(position)
    for node in ActiveNodes do
        if node.unit and not node.unit.Dead and node.currentRadius > 0 then
            local dx = position[1] - node.pos[1]
            local dz = position[3] - node.pos[3]
            if (dx * dx + dz * dz) <= (node.currentRadius * node.currentRadius) then
                return true
            end
        end
    end
    return false
end

-- ---------------------------------------------------------------------------
-- 4. CREEP NODE COROUTINE (Spreading, Decals, Buffs, 10x Decay)
-- ---------------------------------------------------------------------------
---Initializes creep spreading from a Raptor structure
---@param unit Unit
---@param maxRadius number Maximum radius of creep spread in game units
---@param growthRate number Growth rate in units per second
function StartCreepNode(unit, maxRadius, growthRate)
    maxRadius = maxRadius or 32
    growthRate = growthRate or 1.0

    local node = {
        unit = unit,
        pos = unit:GetPosition(),
        maxRadius = maxRadius,
        growthRate = growthRate,
        currentRadius = math.min(10, maxRadius * 0.35),
        decals = {},
        subDecals = {},
        heading = math.random() * 6.2831853,
        army = unit.Army,
    }

    RegisterNode(node)

    -- Attach Creep Node to Unit for clean destruction handling
    unit.CreepNode = node

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
    local army = node.army
    local pos = node.pos
    local heading = node.heading
    local maxRadius = node.maxRadius
    local growthRate = node.growthRate

    local function ClearDecals(t)
        for _, d in t do
            if d then
                d:Destroy()
            end
        end
        return {}
    end

    local function SpawnCoreDecals(radius)
        ClearDecals(node.decals)
        local diam = radius * 2
        local dAlb = CreateDecal(pos, heading, CreepAlbedo, '', 'Albedo', diam, diam, 350, 0, army, 0)
        local dNorm = CreateDecal(pos, heading, CreepNormals, '', 'Alpha Normals', diam, diam, 350, 0, army, 0)
        node.decals = { dAlb, dNorm }
    end

    local function SpawnSubDecals(radius)
        ClearDecals(node.subDecals)
        if radius < 18 then return end

        local subDiam = radius * 1.3
        local subList = {}
        -- Spawn 2 overlapping organic lobes rotated at angles for natural irregular creep contour
        for _, ang in { 1.047, 3.141, 5.235 } do
            local offDist = radius * 0.35
            local lx = pos[1] + math.cos(heading + ang) * offDist
            local lz = pos[3] + math.sin(heading + ang) * offDist
            local subPos = { lx, pos[2], lz }
            local dA = CreateDecal(subPos, heading + ang, CreepSubAlbedo, '', 'Albedo', subDiam, subDiam, 320, 0, army, 0)
            local dN = CreateDecal(subPos, heading + ang, CreepSubNormals, '', 'Alpha Normals', subDiam, subDiam, 320, 0, army, 0)
            table.insert(subList, dA)
            table.insert(subList, dN)
        end
        node.subDecals = subList
    end

    -- Initial decal creation
    SpawnCoreDecals(node.currentRadius)

    local dt = 1.2
    local lastSubUpdate = 0

    -- Growth & Buff Pulse Loop
    while unit and not unit.Dead do
        -- Grow Creep Radius
        if node.currentRadius < maxRadius then
            node.currentRadius = math.min(maxRadius, node.currentRadius + growthRate * dt)
            SpawnCoreDecals(node.currentRadius)

            if (node.currentRadius - lastSubUpdate) >= 6.0 and node.currentRadius >= 18 then
                SpawnSubDecals(node.currentRadius)
                lastSubUpdate = node.currentRadius
            end
        end

        -- Creep Aura Pulse (Buffs & Debuffs)
        local brain = unit:GetAIBrain()
        local r = node.currentRadius

        -- 1. Friendly Raptors on Creep: Speed + Regen
        local raptorAllies = brain:GetUnitsAroundPoint(categories.RAPTOR * categories.MOBILE, pos, r, 'Ally')
        if raptorAllies then
            for _, ally in raptorAllies do
                if ally and not ally.Dead then
                    Buff.ApplyBuff(ally, 'RaptorCreepBuff')
                end
            end
        end

        -- 2. Hostile Land Units on Creep: Sludge Slow + Minor Acid Damage
        local enemies = brain:GetUnitsAroundPoint(categories.MOBILE * (categories.LAND + categories.AMPHIBIOUS) - categories.AIR, pos, r, 'Enemy')
        if enemies then
            for _, enemy in enemies do
                if enemy and not enemy.Dead then
                    Buff.ApplyBuff(enemy, 'RaptorCreepDebuff')
                    Damage(unit, enemy:GetPosition(), enemy, 6, 'Normal')
                end
            end
        end

        WaitSeconds(dt)
    end

    -- -----------------------------------------------------------------------
    -- RAPID 10x DECAY ON DEATH (Exact BAR Scum Decay Logic)
    -- -----------------------------------------------------------------------
    -- Destroy ambient emitters immediately upon structure death
    if node.ambientEmitters then
        for _, emit in node.ambientEmitters do
            if emit then
                emit:Destroy()
            end
        end
        node.ambientEmitters = nil
    end

    local decayRate = growthRate * 10.0
    local shrinkDt = 0.4

    ClearDecals(node.subDecals)
    node.subDecals = {}

    while node.currentRadius > 0 do
        node.currentRadius = node.currentRadius - (decayRate * shrinkDt)
        if node.currentRadius <= 2.0 then
            break
        end
        SpawnCoreDecals(node.currentRadius)
        WaitSeconds(shrinkDt)
    end

    ClearDecals(node.decals)
    node.decals = {}
    node.currentRadius = 0
    UnregisterNode(node)
end
