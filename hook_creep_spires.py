import os

units_dir = r"C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction\units"
spires = [
    ('XRA0304', 36, 1.0),
    ('XRA0315', 34, 1.0),
    ('XRA0306', 36, 1.0),
    ('XRA0307', 36, 1.0),
    ('XRA0308', 40, 1.0),
    ('XRA0309', 36, 1.0),
]

for uid, rad, rate in spires:
    p = os.path.join(units_dir, uid, f"{uid}_script.lua")
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()

    if "RaptorCreep" not in content:
        content = "local RaptorCreep = import('/mods/RaptorFaction/lua/RaptorCreep.lua')\n" + content

        if "OnCreate = function(self)" in content:
            content = content.replace(
                "CStructureUnit.OnCreate(self)",
                f"CStructureUnit.OnCreate(self)\n        if self:GetFractionComplete() == 1.0 then\n            RaptorCreep.StartCreepNode(self, {rad}, {rate})\n        end"
            )
            content = content.replace(
                "OnKilled = function",
                f"OnStopBeingBuilt = function(self, builder, layer)\n        CStructureUnit.OnStopBeingBuilt(self, builder, layer)\n        if not self.CreepNode then\n            RaptorCreep.StartCreepNode(self, {rad}, {rate})\n        end\n    end,\n\n    OnKilled = function"
            )
        else:
            hook_code = f"""
    OnCreate = function(self)
        CStructureUnit.OnCreate(self)
        if self:GetFractionComplete() == 1.0 then
            RaptorCreep.StartCreepNode(self, {rad}, {rate})
        end
    end,

    OnStopBeingBuilt = function(self, builder, layer)
        CStructureUnit.OnStopBeingBuilt(self, builder, layer)
        if not self.CreepNode then
            RaptorCreep.StartCreepNode(self, {rad}, {rate})
        end
    end,
"""
            content = content.replace("OnKilled = function", hook_code.strip() + "\n\n    OnKilled = function")

        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {uid}")

print("All T3 spires updated with RaptorCreep!")
