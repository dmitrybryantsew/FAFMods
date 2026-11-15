import os
import glob
import re
import shutil

MOD_DIR = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
WS_DIR = r"E:\Games\FAFMods"

print("=================================================================")
print("Applying Seabed & Underwater Ignore Targeting Fixes for Raptors")
print("=================================================================")

# 1. Update Unit Blueprints
for base_dir in [MOD_DIR, WS_DIR]:
    u_dir = os.path.join(base_dir, "units")
    if not os.path.exists(u_dir):
        continue
    for bp_path in glob.glob(os.path.join(u_dir, "*", "*_unit.bp")):
        with open(bp_path, "r", encoding="utf-8") as f:
            content = f.read()

        orig_content = content
        uid = os.path.basename(os.path.dirname(bp_path))
        is_air = "RULEUMT_Air" in content

        if is_air:
            # Air units cannot attack underwater seabed targets
            content = re.sub(r"Air\s*=\s*'Land\|Water\|Seabed'", "Air = 'Land|Water'", content)
            content = re.sub(r"Air\s*=\s*'Land\|Water\|Seabed\|Air'", "Air = 'Land|Water|Air'", content)
            content = re.sub(r"Air\s*=\s*'Air\|Land\|Seabed\|Water'", "Air = 'Air|Land|Water'", content)
            content = re.sub(r"Air\s*=\s*'Land\|Seabed\|Water'", "Air = 'Land|Water'", content)
            content = re.sub(r"Land\s*=\s*'Land\|Water\|Seabed'", "Land = 'Land|Water'", content)
            content = re.sub(r"Land\s*=\s*'Air\|Land\|Seabed\|Water'", "Land = 'Air|Land|Water'", content)
            content = re.sub(r"Land\s*=\s*'Air\|Land\|Water\|Seabed'", "Land = 'Air|Land|Water'", content)
            content = re.sub(r"Water\s*=\s*'Land\|Water\|Seabed'", "Water = 'Land|Water'", content)
        else:
            # Land units: when in Air or on Land, remove Seabed
            content = re.sub(r"Air\s*=\s*'Land\|Water\|Seabed'", "Air = 'Land|Water'", content)
            content = re.sub(r"Air\s*=\s*'Air\|Land\|Seabed\|Water'", "Air = 'Air|Land|Water'", content)
            content = re.sub(r"Land\s*=\s*'Land\|Water\|Seabed'", "Land = 'Land|Water'", content)
            content = re.sub(r"Land\s*=\s*'Air\|Land\|Water\|Seabed'", "Land = 'Air|Land|Water'", content)
            content = re.sub(r"Land\s*=\s*'Air\|Land\|Seabed\|Water'", "Land = 'Air|Land|Water'", content)

        if content != orig_content:
            with open(bp_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Updated {uid}_unit.bp in {os.path.basename(base_dir)}: removed Seabed targeting")

print("\n--- Syncing Lua Files to MOD_DIR ---")
lua_src = os.path.join(WS_DIR, "lua")
lua_dst = os.path.join(MOD_DIR, "lua")
for fname in os.listdir(lua_src):
    if fname.endswith(".lua"):
        s = os.path.join(lua_src, fname)
        d = os.path.join(lua_dst, fname)
        shutil.copyfile(s, d)
        print(f"Synced {fname} to active mod directory")

print("\nAll seabed ignore targeting fixes applied successfully!")
