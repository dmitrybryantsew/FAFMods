import os
import re
import zipfile

mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
units_dir = os.path.join(mod_dir, "units")
export_zip = r"E:\Games\FAFMods\exports\RaptorFaction.zip"

# Specification for each unit that needs fixing
FIXES = {
    "XRA0100": {
        "UniformScale": 0.65,
        "SelectionSizeX": 0.35,
        "SelectionSizeZ": 0.50,
        "LifeBarOffset": 0.35,
        "LifeBarSize": 0.50,
        "SizeX": 0.45,
        "SizeY": 0.40,
        "SizeZ": 0.70,
    },
    "XRA0103": {
        "UniformScale": 0.70,
        "SelectionSizeX": 0.45,
        "SelectionSizeZ": 0.60,
        "LifeBarOffset": 0.55,
        "LifeBarSize": 0.65,
        "SizeX": 0.55,
        "SizeY": 0.60,
        "SizeZ": 0.85,
    },
    "XRA0104": {
        "UniformScale": 0.50,
        "SelectionSizeX": 1.4,
        "SelectionSizeZ": 1.1,
        "LifeBarOffset": 0.45,
        "LifeBarSize": 1.2,
        "SizeX": 1.6,
        "SizeY": 0.45,
        "SizeZ": 1.5,
    },
    "XRA0109": {
        "UniformScale": 0.85,
        "SelectionSizeX": 0.50,
        "SelectionSizeZ": 0.65,
        "LifeBarOffset": 0.50,
        "LifeBarSize": 0.65,
        "SizeX": 0.65,
        "SizeY": 0.55,
        "SizeZ": 0.90,
    },
    "XRA0111": {
        "UniformScale": 0.70,
        "SelectionSizeX": 0.85,
        "SelectionSizeZ": 0.70,
        "LifeBarOffset": 0.40,
        "LifeBarSize": 0.75,
        "SizeX": 0.90,
        "SizeY": 0.30,
        "SizeZ": 0.85,
    },
    "XRA0202": {
        "UniformScale": 1.10,
        "SelectionSizeX": 0.90,
        "SelectionSizeZ": 1.20,
        "LifeBarOffset": 0.80,
        "LifeBarSize": 1.20,
        "SizeX": 1.20,
        "SizeY": 1.10,
        "SizeZ": 1.80,
    },
    "XRA0203": {
        "UniformScale": 0.80,
        "SelectionSizeX": 0.55,
        "SelectionSizeZ": 0.65,
        "LifeBarOffset": 0.60,
        "LifeBarSize": 0.75,
        "SizeX": 0.65,
        "SizeY": 0.65,
        "SizeZ": 0.95,
    },
    "XRA0204": {
        "UniformScale": 0.50,
        "SelectionSizeX": 1.8,
        "SelectionSizeZ": 1.4,
        "LifeBarOffset": 0.60,
        "LifeBarSize": 1.6,
        "SizeX": 1.9,
        "SizeY": 0.50,
        "SizeZ": 1.9,
    },
    "XRA0205": {
        "UniformScale": 0.65,
        "SelectionSizeX": 1.5,
        "SelectionSizeZ": 1.3,
        "LifeBarOffset": 0.50,
        "LifeBarSize": 1.4,
        "SizeX": 1.6,
        "SizeY": 0.45,
        "SizeZ": 1.6,
    },
    "XRA0206": {
        "UniformScale": 1.05,
        "SelectionSizeX": 0.85,
        "SelectionSizeZ": 1.05,
        "LifeBarOffset": 0.70,
        "LifeBarSize": 0.95,
        "SizeX": 1.0,
        "SizeY": 0.8,
        "SizeZ": 1.5,
    },
    "XRA0302": {
        "UniformScale": 0.60,
        "SelectionSizeX": 1.1,
        "SelectionSizeZ": 1.4,
        "LifeBarOffset": 0.85,
        "LifeBarSize": 1.3,
        "SizeX": 1.3,
        "SizeY": 1.1,
        "SizeZ": 1.8,
    },
    "XRA0303": {
        "UniformScale": 0.55,
        "SelectionSizeX": 1.8,
        "SelectionSizeZ": 2.4,
        "LifeBarOffset": 1.6,
        "LifeBarSize": 2.2,
        "SizeX": 2.2,
        "SizeY": 2.2,
        "SizeZ": 3.5,
    },
    "XRA0315": {
        "UniformScale": 3.5,
        "SelectionSizeX": 1.8,
        "SelectionSizeZ": 1.8,
        "LifeBarOffset": 1.4,
        "LifeBarSize": 2.4,
        "SizeX": 2.4,
        "SizeY": 1.8,
        "SizeZ": 2.4,
    },
    "XRA0310": {
        "UniformScale": 0.85,
        "SelectionSizeX": 0.85,
        "SelectionSizeZ": 1.10,
        "LifeBarOffset": 0.85,
        "LifeBarSize": 1.1,
        "SizeX": 1.0,
        "SizeY": 1.1,
        "SizeZ": 1.6,
    },
    "XRA0401": {
        "UniformScale": 0.38,
        "SelectionSizeX": 3.5,
        "SelectionSizeZ": 4.5,
        "LifeBarOffset": 3.2,
        "LifeBarSize": 4.2,
        "SizeX": 4.0,
        "SizeY": 4.5,
        "SizeZ": 7.0,
    },
}

def update_blueprint_text(text, fixes):
    lines = text.splitlines(True)
    out = []
    
    # We want to replace only specific field assignments, taking care not to replace inside Footprint/Skirt
    for line in lines:
        stripped = line.strip()
        replaced = False
        for k, v in fixes.items():
            # Check for exact key match at start of assignment
            # E.g. 'UniformScale = ...,'
            pattern = rf"^(\s*{k}\s*=\s*)([0-9\.]+)(,.*)$"
            m = re.match(pattern, line)
            if m:
                # Avoid touching Footprint SizeX / SizeZ if present
                if k in ["SizeX", "SizeZ"] and ("Footprint" in line or "Skirt" in line):
                    continue
                # For SizeX/SizeZ, make sure it's not SkirtSizeX or SelectionSizeX
                prefix = m.group(1)
                suffix = m.group(3)
                out.append(f"{prefix}{v}{suffix}\n")
                replaced = True
                break
        if not replaced:
            out.append(line)
    return "".join(out)

# 1. Update individual blueprint files in mod_dir
print("--- Updating active mod unit blueprints ---")
for uid, fix in FIXES.items():
    bp_path = os.path.join(units_dir, uid, f"{uid}_unit.bp")
    if not os.path.exists(bp_path):
        print(f"Warning: {bp_path} not found!")
        continue
    with open(bp_path, "r", encoding="utf-8") as f:
        content = f.read()
    new_content = update_blueprint_text(content, fix)
    with open(bp_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Updated {uid} in {bp_path}")

# 2. Update build generator scripts
scripts_to_update = [
    r"E:\Games\FAFMods\build_remaining_bar_units.py",
    r"E:\Games\FAFMods\build_raptor_expansion_complete.py",
    r"E:\Games\FAFMods\build_raptor_faction_complete.py",
]

print("\n--- Updating build python scripts ---")
for s_path in scripts_to_update:
    if not os.path.exists(s_path):
        continue
    with open(s_path, "r", encoding="utf-8") as f:
        s_content = f.read()

    modified = False
    for uid, fix in FIXES.items():
        # Match unit block or blueprint variable, e.g. bp_xra0100 = """..."""
        pattern = rf"(bp_{uid.lower()}\s*=\s*\"\"\"[\s\S]*?\"\"\")"
        m = re.search(pattern, s_content, re.IGNORECASE)
        if m:
            orig_block = m.group(1)
            new_block = update_blueprint_text(orig_block, fix)
            if orig_block != new_block:
                s_content = s_content.replace(orig_block, new_block)
                modified = True
                print(f"Updated {uid} blueprint template in {os.path.basename(s_path)}")

    if modified:
        with open(s_path, "w", encoding="utf-8") as f:
            f.write(s_content)
        print(f"Saved changes to {os.path.basename(s_path)}")

# 3. Re-package RaptorFaction.zip
print(f"\n--- Packaging updated mod to {export_zip} ---")
with zipfile.ZipFile(export_zip, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(mod_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(mod_dir))
            z.write(full_path, rel_path)

print(f"SUCCESS: Exported {os.path.getsize(export_zip):,} bytes to {export_zip}")
