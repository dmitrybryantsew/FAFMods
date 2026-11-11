# Porting Guide: Biological Air Bomber (Acid / Spore Bomber)

## 1. Required Context & Unit Identity
* **Role**: Tech 1 / Tech 2 Biological Bomber (Aerial Goo Bomber)
* **Design Concept**: A heavy winged airborne raptor with an enlarged underbelly carrying clusters of pressurized bio-bombs. It performs high-speed bombing runs over ground formations and defensive structures, releasing salvos of acidic bile payloads that dissolve armor.
* **Suggested Unit ID**: `XRA0104` (T1 Biological Bomber)

### BAR Source Files
* **Unit Definition**: `units/other/raptors/bomber/raptor_air_bomber_basic_t1_v1.lua` / `units/other/raptors/bomber/raptor_air_bomber_basic_t2_v1.lua`
* **3D Models**:
  * Primary: `objects3d/raptors/raptoracidbomber.s3o` or `objects3d/raptors/raptorf1_mini.s3o`
  * Alternative: `objects3d/raptors/raptorebomber1.s3o`
* **Textures**:
  * Diffuse: `unittextures/raptors/raptoracidbomber.dds`
  * Normal / Specular: Synthesized tangent-space normal map + specular mask.
* **Audio**:
  * Bomb Release: `sounds/raptors/alien_bombrel.wav` (organic wet release/plop)
  * Death Screech: `sounds/raptors/talondie.wav`

### Recommended FAF Game Stats
* **Health**: 220 HP
* **Cost**: Mass: 105, Energy: 2,250, Build Time: 700
* **MaxAirspeed**: 11.0 (Deliberate bombing flight)
* **TurnSpeed**: 1.5
* **Motion Type**: `RULEUMT_Air`
* **Weapon (`GooBomb`)**:
  * `DisplayName`: Bio-Acid Cluster Bomb
  * `Damage`: 240
  * `DamageRadius`: 2.5
  * `DamageType`: `Normal`
  * `MuzzleSalvoSize`: 3 (Drops 3 bio-sacks per run)
  * `MuzzleSalvoDelay`: 0.15
  * `RateOfFire`: 0.2 (1 pass every 5 seconds)

---

## 2. Step-by-Step Porting Instructions

### Step 1: Model & Bone Hierarchy
1. Extract `objects3d/raptors/raptoracidbomber.s3o`.
2. Convert to `.scm` via `convert_s3o_to_scm.py`:
   * Bone Tree:
     * `root` (Bone 0, parent: -1)
     * `body` (Bone 1)
     * `head` (Bone 2)
     * `lwing`, `rwing` (Articulated primary wings)
     * `bomb_bay` / `belly` (Ventral bomb release point)
     * `firepoint` (Muzzle bone)
   * Export to `/mods/RaptorFaction/units/XRA0104/XRA0104_lod0.scm`.

### Step 2: Continuous Flapping Animation (`.sca`)
1. **Flight Flap (`XRA0104_Afly.sca`)**:
   * Continuous looping 20-frame flapping cycle (rate = 2.0).
   * Frame 0 Root bone must be centered: `px=0, py=0, pz=0, qw=1, qx=0, qy=0, qz=0`.
2. **Crash Death (`XRA0104_Adeath01.sca`)**:
   * 24-frame death spiral: wings fold and unit tumbles toward the earth.

### Step 3: Projectile Creation (`XRA_BioBomb01`)
* Create `/mods/RaptorFaction/projectiles/XRA_BioBomb01/XRA_BioBomb01_proj.bp`.
* Set `Physics`:
  * `VelocityAlign = true`
  * `Gravity = true`
  * `RealisticOrdinance = true`
  * `InitialSpeed = 0` (falls under gravity with aircraft forward inertia)

### Step 4: Unit Blueprint (`XRA0104_unit.bp`)
* Key parameters for FAF bombers:
  ```lua
  Air = {
      AutoLandTime = 1,
      BankFactor = 2.5,
      BreakOffDistance = 30,
      BreakOffTrigger = 20,
      CanFly = true,
      CombatTurnSpeed = 1.5,
      KMove = 1,
      KTurn = 1,
      LiftFactor = 10,
      MaxAirspeed = 11.0,
      MinAirspeed = 8.0,
      StartTurnDistance = 10,
      TurnSpeed = 1.5,
  },
  ```
* Mandatory crash weapon:
  ```lua
  Weapon = {
      {
          -- Primary Bomb Weapon
          AboveWaterTargetsOnly = true,
          BallisticArc = 'RULEUBA_None',
          BombDropThreshold = 3,
          Damage = 240,
          DamageRadius = 2.5,
          DisplayName = 'Bio-Acid Bomb',
          Label = 'Bomb',
          MaxRadius = 40,
          MuzzleSalvoDelay = 0.15,
          MuzzleSalvoSize = 3,
          NeedToComputeBombDrop = true,
          ProjectileId = '/mods/RaptorFaction/projectiles/XRA_BioBomb01/XRA_BioBomb01_proj.bp',
          RateOfFire = 0.2,
      },
      {
          -- Critical Crash Weapon to avoid engine crash on impact
          Damage = 100,
          DamageRadius = 1.5,
          DisplayName = 'Air Crash',
          Label = 'DeathImpact',
          WeaponCategory = 'Death',
      },
  },
  ```

### Step 5: Unit Scripting (`XRA0104_script.lua`)
```lua
local CAirUnit = import('/lua/cybranunits.lua').CAirUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

XRA0104 = ClassUnit(CAirUnit) {
    OnCreate = function(self)
        CAirUnit.OnCreate(self)
        -- Continuous flapping flight animation
        local flyAnim = CreateAnimator(self)
        flyAnim:PlayAnim('/mods/RaptorFaction/units/XRA0104/XRA0104_Afly.sca', true)
        flyAnim:SetRate(2.0)
        self.FlyAnimManip = flyAnim
        self.Trash:Add(flyAnim)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.1)
        end
        CAirUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        local scale = 1.2 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}
TypeClass = XRA0104
```

---

## 3. Pitfalls & Errors to Avoid

1. **Missing `DeathImpact` Weapon**:
   * If a flying unit lacks a `DeathImpact` weapon, the engine logs severe warnings or crashes when the dying aircraft collides with the ground.
2. **Missing `NeedToComputeBombDrop`**:
   * Must be set to `true` on the bomb weapon; otherwise, the bomber will not calculate bomb lead inertia, and bombs will drop hundreds of meters off target.
3. **No Jet Audio Loops**:
   * Do not copy standard bomber audio blocks containing jet engines (`TakeOff`, `Landing`, `MoveLoop`). Keep movement silent.
4. **SoundBank `loopCount`**:
   * Ensure `alien_bombrel` sound bank has `sb[229] = 0` so the wet release audio does not repeat indefinitely.
