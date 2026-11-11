import os
import gzip
import struct
import io
import math
import zipfile
from PIL import Image
import numpy as np

# ---------------------------------------------------------------------------
# Directories & Setup
# ---------------------------------------------------------------------------
mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
decal_dir = os.path.join(mod_dir, "env", "decals")
emit_dir = os.path.join(mod_dir, "effects", "emitters")
lua_dir = os.path.join(mod_dir, "lua")
units_dir = os.path.join(mod_dir, "units")
export_zip = os.path.join(os.path.dirname(__file__), "exports", "RaptorFaction.zip")

for d in [decal_dir, emit_dir, lua_dir]:
    os.makedirs(d, exist_ok=True)

# ---------------------------------------------------------------------------
# DDS Writer with Complete Mipmap Pyramids (Ensures High-Quality Zoom-Out)
# ---------------------------------------------------------------------------
def save_bgra_dds_with_mipmaps(pil_img, filepath):
    img = pil_img.convert('RGBA')
    w, h = img.size
    levels = []
    curr = img
    while True:
        levels.append(curr)
        cw, ch = curr.size
        if cw == 1 and ch == 1:
            break
        nw = max(1, cw // 2)
        nh = max(1, ch // 2)
        curr = curr.resize((nw, nh), Image.Resampling.LANCZOS)
    
    num_mips = len(levels)
    header = bytearray(128)
    header[0:4] = b'DDS '
    struct.pack_into('<I', header, 4, 124)           # dwSize
    struct.pack_into('<I', header, 8, 0x2100F)       # dwFlags: CAPS|HEIGHT|WIDTH|PITCH|PIXELFORMAT|MIPMAPCOUNT
    struct.pack_into('<I', header, 12, h)            # dwHeight
    struct.pack_into('<I', header, 16, w)            # dwWidth
    struct.pack_into('<I', header, 20, w * 4)        # dwPitchOrLinearSize
    struct.pack_into('<I', header, 28, num_mips)     # dwMipMapCount
    
    # DDS_PIXELFORMAT (32 bytes at offset 76)
    pf_off = 76
    struct.pack_into('<IIIIIIII', header, pf_off, 32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    struct.pack_into('<I', header, 108, 0x401008)    # dwCaps: COMPLEX|TEXTURE|MIPMAP
    
    with open(filepath, 'wb') as f:
        f.write(header)
        for lvl in levels:
            arr = np.array(lvl, dtype=np.uint8)
            bgra = np.zeros_like(arr)
            bgra[:, :, 0] = arr[:, :, 2] # B
            bgra[:, :, 1] = arr[:, :, 1] # G
            bgra[:, :, 2] = arr[:, :, 0] # R
            bgra[:, :, 3] = arr[:, :, 3] # A
            f.write(bgra.tobytes())

# ---------------------------------------------------------------------------
# 1. BAR Package Indexing
# ---------------------------------------------------------------------------
print("Indexing BAR package...")
pkg = r'P:\Games\Beyond-All-Reason\data\packages\ad33f718d83a34e194d7182194a91ede.sdp'
with gzip.open(pkg, 'rb') as gz:
    pkg_data = gz.read()

entries = {}
pos = 0
while pos < len(pkg_data):
    namelen = pkg_data[pos]
    pos += 1
    name = pkg_data[pos:pos+namelen].decode('utf-8', 'ignore')
    pos += namelen
    md5_bytes = pkg_data[pos:pos+16]
    pos += 16
    crc = struct.unpack('<I', pkg_data[pos:pos+4])[0]
    pos += 4
    size = struct.unpack('>I', pkg_data[pos:pos+4])[0]
    pos += 4
    entries[name.lower().replace('\\', '/')] = (md5_bytes.hex(), size)

def get_bar_file(relpath):
    k = relpath.lower().replace('\\', '/')
    if k in entries:
        md5_hex, size = entries[k]
        sub = md5_hex[:2]
        fn = md5_hex[2:] + '.gz'
        p = os.path.join(r'P:\Games\Beyond-All-Reason\data\pool', sub, fn)
        with gzip.open(p, 'rb') as gz:
            return gz.read()
    return None

print(f"BAR package indexed ({len(entries)} files).")

# ---------------------------------------------------------------------------
# 2. Extract & Convert BAR Scum Textures to High-Visibility FAF Decals
# ---------------------------------------------------------------------------
print("Processing BAR Scum textures with organic tendrils and strategic zoom visibility...")
raw_albedo = get_bar_file('luaui/images/raptor_scum/alien_guts_colorheight.dds')
img_albedo = Image.open(io.BytesIO(raw_albedo)).resize((1024, 1024), Image.Resampling.LANCZOS)
r_a, g_a, b_a, h_a = img_albedo.split()

arr_r = np.array(r_a, dtype=np.float32)
arr_g = np.array(g_a, dtype=np.float32)
arr_b = np.array(b_a, dtype=np.float32)
arr_h = np.array(h_a, dtype=np.float32) / 255.0

# Boost biological crimson/purple saturation so it stands out strongly from orbital zoom
arr_r = np.clip(arr_r * 1.25, 0, 255)
arr_g = np.clip(arr_g * 0.90, 0, 255)
arr_b = np.clip(arr_b * 1.15, 0, 255)

raw_normals = get_bar_file('luaui/images/raptor_scum/alien_guts_normalspec.dds')
img_normals = Image.open(io.BytesIO(raw_normals)).resize((1024, 1024), Image.Resampling.LANCZOS)
r_n, g_n, b_n, a_spec = img_normals.split()
arr_nx = np.array(r_n, dtype=np.uint8) # Tangent Normal X
arr_ny = np.array(g_n, dtype=np.uint8) # Tangent Normal Y

# Normalized coordinates: center = (511.5, 511.5), 0 at center, 1.0 at quad mid-edges
y, x = np.ogrid[:1024, :1024]
cx, cy = 511.5, 511.5
dx = (x - cx) / 512.0
dy = (y - cy) / 512.0
dist = np.sqrt(dx**2 + dy**2)
angle = np.arctan2(dy, dx)

# Multi-harmonic organic lobes (spidering tendril fingers)
lobe1 = np.sin(angle * 5.0 + 0.4) * 0.08
lobe2 = np.cos(angle * 8.0 - 1.2) * 0.05
lobe3 = np.sin(angle * 14.0 + 1.8) * 0.03
lobe_noise = lobe1 + lobe2 + lobe3

eff_dist = dist - lobe_noise - (arr_h - 0.5) * 0.12

# Solid central core (under the nest)
core_mask = np.clip((0.32 - dist) / 0.18, 0.0, 1.0)
core_mask = core_mask * core_mask * (3.0 - 2.0 * core_mask)

# Outer falloff: all tendrils terminate well inside 0.65
r_inner = 0.22
r_outer = 0.63
falloff = np.clip((r_outer - eff_dist) / (r_outer - r_inner), 0.0, 1.0)
smooth_falloff = falloff * falloff * (3.0 - 2.0 * falloff)

# Tissue weighting: high height veins stay prominent, crevices fade into terrain
tissue_weight = 0.50 + 0.50 * arr_h
alpha_creep = smooth_falloff * tissue_weight

# Blend core so the center is dense and punchy
final_alpha = np.maximum(alpha_creep, core_mask * 0.98)

# Absolute safety boundary: beyond dist >= 0.65, force 0.0 (wide transparent padding to quad edge at 1.0)
final_alpha = np.where(dist >= 0.65, 0.0, final_alpha)
final_alpha_u8 = np.clip(final_alpha * 255.0, 0, 255).astype(np.uint8)

# 1. Albedo: RGBA
albedo_final = Image.merge('RGBA', (
    Image.fromarray(arr_r.astype(np.uint8)),
    Image.fromarray(arr_g.astype(np.uint8)),
    Image.fromarray(arr_b.astype(np.uint8)),
    Image.fromarray(final_alpha_u8)
))

# 2. FAF Normal:
# In FAF's DecalsNormalsPS (terrain.fx):
#   blendFactor = decalRaw.r (R channel is the BLEND MASK!)
#   decalNormal.xz = decalRaw.ag * 2 - 1 (G is Normal Y, A is Normal X)
#   B is unused (0)
zeros = np.zeros_like(final_alpha_u8)
normals_final = Image.merge('RGBA', (
    Image.fromarray(final_alpha_u8), # R = Blend Mask (0 outside tendrils!)
    Image.fromarray(arr_ny),         # G = Normal Y
    Image.fromarray(zeros),          # B = 0
    Image.fromarray(arr_nx)          # A = Normal X
))

out_albedo_path = os.path.join(decal_dir, 'raptor_creep_albedo.dds')
out_normals_path = os.path.join(decal_dir, 'raptor_creep_normals.dds')
out_sub_albedo_path = os.path.join(decal_dir, 'raptor_creep_sub_albedo.dds')
out_sub_normals_path = os.path.join(decal_dir, 'raptor_creep_sub_normals.dds')

save_bgra_dds_with_mipmaps(albedo_final, out_albedo_path)
save_bgra_dds_with_mipmaps(normals_final, out_normals_path)

# Rotated variants for natural non-repeating lobe tiling
save_bgra_dds_with_mipmaps(albedo_final.rotate(72), out_sub_albedo_path)
save_bgra_dds_with_mipmaps(normals_final.rotate(72), out_sub_normals_path)

print("Organic Creep decals with full 11-level mipmaps exported successfully.")

# ---------------------------------------------------------------------------
# 3. Particle Emitters
# ---------------------------------------------------------------------------
print("Exporting creep particle emitters...")
spores_emit = """EmitterBlueprint {
    BlueprintId = 'raptor_creep_spores_01',
    Lifetime = -1.00,
    Repeattime = 1.00,
    TextureFramecount = 1.00,
    Blendmode = 1.00,
    LocalVelocity = false,
    LocalAcceleration = false,
    Gravity = false,
    AlignRotation = false,
    AlignToBone = false,
    Flat = true,
    LODCutoff = 250.00,
    EmitIfVisible = true,
    CatchupEmit = true,
    CreateIfVisible = false,
    SnapToWaterline = false,
    OnlyEmitOnWater = false,
    InterpolateEmission = true,
    TextureStripcount = 1.00,
    SortOrder = 0.00,
    Texture = '/textures/particles/cloud_smoke_alpha_03.dds',
    RampTexture = '/textures/particles/ramp_green_02.dds',
    XDirectionCurve = {
        XRange = 1.00,
        Keys = { { x=0.50, y=0.00, z=0.40 } },
    },
    YDirectionCurve = {
        XRange = 1.00,
        Keys = { { x=0.50, y=0.15, z=0.08 } },
    },
    ZDirectionCurve = {
        XRange = 1.00,
        Keys = { { x=0.50, y=0.00, z=0.40 } },
    },
    EmitRateCurve = {
        XRange = 1.00,
        Keys = { { x=0.00, y=3.00, z=0.00 }, { x=1.00, y=3.00, z=0.00 } },
    },
    LifetimeCurve = {
        XRange = 1.00,
        Keys = { { x=0.50, y=3.20, z=0.50 } },
    },
    VelocityCurve = {
        XRange = 1.00,
        Keys = { { x=0.20, y=0.40, z=0.10 }, { x=0.80, y=0.15, z=0.05 } },
    },
    SizeCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.00, y=1.20, z=0.20 },
            { x=0.50, y=2.80, z=0.40 },
            { x=1.00, y=3.50, z=0.30 },
        },
    },
    StartSize = 1.50,
    EndSize = 4.00,
}
"""
with open(os.path.join(emit_dir, 'raptor_creep_spores_01_emit.bp'), 'w', encoding='utf-8') as f:
    f.write(spores_emit)

bubbles_emit = """EmitterBlueprint {
    BlueprintId = 'raptor_creep_bubbles_01',
    Lifetime = -1.00,
    Repeattime = 1.00,
    TextureFramecount = 16.00,
    Blendmode = 0.00,
    LocalVelocity = false,
    LocalAcceleration = false,
    Gravity = false,
    AlignRotation = false,
    AlignToBone = false,
    Flat = true,
    LODCutoff = 200.00,
    EmitIfVisible = true,
    CatchupEmit = true,
    CreateIfVisible = false,
    SnapToWaterline = false,
    OnlyEmitOnWater = false,
    InterpolateEmission = false,
    TextureStripcount = 4.00,
    SortOrder = 0.00,
    Texture = '/textures/particles/mudpot_bubble_anim_01.dds',
    RampTexture = '/textures/particles/ramp_green_02.dds',
    XDirectionCurve = {
        XRange = 1.00,
        Keys = { { x=0.50, y=0.00, z=0.20 } },
    },
    YDirectionCurve = {
        XRange = 1.00,
        Keys = { { x=0.50, y=0.05, z=0.02 } },
    },
    ZDirectionCurve = {
        XRange = 1.00,
        Keys = { { x=0.50, y=0.00, z=0.20 } },
    },
    EmitRateCurve = {
        XRange = 1.00,
        Keys = { { x=0.00, y=1.50, z=0.00 }, { x=1.00, y=1.50, z=0.00 } },
    },
    LifetimeCurve = {
        XRange = 1.00,
        Keys = { { x=0.50, y=1.40, z=0.20 } },
    },
    VelocityCurve = {
        XRange = 1.00,
        Keys = { { x=0.50, y=0.05, z=0.02 } },
    },
    SizeCurve = {
        XRange = 1.00,
        Keys = {
            { x=0.00, y=0.60, z=0.10 },
            { x=0.50, y=1.20, z=0.20 },
            { x=1.00, y=1.60, z=0.20 },
        },
    },
    StartSize = 0.80,
    EndSize = 1.80,
}
"""
with open(os.path.join(emit_dir, 'raptor_creep_bubbles_01_emit.bp'), 'w', encoding='utf-8') as f:
    f.write(bubbles_emit)

heal_burst_emit = """EmitterBlueprint {
    BlueprintId = 'raptor_bio_heal_burst_01',
    Lifetime = 1.20,
    Repeattime = 1.20,
    TextureFramecount = 16.00,
    Blendmode = 0.00,
    LocalVelocity = false,
    LocalAcceleration = false,
    Gravity = false,
    AlignRotation = false,
    AlignToBone = false,
    Flat = true,
    LODCutoff = 200.00,
    EmitIfVisible = true,
    CatchupEmit = true,
    CreateIfVisible = false,
    SnapToWaterline = false,
    OnlyEmitOnWater = false,
    InterpolateEmission = false,
    TextureStripcount = 4.00,
    SortOrder = 0.00,
    Texture = '/textures/particles/mudpot_bubble_anim_01.dds',
    RampTexture = '/textures/particles/ramp_green_02.dds',
    XDirectionCurve = {
        XRange = 1.20,
        Keys = { { x=0.50, y=0.00, z=0.20 } },
    },
    YDirectionCurve = {
        XRange = 1.20,
        Keys = { { x=0.50, y=0.10, z=0.05 } },
    },
    ZDirectionCurve = {
        XRange = 1.20,
        Keys = { { x=0.50, y=0.00, z=0.20 } },
    },
    EmitRateCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.10, y=4.00, z=0.00 },
            { x=0.60, y=0.00, z=0.00 },
        },
    },
    LifetimeCurve = {
        XRange = 1.20,
        Keys = { { x=0.50, y=0.80, z=0.10 } },
    },
    VelocityCurve = {
        XRange = 1.20,
        Keys = { { x=0.50, y=0.05, z=0.02 } },
    },
    SizeCurve = {
        XRange = 1.20,
        Keys = {
            { x=0.00, y=0.60, z=0.10 },
            { x=0.50, y=1.20, z=0.20 },
            { x=1.00, y=1.60, z=0.20 },
        },
    },
    StartSize = 0.60,
    EndSize = 1.40,
}
"""
with open(os.path.join(emit_dir, 'raptor_bio_heal_burst_01_emit.bp'), 'w', encoding='utf-8') as f:
    f.write(heal_burst_emit)

print("Particle emitters exported.")

# ---------------------------------------------------------------------------
# 4. Packaging
# ---------------------------------------------------------------------------
print(f"Packaging updated mod to {export_zip}...")
with zipfile.ZipFile(export_zip, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(mod_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(mod_dir))
            z.write(full_path, rel_path)

print(f"RAPTOR CREEP PORT COMPLETED SUCCESSFULLY! ({os.path.getsize(export_zip)} bytes)")
