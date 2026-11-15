import os
import io
import zipfile
import numpy as np
from PIL import Image

print("=== Implementing Visceral Crimson / Blood-Plasma Red Raptor Shield ===")

MOD_DIR = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
WORKSPACE_DIR = r"E:\Games\FAFMods"
EXPORT_ZIP = r"E:\Games\FAFMods\exports\RaptorFaction.zip"
EFFECTS_NMD = r"C:\ProgramData\FAForever\gamedata\effects.nmd"
EFFECTS_SCD = r"P:\SteamLibrary\steamapps\common\Supreme Commander Forged Alliance\gamedata\effects.scd"

# Destination directories
mod_entity_dir = os.path.join(MOD_DIR, "effects", "entities", "RaptorShield01")
ws_entity_dir = os.path.join(WORKSPACE_DIR, "effects", "entities", "RaptorShield01")
mod_emit_dir = os.path.join(MOD_DIR, "effects", "emitters")
ws_emit_dir = os.path.join(WORKSPACE_DIR, "effects", "emitters")
mod_hook_dir = os.path.join(MOD_DIR, "hook", "lua")
ws_hook_dir = os.path.join(WORKSPACE_DIR, "hook", "lua")

for d in [mod_entity_dir, ws_entity_dir, mod_emit_dir, ws_emit_dir, mod_hook_dir, ws_hook_dir]:
    os.makedirs(d, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. GENERATE VISCERAL CRIMSON / BLOOD-PLASMA RED ALBEDO TEXTURE
# ---------------------------------------------------------------------------
print("\n[1/5] Generating RaptorShield01_Albedo.dds (Visceral Crimson Blood-Plasma)...")

# Load template intensity from effects.nmd Shield05
with zipfile.ZipFile(EFFECTS_NMD) as z:
    nomad_img = Image.open(io.BytesIO(z.read("effects/Entities/Shield05/Shield05_Albedo.dds")))
    sec_bytes = z.read("effects/Entities/Shield05/Shield05_Secondary.dds")
    spec_bytes = z.read("effects/Entities/Shield05/Shield05_Specular.dds")
    nomad_arr = np.array(nomad_img, dtype=float)

intensity = nomad_arr[:, :, 0] / 255.0
h, w = intensity.shape
y, x = np.ogrid[:h, :w]

# Bio-vascular plasma wave modulation
wave1 = np.sin(x * 0.16 + np.sin(y * 0.08) * 2.5) * 0.06
wave2 = np.cos(y * 0.18 + np.cos(x * 0.14) * 2.5) * 0.06
mod = np.clip(intensity + wave1 + wave2, 0.20, 1.0)

# Build Blood-Plasma Red channels
# R: 65 (deep translucent arterial wine) -> 255 (radiant plasma crimson)
r = np.clip(mod * 255.0, 60, 255).astype(np.uint8)
# G: 0 in body, 25-40 in core plasma hot spots (flaring bio-heat)
g = np.clip(np.maximum(mod - 0.82, 0) / 0.18 * 35.0, 0, 35).astype(np.uint8)
# B: 10 -> 32 (deep blood warmth, prevents synthetic pure-red look)
b = np.clip(10.0 + mod * 20.0, 10, 32).astype(np.uint8)
a = np.full((h, w), 255, dtype=np.uint8)

crimson_arr = np.dstack([r, g, b, a])
crimson_img = Image.fromarray(crimson_arr, "RGBA")

buf_albedo = io.BytesIO()
crimson_img.save(buf_albedo, format="DDS", pixel_format="DXT3")
albedo_bytes = buf_albedo.getvalue()

# Save textures to both mod and workspace
for dest_dir in [mod_entity_dir, ws_entity_dir]:
    with open(os.path.join(dest_dir, "RaptorShield01_Albedo.dds"), "wb") as f:
        f.write(albedo_bytes)
    with open(os.path.join(dest_dir, "RaptorShield01_Secondary.dds"), "wb") as f:
        f.write(sec_bytes)
    with open(os.path.join(dest_dir, "RaptorShield01_Specular.dds"), "wb") as f:
        f.write(spec_bytes)

print(f"  -> Generated {len(albedo_bytes)} byte DXT3 Albedo texture and bundled Secondary + Specular maps.")

# ---------------------------------------------------------------------------
# 2. WRITE RAPTOR SHIELD MESH BLUEPRINT
# ---------------------------------------------------------------------------
print("\n[2/5] Creating RaptorShield01_mesh.bp...")

mesh_bp_content = """MeshBlueprint {
    IconFadeInZoom = 4,
    LODs = {
        {
            MeshName = '/effects/Entities/Sphere01/Sphere01_lod0.scm',
            AlbedoName = '/mods/RaptorFaction/effects/entities/RaptorShield01/RaptorShield01_Albedo.dds',
            SecondaryName = '/mods/RaptorFaction/effects/entities/RaptorShield01/RaptorShield01_Secondary.dds',
            SpecularName = '/mods/RaptorFaction/effects/entities/RaptorShield01/RaptorShield01_Specular.dds',
            ShaderName = 'ShieldNomads',
            LODCutoff = 1000,
        },
    },
    SortOrder = 1000,
    StraddleWater = true,
}
"""

for dest_dir in [mod_entity_dir, ws_entity_dir]:
    with open(os.path.join(dest_dir, "RaptorShield01_mesh.bp"), "w", encoding="utf-8") as f:
        f.write(mesh_bp_content)

print("  -> RaptorShield01_mesh.bp written successfully.")

# ---------------------------------------------------------------------------
# 3. CREATE CUSTOM RAPTOR SHIELD IMPACT EMITTER & HOOK
# ---------------------------------------------------------------------------
print("\n[3/5] Creating RaptorShieldHit01 impact emitter & EffectTemplates hook...")

impact_emit_content = """EmitterBlueprint {
    BlueprintId = 'raptor_shield_impact_01',
    Lifetime = 3.50,
    Repeattime = 3.50,
    TextureFramecount = 1.00,
    Blendmode = 3.00,
    LocalVelocity = true,
    LocalAcceleration = false,
    Gravity = false,
    AlignRotation = false,
    AlignToBone = false,
    Flat = false,
    LODCutoff = 250.00,
    EmitIfVisible = true,
    CatchupEmit = true,
    CreateIfVisible = false,
    SnapToWaterline = true,
    OnlyEmitOnWater = false,
    ParticleResistance = true,
    InterpolateEmission = true,
    TextureStripcount = 1.00,
    SortOrder = 0.00,
    LowFidelity = true,
    MedFidelity = true,
    HighFidelity = true,
    Texture = '/textures/particles/flare_lens_add_01.dds',
    RampTexture = '/textures/particles/ramp_red_01.dds',
    XDirectionCurve = {
        XRange = 4.00,
        Keys = {
            { x=2.021, y=0.000, z=0.850 },
        },
    },
    YDirectionCurve = {
        XRange = 4.00,
        Keys = {
            { x=2.016, y=0.000, z=0.850 },
        },
    },
    ZDirectionCurve = {
        XRange = 4.00,
        Keys = {
            { x=1.963, y=0.170, z=0.200 },
        },
    },
    EmitRateCurve = {
        XRange = 4.00,
        Keys = {
            { x=0.000, y=20.000, z=0.000 },
            { x=3.974, y=1.921, z=0.000 },
        },
    },
    LifetimeCurve = {
        XRange = 4.00,
        Keys = {
            { x=2.005, y=11.429, z=10.000 },
        },
    },
    VelocityCurve = {
        XRange = 4.00,
        Keys = {
            { x=2.005, y=1.333, z=0.000 },
        },
    },
    ResistanceCurve = {
        XRange = 4.00,
        Keys = {
            { x=2.069, y=0.329, z=0.050 },
        },
    },
    StartSizeCurve = {
        XRange = 4.00,
        Keys = {
            { x=1.989, y=0.150, z=0.000 },
        },
    },
    EndSizeCurve = {
        XRange = 4.00,
        Keys = {
            { x=2.042, y=0.000, z=0.120 },
        },
    },
    InitialRotationCurve = {
        XRange = 4.00,
        Keys = {
            { x=2.000, y=180.000, z=360.000 },
        },
    },
    RotationRateCurve = {
        XRange = 4.00,
        Keys = {
            { x=2.000, y=0.000, z=10.000 },
        },
    },
}
"""

for dest_dir in [mod_emit_dir, ws_emit_dir]:
    with open(os.path.join(dest_dir, "raptor_shield_impact_01_emit.bp"), "w", encoding="utf-8") as f:
        f.write(impact_emit_content)

hook_effect_templates = """-- Hook EffectTemplates for Raptor Faction
RaptorShieldHit01 = {
    '/mods/RaptorFaction/effects/emitters/raptor_shield_impact_01_emit.bp',
}
"""

for dest_dir in [mod_hook_dir, ws_hook_dir]:
    hook_file = os.path.join(dest_dir, "EffectTemplates.lua")
    if os.path.exists(hook_file):
        with open(hook_file, "r", encoding="utf-8") as f:
            existing = f.read()
        if "RaptorShieldHit01" not in existing:
            with open(hook_file, "a", encoding="utf-8") as f:
                f.write("\n" + hook_effect_templates)
    else:
        with open(hook_file, "w", encoding="utf-8") as f:
            f.write(hook_effect_templates)

print("  -> Created raptor_shield_impact_01_emit.bp and hooked EffectTemplates.lua.")

# ---------------------------------------------------------------------------
# 4. UPDATE UNIT BLUEPRINTS & BUILD SCRIPTS
# ---------------------------------------------------------------------------
print("\n[4/5] Updating Raptor shield unit blueprints (XRA0225, XRA0226, XRA0328)...")

units_to_update = ["XRA0225", "XRA0226", "XRA0328"]
old_mesh = "/effects/entities/CybranShield01/CybranShield01_mesh"
new_mesh = "/mods/RaptorFaction/effects/entities/RaptorShield01/RaptorShield01_mesh"

for uid in units_to_update:
    bp_path = os.path.join(MOD_DIR, "units", uid, f"{uid}_unit.bp")
    if os.path.exists(bp_path):
        with open(bp_path, "r", encoding="utf-8") as f:
            bp_text = f.read()
        
        # Replace Mesh and ImpactEffects
        bp_text = bp_text.replace(old_mesh, new_mesh)
        bp_text = bp_text.replace("ImpactEffects = 'CybranShieldHit01'", "ImpactEffects = 'RaptorShieldHit01'")
        
        with open(bp_path, "w", encoding="utf-8") as f:
            f.write(bp_text)
        print(f"  -> Updated {uid}_unit.bp with RaptorShield01 mesh and RaptorShieldHit01 impact.")

# Update import_zerok_models.py
zk_py = os.path.join(WORKSPACE_DIR, "import_zerok_models.py")
if os.path.exists(zk_py):
    with open(zk_py, "r", encoding="utf-8") as f:
        zk_text = f.read()
    
    zk_text = zk_text.replace("ImpactEffects = 'CybranShieldHit01',", "ImpactEffects = 'RaptorShieldHit01',")
    zk_text = zk_text.replace(old_mesh, new_mesh)
    
    with open(zk_py, "w", encoding="utf-8") as f:
        f.write(zk_text)
    print("  -> Updated import_zerok_models.py")

# ---------------------------------------------------------------------------
# 5. RE-PACKAGE EXPORT ZIP
# ---------------------------------------------------------------------------
print(f"\n[5/5] Re-packaging updated mod archive to {EXPORT_ZIP}...")
os.makedirs(os.path.dirname(EXPORT_ZIP), exist_ok=True)
with zipfile.ZipFile(EXPORT_ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(MOD_DIR):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(MOD_DIR))
            z.write(full_path, rel_path)

print(f"  -> Updated export zip: {os.path.getsize(EXPORT_ZIP) / (1024*1024):.2f} MB")
print("\nSUCCESS: Visceral Crimson / Blood-Plasma Red shield system fully installed and packaged!")
