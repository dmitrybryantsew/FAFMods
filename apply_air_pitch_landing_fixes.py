import os
import re
import glob
import zipfile

MOD_DIR = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction"
UNITS_DIR = os.path.join(MOD_DIR, "units")
WORKSPACE_DIR = r"E:\Games\FAFMods"

print("--- Step 1: Fixing XRA0115 (Raptor Wing Swarmer) ---")
bp_xra0115 = os.path.join(UNITS_DIR, "XRA0115", "XRA0115_unit.bp")
if os.path.exists(bp_xra0115):
    with open(bp_xra0115, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Air table: AutoLandTime = -1, MinAirspeed = 10, clean aerodynamic parameters
    new_air = """    Air = {
        AutoLandTime = -1,
        BankFactor = 3.0,
        BankForward = false,
        BreakOffDistance = 10,
        BreakOffTrigger = 15,
        CanFly = true,
        CombatTurnSpeed = 1.7,
        EngageDistance = 50,
        KLift = 2.0,
        KLiftDamping = 2.0,
        KMove = 1.5,
        KMoveDamping = 1.0,
        KRoll = 2.0,
        KRollDamping = 1.0,
        KTurn = 1.0,
        KTurnDamping = 1.5,
        LiftFactor = 7,
        MaxAirspeed = 15.0,
        MinAirspeed = 10.0,
        StartTurnDistance = 5,
        TightTurnMultiplier = 1.05,
        TurnSpeed = 1.7,
        WingLoopRange = 0,
        Winged = true,
    },"""
    content = re.sub(r'    Air = \{[^}]+\},', new_air, content, flags=re.DOTALL)

    # 2. General CommandCaps: RULEUCC_Dock = false
    content = re.sub(r'RULEUCC_Dock = true,', 'RULEUCC_Dock = false,', content)

    # 3. Physics table: Elevation = 14.0, FuelUseTime = 0, MaxSpeed = 0.5, remove TurnRadius/TurnRate
    new_physics = """    Physics = {
        BuildOnLayerCaps = {
            LAYER_Air = true,
            LAYER_Land = false,
            LAYER_Orbit = false,
            LAYER_Seabed = false,
            LAYER_Sub = false,
            LAYER_Water = false,
        },
        Elevation = 14.0,
        FuelRechargeRate = 0,
        FuelUseTime = 0,
        GroundCollisionOffset = 1.6,
        MaxSpeed = 0.5,
        MeshExtentsX = 1.5,
        MeshExtentsY = 0.5,
        MeshExtentsZ = 1.2,
        MotionType = 'RULEUMT_Air',
    },"""
    content = re.sub(r'    Physics = \{[^}]+\},', new_physics, content, flags=re.DOTALL)

    # 4. Weapon table: SlavedToBody, firepoint turret bones, 55 deg pitch/yaw range
    # Replace weapon 1 (AirBioSpike) turret bones and add SlavedToBody
    content = re.sub(r"TurretBonePitch = 'head',", "TurretBonePitch = 'firepoint',", content)
    content = re.sub(r"TurretBoneYaw = 'body',", "TurretBoneYaw = 'firepoint',", content)
    content = re.sub(r"TurretPitchRange = 90,", "TurretPitchRange = 55,", content)
    content = re.sub(r"TurretYawRange = 90,", "TurretYawRange = 55,", content)
    if "SlavedToBody" not in content:
        content = content.replace(
            "RateOfFire = 2.0,",
            "RateOfFire = 2.0,\n            SlavedToBody = true,\n            SlavedToBodyArcRange = 50,\n            UseFiringSolutionInsteadOfAimBone = true,"
        )

    with open(bp_xra0115, "w", encoding="utf-8") as f:
        f.write(content)
    print("XRA0115_unit.bp updated successfully.")

print("\n--- Step 2: Fixing All Other Air Units in RaptorFaction ---")
air_uids = [
    'XRA0104', 'XRA0111', 'XRA0204', 'XRA0205', 'XRA0213', 'XRA0215',
    'XRA0216', 'XRA0217', 'XRA0218', 'XRA0219', 'XRA0224', 'XRA0227',
    'XRA0314', 'XRA0402'
]

for uid in air_uids:
    bp_path = os.path.join(UNITS_DIR, uid, f"{uid}_unit.bp")
    if not os.path.exists(bp_path):
        print(f"Skipping {uid} (file not found)")
        continue
    with open(bp_path, "r", encoding="utf-8") as f:
        c = f.read()

    # 1. AutoLandTime = -1
    if "AutoLandTime = 0" in c:
        c = c.replace("AutoLandTime = 0", "AutoLandTime = -1")
    elif "AutoLandTime" not in c and "Air = {" in c:
        c = c.replace("Air = {", "Air = {\n        AutoLandTime = -1,")

    # 2. Fuel: FuelUseTime = 0, FuelRechargeRate = 0
    c = re.sub(r'FuelUseTime = \d+,', 'FuelUseTime = 0,', c)
    c = re.sub(r'FuelRechargeRate = \d+,', 'FuelRechargeRate = 0,', c)

    # 3. Dock: RULEUCC_Dock = false
    c = re.sub(r'RULEUCC_Dock = true,', 'RULEUCC_Dock = false,', c)

    # 4. Elevation: ensure at least 12.0 for gunships, 14.0 for fighters/bombers
    is_winged = "Winged = true" in c or "BOMBER" in c
    if is_winged:
        # Elevate to 14.0 if less
        m = re.search(r'Elevation = ([\d\.]+)', c)
        if m and float(m.group(1)) < 14.0:
            c = re.sub(r'Elevation = [\d\.]+,', 'Elevation = 14.0,', c)
            c = re.sub(r'GroundElevation = [\d\.]+,', 'GroundElevation = 14.0,', c)
        # Remove TurnRadius and TurnRate for winged aircraft
        c = re.sub(r'\s*TurnRadius = \d+,', '', c)
        c = re.sub(r'\s*TurnRate = \d+,', '', c)
        # Set MaxSpeed = 0.5 in Physics
        c = re.sub(r'MaxSpeed = \d+(\.\d+)?,', 'MaxSpeed = 0.5,', c)
    else:
        # Gunship elevation: at least 12.0
        m = re.search(r'Elevation = ([\d\.]+)', c)
        if m and float(m.group(1)) < 12.0:
            c = re.sub(r'Elevation = [\d\.]+,', 'Elevation = 12.0,', c)
            c = re.sub(r'GroundElevation = [\d\.]+,', 'GroundElevation = 12.0,', c)

    # 5. Fix weapon turret bones:
    # On T3 fighter XRA0314: change body to firepoint and slave to body
    if uid == "XRA0314":
        c = c.replace("TurretBoneMuzzle = 'body'", "TurretBoneMuzzle = 'firepoint'")
        c = c.replace("TurretBonePitch = 'body'", "TurretBonePitch = 'firepoint'")
        c = c.replace("TurretBoneYaw = 'body'", "TurretBoneYaw = 'firepoint'")
        c = c.replace("TurretPitchRange = 90,", "TurretPitchRange = 55,")
        c = c.replace("TurretYawRange = 180,", "TurretYawRange = 55,")
        if "SlavedToBody" not in c:
            c = c.replace(
                "RateOfFire = 3.0,",
                "RateOfFire = 3.0,\n            SlavedToBody = true,\n            SlavedToBodyArcRange = 50,\n            UseFiringSolutionInsteadOfAimBone = true,"
            )

    # On gunships XRA0216, XRA0217, XRA0218, XRA0219: change TurretBonePitch/Yaw from body to head
    if uid in ["XRA0216", "XRA0217", "XRA0218", "XRA0219"]:
        c = c.replace("TurretBonePitch = 'body'", "TurretBonePitch = 'head'")
        c = c.replace("TurretBoneYaw = 'body'", "TurretBoneYaw = 'head'")

    with open(bp_path, "w", encoding="utf-8") as f:
        f.write(c)
    print(f"Updated {uid}_unit.bp.")

print("\n--- Step 3: Updating Workspace files in E:\\Games\\FAFMods ---")
# 1. Update units/XRA0402/XRA0402_unit.bp
ws_xra0402 = os.path.join(WORKSPACE_DIR, "units", "XRA0402", "XRA0402_unit.bp")
if os.path.exists(ws_xra0402):
    with open(ws_xra0402, "r", encoding="utf-8") as f:
        c = f.read()
    c = c.replace("AutoLandTime = 0,", "AutoLandTime = -1,")
    c = re.sub(r'RULEUCC_Dock = true,', 'RULEUCC_Dock = false,', c)
    with open(ws_xra0402, "w", encoding="utf-8") as f:
        f.write(c)
    print("Updated E:\\Games\\FAFMods\\units\\XRA0402\\XRA0402_unit.bp")

# 2. Update port_all_bar_subtypes.py
port_script = os.path.join(WORKSPACE_DIR, "port_all_bar_subtypes.py")
if os.path.exists(port_script):
    with open(port_script, "r", encoding="utf-8") as f:
        c = f.read()
    c = c.replace("AutoLandTime = 0,", "AutoLandTime = -1,")
    c = c.replace("FuelUseTime = 1500,", "FuelUseTime = 0,")
    c = c.replace("FuelRechargeRate = 150,", "FuelRechargeRate = 0,")
    c = c.replace("Elevation = 8,", "Elevation = 14,")
    c = c.replace("GroundElevation = 8,", "GroundElevation = 14,")
    with open(port_script, "w", encoding="utf-8") as f:
        f.write(c)
    print("Updated port_all_bar_subtypes.py")

# 3. Update build_raptors_expansion.py
build_script = os.path.join(WORKSPACE_DIR, "build_raptors_expansion.py")
if os.path.exists(build_script):
    with open(build_script, "r", encoding="utf-8") as f:
        c = f.read()
    c = c.replace("AutoLandTime = 0,", "AutoLandTime = -1,")
    c = c.replace("RULEUCC_Dock = true,", "RULEUCC_Dock = false,")
    c = c.replace("Elevation = 9.5,", "Elevation = 14.0,")
    c = c.replace("FuelUseTime = 400,", "FuelUseTime = 0,")
    c = c.replace("FuelRechargeRate = 5,", "FuelRechargeRate = 0,")
    c = c.replace("TurretBonePitch = 'head',", "TurretBonePitch = 'firepoint',")
    c = c.replace("TurretBoneYaw = 'body',", "TurretBoneYaw = 'firepoint',")
    c = c.replace("TurretPitchRange = 90,", "TurretPitchRange = 55,")
    c = c.replace("TurretYawRange = 90,", "TurretYawRange = 55,")
    with open(build_script, "w", encoding="utf-8") as f:
        f.write(c)
    print("Updated build_raptors_expansion.py")

# 4. Update build_raptor_expansion_complete.py
rec_script = os.path.join(WORKSPACE_DIR, "build_raptor_expansion_complete.py")
if os.path.exists(rec_script):
    with open(rec_script, "r", encoding="utf-8") as f:
        c = f.read()
    c = c.replace("AutoLandTime = 0,", "AutoLandTime = -1,")
    with open(rec_script, "w", encoding="utf-8") as f:
        f.write(c)
    print("Updated build_raptor_expansion_complete.py")

# 5. Update build_remaining_bar_units.py
rem_script = os.path.join(WORKSPACE_DIR, "build_remaining_bar_units.py")
if os.path.exists(rem_script):
    with open(rem_script, "r", encoding="utf-8") as f:
        c = f.read()
    c = c.replace("AutoLandTime = 0,", "AutoLandTime = -1,")
    with open(rem_script, "w", encoding="utf-8") as f:
        f.write(c)
    print("Updated build_remaining_bar_units.py")

# 6. Update import_zerok_models.py
zk_script = os.path.join(WORKSPACE_DIR, "import_zerok_models.py")
if os.path.exists(zk_script):
    with open(zk_script, "r", encoding="utf-8") as f:
        c = f.read()
    c = c.replace("AutoLandTime = 0,", "AutoLandTime = -1,")
    with open(zk_script, "w", encoding="utf-8") as f:
        f.write(c)
    print("Updated import_zerok_models.py")

# 7. Update exports/RaptorFaction.zip
zip_path = os.path.join(WORKSPACE_DIR, "exports", "RaptorFaction.zip")
if os.path.exists(zip_path):
    print("Export zip exists. Updating zip with fixed unit blueprints...")
    # Read existing zip and rewrite with updated files from MOD_DIR
    temp_zip = zip_path + ".tmp"
    with zipfile.ZipFile(zip_path, 'r') as zin, zipfile.ZipFile(temp_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            # Check if this item is a modified unit blueprint
            matched_air = None
            for uid in (air_uids + ['XRA0115']):
                if item.filename.lower() == f"raptorfaction/units/{uid.lower()}/{uid.lower()}_unit.bp":
                    matched_air = uid
                    break
            if matched_air:
                src_file = os.path.join(UNITS_DIR, matched_air, f"{matched_air}_unit.bp")
                with open(src_file, 'rb') as sf:
                    zout.writestr(item, sf.read())
            else:
                zout.writestr(item, zin.read(item.filename))
    os.replace(temp_zip, zip_path)
    print("Updated exports\\RaptorFaction.zip successfully.")

print("\n--- All fixes applied successfully! ---")
