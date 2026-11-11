/**
 * FAF Mod Forge - Central State Store & Cross-Page Synchronization
 * Manages localStorage persistence for Unit Buffs, Limits, Popups, and Relics.
 */

const ForgeStore = (() => {
  const KEYS = {
    BUFFS: "faf_mod_buffs",
    LIMITS: "faf_mod_limits",
    POPUPS: "faf_mod_popups",
    RELICS: "faf_mod_relics",
    LOOTBOX: "faf_mod_lootbox",
    PROFILES: "faf_mod_profiles",
    META: "faf_mod_meta",
    INITIALIZED: "faf_mod_initialized_v1"
  };

  const DEFAULT_LOOTBOX = {
    enabled: true,
    name: "Quantum Surprise Vault",
    modelBpId: "uec1904",
    modelName: "UEF Communication Tower",
    spawnDelay: 30,
    locMode: "center", // "center", "random_center", "coords"
    customX: 256,
    customZ: 256,
    spawnCount: 2,
    openMode: "instant_crack", // "instant_crack" (Capture & Run), "interactive" (Contested Casino)
    observerGmName: "DrReed",
    observerGmPlacement: true,
    respawnMode: "single_use", // "reusable", "single_use"
    cooldownSec: 60,
    spinCostEnergy: 500,
    spinCostMass: 0,
    claimMode: "both", // "both", "capture", "proximity"
    dropTable: [
      {
        id: "prize_exp",
        name: "🌟 Experimental Superweapon (T4)",
        type: "spawn_unit",
        rarity: "jackpot",
        weight: 60,
        unitId: "uel0401",
        unitCount: 1,
        mass: 0,
        energy: 0,
        reels: ["🌟", "🌟", "🌟"],
        desc: "Spawns a massive T4 Experimental Mobile Factory!"
      },
      {
        id: "prize_t3_squad",
        name: "💎 T3 Heavy Assault Battalion",
        type: "spawn_unit",
        rarity: "rare",
        weight: 180,
        unitId: "uel0303",
        unitCount: 3,
        mass: 0,
        energy: 0,
        reels: ["💎", "💎", "💎"],
        desc: "Spawns 3 Tier 3 Heavy Siege Assault Bots!"
      },
      {
        id: "prize_mass_vault",
        name: "🪙 Quantum Mass Jackpot",
        type: "give_resources",
        rarity: "rare",
        weight: 180,
        mass: 7500,
        energy: 25000,
        reels: ["🪙", "🪙", "🪙"],
        desc: "Transfers +7,500 Mass and +25,000 Energy instantly!"
      },
      {
        id: "prize_energy_burst",
        name: "⚡ Energy Singularity Cache",
        type: "give_resources",
        rarity: "common",
        weight: 220,
        mass: 1500,
        energy: 50000,
        reels: ["⚡", "⚡", "⚡"],
        desc: "Injects +1,500 Mass and +50,000 Energy into your grid!"
      },
      {
        id: "prize_t2_platoon",
        name: "🛡️ T2 Combat Strike Wing",
        type: "spawn_unit",
        rarity: "common",
        weight: 160,
        unitId: "uel0202",
        unitCount: 4,
        mass: 0,
        energy: 0,
        reels: ["🛡️", "🛡️", "🛡️"],
        desc: "Spawns 4 T2 Heavy Battle Tanks!"
      },
      {
        id: "hazard_pirate_drain",
        name: "💸 Hacker Syndicate Siphon",
        type: "take_resources",
        rarity: "unlucky",
        weight: 100,
        massDrain: 1500,
        energyDrain: 25000,
        reels: ["💸", "💸", "💸"],
        desc: "Cyber bandits hack your economy: -1,500 Mass & -25,000 Energy drained!"
      },
      {
        id: "hazard_hostile_ambush",
        name: "💀 Hostile Civilian Mercenary Ambush!",
        type: "spawn_hostile",
        rarity: "disaster",
        weight: 100,
        unitId: "url0303",
        unitCount: 3,
        reels: ["💀", "💀", "💀"],
        desc: "Vault is a TRAP! Spawns 3 hostile civilian rogue battle mechs that attack immediately!"
      }
    ]
  };

  const DEFAULT_META = {
    modName: "FAF Master Overhaul",
    author: "Taily",
    version: 1,
    targetMode: "player",
    playerName: "Taily"
  };

  const DEFAULT_PROFILES = [
    {
      id: "prof_1",
      playerName: "Taily",
      roleName: "Player 1 (Host)",
      icon: "👑",
      damageDealtMult: 1.0,
      damageTakenMult: 1.0,
      buildRateMult: 1.0,
      prodMult: 1.0,
      buffsMode: "global",
      limitsMode: "global",
      customBuffs: {},
      customLimits: []
    },
    {
      id: "prof_2",
      playerName: "Player2",
      roleName: "Player 2 (Ally / Rival)",
      icon: "⚔️",
      damageDealtMult: 1.25,
      damageTakenMult: 1.0,
      buildRateMult: 1.2,
      prodMult: 1.0,
      buffsMode: "global",
      limitsMode: "none",
      customBuffs: {},
      customLimits: []
    },
    {
      id: "prof_3",
      playerName: "AI",
      roleName: "AI Boss / Wave",
      icon: "🤖",
      damageDealtMult: 1.5,
      damageTakenMult: 0.8,
      buildRateMult: 1.5,
      prodMult: 1.5,
      buffsMode: "none",
      limitsMode: "none",
      customBuffs: {},
      customLimits: []
    }
  ];

  function isFirstVisit() {
    return !localStorage.getItem(KEYS.INITIALIZED);
  }

  function markInitialized() {
    localStorage.setItem(KEYS.INITIALIZED, "true");
  }

  // --- Buffs (Unit Stat Forge) ---
  function getBuffs() {
    try {
      const data = localStorage.getItem(KEYS.BUFFS);
      return data ? JSON.parse(data) : {};
    } catch (e) {
      console.warn("Failed to read buffs from localStorage:", e);
      return {};
    }
  }

  function setBuffs(buffs) {
    try {
      const plain = (buffs instanceof Map) ? Object.fromEntries(buffs) : (buffs || {});
      localStorage.setItem(KEYS.BUFFS, JSON.stringify(plain));
      markInitialized();
      syncNavBadges();
    } catch (e) {
      console.warn("Failed to save buffs:", e);
    }
  }

  // --- Limits (Unit Limiter) ---
  function getLimits() {
    try {
      const data = localStorage.getItem(KEYS.LIMITS);
      return data ? JSON.parse(data) : null;
    } catch (e) {
      console.warn("Failed to read limits from localStorage:", e);
      return null;
    }
  }

  function setLimits(limits) {
    try {
      let arr = [];
      if (limits instanceof Map) {
        arr = Array.from(limits.values());
      } else if (Array.isArray(limits)) {
        arr = limits;
      } else if (limits && typeof limits === "object") {
        arr = Object.values(limits);
      }
      localStorage.setItem(KEYS.LIMITS, JSON.stringify(arr));
      markInitialized();
      syncNavBadges();
    } catch (e) {
      console.warn("Failed to save limits:", e);
    }
  }

  // --- Popups (Tactical Event Popups) ---
  function getPopups() {
    try {
      const data = localStorage.getItem(KEYS.POPUPS);
      return data ? JSON.parse(data) : null;
    } catch (e) {
      console.warn("Failed to read popups from localStorage:", e);
      return null;
    }
  }

  function setPopups(popups) {
    try {
      let arr = [];
      if (popups instanceof Map) {
        arr = Array.from(popups.values());
      } else if (Array.isArray(popups)) {
        arr = popups;
      } else if (popups && typeof popups === "object") {
        arr = Object.values(popups);
      }
      localStorage.setItem(KEYS.POPUPS, JSON.stringify(arr));
      markInitialized();
      syncNavBadges();
    } catch (e) {
      console.warn("Failed to save popups:", e);
    }
  }

  // --- Relics (Relic Objectives) ---
  function getRelics() {
    try {
      const data = localStorage.getItem(KEYS.RELICS);
      return data ? JSON.parse(data) : null;
    } catch (e) {
      console.warn("Failed to read relics from localStorage:", e);
      return null;
    }
  }

  function setRelics(relics) {
    try {
      let arr = [];
      if (relics instanceof Map) {
        arr = Array.from(relics.values());
      } else if (Array.isArray(relics)) {
        arr = relics;
      } else if (relics && typeof relics === "object") {
        arr = Object.values(relics);
      }
      localStorage.setItem(KEYS.RELICS, JSON.stringify(arr));
      markInitialized();
      syncNavBadges();
    } catch (e) {
      console.warn("Failed to save relics:", e);
    }
  }

  // --- Lootbox (Surprise Casino & Lootbox) ---
  function getLootbox() {
    try {
      const data = localStorage.getItem(KEYS.LOOTBOX);
      if (data) {
        const parsed = JSON.parse(data);
        if (parsed && typeof parsed === "object") {
          return { ...DEFAULT_LOOTBOX, ...parsed };
        }
      }
      return JSON.parse(JSON.stringify(DEFAULT_LOOTBOX));
    } catch (e) {
      console.warn("Failed to read lootbox from localStorage:", e);
      return JSON.parse(JSON.stringify(DEFAULT_LOOTBOX));
    }
  }

  function setLootbox(lootbox) {
    try {
      localStorage.setItem(KEYS.LOOTBOX, JSON.stringify(lootbox || DEFAULT_LOOTBOX));
      markInitialized();
      syncNavBadges();
    } catch (e) {
      console.warn("Failed to save lootbox:", e);
    }
  }

  // --- Multiplayer Profiles ---
  function getPlayerProfiles() {
    try {
      const data = localStorage.getItem(KEYS.PROFILES);
      if (data) {
        const parsed = JSON.parse(data);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
      return JSON.parse(JSON.stringify(DEFAULT_PROFILES));
    } catch (e) {
      console.warn("Failed to read player profiles:", e);
      return JSON.parse(JSON.stringify(DEFAULT_PROFILES));
    }
  }

  function setPlayerProfiles(profiles) {
    try {
      const arr = Array.isArray(profiles) ? profiles : [];
      localStorage.setItem(KEYS.PROFILES, JSON.stringify(arr));
      markInitialized();
    } catch (e) {
      console.warn("Failed to save player profiles:", e);
    }
  }

  // --- Shared Mod Metadata ---
  function getModMeta() {
    try {
      const data = localStorage.getItem(KEYS.META);
      return data ? { ...DEFAULT_META, ...JSON.parse(data) } : { ...DEFAULT_META };
    } catch (e) {
      return { ...DEFAULT_META };
    }
  }

  function setModMeta(meta) {
    try {
      const current = getModMeta();
      const merged = { ...current, ...meta };
      localStorage.setItem(KEYS.META, JSON.stringify(merged));
    } catch (e) {
      console.warn("Failed to save meta:", e);
    }
  }

  // --- Counts Helper ---
  function getCounts() {
    const buffs = Object.keys(getBuffs()).length;
    const limits = (getLimits() || []).length;
    const popups = (getPopups() || []).length;
    const relics = (getRelics() || []).length;
    const lb = getLootbox();
    const lootbox = (lb && lb.enabled) ? (lb.dropTable ? lb.dropTable.length : 1) : 0;
    return {
      buffs,
      limits,
      popups,
      relics,
      lootbox,
      total: buffs + limits + popups + relics + (lootbox > 0 ? 1 : 0)
    };
  }

  // --- Live Navbar Badge Synchronization ---
  function syncNavBadges() {
    const counts = getCounts();

    const countBuffsEl = document.getElementById("nav-count-buffs");
    if (countBuffsEl) {
      countBuffsEl.textContent = counts.buffs;
      countBuffsEl.style.display = counts.buffs > 0 ? "inline-flex" : "none";
    }

    const countLimitsEl = document.getElementById("nav-count-limits");
    if (countLimitsEl) {
      countLimitsEl.textContent = counts.limits;
      countLimitsEl.style.display = counts.limits > 0 ? "inline-flex" : "none";
    }

    const countPopupsEl = document.getElementById("nav-count-popups");
    if (countPopupsEl) {
      countPopupsEl.textContent = counts.popups;
      countPopupsEl.style.display = counts.popups > 0 ? "inline-flex" : "none";
    }

    const countRelicsEl = document.getElementById("nav-count-relics");
    if (countRelicsEl) {
      countRelicsEl.textContent = counts.relics;
      countRelicsEl.style.display = counts.relics > 0 ? "inline-flex" : "none";
    }

    const countLootboxEl = document.getElementById("nav-count-lootbox");
    if (countLootboxEl) {
      countLootboxEl.textContent = counts.lootbox;
      countLootboxEl.style.display = counts.lootbox > 0 ? "inline-flex" : "none";
    }

    const countCombinedEl = document.getElementById("nav-count-combined");
    if (countCombinedEl) {
      countCombinedEl.textContent = counts.total;
      countCombinedEl.style.display = counts.total > 0 ? "inline-flex" : "none";
    }

    const headerCombinedCountEl = document.getElementById("header-combined-count");
    if (headerCombinedCountEl) {
      headerCombinedCountEl.textContent = counts.total;
    }
  }

  function clearAll() {
    localStorage.removeItem(KEYS.BUFFS);
    localStorage.removeItem(KEYS.LIMITS);
    localStorage.removeItem(KEYS.POPUPS);
    localStorage.removeItem(KEYS.RELICS);
    localStorage.removeItem(KEYS.LOOTBOX);
    localStorage.removeItem(KEYS.PROFILES);
    syncNavBadges();
  }

  // Initialize navbar badges on DOMContentLoaded
  if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", () => {
      syncNavBadges();
    });
    window.addEventListener("storage", () => {
      syncNavBadges();
    });
  }

  return {
    isFirstVisit,
    markInitialized,
    getBuffs,
    setBuffs,
    getLimits,
    setLimits,
    getPopups,
    setPopups,
    getRelics,
    setRelics,
    getLootbox,
    setLootbox,
    DEFAULT_LOOTBOX,
    getPlayerProfiles,
    setPlayerProfiles,
    DEFAULT_PROFILES,
    getModMeta,
    setModMeta,
    getCounts,
    syncNavBadges,
    clearAll
  };
})();
