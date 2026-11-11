# Porting Guide: Biological Hives & Defense Spires (Structures & Spawners)

## 1. Required Context & Unit Identity
* **Role**: Biological Production Hives & Static Defense Spires
* **Design Concept**: Organic, pulsing bio-structures formed from resin, hardened carapace, and living muscle.
  1. **Raptor Hive / Roost (`XRA0107`)**: The organic factory of the swarm. It gestates eggs and births ground swarmers, heavy bruisers, and winged fighters from biomass.
  2. **Bio-Acid Spire (`XRA0108`)**: A writhing defense tower with an elevated corrosive gland that spews rapid-fire acidic spikes at encroaching enemies.
  3. **Burrowing Bio-Worm (`XRA0208`)**: A submerged tentacle pod that remains invisible underground until ground units walk within range, bursting out to crush armor with ringed fangs.

### BAR Source Files
* **Unit Definitions**:
  * Hive: `units/other/raptors/structures/raptor_hive.lua`
  * Turrets: `units/other/raptors/structures/raptor_turret_basic_t2_v1.lua` / `raptor_turret_acid_t2_v1.lua` / `raptor_turret_antiair_t2_v1.lua`
  * Worm: `units/other/raptors/structures/raptor_worm_green.lua`
* **3D Models**:
  * Hive: `objects3d/raptors/raptor_hive.s3o` (massive pulsing egg nest)
  * Spire / Turret: `objects3d/raptors/raptor_turrets_v2.s3o` / `raptor_turretl_v2.s3o`
  * Worm: `objects3d/raptors/raptor_worm_green.s3o` / `raptor_worm_brown.s3o`
* **Textures**:
  * Diffuse: `unittextures/raptors/raptor_hive.dds`, `raptor_turrets_v2.dds`
  * Normal / Specular: Synthesized tangent-space normal map + specular mask.
* **Audio**:
  * Hive Gestation: `sounds/raptors/smallraptorhiss.wav`
  * Spire Attack: `sounds/raptors/smallraptorattack.wav` / `talonattack.wav`
  * Worm Eruption: `sounds/raptors/bigraptorbreath.wav`
  * Structure Collapse: `sounds/raptors/alien_bombrel.wav` / `wet_splat_large.wav`

---

## 2. Step-by-Step Porting Instructions

### Part A: The Raptor Hive (`XRA0107`)

#### Step 1: Model & Bone Hierarchy
1. Extract `objects3d/raptors/raptor_hive.s3o`.
2. Convert to `.scm`:
   * Bones:
     * `root` (Bone 0, parent: -1)
     * `nest_base` (Ground footprint)
     * `egg_sac_center` (Pulsing central gestation bulb)
     * `birth_aperture` (Birth canal / exit point)
     * `Attachpoint` / `Spawnpoint` (Where newly born raptors appear)
   * Export to `/mods/RaptorFaction/units/XRA0107/XRA0107_lod0.scm`.

#### Step 2: Nest Blueprint Setup (`XRA0107_unit.bp`)
* Key categories for biological factory:
  ```lua
  Categories = {
      'PRODUCTSC1', 'SELECTABLE', 'BUILTBYTIER1ENGINEER', 'BUILTBYTIER2ENGINEER',
      'CYBRAN', 'RAPTOR', 'STRUCTURE', 'FACTORY', 'LAND', 'TECH1',
      'CONSTRUCTION', 'SHOWQUEUE', 'VISIBLETORECON', 'RECLAIMABLE',
  },
  Economy = {
      BuildCostEnergy = 2100,
      BuildCostMass = 240,
      BuildRate = 20,
      BuildTime = 400,
      BuildableCategory = {
          'BUILTBYTIER1FACTORY RAPTOR MOBILE',
      },
  },
  ```

#### Step 3: Scripting Factory Births (`XRA0107_script.lua`)
```lua
local CStructureUnit = import('/lua/cybranunits.lua').CStructureUnit

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

XRA0107 = ClassUnit(CStructureUnit) {
    OnCreate = function(self)
        CStructureUnit.OnCreate(self)
        -- Pulsing egg sac breathing animation
        self:ForkThread(self.EggBreathingThread)
    end,

    EggBreathingThread = function(self)
        local rot = CreateRotator(self, 'egg_sac_center', 'y', 0, 15, 15)
        while not self.Dead do
            rot:SetGoal(15)
            WaitFor(rot)
            rot:SetGoal(-15)
            WaitFor(rot)
        end
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(3.0)
        end
        CStructureUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(3.5)
        end
    end,
}
TypeClass = XRA0107
```

---

### Part B: The Bio-Acid Defense Spire (`XRA0108`)

#### Step 1: Model & Bone Hierarchy
1. Extract `objects3d/raptors/raptor_turrets_v2.s3o`.
2. Convert to `.scm`:
   * Bones:
     * `root` (Bone 0, parent: -1)
     * `stalk` (Elevated chitinous spine)
     * `turret_head` (Rotating acid gland)
     * `firepoint` (Muzzle)
   * Export to `/mods/RaptorFaction/units/XRA0108/XRA0108_lod0.scm`.

#### Step 2: Defense Blueprint (`XRA0108_unit.bp`)
* Point defense weapon parameters:
  ```lua
  Categories = {
      'PRODUCTSC1', 'SELECTABLE', 'BUILTBYTIER1ENGINEER', 'BUILTBYTIER2ENGINEER',
      'CYBRAN', 'RAPTOR', 'STRUCTURE', 'DEFENSE', 'DIRECTFIRE', 'TECH1',
      'VISIBLETORECON', 'RECLAIMABLE', 'OVERLAYDIRECTFIRE',
  },
  Defense = {
      Health = 1300,
      MaxHealth = 1300,
      RegenRate = 3,
  },
  Weapon = {
      {
          Audio = {
              Fire = Sound {
                  Bank = 'Raptor_Attack',
                  Cue = 'Attack',
                  LodCutoff = 'Weapon_LodCutoff',
              },
          },
          Damage = 50,
          DamageType = 'Normal',
          DisplayName = 'Acid Spire Spine Spitter',
          FireTargetLayerCapsTable = {
              Land = 'Land|Water|Seabed',
              Water = 'Land|Water|Seabed',
          },
          MaxRadius = 26,
          RateOfFire = 2.0, -- 100 DPS point defense
          TurretBoneMuzzle = 'firepoint',
          TurretBonePitch = 'turret_head',
          TurretBoneYaw = 'turret_head',
          TurretPitchRange = 55,
          TurretPitchSpeed = 80,
          TurretYawRange = 180,
          TurretYawSpeed = 90,
          Turreted = true,
      },
  },
  ```

---

## 3. Pitfalls & Errors to Avoid

1. **Factory Exit Orientation**:
   * For the Hive (`XRA0107`), ensure `Physics.RollOffPoints` in the blueprint specifies clean vectors pointing away from the nest mouth. Otherwise, newly born swarmers will spawn colliding with the nest geometry and fail to roll off.
2. **Terrain Flattening**:
   * Set `FlattenSkirt = true` on the Hive and Spire blueprints so the biological structures don't clip through uneven slopes.
3. **SoundBank Checksums**:
   * All sound banks used by structures must have `sb[229] = 0` (no loop) and verified CRC-16 checksums.
