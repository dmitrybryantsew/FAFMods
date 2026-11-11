// FAF Mod Forge - Relic & Crate Objectives System
// Allows spawning capturable beacons, monuments, or proximity crates that reward players with unit buffs.

let allUnits = [];
let unitMap = new Map();
let filteredTargetUnits = [];

// Array of configured objectives in the mod
let configuredObjectives = [];

// Current selected target in the builder
let selectedTarget = {
  type: "category", // "category" or "unit"
  name: "Commander (ACU)",
  unitId: null,
  categoryLua: "categories.COMMAND",
  icon: "👑",
  meta: "Category: COMMAND | All Factions"
};

const PRESETS = [
  {
    id: "preset_center_beacon",
    icon: "📡",
    name: "Center Data Beacon",
    modelBpId: "uec1904",
    modelName: "UEF Communication Tower",
    desc: "Spawns at map center. Captured or walked over by any combat unit, engineer, or ACU to grant T1 combat units (tanks, artillery, anti-air) powerful battlefield upgrades.",
    spawnDelay: 0,
    locMode: "center",
    triggerType: "both",
    pickupRadius: 15,
    claimer: "any",
    claimerCategoryLua: "categories.COMMAND + categories.ENGINEER + categories.LAND",
    targetType: "category",
    targetName: "All T1 Combat Units",
    targetUnitId: null,
    targetCategoryLua: "categories.LAND * categories.TECH1 * (categories.DIRECTFIRE + categories.INDIRECTFIRE + categories.ANTIAIR)",
    buffDuration: 0,
    buffs: {
      hpMult: 1.50,
      rangeMult: 1.25,
      damageMult: 1.30,
      speedMult: 1.15,
      shieldMult: 1.0,
      regenMult: 1.0
    }
  },
  {
    id: "preset_ancient_monolith",
    icon: "🛸",
    name: "Ancient Aeon Relic Beacon",
    modelBpId: "uac1902",
    modelName: "Aeon Network Node",
    desc: "Spawns 60s into the match at map center. Capture beam or walkover by Commander to infuse your ACU with supreme combat stats.",
    spawnDelay: 60,
    locMode: "center",
    triggerType: "both",
    pickupRadius: 15,
    claimer: "commander",
    claimerCategoryLua: "categories.COMMAND",
    targetType: "category",
    targetName: "Commander (ACU)",
    targetUnitId: null,
    targetCategoryLua: "categories.COMMAND",
    buffDuration: 0,
    buffs: {
      hpMult: 1.75,
      rangeMult: 1.30,
      damageMult: 1.50,
      speedMult: 1.10,
      shieldMult: 1.0,
      regenMult: 2.0
    }
  },
  {
    id: "preset_quantum_core",
    icon: "⚡",
    name: "Quantum Experimental Core",
    modelBpId: "urc1902",
    modelName: "Cybran Network Spire Node",
    desc: "Spawns at 5 minutes near center. Walking over it supercharges all Experimental (T4) units produced by the player.",
    spawnDelay: 300,
    locMode: "random_center",
    triggerType: "walkover",
    pickupRadius: 15,
    claimer: "commander",
    claimerCategoryLua: "categories.COMMAND",
    targetType: "category",
    targetName: "All Experimentals (T4)",
    targetUnitId: null,
    targetCategoryLua: "categories.EXPERIMENTAL",
    buffDuration: 0,
    buffs: {
      hpMult: 1.30,
      rangeMult: 1.20,
      damageMult: 1.25,
      speedMult: 1.15,
      shieldMult: 1.25,
      regenMult: 1.5
    }
  },
  {
    id: "preset_supply_cache",
    icon: "🚚",
    name: "Tactical Supply Depot",
    modelBpId: "uec0001",
    modelName: "Civilian Supply Truck",
    desc: "Spawns 2 minutes in. Walking over or capturing it provides long-range ballistic targeting boosts for all Artillery and Missiles.",
    spawnDelay: 120,
    locMode: "center",
    triggerType: "both",
    pickupRadius: 14,
    claimer: "subcommander",
    claimerCategoryLua: "categories.COMMAND + categories.SUBCOMMANDER",
    targetType: "category",
    targetName: "All Artillery & Missile Units",
    targetUnitId: null,
    targetCategoryLua: "categories.ARTILLERY + categories.SILO",
    buffDuration: 0,
    buffs: {
      hpMult: 1.20,
      rangeMult: 1.40,
      damageMult: 1.35,
      speedMult: 1.20,
      shieldMult: 1.0,
      regenMult: 1.0
    }
  }
];

// DOM Elements
const totalObjectivesCountEl = document.getElementById("total-objectives-count");
const activeBadgeCountEl = document.getElementById("active-badge-count");
const btnRelicsCountEl = document.getElementById("btn-relics-count");
const activeObjectivesContainer = document.getElementById("active-objectives-container");
const objectivesEmptyState = document.getElementById("objectives-empty-state");
const relicPresetGrid = document.getElementById("relic-preset-grid");

// Inputs
const inputModName = document.getElementById("input-mod-name");
const inputAuthor = document.getElementById("input-author");
const inputVersion = document.getElementById("input-version");
const inputPlayerName = document.getElementById("input-player-name");
const groupPlayerName = document.getElementById("group-player-name");
const cardScopePlayer = document.getElementById("card-scope-player");
const cardScopeGlobal = document.getElementById("card-scope-global");
const radioScopes = document.querySelectorAll('input[name="target-scope"]');

// Builder Controls
const inputObjName = document.getElementById("obj-name");
const selectObjModel = document.getElementById("obj-model-select");
const groupCustomBlueprint = document.getElementById("group-custom-blueprint");
const inputCustomBp = document.getElementById("obj-custom-bp");

const selectTiming = document.getElementById("obj-timing");
const selectLocationMode = document.getElementById("obj-location-mode");
const groupCustomCoords = document.getElementById("group-custom-coords");
const inputCoordX = document.getElementById("obj-coord-x");
const inputCoordZ = document.getElementById("obj-coord-z");

const selectTriggerType = document.getElementById("obj-trigger-type");
const selectClaimer = document.getElementById("obj-claimer");
const groupPickupRadius = document.getElementById("group-pickup-radius");
const sliderRadius = document.getElementById("obj-pickup-radius");
const valRadius = document.getElementById("radius-val");

// Target Selector Elements
const targetPreviewBox = document.getElementById("target-preview-box");
const previewIcon = document.getElementById("preview-icon");
const previewName = document.getElementById("preview-name");
const previewMeta = document.getElementById("preview-meta");
const btnChooseUnitToggle = document.getElementById("btn-choose-unit-toggle");
const unitSelectorPanel = document.getElementById("unit-selector-panel");
const targetUnitSearch = document.getElementById("target-unit-search");
const clearTargetSearch = document.getElementById("clear-target-search");
const targetUnitGrid = document.getElementById("target-unit-grid");

// Sliders
const sliderHp = document.getElementById("slider-hp");
const sliderRange = document.getElementById("slider-range");
const sliderDamage = document.getElementById("slider-damage");
const sliderSpeed = document.getElementById("slider-speed");
const sliderShield = document.getElementById("slider-shield");
const sliderRegen = document.getElementById("slider-regen");

const valHp = document.getElementById("val-hp");
const valRange = document.getElementById("val-range");
const valDamage = document.getElementById("val-damage");
const valSpeed = document.getElementById("val-speed");
const valShield = document.getElementById("val-shield");
const valRegen = document.getElementById("val-regen");

// Action Buttons
const btnAddObjective = document.getElementById("btn-add-objective");
const btnClearAllObjectives = document.getElementById("btn-clear-all-objectives");
const btnAddAllPresets = document.getElementById("btn-add-all-presets");
const btnClearPresets = document.getElementById("btn-clear-presets");
const btnExportRelics = document.getElementById("btn-export-relics");
const btnOpenFolder = document.getElementById("btn-open-folder");
const exportFeedback = document.getElementById("export-feedback");
const toastEl = document.getElementById("toast");

// Current Unit Filters
let currentFilters = {
  search: "",
  faction: "ALL",
  tech: "ALL",
  type: "ALL"
};

// Initialize
async function init() {
  bindEvents();
  loadSavedMetadata();
  renderPresets();
  updateSliderReadouts();
  await loadUnits();

  const savedRelics = ForgeStore.getRelics();
  if (savedRelics && Array.isArray(savedRelics) && savedRelics.length > 0) {
    configuredObjectives = savedRelics;
    renderActiveObjectives();
  } else if (savedRelics !== null) {
    configuredObjectives = [];
    renderActiveObjectives();
  } else if (ForgeStore.isFirstVisit()) {
    addPreset(PRESETS[0]);
    addPreset(PRESETS[1]);
  } else {
    renderActiveObjectives();
  }
  ForgeStore.syncNavBadges();
}

function loadSavedMetadata() {
  const meta = ForgeStore.getModMeta();
  if (meta.modName && meta.modName !== "FAF Master Overhaul") inputModName.value = meta.modName;
  if (meta.author) inputAuthor.value = meta.author;
  if (meta.version) inputVersion.value = meta.version;
  if (meta.playerName) inputPlayerName.value = meta.playerName;
  if (meta.targetMode === "player") {
    cardScopePlayer.classList.add("active");
    cardScopeGlobal.classList.remove("active");
    const radio = document.querySelector('input[name="target-scope"][value="player"]');
    if (radio) radio.checked = true;
    groupPlayerName.style.display = "block";
  } else {
    cardScopeGlobal.classList.add("active");
    cardScopePlayer.classList.remove("active");
    const radio = document.querySelector('input[name="target-scope"][value="global"]');
    if (radio) radio.checked = true;
    groupPlayerName.style.display = "none";
  }
}

function saveCurrentMetadata() {
  const targetMode = document.querySelector('input[name="target-scope"]:checked')?.value || "global";
  ForgeStore.setModMeta({
    author: inputAuthor.value.trim(),
    version: parseInt(inputVersion.value, 10) || 1,
    targetMode,
    playerName: inputPlayerName.value.trim()
  });
}

function bindEvents() {
  // Scope Radio Cards
  radioScopes.forEach(radio => {
    radio.addEventListener("change", () => {
      if (radio.value === "player") {
        cardScopePlayer.classList.add("active");
        cardScopeGlobal.classList.remove("active");
        groupPlayerName.style.display = "block";
      } else {
        cardScopeGlobal.classList.add("active");
        cardScopePlayer.classList.remove("active");
        groupPlayerName.style.display = "none";
      }
      saveCurrentMetadata();
    });
  });

  inputAuthor.addEventListener("input", saveCurrentMetadata);
  inputVersion.addEventListener("input", saveCurrentMetadata);
  inputPlayerName.addEventListener("input", saveCurrentMetadata);

  // Model select
  selectObjModel.addEventListener("change", () => {
    if (selectObjModel.value === "custom") {
      groupCustomBlueprint.style.display = "block";
    } else {
      groupCustomBlueprint.style.display = "none";
    }
  });

  // Location mode select
  selectLocationMode.addEventListener("change", () => {
    if (selectLocationMode.value === "coords") {
      groupCustomCoords.style.display = "flex";
    } else {
      groupCustomCoords.style.display = "none";
    }
  });

  // Trigger type select
  selectTriggerType.addEventListener("change", () => {
    if (selectTriggerType.value === "capture") {
      groupPickupRadius.style.display = "none";
    } else {
      groupPickupRadius.style.display = "block";
    }
  });

  // Pickup radius slider
  sliderRadius.addEventListener("input", () => {
    valRadius.textContent = `${sliderRadius.value} O-Grid units`;
  });

  // Target Unit Selector Toggle
  btnChooseUnitToggle.addEventListener("click", () => {
    const isShown = unitSelectorPanel.style.display === "block";
    unitSelectorPanel.style.display = isShown ? "none" : "block";
    btnChooseUnitToggle.textContent = isShown ? "Change Target Unit" : "Close Selector";
  });

  // Quick Category Buttons
  document.querySelectorAll(".category-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".category-chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");

      const catLua = chip.dataset.cat;
      const catName = chip.dataset.name;

      selectedTarget = {
        type: "category",
        name: catName,
        unitId: null,
        categoryLua: catLua,
        icon: chip.textContent.split(" ")[0] || "🎖️",
        meta: `Category: ${catLua}`
      };

      updateTargetPreview();
      unitSelectorPanel.style.display = "none";
      btnChooseUnitToggle.textContent = "Change Target Unit";
    });
  });

  // Unit Search in selector
  targetUnitSearch.addEventListener("input", (e) => {
    currentFilters.search = e.target.value.trim().toLowerCase();
    clearTargetSearch.style.display = currentFilters.search ? "block" : "none";
    applyUnitFilters();
  });

  clearTargetSearch.addEventListener("click", () => {
    targetUnitSearch.value = "";
    currentFilters.search = "";
    clearTargetSearch.style.display = "none";
    applyUnitFilters();
  });

  // Filter chips in selector
  bindFilterChips("target-faction-chips", "faction");
  bindFilterChips("target-tech-chips", "tech");
  bindFilterChips("target-type-chips", "type");

  // Sliders input
  [sliderHp, sliderRange, sliderDamage, sliderSpeed, sliderShield, sliderRegen].forEach(slider => {
    slider.addEventListener("input", updateSliderReadouts);
  });

  // Duration chips
  document.querySelectorAll(".duration-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".duration-chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      const sec = parseInt(chip.dataset.sec, 10) || 0;
      const inputDur = document.getElementById("input-buff-duration");
      if (inputDur) inputDur.value = sec;
      const valDurEl = document.getElementById("val-duration");
      if (valDurEl) {
        valDurEl.textContent = sec > 0 ? `⏱️ ${sec} Seconds (Temporal)` : "♾️ Permanent (Until Match End)";
      }
    });
  });

  // Add Objective
  btnAddObjective.addEventListener("click", handleAddCustomObjective);

  // Clear Objectives
  btnClearAllObjectives.addEventListener("click", () => {
    configuredObjectives = [];
    renderActiveObjectives();
    showToast("Cleared all active objectives.");
  });

  // Presets batch
  btnAddAllPresets.addEventListener("click", () => {
    PRESETS.forEach(p => addPreset(p));
    showToast("Added all 4 ready-to-play presets!");
  });

  btnClearPresets.addEventListener("click", () => {
    configuredObjectives = [];
    renderActiveObjectives();
    showToast("Cleared objectives.");
  });

  // Export
  btnExportRelics.addEventListener("click", handleExportRelics);

  // Open Folder
  btnOpenFolder.addEventListener("click", async () => {
    try {
      await fetch("/api/open-folder");
      showToast("Opened Supreme Commander mods folder.");
    } catch (e) {
      showToast("Error opening mods directory.");
    }
  });
}

function bindFilterChips(containerId, filterKey) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    container.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    currentFilters[filterKey] = chip.dataset.val;
    applyUnitFilters();
  });
}

function updateSliderReadouts() {
  const hp = parseFloat(sliderHp.value);
  const range = parseFloat(sliderRange.value);
  const dmg = parseFloat(sliderDamage.value);
  const spd = parseFloat(sliderSpeed.value);
  const shd = parseFloat(sliderShield.value);
  const rgn = parseFloat(sliderRegen.value);

  valHp.textContent = `${hp.toFixed(2)}x (${formatBonusPercent(hp)})`;
  valRange.textContent = `${range.toFixed(2)}x (${formatBonusPercent(range)})`;
  valDamage.textContent = `${dmg.toFixed(2)}x (${formatBonusPercent(dmg)})`;
  valSpeed.textContent = `${spd.toFixed(2)}x (${formatBonusPercent(spd)})`;
  valShield.textContent = shd === 1.0 ? "1.00x (Default)" : `${shd.toFixed(2)}x (${formatBonusPercent(shd)})`;
  valRegen.textContent = rgn === 1.0 ? "1.00x (Default)" : `${rgn.toFixed(2)}x (${formatBonusPercent(rgn)})`;
}

function formatBonusPercent(mult) {
  const pct = Math.round((mult - 1.0) * 100);
  if (pct === 0) return "Default";
  return pct > 0 ? `+${pct}%` : `${pct}%`;
}

function updateTargetPreview() {
  previewIcon.textContent = selectedTarget.icon || "🎖️";
  previewName.textContent = selectedTarget.name;
  previewMeta.textContent = selectedTarget.meta;
}

// Load 503 Units from API
async function loadUnits() {
  try {
    const res = await fetch("/api/units");
    allUnits = await res.json();
    unitMap = new Map(allUnits.map(u => [u.id.toLowerCase(), u]));
    filteredTargetUnits = allUnits.slice();
    renderTargetUnitGrid();
  } catch (err) {
    console.error("Failed to load units:", err);
  }
}

function applyUnitFilters() {
  filteredTargetUnits = allUnits.filter(u => {
    // Search
    if (currentFilters.search) {
      const q = currentFilters.search;
      const match = u.id.toLowerCase().includes(q) ||
                    u.name.toLowerCase().includes(q) ||
                    u.desc.toLowerCase().includes(q) ||
                    u.faction.toLowerCase().includes(q);
      if (!match) return false;
    }

    // Faction
    if (currentFilters.faction !== "ALL" && u.faction.toUpperCase() !== currentFilters.faction.toUpperCase()) {
      return false;
    }

    // Tech
    if (currentFilters.tech !== "ALL" && u.tech.toUpperCase() !== currentFilters.tech.toUpperCase()) {
      return false;
    }

    // Type
    if (currentFilters.type !== "ALL" && u.type.toUpperCase() !== currentFilters.type.toUpperCase()) {
      return false;
    }

    return true;
  });

  renderTargetUnitGrid();
}

function renderTargetUnitGrid() {
  if (!targetUnitGrid) return;
  targetUnitGrid.innerHTML = "";

  const displayList = filteredTargetUnits.slice(0, 60); // render first 60 for speed

  if (displayList.length === 0) {
    targetUnitGrid.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 20px; text-align: center; color: var(--text-muted); font-size: 0.8rem;">
        No units match your search filters.
      </div>
    `;
    return;
  }

  displayList.forEach(u => {
    const card = document.createElement("div");
    card.className = "unit-card";
    const factionClass = u.faction ? u.faction.toLowerCase() : "unknown";

    card.innerHTML = `
      <div class="unit-card-header">
        <span class="unit-card-tier ${u.tech.toLowerCase()}">${u.tech}</span>
        <span class="unit-card-faction ${factionClass}">${u.faction}</span>
      </div>
      <div class="unit-card-title">${u.name}</div>
      <div class="unit-card-id">${u.id} &bull; ${u.type}</div>
      <div style="font-size: 0.7rem; color: var(--text-dim); margin-top: 4px;">
        HP: ${u.hp.toLocaleString()} &bull; Dmg: ${u.weaponDamage || 0} &bull; Range: ${u.weaponRange || 0}
      </div>
      <button class="unit-card-limit-btn" data-id="${u.id}">🎯 Buff This Unit</button>
    `;

    card.querySelector(".unit-card-limit-btn").addEventListener("click", () => {
      // Set as target
      selectedTarget = {
        type: "unit",
        name: `${u.name} (${u.id})`,
        unitId: u.id,
        categoryLua: `categories.${u.id.toUpperCase()}`,
        icon: getFactionEmoji(u.faction),
        meta: `Unit ID: ${u.id} | ${u.faction} ${u.tech} ${u.type} | Base HP: ${u.hp}`
      };

      document.querySelectorAll(".category-chip").forEach(c => c.classList.remove("active"));
      updateTargetPreview();
      unitSelectorPanel.style.display = "none";
      btnChooseUnitToggle.textContent = "Change Target Unit";
      showToast(`Selected ${u.name} as target unit.`);
    });

    targetUnitGrid.appendChild(card);
  });
}

function getFactionEmoji(faction) {
  switch ((faction || "").toUpperCase()) {
    case "UEF": return "🛡️";
    case "CYBRAN": return "🕷️";
    case "AEON": return "🛸";
    case "SERAPHIM": return "🌌";
    case "NOMADS": return "🚀";
    default: return "⚔️";
  }
}

// Render Presets
function renderPresets() {
  if (!relicPresetGrid) return;
  relicPresetGrid.innerHTML = "";

  PRESETS.forEach(p => {
    const card = document.createElement("div");
    card.className = "relic-preset-card";

    const pills = [];
    if (p.buffs.hpMult > 1.0) pills.push(`<span class="pill-badge hp">+${Math.round((p.buffs.hpMult-1)*100)}% HP</span>`);
    if (p.buffs.rangeMult > 1.0) pills.push(`<span class="pill-badge range">+${Math.round((p.buffs.rangeMult-1)*100)}% Range</span>`);
    if (p.buffs.damageMult > 1.0) pills.push(`<span class="pill-badge damage">+${Math.round((p.buffs.damageMult-1)*100)}% Dmg</span>`);
    if (p.buffs.speedMult > 1.0) pills.push(`<span class="pill-badge speed">+${Math.round((p.buffs.speedMult-1)*100)}% Speed</span>`);
    if (p.buffs.regenMult > 1.0) pills.push(`<span class="pill-badge regen">+${Math.round((p.buffs.regenMult-1)*100)}% Regen</span>`);

    let triggerBadge = "";
    if (p.triggerType === "capture") triggerBadge = `<span class="trigger-badge capture">📡 Capture Beam</span>`;
    else if (p.triggerType === "walkover") triggerBadge = `<span class="trigger-badge walkover">🚶 Walk-Over</span>`;
    else triggerBadge = `<span class="trigger-badge both">⚡ Capture or Pickup</span>`;

    card.innerHTML = `
      <div>
        <div class="relic-preset-top">
          <div class="relic-preset-icon">${p.icon}</div>
          <div class="relic-preset-info">
            <div class="relic-preset-name">${p.name}</div>
            <div class="relic-preset-target">Target: ${p.targetName}</div>
            <div style="margin-bottom: 4px;">${triggerBadge}</div>
          </div>
        </div>
        <div class="relic-preset-desc">${p.desc}</div>
        <div class="relic-pills-row">${pills.join("")}</div>
      </div>
      <div style="margin-top: 10px;">
        <button class="btn btn-sm btn-outline btn-block btn-add-preset" style="color: var(--accent-gold); border-color: rgba(255,183,3,0.4);">
          ➕ Add This Objective
        </button>
      </div>
    `;

    card.querySelector(".btn-add-preset").addEventListener("click", () => {
      addPreset(p);
      showToast(`Added '${p.name}' objective!`);
    });

    relicPresetGrid.appendChild(card);
  });
}

function addPreset(preset) {
  // Check if already added
  const existing = configuredObjectives.find(o => o.presetId === preset.id);
  if (existing) {
    showToast(`'${preset.name}' is already added.`);
    return;
  }

  const obj = {
    id: "obj_" + Date.now() + "_" + Math.floor(Math.random() * 1000),
    presetId: preset.id,
    name: preset.name,
    icon: preset.icon,
    modelBpId: preset.modelBpId,
    modelName: preset.modelName,
    spawnDelay: preset.spawnDelay,
    locMode: preset.locMode,
    customX: 256,
    customZ: 256,
    triggerType: preset.triggerType,
    pickupRadius: preset.pickupRadius,
    claimer: preset.claimer,
    claimerCategoryLua: preset.claimerCategoryLua,
    targetType: preset.targetType,
    targetName: preset.targetName,
    targetUnitId: preset.targetUnitId,
    targetCategoryLua: preset.targetCategoryLua,
    buffDuration: preset.buffDuration || 0,
    buffs: Object.assign({}, preset.buffs)
  };

  configuredObjectives.push(obj);
  renderActiveObjectives();
}

// Add Custom Objective from Builder
function handleAddCustomObjective() {
  const name = inputObjName.value.trim() || "Custom Objective";

  let modelBpId = selectObjModel.value;
  let modelName = selectObjModel.options[selectObjModel.selectedIndex].text;
  if (modelBpId === "custom") {
    modelBpId = inputCustomBp.value.trim();
    if (!modelBpId) {
      alert("Please specify a custom blueprint ID.");
      return;
    }
    modelName = `Custom (${modelBpId})`;
  }

  const spawnDelay = parseInt(selectTiming.value, 10) || 0;
  const locMode = selectLocationMode.value;
  const customX = parseFloat(inputCoordX.value) || 256;
  const customZ = parseFloat(inputCoordZ.value) || 256;

  const triggerType = selectTriggerType.value;
  const claimer = selectClaimer.value;
  let claimerCatLua = "categories.COMMAND";
  if (claimer === "subcommander") {
    claimerCatLua = "categories.COMMAND + categories.SUBCOMMANDER";
  } else if (claimer === "any") {
    claimerCatLua = "categories.ALLUNITS";
  }

  const pickupRadius = parseFloat(sliderRadius.value) || 6.0;

  const buffs = {
    hpMult: parseFloat(sliderHp.value) || 1.0,
    rangeMult: parseFloat(sliderRange.value) || 1.0,
    damageMult: parseFloat(sliderDamage.value) || 1.0,
    speedMult: parseFloat(sliderSpeed.value) || 1.0,
    shieldMult: parseFloat(sliderShield.value) || 1.0,
    regenMult: parseFloat(sliderRegen.value) || 1.0,
  };

  const obj = {
    id: "obj_" + Date.now() + "_" + Math.floor(Math.random() * 1000),
    name: name,
    icon: "💎",
    modelBpId: modelBpId,
    modelName: modelName,
    spawnDelay: spawnDelay,
    locMode: locMode,
    customX: customX,
    customZ: customZ,
    triggerType: triggerType,
    pickupRadius: pickupRadius,
    claimer: claimer,
    claimerCategoryLua: claimerCatLua,
    targetType: selectedTarget.type,
    targetName: selectedTarget.name,
    targetUnitId: selectedTarget.unitId,
    targetCategoryLua: selectedTarget.categoryLua,
    buffDuration: parseInt(document.getElementById("input-buff-duration") ? document.getElementById("input-buff-duration").value : 0, 10) || 0,
    buffs: buffs
  };

  configuredObjectives.push(obj);
  renderActiveObjectives();
  showToast(`Added '${name}' objective to mod!`);
}

// Render Active Objectives in Sidebar
function renderActiveObjectives() {
  const count = configuredObjectives.length;
  totalObjectivesCountEl.textContent = count;
  activeBadgeCountEl.textContent = count;
  btnRelicsCountEl.textContent = count;

  ForgeStore.setRelics(configuredObjectives);
  ForgeStore.syncNavBadges();

  if (count === 0) {
    activeObjectivesContainer.innerHTML = `
      <div class="rules-empty-box" id="objectives-empty-state">
        <span>No objectives configured yet.<br>Click a quick preset or add one above.</span>
      </div>
    `;
    return;
  }

  activeObjectivesContainer.innerHTML = "";

  configuredObjectives.forEach((obj, idx) => {
    const item = document.createElement("div");
    item.className = "active-objective-item";

    const pills = [];
    if (obj.buffs.hpMult > 1.0) pills.push(`<span class="pill-badge hp">+${Math.round((obj.buffs.hpMult-1)*100)}% HP</span>`);
    if (obj.buffs.rangeMult > 1.0) pills.push(`<span class="pill-badge range">+${Math.round((obj.buffs.rangeMult-1)*100)}% Range</span>`);
    if (obj.buffs.damageMult > 1.0) pills.push(`<span class="pill-badge damage">+${Math.round((obj.buffs.damageMult-1)*100)}% Dmg</span>`);
    if (obj.buffs.speedMult > 1.0) pills.push(`<span class="pill-badge speed">+${Math.round((obj.buffs.speedMult-1)*100)}% Spd</span>`);
    if (obj.buffDuration && obj.buffDuration > 0) {
      pills.push(`<span class="pill-badge" style="background: rgba(0, 210, 255, 0.15); color: #00d2ff; border: 1px solid rgba(0, 210, 255, 0.4);">⏳ ${obj.buffDuration}s</span>`);
    } else {
      pills.push(`<span class="pill-badge" style="background: rgba(144, 224, 239, 0.1); color: var(--text-dim);">♾️ Perm</span>`);
    }

    let triggerBadge = "";
    if (obj.triggerType === "capture") triggerBadge = `<span class="trigger-badge capture" style="font-size: 0.65rem;">📡 Capture</span>`;
    else if (obj.triggerType === "walkover") triggerBadge = `<span class="trigger-badge walkover" style="font-size: 0.65rem;">🚶 Pickup (${obj.pickupRadius}r)</span>`;
    else triggerBadge = `<span class="trigger-badge both" style="font-size: 0.65rem;">⚡ Capture/Pickup</span>`;

    let timeText = obj.spawnDelay > 0 ? ` @ ${obj.spawnDelay}s` : " @ Start";

    item.innerHTML = `
      <div class="active-objective-top">
        <span class="active-objective-title">${obj.icon || "💎"} ${obj.name}</span>
        <button class="btn-remove-rule" title="Delete objective" data-idx="${idx}">✕</button>
      </div>
      <div class="active-objective-target">
        🎯 <strong>${obj.targetName}</strong> ${triggerBadge} <span style="color: var(--text-dim);">${timeText}</span>
      </div>
      <div class="relic-pills-row">${pills.join("")}</div>
    `;

    item.querySelector(".btn-remove-rule").addEventListener("click", () => {
      configuredObjectives.splice(idx, 1);
      renderActiveObjectives();
      showToast("Removed objective.");
    });

    activeObjectivesContainer.appendChild(item);
  });
}

// Export Mod
async function handleExportRelics() {
  if (configuredObjectives.length === 0) {
    alert("Please add at least one Relic Objective before exporting.");
    return;
  }

  const selectedScopeRadio = document.querySelector('input[name="target-scope"]:checked');
  const targetScope = selectedScopeRadio ? selectedScopeRadio.value : "global";
  const playerName = inputPlayerName.value.trim();

  if (targetScope === "player" && !playerName) {
    alert("Please enter the target player's FAF nickname.");
    inputPlayerName.focus();
    return;
  }

  const payload = {
    modName: inputModName.value.trim() || "Commander Relic Objectives",
    author: inputAuthor.value.trim() || "FAF Player",
    version: parseInt(inputVersion.value, 10) || 1,
    targetMode: targetScope,
    playerName: playerName,
    objectives: configuredObjectives
  };

  btnExportRelics.disabled = true;
  btnExportRelics.textContent = "⏳ Packaging Relics Mod...";

  try {
    const res = await fetch("/api/export-relics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const result = await res.json();

    if (result.success) {
      showToast("✅ Commander Relics Mod packaged and installed!");
      renderExportSuccess(result);
    } else {
      showToast("❌ Export error: " + result.error);
      renderExportError(result.error);
    }
  } catch (err) {
    showToast("❌ Export failed: " + err.message);
    renderExportError(err.message);
  } finally {
    btnExportRelics.disabled = false;
    btnExportRelics.innerHTML = `🚀 Pack & Export Relic Mod (<span id="btn-relics-count">${configuredObjectives.length}</span> objectives)`;
  }
}

function renderExportSuccess(result) {
  exportFeedback.className = "feedback-card";
  exportFeedback.style.display = "block";

  const modeBadge = result.targetMode === "player"
    ? `<span style="color: var(--accent-gold);">👑 Specific Player (${result.playerName})</span>`
    : `<span style="color: var(--accent-cyan);">🌐 Contested (Whoever Claims Wins)</span>`;

  exportFeedback.innerHTML = `
    <h4>🎉 Relic Objectives Mod Ready!</h4>
    <p><strong>${result.modName}</strong> (v${inputVersion.value})</p>
    <p>Scope: ${modeBadge} | Total Objectives: <strong>${result.objectivesCount}</strong></p>
    
    <div style="margin-top: 8px;">
      <span style="font-size: 0.72rem; color: var(--text-muted);">Installed directly to FAF Mods:</span>
      <div class="feedback-path">${result.targetModDir}</div>
    </div>

    <div style="margin-top: 6px;">
      <span style="font-size: 0.72rem; color: var(--text-muted);">Shareable Zip Archive:</span>
      <div class="feedback-path">${result.zipPath}</div>
    </div>

    <div style="margin-top: 10px; font-size: 0.72rem; color: var(--accent-cyan);">
      <strong>How to play in FAF:</strong><br>
      1. Host a game in the FAF Client.<br>
      2. Click <strong>Options / Mods</strong> in the lobby.<br>
      3. Enable <strong>"${result.modName}"</strong>.<br>
      4. Relics will spawn on the battlefield and grant rewards when your ACU captures or picks them up!
    </div>
  `;
}

function renderExportError(errorMsg) {
  exportFeedback.className = "feedback-card error";
  exportFeedback.style.display = "block";
  exportFeedback.innerHTML = `
    <h4 style="color: var(--accent-red);">❌ Export Failed</h4>
    <p style="font-size: 0.75rem;">${errorMsg}</p>
  `;
}

function showToast(msg) {
  toastEl.textContent = msg;
  toastEl.style.display = "block";
  setTimeout(() => {
    toastEl.style.display = "none";
  }, 3500);
}

// Launch
init();
