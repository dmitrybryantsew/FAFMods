# Porting Guide: Raptor Matriarch & Queen (Experimental Boss Titan)

## 1. Required Context & Unit Identity
* **Role**: Tech 4 / Experimental Biological Titan (Raptor Queen)
* **Design Concept**: The apex matriarch of the swarm. A colossal multi-limbed behemoth standing higher than a Cybran Monkeylord. Armed with a titanic bio-plasma roar cannon, sweeping scythe claws that crush armored battalions, an anti-air spore battery, and the ability to gestate raptor swarmers directly onto the battlefield.
* **Suggested Unit ID**: `XRA0401` (Experimental Raptor Queen)

### BAR Source Files
* **Unit Definition**: `units/other/raptors/queens/raptor_queen_normal.lua` / `units/other/raptors/miniqueen/raptor_matriarch_basic.lua`
* **3D Models**:
  * Primary Queen: `objects3d/raptors/epic_raptorq.s3o` or `objects3d/raptors/raptorq.s3o`
  * Mini-Queen / Matriarch: `objects3d/raptors/raptor_miniqueen_basic.s3o`
* **Textures**:
  * Diffuse: `unittextures/raptors/raptor_queen.dds`
  * Normal / Specular: Synthesized tangent-space normal map + specular mask.
* **Audio**:
  * Roar Plasma: `sounds/raptors/bigraptorroar.wav` (Earth-shaking guttural roar)
  * Massive Cleave: `sounds/raptors/bigraptorbreath.wav`
  * Spore Battery: `sounds/raptors/spore_xl.wav`
  * Cataclysmic Death Screech: `sounds/raptors/bigraptordead.wav`

### Recommended FAF Game Stats
* **Health**: 68,000 HP (Experimental Titan durability)
* **Cost**: Mass: 28,000, Energy: 320,000, Build Time: 42,000
* **Speed**: 2.2 (Grand, stomping gait that crushes trees and debris)
* **Footprint**: SizeX = 5.0, SizeZ = 6.0, CollisionOffsetY = 1.8
* **Motion Type**: `RULEUMT_Amphibious`
* **Weapons**:
  1. **Primary: Titanic Bio-Plasma Roar Cannon**:
     * `Damage`: 2,200 (Every 3 seconds, range: 48)
     * `DamageRadius`: 4.0 (Huge corrosive plasma sphere)
  2. **Secondary: Crushing Mandible & Scythe Sweep**:
     * `Damage`: 1,200 (Continuous melee cleave, range: 12)
     * `DamageRadius`: 2.5
  3. **Tertiary: Heavy Anti-Air Spore Flak**:
     * `Damage`: 120 per spore (Salvo size: 6, range: 42)
  4. **Field Gestation (Passive Ability)**:
     * Spawns 4 T1 Raptor Swarmers (`XRA0101`) every 25 seconds directly from her brood sack.

---

## 2. Step-by-Step Porting Instructions

### Step 1: Model Extraction & Rigging
1. Extract `objects3d/raptors/epic_raptorq.s3o`.
2. Convert to `.scm`:
   * Ensure bone tree contains:
     * `root` (Bone 0, parent: -1)
     * `pelvis` / `lower_body` (Bone 1)
     * `thorax` / `upper_body` (Bone 2)
     * `head` / `jaw` (Primary roar cannon muzzle: `firepoint_roar`)
     * `brood_sack` (Rear swollen gestation bulb)
     * Foreleg Scythes: `lscythe1`, `lscythe2`, `rscythe1`, `rscythe2`
     * 6 Massive Legs: `leg_fl`, `leg_fr`, `leg_ml`, `leg_mr`, `leg_rl`, `leg_rr`
   * Export to `/mods/RaptorFaction/units/XRA0401/XRA0401_lod0.scm`.

### Step 2: Animations (.sca)
1. **Epic Stomp Walk (`XRA0401_Awalk.sca`)**:
   * Heavy 32-frame staggered 6-leg cycle with deep torso swaying.
   * Frame 0 Root bone must be centered: `px=0, py=0, pz=0, qw=1, qx=0, qy=0, qz=0`.
2. **Roar Cannon Fire (`XRA0401_Aroar.sca`)**:
   * Chest rears up, jaws gape wide, head shakes violently during plasma expulsion.
3. **Cataclysmic Death (`XRA0401_Adeath01.sca`)**:
   * 40-frame collapse: legs buckle, brood sack ruptures, massive tremor.

### Step 3: Experimental Blueprint (`XRA0401_unit.bp`)
* Mandatory categories:
  ```lua
  Categories = {
      'PRODUCTSC1', 'SELECTABLE', 'BUILTBYTIER3COMMANDER', 'BUILTBYTIER3ENGINEER',
      'CYBRAN', 'RAPTOR', 'MOBILE', 'LAND', 'EXPERIMENTAL', 'DIRECTFIRE',
      'AMPHIBIOUS', 'VISIBLETORECON', 'RECLAIMABLE', 'OVERLAYDIRECTFIRE',
      'OVERLAYANTIAIR', 'NEEDMOBILEBUILD',
  },
  ```
* Include footfall camera shakes and terrain deformation sound.

### Step 4: Unit Scripting with Swarm Gestation (`XRA0401_script.lua`)
```lua
local CWalkingLandUnit = import('/lua/cybranunits.lua').CWalkingLandUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon

local BloodDeathEffects = {
    '/mods/RaptorFaction/effects/emitters/raptor_blood_spray_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_flesh_chunks_01_emit.bp',
    '/mods/RaptorFaction/effects/emitters/raptor_blood_cloud_01_emit.bp',
}

---@class RoarWeapon : DefaultProjectileWeapon
local RoarWeapon = ClassWeapon(DefaultProjectileWeapon) {
    CreateProjectileAtMuzzle = function(self, muzzle)
        local proj = DefaultProjectileWeapon.CreateProjectileAtMuzzle(self, muzzle)
        self.unit:PlayRoarAnimation()
        return proj
    end,
}

XRA0401 = ClassUnit(CWalkingLandUnit) {
    Weapons = {
        RoarCannon = ClassWeapon(RoarWeapon) {},
        ScytheCleave = ClassWeapon(DefaultProjectileWeapon) {},
        DefensiveSpores = ClassWeapon(DefaultProjectileWeapon) {},
    },

    OnCreate = function(self)
        CWalkingLandUnit.OnCreate(self)
        -- Start passive swarmer gestation thread
        self:ForkThread(self.BroodGestationThread)
    end,

    BroodGestationThread = function(self)
        while not self.Dead do
            WaitSeconds(25)
            if not self.Dead then
                local pos = self:GetPosition()
                -- Spawn 4 T1 Swarmers around brood sack
                for i = 1, 4 do
                    local ox = (i - 2.5) * 2.0
                    local oz = -4.0
                    local unit = CreateUnitHPR('XRA0101', self.Army, pos[1] + ox, pos[2], pos[3] + oz, 0, 0, 0)
                end
            end
        end
    end,

    OnKilled = function(self, instigator, type, overkillRatio)
        local army = self.Army
        -- Titanic blood eruption
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(4.0)
        end
        CWalkingLandUnit.OnKilled(self, instigator, type, overkillRatio)
    end,

    CreateDestructionEffects = function(self, overKillRatio)
        local army = self.Army
        local scale = 4.5 * (1 + (overKillRatio or 0) * 0.3)
        for _, emit in BloodDeathEffects do
            CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
        end
    end,
}
TypeClass = XRA0401
```

### Step 5: Sound Banks
* Banks: `Raptor_Queen_Roar.xsb`, `Raptor_Queen_Cleave.xsb`, `Raptor_Queen_Death.xsb`.
* Must set `sb[229] = 0` and recalculate CRC-16 checksum over `data[18:]`.

---

## 3. Pitfalls & Errors to Avoid

1. **Footprint & Navigation Meshes**:
   * An experimental unit needs `UniformScale = 1.8` to `2.2`. Ensure `SizeX = 4.5`, `SizeZ = 5.0` so other units can navigate around her without getting stuck in collision physics.
2. **Spawn Elevation Bug**:
   * In `BroodGestationThread`, compute `GetSurfaceHeight(pos[1] + ox, pos[3] + oz)` for the spawned units to prevent swarmers from spawning clipped beneath the terrain geometry.
3. **Sound LodCutoff**:
   * Because the Queen is an experimental boss, set `LodCutoff = 'UnitMove_LodCutoff'` or `'Weapon_LodCutoff'` with high values (e.g. 500+) so her roar and footfalls reverberate across the map.
