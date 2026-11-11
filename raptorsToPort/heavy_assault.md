# Porting Guide: Heavy Assault Bruiser (T3/T4 Behemoth & Apex Raptor)

## 1. Required Context & Unit Identity
* **Role**: Tech 3 Heavy Armored Assault Brawler (Apex Raptor Behemoth)
* **Design Concept**: A towering, hulking predatory dinosaur-insect hybrid. Covered in thick overlapping chitinous armor plates, equipped with dual heavy crushing scythe forelegs and an active dorsal bio-spore pod to ward off aerial gunships and light swarmers.
* **Suggested Unit ID**: `XRA0301` (T3 Heavy Assault Raptor)

### BAR Source Files
* **Unit Definition**: `units/other/raptors/assault/raptor_land_assault_basic_t2_v1.lua` / `units/other/raptors/assault/advanced/raptor_land_assault_basic_t4_v1.lua`
* **3D Models**:
  * Primary: `objects3d/raptors/raptora2.s3o` (Advanced 2-legged apex land assault raptor with quad scythes)
  * Secondary: `objects3d/raptors/raptora.s3o` (T2 bipedal assault raptor)
* **Textures**:
  * Diffuse: `unittextures/chicken_redc_l_color.dds` (dark obsidian-crimson carapace)
  * Normal / Specular: Synthesized tangent-space normal map + specular mask.
* **Audio**:
  * Primary Cleave: `sounds/raptors/smallraptorattack.wav` (heavy pitched down by -400 cents) or `bigraptorbreath.wav`
  * Defensive Spores: `sounds/raptors/spore_xl.wav`
  * Death Screech: `sounds/raptors/bigraptordead.wav` or `talondie.wav`

### Recommended FAF Game Stats
* **Health**: 5,400 HP (Heavy frontline tank)
* **Cost**: Mass: 920, Energy: 7,500, Build Time: 3,200
* **Speed**: 3.2 (Heavy bounding stride)
* **Motion Type**: `RULEUMT_Amphibious`
* **Weapons**:
  1. **Primary: Heavy Razor Scythes**:
     * `DisplayName`: Heavy Scythe Cleave
     * `Damage`: 350
     * `DamageRadius`: 1.2 (Cleave splash)
     * `RateOfFire`: 1.5 (Fast, aggressive slashing)
     * `MaxRadius`: 18
     * `BallisticArc`: `RULEUBA_LowArc`
  2. **Secondary: Anti-Air Bio-Spores (`DefensiveSpores`)**:
     * `DisplayName`: Bio-Aerial Spore Launcher
     * `Damage`: 45
     * `RateOfFire`: 2.0
     * `MaxRadius`: 32
     * `TargetLayerCaps`: `Air` (Protects the Behemoth from gunships)

---

## 2. Step-by-Step Porting Instructions

### Step 1: Model Extraction & Rigging
1. Extract `objects3d/raptors/raptora2.s3o`.
2. Convert to `.scm` via `convert_s3o_to_scm.py`:
   * Key bones:
     * `base` (Bone 0, parent: -1)
     * `body` (Bone 1, parent: 0)
     * `aimy1` (Bone 2, parent: 1)
     * `head` (Bone 3, parent: 2)
     * `lforearmu`, `lbladeu`, `rforearmu`, `rbladeu`
     * `lforearml`, `lbladel`, `rforearml`, `rbladel`
     * `headfirepoint`
     * `lthigh`, `lknee`, `lshin`, `lfoot`
     * `rthigh`, `rknee`, `rshin`, `rfoot`
     * `tail`
   * Export to `/mods/RaptorFaction/units/XRA0301/XRA0301_lod0.scm`.

### Step 2: Animations (.sca)
1. **Walk Cycle (`XRA0301_Awalk.sca`)**:
   * Heavy 24-frame stomping gait with screen shake and dynamic arm balance.
   * Root bone frame 0 must be centered: `px=0, py=0, pz=0, qw=1, qx=0, qy=0, qz=0`.
2. **Double Cleave Attack (`XRA0301_Aattack.sca`)**:
   * High-intensity overhead strike followed by a sweep.
3. **Death Animation (`XRA0301_Adeath01.sca`)**:
   * Heavy collapse forward, smashing the terrain and releasing a massive blood burst.

### Step 3: Dual Weapon Implementation in Blueprint (`XRA0301_unit.bp`)
* Include both primary melee cleave and secondary anti-air bio-missiles:
  ```lua
  Weapon = {
      {
          DisplayName = 'Heavy Scythe Cleave',
          Audio = {
              Fire = Sound {
                  Bank = 'Raptor_Heavy_Attack',
                  Cue = 'Attack',
                  LodCutoff = 'Weapon_LodCutoff',
              },
          },
          Damage = 350,
          DamageRadius = 1.2,
          MaxRadius = 18,
          RateOfFire = 1.5,
          Turreted = true,
      },
      {
          DisplayName = 'Defensive Bio-Spores',
          Audio = {
              Fire = Sound {
                  Bank = 'Raptor_Spores',
                  Cue = 'Attack',
                  LodCutoff = 'Weapon_LodCutoff',
              },
          },
          CannotAttackGround = true,
          Damage = 45,
          FireTargetLayerCapsTable = {
              Land = 'Air',
              Water = 'Air',
          },
          MaxRadius = 32,
          ProjectileId = '/mods/RaptorFaction/projectiles/XRA_Spore01/XRA_Spore01_proj.bp',
          RateOfFire = 2.0,
      },
  },
  ```

### Step 4: Unit Scripting (`XRA0301_script.lua`)
```lua
local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class HeavyCleaveWeapon : DefaultProjectileWeapon
local HeavyCleaveWeapon = ClassWeapon(DefaultProjectileWeapon) {
    CreateProjectileAtMuzzle = function(self, muzzle)
        local proj = DefaultProjectileWeapon.CreateProjectileAtMuzzle(self, muzzle)
        self.unit:PlayCleaveMotion()
        return proj
    end,
}

---@class DefensiveSporeWeapon : DefaultProjectileWeapon
local DefensiveSporeWeapon = ClassWeapon(DefaultProjectileWeapon) {}

XRA0301 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Scythes = ClassWeapon(HeavyCleaveWeapon) {},
        DefensiveSpores = ClassWeapon(DefensiveSporeWeapon) {},
    },

    PlayCleaveMotion = function(self)
        -- Dual scythe slash rotators
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.0)
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        local scale = 2.2 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}
TypeClass = XRA0301
```

### Step 5: Sound Banks & FCS16 Checksums
* Generate `Raptor_Heavy_Attack.xsb` / `.xwb` and `Raptor_Spores.xsb` / `.xwb`.
* Set `sb[229] = 0` to prevent infinite looping.
* Recompute CRC-16 checksum via `calc_xact_crc(sb[18:])` and store at offset 8.
* Set all 16 hash buckets at offset 239 to `0x0000`.

---

## 3. Pitfalls & Errors to Avoid

1. **Secondary Weapon Priority Bug**:
   * If `CannotAttackGround = true` is missing on the Spore weapon, the unit might prioritize shooting ground targets with low-damage spores rather than using its devastating primary scythes.
2. **Overkill Gore Scaling**:
   * Because the Apex Raptor has 5,400+ HP, a high-yield death blast (e.g. from a strategic bomber or nuke) can produce overkill ratios > 4. Clamp the gore scale multiplier to a reasonable maximum (e.g. `math.min(scale, 4.5)`) to prevent particle count frame drops.
3. **Collision Box Sizing**:
   * Ensure `SizeX = 1.4`, `SizeY = 1.8`, `SizeZ = 2.0` in the blueprint. A mismatch between physical size and collision volume will cause enemy direct-fire lasers to shoot through empty air or miss the model entirely.
