# Porting Guide: Heavy Bio-Gunship (Aerial Hunter / Spiker)

## 1. Required Context & Unit Identity
* **Role**: Tech 2 Biological Gunship (Aerial Hunter)
* **Design Concept**: A hovering, multi-winged predatory wasp/mantis hybrid that circles over enemy armies, raining sustained bursts of acidic stingers and bio-spikes into tanks and defenses.
* **Suggested Unit ID**: `XRA0205` (T2 Bio-Gunship)

### BAR Source Files
* **Unit Definition**: `units/other/raptors/raptor_air_gunship_basic_t2_v1.lua`
* **3D Models**:
  * Primary: `objects3d/raptors/spiker_gunship.s3o` (Dedicated gunship model with articulated ventral stinger turret)
  * Secondary: `objects3d/raptors/flying_raptor_remaster.s3o`
* **Textures**:
  * Diffuse: `unittextures/raptors/spiker_gunship.dds`
  * Normal / Specular: Synthesized tangent-space normal map + specular mask.
* **Audio**:
  * Stinger Fire: `sounds/raptors/smallraptorattack.wav` or `talonattack.wav`
  * Death Screech: `sounds/raptors/talondie.wav`

### Recommended FAF Game Stats
* **Health**: 850 HP
* **Cost**: Mass: 240, Energy: 4,800, Build Time: 1,600
* **MaxAirspeed**: 8.0 (Hovering / strafing capability)
* **CombatTurnSpeed**: 2.5
* **Motion Type**: `RULEUMT_Air` (Gunship physics)
* **Weapon (`StingerBurst`)**:
  * `DisplayName`: Bio-Stinger Gatling Spikes
  * `Damage`: 28
  * `DamageType`: `Normal`
  * `MuzzleSalvoSize`: 2
  * `MuzzleSalvoDelay`: 0.1
  * `RateOfFire`: 2.5 (High sustained DPS: ~140 DPS)
  * `MaxRadius`: 22
  * `TurretPitchRange`: 70
  * `TurretYawRange`: 180 (Full hemisphere coverage)

---

## 2. Step-by-Step Porting Instructions

### Step 1: Model & Bone Hierarchy
1. Extract `objects3d/raptors/spiker_gunship.s3o`.
2. Convert to `.scm`:
   * Required Bones:
     * `root` (Bone 0, parent: -1)
     * `body` (Bone 1)
     * `head` (Bone 2)
     * `turret_stinger` (Ventral rotating turret bone)
     * `firepoint_l`, `firepoint_r` (Alternating muzzles)
     * `lwing_upper`, `lwing_lower`, `rwing_upper`, `rwing_lower` (4 wings for hover balance)
   * Export to `/mods/RaptorFaction/units/XRA0205/XRA0205_lod0.scm`.

### Step 2: Quad-Wing Hover Animation (`.sca`)
1. **Hover Flap (`XRA0205_Afly.sca`)**:
   * Rapid 16-frame figure-8 wing stroke (playback rate = 2.5).
   * Frame 0 Root bone must be centered: `px=0, py=0, pz=0, qw=1, qx=0, qy=0, qz=0`.
2. **Death Spiral (`XRA0205_Adeath01.sca`)**:
   * 20-frame violent spin with severed wing and trailing gore.

### Step 3: Gunship Flight Physics in Blueprint (`XRA0205_unit.bp`)
* Gunships require specific `Air` physics settings:
  ```lua
  Air = {
      AutoLandTime = 1,
      BankFactor = 0.1,
      BankForward = false,
      CanFly = true,
      CirclingDirChangeFrequencySec = 1,
      CirclingElevationChangeRatio = 0.25,
      CirclingFlight = true,
      CirclingRadiusChangeMaxRatio = 0.9,
      CirclingRadiusChangeMinRatio = 0.6,
      CirclingRadiusVsTurnSpeed = 0.6,
      CombatTurnSpeed = 2.5,
      KMove = 0.8,
      KTurn = 2.0,
      LiftFactor = 7,
      MaxAirspeed = 8.0,
      StartTurnDistance = 5,
      TurnSpeed = 2.5,
  },
  ```
* Include `DeathImpact` weapon for ground collision.

### Step 4: Unit Scripting (`XRA0205_script.lua`)
```lua
local CAirUnit = import('/lua/cybranunits.lua').CAirUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

XRA0205 = ClassUnit(CAirUnit) {
    OnCreate = function(self)
        CAirUnit.OnCreate(self)
        local flyAnim = CreateAnimator(self)
        flyAnim:PlayAnim('/mods/RaptorFaction/units/XRA0205/XRA0205_Afly.sca', true)
        flyAnim:SetRate(2.5)
        self.FlyAnimManip = flyAnim
        self.Trash:Add(flyAnim)
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.3)
        end
        CAirUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        local scale = 1.4 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}
TypeClass = XRA0205
```

---

## 3. Pitfalls & Errors to Avoid

1. **CirclingFlight vs Hover**:
   * If `CirclingFlight = false`, gunships attempt to stop and shoot motionless, becoming sitting ducks for enemy mobile AA. Ensure `CirclingFlight = true` with reasonable radius.
2. **Turret Pitch Limit**:
   * Since the gunship fires downward at ground units, `TurretPitchRange = 70` and `TurretPitch = -20` ensures the stinger points naturally down toward targets beneath it.
3. **SoundBank Configuration**:
   * Audio bank `Raptor_Gunship_Attack` must have `sb[229] = 0` and verified CRC-16 checksum.
