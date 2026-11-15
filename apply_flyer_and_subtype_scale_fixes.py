import os
import re
import zipfile

mod_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
units_dir = os.path.join(mod_dir, "units")
export_zip = r"E:\Games\FAFMods\exports\RaptorFaction.zip"

FIXES = {
    # --- AIR UNITS ---
    "XRA0224": {  # Bio-EMP Disruption Bomber (T2 Carpet Bomber)
        "UniformScale": 0.50,
        "SelectionSizeX": 1.5,
        "SelectionSizeZ": 1.2,
        "LifeBarOffset": 0.55,
        "LifeBarSize": 1.4,
        "SizeX": 1.7,
        "SizeY": 0.50,
        "SizeZ": 1.6,
        "CollisionOffsetY": 0,
        "SizeSphere": 1.6,
    },
    "XRA0219": {  # Bio-Spore AA Gunship (T2 AA Interceptor Gunship)
        "UniformScale": 0.65,
        "SelectionSizeX": 1.4,
        "SelectionSizeZ": 1.2,
        "LifeBarOffset": 0.50,
        "LifeBarSize": 1.3,
        "SizeX": 1.5,
        "SizeY": 0.45,
        "SizeZ": 1.5,
        "CollisionOffsetY": 0,
        "SizeSphere": 1.4,
    },
    "XRA0314": {  # Apex Air Crow (T3 Heavy Air Superiority Raptor)
        "UniformScale": 0.95,
        "SelectionSizeX": 1.5,
        "SelectionSizeZ": 1.4,
        "LifeBarOffset": 0.60,
        "LifeBarSize": 1.5,
        "SizeX": 1.6,
        "SizeY": 0.50,
        "SizeZ": 1.6,
        "CollisionOffsetY": 0,
        "SizeSphere": 1.6,
    },
    "XRA0216": {  # Corrosive Acid Gunship (T2 Acid Gunship)
        "UniformScale": 0.65,
        "SelectionSizeX": 1.4,
        "SelectionSizeZ": 1.2,
        "LifeBarOffset": 0.50,
        "LifeBarSize": 1.3,
        "SizeX": 1.5,
        "SizeY": 0.45,
        "SizeZ": 1.5,
        "CollisionOffsetY": 0,
        "SizeSphere": 1.4,
    },
    "XRA0217": {  # Bio-EMP Shock Gunship (T2 EMP Gunship)
        "UniformScale": 0.65,
        "SelectionSizeX": 1.4,
        "SelectionSizeZ": 1.2,
        "LifeBarOffset": 0.50,
        "LifeBarSize": 1.3,
        "SizeX": 1.5,
        "SizeY": 0.45,
        "SizeZ": 1.5,
        "CollisionOffsetY": 0,
        "SizeSphere": 1.4,
    },
    "XRA0218": {  # Bio-Inferno Gunship (T2 Fire Gunship)
        "UniformScale": 0.65,
        "SelectionSizeX": 1.4,
        "SelectionSizeZ": 1.2,
        "LifeBarOffset": 0.50,
        "LifeBarSize": 1.3,
        "SizeX": 1.5,
        "SizeY": 0.45,
        "SizeZ": 1.5,
        "CollisionOffsetY": 0,
        "SizeSphere": 1.4,
    },
    "XRA0213": {  # Bio-Dive Kamikaze Tick (T2 Kamikaze Dive Flyer)
        "UniformScale": 0.70,
        "SelectionSizeX": 0.8,
        "SelectionSizeZ": 0.7,
        "LifeBarOffset": 0.40,
        "LifeBarSize": 0.8,
        "SizeX": 0.9,
        "SizeY": 0.35,
        "SizeZ": 0.9,
        "CollisionOffsetY": 0,
        "SizeSphere": 1.0,
    },
    "XRA0215": {  # Bio-Healer Drone (T2 Bio-Repair Drone)
        "UniformScale": 0.85,
        "SelectionSizeX": 0.65,
        "SelectionSizeZ": 0.85,
        "LifeBarOffset": 0.45,
        "LifeBarSize": 0.8,
        "SizeX": 0.75,
        "SizeY": 0.50,
        "SizeZ": 0.9,
        "CollisionOffsetY": 0,
        "SizeSphere": 1.0,
    },

    # --- LAND SUBTYPES ---
    "XRA0112": {  # Caustic Acid Swarmer
        "UniformScale": 1.00,
        "SelectionSizeX": 0.50,
        "SelectionSizeZ": 0.60,
        "LifeBarOffset": 0.40,
        "LifeBarSize": 0.70,
        "SizeX": 0.65,
        "SizeY": 0.50,
        "SizeZ": 0.85,
    },
    "XRA0113": {  # Shock EMP Swarmer
        "UniformScale": 1.00,
        "SelectionSizeX": 0.50,
        "SelectionSizeZ": 0.60,
        "LifeBarOffset": 0.40,
        "LifeBarSize": 0.70,
        "SizeX": 0.65,
        "SizeY": 0.50,
        "SizeZ": 0.85,
    },
    "XRA0114": {  # Brood Swarmer
        "UniformScale": 1.00,
        "SelectionSizeX": 0.50,
        "SelectionSizeZ": 0.60,
        "LifeBarOffset": 0.40,
        "LifeBarSize": 0.70,
        "SizeX": 0.65,
        "SizeY": 0.50,
        "SizeZ": 0.85,
    },
    "XRA0210": {  # Chitin Needle Spiker
        "UniformScale": 0.85,
        "SelectionSizeX": 0.70,
        "SelectionSizeZ": 0.90,
        "LifeBarOffset": 0.65,
        "LifeBarSize": 0.90,
        "SizeX": 0.85,
        "SizeY": 0.80,
        "SizeZ": 1.10,
    },
    "XRA0211": {  # Spectre Cloaked Swarmer
        "UniformScale": 0.90,
        "SelectionSizeX": 0.60,
        "SelectionSizeZ": 0.80,
        "LifeBarOffset": 0.55,
        "LifeBarSize": 0.80,
        "SizeX": 0.75,
        "SizeY": 0.65,
        "SizeZ": 1.00,
    },
    "XRA0222": {  # Mobile Brood Mortar Bug
        "UniformScale": 1.10,
        "SelectionSizeX": 0.90,
        "SelectionSizeZ": 1.20,
        "LifeBarOffset": 0.80,
        "LifeBarSize": 1.20,
        "SizeX": 1.20,
        "SizeY": 1.10,
        "SizeZ": 1.80,
    },
    "XRA0320": {  # Behemoth EMP Shock Dodo
        "UniformScale": 0.85,
        "SelectionSizeX": 0.85,
        "SelectionSizeZ": 1.10,
        "LifeBarOffset": 0.85,
        "LifeBarSize": 1.10,
        "SizeX": 1.00,
        "SizeY": 1.10,
        "SizeZ": 1.60,
    },
    "XRA0322": {  # Mobile EMP Bio-Artillery
        "UniformScale": 1.20,
        "SelectionSizeX": 1.00,
        "SelectionSizeZ": 1.30,
        "LifeBarOffset": 0.85,
        "LifeBarSize": 1.30,
        "SizeX": 1.30,
        "SizeY": 1.20,
        "SizeZ": 2.00,
    },
    "XRA0323": {  # Mobile Acid Bio-Artillery
        "UniformScale": 1.20,
        "SelectionSizeX": 1.00,
        "SelectionSizeZ": 1.30,
        "LifeBarOffset": 0.85,
        "LifeBarSize": 1.30,
        "SizeX": 1.30,
        "SizeY": 1.20,
        "SizeZ": 2.00,
    },
    "XRA0312": {  # Apex Heavy Needle Spiker
        "UniformScale": 0.85,
        "SelectionSizeX": 0.90,
        "SelectionSizeZ": 1.20,
        "LifeBarOffset": 0.85,
        "LifeBarSize": 1.20,
        "SizeX": 1.10,
        "SizeY": 1.10,
        "SizeZ": 1.60,
    },
    "XRA0313": {  # Spectre Stalker Behemoth
        "UniformScale": 0.90,
        "SelectionSizeX": 1.00,
        "SelectionSizeZ": 1.30,
        "LifeBarOffset": 0.90,
        "LifeBarSize": 1.30,
        "SizeX": 1.20,
        "SizeY": 1.20,
        "SizeZ": 1.80,
    },
    "XRA0318": {  # Spectre Phantom Spiker
        "UniformScale": 0.85,
        "SelectionSizeX": 0.90,
        "SelectionSizeZ": 1.20,
        "LifeBarOffset": 0.85,
        "LifeBarSize": 1.20,
        "SizeX": 1.10,
        "SizeY": 1.10,
        "SizeZ": 1.60,
    },
    "XRA0331": {  # Acid Matriarch Sub-Boss
        "UniformScale": 0.55,
        "SelectionSizeX": 1.80,
        "SelectionSizeZ": 2.40,
        "LifeBarOffset": 1.60,
        "LifeBarSize": 2.20,
        "SizeX": 2.20,
        "SizeY": 2.20,
        "SizeZ": 3.50,
    },
    "XRA0332": {  # Storm Matriarch Sub-Boss
        "UniformScale": 0.55,
        "SelectionSizeX": 1.80,
        "SelectionSizeZ": 2.40,
        "LifeBarOffset": 1.60,
        "LifeBarSize": 2.20,
        "SizeX": 2.20,
        "SizeY": 2.20,
        "SizeZ": 3.50,
    },
    "XRA0333": {  # Pyro Matriarch Sub-Boss
        "UniformScale": 0.55,
        "SelectionSizeX": 1.80,
        "SelectionSizeZ": 2.40,
        "LifeBarOffset": 1.60,
        "LifeBarSize": 2.20,
        "SizeX": 2.20,
        "SizeY": 2.20,
        "SizeZ": 3.50,
    },
    "XRA0334": {  # Broodmother Matriarch Sub-Boss
        "UniformScale": 0.55,
        "SelectionSizeX": 1.80,
        "SelectionSizeZ": 2.40,
        "LifeBarOffset": 1.60,
        "LifeBarSize": 2.20,
        "SizeX": 2.20,
        "SizeY": 2.20,
        "SizeZ": 3.50,
    },
    "XRA0335": {  # Shadow Matriarch Sub-Boss
        "UniformScale": 0.55,
        "SelectionSizeX": 1.80,
        "SelectionSizeZ": 2.40,
        "LifeBarOffset": 1.60,
        "LifeBarSize": 2.20,
        "SizeX": 2.20,
        "SizeY": 2.20,
        "SizeZ": 3.50,
    },
}

def update_unit_bp(content, fixes):
    lines = content.splitlines(True)
    out = []
    keys_handled = set()

    for line in lines:
        stripped = line.strip()

        # Remove erroneous GroundElevation
        if stripped.startswith("GroundElevation"):
            continue

        replaced = False
        for k, v in fixes.items():
            pattern = rf"^(\s*{k}\s*=\s*)([0-9\.\-]+)(,.*)$"
            m = re.match(pattern, line)
            if m:
                if k in ["SizeX", "SizeZ"] and ("Footprint" in line or "Skirt" in line):
                    continue
                prefix = m.group(1)
                suffix = m.group(3)
                out.append(f"{prefix}{v}{suffix}\n")
                keys_handled.add(k)
                replaced = True
                break
        if not replaced:
            out.append(line)

    result = "".join(out)

    # Insert missing fields:
    # 1. CollisionOffsetY (before Defense or LifeBar)
    if "CollisionOffsetY" in fixes and "CollisionOffsetY" not in keys_handled:
        val = fixes["CollisionOffsetY"]
        if "CollisionOffsetY" in result:
            result = re.sub(r"CollisionOffsetY\s*=\s*[0-9\.\-]+,", f"CollisionOffsetY = {val},", result)
        else:
            result = re.sub(r"(\n\s*Defense\s*=\s*\{)", rf"\n    CollisionOffsetY = {val},\1", result)

    # 2. LifeBarSize (after LifeBarOffset)
    if "LifeBarSize" in fixes and "LifeBarSize" not in keys_handled:
        val = fixes["LifeBarSize"]
        if "LifeBarSize" in result:
            result = re.sub(r"LifeBarSize\s*=\s*[0-9\.\-]+,", f"LifeBarSize = {val},", result)
        else:
            result = re.sub(r"(LifeBarOffset\s*=\s*[0-9\.\-]+,)", rf"\1\n    LifeBarSize = {val},", result)

    # 3. SizeSphere (before or after SelectionThickness / SizeX)
    if "SizeSphere" in fixes and "SizeSphere" not in keys_handled:
        val = fixes["SizeSphere"]
        if "SizeSphere" in result:
            result = re.sub(r"SizeSphere\s*=\s*[0-9\.\-]+,", f"SizeSphere = {val},", result)
        else:
            result = re.sub(r"(SelectionThickness\s*=\s*[0-9\.\-]+,)", rf"\1\n    SizeSphere = {val},", result)

    return result

print("=== Step 1: Updating mod units in active game mod directory ===")
for uid, fix in FIXES.items():
    bp_path = os.path.join(units_dir, uid, f"{uid}_unit.bp")
    if not os.path.exists(bp_path):
        print(f"Warning: {bp_path} not found!")
        continue
    with open(bp_path, "r", encoding="utf-8") as f:
        old_content = f.read()
    new_content = update_unit_bp(old_content, fix)
    with open(bp_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Updated {uid}: scale -> {fix.get('UniformScale')}")

print("\n=== Step 2: Updating port_all_bar_subtypes.py unit dictionaries ===")
port_script = r"E:\Games\FAFMods\port_all_bar_subtypes.py"
if os.path.exists(port_script):
    with open(port_script, "r", encoding="utf-8") as f:
        port_content = f.read()

    for uid, fix in FIXES.items():
        if "UniformScale" in fix:
            s_val = fix["UniformScale"]
            # Match unit block e.g. "id": "XRA0224", ... "scale": 0.06,
            pattern = rf'("id":\s*"{uid}".*?"scale":\s*)([0-9\.]+)'
            port_content = re.sub(pattern, rf'\g<1>{s_val}', port_content, flags=re.DOTALL)

    # Remove GroundElevation from port_all_bar_subtypes template
    port_content = port_content.replace("        GroundElevation = {physics_elev},\n", "")

    with open(port_script, "w", encoding="utf-8") as f:
        f.write(port_content)
    print("Updated port_all_bar_subtypes.py.")

print("\n=== Step 3: Updating apply_scale_fixes.py dictionary ===")
scale_fixes_script = r"E:\Games\FAFMods\apply_scale_fixes.py"
if os.path.exists(scale_fixes_script):
    with open(scale_fixes_script, "r", encoding="utf-8") as f:
        scale_content = f.read()
    # Merge FIXES into apply_scale_fixes.py
    for uid, fix in FIXES.items():
        if f'"{uid}": {{' not in scale_content:
            fix_str = f'    "{uid}": {{\n'
            for k, v in fix.items():
                fix_str += f'        "{k}": {v},\n'
            fix_str += "    },\n"
            # Insert right after "FIXES = {"
            scale_content = scale_content.replace("FIXES = {\n", f"FIXES = {{\n{fix_str}")

    with open(scale_fixes_script, "w", encoding="utf-8") as f:
        f.write(scale_content)
    print("Updated apply_scale_fixes.py.")

print(f"\n=== Step 4: Re-packaging RaptorFaction.zip to {export_zip} ===")
with zipfile.ZipFile(export_zip, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(mod_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(mod_dir))
            z.write(full_path, rel_path)

print(f"SUCCESS: Exported {os.path.getsize(export_zip):,} bytes to {export_zip}")
