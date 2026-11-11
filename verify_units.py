import os, re

units_dir = r'C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction\units'
units = sorted(os.listdir(units_dir))
print(f"Total units found: {len(units)}")
for u in units:
    bp = os.path.join(units_dir, u, f"{u}_unit.bp")
    if not os.path.exists(bp):
        print(f"MISSING BP: {u}")
        continue
    txt = open(bp, "r", encoding="utf-8", errors="ignore").read()
    fn = re.findall(r"FactionName\s*=\s*['\"]([^'\"]+)['\"]", txt)
    cats = re.findall(r"Categories\s*=\s*\{([^}]+)\}", txt, re.DOTALL)
    cat_list = [c.strip().strip("'\",") for c in cats[0].split("\n") if c.strip().strip("'\",")] if cats else []
    
    # Check for foreign factions
    foreign = [c for c in cat_list if any(f in c for f in ['CYBRAN', 'SERAPHIM', 'AEON', 'UEF'])]
    print(f"{u}: Faction={fn[0] if fn else 'None'} | ForeignCats={foreign} | TotalCats={len(cat_list)}")
