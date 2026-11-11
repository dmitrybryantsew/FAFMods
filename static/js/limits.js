// FAF Mod Forge - Unit Limiter System
// Enforce player-specific or global unit caps for T3 Mexes, Experimentals, and custom units.

let allUnits = [];
let unitMap = new Map();
let filteredCustomUnits = [];

// activeRules: Map of ruleId -> { id, name, limit, categoryLua, unitIds, icon, tag, isPreset }
const activeRules = new Map();

const PRESETS = [
  {
    id: "preset_t3_mex",
    icon: "💎",
    name: "T3 Mass Extractors",
    tag: "TECH3 * MASSEXTRACTION",
    desc: "Limits Tech 3 Mass Extractors across all factions (UEF, Cybran, Aeon, Seraphim, Nomads).",
    defaultLimit: 4,
    categoryLua: "categories.MASSEXTRACTION * categories.TECH3",
    recommended: true
  },
  {
    id: "preset_t2_mex",
    icon: "💎",
    name: "T2 Mass Extractors",
    tag: "TECH2 * MASSEXTRACTION",
    desc: "Limits Tech 2 Mass Extractors to balance mid-game eco.",
    defaultLimit: 8,
    categoryLua: "categories.MASSEXTRACTION * categories.TECH2",
    recommended: false
  },
  {
    id: "preset_all_mex",
    icon: "💎",
    name: "All Mass Extractors",
    tag: "MASSEXTRACTION",
    desc: "Global cap on total Mass Extractors of any tech tier owned by the player.",
    defaultLimit: 16,
    categoryLua: "categories.MASSEXTRACTION",
    recommended: false
  },
  {
    id: "preset_all_exp",
    icon: "🚀",
    name: "All Experimentals (T4)",
    tag: "EXPERIMENTAL",
    desc: "Total cap on all Experimental combat units (Colossus, Fatboy, Megalith, Ahwassa, etc.).",
    defaultLimit: 2,
    categoryLua: "categories.EXPERIMENTAL",
    recommended: true
  },
  {
    id: "preset_paragon",
    icon: "👑",
    name: "Paragon (Resource Gen)",
    tag: "EXPERIMENTAL * ECONOMIC",
    desc: "Bans or limits the Aeon Game-Ender Paragon (infinite resources). Default limit 0 = Banned.",
    defaultLimit: 0,
    categoryLua: "categories.EXPERIMENTAL * categories.STRUCTURE * categories.ECONOMIC",
    recommended: true
  },
  {
    id: "preset_nukes",
    icon: "☢️",
    name: "Strategic Nuke Silos",
    tag: "STRATEGIC * SILO",
    desc: "Limits Strategic Missile Launchers to prevent end-game nuclear spam.",
    defaultLimit: 1,
    categoryLua: "categories.STRATEGIC * categories.SILO",
    recommended: true
  },
  {
    id: "preset_smd",
    icon: "🛡️",
    name: "Strategic Missile Defense (SMD)",
    tag: "ANTIMISSILE * TECH3",
    desc: "Limits Anti-Nuke Silo installations.",
    defaultLimit: 2,
    categoryLua: "categories.ANTIMISSILE * categories.TECH3 * categories.STRUCTURE",
    recommended: false
  },
  {
    id: "preset_t3_arty",
    icon: "🎯",
    name: "T3 Heavy Artillery",
    tag: "TECH3 * ARTILLERY",
    desc: "Limits map-wide strategic heavy artillery batteries (Mavor, Scathis, Salvation, T3 Arty).",
    defaultLimit: 1,
    categoryLua: "categories.TECH3 * categories.ARTILLERY * categories.STRUCTURE",
    recommended: false
  },
  {
    id: "preset_t3_pgen",
    icon: "⚡",
    name: "T3 Power Generators",
    tag: "TECH3 * ENERGYPRODUCTION",
    desc: "Limits T3 Power Generators to avoid massive chain-reaction explosions and power spam.",
    defaultLimit: 6,
    categoryLua: "categories.ENERGYPRODUCTION * categories.TECH3 * categories.STRUCTURE",
    recommended: false
  },
  {
    id: "preset_t3_omni",
    icon: "🛰️",
    name: "T3 Omni Sensor / Radar",
    tag: "TECH3 * RADAR",
    desc: "Limits long-range Omni and radar installations.",
    defaultLimit: 1,
    categoryLua: "categories.TECH3 * categories.RADAR * categories.STRUCTURE",
    recommended: false
  },
  {
    id: "preset_t3_shield",
    icon: "🛡️",
    name: "T3 Heavy Shield Generators",
    tag: "TECH3 * SHIELD",
    desc: "Limits stationary shield generators to prevent turtle shield overlapping.",
    defaultLimit: 4,
    categoryLua: "categories.TECH3 * categories.SHIELD * categories.STRUCTURE",
    recommended: false
  },
  {
    id: "preset_flagships",
    icon: "🚢",
    name: "T3/T4 Naval Flagships",
    tag: "BATTLESHIP + CARRIER",
    desc: "Limits capital battleships, aircraft carriers, and experimental dreadnoughts.",
    defaultLimit: 3,
    categoryLua: "categories.BATTLESHIP + categories.CARRIER + categories.DREADNOUGHT",
    recommended: false
  }
];

const customFilters = {
  search: "",
  faction: "ALL",
  tech: "ALL",
  type: "ALL"
};

// DOM Elements
const presetGrid = document.getElementById("preset-grid");
const customUnitGrid = document.getElementById("custom-unit-grid");
const totalLimitsCount = document.getElementById("total-limits-count");
const activeBadgeCount = document.getElementById("active-badge-count");
const btnLimitsCount = document.getElementById("btn-limits-count");
const activeRulesContainer = document.getElementById("active-rules-container");
const rulesEmptyState = document.getElementById("rules-empty-state");

const customSearch = document.getElementById("custom-search");
const clearCustomSearch = document.getElementById("clear-custom-search");
const filteredUnitsText = document.getElementById("filtered-units-text");

const btnEnableRecommended = document.getElementById("btn-enable-recommended");
const btnDisableAllPresets = document.getElementById("btn-disable-all-presets");
const btnClearAllRules = document.getElementById("btn-clear-all-rules");

const cardScopePlayer = document.getElementById("card-scope-player");
const cardScopeGlobal = document.getElementById("card-scope-global");
const groupPlayerName = document.getElementById("group-player-name");
const inputPlayerName = document.getElementById("input-player-name");
const inputModName = document.getElementById("input-mod-name");
const inputAuthor = document.getElementById("input-author");
const inputVersion = document.getElementById("input-version");

const btnExportLimits = document.getElementById("btn-export-limits");
const btnOpenFolder = document.getElementById("btn-open-folder");
const exportFeedback = document.getElementById("export-feedback");
const toastEl = document.getElementById("toast");

// --- Initialization ---
async function init() {
  setupEventListeners();
  loadSavedMetadata();

  const savedLimits = ForgeStore.getLimits();
  if (savedLimits && Array.isArray(savedLimits) && savedLimits.length > 0) {
    activeRules.clear();
    savedLimits.forEach(r => activeRules.set(r.id, r));
    renderPresets();
    renderActiveRulesList();
    updateCounters();
  } else if (savedLimits !== null) {
    // User intentionally cleared or emptied all limits previously
    activeRules.clear();
    renderPresets();
    renderActiveRulesList();
    updateCounters();
  } else if (ForgeStore.isFirstVisit()) {
    enableRecommendedPresets();
  } else {
    renderPresets();
    renderActiveRulesList();
    updateCounters();
  }

  await loadUnits();
  ForgeStore.syncNavBadges();
}

function loadSavedMetadata() {
  const meta = ForgeStore.getModMeta();
  if (meta.modName && meta.modName !== "FAF Master Overhaul") inputModName.value = meta.modName;
  if (meta.author) inputAuthor.value = meta.author;
  if (meta.version) inputVersion.value = meta.version;
  if (meta.playerName) inputPlayerName.value = meta.playerName;
  if (meta.targetMode === "global") {
    cardScopeGlobal.classList.add("active");
    cardScopePlayer.classList.remove("active");
    cardScopeGlobal.querySelector("input").checked = true;
    groupPlayerName.style.display = "none";
  } else {
    cardScopePlayer.classList.add("active");
    cardScopeGlobal.classList.remove("active");
    cardScopePlayer.querySelector("input").checked = true;
    groupPlayerName.style.display = "block";
  }
}

function saveCurrentMetadata() {
  const targetMode = document.querySelector('input[name="target-scope"]:checked')?.value || "player";
  ForgeStore.setModMeta({
    author: inputAuthor.value.trim(),
    version: parseInt(inputVersion.value, 10) || 1,
    targetMode,
    playerName: inputPlayerName.value.trim()
  });
}

async function loadUnits() {
  try {
    const res = await fetch("/api/units");
    allUnits = await res.json();
    unitMap.clear();
    allUnits.forEach(u => unitMap.set(u.id, u));
    applyCustomFilters();
  } catch (err) {
    showToast("Failed to load units database: " + err.message);
  }
}

// --- Render Preset Cards ---
function renderPresets() {
  presetGrid.innerHTML = "";

  PRESETS.forEach(preset => {
    const isEnabled = activeRules.has(preset.id);
    const rule = isEnabled ? activeRules.get(preset.id) : null;
    const currentLimit = rule ? rule.limit : preset.defaultLimit;
    const isBanned = currentLimit === 0 && isEnabled;

    const card = document.createElement("div");
    card.className = `preset-card ${isEnabled ? "active" : ""} ${isBanned ? "banned" : ""}`;
    card.id = `preset-card-${preset.id}`;

    card.innerHTML = `
      <div class="preset-card-top">
        <div class="preset-icon">${preset.icon}</div>
        <div class="preset-info">
          <div class="preset-title">${preset.name}</div>
          <span class="preset-category-tag">${preset.tag}</span>
          <div class="preset-desc">${preset.desc}</div>
        </div>
      </div>
      <div class="preset-card-bottom">
        <div class="stepper-control">
          <button class="stepper-btn btn-minus" title="Decrease limit" ${!isEnabled ? "disabled" : ""}>-</button>
          <input type="text" class="stepper-val" value="${currentLimit}" ${!isEnabled ? "disabled" : ""}>
          <button class="stepper-btn btn-plus" title="Increase limit" ${!isEnabled ? "disabled" : ""}>+</button>
        </div>
        <label class="switch-container" title="${isEnabled ? 'Click to disable rule' : 'Click to enable rule'}">
          <span style="font-size: 0.75rem; color: ${isEnabled ? 'var(--accent-cyan)' : 'var(--text-muted)'}; font-weight: 600;">
            ${isBanned ? '⛔ Banned' : isEnabled ? 'Active' : 'Off'}
          </span>
          <div class="toggle-switch">
            <input type="checkbox" class="toggle-input" ${isEnabled ? "checked" : ""}>
            <span class="slider-switch"></span>
          </div>
        </label>
      </div>
    `;

    // Toggle switch listener
    const toggleInput = card.querySelector(".toggle-input");
    toggleInput.addEventListener("change", (e) => {
      if (e.target.checked) {
        setPresetRule(preset, currentLimit);
      } else {
        removeRule(preset.id);
      }
    });

    // Stepper listeners
    const stepperVal = card.querySelector(".stepper-val");
    const btnMinus = card.querySelector(".btn-minus");
    const btnPlus = card.querySelector(".btn-plus");

    btnMinus.addEventListener("click", () => {
      let val = parseInt(stepperVal.value, 10) || 0;
      if (val > 0) {
        val -= 1;
        stepperVal.value = val;
        updateRuleLimit(preset.id, val);
      }
    });

    btnPlus.addEventListener("click", () => {
      let val = parseInt(stepperVal.value, 10) || 0;
      val += 1;
      stepperVal.value = val;
      updateRuleLimit(preset.id, val);
    });

    stepperVal.addEventListener("change", () => {
      let val = parseInt(stepperVal.value, 10);
      if (isNaN(val) || val < 0) val = 0;
      stepperVal.value = val;
      updateRuleLimit(preset.id, val);
    });

    presetGrid.appendChild(card);
  });
}

function setPresetRule(preset, limit) {
  activeRules.set(preset.id, {
    id: preset.id,
    name: preset.name,
    limit: limit,
    categoryLua: preset.categoryLua,
    unitIds: [],
    icon: preset.icon,
    tag: preset.tag,
    isPreset: true
  });

  ForgeStore.setLimits(activeRules);
  renderPresets();
  renderActiveRulesList();
  updateCounters();
}

function updateRuleLimit(ruleId, newLimit) {
  if (activeRules.has(ruleId)) {
    const rule = activeRules.get(ruleId);
    rule.limit = newLimit;
    activeRules.set(ruleId, rule);
    ForgeStore.setLimits(activeRules);
    renderPresets();
    renderActiveRulesList();
  }
}

function removeRule(ruleId) {
  if (activeRules.has(ruleId)) {
    const rule = activeRules.get(ruleId);
    activeRules.delete(ruleId);
    ForgeStore.setLimits(activeRules);
    renderPresets();
    renderActiveRulesList();
    applyCustomFilters(); // update button state in custom picker
    updateCounters();
    showToast(`Removed limit: ${rule.name}`);
  }
}

function enableRecommendedPresets() {
  PRESETS.filter(p => p.recommended).forEach(p => {
    activeRules.set(p.id, {
      id: p.id,
      name: p.name,
      limit: p.defaultLimit,
      categoryLua: p.categoryLua,
      unitIds: [],
      icon: p.icon,
      tag: p.tag,
      isPreset: true
    });
  });

  ForgeStore.setLimits(activeRules);
  renderPresets();
  renderActiveRulesList();
  updateCounters();
  showToast("Recommended limit presets enabled!");
}

function disableAllPresets() {
  PRESETS.forEach(p => {
    if (activeRules.has(p.id)) {
      activeRules.delete(p.id);
    }
  });

  ForgeStore.setLimits(activeRules);
  renderPresets();
  renderActiveRulesList();
  updateCounters();
  showToast("All category presets disabled.");
}

function clearAllRules() {
  activeRules.clear();
  ForgeStore.setLimits(activeRules);
  renderPresets();
  renderActiveRulesList();
  applyCustomFilters();
  updateCounters();
  showToast("All active limits cleared.");
}

// --- Active Rules List Rendering ---
function renderActiveRulesList() {
  // Clear container except empty state
  activeRulesContainer.innerHTML = "";

  if (activeRules.size === 0) {
    activeRulesContainer.appendChild(rulesEmptyState);
    rulesEmptyState.style.display = "block";
    return;
  }

  rulesEmptyState.style.display = "none";

  activeRules.forEach(rule => {
    const isBanned = rule.limit === 0;
    const item = document.createElement("div");
    item.className = `active-rule-item ${isBanned ? "banned" : ""}`;

    item.innerHTML = `
      <div class="active-rule-info">
        <div class="active-rule-title" title="${rule.name}">
          ${rule.icon || "🛑"} ${rule.name}
        </div>
        <div class="active-rule-sub">
          ${rule.tag} &bull; <strong style="color: ${isBanned ? 'var(--accent-red)' : 'var(--accent-cyan)'};">
            ${isBanned ? 'BANNED (0)' : `Limit: ${rule.limit}`}
          </strong>
        </div>
      </div>
      <div class="active-rule-controls">
        <div class="stepper-control">
          <button class="stepper-btn item-btn-minus">-</button>
          <input type="text" class="stepper-val item-stepper-val" value="${rule.limit}">
          <button class="stepper-btn item-btn-plus">+</button>
        </div>
        <button class="btn-remove-rule" title="Remove limit">✕</button>
      </div>
    `;

    const itemMinus = item.querySelector(".item-btn-minus");
    const itemPlus = item.querySelector(".item-btn-plus");
    const itemVal = item.querySelector(".item-stepper-val");
    const btnRemove = item.querySelector(".btn-remove-rule");

    itemMinus.addEventListener("click", () => {
      let val = parseInt(itemVal.value, 10) || 0;
      if (val > 0) {
        val -= 1;
        itemVal.value = val;
        updateRuleLimit(rule.id, val);
      }
    });

    itemPlus.addEventListener("click", () => {
      let val = parseInt(itemVal.value, 10) || 0;
      val += 1;
      itemVal.value = val;
      updateRuleLimit(rule.id, val);
    });

    itemVal.addEventListener("change", () => {
      let val = parseInt(itemVal.value, 10);
      if (isNaN(val) || val < 0) val = 0;
      itemVal.value = val;
      updateRuleLimit(rule.id, val);
    });

    btnRemove.addEventListener("click", () => {
      removeRule(rule.id);
    });

    activeRulesContainer.appendChild(item);
  });
}

function updateCounters() {
  const count = activeRules.size;
  totalLimitsCount.textContent = count;
  activeBadgeCount.textContent = count;
  btnLimitsCount.textContent = count;
}

// --- Custom Unit Limiter & Grid ---
function applyCustomFilters() {
  const searchLower = customFilters.search.trim().toLowerCase();

  filteredCustomUnits = allUnits.filter(u => {
    if (customFilters.faction !== "ALL" && (u.faction || "").toUpperCase() !== customFilters.faction.toUpperCase()) {
      return false;
    }
    if (customFilters.tech !== "ALL" && (u.tech || "").toUpperCase() !== customFilters.tech.toUpperCase()) {
      return false;
    }
    if (customFilters.type !== "ALL" && (u.type || "").toUpperCase() !== customFilters.type.toUpperCase()) {
      return false;
    }
    if (searchLower) {
      const matchId = u.id.toLowerCase().includes(searchLower);
      const matchName = (u.name || "").toLowerCase().includes(searchLower);
      const matchDesc = (u.desc || "").toLowerCase().includes(searchLower);
      const matchFaction = (u.faction || "").toLowerCase().includes(searchLower);
      if (!matchId && !matchName && !matchDesc && !matchFaction) return false;
    }
    return true;
  });

  filteredUnitsText.textContent = `${filteredCustomUnits.length} of ${allUnits.length} units shown`;
  renderCustomUnitGrid();
}

function renderCustomUnitGrid() {
  customUnitGrid.innerHTML = "";

  // Render first 60 filtered units for fast rendering performance
  const displaySlice = filteredCustomUnits.slice(0, 60);

  const fragment = document.createDocumentFragment();

  displaySlice.forEach(u => {
    const ruleId = `unit_${u.id.toLowerCase()}`;
    const isLimited = activeRules.has(ruleId);
    const existingRule = isLimited ? activeRules.get(ruleId) : null;

    const card = document.createElement("div");
    card.className = `unit-card ${isLimited ? "included" : ""}`;

    const factionClass = (u.faction || "").toLowerCase();
    const techClass = (u.tech || "").toLowerCase();

    card.innerHTML = `
      <div class="faction-bar ${factionClass}"></div>
      <span class="unit-tech-badge ${techClass}">${u.tech}</span>
      <div class="unit-icon-wrapper">
        <div class="icon-${u.id}"></div>
      </div>
      <div class="unit-info">
        <div class="unit-id">${u.id}</div>
        <div class="unit-name" title="${u.name}">${u.name}</div>
        <div class="unit-stats-mini">
          <span>🛡️ ${u.hp || 0}</span>
          <span>💰 ${u.mass || 0}</span>
        </div>
      </div>
      <button class="unit-card-limit-btn ${isLimited ? 'added' : ''}">
        ${isLimited ? `✓ Limit: ${existingRule.limit}` : '+ Add Limit'}
      </button>
    `;

    const limitBtn = card.querySelector(".unit-card-limit-btn");
    limitBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (activeRules.has(ruleId)) {
        removeRule(ruleId);
      } else {
        addCustomUnitLimit(u);
      }
    });

    fragment.appendChild(card);
  });

  customUnitGrid.appendChild(fragment);
}

function addCustomUnitLimit(unit) {
  const ruleId = `unit_${unit.id.toLowerCase()}`;
  activeRules.set(ruleId, {
    id: ruleId,
    name: unit.name,
    limit: 1, // Default limit 1 for individual units
    categoryLua: `categories.${unit.id.toUpperCase()}`,
    unitIds: [unit.id.toLowerCase()],
    icon: "🎯",
    tag: `${unit.faction} ${unit.tech}`,
    isPreset: false
  });

  ForgeStore.setLimits(activeRules);
  renderActiveRulesList();
  applyCustomFilters();
  updateCounters();
  showToast(`Added unit limit for ${unit.name} (Max: 1)`);
}

// --- Event Listeners Setup ---
function setupEventListeners() {
  // Navigation between Forge & Limits
  btnEnableRecommended.addEventListener("click", enableRecommendedPresets);
  btnDisableAllPresets.addEventListener("click", disableAllPresets);
  btnClearAllRules.addEventListener("click", clearAllRules);

  // Search
  customSearch.addEventListener("input", (e) => {
    customFilters.search = e.target.value;
    clearCustomSearch.style.display = customFilters.search ? "block" : "none";
    applyCustomFilters();
  });

  clearCustomSearch.addEventListener("click", () => {
    customSearch.value = "";
    customFilters.search = "";
    clearCustomSearch.style.display = "none";
    applyCustomFilters();
  });

  // Filter Chips
  const filterContainers = [
    { container: document.getElementById("custom-faction-chips"), key: "faction" },
    { container: document.getElementById("custom-tech-chips"), key: "tech" },
    { container: document.getElementById("custom-type-chips"), key: "type" }
  ];

  filterContainers.forEach(({ container, key }) => {
    container.addEventListener("click", (e) => {
      if (e.target.classList.contains("chip")) {
        container.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
        e.target.classList.add("active");
        customFilters[key] = e.target.dataset.val;
        applyCustomFilters();
      }
    });
  });

  // Target Scope Switcher
  cardScopePlayer.addEventListener("click", () => {
    cardScopePlayer.classList.add("active");
    cardScopeGlobal.classList.remove("active");
    cardScopePlayer.querySelector("input").checked = true;
    groupPlayerName.style.display = "block";
    saveCurrentMetadata();
  });

  cardScopeGlobal.addEventListener("click", () => {
    cardScopeGlobal.classList.add("active");
    cardScopePlayer.classList.remove("active");
    cardScopeGlobal.querySelector("input").checked = true;
    groupPlayerName.style.display = "none";
    saveCurrentMetadata();
  });

  // Metadata inputs change listeners
  inputAuthor.addEventListener("input", saveCurrentMetadata);
  inputVersion.addEventListener("input", saveCurrentMetadata);
  inputPlayerName.addEventListener("input", saveCurrentMetadata);

  // Export Action
  btnExportLimits.addEventListener("click", handleExportLimits);

  // Open Mods Folder
  btnOpenFolder.addEventListener("click", async () => {
    try {
      await fetch("/api/open-folder", { method: "POST" });
      showToast("Opened Supreme Commander Mods folder.");
    } catch (err) {
      showToast("Failed to open folder: " + err.message);
    }
  });
}

// --- Export Mod Handler ---
async function handleExportLimits() {
  if (activeRules.size === 0) {
    showToast("⚠️ Please configure at least one unit or category limit first!");
    return;
  }

  const modName = inputModName.value.trim() || "Player Unit Limits";
  const author = inputAuthor.value.trim() || "User";
  const version = parseInt(inputVersion.value, 10) || 1;
  const targetMode = document.querySelector('input[name="target-scope"]:checked').value;
  const playerName = inputPlayerName.value.trim();

  if (targetMode === "player" && !playerName) {
    showToast("⚠️ Please enter the exact FAF lobby nickname for the player!");
    inputPlayerName.focus();
    return;
  }

  // Convert Map to array of rules
  const rulesList = [];
  activeRules.forEach(rule => {
    rulesList.push({
      id: rule.id,
      name: rule.name,
      limit: rule.limit,
      categoryLua: rule.categoryLua,
      unitIds: rule.unitIds || []
    });
  });

  const payload = {
    modName,
    author,
    version,
    targetMode,
    playerName,
    rules: rulesList
  };

  btnExportLimits.disabled = true;
  btnExportLimits.textContent = "⏳ Packaging Limits Mod...";
  exportFeedback.style.display = "none";

  try {
    const res = await fetch("/api/export-limits", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const result = await res.json();

    if (result.success) {
      showToast("✅ Unit Limits Mod packaged and installed!");
      renderExportSuccess(result);
    } else {
      showToast("❌ Export error: " + result.error);
      renderExportError(result.error);
    }
  } catch (err) {
    showToast("❌ Export failed: " + err.message);
    renderExportError(err.message);
  } finally {
    btnExportLimits.disabled = false;
    btnExportLimits.innerHTML = `🚀 Pack & Export Limits Mod (<span id="btn-limits-count">${activeRules.size}</span> rules)`;
  }
}

function renderExportSuccess(result) {
  exportFeedback.className = "feedback-card";
  exportFeedback.style.display = "block";

  const modeBadge = result.targetMode === "player"
    ? `<span style="color: var(--accent-gold);">👑 Specific Player (${result.playerName})</span>`
    : `<span style="color: var(--accent-cyan);">🌐 Global (All Players)</span>`;

  exportFeedback.innerHTML = `
    <h4>🎉 Limits Mod Ready!</h4>
    <p><strong>${result.modName}</strong> (v${inputVersion.value})</p>
    <p>Target: ${modeBadge} | Active Limits: <strong>${result.rulesCount}</strong></p>
    
    <div style="margin-top: 8px;">
      <span style="font-size: 0.72rem; color: var(--text-muted);">Installed to Game Mods:</span>
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
      4. Limits are enforced automatically in the Sim tick engine!
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

// Start
init();
