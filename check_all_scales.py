import struct
import os
import glob
import sys

units_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction\units"

results = []
for u in sorted(os.listdir(units_dir)):
    u_dir = os.path.join(units_dir, u)
    if not os.path.isdir(u_dir):
        continue
    scms = glob.glob(os.path.join(u_dir, "*.scm"))
    bps = glob.glob(os.path.join(u_dir, "*_unit.bp"))
    if not scms or not bps:
        continue
    
    with open(scms[0], "rb") as f:
        data = f.read()
    magic, ver, b_off, b_cnt, v_off, ev_off, v_cnt = struct.unpack("<4s6I", data[:28])
    if v_cnt == 0:
        continue
    verts = []
    for i in range(v_cnt):
        vx, vy, vz = struct.unpack("<3f", data[v_off + i*68 : v_off + i*68 + 12])
        verts.append((vx, vy, vz))
    min_x, max_x = min(v[0] for v in verts), max(v[0] for v in verts)
    min_y, max_y = min(v[1] for v in verts), max(v[1] for v in verts)
    min_z, max_z = min(v[2] for v in verts), max(v[2] for v in verts)
    dx, dy, dz = max_x - min_x, max_y - min_y, max_z - min_z

    with open(bps[0], "r", encoding="utf-8", errors="ignore") as f:
        bp_lines = f.readlines()
    
    def get_val(key, default=None):
        for line in bp_lines:
            stripped = line.strip()
            if stripped.startswith(key) and "=" in stripped:
                parts = stripped.split("=", 1)[1].split(",")[0].strip().strip("'\"")
                try:
                    return float(parts)
                except ValueError:
                    return parts
        return default

    uscale = float(get_val("UniformScale", 1.0))
    sel_x = float(get_val("SelectionSizeX", 0.5))
    sel_z = float(get_val("SelectionSizeZ", 0.5))
    sz_x = float(get_val("SizeX", 1.0))
    sz_y = float(get_val("SizeY", 1.0))
    sz_z = float(get_val("SizeZ", 1.0))
    lb_off = float(get_val("LifeBarOffset", 0.5))
    lb_sz = float(get_val("LifeBarSize", 1.0))
    
    unit_name = ""
    desc = ""
    for line in bp_lines:
        if "UnitName" in line and "=" in line:
            unit_name = line.split("=", 1)[1].split(",")[0].strip().strip("'\"")
        if "Description" in line and "=" in line:
            desc = line.split("=", 1)[1].split(",")[0].strip().strip("'\"")

    rx, ry, rz = dx * uscale, dy * uscale, dz * uscale
    sel_w = sel_x * 2.0
    sel_l = sel_z * 2.0
    ratio = rx / sel_w if sel_w > 0 else 1.0

    results.append({
        "id": u, "bp_path": bps[0], "name": unit_name, "desc": desc,
        "mesh": (dx, dy, dz), "mesh_y": (min_y, max_y), "mesh_z": (min_z, max_z),
        "scale": uscale, "rendered": (rx, ry, rz),
        "sel": (sel_x, sel_z), "size": (sz_x, sz_y, sz_z),
        "lb": (lb_sz, lb_off), "ratio": ratio
    })

print(f"{'Unit':8s} | {'Scale':5s} | {'Mesh (X,Y,Z)':17s} | {'Rendered (X,Y,Z)':19s} | {'SelBox (W,L)':13s} | {'Ratio':5s} | {'Name'}")
print("-" * 105)
for r in results:
    u = r["id"]
    sc = r["scale"]
    mx, my, mz = r["mesh"]
    rx, ry, rz = r["rendered"]
    sx, sz = r["sel"]
    ratio = r["ratio"]
    name = r["name"]
    print(f"{u:8s} | {sc:5.3f} | ({mx:4.1f},{my:4.1f},{mz:4.1f})   | ({rx:4.1f},{ry:4.1f},{rz:4.1f})     | ({sx*2:4.1f},{sz*2:4.1f})      | {ratio:5.2f} | {name}")
