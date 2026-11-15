"""
Build & Deploy Custom Raptor Strategic Icons for FAF
Generates crisp, team-colorable 4-state DDS icons and updates all 64 Raptor unit blueprints.
Includes distinct silhouettes for:
- Gestation Hives (Factories) vs Point Defense (PD Spires)
- Air Fighters / AA Flier vs Air Bombers vs Air Scouts vs Gunships
"""

import os
import re
import glob
from PIL import Image, ImageDraw

MOD_DIR = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
ICONS_DIR = os.path.join(MOD_DIR, "custom-strategic-icons")
UNITS_DIR = os.path.join(MOD_DIR, "units")

os.makedirs(ICONS_DIR, exist_ok=True)

# Supreme Commander Strategic Icon Color Standards:
# Grey (128, 128, 128) is multiplied by Army Color in the engine shader.
COLOR_GREY = (128, 128, 128, 255)
COLOR_GREY_HOVER = (210, 210, 210, 255)
COLOR_BLACK = (0, 0, 0, 255)
COLOR_WHITE = (255, 255, 255, 255)
COLOR_TRANS = (0, 0, 0, 0)

# Icon dimensions:
# Rest & Over: 20 x 20
# Selected & SelectedOver: 24 x 24 (provides 2px margin for tactical selection corners)
SIZE_REST = (20, 20)
SIZE_SEL = (24, 24)


def draw_chitin_diamond(d, cx, cy, r, fill, outline, stroke_w=1):
    pts = [
        (cx, cy - r),
        (cx + int(r * 0.55), cy - int(r * 0.45)),
        (cx + int(r * 0.85), cy),
        (cx + int(r * 0.55), cy + int(r * 0.45)),
        (cx, cy + r),
        (cx - int(r * 0.55), cy + int(r * 0.45)),
        (cx - int(r * 0.85), cy),
        (cx - int(r * 0.55), cy - int(r * 0.45)),
    ]
    d.polygon(pts, fill=fill, outline=outline)
    for i in range(len(pts)):
        d.line([pts[i], pts[(i + 1) % len(pts)]], fill=outline, width=stroke_w)


def draw_air_wings(d, cx, cy, r, fill, outline, stroke_w=1):
    """Organic swept bat/pterosaur wings for aerial units"""
    pts = [
        (cx, cy + r),
        (cx - r, cy - int(r * 0.6)),
        (cx - int(r * 0.4), cy - int(r * 0.2)),
        (cx, cy - int(r * 0.1)),
        (cx + int(r * 0.4), cy - int(r * 0.2)),
        (cx + r, cy - int(r * 0.6))
    ]
    d.polygon(pts, fill=fill, outline=outline)
    for i in range(len(pts)):
        d.line([pts[i], pts[(i + 1) % len(pts)]], fill=outline, width=stroke_w)


def draw_hive_mound(d, cx, cy, r, fill, outline, stroke_w=1):
    """Wide bulbous nesting mound for Gestation Roosts / Factories"""
    pts = [
        (cx - int(r * 1.0), cy + int(r * 0.7)),
        (cx - int(r * 0.9), cy - int(r * 0.2)),
        (cx - int(r * 0.5), cy - int(r * 0.8)),
        (cx, cy - int(r * 0.95)),
        (cx + int(r * 0.5), cy - int(r * 0.8)),
        (cx + int(r * 0.9), cy - int(r * 0.2)),
        (cx + int(r * 1.0), cy + int(r * 0.7)),
    ]
    d.polygon(pts, fill=fill, outline=outline)
    for i in range(len(pts)):
        d.line([pts[i], pts[(i + 1) % len(pts)]], fill=outline, width=stroke_w)


def draw_pd_spire(d, cx, cy, r, fill, outline, stroke_w=1):
    """Tall, slender conical obelisk / spire for Point Defense (PD)"""
    pts = [
        (cx - int(r * 0.65), cy + int(r * 0.85)),
        (cx - int(r * 0.55), cy + int(r * 0.3)),
        (cx - int(r * 0.35), cy - int(r * 0.4)),
        (cx, cy - int(r * 1.0)),
        (cx + int(r * 0.35), cy - int(r * 0.4)),
        (cx + int(r * 0.55), cy + int(r * 0.3)),
        (cx + int(r * 0.65), cy + int(r * 0.85)),
    ]
    d.polygon(pts, fill=fill, outline=outline)
    for i in range(len(pts)):
        d.line([pts[i], pts[(i + 1) % len(pts)]], fill=outline, width=stroke_w)


def draw_queen_crown(d, cx, cy, r, fill, outline, stroke_w=1):
    pts = [
        (cx, cy - r),
        (cx + int(r * 0.45), cy - int(r * 0.6)),
        (cx + int(r * 0.95), cy - int(r * 0.8)),
        (cx + int(r * 0.75), cy),
        (cx + int(r * 0.9), cy + int(r * 0.7)),
        (cx, cy + r),
        (cx - int(r * 0.9), cy + int(r * 0.7)),
        (cx - int(r * 0.75), cy),
        (cx - int(r * 0.95), cy - int(r * 0.8)),
        (cx - int(r * 0.45), cy - int(r * 0.6))
    ]
    d.polygon(pts, fill=fill, outline=outline)
    for i in range(len(pts)):
        d.line([pts[i], pts[(i + 1) % len(pts)]], fill=outline, width=stroke_w)


def render_icon_image(role, state="rest"):
    is_sel = "selected" in state
    is_hover = "over" in state

    w, h = SIZE_SEL if is_sel else SIZE_REST
    img = Image.new("RGBA", (w, h), COLOR_TRANS)
    draw = ImageDraw.Draw(img)

    cx, cy = w // 2, h // 2
    r = 8 if not is_sel else 8

    # Frame & glyph colors
    fill_col = COLOR_GREY_HOVER if is_hover else COLOR_GREY
    border_col = COLOR_WHITE if is_hover else COLOR_BLACK
    glyph_col = COLOR_WHITE if is_hover else COLOR_BLACK

    # Selection brackets
    if is_sel:
        b_col = COLOR_WHITE
        bracket_len = 3
        # Top-Left
        draw.line([(1, 1), (1 + bracket_len, 1)], fill=b_col, width=1)
        draw.line([(1, 1), (1, 1 + bracket_len)], fill=b_col, width=1)
        # Top-Right
        draw.line([(w - 2, 1), (w - 2 - bracket_len, 1)], fill=b_col, width=1)
        draw.line([(w - 2, 1), (w - 2, 1 + bracket_len)], fill=b_col, width=1)
        # Bottom-Left
        draw.line([(1, h - 2), (1 + bracket_len, h - 2)], fill=b_col, width=1)
        draw.line([(1, h - 2), (1, h - 2 - bracket_len)], fill=b_col, width=1)
        # Bottom-Right
        draw.line([(w - 2, h - 2), (w - 2 - bracket_len, h - 2)], fill=b_col, width=1)
        draw.line([(w - 2, h - 2), (w - 2, h - 2 - bracket_len)], fill=b_col, width=1)

    # 1. Base Silhouettes & Inner Glyphs

    # --- LAND UNITS ---
    if role.startswith("swarmer"):
        draw_chitin_diamond(draw, cx, cy, r, fill_col, border_col)
        # Crossed Mandibles
        draw.line([(cx - 3, cy - 4), (cx + 1, cy + 4)], fill=glyph_col, width=1)
        draw.line([(cx + 3, cy - 4), (cx - 1, cy + 4)], fill=glyph_col, width=1)
        draw.point((cx, cy), fill=glyph_col)

    elif role.startswith("kamikaze"):
        if "_air" in role:
            draw_air_wings(draw, cx, cy, r, fill_col, border_col)
        else:
            draw_chitin_diamond(draw, cx, cy, r, fill_col, border_col)
        draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=glyph_col)
        draw.point((cx, cy), fill=COLOR_WHITE if not is_hover else COLOR_BLACK)
        # Blast ticks
        draw.line([(cx, cy - 6), (cx, cy - 4)], fill=glyph_col, width=1)
        draw.line([(cx, cy + 4), (cx, cy + 6)], fill=glyph_col, width=1)
        draw.line([(cx - 6, cy), (cx - 4, cy)], fill=glyph_col, width=1)
        draw.line([(cx + 4, cy), (cx + 6, cy)], fill=glyph_col, width=1)

    elif role.startswith("acid"):
        if "_struct" in role or "_t1" in role and "struct" in role:
            draw_pd_spire(draw, cx, cy, r, fill_col, border_col)
        elif "_air" in role:
            draw_air_wings(draw, cx, cy, r, fill_col, border_col)
        else:
            draw_chitin_diamond(draw, cx, cy, r, fill_col, border_col)
        draw.polygon([(cx, cy - 4), (cx + 2, cy + 1), (cx - 2, cy + 1)], fill=glyph_col)
        draw.ellipse([cx - 2, cy, cx + 2, cy + 3], fill=glyph_col)
        draw.point((cx - 3, cy + 2), fill=glyph_col)
        draw.point((cx + 3, cy + 2), fill=glyph_col)

    elif role.startswith("emp"):
        if "_struct" in role:
            draw_pd_spire(draw, cx, cy, r, fill_col, border_col)
        elif "_air" in role or "_bomber" in role:
            draw_air_wings(draw, cx, cy, r, fill_col, border_col)
        else:
            draw_chitin_diamond(draw, cx, cy, r, fill_col, border_col)
        bolt = [(cx + 1, cy - 5), (cx - 2, cy - 1), (cx, cy - 1), (cx - 1, cy + 4), (cx + 2, cy), (cx + 1, cy)]
        draw.polygon(bolt, fill=glyph_col)

    elif role.startswith("fire"):
        if "_air" in role:
            draw_air_wings(draw, cx, cy, r, fill_col, border_col)
        else:
            draw_chitin_diamond(draw, cx, cy, r, fill_col, border_col)
        flame = [(cx, cy - 5), (cx + 3, cy), (cx + 1, cy + 3), (cx - 1, cy + 3), (cx - 3, cy)]
        draw.polygon(flame, fill=glyph_col)
        draw.point((cx, cy + 1), fill=fill_col)

    elif role.startswith("spiker"):
        draw_chitin_diamond(draw, cx, cy, r, fill_col, border_col)
        draw.polygon([(cx, cy - 5), (cx + 2, cy - 1), (cx - 2, cy - 1)], fill=glyph_col)
        draw.line([(cx, cy - 1), (cx, cy + 4)], fill=glyph_col, width=1)
        draw.point((cx - 2, cy + 1), fill=glyph_col)
        draw.point((cx + 2, cy + 1), fill=glyph_col)

    # --- STRUCTURES & DEFENSE ---
    elif role.startswith("pd"):
        # POINT DEFENSE SPIRE (Direct Fire '+' Cross with center targeting pip)
        draw_pd_spire(draw, cx, cy, r, fill_col, border_col)
        draw.line([(cx, cy - 4), (cx, cy + 4)], fill=glyph_col, width=1)
        draw.line([(cx - 4, cy), (cx + 4, cy)], fill=glyph_col, width=1)
        draw.point((cx, cy), fill=COLOR_WHITE if not is_hover else COLOR_BLACK)

    elif role.startswith("hive"):
        # HIVE / GESTATION ROOST (FACTORY)
        draw_hive_mound(draw, cx, cy, r, fill_col, border_col)
        maw_pts = [(cx - 3, cy + 5), (cx - 2, cy), (cx, cy - 2), (cx + 2, cy), (cx + 3, cy + 5)]
        draw.polygon(maw_pts, fill=glyph_col)
        draw.ellipse([cx - 2, cy - 4, cx + 2, cy - 1], fill=glyph_col)
        draw.point((cx, cy - 2), fill=COLOR_WHITE if not is_hover else COLOR_BLACK)

    elif role.startswith("engineer"):
        # Mobile Weaver / Engineer
        draw_chitin_diamond(draw, cx, cy, r, fill_col, border_col)
        draw.arc([cx - 3, cy - 4, cx + 3, cy + 2], 200, 340, fill=glyph_col, width=1)
        draw.line([(cx, cy), (cx, cy + 5)], fill=glyph_col, width=1)

    elif role.startswith("brood"):
        if "_struct" in role:
            draw_pd_spire(draw, cx, cy, r, fill_col, border_col)
        elif "_air" in role:
            draw_air_wings(draw, cx, cy, r, fill_col, border_col)
        else:
            draw_chitin_diamond(draw, cx, cy, r, fill_col, border_col)
        draw.ellipse([cx - 1, cy - 4, cx + 1, cy - 2], fill=glyph_col)
        draw.ellipse([cx - 3, cy + 1, cx - 1, cy + 3], fill=glyph_col)
        draw.ellipse([cx + 1, cy + 1, cx + 3, cy + 3], fill=glyph_col)

    elif role.startswith("shield"):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill_col, outline=border_col)
        draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=glyph_col)
        draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=fill_col)
        draw.line([(cx, cy - 4), (cx, cy + 4)], fill=glyph_col, width=1)
        draw.line([(cx - 4, cy), (cx + 4, cy)], fill=glyph_col, width=1)

    elif role.startswith("stealth"):
        draw_chitin_diamond(draw, cx, cy, r, fill_col, border_col)
        draw.ellipse([cx - 4, cy - 2, cx + 4, cy + 2], fill=glyph_col)
        draw.line([(cx, cy - 2), (cx, cy + 2)], fill=COLOR_WHITE, width=1)

    # --- AIR SPECIALIZATIONS (FIGHTER vs BOMBER vs SCOUT vs GUNSHIP) ---
    elif role.startswith("fighter"):
        # AIR FIGHTER / AA INTERCEPTOR (Swept wings + Upward AA Chevron '^')
        draw_air_wings(draw, cx, cy, r, fill_col, border_col)
        draw.line([(cx - 3, cy + 2), (cx, cy - 3)], fill=glyph_col, width=1)
        draw.line([(cx + 3, cy + 2), (cx, cy - 3)], fill=glyph_col, width=1)
        draw.line([(cx, cy - 3), (cx, cy + 4)], fill=glyph_col, width=1)
        draw.point((cx, cy - 3), fill=COLOR_WHITE if not is_hover else COLOR_BLACK)

    elif role.startswith("bomber"):
        # AIR BOMBER (Swept wings + Falling Teardrop Bomb)
        draw_air_wings(draw, cx, cy, r, fill_col, border_col)
        # Teardrop Bomb in center
        draw.ellipse([cx - 2, cy - 1, cx + 2, cy + 4], fill=glyph_col)
        draw.polygon([(cx - 2, cy), (cx, cy - 3), (cx + 2, cy)], fill=glyph_col)
        draw.line([(cx - 2, cy - 3), (cx + 2, cy - 3)], fill=glyph_col, width=1)
        draw.point((cx, cy + 1), fill=COLOR_WHITE if not is_hover else COLOR_BLACK)

    elif role.startswith("scout"):
        # AIR SCOUT / RECON (Swept wings + Radar Sensor Eye)
        draw_air_wings(draw, cx, cy, r, fill_col, border_col)
        draw.ellipse([cx - 3, cy - 1, cx + 3, cy + 2], fill=glyph_col)
        draw.point((cx, cy), fill=COLOR_WHITE if not is_hover else COLOR_BLACK)
        # Radar scan arc
        draw.arc([cx - 4, cy - 4, cx + 4, cy], 190, 350, fill=glyph_col, width=1)

    elif role.startswith("gunship"):
        # GUNSHIP (Swept wings + Direct-Fire Gun Cross '+')
        draw_air_wings(draw, cx, cy, r, fill_col, border_col)
        draw.line([(cx, cy - 3), (cx, cy + 4)], fill=glyph_col, width=1)
        draw.line([(cx - 3, cy), (cx + 3, cy)], fill=glyph_col, width=1)
        draw.point((cx, cy), fill=COLOR_WHITE if not is_hover else COLOR_BLACK)

    elif role.startswith("regen"):
        # Bio-Repair Caduceus / Cross
        draw_air_wings(draw, cx, cy, r, fill_col, border_col)
        draw.line([(cx, cy - 3), (cx, cy + 3)], fill=glyph_col, width=1)
        draw.line([(cx - 2, cy), (cx + 2, cy)], fill=glyph_col, width=1)

    elif role.startswith("antiair"):
        if "_struct" in role or "_t1" in role:
            draw_pd_spire(draw, cx, cy, r, fill_col, border_col)
        else:
            draw_air_wings(draw, cx, cy, r, fill_col, border_col)
        draw.polygon([(cx, cy - 5), (cx + 3, cy), (cx - 3, cy)], fill=glyph_col)
        draw.point((cx, cy + 3), fill=glyph_col)

    elif role.startswith("nuke"):
        draw_pd_spire(draw, cx, cy, r, fill_col, border_col)
        draw.line([(cx, cy - 6), (cx, cy + 4)], fill=glyph_col, width=1)
        draw.polygon([(cx, cy - 6), (cx + 2, cy - 2), (cx - 2, cy - 2)], fill=glyph_col)

    elif role.startswith("antinuke"):
        draw_pd_spire(draw, cx, cy, r, fill_col, border_col)
        draw.arc([cx - 4, cy - 5, cx + 4, cy + 3], 180, 0, fill=glyph_col, width=1)
        draw.line([(cx, cy - 1), (cx, cy + 4)], fill=glyph_col, width=1)

    elif role.startswith("boss"):
        draw_queen_crown(draw, cx, cy, r, fill_col, border_col)
        draw.polygon([(cx - 3, cy + 2), (cx - 2, cy - 2), (cx, cy), (cx + 2, cy - 2), (cx + 3, cy + 2)], fill=glyph_col)

    elif role.startswith("queen"):
        draw_queen_crown(draw, cx, cy, r, fill_col, border_col)
        draw.polygon([(cx - 4, cy + 2), (cx - 3, cy - 2), (cx, cy), (cx + 3, cy - 2), (cx + 4, cy + 2)], fill=glyph_col)
        draw.point((cx, cy + 2), fill=COLOR_WHITE)

    elif role.startswith("skyqueen"):
        draw_air_wings(draw, cx, cy, r, fill_col, border_col)
        draw.polygon([(cx - 3, cy), (cx - 2, cy - 3), (cx, cy - 1), (cx + 2, cy - 3), (cx + 3, cy)], fill=glyph_col)
        draw.line([(cx, cy), (cx, cy + 4)], fill=glyph_col, width=1)

    else:
        draw_chitin_diamond(draw, cx, cy, r, fill_col, border_col)
        draw.point((cx, cy), fill=glyph_col)

    # 2. Add Tier Pips at the bottom
    if "_t1" in role:
        draw.rectangle([cx - 1, h - 3, cx + 1, h - 1], fill=COLOR_WHITE, outline=COLOR_BLACK)
    elif "_t2" in role:
        draw.rectangle([cx - 3, h - 3, cx - 1, h - 1], fill=COLOR_WHITE, outline=COLOR_BLACK)
        draw.rectangle([cx + 1, h - 3, cx + 3, h - 1], fill=COLOR_WHITE, outline=COLOR_BLACK)
    elif "_t3" in role:
        draw.rectangle([cx - 4, h - 3, cx - 3, h - 1], fill=COLOR_WHITE, outline=COLOR_BLACK)
        draw.rectangle([cx - 1, h - 3, cx + 1, h - 1], fill=COLOR_WHITE, outline=COLOR_BLACK)
        draw.rectangle([cx + 3, h - 3, cx + 4, h - 1], fill=COLOR_WHITE, outline=COLOR_BLACK)
    elif "_exp" in role:
        draw.polygon([(cx, h - 4), (cx + 2, h - 2), (cx, h), (cx - 2, h - 2)], fill=COLOR_WHITE, outline=COLOR_BLACK)

    return img


# Master Icon Archetypes
ALL_ICONS = [
    # Land Swarmers
    "icon_raptor_swarmer_t1",
    "icon_raptor_swarmer_t2",
    "icon_raptor_swarmer_t3",
    # Kamikaze
    "icon_raptor_kamikaze_t1",
    "icon_raptor_kamikaze_t2",
    "icon_raptor_kamikaze_t3",
    "icon_raptor_kamikaze_air",
    "icon_raptor_emp_kamikaze",
    # Point Defense (PD) Spires - DISTINCT FROM HIVES!
    "icon_raptor_pd_t1",
    "icon_raptor_pd_t2",
    # Factories / Hives - WIDE BROOD MOUND!
    "icon_raptor_hive_t1",
    # Acid
    "icon_raptor_acid_t1",
    "icon_raptor_acid_air",
    "icon_raptor_acid_t3",
    "icon_raptor_acid_struct",
    # EMP
    "icon_raptor_emp_air",
    "icon_raptor_emp_bomber",
    "icon_raptor_emp_t3",
    "icon_raptor_emp_struct",
    # Fire & Spikers
    "icon_raptor_fire_air",
    "icon_raptor_spiker_t1",
    "icon_raptor_spiker_t2",
    "icon_raptor_spiker_t3",
    # Brood Artillery & Shields
    "icon_raptor_brood_t2",
    "icon_raptor_brood_air",
    "icon_raptor_brood_struct",
    "icon_raptor_shield_t2",
    "icon_raptor_shield_struct",
    "icon_raptor_shield_t3",
    # Stealth & Recon
    "icon_raptor_stealth_t3",
    "icon_raptor_engineer_t1",
    # AIR SPECIALIZATIONS (FIGHTER vs BOMBER vs SCOUT vs GUNSHIP)
    "icon_raptor_fighter_t1",
    "icon_raptor_fighter_t3",
    "icon_raptor_bomber_t1",
    "icon_raptor_bomber_t2",
    "icon_raptor_scout_t1",
    "icon_raptor_gunship_t2",
    "icon_raptor_regen_air",
    "icon_raptor_antiair_t1",
    "icon_raptor_antiair_air",
    # Strategic Silos
    "icon_raptor_nuke",
    "icon_raptor_antinuke",
    # Titans & Queens
    "icon_raptor_boss_t3",
    "icon_raptor_queen_exp",
    "icon_raptor_skyqueen_exp",
]

STATES = ["rest", "over", "selected", "selectedover"]


def generate_all_dds():
    print(f"Generating {len(ALL_ICONS)} icon sets ({len(ALL_ICONS)*4} DDS files) into: {ICONS_DIR}")
    count = 0
    for icon_name in ALL_ICONS:
        for state in STATES:
            img = render_icon_image(icon_name.replace("icon_raptor_", ""), state)
            out_fn = f"{icon_name}_{state}.dds"
            out_path = os.path.join(ICONS_DIR, out_fn)
            img.save(out_path, format="DDS")
            count += 1
    print(f"Successfully generated {count} strategic icon DDS files!")


# Unit Mapping Dictionary: Unit ID -> StrategicIconName
# Explicitly separates Point Defense (PD) Spires from Gestation Hives (Factories)
# and Air Fighters / AA from Bombers, Scouts, and Gunships!
UNIT_ICON_MAP = {
    # T1 Land / Swarmers
    "XRA0100": "icon_raptor_swarmer_t1",
    "XRA0101": "icon_raptor_swarmer_t1",
    "XRA0114": "icon_raptor_swarmer_t1",
    "XRA0116": "icon_raptor_swarmer_t1",

    # T1 Kamikaze
    "XRA0103": "icon_raptor_kamikaze_t1",

    # T1 Spikers / Acid / EMP
    "XRA0112": "icon_raptor_acid_t1",
    "XRA0113": "icon_raptor_emp_t3",

    # T1 AIR DIFFERENTIATION (FIGHTER / AA vs BOMBER vs SCOUT)
    "XRA0104": "icon_raptor_bomber_t1",     # Bio-Acid Bomber -> BOMBER!
    "XRA0111": "icon_raptor_scout_t1",      # Bio-Recon Scout -> SCOUT / RADAR EYE!
    "XRA0115": "icon_raptor_fighter_t1",    # Raptor Wing Swarmer -> FIGHTER / AA INTERCEPTOR!

    # T1 Mobile Engineer / Weaver
    "XRA0109": "icon_raptor_engineer_t1",

    # T1 Factory / Spawning Hive
    "XRA0107": "icon_raptor_hive_t1",       # Raptor Gestation Roost (FACTORY)

    # T1 Point Defense (PD) & Defensive Spires (NOT Hives!)
    "XRA0121": "icon_raptor_pd_t1",         # Chitin Spore Spire (POINT DEFENSE)
    "XRA0102": "icon_raptor_pd_t1",         # Chitin Spine Spire (POINT DEFENSE)
    "XRA0110": "icon_raptor_pd_t1",         # Burrowing Ambush Spire (POINT DEFENSE)
    "XRA0106": "icon_raptor_antiair_t1",    # Bio-Spore AA Spire (AA DEFENSE)
    "XRA0108": "icon_raptor_acid_t1",       # Bio-Acid Spire (ACID DEFENSE)

    # T2 Land
    "XRA0201": "icon_raptor_swarmer_t2",
    "XRA0202": "icon_raptor_brood_t2",
    "XRA0203": "icon_raptor_kamikaze_t2",
    "XRA0206": "icon_raptor_fire_air",
    "XRA0210": "icon_raptor_spiker_t2",
    "XRA0211": "icon_raptor_stealth_t3",
    "XRA0222": "icon_raptor_brood_t2",
    "XRA0225": "icon_raptor_shield_t2",

    # T2 AIR DIFFERENTIATION
    "XRA0204": "icon_raptor_bomber_t2",     # Brood Swarm Bomber -> BOMBER T2!
    "XRA0205": "icon_raptor_gunship_t2",    # Bio-Hunter Gunship -> GUNSHIP!
    "XRA0213": "icon_raptor_kamikaze_air",  # Air Dive Kamikaze Tick
    "XRA0215": "icon_raptor_regen_air",     # Bio-Healer Drone
    "XRA0216": "icon_raptor_acid_air",      # Corrosive Acid Gunship
    "XRA0217": "icon_raptor_emp_air",       # Bio-EMP Shock Gunship
    "XRA0218": "icon_raptor_fire_air",      # Bio-Inferno Gunship
    "XRA0219": "icon_raptor_antiair_air",   # Bio-Spore AA Gunship
    "XRA0224": "icon_raptor_emp_bomber",    # Bio-EMP Disruption Bomber
    "XRA0227": "icon_raptor_brood_air",     # Bio-Zeppelin Blimpy

    # T2 Defensive Worms & Shields (PD Spires)
    "XRA0208": "icon_raptor_pd_t2",         # Burrowing Bio-Worm (T2 POINT DEFENSE)
    "XRA0209": "icon_raptor_pd_t2",         # Volcanic Magma Worm (T2 POINT DEFENSE)
    "XRA0226": "icon_raptor_shield_struct",  # Rafflesia Shield Bloom (SHIELD)

    # T3 Land
    "XRA0301": "icon_raptor_swarmer_t3",
    "XRA0302": "icon_raptor_stealth_t3",
    "XRA0310": "icon_raptor_kamikaze_t3",
    "XRA0312": "icon_raptor_spiker_t3",
    "XRA0313": "icon_raptor_stealth_t3",
    "XRA0318": "icon_raptor_stealth_t3",
    "XRA0320": "icon_raptor_emp_kamikaze",
    "XRA0322": "icon_raptor_emp_t3",
    "XRA0323": "icon_raptor_acid_t3",
    "XRA0328": "icon_raptor_shield_t3",

    # T3 Air Superiority Fighter
    "XRA0314": "icon_raptor_fighter_t3",    # Apex Air Crow -> T3 FIGHTER / AA SUPERIORITY!

    # T3 Structures & Spires
    "XRA0304": "icon_raptor_nuke",
    "XRA0306": "icon_raptor_brood_struct",
    "XRA0307": "icon_raptor_emp_struct",
    "XRA0308": "icon_raptor_acid_struct",
    "XRA0309": "icon_raptor_acid_struct",
    "XRA0315": "icon_raptor_antinuke",

    # T3 Sub-Boss Matriarchs
    "XRA0303": "icon_raptor_boss_t3",
    "XRA0331": "icon_raptor_boss_t3",
    "XRA0332": "icon_raptor_boss_t3",
    "XRA0333": "icon_raptor_boss_t3",
    "XRA0334": "icon_raptor_boss_t3",
    "XRA0335": "icon_raptor_boss_t3",

    # Experimentals & Titans
    "XRA0329": "icon_raptor_queen_exp",
    "XRA0401": "icon_raptor_queen_exp",
    "XRA0402": "icon_raptor_skyqueen_exp",
}


def update_unit_blueprints():
    print(f"Updating unit blueprints in: {UNITS_DIR}")
    patched_count = 0

    for uid, icon_rel in UNIT_ICON_MAP.items():
        bp_path = os.path.join(UNITS_DIR, uid, f"{uid}_unit.bp")
        if not os.path.exists(bp_path):
            print(f"[Warning] Blueprint not found: {bp_path}")
            continue

        with open(bp_path, "r", encoding="utf-8") as f:
            content = f.read()

        new_icon_val = f"raptorfaction/{icon_rel}"

        # Replace existing StrategicIconName
        if "StrategicIconName" in content:
            new_content = re.sub(
                r"StrategicIconName\s*=\s*['\"][^'\"]*['\"]",
                f"StrategicIconName = '{new_icon_val}'",
                content
            )
        else:
            insert_point = re.search(r"Description\s*=.*?,", content)
            if insert_point:
                pos = insert_point.end()
                new_content = content[:pos] + f"\n    StrategicIconName = '{new_icon_val}'," + content[pos:]
            else:
                new_content = content

        if new_content != content:
            with open(bp_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            patched_count += 1

    print(f"Successfully updated {patched_count} unit blueprints!")


def create_mod_icons_lua():
    lua_path = os.path.join(MOD_DIR, "mod_icons.lua")
    print(f"Creating mod_icons.lua in: {lua_path}")
    lines = ["-- Custom Strategic Icons Configuration for Raptor Swarm Faction", "UnitIconAssignments = {"]
    for uid, icon_rel in sorted(UNIT_ICON_MAP.items()):
        lines.append(f"    {{ BlueprintId = '{uid.lower()}', IconSet = '{icon_rel}' }},")
    lines.append("}\n")

    with open(lua_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Created mod_icons.lua successfully!")


if __name__ == "__main__":
    generate_all_dds()
    update_unit_blueprints()
    create_mod_icons_lua()
    print("=== RAPTOR STRATEGIC ICONS DEPLOYMENT COMPLETE ===")
