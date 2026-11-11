# Comprehensive Porting Guide: 6-Legged & Flying Raptors (BAR to FAF)

This guide provides complete, battle-tested instructions for an agent or developer to port **6-Legged All-Terrain Raptors** and **Flying Air Raptors** from Beyond-All-Reason (BAR) into the Supreme Commander: Forged Alliance Forever (FAF) `RaptorFaction` standalone mod.

---

## 1. Prerequisites & Shared Foundation

All conversion tooling relies on the foundation established in:
- `scm_io.py`: Binary reading/writing for `.scm` (meshes) and `.sca` (animations).
- `build_raptor_v2.py`: Pipeline template for package indexing, mesh conversion, XACT audio, and zip export.
- Target Mod Directory: `C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction`
- BAR Package Path: `P:\Games\Beyond-All-Reason\data\packages\ad33f718d83a34e194d7182194a91ede.sdp`
- BAR Pool Directory: `P:\Games\Beyond-All-Reason\data\pool`

### The Golden Rule of FAF SCA Animations (DO NOT SKIP)
> [!CAUTION]
> In Supreme Commander / FAF, every `.sca` file requires a **28-byte dummy root pose** (`px=0, py=0, pz=0, qw=1, qx=0, qy=0, qz=0`) at `anim_data_offset` before Frame 0 begins!
> Total data size must strictly equal:
> $$\text{anim\_data\_off} + 28 + (\text{num\_frames} \times \text{frame\_size})$$
> Omitting these 28 bytes will cause a 1-bone stride shift in the C++ engine, causing all limbs and parts to detach and fly across the map.

### The Microsoft XACT Audio Rule
> [!IMPORTANT]
> FAF rejects hand-crafted `.xwb` files without official XACT alignment and flags. Always use the tested `build_xact_bank()` function:
> 1. In `WAVEBANKENTRY` (Seg1), Duration is packed in the upper 28 bits: `dwFlagsAndDuration = (num_samples << 4) & 0xFFFFFFFF`. Passing raw unshifted sample count corrupts the Flags bitfield, causing the engine to fail with `Error loading WaveBank: Invalid data`.
> 2. `seg4_len` must be padded to 4-byte alignment matching `dwAlignment = 4`.
> 3. Cues must point to offset 277 with exact string length in uint16 at `0x1e`.
> 4. For biological units with no engine/hum sound, omit `AmbientMove`, `StartMove`, `StopMove`, `Landing`, `TakeOff` from `Audio = { ... }`. FAF's engine cleanly returns `false` without playing sound, providing authentic silence with zero channel overhead.

---

## 2. Porting 6-Legged All-Terrain Raptors

### 2.1 Target Unit Specifications
- **Unit ID**: `XRA0201` (Tech 2 All-Terrain Heavy Crawler / Spiker)
- **BAR S3O Model**: `objects3d/raptors/raptor_6legged_l.s3o`
- **BAR Script**: `scripts/raptors/raptor_walk_6legged.h`
- **Unit Definition**: `units/other/raptors/swarmer/allterrain/raptor_6legged_l.lua`

### 2.2 Bone Hierarchy
Extracted from `raptor_6legged_l.s3o`:
```
- base (root, pivot 0, 0, 0)
  - torso (pivot 0, 12.0, 0)
    - thor1 -> thor2 -> thor3 -> thor4 -> thor5 -> thor6 -> thor7 (Spine / Tail Stinger)
      - flare (Muzzle at thor6/7)
    - wingl, wingr (Side armor crests)
    - thigh1l -> leg1l -> foot1l (Front Left Leg)
    - thigh1r -> leg1r -> foot1r (Front Right Leg)
    - thigh2l -> leg2l -> foot2l (Middle Left Leg)
    - thigh2r -> leg2r -> foot2r (Middle Right Leg)
    - thigh3l -> leg3l -> foot3l (Rear Left Leg)
    - thigh3r -> leg3r -> foot3r (Rear Right Leg)
```

### 2.3 Mathematical Tripod Walk Cycle
Insects and hexapods walk using an **alternating tripod gait**:
- **Tripod A**: `leg1l` (front-left), `leg2r` (middle-right), `leg3l` (rear-left).
- **Tripod B**: `leg1r` (front-right), `leg2l` (middle-left), `leg3r` (rear-right).
- Tripod B is out-of-phase with Tripod A by $\pi$ radians ($180^\circ$).

#### Keyframe Generator Code (`generate_6legged_anims.py`):
```python
num_walk_frames = 24
walk_duration = 0.8
for f_idx in range(num_walk_frames):
    t_ratio = f_idx / num_walk_frames
    phase_A = 2.0 * math.pi * t_ratio
    phase_B = phase_A + math.pi

    # Spine undulating wave
    for i in range(1, 8):
        b_name = f"thor{i}"
        wave = math.sin(phase_A - i * 0.4) * math.radians(6.0)
        rot[b_name] = (wave, 0, 0)

    # Tripod A legs
    for side, leg_idx in [('l', 1), ('r', 2), ('l', 3)]:
        p = phase_A
        rot[f"thigh{leg_idx}{side}"] = (math.sin(p) * math.radians(24.0), 0, math.sin(p) * math.radians(12.0))
        rot[f"leg{leg_idx}{side}"]   = (-max(0.0, -math.sin(p)) * math.radians(35.0), 0, 0)
        rot[f"foot{leg_idx}{side}"]  = (math.sin(p) * math.radians(15.0), 0, 0)

    # Tripod B legs
    for side, leg_idx in [('r', 1), ('l', 2), ('r', 3)]:
        p = phase_B
        rot[f"thigh{leg_idx}{side}"] = (math.sin(p) * math.radians(24.0), 0, math.sin(p) * math.radians(12.0))
        rot[f"leg{leg_idx}{side}"]   = (-max(0.0, -math.sin(p)) * math.radians(35.0), 0, 0)
        rot[f"foot{leg_idx}{side}"]  = (math.sin(p) * math.radians(15.0), 0, 0)
```

### 2.4 Unit Blueprint Settings (`XRA0201_unit.bp`)
- **Categories**: `'SELECTABLE'`, `'RAPTOR'`, `'MOBILE'`, `'LAND'`, `'TECH2'`, `'DIRECTFIRE'`, `'ALLTERRAIN'`
- **Physics**:
  ```lua
  Physics = {
      BankingSlope = 0,
      MaxAcceleration = 3.5,
      MaxBrake = 3.5,
      MaxSpeed = 3.6,
      MaxSpeedReverse = 0,
      MaxSteerForce = 15,
      MotionType = 'RULEUMT_Amphibious',
      TurnRadius = 0,
      TurnRate = 180,
  },
  ```
- **Audio**:
  - `Destroyed`: `Sound { Bank = 'Raptor_Death', Cue = 'Death' }`
  - `Fire`: `Sound { Bank = 'Raptor_Attack', Cue = 'Attack' }`
  - `AmbientMove` / `StartMove` / `StopMove`: Omitted (silence, no mechanical Mantis sounds)

---

## 3. Porting Flying Raptors (Air Units)

### 3.1 Target Unit Specifications
- **Unit ID**: `XRA0105` (Tech 1 or Tech 2 Air Swarm Fighter / Dive Bomber)
- **BAR S3O Model**: `objects3d/raptors/flying_raptor_remaster.s3o`
- **BAR Script**: `scripts/raptors/raptor_fly.h`
- **Unit Definition**: `units/other/raptors/fighter/raptor_air_fighter_basic_t1_v1.lua`

### 3.2 Bone Hierarchy
Extracted from `flying_raptor_remaster.s3o`:
```
- body (root, pivot 0, 6.79, -2.08)
  - head (pivot 0, 0.81, 2.80)
    - lsack -> lblade (Left Mandible Scissor)
    - rsack -> rblade (Right Mandible Scissor)
    - mblade (Center Spike Tongue)
  - liwing -> lowing (Left Inner Wing -> Left Outer Wing)
  - riwing -> rowing (Right Inner Wing -> Right Outer Wing)
  - tail (pivot 0, 1.39, -16.0)
```

### 3.3 Mathematical Flight Animation (`XRA0105_Afly.sca`)
Flying raptors require a fluid flapping and gliding cycle:
- **Flap Frequency**: 2.5 Hz (0.4s period per flap cycle)
- **Inner Wings (`liwing`, `riwing`)**: Roll around Z axis by $\pm 32^\circ$.
- **Outer Wings (`lowing`, `rowing`)**: Flap with a $35^\circ$ phase lag (simulating aerodynamic flexible membrane bending).
- **Body Bobbing**: Up/down translation of 0.12 units in phase with wing downstroke.
- **Tail Balance**: Gentle counter-pitching ($\pm 8^\circ$).

#### Keyframe Generator Code:
```python
num_fly_frames = 20
fly_duration = 0.45
for f_idx in range(num_fly_frames):
    t_ratio = f_idx / num_fly_frames
    phase = 2.0 * math.pi * t_ratio

    # Wing Flapping (Z-axis roll)
    flap_inner = math.sin(phase) * math.radians(32.0)
    flap_outer = math.sin(phase - 0.5) * math.radians(45.0)

    rot["liwing"] = (0, 0, flap_inner)
    rot["riwing"] = (0, 0, -flap_inner)
    rot["lowing"] = (0, 0, flap_outer)
    rot["rowing"] = (0, 0, -flap_outer)

    # Body Lift & Pitch
    lift = -math.sin(phase) * 0.08
    body_pitch = math.sin(phase) * math.radians(5.0)
    pos["body"] = (rest["body"][0], rest["body"][1] + lift, rest["body"][2])
    rot["body"] = (body_pitch, 0, 0)
    rot["tail"] = (-body_pitch * 1.5, 0, 0)
```

### 3.4 Air Unit Script (`XRA0105_script.lua`)
Air units inherit from `CAirUnit`:
```lua
local CAirUnit = import('/lua/cybranunits.lua').CAirUnit
local DefaultProjectileWeapon = import('/lua/sim/defaultweapons.lua').DefaultProjectileWeapon
local EffectTemplate = import('/lua/EffectTemplates.lua')

---@class RaptorAirWeapon : DefaultProjectileWeapon
local RaptorAirWeapon = ClassWeapon(DefaultProjectileWeapon) {
    FxMuzzleFlash = EffectTemplate.PhasicAutoGunMuzzleFlash,

    CreateProjectileAtMuzzle = function(self, muzzle)
        local proj = DefaultProjectileWeapon.CreateProjectileAtMuzzle(self, muzzle)
        self.unit:PlayBiteAttack()
        return proj
    end,
}

---@class XRA0105 : CAirUnit
XRA0105 = ClassUnit(CAirUnit) {
    Weapons = {
        Claws = ClassWeapon(RaptorAirWeapon) {},
    },

    OnCreate = function(self)
        CAirUnit.OnCreate(self)
        self.Rotators = {
            lsack = CreateRotator(self, 'lsack', 'y', 0, 600, 1000),
            rsack = CreateRotator(self, 'rsack', 'y', 0, 600, 1000),
            lblade = CreateRotator(self, 'lblade', 'y', 0, 600, 1000),
            rblade = CreateRotator(self, 'rblade', 'y', 0, 600, 1000),
        }
    end,

    PlayBiteAttack = function(self)
        if self.BiteThread then KillThread(self.BiteThread) end
        self.BiteThread = self:ForkThread(function()
            local r = self.Rotators
            if not r then return end
            r.lsack:SetGoal(-90); r.lsack:SetSpeed(600)
            r.rsack:SetGoal(90);  r.rsack:SetSpeed(600)
            r.lblade:SetGoal(90); r.lblade:SetSpeed(600)
            r.rblade:SetGoal(-90); r.rblade:SetSpeed(600)
            WaitFor(r.rblade)
            r.lsack:SetGoal(0); r.lsack:SetSpeed(140)
            r.rsack:SetGoal(0); r.rsack:SetSpeed(140)
            r.lblade:SetGoal(0); r.lblade:SetSpeed(140)
            r.rblade:SetGoal(0); r.rblade:SetSpeed(140)
        end)
    end,
}

TypeClass = XRA0105
```

### 3.5 Air Unit Blueprint Settings (`XRA0105_unit.bp`)
- **Categories**: `'SELECTABLE'`, `'RAPTOR'`, `'MOBILE'`, `'AIR'`, `'TECH1'`, `'ANTIAIR'`, `'HIGHALTAIR'`
- **Air Physics**:
  ```lua
  Air = {
      AutoLandTime = 1,
      BankFactor = 1.2,
      BankForward = false,
      BreakOffDistance = 15,
      BreakOffTrigger = 10,
      CanFly = true,
      CombatTurnSpeed = 1.8,
      EngageDistance = 50,
      KLift = 3,
      KLiftDamping = 2.5,
      KMove = 1.5,
      KMoveDamping = 1,
      KRoll = 1.5,
      KRollDamping = 1,
      KTurn = 1.5,
      KTurnDamping = 1.5,
      LiftFactor = 7,
      MaxAirspeed = 12,
      MinAirspeed = 6,
      StartTurnDistance = 5,
      TightTurnMultiplier = 1.05,
      TurnSpeed = 2.4,
      WingLoopRange = 0,
  },
  Physics = {
      Elevation = 9.5,
      MotionType = 'RULEUMT_Air',
  },
  ```

---

## 4. Verification & Testing Checklist

When porting a new raptor, always run these checks:
1. **Model & Skeleton**:
   - Verify `write_scm` receives inverted local bind matrices.
   - Run python inspect script to ensure vertex count matches S3O.
2. **Animation**:
   - Check file length in bytes: must strictly match $\text{anim\_data\_off} + 28 + (\text{num\_frames} \times \text{frame\_size})$.
   - Verify `px=0, py=0, pz=0, qw=1, qx=0, qy=0, qz=0` exists at `anim_data_off`.
3. **Sound**:
   - Wavebank flag in Seg0 must be `524288` (`0x80000`).
   - `dwFlagsAndDuration` in Seg1 must encode duration as `(num_samples << 4) & 0xFFFFFFFF`.
   - Seg4 length must be padded to 4-byte alignment.
   - **XACT SoundBank Checksum (FCS16)**: Microsoft XACT engine (`xactengine3_0.dll`) validates a 16-bit CCITT CRC checksum (polynomial `0x8408`) stored at offset `0x08` calculated over `data[18:]`. If mismatched, bank loading fails with `Invalid data`.
   - **Cue Hash Table**: Map all 16 hash slots (at offset 239) to `0x0000` (pointing to Cue 0) so any cue lookup (`Attack`, `Death`, `Silence`) immediately resolves to the sound regardless of the cue name.
   - **One-Shot vs Looping**: In the XACT SoundBank event, byte 229 stores `loopCount`. A value of `0xFF` (255) means infinite looping. For weapon attacks, death screams, or one-shot sound effects, `loopCount` must be set to `0x00` (`0`) to prevent infinite looping.
   - Ground & air raptor movement: omit `AmbientMove`, `Landing`, `TakeOff` etc. for authentic silence without jet/bot sounds.
   - **Biological Death Particles**: Override `CreateDestructionEffects` and `OnKilled` in unit scripts to spawn custom blood spray (`raptor_blood_spray_01_emit.bp`), flesh chunks (`raptor_flesh_chunks_01_emit.bp`), and red mist (`raptor_blood_cloud_01_emit.bp`), replacing metallic explosions with visceral alien gore.
4. **Projectiles & Weapons**:
   - Never use invalid poly trail paths. Always use `/effects/emitters/default_polytrail_01_emit.bp` or other verified emitters in `effects.nx2`.
   - Scale projectile mesh to `UniformScale = 2.5` to `3.5` so it is clearly visible.
5. **Invisibility & Recon Checklist (Crucial for Multiplayer)**:
   - Always include `'VISIBLETORECON'` in `Categories`. Without it, enemy players will only see an un-identified radar ping and the 3D model will be completely invisible.
   - For single-LOD units, set `LODCutoff = 250` or `260` (especially for air units) to prevent the unit from disappearing when zoomed out.
   - Ensure air units have a `DeathImpact` weapon (`DisplayName = 'Air Crash'`) to prevent engine crash warnings on crash landing.
6. **Unit Icons & BAR Discrepancy Rule**:
   - Beware: In the BAR codebase, several units (like `raptor_6legged_l.lua`) point `buildpic` to older 4-legged units (`raptorc3c.DDS`) as temporary placeholders.
   - For an authentic match, render the actual `.scm` mesh directly into a 256x256 RGBA image with lighting and soft ground shadow.
   - Save as standard FAF icon format: uncompressed 32-bit BGRA (`flags = 0x41`, `DDPF_RGB | DDPF_ALPHAPIXELS`), with 9 mipmap levels (exact file size: 349,652 bytes).
7. **In FAF Engine Logs**:
   - Check `game_<id>.log` for any warnings or unresolved banks.
   - Verify cheat menu (`F2`) spawns the unit cleanly and test both player and enemy perspectives.
