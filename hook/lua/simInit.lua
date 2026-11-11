-- ****************************************************************************
-- **
-- **  File     :  /mods/RaptorFaction/hook/lua/simInit.lua
-- **  Author   :  Raptor Swarm Faction Auto-Start Hook
-- **  Summary  :  Detects Raptor / AI enemy armies and automatically launches
-- **              the Raptor Defense Dual-Anger wave spawner engine.
-- **
-- ****************************************************************************

local OldBeginSession = BeginSession

function BeginSession()
    OldBeginSession()

    ForkThread(function()
        WaitSeconds(1.5)
        local Spawner = import('/mods/RaptorFaction/lua/RaptorSpawner.lua')
        local raptorArmy = nil
        local raptorBrain = nil

        local opts = ScenarioInfo.Options or {}
        local mode = opts.RaptorFactionMode or 'auto'
        local diff = opts.RaptorDifficulty or 'normal'

        if mode == 'disabled' then return end

        -- 1. Scan for custom Raptor AI or army named 'Raptor' or 'Swarm'
        for i, brain in ArmyBrains do
            local per = ScenarioInfo.ArmySetup[brain.Name] and ScenarioInfo.ArmySetup[brain.Name].AIPersonality
            local name = string.lower(brain.Nickname or '')
            if brain.IsRaptorSwarm or (per and string.find(string.lower(per), 'raptor')) or string.find(name, 'raptor') or string.find(name, 'swarm') then
                raptorArmy = i
                raptorBrain = brain
                break
            end
        end

        -- 2. Fallback: If mode is 'enabled' or 'auto', find first enemy AI army
        if not raptorArmy and table.getn(ArmyBrains) >= 2 then
            for i, brain in ArmyBrains do
                if brain.BrainType == 'AI' and not ArmyIsCivilian(i) then
                    raptorArmy = i
                    raptorBrain = brain
                    break
                end
            end
        end

        -- 3. Launch Spawner if Raptor/AI army exists
        if raptorArmy and raptorBrain then
            LOG("* RAPTOR FACTION: Launching Raptor Swarm Defense on Army " .. tostring(raptorArmy) .. " (Difficulty: " .. tostring(diff) .. ")")

            -- 1. Ensure primary hive exists at start spot so army is never Commander-less
            local hives = raptorBrain:GetListOfUnits(categories.BURROW, false)
            local primaryHive = hives and hives[1]
            if not primaryHive or primaryHive.Dead then
                local sx, sz = raptorBrain:GetArmyStartPos()
                local startPos = { sx, GetSurfaceHeight(sx, sz), sz }
                primaryHive = raptorBrain:CreateUnitNearSpot('XRA0107', startPos[1], startPos[3])
            end

            -- 2. Remove generic humanoid ACUs (only non-raptor commanders from standard faction slots)
            local genericAcus = raptorBrain:GetListOfUnits(categories.COMMAND - categories.RAPTOR, false)
            if genericAcus then
                for _, u in genericAcus do
                    if u and not u.Dead then
                        u:Destroy()
                    end
                end
            end

            -- 3. Launch the Raptor Spawner
            Spawner.StartRaptorDefense(raptorArmy, diff)
        end
    end)
end
