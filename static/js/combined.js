/**
 * FAF Mod Forge - Combined Master Mod Dashboard Logic
 * Aggregates all rules from Unit Buffs, Limits, Popups, and Relics into a single mod.
 */

let allUnits = [];
let unitMap = new Map();

// DOM Elements
const totalCombinedCountEl = document.getElementById("total-combined-count");
const btnCombinedCountEl = document.getElementById("btn-combined-count");
const btnExportCombined = document.getElementById("btn-export-combined");
const exportFeedback = document.getElementById("export-feedback");
const toastEl = document.getElementById("toast");

const checkIncludeBuffs = document.getElementById("check-include-buffs");
const checkIncludeLimits = document.getElementById("check-include-limits");
const checkIncludePopups = document.getElementById("check-include-popups");
const checkIncludeRelics = document.getElementById("check-include-relics");
const checkIncludeLootbox = document.getElementById("check-include-lootbox");

const cardModuleBuffs = document.getElementById("card-module-buffs");
const cardModuleLimits = document.getElementById("card-module-limits");
const cardModulePopups = document.getElementById("card-module-popups");
const cardModuleRelics = document.getElementById("card-module-relics");
const cardModuleLootbox = document.getElementById("card-module-lootbox");

const previewListBuffs = document.getElementById("preview-list-buffs");
const previewListLimits = document.getElementById("preview-list-limits");
const previewListPopups = document.getElementById("preview-list-popups");
const previewListRelics = document.getElementById("preview-list-relics");
const previewListLootbox = document.getElementById("preview-list-lootbox");

const statusBadgeBuffs = document.getElementById("status-badge-buffs");
const statusBadgeLimits = document.getElementById("status-badge-limits");
const statusBadgePopups = document.getElementById("status-badge-popups");
const statusBadgeRelics = document.getElementById("status-badge-relics");
const statusBadgeLootbox = document.getElementById("status-badge-lootbox");

const bdBuffsVal = document.getElementById("bd-buffs-val");
const bdLimitsVal = document.getElementById("bd-limits-val");
const bdPopupsVal = document.getElementById("bd-popups-val");
const bdRelicsVal = document.getElementById("bd-relics-val");
const bdLootboxVal = document.getElementById("bd-lootbox-val");
const bdProfilesRow = document.getElementById("bd-profiles-row");
const bdProfilesVal = document.getElementById("bd-profiles-val");
const bdTotalVal = document.getElementById("bd-total-val");

const inputModName = document.getElementById("input-mod-name");
const inputAuthor = document.getElementById("input-author");
const inputVersion = document.getElementById("input-version");
const inputPlayerName = document.getElementById("input-player-name");
const cardScopePlayer = document.getElementById("card-scope-player");
const cardScopeMultiplayer = document.getElementById("card-scope-multiplayer");
const cardScopeGlobal = document.getElementById("card-scope-global");
const groupPlayerName = document.getElementById("group-player-name");

const multiplayerProfilesPanel = document.getElementById("multiplayer-profiles-panel");
const profilesCardsContainer = document.getElementById("profiles-cards-container");
const btnAddProfile = document.getElementById("btn-add-profile");
const btnPreset1v1 = document.getElementById("btn-preset-1v1");
const btnPresetBoss = document.getElementById("btn-preset-boss");
const btnPresetRoles = document.getElementById("btn-preset-roles");

// --- Initialization ---
document.addEventListener("DOMContentLoaded", async () => {
  setupEventListeners();
  loadSavedMetadata();
  await loadUnits();
  renderAllModulePreviews();
  renderPlayerProfiles();
  updateBreakdownCounters();
  ForgeStore.syncNavBadges();
});

async function loadUnits() {
  try {
    const res = await fetch("/api/units");
    allUnits = await res.json();
    unitMap.clear();
    allUnits.forEach(u => unitMap.set(u.id.toLowerCase(), u));
  } catch (err) {
    console.error("Failed to load units:", err);
  }
}

function setScope(mode) {
  cardScopePlayer.classList.toggle("active", mode === "player");
  cardScopeMultiplayer.classList.toggle("active", mode === "multiplayer");
  cardScopeGlobal.classList.toggle("active", mode === "global");

  const radio = document.querySelector(`input[name="target-scope"][value="${mode}"]`);
  if (radio) radio.checked = true;

  groupPlayerName.style.display = mode === "player" ? "block" : "none";
  if (multiplayerProfilesPanel) {
    multiplayerProfilesPanel.style.display = mode === "multiplayer" ? "block" : "none";
  }

  if (mode === "multiplayer") {
    renderPlayerProfiles();
  }

  saveCurrentMetadata();
  updateBreakdownCounters();
}

function loadSavedMetadata() {
  const meta = ForgeStore.getModMeta();
  if (meta.modName) inputModName.value = meta.modName;
  if (meta.author) inputAuthor.value = meta.author;
  if (meta.version) inputVersion.value = meta.version;
  if (meta.playerName) inputPlayerName.value = meta.playerName;
  
  if (meta.targetMode === "multiplayer") {
    setScope("multiplayer");
  } else if (meta.targetMode === "global") {
    setScope("global");
  } else {
    setScope("player");
  }
}

function saveCurrentMetadata() {
  const targetMode = document.querySelector('input[name="target-scope"]:checked')?.value || "player";
  ForgeStore.setModMeta({
    modName: inputModName.value.trim(),
    author: inputAuthor.value.trim(),
    version: parseInt(inputVersion.value, 10) || 1,
    targetMode,
    playerName: inputPlayerName.value.trim()
  });
}

function setupEventListeners() {
  // Checkbox change handlers
  [checkIncludeBuffs, checkIncludeLimits, checkIncludePopups, checkIncludeRelics, checkIncludeLootbox].forEach(chk => {
    if (!chk) return;
    chk.addEventListener("change", () => {
      updateModuleCardStyles();
      updateBreakdownCounters();
    });
  });

  // Select all modules
  document.getElementById("btn-select-all-modules").addEventListener("click", () => {
    checkIncludeBuffs.checked = true;
    checkIncludeLimits.checked = true;
    checkIncludePopups.checked = true;
    checkIncludeRelics.checked = true;
    if (checkIncludeLootbox) checkIncludeLootbox.checked = true;
    updateModuleCardStyles();
    updateBreakdownCounters();
    showToast("Selected all 5 modules.");
  });

  // Clear all data
  document.getElementById("btn-clear-all-data").addEventListener("click", () => {
    if (confirm("Are you sure you want to clear all configured rules across all pages? This cannot be undone.")) {
      ForgeStore.clearAll();
      renderAllModulePreviews();
      renderPlayerProfiles();
      updateBreakdownCounters();
      ForgeStore.syncNavBadges();
      showToast("Cleared all rules across all forge modules.");
    }
  });

  // Scope Radio Cards
  cardScopePlayer.addEventListener("click", () => setScope("player"));
  cardScopeMultiplayer.addEventListener("click", () => setScope("multiplayer"));
  cardScopeGlobal.addEventListener("click", () => setScope("global"));

  inputModName.addEventListener("input", saveCurrentMetadata);
  inputAuthor.addEventListener("input", saveCurrentMetadata);
  inputVersion.addEventListener("input", saveCurrentMetadata);
  inputPlayerName.addEventListener("input", saveCurrentMetadata);

  // Roster Add and Preset Buttons
  if (btnAddProfile) {
    btnAddProfile.addEventListener("click", () => {
      const profiles = ForgeStore.getPlayerProfiles();
      const newId = "prof_" + Date.now();
      profiles.push({
        id: newId,
        playerName: "Player" + (profiles.length + 1),
        roleName: "Custom Role",
        icon: "⚔️",
        damageDealtMult: 1.0,
        damageTakenMult: 1.0,
        buildRateMult: 1.0,
        prodMult: 1.0,
        buffsMode: "global",
        limitsMode: "global",
        customBuffs: {},
        customLimits: []
      });
      ForgeStore.setPlayerProfiles(profiles);
      renderPlayerProfiles();
      showToast("➕ Added new player profile.");
    });
  }

  if (btnPreset1v1) {
    btnPreset1v1.addEventListener("click", () => {
      const currentHost = inputPlayerName.value.trim() || "HostPlayer";
      const preset = [
        {
          id: "prof_1",
          playerName: currentHost,
          roleName: "Player 1 (Host Standard)",
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
          playerName: "Challenger",
          roleName: "Challenger (+35% Dmg, +25% Build)",
          icon: "⚡",
          damageDealtMult: 1.35,
          damageTakenMult: 0.85,
          buildRateMult: 1.25,
          prodMult: 1.1,
          buffsMode: "global",
          limitsMode: "none",
          customBuffs: {},
          customLimits: []
        },
        {
          id: "prof_3",
          playerName: "*",
          roleName: "All Other Players (Vanilla)",
          icon: "🌐",
          damageDealtMult: 1.0,
          damageTakenMult: 1.0,
          buildRateMult: 1.0,
          prodMult: 1.0,
          buffsMode: "none",
          limitsMode: "none",
          customBuffs: {},
          customLimits: []
        }
      ];
      ForgeStore.setPlayerProfiles(preset);
      renderPlayerProfiles();
      showToast("⚡ Loaded 1v1 Asymmetric Preset!");
    });
  }

  if (btnPresetBoss) {
    btnPresetBoss.addEventListener("click", () => {
      const currentHost = inputPlayerName.value.trim() || "Defender1";
      const preset = [
        {
          id: "prof_1",
          playerName: currentHost,
          roleName: "Co-op Defender 1",
          icon: "🛡️",
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
          playerName: "Ally",
          roleName: "Co-op Defender 2",
          icon: "⚔️",
          damageDealtMult: 1.0,
          damageTakenMult: 1.0,
          buildRateMult: 1.1,
          prodMult: 1.0,
          buffsMode: "global",
          limitsMode: "global",
          customBuffs: {},
          customLimits: []
        },
        {
          id: "prof_3",
          playerName: "AI",
          roleName: "Colossus AI Boss (2x Dmg, 50% Armor)",
          icon: "🤖",
          damageDealtMult: 2.0,
          damageTakenMult: 0.5,
          buildRateMult: 2.0,
          prodMult: 2.0,
          buffsMode: "global",
          limitsMode: "none",
          customBuffs: {},
          customLimits: []
        },
        {
          id: "prof_4",
          playerName: "*",
          roleName: "Unlisted Players (Vanilla)",
          icon: "🌐",
          damageDealtMult: 1.0,
          damageTakenMult: 1.0,
          buildRateMult: 1.0,
          prodMult: 1.0,
          buffsMode: "none",
          limitsMode: "none",
          customBuffs: {},
          customLimits: []
        }
      ];
      ForgeStore.setPlayerProfiles(preset);
      renderPlayerProfiles();
      showToast("👑 Loaded Boss Raid Preset!");
    });
  }

  if (btnPresetRoles) {
    btnPresetRoles.addEventListener("click", () => {
      const currentHost = inputPlayerName.value.trim() || "ArmorSpec";
      const preset = [
        {
          id: "prof_1",
          playerName: currentHost,
          roleName: "Heavy Armor Specialist",
          icon: "🛡️",
          damageDealtMult: 1.25,
          damageTakenMult: 0.8,
          buildRateMult: 1.0,
          prodMult: 1.0,
          buffsMode: "global",
          limitsMode: "global",
          customBuffs: {},
          customLimits: []
        },
        {
          id: "prof_2",
          playerName: "SupportPlayer",
          roleName: "Macro & Tech Specialist",
          icon: "🏗️",
          damageDealtMult: 1.0,
          damageTakenMult: 1.0,
          buildRateMult: 2.0,
          prodMult: 1.5,
          buffsMode: "none",
          limitsMode: "global",
          customBuffs: {},
          customLimits: []
        },
        {
          id: "prof_3",
          playerName: "AI",
          roleName: "AI Opponent Wave",
          icon: "🤖",
          damageDealtMult: 1.3,
          damageTakenMult: 0.9,
          buildRateMult: 1.3,
          prodMult: 1.2,
          buffsMode: "none",
          limitsMode: "none",
          customBuffs: {},
          customLimits: []
        }
      ];
      ForgeStore.setPlayerProfiles(preset);
      renderPlayerProfiles();
      showToast("🤝 Loaded Co-op Specialized Roles Preset!");
    });
  }

  // Folder open button
  document.getElementById("btn-open-folder").addEventListener("click", async () => {
    try {
      await fetch("/api/open-folder", { method: "POST" });
      showToast("Opened Supreme Commander mods directory in File Explorer.");
    } catch (e) {
      showToast("Could not open mods folder: " + e.message);
    }
  });

  // Export Combined Mod Button
  btnExportCombined.addEventListener("click", handleExportCombined);
}

// --- Render Previews for All 5 Modules ---
function renderAllModulePreviews() {
  renderBuffsPreview();
  renderLimitsPreview();
  renderPopupsPreview();
  renderRelicsPreview();
  renderLootboxPreview();
  updateModuleCardStyles();
}

function renderBuffsPreview() {
  const buffs = ForgeStore.getBuffs();
  const entries = Object.entries(buffs);
  previewListBuffs.innerHTML = "";

  if (entries.length === 0) {
    statusBadgeBuffs.textContent = "0 Units";
    statusBadgeBuffs.className = "module-status-badge empty";
    previewListBuffs.innerHTML = `
      <div class="module-empty-notice">
        No unit stat buffs configured. Click "Edit Buffs" to boost units.
      </div>
    `;
    return;
  }

  statusBadgeBuffs.textContent = `${entries.length} Units`;
  statusBadgeBuffs.className = "module-status-badge enabled";

  entries.forEach(([uid, cfg]) => {
    const unit = unitMap.get(uid.toLowerCase());
    const unitName = unit ? unit.name : uid.toUpperCase();

    const pills = [];
    if (cfg.hpMult && cfg.hpMult !== 1.0) pills.push(`HP x${cfg.hpMult}`);
    if (cfg.damageMult && cfg.damageMult !== 1.0) pills.push(`Dmg x${cfg.damageMult}`);
    if (cfg.speedMult && cfg.speedMult !== 1.0) pills.push(`Spd x${cfg.speedMult}`);
    if (cfg.rangeMult && cfg.rangeMult !== 1.0) pills.push(`Rng x${cfg.rangeMult}`);
    if (cfg.massDiscount && cfg.massDiscount > 0) pills.push(`-${cfg.massDiscount}% Mass`);
    if (cfg.buildRateMult && cfg.buildRateMult !== 1.0) pills.push(`Build x${cfg.buildRateMult}`);

    const item = document.createElement("div");
    item.className = "module-item-pill";
    item.innerHTML = `
      <span class="name" title="${unitName}">⚡ ${unitName}</span>
      <span class="detail">${pills.slice(0, 3).join(", ") || "Modified"}</span>
    `;
    previewListBuffs.appendChild(item);
  });
}

function renderLimitsPreview() {
  const limits = ForgeStore.getLimits() || [];
  previewListLimits.innerHTML = "";

  if (limits.length === 0) {
    statusBadgeLimits.textContent = "0 Limits";
    statusBadgeLimits.className = "module-status-badge empty";
    previewListLimits.innerHTML = `
      <div class="module-empty-notice">
        No unit limits configured. Click "Edit Limits" to set caps or bans.
      </div>
    `;
    return;
  }

  statusBadgeLimits.textContent = `${limits.length} Limits`;
  statusBadgeLimits.className = "module-status-badge enabled";

  limits.forEach(r => {
    const isBanned = r.limit === 0;
    const limitLabel = isBanned ? "⛔ BANNED" : `Max: ${r.limit}`;

    const item = document.createElement("div");
    item.className = "module-item-pill";
    item.innerHTML = `
      <span class="name">${r.icon || "🛑"} ${r.name}</span>
      <span class="detail" style="color: ${isBanned ? 'var(--accent-red)' : 'var(--accent-cyan)'}; font-weight: 700;">
        ${limitLabel}
      </span>
    `;
    previewListLimits.appendChild(item);
  });
}

function renderPopupsPreview() {
  const popups = ForgeStore.getPopups() || [];
  previewListPopups.innerHTML = "";

  if (popups.length === 0) {
    statusBadgePopups.textContent = "0 Alerts";
    statusBadgePopups.className = "module-status-badge empty";
    previewListPopups.innerHTML = `
      <div class="module-empty-notice">
        No event popups configured. Click "Edit Popups" to add notifications.
      </div>
    `;
    return;
  }

  statusBadgePopups.textContent = `${popups.length} Alerts`;
  statusBadgePopups.className = "module-status-badge enabled";

  popups.forEach(p => {
    const item = document.createElement("div");
    item.className = "module-item-pill";
    item.innerHTML = `
      <span class="name">${p.icon || "📢"} ${p.name || p.title}</span>
      <span class="detail">${p.theme ? p.theme.toUpperCase() : "ALERT"} ${p.hasPinpoint ? '🎯' : ''}</span>
    `;
    previewListPopups.appendChild(item);
  });
}

function renderRelicsPreview() {
  const relics = ForgeStore.getRelics() || [];
  previewListRelics.innerHTML = "";

  if (relics.length === 0) {
    statusBadgeRelics.textContent = "0 Objectives";
    statusBadgeRelics.className = "module-status-badge empty";
    previewListRelics.innerHTML = `
      <div class="module-empty-notice">
        No relic objectives configured. Click "Edit Relics" to add battlefield crates.
      </div>
    `;
    return;
  }

  statusBadgeRelics.textContent = `${relics.length} Objectives`;
  statusBadgeRelics.className = "module-status-badge enabled";

  relics.forEach(o => {
    const item = document.createElement("div");
    item.className = "module-item-pill";
    item.innerHTML = `
      <span class="name">${o.icon || "💎"} ${o.name}</span>
      <span class="detail">🎯 ${o.targetName || "Units"}</span>
    `;
    previewListRelics.appendChild(item);
  });
}

function renderLootboxPreview() {
  const lb = ForgeStore.getLootbox();
  if (!previewListLootbox) return;
  previewListLootbox.innerHTML = "";

  if (!lb || !lb.enabled || !lb.dropTable || lb.dropTable.length === 0) {
    statusBadgeLootbox.textContent = "0 Outcomes";
    statusBadgeLootbox.className = "module-status-badge empty";
    previewListLootbox.innerHTML = `
      <div class="module-empty-notice">
        No casino lootbox configured. Click "Edit Casino" to set up vaults.
      </div>
    `;
    return;
  }

  statusBadgeLootbox.textContent = `${lb.dropTable.length} Outcomes`;
  statusBadgeLootbox.className = "module-status-badge enabled";

  const modeLabel = lb.openMode === "instant_crack" ? "Capture & Run" : "Casino";
  const gmLabel = lb.observerGmPlacement ? ` | GM: ${lb.observerGmName || "DrReed"}` : "";
  const vaultItem = document.createElement("div");
  vaultItem.className = "module-item-pill";
  vaultItem.innerHTML = `
    <span class="name" style="color: #ffd700;">📦 ${lb.name || "Quantum Vault"}</span>
    <span class="detail">${modeLabel}${gmLabel}</span>
  `;
  previewListLootbox.appendChild(vaultItem);

  lb.dropTable.slice(0, 3).forEach(drop => {
    const item = document.createElement("div");
    item.className = "module-item-pill";
    const icon = (drop.reels && drop.reels[0]) || "🎲";
    item.innerHTML = `
      <span class="name">${icon} ${drop.name}</span>
      <span class="detail" style="color: #c084fc;">${drop.rarity.toUpperCase()}</span>
    `;
    previewListLootbox.appendChild(item);
  });
}

function updateModuleCardStyles() {
  cardModuleBuffs.style.opacity = checkIncludeBuffs.checked ? "1" : "0.5";
  cardModuleLimits.style.opacity = checkIncludeLimits.checked ? "1" : "0.5";
  cardModulePopups.style.opacity = checkIncludePopups.checked ? "1" : "0.5";
  cardModuleRelics.style.opacity = checkIncludeRelics.checked ? "1" : "0.5";
  if (cardModuleLootbox && checkIncludeLootbox) {
    cardModuleLootbox.style.opacity = checkIncludeLootbox.checked ? "1" : "0.5";
  }
}

const AVATAR_OPTIONS = ["👑", "⚔️", "🛡️", "🤖", "⚡", "🏗️", "🌱", "🚀", "💎", "🌐"];

function updateBreakdownCounters() {
  const buffs = ForgeStore.getBuffs();
  const limits = ForgeStore.getLimits() || [];
  const popups = ForgeStore.getPopups() || [];
  const relics = ForgeStore.getRelics() || [];
  const lootbox = ForgeStore.getLootbox();
  const profiles = ForgeStore.getPlayerProfiles();

  const buffsCount = Object.keys(buffs).length;
  const limitsCount = limits.length;
  const popupsCount = popups.length;
  const relicsCount = relics.length;
  const lootboxCount = (lootbox && lootbox.enabled && lootbox.dropTable) ? lootbox.dropTable.length : 0;
  const targetMode = document.querySelector('input[name="target-scope"]:checked')?.value || "player";

  bdBuffsVal.textContent = checkIncludeBuffs.checked ? buffsCount : 0;
  bdLimitsVal.textContent = checkIncludeLimits.checked ? limitsCount : 0;
  bdPopupsVal.textContent = checkIncludePopups.checked ? popupsCount : 0;
  bdRelicsVal.textContent = checkIncludeRelics.checked ? relicsCount : 0;
  if (bdLootboxVal) {
    bdLootboxVal.textContent = (checkIncludeLootbox && checkIncludeLootbox.checked) ? lootboxCount : 0;
  }

  if (bdProfilesRow && bdProfilesVal) {
    if (targetMode === "multiplayer") {
      bdProfilesRow.style.display = "flex";
      bdProfilesVal.textContent = profiles.length;
    } else {
      bdProfilesRow.style.display = "none";
    }
  }

  let total = 0;
  const lbIncluded = (checkIncludeLootbox && checkIncludeLootbox.checked && lootboxCount > 0) ? 1 : 0;
  if (targetMode === "multiplayer") {
    total = profiles.length +
            (checkIncludePopups.checked ? popupsCount : 0) +
            (checkIncludeRelics.checked ? relicsCount : 0) +
            lbIncluded;
  } else {
    total = (checkIncludeBuffs.checked ? buffsCount : 0) +
            (checkIncludeLimits.checked ? limitsCount : 0) +
            (checkIncludePopups.checked ? popupsCount : 0) +
            (checkIncludeRelics.checked ? relicsCount : 0) +
            lbIncluded;
  }

  bdTotalVal.textContent = total;
  btnCombinedCountEl.textContent = total;
  totalCombinedCountEl.textContent = total;
}

// --- Multiplayer Profiles Rendering ---
function renderPlayerProfiles() {
  if (!profilesCardsContainer) return;
  const profiles = ForgeStore.getPlayerProfiles();
  profilesCardsContainer.innerHTML = "";

  profiles.forEach((p, index) => {
    const card = document.createElement("div");
    let themeClass = "ally";
    const pName = (p.playerName || "").trim();
    const rName = (p.roleName || "").toLowerCase();
    if (index === 0) themeClass = "host";
    else if (pName.toLowerCase().includes("ai") || rName.includes("boss")) themeClass = "boss";
    else if (pName === "*" || pName.toLowerCase() === "default") themeClass = "unlisted";

    card.className = `player-profile-card ${themeClass}`;

    const icon = p.icon || (index === 0 ? "👑" : (themeClass === "boss" ? "🤖" : (themeClass === "unlisted" ? "🌐" : "⚔️")));
    const isUnlisted = pName === "*" || pName.toLowerCase() === "default";

    card.innerHTML = `
      <div class="profile-card-top">
        <div class="profile-identity-wrap">
          <button type="button" class="profile-avatar-select" data-id="${p.id}" title="Click to cycle icon">${icon}</button>
          <div class="profile-name-fields">
            <input type="text" class="profile-input-player" data-field="playerName" data-id="${p.id}" 
                   value="${p.playerName || ''}" placeholder="FAF Nickname or *" ${isUnlisted ? 'title="Wildcard matches all unlisted players in match"' : ''}>
            <input type="text" class="profile-input-role" data-field="roleName" data-id="${p.id}" 
                   value="${p.roleName || ''}" placeholder="Role description (e.g. Tank Specialist)">
          </div>
        </div>
        <div class="profile-card-actions">
          <button type="button" class="profile-icon-btn duplicate" data-id="${p.id}" title="Duplicate Profile">📋</button>
          ${profiles.length > 1 ? `<button type="button" class="profile-icon-btn delete" data-id="${p.id}" title="Remove Profile">🗑️</button>` : ''}
        </div>
      </div>

      <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
        <span class="profile-assign-label">⚡ Role Preset:</span>
        <select class="profile-assign-select profile-preset-select" data-id="${p.id}" style="flex: 1;">
          <option value="custom">⚙️ Custom Multipliers</option>
          <option value="boss">👑 Juggernaut Boss (2x Dmg, 50% Armor, 2x Econ)</option>
          <option value="tank">🛡️ Vanguard Armor (1.25x Dmg, 15% Armor)</option>
          <option value="speed">⚡ Speed Blitz (+30% Speed/RoF, 1.2x Dmg)</option>
          <option value="builder">🏗️ Macro Titan (2x Build Rate, 1.5x Income)</option>
          <option value="handicap">🌱 Beginner Handicap (+30% HP, -20% Cost)</option>
          <option value="vanilla">⚪ Vanilla Standard (Default 1.0x)</option>
        </select>
      </div>

      <div class="profile-modifiers-grid">
        <div class="profile-mod-cell" title="Damage dealt multiplier (e.g. 1.25 = +25% damage dealt)">
          <span class="profile-mod-label">Dmg Dealt</span>
          <input type="number" step="0.05" min="0.1" max="10.0" class="profile-mod-input" 
                 data-field="damageDealtMult" data-id="${p.id}" value="${p.damageDealtMult ?? 1.0}">
        </div>
        <div class="profile-mod-cell" title="Damage taken multiplier (e.g. 0.8 = 20% damage reduction / armor)">
          <span class="profile-mod-label">Dmg Taken</span>
          <input type="number" step="0.05" min="0.1" max="10.0" class="profile-mod-input" 
                 data-field="damageTakenMult" data-id="${p.id}" value="${p.damageTakenMult ?? 1.0}">
        </div>
        <div class="profile-mod-cell" title="Build rate multiplier for engineers and factories">
          <span class="profile-mod-label">Build Rate</span>
          <input type="number" step="0.05" min="0.1" max="10.0" class="profile-mod-input" 
                 data-field="buildRateMult" data-id="${p.id}" value="${p.buildRateMult ?? 1.0}">
        </div>
        <div class="profile-mod-cell" title="Mass & Energy production multiplier">
          <span class="profile-mod-label">Income</span>
          <input type="number" step="0.05" min="0.1" max="10.0" class="profile-mod-input" 
                 data-field="prodMult" data-id="${p.id}" value="${p.prodMult ?? 1.0}">
        </div>
      </div>

      <div class="profile-assignments-row">
        <div class="profile-assign-box">
          <span class="profile-assign-label">⚡ Unit Buffs:</span>
          <select class="profile-assign-select" data-field="buffsMode" data-id="${p.id}">
            <option value="global" ${p.buffsMode === 'global' ? 'selected' : ''}>Apply Global Buffs</option>
            <option value="none" ${p.buffsMode === 'none' ? 'selected' : ''}>Vanilla Units (No Buffs)</option>
          </select>
        </div>
        <div class="profile-assign-box">
          <span class="profile-assign-label">🛑 Unit Limits:</span>
          <select class="profile-assign-select" data-field="limitsMode" data-id="${p.id}">
            <option value="global" ${p.limitsMode === 'global' ? 'selected' : ''}>Enforce Global Limits</option>
            <option value="none" ${p.limitsMode === 'none' ? 'selected' : ''}>No Limits (Uncapped)</option>
          </select>
        </div>
      </div>
    `;

    profilesCardsContainer.appendChild(card);
  });

  attachProfileCardEventListeners();
  updateBreakdownCounters();
}

function attachProfileCardEventListeners() {
  // Avatar cycling
  profilesCardsContainer.querySelectorAll(".profile-avatar-select").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-id");
      const profiles = ForgeStore.getPlayerProfiles();
      const prof = profiles.find(p => p.id === id);
      if (prof) {
        const currentIcon = prof.icon || "👑";
        const currentIndex = AVATAR_OPTIONS.indexOf(currentIcon);
        const nextIndex = (currentIndex + 1) % AVATAR_OPTIONS.length;
        prof.icon = AVATAR_OPTIONS[nextIndex];
        ForgeStore.setPlayerProfiles(profiles);
        renderPlayerProfiles();
      }
    });
  });

  // Inputs change handlers
  profilesCardsContainer.querySelectorAll("input, select:not(.profile-preset-select)").forEach(input => {
    input.addEventListener("input", () => {
      const id = input.getAttribute("data-id");
      const field = input.getAttribute("data-field");
      const profiles = ForgeStore.getPlayerProfiles();
      const prof = profiles.find(p => p.id === id);
      if (prof && field) {
        if (input.type === "number") {
          prof[field] = parseFloat(input.value) || 1.0;
        } else {
          prof[field] = input.value;
        }
        ForgeStore.setPlayerProfiles(profiles);
        updateBreakdownCounters();
      }
    });
  });

  // Role Preset handler
  profilesCardsContainer.querySelectorAll(".profile-preset-select").forEach(select => {
    select.addEventListener("change", () => {
      const id = select.getAttribute("data-id");
      const presetType = select.value;
      if (presetType === "custom") return;

      const profiles = ForgeStore.getPlayerProfiles();
      const prof = profiles.find(p => p.id === id);
      if (!prof) return;

      if (presetType === "boss") {
        prof.icon = "🤖";
        prof.roleName = "Juggernaut Boss";
        prof.damageDealtMult = 2.0;
        prof.damageTakenMult = 0.5;
        prof.buildRateMult = 2.0;
        prof.prodMult = 2.0;
        prof.buffsMode = "global";
        prof.limitsMode = "none";
      } else if (presetType === "tank") {
        prof.icon = "🛡️";
        prof.roleName = "Vanguard Armor";
        prof.damageDealtMult = 1.25;
        prof.damageTakenMult = 0.85;
        prof.buildRateMult = 1.0;
        prof.prodMult = 1.0;
        prof.buffsMode = "global";
        prof.limitsMode = "global";
      } else if (presetType === "speed") {
        prof.icon = "⚡";
        prof.roleName = "Speed Blitz";
        prof.damageDealtMult = 1.2;
        prof.damageTakenMult = 1.0;
        prof.buildRateMult = 1.25;
        prof.prodMult = 1.0;
        prof.buffsMode = "global";
        prof.limitsMode = "none";
      } else if (presetType === "builder") {
        prof.icon = "🏗️";
        prof.roleName = "Macro Titan";
        prof.damageDealtMult = 1.0;
        prof.damageTakenMult = 1.0;
        prof.buildRateMult = 2.0;
        prof.prodMult = 1.5;
        prof.buffsMode = "none";
        prof.limitsMode = "global";
      } else if (presetType === "handicap") {
        prof.icon = "🌱";
        prof.roleName = "Beginner Boost";
        prof.damageDealtMult = 1.2;
        prof.damageTakenMult = 0.75;
        prof.buildRateMult = 1.3;
        prof.prodMult = 1.3;
        prof.buffsMode = "global";
        prof.limitsMode = "none";
      } else if (presetType === "vanilla") {
        prof.icon = "⚪";
        prof.roleName = "Vanilla Standard";
        prof.damageDealtMult = 1.0;
        prof.damageTakenMult = 1.0;
        prof.buildRateMult = 1.0;
        prof.prodMult = 1.0;
        prof.buffsMode = "none";
        prof.limitsMode = "none";
      }

      ForgeStore.setPlayerProfiles(profiles);
      renderPlayerProfiles();
      showToast(`Applied ${presetType.toUpperCase()} preset to ${prof.playerName}!`);
    });
  });

  // Duplicate handler
  profilesCardsContainer.querySelectorAll(".profile-icon-btn.duplicate").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-id");
      const profiles = ForgeStore.getPlayerProfiles();
      const prof = profiles.find(p => p.id === id);
      if (prof) {
        const clone = JSON.parse(JSON.stringify(prof));
        clone.id = "prof_" + Date.now();
        clone.playerName = (clone.playerName || "Player") + "_Copy";
        profiles.push(clone);
        ForgeStore.setPlayerProfiles(profiles);
        renderPlayerProfiles();
        showToast("📋 Duplicated profile.");
      }
    });
  });

  // Delete handler
  profilesCardsContainer.querySelectorAll(".profile-icon-btn.delete").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-id");
      let profiles = ForgeStore.getPlayerProfiles();
      if (profiles.length <= 1) {
        showToast("⚠️ Must have at least one player profile!");
        return;
      }
      profiles = profiles.filter(p => p.id !== id);
      ForgeStore.setPlayerProfiles(profiles);
      renderPlayerProfiles();
      showToast("🗑️ Profile removed.");
    });
  });
}

// --- Export Combined Mod ---
async function handleExportCombined() {
  const targetMode = document.querySelector('input[name="target-scope"]:checked')?.value || "player";
  const playerName = inputPlayerName.value.trim();

  const includeBuffs = checkIncludeBuffs.checked;
  const includeLimits = checkIncludeLimits.checked;
  const includePopups = checkIncludePopups.checked;
  const includeRelics = checkIncludeRelics.checked;
  const includeLootbox = checkIncludeLootbox ? checkIncludeLootbox.checked : false;

  const buffs = includeBuffs ? ForgeStore.getBuffs() : {};
  const limits = includeLimits ? (ForgeStore.getLimits() || []) : [];
  const popups = includePopups ? (ForgeStore.getPopups() || []) : [];
  const relics = includeRelics ? (ForgeStore.getRelics() || []) : [];
  const lootbox = includeLootbox ? ForgeStore.getLootbox() : null;
  const profiles = ForgeStore.getPlayerProfiles();

  if (targetMode === "multiplayer") {
    const validProfiles = profiles.filter(p => p.playerName && p.playerName.trim() !== "");
    if (validProfiles.length === 0) {
      showToast("⚠️ Please enter at least one valid player nickname in the Multiplayer Roster!");
      return;
    }
  } else if (targetMode === "player" && !playerName) {
    showToast("⚠️ Please enter your exact FAF lobby nickname for player targeting!");
    inputPlayerName.focus();
    return;
  }

  const lbCount = (includeLootbox && lootbox && lootbox.enabled) ? 1 : 0;
  const totalRules = (targetMode === "multiplayer")
    ? (profiles.length + popups.length + relics.length + lbCount)
    : (Object.keys(buffs).length + limits.length + popups.length + relics.length + lbCount);

  if (totalRules === 0) {
    showToast("⚠️ No rules or profiles configured to export!");
    return;
  }

  const modName = inputModName.value.trim() || "FAF Master Overhaul";
  const author = inputAuthor.value.trim() || "User";
  const version = parseInt(inputVersion.value, 10) || 1;

  const payload = {
    modName,
    author,
    version,
    targetMode,
    playerName,
    playerProfiles: targetMode === "multiplayer" ? profiles : [],
    includeBuffs,
    includeLimits,
    includePopups,
    includeRelics,
    includeLootbox,
    unitConfigs: buffs,
    limitsRules: limits,
    popupRules: popups,
    relicObjectives: relics,
    lootboxConfig: lootbox
  };

  btnExportCombined.disabled = true;
  btnExportCombined.textContent = "⏳ Packaging Combined Mod...";
  exportFeedback.style.display = "none";

  try {
    const res = await fetch("/api/export-combined", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();

    if (result.success) {
      showToast("✅ Combined Mod packaged and installed!");
      renderExportSuccess(result);
    } else {
      showToast("❌ Export error: " + result.error);
      renderExportError(result.error);
    }
  } catch (err) {
    showToast("❌ Export failed: " + err.message);
    renderExportError(err.message);
  } finally {
    btnExportCombined.disabled = false;
    btnExportCombined.innerHTML = `🚀 Pack & Export Combined Mod (<span id="btn-combined-count">${totalRules}</span> rules)`;
  }
}

function renderExportSuccess(result) {
  exportFeedback.className = "feedback-card";
  exportFeedback.style.display = "block";

  let modeBadge = "";
  if (result.targetMode === "multiplayer") {
    modeBadge = `<span style="color: var(--accent-cyan); font-weight: 700;">👥 Multiplayer (${result.playerProfilesCount} Profiles Asymmetric)</span>`;
  } else if (result.targetMode === "player") {
    modeBadge = `<span style="color: var(--accent-gold); font-weight: 700;">👑 Specific Player (${result.playerName})</span>`;
  } else {
    modeBadge = `<span style="color: var(--accent-cyan); font-weight: 700;">🌐 Global (All Players)</span>`;
  }

  exportFeedback.innerHTML = `
    <h4>🎉 Combined Master Mod Ready!</h4>
    <p><strong>${result.modName}</strong> (v${inputVersion.value})</p>
    <p>Target Scope: ${modeBadge} | Total Integrated: <strong>${result.totalRules}</strong></p>

    <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 6px; line-height: 1.5;">
      ${result.breakdownSummary}
    </div>

    <div style="margin-top: 10px;">
      <span style="font-size: 0.72rem; color: var(--text-muted);">Installed to Game Mods:</span>
      <div class="feedback-path">${result.targetModDir}</div>
    </div>

    <div style="margin-top: 6px;">
      <span style="font-size: 0.72rem; color: var(--text-muted);">Shareable Zip Archive:</span>
      <div class="feedback-path">${result.zipPath}</div>
    </div>

    <div style="margin-top: 10px; font-size: 0.72rem; color: #34d399;">
      <strong>How to play in FAF:</strong><br>
      1. Host a game in the FAF Client.<br>
      2. Click <strong>Options / Mods</strong> in the lobby.<br>
      3. Enable <strong>"${result.modName}"</strong>.<br>
      4. Each player receives their unique profile multipliers, limits, and rules automatically!
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
