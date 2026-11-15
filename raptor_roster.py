"""
Raptor Unit Roster - Agent & Developer Tool
Provides programmatic access to the Raptor Swarm Faction unit roster.
Includes detailed blueprints, combat stats, economy costs, physics, abilities, and weapons.

Usage (in Python for Agents / Code):
    from raptor_roster import get_raptor_roster, get_raptor_roster_summary, get_raptor_unit

    # Get list of all raptor units:
    roster = get_raptor_roster()

    # Filter by tech tier:
    t3_units = get_raptor_roster(tier="T3")

    # Get single unit details:
    queen = get_raptor_unit("XRA0401")

    # Get markdown table summary for LLM context / reports:
    summary_md = get_raptor_roster_summary()

CLI Usage:
    python raptor_roster.py
    python raptor_roster.py --tier T1
    python raptor_roster.py --unit XRA0401
    python raptor_roster.py --json
    python raptor_roster.py --refresh
"""

import sys
import os
import json
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "raptor_units.json"
MOD_UNITS_DIR = Path(os.path.expanduser("~")) / "Documents" / "My Games" / "Gas Powered Games" / "Supreme Commander Forged Alliance" / "mods" / "RaptorFaction" / "units"

_CACHED_ROSTER = None

def _load_roster(force_reload=False):
    global _CACHED_ROSTER
    if _CACHED_ROSTER is not None and not force_reload:
        return _CACHED_ROSTER

    if DATA_FILE.exists() and not force_reload:
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                _CACHED_ROSTER = json.load(f)
                return _CACHED_ROSTER
        except Exception:
            pass

    # If cache not present or forced reload, try generating from build_raptor_json
    try:
        from build_raptor_json import generate_raptor_json
        _CACHED_ROSTER = generate_raptor_json()
        return _CACHED_ROSTER
    except Exception as e:
        print(f"[Warning] Failed to generate raptor roster dynamically: {e}", file=sys.stderr)
        _CACHED_ROSTER = {}
        return _CACHED_ROSTER


def get_raptor_roster(tier=None, category=None, utype=None, as_dict=False, format="dict"):
    """
    Get current Raptor Swarm unit roster.

    Parameters:
        tier (str, optional): Filter by tier ('T1', 'T2', 'T3', 'EXP').
        category (str, optional): Filter by FAF category tag (e.g. 'DIRECTFIRE', 'KAMIKAZE', 'ALLTERRAIN').
        utype (str, optional): Filter by type ('LAND', 'AIR', 'DEFENSE', 'STRUCTURE', 'COMMAND').
        as_dict (bool): If True, returns a dict keyed by unit ID. Defaults to False (returns list).
        format (str): 'dict' (Python objects), 'json' (JSON string), or 'summary' (Markdown table).

    Returns:
        list | dict | str: The filtered Raptor unit roster.
    """
    roster_dict = _load_roster()
    units = list(roster_dict.values())

    # Tier filter
    if tier:
        tier_norm = tier.upper().strip()
        units = [u for u in units if u.get("tech", "").upper() == tier_norm]

    # Type filter
    if utype:
        type_norm = utype.upper().strip()
        units = [u for u in units if u.get("type", "").upper() == type_norm]

    # Category filter
    if category:
        cat_norm = category.upper().strip()
        units = [u for u in units if cat_norm in [c.upper() for c in u.get("categories", [])]]

    # Sort units naturally: T1, T2, T3, EXP, then ID
    tier_order = {"T1": 1, "T2": 2, "T3": 3, "EXP": 4}
    units.sort(key=lambda u: (tier_order.get(u.get("tech", "T1"), 9), u.get("id", "")))

    if format == "summary":
        return _format_markdown_table(units)
    elif format == "json":
        if as_dict:
            return json.dumps({u["id"]: u for u in units}, indent=2)
        return json.dumps(units, indent=2)

    if as_dict:
        return {u["id"]: u for u in units}
    return units


# Convenient Aliases for Agents
get_raptor_unit_roster = get_raptor_roster
get_current_raptor_roster = get_raptor_roster


def get_raptor_unit(unit_id):
    """
    Retrieve deep blueprint specifications for a single Raptor unit.

    Parameters:
        unit_id (str): Unit ID (case-insensitive, e.g. 'xra0101' or 'XRA0401').

    Returns:
        dict | None: Complete unit data or None if not found.
    """
    roster_dict = _load_roster()
    uid = unit_id.upper().strip()
    return roster_dict.get(uid)


def get_raptor_unit_by_id(unit_id):
    """Alias for get_raptor_unit."""
    return get_raptor_unit(unit_id)


def get_raptor_roster_summary(tier=None):
    """
    Returns a human-readable and LLM-friendly Markdown table summarizing the Raptor roster.
    """
    units = get_raptor_roster(tier=tier)
    return _format_markdown_table(units)


def _format_markdown_table(units):
    lines = [
        f"### Raptor Swarm Unit Roster ({len(units)} Units)",
        "",
        "| ID | Tier | Name | Role | Health | Regen | Mass Cost | Speed | Total DPS | Key Weapon & Range | Abilities |",
        "| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |"
    ]

    for u in units:
        uid = u["id"]
        tier = u.get("tech", "T1")
        name = u.get("name", "")
        role = u.get("role", "")
        stats = u.get("stats", {})
        hp = stats.get("health", 0)
        regen = f"+{stats.get('regen', 0)}/s" if stats.get("regen") else "0"
        mass = stats.get("mass", 0)
        speed = stats.get("speed", 0)
        dps = round(stats.get("totalDps", 0))

        # Main weapon
        weapons = u.get("weapons", [])
        if weapons:
            w = weapons[0]
            w_info = f"{w['name']} ({w['rangeStr']} r, {w['dps']} dps)"
        else:
            w_info = "None (Constructor/Nexus)"

        # Abilities (top 2-3)
        abilities = ", ".join(u.get("abilities", [])[:2]) or "None"

        lines.append(f"| `{uid}` | **{tier}** | **{name}** | {role} | {hp:,} | {regen} | {mass:,} | {speed} | {dps:,} | {w_info} | {abilities} |")

    return "\n".join(lines)


def refresh_raptor_roster():
    """Forces a reload and rebuild of the roster from the local mod blueprints."""
    try:
        from build_raptor_json import generate_raptor_json
        data = generate_raptor_json()
        global _CACHED_ROSTER
        _CACHED_ROSTER = data
        return data
    except Exception as e:
        print(f"Error refreshing roster: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Query and view the Raptor Swarm Unit Roster.")
    parser.add_argument("--tier", choices=["T1", "T2", "T3", "EXP"], help="Filter units by Tech Tier")
    parser.add_argument("--type", dest="utype", choices=["LAND", "AIR", "DEFENSE", "STRUCTURE", "COMMAND"], help="Filter by Unit Type")
    parser.add_argument("--unit", help="Get full stats for a specific unit ID (e.g. XRA0401)")
    parser.add_argument("--json", action="store_true", help="Output full JSON instead of table")
    parser.add_argument("--refresh", action="store_true", help="Re-scan and refresh blueprints from disk")
    args = parser.parse_args()

    if args.refresh:
        print("Refreshing roster from mod blueprints...")
        refresh_raptor_roster()
        print("Done!")
        return

    if args.unit:
        unit = get_raptor_unit(args.unit)
        if not unit:
            print(f"Unit '{args.unit}' not found in Raptor roster.")
            sys.exit(1)
        if args.json:
            print(json.dumps(unit, indent=2))
        else:
            print(f"=== {unit['id']}: {unit['name']} ({unit['tech']} {unit['role']}) ===")
            print(f"Description: {unit['description']}")
            print(f"Stats: HP={unit['stats']['health']} (Regen={unit['stats']['regen']}), Mass={unit['stats']['mass']}, Energy={unit['stats']['energy']}, Speed={unit['stats']['speed']}, DPS={unit['stats']['totalDps']}")
            print(f"Abilities: {', '.join(unit['abilities'])}")
            print("Weapons:")
            for w in unit['weapons']:
                print(f"  - {w['name']} [{w['type']}]: {w['damage']} dmg @ {w['rateOfFire']} rof ({w['dps']} dps), Range: {w['rangeStr']}, Vel: {w['muzzleVelocity']}")
        return

    if args.json:
        print(get_raptor_roster(tier=args.tier, utype=args.utype, format="json"))
    else:
        print(get_raptor_roster_summary(tier=args.tier))

if __name__ == "__main__":
    main()
