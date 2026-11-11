# Porting Guide: Mobile Bio-Artillery (Lobber / Mortar Bug)

## 1. Required Context & Unit Identity
* **Role**: Tech 2 Mobile Bio-Artillery (Mortar Bug)
* **Design Concept**: An arched, armored bug with an organic bio-mortar dorsal bulb. It anchors its rear claws and contracts its dorsal thorax to heave heavy, arcing globs of acidic bile over obstacles, base walls, and shields.
* **Suggested Unit ID**: `XRA0202` (Tech 2 Raptor Artillery)

### BAR Source Files
* **Unit Definition**: `units/other/raptors/arty/raptor_allterrain_arty_basic_t2_v1.lua` / `units/other/raptors/arty/raptorartillery.lua`
* **3D Models**:
  * Primary: `objects3d/raptors/raptor_artillery_v2.s3o` (Modern remastered model with articulated mortar barrel)
  * Classic: `objects3d/raptors/raptorearty1.s3o`
* **Textures**:
  * Diffuse: `unittextures/raptors/raptor_artillery_diffuse.dds` (or `raptorc3c.dds`)
  * Normal / Specular: Synthesized tangent-space normal map + specular mask.
* **Audio**:
  * Weapon Fire: `sounds/raptors/bugarty.wav` (low-frequency wet thud / biological launch)
  * Death Screech: `sounds/raptors/smallraptordead.wav` or `talondie.wav`

### Recommended FAF Game Stats
* **Health**: 480 HP
* **Cost**: Mass: 280, Energy: 2,000, Build Time: 1,400
* **Speed**: 2.5 (slower than swarmers, deliberate gait)
* **Motion Type**: `RULEUMT_Amphibious`
* **Weapon**:
  * `DisplayName`: Bio-Acid Lobber
  * `Damage`: 280 (High damage per shot, slow RoF)
  * `DamageRadius`: 2.5 (Area of effect acid splash)
  * `DamageType`: `Normal`
  * `RateOfFire`: 0.25 (1 shot every 4 seconds)
  * `MinRadius`: 8
  * `MaxRadius`: 64 (Indirect fire artillery range)
  * `BallisticArc`: `RULEUBA_HighArc`

---

## 2. Step-by-Step Porting Instructions

### Step 1: S3O to SCM Model Extraction
1. Extract `objects3d/raptors/raptor_artillery_v2.s3o` from the BAR archive pool.
2. Convert to Supreme Commander `.scm` using `convert_s3o_to_scm.py`:
   * Ensure bone tree contains:
     * `root` (Bone 0, parent: -1)
     * `torso` / `body` (Bone 1, parent: 0)
     * `cannon` / `barrel` (Dorsal mortar tube, parent: 1)
     * `firepoint` (Mortar muzzle, parent: cannon)
     * Leg bones: `lleg1`, `rleg1`, `lleg2`, `rleg2`, `lleg3`, `rleg3`
   * Export to `/mods/RaptorFaction/units/XRA0202/XRA0202_lod0.scm`.

### Step 2: Animation Synthesis (.sca)
1. **Walk Cycle (`XRA0202_Awalk.sca`)**:
   * 24-frame alternating gait cycle for 6 articulated legs.
   * Subtle rhythmic up-down bobbing of the dorsal mortar sack (`cannon`).
   * **Root Frame 0 Requirement**: `px=0, py=0, pz=0, qw=1, qx=0, qy=0, qz=0`.
2. **Mortar Recoil Animation (`XRA0202_Afire.sca`)**:
   * 12-frame lunge: dorsal tube tilts upward + back, squishes down, then snaps forward on launch.
3. **Death Collapse (`XRA0202_Adeath01.sca`)**:
   * 20-frame collapse: legs buckle outward, dorsal bulb ruptures and deflates against the terrain.

### Step 3: Projectile Creation (`XRA_AcidGoo01`)
1. Create projectile directory `/mods/RaptorFaction/projectiles/XRA_AcidGoo01/`.
2. Projectile Mesh: Sphere / teardrop bio-bomb with `UniformScale = 2.0`.
3. Trail Emitter: Use acid mist trail `/effects/emitters/miasma_munition_burst_01_emit.bp` or `/effects/emitters/build_red_paint_spray_emit.bp`.
4. Impact Emitter: On impact, spawn acid burst + red blood splash decal.

### Step 4: Unit Blueprint (`XRA0202_unit.bp`)
* Include mandatory categories:
  ```lua
  Categories = {
      'PRODUCTSC1', 'SELECTABLE', 'BUILTBYTIER2FACTORY', 'BUILTBYTIER3FACTORY',
      'CYBRAN', 'RAPTOR', 'MOBILE', 'LAND', 'TECH2', 'INDIRECTFIRE', 'ARTILLERY',
      'VISIBLETORECON', 'RECLAIMABLE', 'OVERLAYINDIRECTFIRE',
  },
  ```
* Set `LODCutoff = 260`.
* High-arc ballistic firing parameters:
  ```lua
  Weapon = {
      {
          Audio = {
              Fire = Sound {
                  Bank = 'Raptor_Artillery',
                  Cue = 'Attack',
                  LodCutoff = 'Weapon_LodCutoff',
              },
          },
          BallisticArc = 'RULEUBA_HighArc',
          FiringRandomness = 1.2,
          MaxRadius = 64,
          MinRadius = 8,
          MuzzleVelocity = 22,
          MuzzleVelocityReduceDistance = 64,
          TurretPitchRange = 80,
          TurretPitchSpeed = 40,
          TurretYawSpeed = 50,
          Turreted = true,
      },
  },
  ```

### Step 5: Unit Scripting (`XRA0202_script.lua`)
```lua
local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

local RaptorArtilleryWeapon = ClassWeapon(DefaultProjectileWeapon) {
    CreateProjectileAtMuzzle = function(self, muzzle)
        local proj = DefaultProjectileWeapon.CreateProjectileAtMuzzle(self, muzzle)
        -- Trigger dorsal sack recoil contraction
        if self.unit.RecoilRotator then
            self.unit:PlayRecoil()
        end
        return proj
    end,
}

XRA0202 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        MainGun = ClassWeapon(RaptorArtilleryWeapon) {},
    },

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(1.4)
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        local scale = 1.5 * (1 + (overKillRatio or 0) * 0.5)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}
TypeClass = XRA0202
```

### Step 6: Audio Bank Generation
* Bank Name: `Raptor_Artillery`
* Source WAV: `sounds/raptors/bugarty.wav`
* SoundBank setup:
  * Set `sb[229] = 0` (`loopCount = 0` for clean single-shot lob).
  * Compute CRC-16 checksum (`calc_xact_crc`) over `sb[18:]`.
  * Map all 16 hash buckets at offset 239 to `0x0000` (Cue 0).

---

## 3. Pitfalls & Errors to Avoid

1. **`loopCount` Must Be 0**:
   * If `sb[229]` remains `0xFF`, every artillery lob will endlessly loop the launch thud forever until the game ends.
2. **Missing `MinRadius`**:
   * Without `MinRadius = 8`, the high-arc artillery will attempt to shoot straight down into its own body when attacked by swarmers, dealing friendly splash damage to itself.
3. **Muzzle Velocity for HighArc**:
   * Ensure `MuzzleVelocity = 20-25` with `MuzzleVelocityReduceDistance = 64`. If muzzle velocity is too high (> 50), the high arc projectile will fly off into the stratosphere.
4. **`VISIBLETORECON` Omission**:
   * If omitted from `Categories`, enemy radar will detect a blip, but the unit mesh will never render when in visual range.
5. **Icon Mipmaps**:
   * Generate uncompressed 32-bit BGRA (`.dds`) with 9 mipmap levels (size 349,652 bytes) to avoid UI rendering corruptions.
