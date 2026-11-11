// FAF Mod Forge - Interactive Unit Inspector & Stat Editor

let allUnits = [];
let unitMap = new Map();
let filteredUnits = [];
let activeUnitId = null;

// unitConfigs: unitId -> { hpMult, regenMult, shieldMult, shieldRegenMult, massDiscount, energyDiscount, buildTimeDiscount, buildRateMult, prodMult, speedMult, turnRateMult, visionMult, radarMult, damageMult, rangeMult, rofMult, aoeMult, muzzleVelMult }
const unitConfigs = new Map();

const DEFAULT_CONFIG = {
  hpMult: 2.0,
  regenMult: 1.0,
  shieldMult: 1.0,
  shieldRegenMult: 1.0,
  massDiscount: 0,
  energyDiscount: 0,
  buildTimeDiscount: 0,
  buildRateMult: 1.0,
  prodMult: 1.0,
  speedMult: 1.0,
  turnRateMult: 1.0,
  visionMult: 1.0,
  radarMult: 1.0,
  damageMult: 1.0,
  rangeMult: 1.0,
  rofMult: 1.0,
  aoeMult: 1.0,
  muzzleVelMult: 1.0
};

const PRESETS = {
  vanilla: {
    hpMult: 1.0, regenMult: 1.0, shieldMult: 1.0, shieldRegenMult: 1.0,
    massDiscount: 0, energyDiscount: 0, buildTimeDiscount: 0, buildRateMult: 1.0, prodMult: 1.0,
    speedMult: 1.0, turnRateMult: 1.0, visionMult: 1.0, radarMult: 1.0,
    damageMult: 1.0, rangeMult: 1.0, rofMult: 1.0, aoeMult: 1.0, muzzleVelMult: 1.0
  },
  buff: {
    hpMult: 2.0, regenMult: 2.0, shieldMult: 2.0, shieldRegenMult: 2.0,
    massDiscount: 50, energyDiscount: 50, buildTimeDiscount: 30, buildRateMult: 2.0, prodMult: 2.0,
    speedMult: 1.3, turnRateMult: 1.3, visionMult: 1.3, radarMult: 1.3,
    damageMult: 1.5, rangeMult: 1.2, rofMult: 1.3, aoeMult: 1.2, muzzleVelMult: 1.2
  },
  god: {
    hpMult: 10.0, regenMult: 5.0, shieldMult: 5.0, shieldRegenMult: 5.0,
    massDiscount: 80, energyDiscount: 80, buildTimeDiscount: 70, buildRateMult: 5.0, prodMult: 5.0,
    speedMult: 2.0, turnRateMult: 2.0, visionMult: 2.0, radarMult: 2.0,
    damageMult: 5.0, rangeMult: 2.5, rofMult: 2.5, aoeMult: 2.0, muzzleVelMult: 2.0
  },
  sniper: {
    hpMult: 1.5, regenMult: 1.0, shieldMult: 1.0, shieldRegenMult: 1.0,
    massDiscount: 20, energyDiscount: 20, buildTimeDiscount: 0, buildRateMult: 1.0, prodMult: 1.0,
    speedMult: 1.1, turnRateMult: 1.2, visionMult: 2.5, radarMult: 2.0,
    damageMult: 3.0, rangeMult: 3.0, rofMult: 1.0, aoeMult: 1.5, muzzleVelMult: 2.5
  },
  speed: {
    hpMult: 1.5, regenMult: 1.5, shieldMult: 1.0, shieldRegenMult: 1.0,
    massDiscount: 40, energyDiscount: 40, buildTimeDiscount: 50, buildRateMult: 3.0, prodMult: 2.0,
    speedMult: 3.0, turnRateMult: 2.5, visionMult: 1.5, radarMult: 1.5,
    damageMult: 1.3, rangeMult: 1.1, rofMult: 3.0, aoeMult: 1.0, muzzleVelMult: 2.0
  },
  swarm: {
    hpMult: 1.5, regenMult: 1.0, shieldMult: 1.0, shieldRegenMult: 1.0,
    massDiscount: 80, energyDiscount: 80, buildTimeDiscount: 80, buildRateMult: 3.0, prodMult: 2.0,
    speedMult: 1.8, turnRateMult: 1.5, visionMult: 1.2, radarMult: 1.2,
    damageMult: 1.2, rangeMult: 1.0, rofMult: 1.5, aoeMult: 1.0, muzzleVelMult: 1.2
  }
};

const currentFilters = {
  faction: 'ALL',
  tech: 'ALL',
  type: 'ALL',
  search: ''
};

// DOM Elements - Main Layout
const unitGrid = document.getElementById('unit-grid');
const totalUnitsCount = document.getElementById('total-units-count');
const selectedUnitsCount = document.getElementById('selected-units-count');
const tabModCount = document.getElementById('tab-mod-count');
const filteredCountText = document.getElementById('filtered-count-text');
const filterSearch = document.getElementById('filter-search');
const clearSearchBtn = document.getElementById('clear-search');

// Tabs
const tabBtnInspector = document.getElementById('tab-btn-inspector');
const tabBtnSettings = document.getElementById('tab-btn-settings');
const tabInspector = document.getElementById('tab-inspector');
const tabSettings = document.getElementById('tab-settings');

// Inspector DOM
const inspectorEmpty = document.getElementById('inspector-empty');
const inspectorBody = document.getElementById('inspector-body');
const inspectorIcon = document.getElementById('inspector-icon');
const inspectorBadgeFaction = document.getElementById('inspector-badge-faction');
const inspectorBadgeTech = document.getElementById('inspector-badge-tech');
const inspectorBadgeType = document.getElementById('inspector-badge-type');
const inspectorName = document.getElementById('inspector-name');
const inspectorId = document.getElementById('inspector-id');
const inspectorDesc = document.getElementById('inspector-desc');
const btnToggleInclude = document.getElementById('btn-toggle-include');

// Inspector Sliders & Calculations - Survivability
const sliderUnitHp = document.getElementById('slider-unit-hp');
const dispUnitHp = document.getElementById('disp-unit-hp');
const calcHp = document.getElementById('calc-hp');

const groupUnitRegen = document.getElementById('group-unit-regen');
const sliderUnitRegen = document.getElementById('slider-unit-regen');
const dispUnitRegen = document.getElementById('disp-unit-regen');
const calcRegen = document.getElementById('calc-regen');

const groupUnitShield = document.getElementById('group-unit-shield');
const sliderUnitShield = document.getElementById('slider-unit-shield');
const dispUnitShield = document.getElementById('disp-unit-shield');
const calcShield = document.getElementById('calc-shield');

const groupUnitShieldRegen = document.getElementById('group-unit-shield-regen');
const sliderUnitShieldRegen = document.getElementById('slider-unit-shield-regen');
const dispUnitShieldRegen = document.getElementById('disp-unit-shield-regen');
const calcShieldRegen = document.getElementById('calc-shield-regen');

// Inspector Sliders & Calculations - Weapons
const sectionWeapons = document.getElementById('section-weapons');
const groupUnitDamage = document.getElementById('group-unit-damage');
const sliderUnitDamage = document.getElementById('slider-unit-damage');
const dispUnitDamage = document.getElementById('disp-unit-damage');
const calcDamage = document.getElementById('calc-damage');
const dispWeaponName = document.getElementById('disp-weapon-name');

const groupUnitRange = document.getElementById('group-unit-range');
const sliderUnitRange = document.getElementById('slider-unit-range');
const dispUnitRange = document.getElementById('disp-unit-range');
const calcRange = document.getElementById('calc-range');

const groupUnitRof = document.getElementById('group-unit-rof');
const sliderUnitRof = document.getElementById('slider-unit-rof');
const dispUnitRof = document.getElementById('disp-unit-rof');
const calcRof = document.getElementById('calc-rof');

const groupUnitAoe = document.getElementById('group-unit-aoe');
const sliderUnitAoe = document.getElementById('slider-unit-aoe');
const dispUnitAoe = document.getElementById('disp-unit-aoe');
const calcAoe = document.getElementById('calc-aoe');

const groupUnitMuzzleVel = document.getElementById('group-unit-muzzle-vel');
const sliderUnitMuzzleVel = document.getElementById('slider-unit-muzzle-vel');
const dispUnitMuzzleVel = document.getElementById('disp-unit-muzzle-vel');
const calcMuzzleVel = document.getElementById('calc-muzzle-vel');

// Inspector Sliders & Calculations - Economy
const sliderUnitMass = document.getElementById('slider-unit-mass');
const dispUnitMass = document.getElementById('disp-unit-mass');
const calcMass = document.getElementById('calc-mass');

const sliderUnitEnergy = document.getElementById('slider-unit-energy');
const dispUnitEnergy = document.getElementById('disp-unit-energy');
const calcEnergy = document.getElementById('calc-energy');

const sliderUnitBuildtime = document.getElementById('slider-unit-buildtime');
const dispUnitBuildtime = document.getElementById('disp-unit-buildtime');
const calcBuildtime = document.getElementById('calc-buildtime');

const groupUnitBuildrate = document.getElementById('group-unit-buildrate');
const sliderUnitBuildrate = document.getElementById('slider-unit-buildrate');
const dispUnitBuildrate = document.getElementById('disp-unit-buildrate');
const calcBuildrate = document.getElementById('calc-buildrate');

const groupUnitProd = document.getElementById('group-unit-prod');
const sliderUnitProd = document.getElementById('slider-unit-prod');
const dispUnitProd = document.getElementById('disp-unit-prod');
const calcProd = document.getElementById('calc-prod');

// Inspector Sliders & Calculations - Mobility & Sensors
const groupUnitSpeed = document.getElementById('group-unit-speed');
const sliderUnitSpeed = document.getElementById('slider-unit-speed');
const dispUnitSpeed = document.getElementById('disp-unit-speed');
const calcSpeed = document.getElementById('calc-speed');

const groupUnitTurnrate = document.getElementById('group-unit-turnrate');
const sliderUnitTurnrate = document.getElementById('slider-unit-turnrate');
const dispUnitTurnrate = document.getElementById('disp-unit-turnrate');
const calcTurnrate = document.getElementById('calc-turnrate');

const groupUnitVision = document.getElementById('group-unit-vision');
const sliderUnitVision = document.getElementById('slider-unit-vision');
const dispUnitVision = document.getElementById('disp-unit-vision');
const calcVision = document.getElementById('calc-vision');

const groupUnitRadar = document.getElementById('group-unit-radar');
const sliderUnitRadar = document.getElementById('slider-unit-radar');
const dispUnitRadar = document.getElementById('disp-unit-radar');
const calcRadar = document.getElementById('calc-radar');

// Inspector Actions
const btnCopyStats = document.getElementById('btn-copy-stats');
const btnResetUnit = document.getElementById('btn-reset-unit');
const btnQuickExport = document.getElementById('btn-quick-export');

// Scope & Mod Metadata
const cardScopePlayer = document.getElementById('card-scope-player');
const cardScopeGlobal = document.getElementById('card-scope-global');
const groupPlayerName = document.getElementById('group-player-name');
const inputPlayerName = document.getElementById('input-player-name');
const inputModName = document.getElementById('input-mod-name');
const inputAuthor = document.getElementById('input-author');
const inputVersion = document.getElementById('input-version');

// Action Buttons
const btnSelectFiltered = document.getElementById('btn-select-filtered');
const btnDeselectFiltered = document.getElementById('btn-deselect-filtered');
const btnClearSelection = document.getElementById('btn-clear-selection');
const btnExport = document.getElementById('btn-export');
const btnOpenFolder = document.getElementById('btn-open-folder');
const exportFeedback = document.getElementById('export-feedback');
const toastEl = document.getElementById('toast');

// --- Initialization ---
async function init() {
  setupEventListeners();
  loadSavedMetadata();

  const savedBuffs = ForgeStore.getBuffs();
  if (savedBuffs && typeof savedBuffs === 'object') {
    Object.entries(savedBuffs).forEach(([uid, cfg]) => {
      unitConfigs.set(uid, cfg);
    });
  }

  await loadUnits();
  updateSelectionCounters();
  ForgeStore.syncNavBadges();
}

function loadSavedMetadata() {
  const meta = ForgeStore.getModMeta();
  if (meta.modName && meta.modName !== "FAF Master Overhaul") inputModName.value = meta.modName;
  if (meta.author) inputAuthor.value = meta.author;
  if (meta.version) inputVersion.value = meta.version;
  if (meta.playerName) inputPlayerName.value = meta.playerName;
  if (meta.targetMode === 'global') {
    cardScopePlayer.classList.remove('active');
    cardScopeGlobal.classList.add('active');
    const radio = document.querySelector('input[name="target-scope"][value="global"]');
    if (radio) radio.checked = true;
    groupPlayerName.style.display = 'none';
  } else {
    cardScopePlayer.classList.add('active');
    cardScopeGlobal.classList.remove('active');
    const radio = document.querySelector('input[name="target-scope"][value="player"]');
    if (radio) radio.checked = true;
    groupPlayerName.style.display = 'block';
  }
}

function saveCurrentMetadata() {
  const targetMode = document.querySelector('input[name="target-scope"]:checked')?.value || 'player';
  ForgeStore.setModMeta({
    author: inputAuthor.value.trim(),
    version: parseInt(inputVersion.value, 10) || 1,
    targetMode,
    playerName: inputPlayerName.value.trim()
  });
}

async function loadUnits() {
  try {
    const res = await fetch('/api/units');
    allUnits = await res.json();
    unitMap.clear();
    allUnits.forEach(u => unitMap.set(u.id, u));
    totalUnitsCount.textContent = allUnits.length;
    applyFilters();

    // Inspect first unit as preview without auto-adding it to mod
    if (allUnits.length > 0) {
      inspectUnit(allUnits[0].id, false);
    }
  } catch (err) {
    showToast('Failed to load unit database: ' + err.message);
  }
}

// --- Filtering Logic ---
function applyFilters() {
  const searchLower = currentFilters.search.trim().toLowerCase();

  filteredUnits = allUnits.filter(u => {
    // Faction
    if (currentFilters.faction !== 'ALL') {
      if ((u.faction || '').toUpperCase() !== currentFilters.faction.toUpperCase()) return false;
    }

    // Tech
    if (currentFilters.tech !== 'ALL') {
      if ((u.tech || '').toUpperCase() !== currentFilters.tech.toUpperCase()) return false;
    }

    // Type
    if (currentFilters.type !== 'ALL') {
      if ((u.type || '').toUpperCase() !== currentFilters.type.toUpperCase()) return false;
    }

    // Search query
    if (searchLower) {
      const matchId = u.id.toLowerCase().includes(searchLower);
      const matchName = (u.name || '').toLowerCase().includes(searchLower);
      const matchDesc = (u.desc || '').toLowerCase().includes(searchLower);
      const matchFaction = (u.faction || '').toLowerCase().includes(searchLower);
      if (!matchId && !matchName && !matchDesc && !matchFaction) return false;
    }

    return true;
  });

  filteredCountText.textContent = `Showing ${filteredUnits.length} of ${allUnits.length} units`;
  renderGrid();
}

function renderGrid() {
  unitGrid.innerHTML = '';

  if (filteredUnits.length === 0) {
    unitGrid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: var(--text-dim); padding: 40px;">No units match your filter criteria.</div>';
    return;
  }

  const fragment = document.createDocumentFragment();

  filteredUnits.forEach(u => {
    const card = document.createElement('div');
    const isIncluded = unitConfigs.has(u.id);
    const isInspecting = (u.id === activeUnitId);
    const hasCustomMods = isIncluded && isModified(unitConfigs.get(u.id));

    let cardClasses = ['unit-card'];
    if (isIncluded) cardClasses.push('selected');
    if (isInspecting) cardClasses.push('inspecting');
    if (hasCustomMods) cardClasses.push('customized');

    card.className = cardClasses.join(' ');
    card.dataset.id = u.id;

    const factionClass = (u.faction || '').toLowerCase();
    const techClass = (u.tech || '').toLowerCase();

    card.innerHTML = `
      <div class="faction-bar ${factionClass}"></div>
      <span class="unit-tech-badge ${techClass}">${u.tech}</span>
      <div class="card-checkbox ${isIncluded ? 'checked' : ''}" title="${isIncluded ? 'Click to remove from mod' : 'Click to add to mod'}">✓</div>
      <div class="mod-badge">⚡ MOD</div>
      <div class="unit-icon-wrapper">
        <div class="icon-${u.id}"></div>
      </div>
      <div class="unit-info">
        <div class="unit-id">${u.id}</div>
        <div class="unit-name" title="${u.name}">${u.name}</div>
        <div class="unit-stats-mini">
          <span title="Health">🛡️ ${u.hp || 0}</span>
          <span title="Mass Cost">💰 ${u.mass || 0}</span>
        </div>
      </div>
    `;

    // Click on Checkbox: Toggles inclusion directly
    const checkbox = card.querySelector('.card-checkbox');
    checkbox.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleUnitInclusion(u.id);
    });

    // Click on Card Body: Inspects unit (and adds if not in mod)
    card.addEventListener('click', () => {
      if (activeUnitId === u.id && unitConfigs.has(u.id)) {
        // Clicking an already active and included card toggles it off
        toggleUnitInclusion(u.id);
      } else {
        inspectUnit(u.id, true);
      }
    });

    fragment.appendChild(card);
  });

  unitGrid.appendChild(fragment);
}

// Toggle a unit in or out of the mod
function toggleUnitInclusion(unitId) {
  if (unitConfigs.has(unitId)) {
    unitConfigs.delete(unitId);
    showToast(`Removed ${unitId} from mod.`);
  } else {
    unitConfigs.set(unitId, { ...DEFAULT_CONFIG });
    showToast(`Added ${unitId} to mod.`);
  }

  updateSelectionCounters();
  updateCardAppearance(unitId);

  // If this unit is currently inspected, update inspector button
  if (activeUnitId === unitId) {
    updateInspectorMembershipButton();
  }
}

// Update single card's classes without re-rendering whole grid
function updateCardAppearance(unitId) {
  const card = document.querySelector(`.unit-card[data-id="${unitId}"]`);
  if (!card) return;

  const isIncluded = unitConfigs.has(unitId);
  const isInspecting = (unitId === activeUnitId);
  const cfg = unitConfigs.get(unitId);
  const hasCustomMods = isIncluded && isModified(cfg);

  const checkbox = card.querySelector('.card-checkbox');
  if (checkbox) {
    if (isIncluded) {
      checkbox.classList.add('checked');
      checkbox.title = 'Click to remove from mod';
    } else {
      checkbox.classList.remove('checked');
      checkbox.title = 'Click to add to mod';
    }
  }

  if (isIncluded) {
    card.classList.add('selected');
  } else {
    card.classList.remove('selected');
  }

  if (isInspecting) {
    card.classList.add('inspecting');
  } else {
    card.classList.remove('inspecting');
  }

  if (hasCustomMods) {
    card.classList.add('customized');
  } else {
    card.classList.remove('customized');
  }
}

function isModified(cfg) {
  if (!cfg) return false;
  return cfg.hpMult !== 1.0 ||
         (cfg.regenMult && cfg.regenMult !== 1.0) ||
         (cfg.shieldMult && cfg.shieldMult !== 1.0) ||
         (cfg.shieldRegenMult && cfg.shieldRegenMult !== 1.0) ||
         cfg.massDiscount > 0 ||
         cfg.energyDiscount > 0 ||
         (cfg.buildTimeDiscount && cfg.buildTimeDiscount > 0) ||
         cfg.buildRateMult !== 1.0 ||
         (cfg.prodMult && cfg.prodMult !== 1.0) ||
         cfg.speedMult !== 1.0 ||
         (cfg.turnRateMult && cfg.turnRateMult !== 1.0) ||
         (cfg.visionMult && cfg.visionMult !== 1.0) ||
         (cfg.radarMult && cfg.radarMult !== 1.0) ||
         cfg.damageMult !== 1.0 ||
         (cfg.rangeMult && cfg.rangeMult !== 1.0) ||
         (cfg.rofMult && cfg.rofMult !== 1.0) ||
         (cfg.aoeMult && cfg.aoeMult !== 1.0) ||
         (cfg.muzzleVelMult && cfg.muzzleVelMult !== 1.0);
}

// --- Inspect Unit & Populate Sliders ---
function inspectUnit(unitId, autoInclude = false) {
  const unit = unitMap.get(unitId);
  if (!unit) return;

  const prevActive = activeUnitId;
  activeUnitId = unitId;

  if (autoInclude && !unitConfigs.has(unitId)) {
    unitConfigs.set(unitId, { ...DEFAULT_CONFIG });
    showToast(`Added ${unit.id} to mod.`);
  }

  updateSelectionCounters();
  switchTab('inspector');

  // Populate Inspector Info
  inspectorEmpty.style.display = 'none';
  inspectorBody.style.display = 'flex';

  inspectorIcon.className = `icon-${unit.id}`;
  inspectorName.textContent = unit.name;
  inspectorId.textContent = unit.id;
  inspectorDesc.textContent = unit.desc || 'No description available.';

  inspectorBadgeFaction.textContent = unit.faction;
  inspectorBadgeTech.textContent = unit.tech;
  inspectorBadgeType.textContent = unit.type;

  updateInspectorMembershipButton();

  // Populate Sliders from current unit config (or default if unincluded)
  const cfg = unitConfigs.get(unitId) || { ...DEFAULT_CONFIG };
  loadSlidersFromConfig(unit, cfg);

  // Update card highlighting in grid
  if (prevActive) updateCardAppearance(prevActive);
  updateCardAppearance(unitId);
}

function updateInspectorMembershipButton() {
  if (!activeUnitId) return;
  const isIncluded = unitConfigs.has(activeUnitId);

  if (isIncluded) {
    btnToggleInclude.className = 'btn btn-block btn-toggle-include included';
    btnToggleInclude.innerHTML = `✓ Included in Mod (Click to Remove)`;
  } else {
    btnToggleInclude.className = 'btn btn-block btn-toggle-include excluded';
    btnToggleInclude.innerHTML = `+ Add This Unit to Mod`;
  }
}

function loadSlidersFromConfig(unit, cfg) {
  // 1. Health (HP)
  sliderUnitHp.value = cfg.hpMult || 1.0;
  dispUnitHp.textContent = (cfg.hpMult || 1.0).toFixed(1) + 'x';
  const newHp = Math.floor((unit.hp || 0) * (cfg.hpMult || 1.0));
  calcHp.textContent = `Base: ${unit.hp || 0} ➔ ${newHp} (${(cfg.hpMult || 1.0).toFixed(1)}x)`;

  // 2. Health Regen
  sliderUnitRegen.value = cfg.regenMult || 1.0;
  dispUnitRegen.textContent = (cfg.regenMult || 1.0).toFixed(1) + 'x';
  const baseRegen = unit.regen || 0;
  const newRegen = Math.floor((baseRegen > 0 ? baseRegen : 5) * (cfg.regenMult || 1.0));
  calcRegen.textContent = baseRegen > 0
    ? `Base: ${baseRegen} ➔ ${newRegen} (${(cfg.regenMult || 1.0).toFixed(1)}x)`
    : `Baseline ➔ +${newRegen} HP/s (${(cfg.regenMult || 1.0).toFixed(1)}x)`;

  // 3. Shield
  if (unit.hasShield) {
    groupUnitShield.style.display = 'flex';
    groupUnitShieldRegen.style.display = 'flex';
    sliderUnitShield.value = cfg.shieldMult || 1.0;
    dispUnitShield.textContent = (cfg.shieldMult || 1.0).toFixed(1) + 'x';
    const newShield = Math.floor((unit.shield || 0) * (cfg.shieldMult || 1.0));
    calcShield.textContent = `Base: ${unit.shield || 0} ➔ ${newShield} (${(cfg.shieldMult || 1.0).toFixed(1)}x)`;

    sliderUnitShieldRegen.value = cfg.shieldRegenMult || 1.0;
    dispUnitShieldRegen.textContent = (cfg.shieldRegenMult || 1.0).toFixed(1) + 'x';
    const newShieldRegen = Math.floor((unit.shieldRegen || 0) * (cfg.shieldRegenMult || 1.0));
    calcShieldRegen.textContent = `Base: ${unit.shieldRegen || 0} ➔ ${newShieldRegen} (${(cfg.shieldRegenMult || 1.0).toFixed(1)}x)`;
  } else {
    groupUnitShield.style.display = 'none';
    groupUnitShieldRegen.style.display = 'none';
  }

  // 4. Weapons
  if (unit.hasWeapons) {
    sectionWeapons.style.display = 'block';
    groupUnitDamage.style.display = 'flex';
    sliderUnitDamage.value = cfg.damageMult || 1.0;
    dispUnitDamage.textContent = (cfg.damageMult || 1.0).toFixed(1) + 'x';
    const newDamage = Math.floor((unit.weaponDamage || 0) * (cfg.damageMult || 1.0));
    calcDamage.textContent = `Base: ${unit.weaponDamage || 0} ➔ ${newDamage} (${(cfg.damageMult || 1.0).toFixed(1)}x)`;
    dispWeaponName.textContent = `${unit.weaponName || 'Primary Weapon'} (Range: ${unit.weaponRange || 'N/A'})`;

    // Range
    groupUnitRange.style.display = 'flex';
    sliderUnitRange.value = cfg.rangeMult || 1.0;
    dispUnitRange.textContent = (cfg.rangeMult || 1.0).toFixed(1) + 'x';
    const newRange = Math.floor((unit.weaponRange || 0) * (cfg.rangeMult || 1.0));
    calcRange.textContent = `Base: ${unit.weaponRange || 0} ➔ ${newRange} (${(cfg.rangeMult || 1.0).toFixed(1)}x)`;

    // Rate of Fire
    groupUnitRof.style.display = 'flex';
    sliderUnitRof.value = cfg.rofMult || 1.0;
    dispUnitRof.textContent = (cfg.rofMult || 1.0).toFixed(1) + 'x';
    const newRof = ((unit.weaponRof || 0) * (cfg.rofMult || 1.0)).toFixed(2);
    calcRof.textContent = `Base: ${unit.weaponRof || 0}/s ➔ ${newRof}/s (${(cfg.rofMult || 1.0).toFixed(1)}x)`;

    // AoE / Splash
    if (unit.weaponAoe && unit.weaponAoe > 0) {
      groupUnitAoe.style.display = 'flex';
      sliderUnitAoe.value = cfg.aoeMult || 1.0;
      dispUnitAoe.textContent = (cfg.aoeMult || 1.0).toFixed(1) + 'x';
      const newAoe = ((unit.weaponAoe || 0) * (cfg.aoeMult || 1.0)).toFixed(1);
      calcAoe.textContent = `Base: ${unit.weaponAoe} ➔ ${newAoe} (${(cfg.aoeMult || 1.0).toFixed(1)}x)`;
    } else {
      groupUnitAoe.style.display = 'none';
    }

    // Muzzle Velocity
    if (unit.weaponMuzzleVel && unit.weaponMuzzleVel > 0) {
      groupUnitMuzzleVel.style.display = 'flex';
      sliderUnitMuzzleVel.value = cfg.muzzleVelMult || 1.0;
      dispUnitMuzzleVel.textContent = (cfg.muzzleVelMult || 1.0).toFixed(1) + 'x';
      const newVel = Math.floor((unit.weaponMuzzleVel || 0) * (cfg.muzzleVelMult || 1.0));
      calcMuzzleVel.textContent = `Base: ${unit.weaponMuzzleVel} ➔ ${newVel} (${(cfg.muzzleVelMult || 1.0).toFixed(1)}x)`;
    } else {
      groupUnitMuzzleVel.style.display = 'none';
    }
  } else {
    sectionWeapons.style.display = 'none';
  }

  // 5. Economy
  sliderUnitMass.value = cfg.massDiscount || 0;
  dispUnitMass.textContent = (cfg.massDiscount || 0) + '%';
  const newMass = Math.floor((unit.mass || 0) * (1 - (cfg.massDiscount || 0) / 100));
  calcMass.textContent = `Base: ${unit.mass || 0} ➔ ${newMass} (-${cfg.massDiscount || 0}%)`;

  sliderUnitEnergy.value = cfg.energyDiscount || 0;
  dispUnitEnergy.textContent = (cfg.energyDiscount || 0) + '%';
  const newEnergy = Math.floor((unit.energy || 0) * (1 - (cfg.energyDiscount || 0) / 100));
  calcEnergy.textContent = `Base: ${unit.energy || 0} ➔ ${newEnergy} (-${cfg.energyDiscount || 0}%)`;

  sliderUnitBuildtime.value = cfg.buildTimeDiscount || 0;
  dispUnitBuildtime.textContent = (cfg.buildTimeDiscount || 0) + '%';
  const newBuildtime = Math.floor((unit.buildTime || 0) * (1 - (cfg.buildTimeDiscount || 0) / 100));
  calcBuildtime.textContent = `Base: ${unit.buildTime || 0} ➔ ${newBuildtime} (-${cfg.buildTimeDiscount || 0}%)`;

  if (unit.buildRate && unit.buildRate > 0) {
    groupUnitBuildrate.style.display = 'flex';
    sliderUnitBuildrate.value = cfg.buildRateMult || 1.0;
    dispUnitBuildrate.textContent = (cfg.buildRateMult || 1.0).toFixed(1) + 'x';
    const newRate = Math.floor((unit.buildRate || 0) * (cfg.buildRateMult || 1.0));
    calcBuildrate.textContent = `Base: ${unit.buildRate || 0} ➔ ${newRate} (${(cfg.buildRateMult || 1.0).toFixed(1)}x)`;
  } else {
    groupUnitBuildrate.style.display = 'none';
  }

  if (unit.hasEcoProd) {
    groupUnitProd.style.display = 'flex';
    sliderUnitProd.value = cfg.prodMult || 1.0;
    dispUnitProd.textContent = (cfg.prodMult || 1.0).toFixed(1) + 'x';
    const newMProd = Math.floor((unit.massProd || 0) * (cfg.prodMult || 1.0));
    const newEProd = Math.floor((unit.energyProd || 0) * (cfg.prodMult || 1.0));
    calcProd.textContent = `Eco: M+${newMProd} | E+${newEProd} (${(cfg.prodMult || 1.0).toFixed(1)}x)`;
  } else {
    groupUnitProd.style.display = 'none';
  }

  // 6. Mobility & Sensors
  if (unit.speed && unit.speed > 0) {
    groupUnitSpeed.style.display = 'flex';
    sliderUnitSpeed.value = cfg.speedMult || 1.0;
    dispUnitSpeed.textContent = (cfg.speedMult || 1.0).toFixed(1) + 'x';
    const newSpeed = ((unit.speed || 0) * (cfg.speedMult || 1.0)).toFixed(2);
    calcSpeed.textContent = `Base: ${unit.speed || 0} ➔ ${newSpeed} (${(cfg.speedMult || 1.0).toFixed(1)}x)`;
  } else {
    groupUnitSpeed.style.display = 'none';
  }

  if (unit.turnRate && unit.turnRate > 0) {
    groupUnitTurnrate.style.display = 'flex';
    sliderUnitTurnrate.value = cfg.turnRateMult || 1.0;
    dispUnitTurnrate.textContent = (cfg.turnRateMult || 1.0).toFixed(1) + 'x';
    const newTurn = Math.floor((unit.turnRate || 0) * (cfg.turnRateMult || 1.0));
    calcTurnrate.textContent = `Base: ${unit.turnRate || 0} ➔ ${newTurn} (${(cfg.turnRateMult || 1.0).toFixed(1)}x)`;
  } else {
    groupUnitTurnrate.style.display = 'none';
  }

  sliderUnitVision.value = cfg.visionMult || 1.0;
  dispUnitVision.textContent = (cfg.visionMult || 1.0).toFixed(1) + 'x';
  const newVision = Math.floor((unit.vision || 0) * (cfg.visionMult || 1.0));
  calcVision.textContent = `Base: ${unit.vision || 0} ➔ ${newVision} (${(cfg.visionMult || 1.0).toFixed(1)}x)`;

  if (unit.hasRadar) {
    groupUnitRadar.style.display = 'flex';
    sliderUnitRadar.value = cfg.radarMult || 1.0;
    dispUnitRadar.textContent = (cfg.radarMult || 1.0).toFixed(1) + 'x';
    const newRadar = Math.floor((unit.radar || 0) * (cfg.radarMult || 1.0));
    calcRadar.textContent = `Base: ${unit.radar || 0} ➔ ${newRadar} (${(cfg.radarMult || 1.0).toFixed(1)}x)`;
  } else {
    groupUnitRadar.style.display = 'none';
  }
}

// Sync slider changes into active unit config
function onSliderChanged() {
  if (!activeUnitId) return;
  const unit = unitMap.get(activeUnitId);
  if (!unit) return;

  const cfg = {
    hpMult: parseFloat(sliderUnitHp.value),
    regenMult: parseFloat(sliderUnitRegen.value),
    shieldMult: parseFloat(sliderUnitShield.value),
    shieldRegenMult: parseFloat(sliderUnitShieldRegen.value),
    massDiscount: parseInt(sliderUnitMass.value, 10),
    energyDiscount: parseInt(sliderUnitEnergy.value, 10),
    buildTimeDiscount: parseInt(sliderUnitBuildtime.value, 10),
    buildRateMult: parseFloat(sliderUnitBuildrate.value),
    prodMult: parseFloat(sliderUnitProd.value),
    speedMult: parseFloat(sliderUnitSpeed.value),
    turnRateMult: parseFloat(sliderUnitTurnrate.value),
    visionMult: parseFloat(sliderUnitVision.value),
    radarMult: parseFloat(sliderUnitRadar.value),
    damageMult: parseFloat(sliderUnitDamage.value),
    rangeMult: parseFloat(sliderUnitRange.value),
    rofMult: parseFloat(sliderUnitRof.value),
    aoeMult: parseFloat(sliderUnitAoe.value),
    muzzleVelMult: parseFloat(sliderUnitMuzzleVel.value),
  };

  unitConfigs.set(activeUnitId, cfg);
  loadSlidersFromConfig(unit, cfg);
  updateSelectionCounters();
  updateCardAppearance(activeUnitId);
  updateInspectorMembershipButton();
}

function updateSelectionCounters() {
  const count = unitConfigs.size;
  selectedUnitsCount.textContent = count;
  tabModCount.textContent = count;
  document.querySelectorAll('.export-units-count').forEach(el => el.textContent = count);
  ForgeStore.setBuffs(unitConfigs);
  ForgeStore.syncNavBadges();
}

// --- Tabs Management ---
function switchTab(tabName) {
  if (tabName === 'inspector') {
    tabBtnInspector.classList.add('active');
    tabBtnSettings.classList.remove('active');
    tabInspector.style.display = 'flex';
    tabSettings.style.display = 'none';
  } else {
    tabBtnInspector.classList.remove('active');
    tabBtnSettings.classList.add('active');
    tabInspector.style.display = 'none';
    tabSettings.style.display = 'flex';
  }
}

// --- Event Listeners Setup ---
function setupEventListeners() {
  // Tabs
  tabBtnInspector.addEventListener('click', () => switchTab('inspector'));
  tabBtnSettings.addEventListener('click', () => switchTab('settings'));

  // Search
  filterSearch.addEventListener('input', (e) => {
    currentFilters.search = e.target.value;
    clearSearchBtn.style.display = e.target.value ? 'block' : 'none';
    applyFilters();
  });

  clearSearchBtn.addEventListener('click', () => {
    filterSearch.value = '';
    currentFilters.search = '';
    clearSearchBtn.style.display = 'none';
    applyFilters();
  });

  // Filter Chips
  setupChipGroup('faction-chips', 'faction');
  setupChipGroup('tech-chips', 'tech');
  setupChipGroup('type-chips', 'type');

  // Sliders input events
  sliderUnitHp.addEventListener('input', onSliderChanged);
  sliderUnitRegen.addEventListener('input', onSliderChanged);
  sliderUnitShield.addEventListener('input', onSliderChanged);
  sliderUnitShieldRegen.addEventListener('input', onSliderChanged);

  sliderUnitDamage.addEventListener('input', onSliderChanged);
  sliderUnitRange.addEventListener('input', onSliderChanged);
  sliderUnitRof.addEventListener('input', onSliderChanged);
  sliderUnitAoe.addEventListener('input', onSliderChanged);
  sliderUnitMuzzleVel.addEventListener('input', onSliderChanged);

  sliderUnitMass.addEventListener('input', onSliderChanged);
  sliderUnitEnergy.addEventListener('input', onSliderChanged);
  sliderUnitBuildtime.addEventListener('input', onSliderChanged);
  sliderUnitBuildrate.addEventListener('input', onSliderChanged);
  sliderUnitProd.addEventListener('input', onSliderChanged);

  sliderUnitSpeed.addEventListener('input', onSliderChanged);
  sliderUnitTurnrate.addEventListener('input', onSliderChanged);
  sliderUnitVision.addEventListener('input', onSliderChanged);
  sliderUnitRadar.addEventListener('input', onSliderChanged);

  // Quick Presets
  document.querySelectorAll('.preset-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const pKey = chip.dataset.preset;
      if (!PRESETS[pKey]) return;
      if (!activeUnitId) return;

      const unit = unitMap.get(activeUnitId);
      if (!unit) return;

      const presetCfg = { ...PRESETS[pKey] };
      unitConfigs.set(activeUnitId, presetCfg);
      loadSlidersFromConfig(unit, presetCfg);
      updateSelectionCounters();
      updateCardAppearance(activeUnitId);
      updateInspectorMembershipButton();
      showToast(`Applied "${chip.textContent.trim()}" preset to ${unit.id}!`);
    });
  });

  // Inspector Include/Exclude Toggle Button
  btnToggleInclude.addEventListener('click', () => {
    if (!activeUnitId) return;
    toggleUnitInclusion(activeUnitId);
  });

  // Copy Stats to All Included Units
  btnCopyStats.addEventListener('click', () => {
    if (!activeUnitId || !unitConfigs.has(activeUnitId)) {
      showToast('⚠️ Please make sure the active unit is included in the mod first.');
      return;
    }
    const srcCfg = unitConfigs.get(activeUnitId);
    let copiedCount = 0;

    unitConfigs.forEach((_, uid) => {
      unitConfigs.set(uid, { ...srcCfg });
      copiedCount++;
      updateCardAppearance(uid);
    });

    showToast(`Copied ${activeUnitId}'s stats to all ${copiedCount} included units!`);
  });

  // Reset Active Unit to Vanilla
  btnResetUnit.addEventListener('click', () => {
    if (!activeUnitId) return;
    const vanilla = { ...PRESETS.vanilla };
    unitConfigs.set(activeUnitId, vanilla);
    const unit = unitMap.get(activeUnitId);
    if (unit) loadSlidersFromConfig(unit, vanilla);
    updateCardAppearance(activeUnitId);
    showToast(`Reset ${activeUnitId} to baseline vanilla stats.`);
  });

  // Batch Select Actions
  btnSelectFiltered.addEventListener('click', () => {
    filteredUnits.forEach(u => {
      if (!unitConfigs.has(u.id)) {
        unitConfigs.set(u.id, { ...DEFAULT_CONFIG });
      }
    });
    updateSelectionCounters();
    renderGrid();
    if (activeUnitId) updateInspectorMembershipButton();
    showToast(`Added ${filteredUnits.length} filtered units to mod.`);
  });

  btnDeselectFiltered.addEventListener('click', () => {
    let removedCount = 0;
    filteredUnits.forEach(u => {
      if (unitConfigs.has(u.id)) {
        unitConfigs.delete(u.id);
        removedCount++;
      }
    });
    updateSelectionCounters();
    renderGrid();
    if (activeUnitId) updateInspectorMembershipButton();
    showToast(`Deselected ${removedCount} units from mod.`);
  });

  btnClearSelection.addEventListener('click', () => {
    unitConfigs.clear();
    updateSelectionCounters();
    renderGrid();
    if (activeUnitId) updateInspectorMembershipButton();
    showToast('Reset all units: Mod is now empty.');
  });

  // Scope Radio Cards
  document.querySelectorAll('input[name="target-scope"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
      if (e.target.value === 'player') {
        cardScopePlayer.classList.add('active');
        cardScopeGlobal.classList.remove('active');
        groupPlayerName.style.display = 'flex';
      } else {
        cardScopePlayer.classList.remove('active');
        cardScopeGlobal.classList.add('active');
        groupPlayerName.style.display = 'none';
      }
      saveCurrentMetadata();
    });
  });

  // Metadata inputs
  inputAuthor.addEventListener('input', saveCurrentMetadata);
  inputVersion.addEventListener('input', saveCurrentMetadata);
  inputPlayerName.addEventListener('input', saveCurrentMetadata);

  // Open Mods Folder
  btnOpenFolder.addEventListener('click', async () => {
    try {
      await fetch('/api/open-folder', { method: 'POST' });
      showToast('Opened Supreme Commander Mods directory in File Explorer.');
    } catch (err) {
      showToast('Error opening folder: ' + err.message);
    }
  });

  // Export Buttons
  btnExport.addEventListener('click', handleExport);
  btnQuickExport.addEventListener('click', handleExport);
}

function setupChipGroup(containerId, filterKey) {
  const container = document.getElementById(containerId);
  container.addEventListener('click', (e) => {
    if (e.target.classList.contains('chip')) {
      container.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      e.target.classList.add('active');
      currentFilters[filterKey] = e.target.dataset.val;
      applyFilters();
    }
  });
}

// --- Export Mod Handler ---
async function handleExport() {
  if (unitConfigs.size === 0) {
    showToast('⚠️ Please select or customize at least one unit first!');
    return;
  }

  const modName = inputModName.value.trim() || 'Custom Player Mod';
  const author = inputAuthor.value.trim() || 'User';
  const version = parseInt(inputVersion.value, 10) || 1;
  const targetMode = document.querySelector('input[name="target-scope"]:checked').value;
  const playerName = inputPlayerName.value.trim();

  if (targetMode === 'player' && !playerName) {
    showToast('⚠️ Please enter your FAF in-game nickname!');
    switchTab('settings');
    inputPlayerName.focus();
    return;
  }

  // Convert unitConfigs Map to regular object
  const configsObj = {};
  unitConfigs.forEach((cfg, uid) => {
    configsObj[uid] = cfg;
  });

  const payload = {
    modName,
    author,
    version,
    targetMode,
    playerName,
    unitConfigs: configsObj
  };

  btnExport.disabled = true;
  btnQuickExport.disabled = true;
  btnExport.textContent = '⏳ Packaging Mod...';
  btnQuickExport.textContent = '⏳ Packaging Mod...';
  exportFeedback.style.display = 'none';

  try {
    const res = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const result = await res.json();

    if (result.success) {
      showToast('✅ Mod successfully packaged and installed!');
      renderExportSuccess(result);
      switchTab('settings');
    } else {
      showToast('❌ Export error: ' + result.error);
      renderExportError(result.error);
      switchTab('settings');
    }
  } catch (err) {
    showToast('❌ Export failed: ' + err.message);
    renderExportError(err.message);
    switchTab('settings');
  } finally {
    btnExport.disabled = false;
    btnQuickExport.disabled = false;
    updateSelectionCounters();
    btnExport.innerHTML = `🚀 Pack & Export Mod (<span class="export-units-count">${unitConfigs.size}</span> units)`;
    btnQuickExport.innerHTML = `🚀 Pack & Export Mod (<span class="export-units-count">${unitConfigs.size}</span> units)`;
  }
}

function renderExportSuccess(result) {
  exportFeedback.className = 'feedback-card';
  exportFeedback.style.display = 'block';

  const modeBadge = result.targetMode === 'player'
    ? `<span style="color: var(--accent-gold);">👑 Specific Player (${result.playerName})</span>`
    : `<span style="color: var(--accent-cyan);">🌐 Global (All Players)</span>`;

  exportFeedback.innerHTML = `
    <h4>🎉 Mod Ready to Play!</h4>
    <p><strong>${result.modName}</strong> (v${inputVersion.value})</p>
    <p>Target: ${modeBadge} | Units: <strong>${result.unitsCount}</strong></p>
    
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
      4. If playing multiplayer with friends, send them the .zip file to extract into their mods folder!
    </div>
  `;
}

function renderExportError(errorMsg) {
  exportFeedback.className = 'feedback-card error';
  exportFeedback.style.display = 'block';
  exportFeedback.innerHTML = `
    <h4 style="color: var(--accent-red);">❌ Export Failed</h4>
    <p style="font-size: 0.75rem;">${errorMsg}</p>
  `;
}

function showToast(msg) {
  toastEl.textContent = msg;
  toastEl.style.display = 'block';
  setTimeout(() => {
    toastEl.style.display = 'none';
  }, 3500);
}

// Start
init();
