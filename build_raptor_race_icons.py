"""
Deploy Authentic Raptor Race & Faction Icons
============================================
Replaces legacy Seraphim placeholders across all UI textures with the authentic,
high-resolution biological Raptor Swarm race emblem (both color and alpha masks),
and updates the HUD Telemetry status panel badge.

Deploys to:
- e:/Games/FAFMods/
- Documents/My Games/Gas Powered Games/Supreme Commander Forged Alliance/mods/RaptorFaction/
"""

import os
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageFilter

REPO_ROOT = Path(r"e:\Games\FAFMods")
MOD_ROOT = Path(os.path.expanduser("~")) / "Documents" / "My Games" / "Gas Powered Games" / "Supreme Commander Forged Alliance" / "mods" / "RaptorFaction"

def generate_and_deploy_icons():
    print("=" * 70)
    print("GENERATING AUTHENTIC RAPTOR RACE & FACTION ICONS")
    print("=" * 70)

    # 1. Load source images
    inv = Image.open(REPO_ROOT / "test_inverted_raptor.png").convert("RGBA")
    orig = Image.open(REPO_ROOT / "test_raptor.png").convert("RGBA")

    inv_arr = np.array(inv, dtype=np.float32)
    orig_arr = np.array(orig, dtype=np.float32)

    # 2. Build White Alpha Silhouette (for widgets/faction-icons-alpha_bmp)
    alpha_raw = inv_arr[:, :, 3]
    gray_raw = orig_arr[:, :, 0]

    alpha_icon = np.zeros((128, 128, 4), dtype=np.uint8)
    alpha_icon[:, :, :3] = 255 # Pure white
    groove_alpha = np.clip((gray_raw - 45) / 140.0, 0, 1) * (alpha_raw / 255.0) * 255.0
    alpha_icon[:, :, 3] = groove_alpha.astype(np.uint8)
    alpha_mask_master = Image.fromarray(alpha_icon, "RGBA")

    # 3. Build High-Res Master Color Emblem
    c_arr = np.zeros_like(inv_arr)
    mask = inv_arr[:, :, 3] > 10

    # Crimson gradient for carapace plates
    y_grad = np.linspace(0.85, 1.25, 128)[:, None]
    c_arr[:, :, 0] = np.clip(220 * y_grad, 0, 255)
    c_arr[:, :, 1] = np.clip(28 * y_grad, 0, 255)
    c_arr[:, :, 2] = np.clip(14 * y_grad, 0, 255)

    # Fiery golden/amber glowing seam edges
    edge_mask = inv_arr[:, :, 0] > 140
    c_arr[edge_mask, 0] = 255
    c_arr[edge_mask, 1] = 160
    c_arr[edge_mask, 2] = 20

    # Mandible tips bio-glow gradient
    for y in range(80, 128):
        for x in range(35, 93):
            if mask[y, x] and orig_arr[y, x, 0] > 150:
                factor = (y - 80) / 48.0
                c_arr[y, x, 0] = np.clip(c_arr[y, x, 0] * (1 - factor) + 255 * factor, 0, 255)
                c_arr[y, x, 1] = np.clip(c_arr[y, x, 1] * (1 - factor) + 120 * factor, 0, 255)
                c_arr[y, x, 2] = np.clip(c_arr[y, x, 2] * (1 - factor) + 10 * factor, 0, 255)

    # Dark chitin outline
    gap_mask = (orig_arr[:, :, 0] < 55) & mask
    c_arr[gap_mask, 0] = 45
    c_arr[gap_mask, 1] = 8
    c_arr[gap_mask, 2] = 8

    c_arr[:, :, 3] = inv_arr[:, :, 3]
    color_master = Image.fromarray(c_arr.astype(np.uint8), "RGBA")

    # 4. Inpaint and Update Raptor HUD Status Panel
    panel_path = REPO_ROOT / "textures" / "ui" / "common" / "raptors" / "raptorpanel.png"
    panel = Image.open(panel_path).convert("RGBA")
    p_arr = np.array(panel)

    # Create mask for yellow Seraphim logo
    s_mask = np.zeros((p_arr.shape[0], p_arr.shape[1]), dtype=np.uint8)
    for y in range(310, 395):
        for x in range(25, 110):
            r, g, b, a = p_arr[y, x]
            if r > 110 and g > 90 and b < 170 and (r > b + 25) and (g > b + 15):
                s_mask[y, x] = 255

    s_kernel = np.ones((3, 3), np.uint8)
    s_mask = cv2.dilate(s_mask, s_kernel, iterations=2)
    inpainted_rgb = cv2.inpaint(p_arr[:, :, :3], s_mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)
    p_arr[:, :, :3] = inpainted_rgb
    updated_panel = Image.fromarray(p_arr, "RGBA")

    # Add glowing Raptor emblem to badge
    emblem_56 = color_master.resize((56, 56), Image.Resampling.LANCZOS)
    glow_arr = np.array(emblem_56)
    glow_arr[:, :, 0] = 255
    glow_arr[:, :, 1] = 60
    glow_arr[:, :, 2] = 20
    glow_arr[:, :, 3] = (glow_arr[:, :, 3] * 0.75).astype(np.uint8)
    glow_img = Image.fromarray(glow_arr, "RGBA").filter(ImageFilter.GaussianBlur(3))

    glow_canvas = Image.new("RGBA", (68, 68), (0, 0, 0, 0))
    glow_canvas.paste(glow_img, (6, 6), glow_img)

    cx, cy = 64, 354
    updated_panel.paste(glow_canvas, (cx - 34, cy - 34), glow_canvas)
    updated_panel.paste(emblem_56, (cx - 28, cy - 28), emblem_56)

    # 5. List of targets to generate
    # Format: (relative_path_without_ext, image_obj, target_size)
    deploy_list = [
        # HUD Panel
        ("textures/ui/common/raptors/raptorpanel", updated_panel, (600, 420)),

        # Alpha Widget Icons (for unitview and UI tinting)
        ("textures/ui/common/widgets/faction-icons-alpha_bmp/raptor_ico", alpha_mask_master, (24, 24)),

        # Large Faction Icons (64x64)
        ("textures/ui/common/faction_icon-lg/raptor_ico", color_master, (64, 64)),
        ("textures/ui/common/faction_icon-lg/raptor_med", color_master, (64, 64)),
        ("textures/ui/common/faction_icon-lg/raptor_mini", color_master, (64, 64)),
        ("textures/ui/common/faction_icon-lg/raptor_thick", color_master, (64, 64)),

        # Small Faction Icons (18x18 & 24x24)
        ("textures/ui/common/faction_icon-sm/raptor_ico", color_master, (18, 18)),
        ("textures/ui/common/dialogs/faction_ico/raptor_ico", color_master, (24, 24)),
        ("textures/ui/common/lobby/raptor_ico", color_master, (24, 24)),

        # Veteran Logo (16x16)
        ("textures/ui/common/game/veteran-logo_bmp/raptor-veteran_bmp", color_master, (16, 16)),

        # Mod Icon & Web Assets
        ("icon", color_master, (64, 64)),
        ("static/img/raptor_ico", color_master, (64, 64)),
    ]

    dest_roots = [REPO_ROOT, MOD_ROOT]

    for rel_base, src_img, size in deploy_list:
        scaled = src_img.resize(size, Image.Resampling.LANCZOS)
        for root in dest_roots:
            p_png = root / f"{rel_base}.png"
            p_dds = root / f"{rel_base}.dds"
            p_png.parent.mkdir(parents=True, exist_ok=True)

            scaled.save(str(p_png), format="PNG")
            # Only save DDS if it's in textures/
            if "textures" in rel_base:
                scaled.save(str(p_dds), format="DDS")
            print(f"Deployed: {p_png.relative_to(root)} ({size[0]}x{size[1]})")

    print("\nALL RAPTOR FACTION ICONS AND HUD BADGE DEPLOYED SUCCESSFULLY!")

if __name__ == "__main__":
    generate_and_deploy_icons()
