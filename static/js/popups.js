// FAF Mod Forge - In-Game Tactical Event Popups & Alerts System
// Create notifications with pinpoint camera buttons, sound cues, and interactive triggers

let allUnits = [];
let unitMap = new Map();
let filteredUnits = [];
let selectedTargetUnit = null;

// activeRules: Map of ruleId -> rule object
const activeRules = new Map();

const PRESETS = [
  {
    id: "preset_all_exp",
    icon: "🚀",
    name: "All Experimentals (T4) Online",
    tag: "EXPERIMENTAL",
    desc: "Alerts when any T4 Experimental unit completes with an immediate Pinpoint camera button.",
    trigger: "unit_built",
    categoryLua: "categories.EXPERIMENTAL",
    unitIds: [],
    title: "⚠️ EXPERIMENTAL DETECTED",
    text: "Hostile {UnitName} has completed construction! Pinpoint to engage.",
    theme: "danger",
    sound: "UI_Alarm",
    hasPinpoint: true,
    hasPing: true,
    hasDismiss: true,
    duration: 10,
    recommended: true
  },
  {
    id: "preset_nuke_silo",
    icon: "☢️",
    name: "Strategic Nuke Silo Finished",
    tag: "STRATEGIC * SILO",
    desc: "Warns all players when a Strategic Missile Silo completes so they can build SMD missile defenses.",
    trigger: "unit_built",
    categoryLua: "categories.STRATEGIC * categories.SILO",
    unitIds: [],
    title: "☢️ STRATEGIC SILO ONLINE",
    text: "Strategic Nuclear Silo constructed! Prepare missile defenses.",
    theme: "danger",
    sound: "UI_Alarm",
    hasPinpoint: true,
    hasPing: true,
    hasDismiss: true,
    duration: 12,
    recommended: true
  },
  {
    id: "preset_paragon",
    icon: "👑",
    name: "Paragon Quantum Generator Built",
    tag: "PARAGON * ECO",
    desc: "Urgent broadcast when Aeon Paragon (infinite mass & energy) is finished.",
    trigger: "unit_built",
    categoryLua: "categories.EXPERIMENTAL * categories.STRUCTURE * categories.ECONOMIC",
    unitIds: [],
    title: "👑 PARAGON ONLINE",
    text: "Aeon Quantum Resource Generator is online! Infinite resources detected.",
    theme: "quantum",
    sound: "UI_Alarm",
    hasPinpoint: true,
    hasPing: true,
    hasDismiss: true,
    duration: 12,
    recommended: true
  },
  {
    id: "preset_acu_killed",
    icon: "💥",
    name: "Commander Eliminated Broadcast",
    tag: "COMMAND",
    desc: "Broadcasts an alert across the match whenever an Armored Command Unit is destroyed.",
    trigger: "unit_killed",
    categoryLua: "categories.COMMAND",
    unitIds: [],
    title: "💥 COMMANDER DESTROYED",
    text: "An Armored Command Unit has suffered total catastrophic detonation!",
    theme: "tactical",
    sound: "UI_Objective_Complete",
    hasPinpoint: true,
    hasPing: true,
    hasDismiss: true,
    duration: 10,
    recommended: true
  },
  {
    id: "preset_acu_danger",
    icon: "🚨",
    name: "Commander Critical Health (< 35%)",
    tag: "COMMAND * DANGER",
    desc: "Emergency alarm when your ACU is below 35% health with instant camera jump.",
    trigger: "health_low",
    categoryLua: "categories.COMMAND",
    unitIds: [],
    healthPct: 35,
    title: "🚨 COMMANDER UNDER HEAVY ATTACK",
    text: "Commander health is critical (< 35%)! Evacuate or reinforce immediately.",
    theme: "danger",
    sound: "UI_Alarm",
    hasPinpoint: true,
    hasPing: true,
    hasDismiss: true,
    duration: 12,
    recommended: true
  },
  {
    id: "preset_t3_arty",
    icon: "🎯",
    name: "T3 Heavy Artillery Completed",
    tag: "TECH3 * ARTILLERY",
    desc: "Alerts when map-wide strategic heavy artillery (Mavor, Scathis, Salvation) is built.",
    trigger: "unit_built",
    categoryLua: "categories.TECH3 * categories.ARTILLERY * categories.STRUCTURE",
    unitIds: [],
    title: "🎯 STRATEGIC ARTILLERY ONLINE",
    text: "Heavy strategic artillery battery constructed! Shield defenses advised.",
    theme: "tactical",
    sound: "UI_Radar_Blip",
    hasPinpoint: true,
    hasPing: true,
    hasDismiss: true,
    duration: 8,
    recommended: false
  },
  {
    id: "preset_timer_20m",
    icon: "⏱️",
    name: "20-Minute Strategic Milestone",
    tag: "MATCH TIMER",
    desc: "Tactical briefing notification at 20 minutes for strategic transition.",
    trigger: "match_timer",
    timerSeconds: 1200,
    categoryLua: "",
    unitIds: [],
    title: "⏱️ MATCH TIME: 20 MINUTES",
    text: "Late game phase initiated. Experimental units and strategic warfare imminent.",
    theme: "intel",
    sound: "UI_Radar_Blip",
    hasPinpoint: false,
    hasPing: false,
    hasDismiss: true,
    duration: 8,
    recommended: false
  }
];

// Current filter state for unit mini-grid
const filterState = {
  search: "",
  faction: "ALL",
  tech: "ALL"
};

document.addEventListener("DOMContentLoaded", async () => {
  setupNavigationAndScope();
  setupPresets();
  setupCustomBuilderControls();
  setupLivePreviewListeners();
  setupExport();
  updateLivePreview();

  loadSavedMetadata();
  const savedPopups = ForgeStore.getPopups();
  if (savedPopups && Array.isArray(savedPopups) && savedPopups.length > 0) {
    activeRules.clear();
    savedPopups.forEach(r => activeRules.set(r.id, r));
    renderActiveRules();
    updatePresetsGridUI();
  } else if (savedPopups !== null) {
    activeRules.clear();
    renderActiveRules();
    updatePresetsGridUI();
  } else if (ForgeStore.isFirstVisit()) {
    enableRecommendedPresets();
  } else {
    renderActiveRules();
    updatePresetsGridUI();
  }
  ForgeStore.syncNavBadges();

  // Load units from API
  try {
    const res = await fetch("/api/units");
    allUnits = await res.json();
    for (const u of allUnits) {
      unitMap.set(u.id.toLowerCase(), u);
    }
    applyUnitFilters();
  } catch (err) {
    console.error("Failed to fetch units:", err);
    showToast("Failed to load units for selector", "error");
  }
});

function loadSavedMetadata() {
  const meta = ForgeStore.getModMeta();
  const inputMod = document.getElementById("input-mod-name");
  const inputAuthor = document.getElementById("input-author");
  const inputVersion = document.getElementById("input-version");
  const inputPlayerName = document.getElementById("input-player-name");
  const radioScopePlayer = document.querySelector('input[name="target-scope"][value="player"]');
  const radioScopeGlobal = document.querySelector('input[name="target-scope"][value="global"]');
  const groupPlayerName = document.getElementById("group-player-name");
  const cardScopePlayer = document.getElementById("card-scope-player");
  const cardScopeGlobal = document.getElementById("card-scope-global");

  if (meta.modName && meta.modName !== "FAF Master Overhaul" && inputMod) inputMod.value = meta.modName;
  if (meta.author && inputAuthor) inputAuthor.value = meta.author;
  if (meta.version && inputVersion) inputVersion.value = meta.version;
  if (meta.playerName && inputPlayerName) inputPlayerName.value = meta.playerName;
  if (meta.targetMode === "global") {
    if (radioScopeGlobal) radioScopeGlobal.checked = true;
    if (cardScopeGlobal) cardScopeGlobal.classList.add("active");
    if (cardScopePlayer) cardScopePlayer.classList.remove("active");
    if (groupPlayerName) groupPlayerName.style.display = "none";
  } else {
    if (radioScopePlayer) radioScopePlayer.checked = true;
    if (cardScopePlayer) cardScopePlayer.classList.add("active");
    if (cardScopeGlobal) cardScopeGlobal.classList.remove("active");
    if (groupPlayerName) groupPlayerName.style.display = "block";
  }
}

function saveCurrentMetadata() {
  const inputAuthor = document.getElementById("input-author");
  const inputVersion = document.getElementById("input-version");
  const inputPlayerName = document.getElementById("input-player-name");
  const targetMode = document.querySelector('input[name="target-scope"]:checked')?.value || "global";
  ForgeStore.setModMeta({
    author: inputAuthor ? inputAuthor.value.trim() : "User",
    version: inputVersion ? (parseInt(inputVersion.value, 10) || 1) : 1,
    targetMode,
    playerName: inputPlayerName ? inputPlayerName.value.trim() : ""
  });
}

/* =========================================================
   1. Scope & Navigation Setup
   ========================================================= */
function setupNavigationAndScope() {
  const radioScopePlayer = document.querySelector('input[name="target-scope"][value="player"]');
  const radioScopeGlobal = document.querySelector('input[name="target-scope"][value="global"]');
  const groupPlayerName = document.getElementById("group-player-name");
  const cardScopePlayer = document.getElementById("card-scope-player");
  const cardScopeGlobal = document.getElementById("card-scope-global");
  const inputAuthor = document.getElementById("input-author");
  const inputVersion = document.getElementById("input-version");
  const inputPlayerName = document.getElementById("input-player-name");

  function syncScopeUI() {
    const isPlayer = radioScopePlayer.checked;
    groupPlayerName.style.display = isPlayer ? "block" : "none";
    if (isPlayer) {
      cardScopePlayer.classList.add("active");
      cardScopeGlobal.classList.remove("active");
    } else {
      cardScopeGlobal.classList.add("active");
      cardScopePlayer.classList.remove("active");
    }
    saveCurrentMetadata();
  }

  radioScopePlayer.addEventListener("change", syncScopeUI);
  radioScopeGlobal.addEventListener("change", syncScopeUI);

  if (inputAuthor) inputAuthor.addEventListener("input", saveCurrentMetadata);
  if (inputVersion) inputVersion.addEventListener("input", saveCurrentMetadata);
  if (inputPlayerName) inputPlayerName.addEventListener("input", saveCurrentMetadata);

  // Folder open button
  document.getElementById("btn-open-folder").addEventListener("click", async () => {
    try {
      const res = await fetch("/api/open-folder", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        showToast("Opened Supreme Commander mods directory", "info");
      }
    } catch (e) {
      showToast("Could not open mods folder", "error");
    }
  });

  // Clear all rules
  document.getElementById("btn-clear-all-rules").addEventListener("click", () => {
    if (activeRules.size === 0) return;
    activeRules.clear();
    renderActiveRules();
    updatePresetsGridUI();
    showToast("Cleared all active popup rules", "info");
  });
}

/* =========================================================
   2. Presets Grid
   ========================================================= */
function setupPresets() {
  const grid = document.getElementById("preset-grid");
  grid.innerHTML = "";

  PRESETS.forEach(preset => {
    const card = document.createElement("div");
    card.className = "popup-preset-card";
    card.id = `preset-card-${preset.id}`;
    card.innerHTML = `
      <div class="popup-preset-top">
        <div class="popup-preset-icon">${preset.icon}</div>
        <div class="popup-preset-info">
          <div class="popup-preset-title">${preset.name}</div>
          <div class="popup-preset-tag">${preset.tag}</div>
          <div class="popup-preset-desc">${preset.desc}</div>
        </div>
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
        <span style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase;">${preset.trigger.replace('_', ' ')}</span>
        <button class="btn btn-sm btn-outline btn-toggle-preset" data-preset-id="${preset.id}">
          + Add Preset
        </button>
      </div>
    `;

    const toggleBtn = card.querySelector(".btn-toggle-preset");
    toggleBtn.addEventListener("click", () => togglePreset(preset.id));

    grid.appendChild(card);
  });

  document.getElementById("btn-enable-recommended-presets").addEventListener("click", () => {
    let count = 0;
    PRESETS.filter(p => p.recommended).forEach(p => {
      if (!activeRules.has(p.id)) {
        addRuleFromPreset(p);
        count++;
      }
    });
    renderActiveRules();
    updatePresetsGridUI();
    showToast(`Added ${count} recommended event popups!`, "success");
  });

  document.getElementById("btn-clear-presets").addEventListener("click", () => {
    PRESETS.forEach(p => activeRules.delete(p.id));
    renderActiveRules();
    updatePresetsGridUI();
    showToast("Removed preset popup rules", "info");
  });
}

function togglePreset(presetId) {
  const preset = PRESETS.find(p => p.id === presetId);
  if (!preset) return;

  if (activeRules.has(presetId)) {
    activeRules.delete(presetId);
    showToast(`Removed: ${preset.name}`, "info");
  } else {
    addRuleFromPreset(preset);
    showToast(`Added: ${preset.name}`, "success");
  }
  renderActiveRules();
  updatePresetsGridUI();
}

function addRuleFromPreset(preset) {
  activeRules.set(preset.id, {
    id: preset.id,
    name: preset.name,
    icon: preset.icon,
    trigger: preset.trigger,
    categoryLua: preset.categoryLua || "",
    unitIds: preset.unitIds || [],
    healthPct: preset.healthPct || 35,
    timerSeconds: preset.timerSeconds || 600,
    title: preset.title,
    text: preset.text,
    theme: preset.theme,
    sound: preset.sound,
    hasPinpoint: preset.hasPinpoint,
    hasPing: preset.hasPing,
    hasDismiss: preset.hasDismiss,
    duration: preset.duration || 8,
    isPreset: true
  });
}

function updatePresetsGridUI() {
  PRESETS.forEach(p => {
    const card = document.getElementById(`preset-card-${p.id}`);
    if (!card) return;
    const btn = card.querySelector(".btn-toggle-preset");
    if (activeRules.has(p.id)) {
      card.style.borderColor = "var(--accent-cyan)";
      btn.className = "btn btn-sm btn-primary btn-toggle-preset";
      btn.textContent = "✓ Added";
    } else {
      card.style.borderColor = "var(--border-color)";
      btn.className = "btn btn-sm btn-outline btn-toggle-preset";
      btn.textContent = "+ Add Preset";
    }
  });
}

/* =========================================================
   3. Custom Builder Controls & Unit Selection
   ========================================================= */
function setupCustomBuilderControls() {
  const triggerSelect = document.getElementById("builder-trigger");
  const groupHealthPct = document.getElementById("group-health-pct");
  const groupTimerSec = document.getElementById("group-timer-sec");
  const groupCategory = document.getElementById("group-target-category");
  const unitSelectorWrapper = document.getElementById("unit-selector-wrapper");
  const categorySelect = document.getElementById("builder-category-select");

  triggerSelect.addEventListener("change", () => {
    const trig = triggerSelect.value;
    groupHealthPct.style.display = (trig === "health_low") ? "block" : "none";
    groupTimerSec.style.display = (trig === "match_timer") ? "block" : "none";
    groupCategory.style.display = (trig === "match_timer") ? "none" : "block";
    unitSelectorWrapper.style.display = (trig === "match_timer") ? "none" : (categorySelect.value === "selected_unit" ? "block" : "none");
    
    // Update default template title and message if user hasn't heavily customized
    if (trig === "match_timer") {
      document.getElementById("builder-title").value = "⏱️ MATCH TIME UPDATE";
      document.getElementById("builder-text").value = "Match has reached 15 minutes. Prepare strategic forces!";
      document.getElementById("builder-theme").value = "intel";
    } else if (trig === "health_low") {
      document.getElementById("builder-title").value = "🚨 UNIT IN CRITICAL DANGER";
      document.getElementById("builder-text").value = "{UnitName} is under heavy attack! Health below 35%.";
      document.getElementById("builder-theme").value = "danger";
      document.getElementById("builder-sound").value = "UI_Alarm";
    } else if (trig === "unit_killed") {
      document.getElementById("builder-title").value = "💥 PRIORITY TARGET DESTROYED";
      document.getElementById("builder-text").value = "{UnitName} has been eliminated from the battlefield.";
      document.getElementById("builder-theme").value = "tactical";
    } else {
      document.getElementById("builder-title").value = "⚠️ EXPERIMENTAL DETECTED";
      document.getElementById("builder-text").value = "A hostile {UnitName} has completed construction! Pinpoint to engage.";
      document.getElementById("builder-theme").value = "danger";
    }

    updateLivePreview();
  });

  categorySelect.addEventListener("change", () => {
    const isCustomUnit = categorySelect.value === "selected_unit";
    unitSelectorWrapper.style.display = isCustomUnit ? "block" : "none";
    updateLivePreview();
  });

  // Search input
  const searchInput = document.getElementById("unit-search");
  const clearSearchBtn = document.getElementById("clear-unit-search");

  searchInput.addEventListener("input", () => {
    filterState.search = searchInput.value.trim().toLowerCase();
    clearSearchBtn.style.display = filterState.search ? "inline-block" : "none";
    applyUnitFilters();
  });

  clearSearchBtn.addEventListener("click", () => {
    searchInput.value = "";
    filterState.search = "";
    clearSearchBtn.style.display = "none";
    applyUnitFilters();
  });

  // Faction chips
  document.querySelectorAll("#unit-faction-chips .chip").forEach(chip => {
    chip.addEventListener("click", () => {
      document.querySelectorAll("#unit-faction-chips .chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      filterState.faction = chip.getAttribute("data-val");
      applyUnitFilters();
    });
  });

  // Tech chips
  document.querySelectorAll("#unit-tech-chips .chip").forEach(chip => {
    chip.addEventListener("click", () => {
      document.querySelectorAll("#unit-tech-chips .chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      filterState.tech = chip.getAttribute("data-val");
      applyUnitFilters();
    });
  });

  // Deselect picked unit
  document.getElementById("btn-clear-picked-unit").addEventListener("click", () => {
    selectedTargetUnit = null;
    document.getElementById("selected-unit-preview").style.display = "none";
    document.querySelectorAll(".unit-card.selected").forEach(c => c.classList.remove("selected"));
    updateLivePreview();
  });

  // Add Custom Popup Button
  document.getElementById("btn-add-custom-popup").addEventListener("click", addCustomPopupRule);
}

function applyUnitFilters() {
  filteredUnits = allUnits.filter(u => {
    if (filterState.faction !== "ALL" && u.faction.toLowerCase() !== filterState.faction.toLowerCase()) {
      return false;
    }
    if (filterState.tech !== "ALL" && u.tech !== filterState.tech) {
      return false;
    }
    if (filterState.search) {
      const q = filterState.search;
      const match = u.id.toLowerCase().includes(q) ||
                    (u.name && u.name.toLowerCase().includes(q)) ||
                    (u.unitName && u.unitName.toLowerCase().includes(q)) ||
                    (u.desc && u.desc.toLowerCase().includes(q));
      if (!match) return false;
    }
    return true;
  });

  renderUnitGrid();
}

function renderUnitGrid() {
  const grid = document.getElementById("builder-unit-grid");
  grid.innerHTML = "";

  if (filteredUnits.length === 0) {
    grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: var(--text-dim); padding: 20px;">No units match filters.</div>';
    return;
  }

  const subset = filteredUnits.slice(0, 48); // Render 48 at a time for high speed
  subset.forEach(u => {
    const card = document.createElement("div");
    card.className = "unit-card";
    if (selectedTargetUnit && selectedTargetUnit.id.toLowerCase() === u.id.toLowerCase()) {
      card.classList.add("selected");
    }

    let techClass = "t1";
    if (u.tech === "T2") techClass = "t2";
    else if (u.tech === "T3") techClass = "t3";
    else if (u.tech === "EXP") techClass = "exp";

    card.innerHTML = `
      <span class="unit-tech-badge ${techClass}">${u.tech}</span>
      <div class="unit-icon-wrapper">
        <div class="icon-${u.id}"></div>
      </div>
      <div class="unit-info">
        <div class="unit-name" title="${u.name}">${u.unitName || u.name}</div>
        <div class="unit-id">${u.id.toUpperCase()}</div>
      </div>
    `;

    card.addEventListener("click", () => {
      document.querySelectorAll(".unit-card.selected").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      pickTargetUnit(u);
    });

    grid.appendChild(card);
  });
}

function pickTargetUnit(unit) {
  selectedTargetUnit = unit;
  const preview = document.getElementById("selected-unit-preview");
  const nameEl = document.getElementById("preview-unit-name");
  const metaEl = document.getElementById("preview-unit-meta");
  const iconEl = document.getElementById("preview-unit-icon");

  preview.style.display = "flex";
  nameEl.textContent = `${unit.unitName || unit.name} (${unit.id.toUpperCase()})`;
  metaEl.textContent = `${unit.faction} ${unit.tech} ${unit.type} • HP: ${unit.hp.toLocaleString()}`;
  iconEl.className = `icon-${unit.id}`;

  // Automatically update Title & Text
  const trig = document.getElementById("builder-trigger").value;
  const cleanName = unit.unitName || unit.desc || unit.id.toUpperCase();
  if (trig === "unit_built") {
    document.getElementById("builder-title").value = `⚠️ ${cleanName.toUpperCase()} DETECTED`;
    document.getElementById("builder-text").value = `Hostile ${cleanName} has entered the battlefield! Pinpoint to engage.`;
  } else if (trig === "unit_killed") {
    document.getElementById("builder-title").value = `💥 ${cleanName.toUpperCase()} ELIMINATED`;
    document.getElementById("builder-text").value = `${cleanName} has been destroyed in combat.`;
  }

  updateLivePreview();
}

/* =========================================================
   4. Live In-Game HUD Preview
   ========================================================= */
function setupLivePreviewListeners() {
  const inputs = [
    "builder-title",
    "builder-text",
    "builder-theme",
    "chk-pinpoint",
    "chk-dismiss"
  ];

  inputs.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", updateLivePreview);
      el.addEventListener("change", updateLivePreview);
    }
  });

  // Clicking pinpoint in live preview gives interactive feedback
  const previewPinpointBtn = document.getElementById("preview-btn-pinpoint");
  previewPinpointBtn.addEventListener("click", () => {
    previewPinpointBtn.style.transform = "scale(0.95)";
    setTimeout(() => {
      previewPinpointBtn.style.transform = "none";
      showToast("🎯 Pinpoint clicked! (In-game: Smoothly pans camera to the unit location)", "info");
    }, 120);
  });

  const previewDismissBtn = document.getElementById("preview-btn-dismiss");
  previewDismissBtn.addEventListener("click", () => {
    const card = document.getElementById("live-in-game-card");
    card.style.opacity = "0.3";
    setTimeout(() => {
      card.style.opacity = "1";
      showToast("✕ Dismiss clicked! (In-game: Closes the notification card)", "info");
    }, 300);
  });
}

function updateLivePreview() {
  const title = document.getElementById("builder-title").value || "TACTICAL ALERT";
  let text = document.getElementById("builder-text").value || "Notification body text.";
  const theme = document.getElementById("builder-theme").value || "danger";
  const hasPinpoint = document.getElementById("chk-pinpoint").checked;
  const hasDismiss = document.getElementById("chk-dismiss").checked;

  // Substitute {UnitName}
  const sampleUnitName = selectedTargetUnit ? (selectedTargetUnit.unitName || selectedTargetUnit.desc || selectedTargetUnit.id.toUpperCase()) : "Colossus";
  text = text.replace("{UnitName}", sampleUnitName);

  const card = document.getElementById("live-in-game-card");
  card.className = `in-game-card theme-${theme}`;

  document.getElementById("preview-card-title").textContent = title;
  document.getElementById("preview-card-message").textContent = text;

  const btnPinpoint = document.getElementById("preview-btn-pinpoint");
  const btnDismiss = document.getElementById("preview-btn-dismiss");

  btnPinpoint.style.display = hasPinpoint ? "inline-flex" : "none";
  btnDismiss.style.display = hasDismiss ? "inline-flex" : "none";
}

/* =========================================================
   5. Active Rules & Custom Rule Creation
   ========================================================= */
function addCustomPopupRule() {
  const trigger = document.getElementById("builder-trigger").value;
  const title = document.getElementById("builder-title").value.trim() || "TACTICAL ALERT";
  const text = document.getElementById("builder-text").value.trim() || "Event occurred!";
  const theme = document.getElementById("builder-theme").value;
  const sound = document.getElementById("builder-sound").value;
  const duration = parseInt(document.getElementById("builder-duration").value, 10);
  const hasPinpoint = document.getElementById("chk-pinpoint").checked;
  const hasPing = document.getElementById("chk-ping").checked;
  const hasDismiss = document.getElementById("chk-dismiss").checked;
  const catChoice = document.getElementById("builder-category-select").value;

  let unitIds = [];
  let categoryLua = "";
  let nameLabel = title;

  if (trigger === "match_timer") {
    const timerMin = parseInt(document.getElementById("builder-timer-min").value, 10) || 15;
    const timerSec = timerMin * 60;
    nameLabel = `⏱️ ${timerMin}m Timer Milestone`;
    const ruleId = `custom_timer_${Date.now()}`;
    activeRules.set(ruleId, {
      id: ruleId,
      name: nameLabel,
      icon: "⏱️",
      trigger: "match_timer",
      timerSeconds: timerSec,
      title: title,
      text: text,
      theme: theme,
      sound: sound,
      hasPinpoint: false,
      hasPing: false,
      hasDismiss: hasDismiss,
      duration: duration,
      unitIds: [],
      categoryLua: ""
    });
    renderActiveRules();
    showToast(`Added: ${nameLabel}`, "success");
    return;
  }

  if (catChoice === "selected_unit") {
    if (!selectedTargetUnit) {
      showToast("Please pick a unit from the mini-grid or select a category!", "error");
      return;
    }
    unitIds = [selectedTargetUnit.id.toLowerCase()];
    nameLabel = `${selectedTargetUnit.unitName || selectedTargetUnit.name} (${selectedTargetUnit.id.toUpperCase()})`;
  } else {
    categoryLua = catChoice;
    nameLabel = `${catChoice.replace('categories.', '')} Alert`;
  }

  const healthPct = (trigger === "health_low") ? parseInt(document.getElementById("builder-health-pct").value, 10) : 35;
  const ruleId = `custom_rule_${Date.now()}`;

  activeRules.set(ruleId, {
    id: ruleId,
    name: nameLabel,
    icon: trigger === "health_low" ? "🚨" : (trigger === "unit_killed" ? "💥" : "🎯"),
    trigger: trigger,
    categoryLua: categoryLua,
    unitIds: unitIds,
    healthPct: healthPct,
    title: title,
    text: text,
    theme: theme,
    sound: sound,
    hasPinpoint: hasPinpoint,
    hasPing: hasPing,
    hasDismiss: hasDismiss,
    duration: duration,
    isPreset: false
  });

  renderActiveRules();
  showToast(`Added custom popup: ${nameLabel}`, "success");
}

function renderActiveRules() {
  const container = document.getElementById("active-rules-container");
  const emptyState = document.getElementById("rules-empty-state");
  const countBadge = document.getElementById("total-popups-count");
  const sidebarCountBadge = document.getElementById("active-badge-count");
  const btnCount = document.getElementById("btn-popups-count");

  const count = activeRules.size;
  countBadge.textContent = count;
  sidebarCountBadge.textContent = count;
  btnCount.textContent = count;

  ForgeStore.setPopups(activeRules);
  ForgeStore.syncNavBadges();

  if (count === 0) {
    emptyState.style.display = "block";
    container.innerHTML = "";
    container.appendChild(emptyState);
    return;
  }

  emptyState.style.display = "none";
  container.innerHTML = "";

  activeRules.forEach((rule, ruleId) => {
    const item = document.createElement("div");
    item.className = "active-popup-item";

    const triggerLabel = rule.trigger === "unit_built" ? "Spawn"
                       : rule.trigger === "unit_killed" ? "Kill"
                       : rule.trigger === "health_low" ? `< ${rule.healthPct}% HP`
                       : `${Math.round((rule.timerSeconds || 0) / 60)}m Timer`;

    item.innerHTML = `
      <div class="active-popup-top">
        <div class="active-popup-title">${rule.icon || "📢"} ${rule.name}</div>
        <button class="btn btn-sm btn-ghost btn-del-rule" data-rule-id="${ruleId}" title="Delete rule">✕</button>
      </div>
      <div class="active-popup-badges">
        <span class="active-popup-badge trigger">${triggerLabel}</span>
        <span class="active-popup-badge theme">${rule.theme.toUpperCase()}</span>
        <span class="active-popup-badge sound">${rule.sound.replace('UI_', '')}</span>
        ${rule.hasPinpoint ? '<span class="active-popup-badge" style="background: rgba(0,210,255,0.1); color:#00d2ff;">🎯 PINPOINT</span>' : ''}
      </div>
      <div style="font-size: 0.72rem; color: var(--text-muted); font-style: italic; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
        "${rule.title}: ${rule.text}"
      </div>
    `;

    item.querySelector(".btn-del-rule").addEventListener("click", () => {
      activeRules.delete(ruleId);
      renderActiveRules();
      updatePresetsGridUI();
      showToast(`Removed rule: ${rule.name}`, "info");
    });

    container.appendChild(item);
  });
}

/* =========================================================
   6. Export Mod Generation
   ========================================================= */
function setupExport() {
  const btnExport = document.getElementById("btn-export-popups");
  const feedback = document.getElementById("export-feedback");

  btnExport.addEventListener("click", async () => {
    if (activeRules.size === 0) {
      showToast("Please add at least one popup rule before exporting!", "error");
      return;
    }

    const modName = document.getElementById("input-mod-name").value.trim() || "Tactical Event Popups";
    const author = document.getElementById("input-author").value.trim() || "User";
    const version = parseInt(document.getElementById("input-version").value, 10) || 1;
    const targetMode = document.querySelector('input[name="target-scope"]:checked').value;
    const playerName = document.getElementById("input-player-name").value.trim();

    if (targetMode === "player" && !playerName) {
      showToast("Please specify the target player nickname!", "error");
      document.getElementById("input-player-name").focus();
      return;
    }

    btnExport.disabled = true;
    btnExport.textContent = "⏳ Packaging Mod...";

    const payload = {
      modName,
      author,
      version,
      targetMode,
      playerName,
      rules: Array.from(activeRules.values())
    };

    try {
      const res = await fetch("/api/export-popups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (data.success) {
        feedback.style.display = "block";
        feedback.className = "feedback-card success";
        feedback.innerHTML = `
          <div style="font-size: 1rem; font-weight: 700; color: #10b981; margin-bottom: 6px;">
            🎉 Mod Exported Successfully!
          </div>
          <div style="font-size: 0.78rem; line-height: 1.5; color: var(--text-muted);">
            <div><strong>Mod:</strong> ${data.modName} (v${version})</div>
            <div><strong>Target Scope:</strong> ${data.targetMode === "player" ? `Specific Player (${data.playerName})` : "Global (All Players)"}</div>
            <div><strong>Active Rules:</strong> ${data.rulesCount}</div>
            <div style="margin-top: 6px; word-break: break-all;"><strong>Installed to:</strong> <code>${data.targetModDir}</code></div>
          </div>
          <div style="margin-top: 10px; display: flex; gap: 8px;">
            <button class="btn btn-sm btn-outline" id="btn-open-exported-folder">📁 Open Folder</button>
            <a href="/exports/${data.folderName}.zip" download class="btn btn-sm btn-secondary">📦 Download .zip</a>
          </div>
        `;

        document.getElementById("btn-open-exported-folder").addEventListener("click", async () => {
          await fetch("/api/open-folder", { method: "POST" });
        });

        showToast(`Exported "${data.modName}" to Supreme Commander mods!`, "success");
      } else {
        feedback.style.display = "block";
        feedback.className = "feedback-card error";
        feedback.innerHTML = `
          <div style="font-weight: 700; color: #ef4444; margin-bottom: 4px;">Export Failed</div>
          <div style="font-size: 0.78rem;">${data.error || "Unknown error occurred"}</div>
        `;
        showToast("Export failed: " + (data.error || "Unknown error"), "error");
      }
    } catch (err) {
      console.error(err);
      feedback.style.display = "block";
      feedback.className = "feedback-card error";
      feedback.innerHTML = `
        <div style="font-weight: 700; color: #ef4444; margin-bottom: 4px;">Export Error</div>
        <div style="font-size: 0.78rem;">${err.message}</div>
      `;
      showToast("Error packaging mod: " + err.message, "error");
    } finally {
      btnExport.disabled = false;
      btnExport.textContent = `🚀 Pack & Export Popups Mod (${activeRules.size} rules)`;
    }
  });
}

/* =========================================================
   7. Notification Toast Helper
   ========================================================= */
function showToast(message, type = "info") {
  const toast = document.getElementById("toast");
  if (!toast) return;

  toast.textContent = message;
  toast.className = `toast show ${type}`;

  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(() => {
    toast.className = "toast";
  }, 3500);
}
