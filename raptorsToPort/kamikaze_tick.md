# Porting Guide: Explosive Kamikaze Tick (Suicide Bug / Dodo)

## 1. Required Context & Unit Identity
* **Role**: Tech 1/Tech 2 Suicide Kamikaze Bomb (Acid Tick)
* **Design Concept**: A swollen, bloated, highly unstable biological tick filled with pressurized volatile acidic digestive bile. It skitters across the battlefield at blinding speed, detonating on contact with enemy formations to vaporize light units and breach defenses.
* **Suggested Unit ID**: `XRA0103` (Kamikaze Bio-Tick)

### BAR Source Files
* **Unit Definition**: `units/other/raptors/kamikaze/raptor_land_kamikaze_basic_t2_v1.lua`
* **3D Models**:
  * Primary: `objects3d/raptors/raptor_dodo.s3o` (Bloated bulbous abdomen with rapid skitter legs)
  * Variant: `objects3d/raptors/raptor_dodo_electric.s3o` (EMP variant with glowing blue sacks)
* **Textures**:
  * Diffuse: `unittextures/raptors/raptor_dodo.dds` (veiny translucent green-yellow sack)
  * Normal / Specular: Synthesized tangent-space normal map + specular mask.
* **Audio**:
  * Skitter / Hiss: `sounds/raptors/smallraptorhiss.wav` or `talonattack.wav`
  * Suicide Detonation: `sounds/raptors/alien_bombrel.wav` / `explosions/wet_splat_large.wav`

### Recommended FAF Game Stats
* **Health**: 110 HP (Fragile, glass-cannon)
* **Cost**: Mass: 45, Energy: 350, Build Time: 160 (Cheap, mass-producible)
* **Speed**: 5.2 (Extremely rapid skitter, faster than scout bots)
* **Motion Type**: `RULEUMT_Amphibious`
* **Suicide Weapon (`DeathWeapon`)**:
  * `DisplayName`: Bio-Acid Self-Destruction
  * `Damage`: 750 (High explosive burst)
  * `DamageRadius`: 3.5 (Significant AOE)
  * `DamageType`: `Normal`
  * `DamageFriendly`: true (Hazardous to clumped allies if detonated early!)

---

## 2. Step-by-Step Porting Instructions

### Step 1: Model & Rigging Extraction
1. Extract `objects3d/raptors/raptor_dodo.s3o` from BAR pool.
2. Convert to `.scm` using `convert_s3o_to_scm.py`:
   * Bone Hierarchy:
     * `root` (Bone 0, parent: -1)
     * `sack` / `abdomen` (Bloated central body)
     * `head` (Small anterior mandibles)
     * Legs: `lleg1`, `rleg1`, `lleg2`, `rleg2`
   * Export to `/mods/RaptorFaction/units/XRA0103/XRA0103_lod0.scm`.

### Step 2: High-Speed Skitter Animation (`.sca`)
1. **Walk Cycle (`XRA0103_Awalk.sca`)**:
   * Rapid 16-frame skitter at 2.8x animation playback rate.
   * Rhythmic jiggle of the swollen acid sack.
   * Frame 0 Root: `px=0, py=0, pz=0, qw=1, qx=0, qy=0, qz=0`.
2. **Detonation Surge (`XRA0103_Adeath01.sca`)**:
   * 8-frame rapid expansion: the sack swells by 140% before violently bursting outward.

### Step 3: Self-Destruct Weapon Logic in Blueprint (`XRA0103_unit.bp`)
* In FAF, suicide units trigger detonation on collision or manual command:
  ```lua
  Weapon = {
      {
          AboveWaterTargetsOnly = true,
          CollideFriendly = false,
          Damage = 750,
          DamageFriendly = true,
          DamageRadius = 3.5,
          DamageType = 'Normal',
          DisplayName = 'Suicide Detonation',
          FireTargetLayerCapsTable = {
              Land = 'Land|Water|Seabed',
              Water = 'Land|Water|Seabed',
          },
          FiringTolerance = 180,
          Label = 'Suicide',
          MaxRadius = 1.5,
          RangeCategory = 'UWRC_DirectFire',
          RateOfFire = 1,
          SlavedToBody = true,
          TargetCheckInterval = 0.1,
          TargetPriorities = {
              'SPECIALHIGHPRI', 'MOBILE', 'STRUCTURE DEFENSE', 'ALLUNITS',
          },
          TargetRestrictDisallow = 'UNTARGETABLE',
          Turreted = false,
          WeaponCategory = 'Direct Fire',
      },
  },
  ```

### Step 4: Unit Script Implementation (`XRA0103_script.lua`)
```lua
local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local Weapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class KamikazeWeapon : Weapon
local KamikazeWeapon = ClassWeapon(Weapon) {
    OnFire = function(self)
        -- Detonate self immediately upon touching enemy target
        self.unit:Kill()
    end,
}

XRA0103 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        Suicide = ClassWeapon(KamikazeWeapon) {},
    },

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        -- Spawn massive explosive gore and acid shockwave
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.5)
        end
        -- Area damage on death
        DamageArea(self, self:GetPosition(), 3.5, 750, 'Normal', true)
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        -- Suppress default metallic explosions; pure bio-acid gore
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(2.8)
        end
    end,
}
TypeClass = XRA0103
```

---

## 3. Pitfalls & Errors to Avoid

1. **Infinite Damage Recursion Loop**:
   * Calling `DamageArea` inside `OnKilled` can trigger friendly death cascades. Ensure the damage function passes `self` as the instigator, but does not re-enter `OnKilled` on an already dead unit (`self.Dead = true`).
2. **Pathfinding Traps for Ultra-Fast Units**:
   * Because speed is 5.2, set `TurnRate = 240` and `MaxBrake = 10` so the unit does not slide uncontrollably past its target during turning.
3. **SoundBank Checksum & Loop**:
   * Detonation sound must have `sb[229] = 0` and verified CRC-16 checksum. If looping is enabled on a suicide unit, the explosion audio will permanently buzz at the death coordinates.
