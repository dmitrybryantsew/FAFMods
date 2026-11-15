"""
Build & Deploy Dedicated High-Resolution Icons for All Raptor Faction Units
=============================================================================
Maps each of the 64 Raptor Swarm units (T1 through Experimental) to its
authentic, high-resolution source portrait from Beyond-All-Reason (BAR) and
Zero-K archives.

Generates:
  1. 128x128 DDS (ARGB8888 with mipmaps) in every unit directory:
     mods/RaptorFaction/units/<UID>/<UID>_icon.dds
  2. 128x128 DDS in mod icons directory:
     mods/RaptorFaction/icons/units/<uid>_icon.dds
  3. 128x128 PNG web assets in:
     static/img/units/<uid>.png and <uid>_icon.png
  4. Automatically refreshes data/raptor_units.json via build_raptor_json.py.
"""

import os
import io
import gzip
import zipfile
import shutil
from pathlib import Path
from PIL import Image

# Directories
BASE_DIR = Path(__file__).resolve().parent
MOD_DIR = Path(os.path.expanduser("~")) / "Documents" / "My Games" / "Gas Powered Games" / "Supreme Commander Forged Alliance" / "mods" / "RaptorFaction"
MOD_UNITS_DIR = MOD_DIR / "units"
MOD_ICONS_DIR = MOD_DIR / "icons" / "units"
LOCAL_UNITS_DIR = BASE_DIR / "units"
STATIC_IMG_DIR = BASE_DIR / "static" / "img" / "units"

MOD_ICONS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_IMG_DIR.mkdir(parents=True, exist_ok=True)

# Archives
BAR_PKG_PATH = r"P:\Games\Beyond-All-Reason\data\packages\ad33f718d83a34e194d7182194a91ede.sdp"
BAR_POOL_DIR = r"P:\Games\Beyond-All-Reason\data\pool"
ZK_PATH = r"P:\SteamLibrary\steamapps\common\Zero-K\games\zk-stable.sdz"

# ---------------------------------------------------------------------------
# Unit Mapping Dictionary: Unit ID -> (SourceArchive, RelativePath)
# ---------------------------------------------------------------------------
UNIT_PORTRAIT_MAP = {
    # --- Tier 1 Land & Swarmers ---
    "XRA0100": ("BAR", "unitpics/raptors/raptor1d.dds"),                    # Raptor Larva
    "XRA0101": ("BAR", "unitpics/raptors/raptor1.dds"),                     # Raptor Swarmer
    "XRA0102": ("BAR", "unitpics/raptors/raptor_turrets.dds"),              # Chitin Spine Spire
    "XRA0103": ("BAR", "unitpics/raptors/raptor_dodo1.dds"),                # Volatile Acid Tick
    "XRA0104": ("BAR", "unitpics/raptors/raptoracidbomber.dds"),            # Bio-Acid Bomber
    "XRA0106": ("BAR", "unitpics/raptors/raptor_turrets_antiair.dds"),      # Bio-Spore AA Spire
    "XRA0107": ("BAR", "unitpics/raptors/raptor_hive.dds"),                 # Raptor Gestation Roost
    "XRA0108": ("BAR", "unitpics/raptors/raptor_turrets_acid.dds"),         # Bio-Acid Spire
    "XRA0109": ("BAR", "unitpics/raptors/raptorh1b.dds"),                   # Bio-Weaver
    "XRA0110": ("BAR", "unitpics/raptors/raptor_turretl.dds"),              # Burrowing Ambush Spire
    "XRA0111": ("BAR", "unitpics/raptors/raptorairscout.dds"),              # Bio-Recon Scout
    "XRA0112": ("BAR", "unitpics/raptors/raptoracidswarmer.dds"),           # Caustic Acid Swarmer
    "XRA0113": ("BAR", "unitpics/raptors/raptor1z.dds"),                    # Shock EMP Swarmer
    "XRA0114": ("BAR", "unitpics/raptors/raptor1y.dds"),                    # Brood Swarmer
    "XRA0115": ("BAR", "unitpics/raptors/raptorw1_mini.dds"),               # Raptor Wing Swarmer
    "XRA0116": ("ZK",  "unitpics/chicken_digger.png"),                      # Subterranean Digger
    "XRA0121": ("ZK",  "unitpics/chickend.png"),                            # Chitin Spore Spire

    # --- Tier 2 Land, Air, & Support ---
    "XRA0201": ("BAR", "unitpics/raptors/raptorc3.dds"),                    # Heavy Raptor Crawler
    "XRA0202": ("BAR", "unitpics/raptors/raptoracidarty.dds"),              # Bio-Mortar Bug
    "XRA0203": ("BAR", "unitpics/raptors/raptor_dodo1_electric.dds"),       # Bio-EMP Shock Tick
    "XRA0204": ("BAR", "unitpics/raptors/raptorbroodbomber.dds"),           # Brood Swarm Bomber
    "XRA0205": ("BAR", "unitpics/raptors/raptora2.dds"),                    # Bio-Hunter Gunship
    "XRA0206": ("BAR", "unitpics/raptors/raptorpyroallterrain.dds"),        # Pyro Raptor
    "XRA0208": ("ZK",  "unitpics/chickenwurm.png"),                         # Burrowing Bio-Worm
    "XRA0209": ("BAR", "unitpics/raptors/raptor_turrets_electric.dds"),     # Volcanic Magma Worm
    "XRA0210": ("BAR", "unitpics/raptors/raptors1.dds"),                    # Chitin Needle Spiker
    "XRA0211": ("BAR", "unitpics/raptors/raptor1x_spectre.dds"),           # Spectre Cloaked Swarmer
    "XRA0213": ("BAR", "unitpics/raptors/raptor_dodoair.dds"),              # Bio-Dive Kamikaze Tick
    "XRA0215": ("BAR", "unitpics/raptors/raptorhealer.dds"),                # Bio-Healer Drone
    "XRA0216": ("BAR", "unitpics/raptors/raptoracidassault.dds"),           # Corrosive Acid Gunship
    "XRA0217": ("BAR", "unitpics/raptors/raptore2.dds"),                    # Bio-EMP Shock Gunship
    "XRA0218": ("BAR", "unitpics/raptors/raptorf1b.dds"),                   # Bio-Inferno Gunship
    "XRA0219": ("BAR", "unitpics/raptors/raptorf1.dds"),                    # Bio-Spore AA Gunship
    "XRA0222": ("BAR", "unitpics/raptors/raptorbroodarty.dds"),             # Mobile Brood Mortar Bug
    "XRA0224": ("BAR", "unitpics/raptors/raptorebomber1.dds"),              # Bio-EMP Disruption Bomber
    "XRA0225": ("ZK",  "unitpics/chicken_shield.png"),                      # Bio-Shield Beetle
    "XRA0226": ("ZK",  "unitpics/chicken_rafflesia.png"),                   # Rafflesia Shield Bloom
    "XRA0227": ("ZK",  "unitpics/chicken_blimpy.png"),                      # Bio-Zeppelin Blimpy

    # --- Tier 3 Heavy Assault & Artilleries ---
    "XRA0301": ("BAR", "unitpics/raptors/raptorapexallterrainassault.dds"), # Apex Raptor Behemoth
    "XRA0302": ("BAR", "unitpics/raptors/raptorr1.dds"),                    # Brain Bug Overseer
    "XRA0303": ("BAR", "unitpics/raptors/raptor_miniqueen_basic.dds"),      # Raptor Matriarch
    "XRA0304": ("BAR", "unitpics/raptors/raptor_turretl_antinuke.dds"),     # Apex Bio-Nuke Worm
    "XRA0306": ("BAR", "unitpics/raptors/raptorbroodarty.dds"),             # Brood Artillery Spire
    "XRA0307": ("BAR", "unitpics/raptors/raptorearty2.dds"),                # Bio-EMP Artillery Spire
    "XRA0308": ("BAR", "unitpics/raptors/raptoracidartyxl.dds"),            # Corrosive Acid Artillery Spire
    "XRA0309": ("BAR", "unitpics/raptors/raptor_turretxl_meteor.dds"),      # Meteor Cataclysm Spire
    "XRA0310": ("BAR", "unitpics/raptors/raptor_dodo2.dds"),                # Behemoth Heavy Dodo
    "XRA0312": ("BAR", "unitpics/raptors/raptors2.dds"),                    # Apex Heavy Needle Spiker
    "XRA0313": ("BAR", "unitpics/raptors/raptor2_spectre.dds"),             # Spectre Stalker Behemoth
    "XRA0314": ("BAR", "unitpics/raptors/raptorw2.dds"),                    # Apex Air Crow
    "XRA0315": ("BAR", "unitpics/raptors/raptor_turretl_antinuke.dds"),     # Chitinous Anti-Nuke Worm
    "XRA0318": ("BAR", "unitpics/raptors/raptors2_spectre.dds"),            # Spectre Phantom Spiker
    "XRA0320": ("BAR", "unitpics/raptors/raptor_dodo2_electric.dds"),      # Behemoth EMP Shock Dodo
    "XRA0322": ("BAR", "unitpics/raptors/raptorearty1.dds"),                # Mobile EMP Bio-Artillery
    "XRA0323": ("BAR", "unitpics/raptors/raptoracidarty.dds"),              # Mobile Acid Bio-Artillery
    "XRA0328": ("ZK",  "unitpics/chicken_tiamat.png"),                      # Tiamat Bio-Juggernaut
    "XRA0329": ("ZK",  "unitpics/chicken_dragon.png"),                      # Apex White Dragon Herald

    # --- Tier 3 Matriarch Sub-Bosses ---
    "XRA0331": ("BAR", "unitpics/raptors/raptor_miniqueen_acid.dds"),       # Acid Matriarch Sub-Boss
    "XRA0332": ("BAR", "unitpics/raptors/raptor_miniqueen_electric.dds"),   # Storm Matriarch Sub-Boss
    "XRA0333": ("BAR", "unitpics/raptors/raptor_miniqueen_fire.dds"),       # Pyro Matriarch Sub-Boss
    "XRA0334": ("BAR", "unitpics/raptors/raptor_miniqueen_healer.dds"),     # Broodmother Matriarch Sub-Boss
    "XRA0335": ("BAR", "unitpics/raptors/raptor_miniqueen_spectre.dds"),    # Shadow Matriarch Sub-Boss

    # --- Experimentals & Supreme Bosses ---
    "XRA0401": ("BAR", "unitpics/raptors/epic_raptorq.dds"),                # Matriarch Raptor Queen
    "XRA0402": ("ZK",  "unitpics/chickenflyerqueen.png"),                   # Apex Sky Matriarch Queen
}


class AssetLoader:
    def __init__(self):
        print(f"Indexing BAR package: {BAR_PKG_PATH}...")
        self.bar_entries = {}
        if os.path.exists(BAR_PKG_PATH):
            with gzip.open(BAR_PKG_PATH, "rb") as gz:
                pkg_data = gz.read()
            pos = 0
            while pos < len(pkg_data):
                namelen = pkg_data[pos]
                pos += 1
                name = pkg_data[pos:pos+namelen].decode("utf-8", "ignore")
                pos += namelen
                md5_hex = pkg_data[pos:pos+16].hex()
                pos += 24
                self.bar_entries[name.lower().replace("\\", "/")] = md5_hex
            print(f"Indexed {len(self.bar_entries)} BAR files.")
        else:
            print(f"[Warning] BAR package not found at: {BAR_PKG_PATH}")

        print(f"Opening Zero-K package: {ZK_PATH}...")
        self.zk_zip = None
        if os.path.exists(ZK_PATH):
            self.zk_zip = zipfile.ZipFile(ZK_PATH, "r")
            print(f"Indexed {len(self.zk_zip.namelist())} Zero-K files.")
        else:
            print(f"[Warning] Zero-K package not found at: {ZK_PATH}")

    def load_image(self, source, rel_path):
        rel_key = rel_path.lower().replace("\\", "/")
        if source == "BAR":
            md5 = self.bar_entries.get(rel_key)
            if not md5:
                raise FileNotFoundError(f"BAR file not found: {rel_path}")
            sub = md5[:2]
            fn = md5[2:] + ".gz"
            pool_path = os.path.join(BAR_POOL_DIR, sub, fn)
            with gzip.open(pool_path, "rb") as f:
                raw_bytes = f.read()
            return Image.open(io.BytesIO(raw_bytes)).convert("RGBA")

        elif source == "ZK":
            if not self.zk_zip:
                raise FileNotFoundError("Zero-K package not loaded.")
            raw_bytes = self.zk_zip.read(rel_path)
            return Image.open(io.BytesIO(raw_bytes)).convert("RGBA")

        else:
            raise ValueError(f"Unknown source: {source}")


def deploy_raptor_icons():
    print("\n" + "=" * 70)
    print("STARTING DEDICATED RAPTOR UNIT ICON DEPLOYMENT")
    print("=" * 70)

    loader = AssetLoader()
    success_count = 0
    total_count = len(UNIT_PORTRAIT_MAP)

    for uid, (src, rel_path) in sorted(UNIT_PORTRAIT_MAP.items()):
        try:
            im = loader.load_image(src, rel_path)

            # Resize to standard 128x128 with Lanczos resampling
            im_128 = im.resize((128, 128), Image.Resampling.LANCZOS)

            # 1. Target directory in RaptorFaction mod units:
            unit_mod_dir = MOD_UNITS_DIR / uid
            if unit_mod_dir.exists():
                dds_target = unit_mod_dir / f"{uid}_icon.dds"
                im_128.save(str(dds_target), format="DDS")

            # 2. Target directory in mod root icons/units/:
            im_128.save(str(MOD_ICONS_DIR / f"{uid}_icon.dds"), format="DDS")
            im_128.save(str(MOD_ICONS_DIR / f"{uid.lower()}_icon.dds"), format="DDS")

            # 3. Target directory in local repo units (if present):
            local_unit_dir = LOCAL_UNITS_DIR / uid
            if local_unit_dir.exists():
                im_128.save(str(local_unit_dir / f"{uid}_icon.dds"), format="DDS")

            # 4. Target web PNG assets in static/img/units/:
            im_128.save(str(STATIC_IMG_DIR / f"{uid.lower()}.png"), format="PNG")
            im_128.save(str(STATIC_IMG_DIR / f"{uid.lower()}_icon.png"), format="PNG")
            im_128.save(str(STATIC_IMG_DIR / f"{uid}.png"), format="PNG")
            im_128.save(str(STATIC_IMG_DIR / f"{uid}_icon.png"), format="PNG")

            success_count += 1
            print(f"[{success_count:02d}/{total_count}] Successfully generated {uid} icon from {src}:{rel_path}")

        except Exception as e:
            print(f"[ERROR] Failed to process {uid} ({src}:{rel_path}): {e}")

    print("\n" + "=" * 70)
    print(f"DEPLOYMENT SUMMARY: {success_count}/{total_count} UNIT ICONS GENERATED & DEPLOYED")
    print("=" * 70)

    # 5. Refresh data/raptor_units.json
    print("\nRefreshing data/raptor_units.json via build_raptor_json.py...")
    try:
        from build_raptor_json import generate_raptor_json
        generate_raptor_json()
        print("Updated data/raptor_units.json successfully!")
    except Exception as e:
        print(f"[Warning] Could not regenerate raptor_units.json: {e}")


if __name__ == "__main__":
    deploy_raptor_icons()
