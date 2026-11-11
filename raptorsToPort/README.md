# Raptor Faction: Comprehensive Unit Porting Master Roadmap

This directory contains complete, production-ready porting guides for every remaining Beyond All Reason (BAR) Raptor unit into Supreme Commander: Forged Alliance (FAF).

---

## 1. Unit Archetype Porting Guides

| Guide | Unit ID | Tech Level | Role | Source Model | Primary Weapon |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [**bio_artillery.md**](file:///E:/Games/FAFMods/raptorsToPort/bio_artillery.md) | `XRA0202` | T2 | Mobile Indirect Artillery | `raptor_artillery_v2.s3o` | High-arc Goo / Acid Mortar |
| [**heavy_assault.md**](file:///E:/Games/FAFMods/raptorsToPort/heavy_assault.md) | `XRA0301` | T3 | Armored Frontline Behemoth | `raptorf1apex.s3o` | Heavy Dual Scythes + AA Spores |
| [**kamikaze_tick.md**](file:///E:/Games/FAFMods/raptorsToPort/kamikaze_tick.md) | `XRA0103` | T1/T2 | Suicide Acid Bomb | `raptor_dodo.s3o` | High-damage Area Self-Destruct |
| [**air_bomber.md**](file:///E:/Games/FAFMods/raptorsToPort/air_bomber.md) | `XRA0104` | T1/T2 | Biological Carpet Bomber | `raptoracidbomber.s3o` | Gravity Acid Salvo Bombs |
| [**air_gunship.md**](file:///E:/Games/FAFMods/raptorsToPort/air_gunship.md) | `XRA0205` | T2 | Hovering Hunter Gunship | `spiker_gunship.s3o` | 360° Gatling Bio-Spikes |
| [**healer_weaver.md**](file:///E:/Games/FAFMods/raptorsToPort/healer_weaver.md) | `XRA0109` | T1 | Mobile Engineer & Healer | `raptorhealer1.s3o` | Bio-Stream Build + Regen Aura |
| [**matriarch_queen.md**](file:///E:/Games/FAFMods/raptorsToPort/matriarch_queen.md) | `XRA0401` | T4 | Experimental Titan Boss | `epic_raptorq.s3o` | Titanic Roar Plasma + Swarm Birth |
| [**hive_spire.md**](file:///E:/Games/FAFMods/raptorsToPort/hive_spire.md) | `XRA0107` / `XRA0108` | T1/T2 | Factory Nest & Defense Spire | `raptor_hive.s3o`, `raptor_turrets_v2.s3o` | Organic Unit Factory / Acid PD |

---

## 2. Universal Porting Pipeline & Technical Rules

Every unit port must strictly adhere to the following architecture established during the Swarmer and Flyer development:

### A. 3D Model Conversion (`.s3o` -> `.scm`)
1. **Bone Hierarchy**:
   * Root bone must always be Bone 0 with parent index `-1`.
   * Never bind multiple non-child bones with mismatched parent indexes.
2. **Vertex Weights**:
   * S3O files have rigid bone assignments. When exporting to SCM, write 1 weight (`1.0`) per vertex matching its parent bone index.
3. **Materials**:
   * Use shader `Insect` or `Unit` in `Display.Mesh.LODs[1].ShaderName`.
   * Pack Team Color / Specular map into the Alpha channel of `_SpecTeam.dds`.

### B. Animation Synthesis (`.sca`)
1. **Root Bone Coordinate Rule (CRITICAL)**:
   * **Frame 0 of Bone 0 (Root)** MUST contain identity translation and rotation:
     `px = 0.0, py = 0.0, pz = 0.0, qw = 1.0, qx = 0.0, qy = 0.0, qz = 0.0`.
   * If frame 0 root coordinates are non-zero, the animation will violently glitch or freeze the unit's position.
2. **Gait Symmetry**:
   * 4-legged units: Diagonal gait (FL+RR, then FR+RL).
   * 6-legged units: Alternating tripod gait (L1+R2+L3, then R1+L2+R3).
   * Air units: Continuous sinusoidal wing flap (rate 2.0 to 2.5) loaded via `CreateAnimator(self):PlayAnim(...)`.

### C. Microsoft XACT Audio Pipeline (`.xwb` + `.xsb`)
Microsoft's XACT audio engine (`xactengine3_0.dll` in SysWOW64) enforces strict binary integrity:

1. **Duration & Segment Alignment (`.xwb`)**:
   * `dwFlagsAndDuration` in segment 1 must pack the sample count in the upper 28 bits:
     `dwFlagsAndDuration = (num_samples << 4) & 0xFFFFFFFF`.
   * Segment 4 (PCM audio data) must be padded to a 4-byte boundary.
2. **FCS16 Checksum Rule (`.xsb`)**:
   * Offset `0x08` contains a 16-bit CCITT CRC checksum (reversed polynomial `0x8408`, initial value `0xFFFF`, bit-inverted output).
   * The CRC must be computed dynamically over `sb[18:]`. Any single modified byte without recalculating this CRC will cause `IXACT3Engine::CreateSoundBank` to reject the bank with `warning: Error loading soundbank: Invalid data`.
3. **One-Shot vs Looping (`loopCount`)**:
   * Offset `229` in the sound event block stores `loopCount`.
   * **Must be set to `0x00` (`0`) for one-shot sounds** (attacks, screams, explosions). A value of `0xFF` (`255`) denotes **infinite looping**, causing the sound to repeat indefinitely.
4. **Cue Hash Table Resolution**:
   * Map all 16 hash buckets at offset 239 to `0x0000` (pointing to Cue 0).
   * Any lookup query (`Attack`, `Death`, `Silence`) immediately resolves to the sound regardless of cue string hashing.
5. **Silent Biological Gait**:
   * Omit `AmbientMove`, `Landing`, `TakeOff`, and engine loops to ensure completely silent movement without robotic Cybran or mechanical jet hums.

### D. Biological Gore & Bloody Death Particles
All raptor units use the custom biological particle emitters in `/mods/RaptorFaction/effects/emitters/`:
* `raptor_blood_spray_01_emit.bp` (High-velocity liquid blood bursts with downward gravity arc).
* `raptor_flesh_chunks_01_emit.bp` (Flying organic flesh and gore chunks with 3D tumble).
* `raptor_blood_cloud_01_emit.bp` (Expanding crimson biological mist/cloud).

#### Script Integration
In every raptor `_script.lua`:
```lua
OnKilled = function(self, instigator, type, overkillRatio)
    local army = self.Army
    for _, emit in BloodDeathEffects do
        CreateEmitterAtEntity(self, army, emit):ScaleEmitter(self.BloodScale or 1.0)
    end
    BaseClass.OnKilled(self, instigator, type, overkillRatio)
end,

CreateDestructionEffects = function(self, overKillRatio)
    local army = self.Army
    local scale = (self.BloodScale or 1.0) * (1 + (overKillRatio or 0) * 0.5)
    for _, emit in BloodDeathEffects do
        CreateEmitterAtEntity(self, army, emit):ScaleEmitter(scale)
    end
end,
```

### E. Multiplayer & Engine Stability Checklist
* **`VISIBLETORECON`**: Mandatory category on every unit; without it, enemy radar sees only an un-identified blip and the 3D model will never render.
* **`LODCutoff = 250` or `260`**: Prevents single-LOD custom models from disappearing when zooming out.
* **`DeathImpact` Weapon**: Mandatory on all air units (`DisplayName = 'Air Crash'`); prevents engine crash when dying aircraft collide with the ground.
* **Strategic Icons**: Render 256x256 uncompressed 32-bit BGRA DDS icons with 9 mipmap levels (`flags = 0x41`, size = 349,652 bytes).
