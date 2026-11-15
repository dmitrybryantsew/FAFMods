import os
import re
import shutil

MOD_DIR = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
WORKSPACE_DIR = r"E:\Games\FAFMods"

print("=================================================================")
print("Applying Water, Cliff, and Underwater Targeting Fixes for Raptors")
print("=================================================================")

# ---------------------------------------------------------------------------
# 1. Update Projectiles: Allow Air Bombs, Acid & Plasma to Penetrate Water
# ---------------------------------------------------------------------------
projectiles_to_fix = [
    'XRA_BioBomb01_proj.bp',
    'XRA_BroodEggBomb01_proj.bp',
    'XRA_DodoBomb01_proj.bp',
    'XRA_ElectroBomb01_proj.bp',
    'XRA_AcidSpike01_proj.bp',
    'XRA_Spike01_proj.bp',
    'XRA_PyroStream01_proj.bp',
    'XRA_QueenPlasma01_proj.bp',
]

proj_dir = os.path.join(MOD_DIR, "projectiles")
for p_file in projectiles_to_fix:
    folder = p_file.replace("_proj.bp", "")
    full_path = os.path.join(proj_dir, folder, p_file)
    if os.path.exists(full_path):
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace DestroyOnWater = true with DestroyOnWater = false
        if "DestroyOnWater = true" in content:
            content = content.replace("DestroyOnWater = true", "DestroyOnWater = false")
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Updated projectile {p_file}: DestroyOnWater = false (enables hitting underwater structures)")
        elif "DestroyOnWater = false" in content:
            print(f"Projectile {p_file} already has DestroyOnWater = false")
        else:
            # If DestroyOnWater not explicitly listed, inject it into Physics
            content = re.sub(r'(Physics\s*=\s*\{)', r'\1\n        DestroyOnWater = false,', content)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Injected DestroyOnWater = false into {p_file}")
    else:
        print(f"Warning: Projectile {full_path} not found!")

# ---------------------------------------------------------------------------
# 2. Update Air Gunships: Add Seabed to FireTargetLayerCapsTable
# ---------------------------------------------------------------------------
gunships_to_fix = ['XRA0216', 'XRA0217', 'XRA0218']
for uid in gunships_to_fix:
    bp_path = os.path.join(MOD_DIR, "units", uid, f"{uid}_unit.bp")
    if os.path.exists(bp_path):
        with open(bp_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Update Air = 'Land|Water' to Air = 'Land|Water|Seabed'
        updated = False
        if "Air = 'Land|Water'" in content:
            content = content.replace("Air = 'Land|Water'", "Air = 'Land|Water|Seabed'")
            updated = True
        if "Land = 'Land|Water'" in content:
            content = content.replace("Land = 'Land|Water'", "Land = 'Land|Water|Seabed'")
            updated = True
        if "Water = 'Land|Water'" in content:
            content = content.replace("Water = 'Land|Water'", "Water = 'Land|Water|Seabed'")
            updated = True

        if updated:
            with open(bp_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Updated gunship {uid}_unit.bp: added Seabed to target caps")
        else:
            print(f"Gunship {uid}_unit.bp already has Seabed in target caps")

# ---------------------------------------------------------------------------
# 3. Update Mobile Land Units: Remove Seabed from Land firing caps
#    (Prevents land units on cliffs/shores from pursuing underwater targets)
# ---------------------------------------------------------------------------
units_dirs = [os.path.join(MOD_DIR, "units")]
workspace_units = os.path.join(WORKSPACE_DIR, "units")
if os.path.exists(workspace_units):
    units_dirs.append(workspace_units)

mobile_land_uids = [
    'XRA0100', 'XRA0101', 'XRA0103', 'XRA0201', 'XRA0202', 'XRA0203',
    'XRA0206', 'XRA0301', 'XRA0302', 'XRA0303', 'XRA0310', 'XRA0320',
    'XRA0328', 'XRA0329', 'XRA0401'
]

melee_uids = ['XRA0100', 'XRA0101']

for u_dir in units_dirs:
    for uid in mobile_land_uids:
        bp_path = os.path.join(u_dir, uid, f"{uid}_unit.bp")
        if os.path.exists(bp_path):
            with open(bp_path, "r", encoding="utf-8") as f:
                content = f.read()

            orig_content = content

            if uid in melee_uids:
                # Melee units: Land = 'Land' (melee cannot claw ships or underwater targets)
                content = re.sub(r"Land\s*=\s*'Land\|Water\|Seabed'", "Land = 'Land'", content)
                content = re.sub(r"Water\s*=\s*'Land\|Water\|Seabed'", "Water = 'Land|Water'", content)
            else:
                # Other mobile land units: Land = 'Land|Water' (can engage surface ships, but not seabed/underwater)
                content = re.sub(r"Land\s*=\s*'Land\|Water\|Seabed'", "Land = 'Land|Water'", content)
                content = re.sub(r"Land\s*=\s*'Air\|Land\|Seabed\|Water'", "Land = 'Air|Land|Water'", content)
                content = re.sub(r"Land\s*=\s*'Air\|Land\|Water\|Seabed'", "Land = 'Air|Land|Water'", content)

            if content != orig_content:
                with open(bp_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Updated {uid}_unit.bp in {os.path.basename(u_dir)}: removed Seabed from Land firing caps")
            else:
                print(f"{uid}_unit.bp in {os.path.basename(u_dir)}: Land firing caps already adjusted")

# ---------------------------------------------------------------------------
# 4. Sync Lua files to MOD_DIR
# ---------------------------------------------------------------------------
lua_src = os.path.join(WORKSPACE_DIR, "lua")
lua_dst = os.path.join(MOD_DIR, "lua")
for fname in ["RaptorTargeting.lua", "RaptorPlatoonAI.lua", "RaptorSpawner.lua", "QueenBossAI.lua"]:
    s = os.path.join(lua_src, fname)
    d = os.path.join(lua_dst, fname)
    if os.path.exists(s):
        shutil.copyfile(s, d)
        print(f"Synced {fname} to active mod directory")

print("\nAll Water, Cliff, and Underwater Targeting Fixes applied successfully!")
