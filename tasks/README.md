# Raptor Swarm AI Overhaul: Master Task Directory

This directory contains standalone, agent-executable workflow specifications to transform the **Raptor Swarm AI** into an aggressive, fluid, high-performance, and tactical horde AI based on proven patterns from **Operation Blockade** and **M27/M28 AI**.

---

## Task Index & Execution Order

| Task ID | Task File | Primary Objective | Target Files |
| :--- | :--- | :--- | :--- |
| **01** | [`01_platoon_cohesion_and_blobs.md`](./01_platoon_cohesion_and_blobs.md) | Eliminate `platoon:Stop()` rubberbanding, combat freezing, and dense single-point blobs. | `lua/RaptorPlatoonAI.lua` |
| **02** | [`02_domain_separation_air_land.md`](./02_domain_separation_air_land.md) | Separate Air and Land units into independent platoons to prevent speed-mismatch deadlocks. | `lua/RaptorSpawner.lua`, `lua/RaptorPlatoonAI.lua` |
| **03** | [`03_multi_pronged_flanking_routes.md`](./03_multi_pronged_flanking_routes.md) | Implement Blockade-style multi-vector approach corridors (Left, Center, Right) instead of single-file charges. | `lua/RaptorPlatoonAI.lua`, `lua/RaptorSpawner.lua` |
| **04** | [`04_threat_aware_eco_targeting.md`](./04_threat_aware_eco_targeting.md) | Replace blind global target rolls with distance-discounted eco weighting and priority asset sniping. | `lua/RaptorTargeting.lua`, `lua/RaptorPlatoonAI.lua` |
| **05** | [`05_reactive_counter_waves.md`](./05_reactive_counter_waves.md) | Implement Blockade-style dynamic composition counters (Anti-Turtle, Anti-Air, Anti-Experimental). | `lua/RaptorSpawner.lua` |
| **06** | [`06_cluster_devastation_superweapons.md`](./06_cluster_devastation_superweapons.md) | Direct Queen Titan abilities and Bio-Nuke Silos into high-density player base infrastructure clusters. | `lua/QueenBossAI.lua`, `lua/RaptorSpawner.lua` |
| **07** | [`07_trait_conflict_resolution.md`](./07_trait_conflict_resolution.md) | Prevent Skirmish, Coward, and Berserk micro-commands from breaking platoon cohesion and causing stop-loops. | `lua/RaptorBaseUnit.lua`, `lua/RaptorPlatoonAI.lua` |
| **08** | [`08_wolfpack_stalk_and_swarm.md`](./08_wolfpack_stalk_and_swarm.md) | Wolfpack Raider AI: Unthrottled `NoFormation` sprint, weapon-range + respectable standoff stalking, and 360-degree overwhelm. | `lua/RaptorPlatoonAI.lua`, `lua/RaptorSpawner.lua` |

---

## Reference Locations

1. **Raptor Mod Source Code:**
   - Platoon Engine: `e:/Games/FAFMods/lua/RaptorPlatoonAI.lua`
   - Spawner Engine: `e:/Games/FAFMods/lua/RaptorSpawner.lua`
   - Scent & Target Engine: `e:/Games/FAFMods/lua/RaptorTargeting.lua`
   - Base Unit & Traits: `e:/Games/FAFMods/lua/RaptorBaseUnit.lua`
   - Queen Boss AI: `e:/Games/FAFMods/lua/QueenBossAI.lua`

2. **Operation Blockade Reference (Assault AI Patterns):**
   - Custom Functions: `C:/Users/User/Documents/My Games/Gas Powered Games/Supreme Commander Forged Alliance/maps/FAF_Coop_Operation_Blockade.v0004/FAF_Coop_Operation_Blockade_CustomFunctions.lua`
   - Threat & Platoon Attack Logic: Lines 315–475, 929–1035, 1053–1079
   - Scenario Script & Counter-Waves: `FAF_Coop_Operation_Blockade_script.lua` Lines 540–640

3. **M27/M28 Architectural Report (Engine Performance & Zero-Lag Micro):**
   - Report: `C:/Users/User/.gemini/antigravity/brain/1e227724-c194-4dc3-80bb-96beed25f3fe/M27_M28_AI_ARCHITECTURAL_REPORT.md`
