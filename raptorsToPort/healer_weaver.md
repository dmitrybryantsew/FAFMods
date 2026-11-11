# Porting Guide: Biological Weaver (Healer / Engineer / Reclaimer)

## 1. Required Context & Unit Identity
* **Role**: Tech 1 / Tech 2 Biological Weaver (Mobile Engineer & Field Healer)
* **Design Concept**: A spindly, multi-legged weaver insect that secretes biological resin, silk, and restorative enzymes. It functions as the mobile builder/worker of the Raptor faction: reclaiming battlefield carcasses into organic biomass, repairing and regenerating damaged swarmers, and gestating defense spires and hive structures.
* **Suggested Unit ID**: `XRA0109` (T1 Biological Weaver / Engineer)

### BAR Source Files
* **Unit Definition**: `units/other/raptors/healer/raptor_land_swarmer_heal_t1_v1.lua` / `units/other/raptors/healer/raptorh1b.lua`
* **3D Models**:
  * Primary: `objects3d/raptors/raptorhealer1.s3o` (4-legged delicate weaver with glowing restorative glands)
  * Secondary: `objects3d/raptors/raptorhealer2.s3o`
* **Textures**:
  * Diffuse: `unittextures/raptors/raptorhealer1.dds` (pale bioluminescent teal-amber chitin)
  * Normal / Specular: Synthesized tangent-space normal map + specular mask.
* **Audio**:
  * Weaving / Healing: `sounds/raptors/smallraptorhiss.wav` or `talonattack.wav` (soft organic chittering)
  * Death Screech: `sounds/raptors/smallraptordead.wav`

### Recommended FAF Game Stats
* **Health**: 260 HP
* **Cost**: Mass: 60, Energy: 280, Build Time: 280
* **Speed**: 3.8
* **Build Rate**: 8 (T1 standard engineer capability)
* **Reclaim Speed**: 25 Mass/s, 250 Energy/s
* **Motion Type**: `RULEUMT_Amphibious`
* **Abilities**:
  * Engineering: Can build biological defense structures, hives, and repair friendly units.
  * Passive Healing Aura: Generates +6 HP/s regeneration to all friendly biological units within a 14m radius.

---

## 2. Step-by-Step Porting Instructions

### Step 1: Model Extraction & Rigging
1. Extract `objects3d/raptors/raptorhealer1.s3o`.
2. Convert to `.scm` via `convert_s3o_to_scm.py`:
   * Bone Tree:
     * `root` (Bone 0, parent: -1)
     * `body` (Bone 1)
     * `head` (Bone 2)
     * `spinneret` / `weaver_arm` (Biological build arm, parent: head)
     * `nozzle` (Build stream emitter bone, parent: weaver_arm)
     * Legs: `lleg1`, `rleg1`, `lleg2`, `rleg2`
   * Export to `/mods/RaptorFaction/units/XRA0109/XRA0109_lod0.scm`.

### Step 2: Animations (.sca)
1. **Walk Cycle (`XRA0109_Awalk.sca`)**:
   * Nimble 24-frame skittering stride.
   * Frame 0 Root bone must be centered: `px=0, py=0, pz=0, qw=1, qx=0, qy=0, qz=0`.
2. **Weaving / Construction (`XRA0109_Abuild.sca`)**:
   * Rhythmic weaving motion of the spinneret appendages.
3. **Death Animation (`XRA0109_Adeath01.sca`)**:
   * Delicate collapse with fluid burst.

### Step 3: Construction & Regeneration in Blueprint (`XRA0109_unit.bp`)
* Key categories and capabilities:
  ```lua
  Categories = {
      'PRODUCTSC1', 'SELECTABLE', 'BUILTBYTIER1FACTORY', 'BUILTBYTIER2FACTORY',
      'CYBRAN', 'RAPTOR', 'MOBILE', 'LAND', 'TECH1', 'CONSTRUCTION', 'ENGINEER',
      'REPAIR', 'RECLAIM', 'CAPTURE', 'VISIBLETORECON', 'PATROLHELPER',
  },
  Economy = {
      BuildCostEnergy = 280,
      BuildCostMass = 60,
      BuildRate = 8,
      BuildTime = 280,
      BuildableCategory = {
          'BUILTBYTIER1ENGINEER RAPTOR',
          'BUILTBYTIER1ENGINEER CYBRAN',
      },
      MaxBuildDistance = 5,
  },
  General = {
      BuildBones = {
          AimBone = 'spinneret',
          BuildEffectBones = { 'nozzle' },
          PitchBone = 'spinneret',
          YawBone = 'head',
      },
      CommandCaps = {
          RULEUCC_Capture = false,
          RULEUCC_Guard = true,
          RULEUCC_Move = true,
          RULEUCC_Patrol = true,
          RULEUCC_Reclaim = true,
          RULEUCC_Repair = true,
          RULEUCC_Stop = true,
      },
      ConstructionBar = true,
  },
  ```

### Step 4: Unit Scripting with Healing Aura (`XRA0109_script.lua`)
```lua
local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

XRA0109 = ClassUnit(CWalkingLandUnit) {
    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
        -- Start passive area regeneration aura
        self:ForkThread(self.HealingAuraThread)
    end,

    HealingAuraThread = function(self)
        while not self.Dead do
            local pos = self:GetPosition()
            local units = GetUnitsInRect(Rect(pos[1]-14, pos[3]-14, pos[1]+14, pos[3]+14))
            if units then
                for _, u in units do
                    if u and not u.Dead and u.Army == self.Army and EntityCategoryContains(categories.RAPTOR, u) then
                        local hp = u:GetHealth()
                        local maxHp = u:GetMaxHealth()
                        if hp < maxHp then
                            u:SetHealth(u, math.min(maxHp, hp + 6))
                        end
                    end
                end
            end
            WaitSeconds(1.0)
        end
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.0)
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        local scale = 1.0 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}
TypeClass = XRA0109
```

---

## 3. Pitfalls & Errors to Avoid

1. **`BuildBones` Configuration**:
   * If `BuildEffectBones` points to a non-existent bone, the engine silently fails to render construction beams and the unit will freeze during construction.
2. **Biomass Reclaim Stream**:
   * Use an organic build beam such as `/effects/emitters/reclaim_spark_01_emit.bp` or `/effects/emitters/build_green_paint_spray_emit.bp` instead of blue robotic welding arcs.
3. **Healing Thread Lifecycle**:
   * The healing loop must check `while not self.Dead do` and rely on `WaitSeconds(1.0)`. Never use tight loops without wait yields, or simulation ticks will stall.
