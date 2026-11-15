"""
Builds data/raptor_units.json by parsing the Raptor blueprints from the game mod directory.
Extracts comprehensive stats for both agent tools and the human FAF Unit Database web page.
"""

import os
import re
import json
from pathlib import Path
from test_bp_parser import parse_lua_value

BASE_DIR = Path(__file__).resolve().parent
MOD_UNITS_DIR = Path(os.path.expanduser("~")) / "Documents" / "My Games" / "Gas Powered Games" / "Supreme Commander Forged Alliance" / "mods" / "RaptorFaction" / "units"
DATA_DIR = BASE_DIR / "data"
OUTPUT_FILE = DATA_DIR / "raptor_units.json"

def clean_loc(text):
    if not isinstance(text, str):
        return text
    # e.g. "<LOC xra0100_name>Raptor Larva" -> "Raptor Larva" or "<LOC>Amphibious" -> "Amphibious"
    return re.sub(r'<LOC\s*[^>]*>', '', text).strip()

def calculate_dps(weapon):
    damage = weapon.get("Damage", 0)
    if not damage and weapon.get("NukeInnerRingDamage"):
        damage = weapon.get("NukeInnerRingDamage", 0)
    
    rof = weapon.get("RateOfFire", 0) or 0
    muzzle_salvo_size = weapon.get("MuzzleSalvoSize", 1) or 1
    
    # If damage is dealt over time or per projectile:
    dps = round(damage * rof * muzzle_salvo_size, 1)
    return dps, damage, rof

def extract_abilities(bp):
    abilities = []
    display = bp.get("Display", {}) or {}
    for ab in display.get("Abilities", []) or []:
        cleaned = clean_loc(ab)
        if cleaned and cleaned not in abilities:
            abilities.append(cleaned)
            
    cats = bp.get("Categories", []) or []
    intel = bp.get("Intel", {}) or {}
    defense = bp.get("Defense", {}) or {}
    physics = bp.get("Physics", {}) or {}
    
    if physics.get("MotionType") == "RULEUMT_Amphibious" and "Amphibious" not in abilities:
        abilities.append("Amphibious")
    if "ALLTERRAIN" in cats and "All-Terrain" not in abilities:
        abilities.append("All-Terrain")
    if intel.get("OmniRadius", 0) > 0 and "Omni Sensor" not in abilities:
        abilities.append(f"Omni Sensor ({intel.get('OmniRadius')} range)")
    if (intel.get("RadarRadius", 0) > 0 or "RADAR" in cats) and "Radar" not in abilities:
        abilities.append("Radar")
    if (intel.get("SonarRadius", 0) > 0 or "SONAR" in cats) and "Sonar" not in abilities:
        abilities.append("Sonar")
    if (intel.get("RadarStealth", False) or intel.get("SonarStealth", False)) and "Stealth" not in abilities:
        abilities.append("Stealth")
    if defense.get("RegenRate", 0) > 0:
        abilities.append(f"Regenerates (+{int(defense.get('RegenRate'))} hp/s)")
    if "KAMIKAZE" in cats or any(w.get("DamageType") == "Kamikaze" or w.get("WeaponCategory") == "Kamikaze" for w in bp.get("Weapon", []) or []):
        if "Kamikaze" not in abilities:
            abilities.append("Kamikaze Detonation")
    if "EXPERIMENTAL" in cats and "Experimental Titan" not in abilities:
        abilities.append("Experimental Titan")
    if "COMMAND" in cats or "SUBCOMMANDER" in cats:
        abilities.append("Hive Mind Node / Sub-Boss")

    return abilities

def build_unit_record(unit_id, bp):
    general = bp.get("General", {}) or {}
    defense = bp.get("Defense", {}) or {}
    economy = bp.get("Economy", {}) or {}
    physics = bp.get("Physics", {}) or {}
    intel = bp.get("Intel", {}) or {}
    cats = bp.get("Categories", []) or []
    weapons_raw = bp.get("Weapon", []) or []
    veteran_raw = bp.get("Veteran", {}) or {}
    buffs_raw = bp.get("Buffs", {}) or {}
    
    unit_name = clean_loc(general.get("UnitName") or unit_id)
    desc = clean_loc(bp.get("Description", ""))
    
    # Tech Tier
    tech = "T1"
    if "EXPERIMENTAL" in cats:
        tech = "EXP"
    elif "TECH3" in cats:
        tech = "T3"
    elif "TECH2" in cats:
        tech = "T2"
    elif "TECH1" in cats:
        tech = "T1"
        
    # Unit Type / Layer
    utype = "LAND"
    if "AIR" in cats:
        utype = "AIR"
    elif "NAVAL" in cats:
        utype = "NAVAL"
    elif "STRUCTURE" in cats:
        utype = "STRUCTURE"
    elif "DEFENSE" in cats:
        utype = "DEFENSE"
    elif "COMMAND" in cats:
        utype = "COMMAND"
    elif "MOBILE" in cats and "LAND" in cats:
        utype = "LAND"

    # Weapons processing
    weapons = []
    for w in weapons_raw:
        w_name = clean_loc(w.get("DisplayName", w.get("Label", "Weapon")))
        w_cat = w.get("WeaponCategory", "Direct Fire")
        d_type = w.get("DamageType", "Normal")
        type_str = f"{w_cat} ({d_type})"
        
        dps, damage, rof = calculate_dps(w)
        r_min = w.get("MinRadius", 0)
        r_max = w.get("MaxRadius", 0)
        muzzle_vel = w.get("MuzzleVelocity", 0)
        
        # Fire cycle text
        cycle_sec = round(1.0 / rof, 2) if rof > 0 else 0
        salvo_size = w.get("MuzzleSalvoSize", 1) or 1
        fire_cycle_str = f"{salvo_size} shot / {cycle_sec} sec" if salvo_size == 1 else f"{salvo_size} shots / {cycle_sec} sec"
        
        # Turret angles
        pitch_range = w.get("TurretPitchRange", 0)
        pitch_speed = w.get("TurretPitchSpeed", 0)
        yaw_range = w.get("TurretYawRange", 0)
        yaw_speed = w.get("TurretYawSpeed", 0)
        
        turret_pitch_str = f"0-{pitch_range}° @ {pitch_speed}°/s" if pitch_range else "Fixed"
        turret_yaw_str = f"0-{yaw_range}° @ {yaw_speed}°/s" if yaw_range else "Fixed"
        
        weapons.append({
            "name": w_name,
            "label": w.get("Label", ""),
            "type": type_str,
            "category": w_cat,
            "damageType": d_type,
            "dps": dps,
            "damage": damage,
            "rateOfFire": rof,
            "fireCycle": fire_cycle_str,
            "rangeMin": r_min,
            "rangeMax": r_max,
            "rangeStr": f"{r_min} - {r_max}" if r_min > 0 else f"0 - {r_max}",
            "damageRadius": w.get("DamageRadius", 0),
            "muzzleVelocity": muzzle_vel,
            "firingTolerance": w.get("FiringTolerance", 0),
            "firingRandomness": w.get("FiringRandomness", 0) or w.get("FiringRandomnessWhileMoving", 0),
            "turretPitch": turret_pitch_str,
            "turretYaw": turret_yaw_str,
            "projectileId": w.get("ProjectileId", ""),
            "ballisticArc": w.get("BallisticArc", "RULEUBA_None")
        })

    # Total DPS across weapons
    total_dps = sum(w["dps"] for w in weapons if w["category"] != "Death")

    # Veterancy levels
    regen_buffs = buffs_raw.get("Regen", {}) or {}
    base_hp = defense.get("Health", 0)
    base_regen = defense.get("RegenRate", 0)
    veterancy = []
    for lvl in range(1, 6):
        kills = veteran_raw.get(f"Level{lvl}", lvl * 5)
        # In FAF veterancy gives +10% HP per level and regen
        bonus_hp = round(base_hp * (1.0 + lvl * 0.1))
        bonus_regen = base_regen + regen_buffs.get(f"Level{lvl}", lvl * 2)
        veterancy.append({
            "level": lvl,
            "kills": kills,
            "health": bonus_hp,
            "regen": f"{bonus_regen} hp/s"
        })

    hp = defense.get("Health", 0)
    mass = economy.get("BuildCostMass", 0)
    energy = economy.get("BuildCostEnergy", 0)
    build_time = economy.get("BuildTime", 0)
    build_rate = economy.get("BuildRate", 0)
    speed = bp.get("Air", {}).get("MaxAirspeed") or physics.get("MaxSpeed", 0)
    turn_rate = physics.get("TurnRate", 0) or bp.get("Air", {}).get("TurnRate", 0)
    vision = intel.get("VisionRadius", 0)
    water_vision = intel.get("WaterVisionRadius", vision)
    radar = intel.get("RadarRadius", 0)
    sonar = intel.get("SonarRadius", 0)
    omni = intel.get("OmniRadius", 0)
    
    abilities = extract_abilities(bp)
    
    # Specific role heuristics
    role = desc
    uid_l = unit_id.lower()
    if uid_l == "xra0100":
        role = "Mini Swarmer / Fast Raider"
    elif uid_l == "xra0101":
        role = "Assault Swarmer Bot"
    elif uid_l == "xra0102":
        role = "Point Defense Kinetic Spire"
    elif uid_l == "xra0103":
        role = "Suicide Acid Kamikaze"
    elif uid_l == "xra0104":
        role = "Bio-Acid Carpet Bomber"
    elif uid_l == "xra0106":
        role = "Anti-Air Spore Defense Spire"
    elif uid_l == "xra0107":
        role = "Gestation Roost & Biomass Hive"
    elif uid_l == "xra0108":
        role = "Corrosive Acid Defense Spire"
    elif uid_l == "xra0109":
        role = "Bio-Weaver (Mobile Engineer & Healer)"
    elif uid_l == "xra0110":
        role = "Subterranean Ambush Spire"
    elif uid_l == "xra0111":
        role = "High-Speed Air Recon Scout"
    elif uid_l == "xra0115":
        role = "Air Swarm Interceptor"
    elif uid_l == "xra0201":
        role = "Heavy All-Terrain Crawler"
    elif uid_l == "xra0202":
        role = "Mobile Bio-Artillery / Mortar Bug"
    elif uid_l == "xra0203":
        role = "EMP Shock Kamikaze & Shield Breaker"
    elif uid_l == "xra0204":
        role = "Living Brood Swarm Bomber"
    elif uid_l == "xra0205":
        role = "Hovering Hunter Gunship"
    elif uid_l == "xra0206":
        role = "All-Terrain Bio-Flamethrower"
    elif uid_l == "xra0208":
        role = "Subterranean Bio-Worm Defense"
    elif uid_l == "xra0209":
        role = "Heavy Volcanic Magma Worm"
    elif uid_l == "xra0301":
        role = "Heavy Assault Apex Behemoth"
    elif uid_l == "xra0302":
        role = "Psychic Brain Bug Overseer"
    elif uid_l == "xra0303":
        role = "Raptor Matriarch Sub-Boss"
    elif uid_l == "xra0304":
        role = "Strategic Bio-Nuke Worm Silo"
    elif uid_l == "xra0306":
        role = "Living Brood Artillery Spire"
    elif uid_l == "xra0307":
        role = "Bio-EMP Disruption Artillery Spire"
    elif uid_l == "xra0308":
        role = "Corrosive Acid Artillery Spire"
    elif uid_l == "xra0309":
        role = "Planetary Cataclysm Meteor Spire"
    elif uid_l == "xra0310":
        role = "Behemoth Heavy Acid Dodo"
    elif uid_l == "xra0315":
        role = "Strategic Anti-Nuke Defense Silo"
    elif uid_l == "xra0401":
        role = "Experimental Matriarch Queen Titan"

    return {
        "id": unit_id.upper(),
        "id_lower": unit_id.lower(),
        "name": unit_name,
        "description": desc,
        "faction": "Raptor",
        "tech": tech,
        "type": utype,
        "role": role,
        "categories": cats,
        "strategicIcon": bp.get("StrategicIconName", "icon_bot1_generic"),
        "icon": f"/static/img/units/{unit_id.lower()}.png",
        "iconDds": f"/mods/RaptorFaction/icons/units/{unit_id.lower()}_icon.dds",
        "stats": {
            "health": hp,
            "maxHealth": hp,
            "regen": defense.get("RegenRate", 0),
            "armorType": defense.get("ArmorType", "Normal"),
            "mass": mass,
            "energy": energy,
            "buildTime": build_time,
            "buildRate": build_rate,
            "massProd": economy.get("ProductionPerSecondMass", 0),
            "energyProd": economy.get("ProductionPerSecondEnergy", 0),
            "massStorage": economy.get("StorageMass", 0),
            "energyStorage": economy.get("StorageEnergy", 0),
            "speed": speed,
            "turnRate": turn_rate,
            "motionType": physics.get("MotionType", "RULEUMT_None"),
            "accel": physics.get("MaxAcceleration", 0),
            "brake": physics.get("MaxBrake", 0),
            "vision": vision,
            "waterVision": water_vision,
            "radar": radar,
            "sonar": sonar,
            "omni": omni,
            "totalDps": total_dps,
            "wreckageHealth": round(hp * 0.9),
            "wreckageMass": round(mass * 0.81)
        },
        "abilities": abilities,
        "veterancy": veterancy,
        "weapons": weapons
    }

def generate_raptor_json():
    print(f"Scanning blueprints in {MOD_UNITS_DIR}...")
    if not MOD_UNITS_DIR.exists():
        print(f"Directory {MOD_UNITS_DIR} does not exist!")
        return {}

    units_data = {}
    for entry in sorted(os.listdir(MOD_UNITS_DIR)):
        unit_dir = MOD_UNITS_DIR / entry
        if not unit_dir.is_dir():
            continue
        bp_path = unit_dir / f"{entry}_unit.bp"
        if not bp_path.exists():
            continue

        with open(bp_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        res, _ = parse_lua_value(content)
        if isinstance(res, dict):
            rec = build_unit_record(entry, res)
            units_data[entry.upper()] = rec

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(units_data, f, indent=2)

    print(f"Successfully generated {OUTPUT_FILE} with {len(units_data)} Raptor units!")
    return units_data

if __name__ == "__main__":
    generate_raptor_json()
