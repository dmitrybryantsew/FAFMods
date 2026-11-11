/**
 * FAF Mod Forge - Surprise Casino & Lootbox Engine Client Script
 * Handles live slot machine simulation, drop table configuration, presets, and export.
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const totalOutcomesCount = document.getElementById("total-outcomes-count");
  const dropItemsCount = document.getElementById("drop-items-count");
  const dropTableContainer = document.getElementById("drop-table-container");
  const oddsBreakdownContainer = document.getElementById("odds-breakdown-container");

  // Simulator Elements
  const btnSimSpin = document.getElementById("btn-sim-spin");
  const reel1 = document.getElementById("reel-1");
  const reel2 = document.getElementById("reel-2");
  const reel3 = document.getElementById("reel-3");
  const reelIcon1 = document.getElementById("reel-icon-1");
  const reelIcon2 = document.getElementById("reel-icon-2");
  const reelIcon3 = document.getElementById("reel-icon-3");
  const reelLabel1 = document.getElementById("reel-label-1");
  const reelLabel2 = document.getElementById("reel-label-2");
  const reelLabel3 = document.getElementById("reel-label-3");
  const slotResultTitle = document.getElementById("slot-result-title");
  const slotResultDesc = document.getElementById("slot-result-desc");
  const simStatusBadge = document.getElementById("sim-status-badge");

  // Vault Settings Elements
  const inputLootboxName = document.getElementById("lootbox-name");
  const selectLootboxModel = document.getElementById("lootbox-model");
  const inputSpawnDelay = document.getElementById("lootbox-spawn-delay");
  const inputSpawnCount = document.getElementById("lootbox-spawn-count");
  const selectLocMode = document.getElementById("lootbox-loc-mode");
  const groupCustomCoords = document.getElementById("group-custom-coords");
  const inputCustomX = document.getElementById("lootbox-custom-x");
  const inputCustomZ = document.getElementById("lootbox-custom-z");
  const selectClaimMode = document.getElementById("lootbox-claim-mode");
  const selectRespawnMode = document.getElementById("lootbox-respawn-mode");
  const inputCooldown = document.getElementById("lootbox-cooldown");
  const inputCostEnergy = document.getElementById("lootbox-cost-energy");
  const inputCostMass = document.getElementById("lootbox-cost-mass");
  const selectOpenMode = document.getElementById("lootbox-open-mode");
  const inputObserverGmName = document.getElementById("observer-gm-name");
  const checkObserverGmPlacement = document.getElementById("observer-gm-placement");

  // Custom Drop Form
  const btnToggleAddDrop = document.getElementById("btn-toggle-add-drop");
  const formAddDrop = document.getElementById("form-add-drop");
  const btnCancelAddDrop = document.getElementById("btn-cancel-add-drop");
  const btnSaveCustomDrop = document.getElementById("btn-save-custom-drop");
  const selectDropType = document.getElementById("drop-type");
  const rowUnitConfig = document.getElementById("row-unit-config");
  const rowResourceConfig = document.getElementById("row-resource-config");
  const inputDropName = document.getElementById("drop-name");
  const inputDropUnitId = document.getElementById("drop-unit-id");
  const inputDropUnitCount = document.getElementById("drop-unit-count");
  const inputDropMass = document.getElementById("drop-mass");
  const inputDropEnergy = document.getElementById("drop-energy");
  const selectDropRarity = document.getElementById("drop-rarity");
  const inputDropWeight = document.getElementById("drop-weight");
  const inputDropReels = document.getElementById("drop-reels");
  const inputDropDesc = document.getElementById("drop-desc");

  // Sidebar / Metadata Elements
  const inputModName = document.getElementById("input-mod-name");
  const inputAuthor = document.getElementById("input-author");
  const inputVersion = document.getElementById("input-version");
  const inputPlayerName = document.getElementById("input-player-name");
  const groupPlayerName = document.getElementById("group-player-name");
  const scopeRadios = document.querySelectorAll('input[name="scope-mode"]');
  const btnExportLootbox = document.getElementById("btn-export-lootbox");
  const exportFeedback = document.getElementById("export-feedback");
  const btnOpenFolder = document.getElementById("btn-open-folder");

  // Presets
  const btnPresetPrototype = document.getElementById("btn-preset-prototype");
  const btnPresetSwarm = document.getElementById("btn-preset-swarm");
  const btnPresetSupply = document.getElementById("btn-preset-supply");
  const btnPresetMotherlode = document.getElementById("btn-preset-motherlode");
  const btnPresetHighroller = document.getElementById("btn-preset-highroller");
  const btnPresetAnarchy = document.getElementById("btn-preset-anarchy");
  const btnResetDefault = document.getElementById("btn-reset-default");

  // State
  let lootboxConfig = ForgeStore.getLootbox() || ForgeStore.DEFAULT_LOOTBOX;
  let modMeta = ForgeStore.getModMeta();

  // Initialize UI Values
  function initFormValues() {
    inputLootboxName.value = lootboxConfig.name || "Quantum Surprise Vault";
    selectLootboxModel.value = lootboxConfig.modelBpId || "uec1904";
    inputSpawnDelay.value = lootboxConfig.spawnDelay !== undefined ? lootboxConfig.spawnDelay : 30;
    inputSpawnCount.value = lootboxConfig.spawnCount || 2;
    selectLocMode.value = lootboxConfig.locMode || "center";
    inputCustomX.value = lootboxConfig.customX || 256;
    inputCustomZ.value = lootboxConfig.customZ || 256;
    groupCustomCoords.style.display = selectLocMode.value === "coords" ? "flex" : "none";

    selectClaimMode.value = lootboxConfig.claimMode || "both";
    selectRespawnMode.value = lootboxConfig.respawnMode || (lootboxConfig.openMode === "instant_crack" ? "single_use" : "reusable");
    inputCooldown.value = lootboxConfig.cooldownSec || 60;
    inputCostEnergy.value = lootboxConfig.spinCostEnergy || 500;
    inputCostMass.value = lootboxConfig.spinCostMass || 0;
    if (selectOpenMode) selectOpenMode.value = lootboxConfig.openMode || "instant_crack";
    if (inputObserverGmName) inputObserverGmName.value = lootboxConfig.observerGmName || "DrReed";
    if (checkObserverGmPlacement) checkObserverGmPlacement.checked = lootboxConfig.observerGmPlacement !== false;

    // Mod Metadata
    inputModName.value = modMeta.modName || "Surprise Casino Lootbox";
    inputAuthor.value = modMeta.author || "User";
    inputVersion.value = modMeta.version || 1;
    inputPlayerName.value = modMeta.playerName || "Taily";

    const targetMode = modMeta.targetMode || "player";
    scopeRadios.forEach(r => {
      r.checked = (r.value === targetMode);
    });
    groupPlayerName.style.display = targetMode === "player" ? "block" : "none";
  }

  // Save Config
  function saveState() {
    lootboxConfig.name = inputLootboxName.value.trim() || "Quantum Surprise Vault";
    lootboxConfig.modelBpId = selectLootboxModel.value;
    lootboxConfig.spawnDelay = parseInt(inputSpawnDelay.value, 10) || 0;
    lootboxConfig.spawnCount = parseInt(inputSpawnCount.value, 10) || 1;
    lootboxConfig.locMode = selectLocMode.value;
    lootboxConfig.customX = parseFloat(inputCustomX.value) || 256;
    lootboxConfig.customZ = parseFloat(inputCustomZ.value) || 256;
    lootboxConfig.claimMode = selectClaimMode.value;
    lootboxConfig.respawnMode = selectRespawnMode.value;
    lootboxConfig.cooldownSec = parseInt(inputCooldown.value, 10) || 60;
    lootboxConfig.spinCostEnergy = parseInt(inputCostEnergy.value, 10) || 0;
    lootboxConfig.spinCostMass = parseInt(inputCostMass.value, 10) || 0;
    if (selectOpenMode) lootboxConfig.openMode = selectOpenMode.value;
    if (inputObserverGmName) lootboxConfig.observerGmName = inputObserverGmName.value.trim() || "DrReed";
    if (checkObserverGmPlacement) lootboxConfig.observerGmPlacement = checkObserverGmPlacement.checked;

    ForgeStore.setLootbox(lootboxConfig);
    renderDropTable();
  }

  function saveMeta() {
    const selectedScope = document.querySelector('input[name="scope-mode"]:checked')?.value || "player";
    modMeta = {
      modName: inputModName.value.trim() || "Surprise Casino Lootbox",
      author: inputAuthor.value.trim() || "User",
      version: parseInt(inputVersion.value, 10) || 1,
      targetMode: selectedScope,
      playerName: inputPlayerName.value.trim() || "Taily"
    };
    ForgeStore.setModMeta(modMeta);
  }

  // Render Drop Table & Odds
  function renderDropTable() {
    const table = lootboxConfig.dropTable || [];
    totalOutcomesCount.textContent = `${table.length} Outcomes`;
    dropItemsCount.textContent = table.length;

    const totalWeight = table.reduce((sum, item) => sum + (parseInt(item.weight, 10) || 0), 0);

    // Drop table list
    dropTableContainer.innerHTML = "";
    table.forEach((item, index) => {
      const weight = parseInt(item.weight, 10) || 0;
      const pct = totalWeight > 0 ? ((weight / totalWeight) * 100).toFixed(1) : 0;
      const rarity = item.rarity || "common";

      const card = document.createElement("div");
      card.className = "drop-item-card";

      const reelDisplay = (item.reels && Array.isArray(item.reels)) ? item.reels.join(" ") : (item.reels || "🎲");

      card.innerHTML = `
        <div class="drop-item-left">
          <div class="drop-item-reels">${reelDisplay}</div>
          <div class="drop-item-info">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="drop-item-name">${item.name}</span>
              <span class="rarity-badge rarity-${rarity}">${rarity}</span>
            </div>
            <div class="drop-item-desc">${item.desc || getAutoDesc(item)}</div>
          </div>
        </div>
        <div class="drop-item-right">
          <div class="drop-weight-box">
            <div><span class="drop-weight-val">${pct}%</span> Odds</div>
            <div style="font-size: 0.68rem; color: #64748b;">Weight: ${weight}</div>
          </div>
          <button class="btn btn-sm btn-ghost btn-delete-drop" data-index="${index}" title="Remove outcome" style="color: #ef4444; font-size: 1rem; padding: 4px 8px;">✕</button>
        </div>
      `;
      dropTableContainer.appendChild(card);
    });

    // Delete buttons
    document.querySelectorAll(".btn-delete-drop").forEach(btn => {
      btn.addEventListener("click", e => {
        const idx = parseInt(e.currentTarget.getAttribute("data-index"), 10);
        if (lootboxConfig.dropTable.length <= 1) {
          showToast("Drop table must have at least one outcome!");
          return;
        }
        lootboxConfig.dropTable.splice(idx, 1);
        saveState();
        showToast("Outcome removed.");
      });
    });

    // Sidebar Odds Breakdown
    oddsBreakdownContainer.innerHTML = "";
    table.forEach(item => {
      const weight = parseInt(item.weight, 10) || 0;
      const pct = totalWeight > 0 ? ((weight / totalWeight) * 100).toFixed(1) : 0;
      const row = document.createElement("div");
      row.style.display = "flex";
      row.style.justifyContent = "space-between";
      row.style.alignItems = "center";
      row.style.padding = "6px 0";
      row.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
      row.style.fontSize = "0.78rem";

      row.innerHTML = `
        <div style="display: flex; align-items: center; gap: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 190px;">
          <span>${(item.reels && item.reels[0]) || "🎲"}</span>
          <span style="color: #fff;">${item.name}</span>
        </div>
        <div style="font-weight: 700; color: #ffd700;">${pct}%</div>
      `;
      oddsBreakdownContainer.appendChild(row);
    });
  }

  function getAutoDesc(item) {
    if (item.type === "spawn_unit") {
      return `Spawns ${item.unitCount || 1}x ${item.unitId} near vault.`;
    } else if (item.type === "spawn_structure") {
      return `Spawns defensive structure ${item.unitId} under player control.`;
    } else if (item.type === "spawn_hostile") {
      return `TRAP! Spawns ${item.unitCount || 1}x hostile civilian rogue ${item.unitId} enemies!`;
    } else if (item.type === "give_resources") {
      return `Awards +${item.mass || 0} Mass and +${item.energy || 0} Energy.`;
    } else if (item.type === "take_resources") {
      return `Drains -${item.massDrain || 0} Mass and -${item.energyDrain || 0} Energy.`;
    } else if (item.type === "explosion_trap") {
      return `Booby trap detonate with kinetic shockwave damage!`;
    }
    return "";
  }

  // Interactive Live Casino Simulator
  let isSpinning = false;
  const ICONS_POOL = ["🌟", "💎", "⚡", "💀", "🪙", "🛡️", "💸", "💥", "🚀"];

  function simulateCasinoSpin() {
    if (isSpinning) return;
    const table = lootboxConfig.dropTable || [];
    if (table.length === 0) {
      showToast("Drop table is empty!");
      return;
    }

    const totalWeight = table.reduce((sum, item) => sum + (parseInt(item.weight, 10) || 0), 0);
    let rand = Math.random() * totalWeight;
    let selectedOutcome = table[0];

    for (let item of table) {
      const w = parseInt(item.weight, 10) || 0;
      if (rand <= w) {
        selectedOutcome = item;
        break;
      }
      rand -= w;
    }

    isSpinning = true;
    simStatusBadge.textContent = "SPINNING...";
    simStatusBadge.className = "rarity-badge rarity-rare";
    btnSimSpin.disabled = true;

    reel1.classList.add("spinning");
    reel2.classList.add("spinning");
    reel3.classList.add("spinning");

    slotResultTitle.textContent = "Rolling the quantum reels...";
    slotResultTitle.style.color = "#c084fc";
    slotResultDesc.textContent = "Simulating server-side deterministic roll...";

    // Rapid spinning animation
    const spinInterval = setInterval(() => {
      reelIcon1.textContent = ICONS_POOL[Math.floor(Math.random() * ICONS_POOL.length)];
      reelIcon2.textContent = ICONS_POOL[Math.floor(Math.random() * ICONS_POOL.length)];
      reelIcon3.textContent = ICONS_POOL[Math.floor(Math.random() * ICONS_POOL.length)];
    }, 60);

    const targetReels = (selectedOutcome.reels && Array.isArray(selectedOutcome.reels))
      ? selectedOutcome.reels
      : [selectedOutcome.reels || "🎲", selectedOutcome.reels || "🎲", selectedOutcome.reels || "🎲"];

    // Reel 1 stop
    setTimeout(() => {
      reel1.classList.remove("spinning");
      reelIcon1.textContent = targetReels[0] || "🌟";
      reelLabel1.textContent = selectedOutcome.rarity.toUpperCase();
    }, 900);

    // Reel 2 stop
    setTimeout(() => {
      reel2.classList.remove("spinning");
      reelIcon2.textContent = targetReels[1] || targetReels[0] || "🌟";
      reelLabel2.textContent = selectedOutcome.rarity.toUpperCase();
    }, 1500);

    // Reel 3 stop & Reveal
    setTimeout(() => {
      clearInterval(spinInterval);
      reel3.classList.remove("spinning");
      reelIcon3.textContent = targetReels[2] || targetReels[0] || "🌟";
      reelLabel3.textContent = selectedOutcome.rarity.toUpperCase();

      isSpinning = false;
      btnSimSpin.disabled = false;
      simStatusBadge.textContent = selectedOutcome.rarity.toUpperCase();
      simStatusBadge.className = `rarity-badge rarity-${selectedOutcome.rarity}`;

      // Styling based on outcome
      let titleColor = "#ffd700";
      if (selectedOutcome.rarity === "disaster") titleColor = "#ef4444";
      else if (selectedOutcome.rarity === "unlucky") titleColor = "#f97316";
      else if (selectedOutcome.rarity === "common") titleColor = "#22d3ee";

      slotResultTitle.textContent = `🎉 RESULT: ${selectedOutcome.name}!`;
      slotResultTitle.style.color = titleColor;
      slotResultDesc.textContent = selectedOutcome.desc || getAutoDesc(selectedOutcome);
    }, 2100);
  }

  btnSimSpin.addEventListener("click", simulateCasinoSpin);

  // Field change events
  [
    inputLootboxName, selectLootboxModel, inputSpawnDelay, inputSpawnCount,
    selectLocMode, inputCustomX, inputCustomZ, selectClaimMode,
    selectRespawnMode, inputCooldown, inputCostEnergy, inputCostMass,
    selectOpenMode, inputObserverGmName, checkObserverGmPlacement
  ].filter(Boolean).forEach(el => {
    el.addEventListener("change", saveState);
  });

  selectLocMode.addEventListener("change", () => {
    groupCustomCoords.style.display = selectLocMode.value === "coords" ? "flex" : "none";
    saveState();
  });

  [inputModName, inputAuthor, inputVersion, inputPlayerName].forEach(el => {
    el.addEventListener("input", saveMeta);
  });

  scopeRadios.forEach(r => {
    r.addEventListener("change", () => {
      groupPlayerName.style.display = r.value === "player" ? "block" : "none";
      saveMeta();
    });
  });

  // Custom Drop Form Handlers
  btnToggleAddDrop.addEventListener("click", () => {
    formAddDrop.style.display = formAddDrop.style.display === "none" ? "block" : "none";
    if (formAddDrop.style.display === "block") {
      formAddDrop.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  });

  btnCancelAddDrop.addEventListener("click", () => {
    formAddDrop.style.display = "none";
  });

  selectDropType.addEventListener("change", () => {
    const t = selectDropType.value;
    const isUnit = (t === "spawn_unit" || t === "spawn_structure" || t === "spawn_hostile");
    const isResource = (t === "give_resources" || t === "take_resources");

    rowUnitConfig.style.display = isUnit ? "flex" : "none";
    rowResourceConfig.style.display = isResource ? "flex" : "none";

    // Adjust defaults
    if (t === "spawn_hostile") {
      selectDropRarity.value = "disaster";
      inputDropReels.value = "💀";
      inputDropUnitId.value = "url0303";
      inputDropDesc.value = "TRAP! Spawns hostile civilian combat mechs!";
    } else if (t === "take_resources") {
      selectDropRarity.value = "unlucky";
      inputDropReels.value = "💸";
      inputDropDesc.value = "Hacker syndicate drained your resource grid!";
    } else if (t === "give_resources") {
      selectDropRarity.value = "rare";
      inputDropReels.value = "🪙";
      inputDropDesc.value = "Jackpot! Massive resource delivery.";
    } else if (t === "explosion_trap") {
      selectDropRarity.value = "disaster";
      inputDropReels.value = "💥";
      inputDropDesc.value = "Detonated booby trap kinetic explosion!";
    } else {
      selectDropRarity.value = "rare";
      inputDropReels.value = "💎";
    }
  });

  btnSaveCustomDrop.addEventListener("click", () => {
    const name = inputDropName.value.trim();
    if (!name) {
      showToast("Please enter an outcome name.");
      return;
    }

    const type = selectDropType.value;
    const rarity = selectDropRarity.value;
    const weight = parseInt(inputDropWeight.value, 10) || 50;
    const icon = inputDropReels.value.trim() || "🎲";
    const desc = inputDropDesc.value.trim();

    const newDrop = {
      id: "custom_" + Date.now(),
      name: name,
      type: type,
      rarity: rarity,
      weight: weight,
      reels: [icon, icon, icon],
      desc: desc
    };

    if (type === "spawn_unit" || type === "spawn_structure" || type === "spawn_hostile") {
      newDrop.unitId = inputDropUnitId.value.trim().toLowerCase() || "uel0202";
      newDrop.unitCount = parseInt(inputDropUnitCount.value, 10) || 1;
    } else if (type === "give_resources") {
      newDrop.mass = parseInt(inputDropMass.value, 10) || 0;
      newDrop.energy = parseInt(inputDropEnergy.value, 10) || 0;
    } else if (type === "take_resources") {
      newDrop.massDrain = parseInt(inputDropMass.value, 10) || 0;
      newDrop.energyDrain = parseInt(inputDropEnergy.value, 10) || 0;
    }

    lootboxConfig.dropTable.push(newDrop);
    saveState();
    formAddDrop.style.display = "none";
    inputDropName.value = "";
    showToast(`Added '${name}' to drop table!`);
  });

  // Presets Handlers
  if (btnPresetPrototype) {
    btnPresetPrototype.addEventListener("click", () => {
      lootboxConfig.name = "Experimental Prototype Pod";
      lootboxConfig.openMode = "instant_crack";
      lootboxConfig.respawnMode = "single_use";
      lootboxConfig.dropTable = [
        {
          id: "proto_monkeylord",
          name: "🌟 Prototype Cybran Monkeylord (T4)",
          type: "spawn_unit",
          rarity: "jackpot",
          weight: 70,
          unitId: "url0402",
          unitCount: 1,
          reels: ["🌟", "🌟", "🌟"],
          desc: "JACKPOT! Unlocks a fully operational Experimental Spider Bot!"
        },
        {
          id: "proto_fatboy",
          name: "🌟 Prototype UEF Fatboy Mobile Factory (T4)",
          type: "spawn_unit",
          rarity: "jackpot",
          weight: 70,
          unitId: "uel0401",
          unitCount: 1,
          reels: ["🌟", "🌟", "🌟"],
          desc: "JACKPOT! Unlocks an Experimental Mobile Heavy Assault Factory!"
        },
        {
          id: "proto_colossus",
          name: "🌟 Prototype Galactic Colossus (T4)",
          type: "spawn_unit",
          rarity: "jackpot",
          weight: 70,
          unitId: "ual0401",
          unitCount: 1,
          reels: ["🌟", "🌟", "🌟"],
          desc: "JACKPOT! Unlocks a towering Aeon Experimental Assault Bot!"
        },
        {
          id: "proto_siege_squad",
          name: "💎 T3 Heavy Siege Assault Battalion",
          type: "spawn_unit",
          rarity: "rare",
          weight: 200,
          unitId: "uel0303",
          unitCount: 4,
          reels: ["💎", "💎", "💎"],
          desc: "Deploys 4 Tier 3 Heavy Siege Assault Bots!"
        },
        {
          id: "proto_sniper_squad",
          name: "💎 T3 Long-Range Sniper Bots",
          type: "spawn_unit",
          rarity: "rare",
          weight: 180,
          unitId: "xal0305",
          unitCount: 3,
          reels: ["💎", "💎", "💎"],
          desc: "Deploys 3 high-precision Tier 3 Sniper Bots!"
        },
        {
          id: "proto_mass_cache",
          name: "🪙 Classified Research Cache (+8,000 Mass)",
          type: "give_resources",
          rarity: "rare",
          weight: 200,
          mass: 8000,
          energy: 40000,
          reels: ["🪙", "🪙", "🪙"],
          desc: "Awards +8,000 Mass and +40,000 Energy research funding!"
        },
        {
          id: "proto_hostile_ambush",
          name: "💀 Rogue Prototype Defender Ambush!",
          type: "spawn_hostile",
          rarity: "disaster",
          weight: 60,
          unitId: "url0303",
          unitCount: 4,
          reels: ["💀", "💀", "💀"],
          desc: "DANGER! Automated security assault bots awakened!"
        },
        {
          id: "proto_booby_trap",
          name: "💥 Vault Core Overload Detonation",
          type: "explosion_trap",
          rarity: "disaster",
          weight: 50,
          reels: ["💥", "💥", "💥"],
          desc: "Containment breached! Vault exploded in a kinetic burst!"
        }
      ];
      saveState();
      initFormValues();
      showToast("🏆 Prototype Experimental (Capture & Run) preset loaded!");
    });
  }

  if (btnPresetSwarm) {
    btnPresetSwarm.addEventListener("click", () => {
      lootboxConfig.name = "Raptor Swarm Bio-Pod";
      lootboxConfig.openMode = "instant_crack";
      lootboxConfig.respawnMode = "single_use";
      lootboxConfig.dropTable = [
        {
          id: "swarm_queen",
          name: "👑 Awakened Matriarch Queen Titan (XRA0401)",
          type: "spawn_unit",
          rarity: "jackpot",
          weight: 50,
          unitId: "xra0401",
          unitCount: 1,
          reels: ["🌟", "🌟", "🌟"],
          desc: "LEGENDARY! The Matriarch Queen Titan awakens under your command!"
        },
        {
          id: "swarm_slashers",
          name: "🦖 Raptor Slasher Pack (XRA0201 x8)",
          type: "spawn_unit",
          rarity: "rare",
          weight: 250,
          unitId: "xra0201",
          unitCount: 8,
          reels: ["💎", "💎", "💎"],
          desc: "A lethal pack of 8 fast predatory Raptor Slashers emerges!"
        },
        {
          id: "swarm_flyers",
          name: "🦅 Winged Brood Swarm (XRA0104 x6)",
          type: "spawn_unit",
          rarity: "rare",
          weight: 200,
          unitId: "xra0104",
          unitCount: 6,
          reels: ["💎", "💎", "💎"],
          desc: "Spawns 6 airborne bio-scourge Raptor flyers!"
        },
        {
          id: "swarm_biomass",
          name: "🪙 Concentrated Biomass Cache (+6,000 Mass)",
          type: "give_resources",
          rarity: "common",
          weight: 250,
          mass: 6000,
          energy: 30000,
          reels: ["🪙", "🪙", "🪙"],
          desc: "Harvests +6,000 Mass and +30,000 Energy in organic biomass!"
        },
        {
          id: "swarm_hostile_breakout",
          name: "💀 Hostile Swarm Brood Outbreak!",
          type: "spawn_hostile",
          rarity: "disaster",
          weight: 120,
          unitId: "xra0101",
          unitCount: 12,
          reels: ["💀", "💀", "💀"],
          desc: "OUTBREAK! 12 feral wild raptors erupt and attack all nearby forces!"
        },
        {
          id: "swarm_acid_bomb",
          name: "💥 Bio-Acid Rupture Blast",
          type: "explosion_trap",
          rarity: "disaster",
          weight: 60,
          reels: ["💥", "💥", "💥"],
          desc: "Acid sac ruptured in a caustic shockwave!"
        }
      ];
      saveState();
      initFormValues();
      showToast("🦖 Raptor Swarm Bio-Pod preset loaded!");
    });
  }

  if (btnPresetMotherlode) {
    btnPresetMotherlode.addEventListener("click", () => {
      lootboxConfig.name = "Quantum Resource Motherlode";
      lootboxConfig.openMode = "instant_crack";
      lootboxConfig.respawnMode = "single_use";
      lootboxConfig.dropTable = [
        {
          id: "res_colossal",
          name: "🌟 Infinite Energy & Mass Core (+25,000 Mass)",
          type: "give_resources",
          rarity: "jackpot",
          weight: 150,
          mass: 25000,
          energy: 150000,
          reels: ["🌟", "🌟", "🌟"],
          desc: "JACKPOT! Enormous resource infusion: +25,000 Mass & +150,000 Energy!"
        },
        {
          id: "res_heavy_mass",
          name: "💎 High-Yield Titanium Mass Vault (+10,000 Mass)",
          type: "give_resources",
          rarity: "rare",
          weight: 350,
          mass: 10000,
          energy: 60000,
          reels: ["💎", "💎", "💎"],
          desc: "Injects +10,000 Mass and +60,000 Energy into your economy!"
        },
        {
          id: "res_tactical_cache",
          name: "🪙 Standard Supply Cache (+5,000 Mass)",
          type: "give_resources",
          rarity: "common",
          weight: 350,
          mass: 5000,
          energy: 30000,
          reels: ["🪙", "🪙", "🪙"],
          desc: "Awards +5,000 Mass and +30,000 Energy!"
        },
        {
          id: "res_siphon",
          name: "💸 Grid Short-Circuit Drain (-2,500 Mass)",
          type: "take_resources",
          rarity: "unlucky",
          weight: 100,
          massDrain: 2500,
          energyDrain: 30000,
          reels: ["💸", "💸", "💸"],
          desc: "Static discharge drained -2,500 Mass & -30,000 Energy!"
        },
        {
          id: "res_overload",
          name: "💥 Superheated Core Detonation",
          type: "explosion_trap",
          rarity: "disaster",
          weight: 50,
          reels: ["💥", "💥", "💥"],
          desc: "Core collapsed into a fiery plasma detonation!"
        }
      ];
      saveState();
      initFormValues();
      showToast("💎 Resource Motherlode preset loaded!");
    });
  }

  btnPresetHighroller.addEventListener("click", () => {
    lootboxConfig.dropTable = [
      {
        id: "exp_jackpot",
        name: "🌟 Grand Jackpot: Experimental War Machine",
        type: "spawn_unit",
        rarity: "jackpot",
        weight: 60,
        unitId: "uel0401",
        unitCount: 1,
        reels: ["🌟", "🌟", "🌟"],
        desc: "JACKPOT! Spawns an Experimental Mobile Factory!"
      },
      {
        id: "mass_jackpot",
        name: "🪙 Titanium Mass Vault (+15,000 Mass)",
        type: "give_resources",
        rarity: "jackpot",
        weight: 120,
        mass: 15000,
        energy: 50000,
        reels: ["🪙", "🪙", "🪙"],
        desc: "Colossal resource transfer: +15,000 Mass & +50,000 Energy!"
      },
      {
        id: "t3_titan_squad",
        name: "💎 T3 Heavy Assault Mechs",
        type: "spawn_unit",
        rarity: "rare",
        weight: 200,
        unitId: "uel0303",
        unitCount: 4,
        reels: ["💎", "💎", "💎"],
        desc: "Spawns 4 T3 Heavy Siege Assault Bots!"
      },
      {
        id: "heist_drain",
        name: "💸 Space Syndicate Robbery (-3,000 Mass)",
        type: "take_resources",
        rarity: "unlucky",
        weight: 150,
        massDrain: 3000,
        energyDrain: 40000,
        reels: ["💸", "💸", "💸"],
        desc: "Syndicate heist drained -3,000 Mass & -40,000 Energy!"
      },
      {
        id: "hostile_ambush_t3",
        name: "💀 Hostile Civilian Mercenary Ambush!",
        type: "spawn_hostile",
        rarity: "disaster",
        weight: 150,
        unitId: "url0303",
        unitCount: 4,
        reels: ["💀", "💀", "💀"],
        desc: "TRAP! 4 hostile civilian rogue assault bots attack immediately!"
      },
      {
        id: "booby_trap",
        name: "💥 Vault Overload Shockwave",
        type: "explosion_trap",
        rarity: "disaster",
        weight: 80,
        reels: ["💥", "💥", "💥"],
        desc: "Vault self-destructed with massive kinetic blast!"
      }
    ];
    saveState();
    showToast("High-Roller Jackpot preset loaded!");
  });

  btnPresetSupply.addEventListener("click", () => {
    lootboxConfig.dropTable = [
      {
        id: "sup_t2_tanks",
        name: "🛡️ T2 Heavy Armor Column",
        type: "spawn_unit",
        rarity: "common",
        weight: 300,
        unitId: "uel0202",
        unitCount: 5,
        reels: ["🛡️", "🛡️", "🛡️"],
        desc: "Spawns 5 Tier 2 Heavy Battle Tanks!"
      },
      {
        id: "sup_mass_cache",
        name: "🪙 Standard Mass Cache (+3,000)",
        type: "give_resources",
        rarity: "common",
        weight: 300,
        mass: 3000,
        energy: 20000,
        reels: ["🪙", "🪙", "🪙"],
        desc: "Replenishes +3,000 Mass and +20,000 Energy."
      },
      {
        id: "sup_gunships",
        name: "🚀 T3 Heavy Gunship Wing",
        type: "spawn_unit",
        rarity: "rare",
        weight: 150,
        unitId: "uea0305",
        unitCount: 2,
        reels: ["🚀", "🚀", "🚀"],
        desc: "Spawns 2 Tier 3 Heavy Gunships!"
      },
      {
        id: "sup_minor_drain",
        name: "💸 Pirate Smuggler Toll (-800 Mass)",
        type: "take_resources",
        rarity: "unlucky",
        weight: 100,
        massDrain: 800,
        energyDrain: 10000,
        reels: ["💸", "💸", "💸"],
        desc: "Pirates confiscated -800 Mass and -10,000 Energy."
      },
      {
        id: "sup_hostile_t1",
        name: "💀 Hostile Civilian Scout Ambush",
        type: "spawn_hostile",
        rarity: "disaster",
        weight: 80,
        unitId: "url0201",
        unitCount: 4,
        reels: ["💀", "💀", "💀"],
        desc: "Hostile civilian rogue tanks emerged from hiding!"
      }
    ];
    saveState();
    showToast("Tactical Supply Crates preset loaded!");
  });

  btnPresetAnarchy.addEventListener("click", () => {
    lootboxConfig.dropTable = [
      {
        id: "anarchy_hostile_heavy",
        name: "💀 Hostile Civilian Megamech Ambush!",
        type: "spawn_hostile",
        rarity: "disaster",
        weight: 300,
        unitId: "url0303",
        unitCount: 5,
        reels: ["💀", "💀", "💀"],
        desc: "LETHAL TRAP! 5 hostile rogue civilian bots burst out!"
      },
      {
        id: "anarchy_booby",
        name: "💥 Seismic Plasma Detonation",
        type: "explosion_trap",
        rarity: "disaster",
        weight: 250,
        reels: ["💥", "💥", "💥"],
        desc: "Crate violently detonates in a kinetic shockwave!"
      },
      {
        id: "anarchy_heist",
        name: "💸 Total Grid Blackout Drain",
        type: "take_resources",
        rarity: "unlucky",
        weight: 250,
        massDrain: 2500,
        energyDrain: 50000,
        reels: ["💸", "💸", "💸"],
        desc: "Total energy drain: -2,500 Mass and -50,000 Energy!"
      },
      {
        id: "anarchy_jackpot",
        name: "🌟 Stolen Prototype Experimental Bot",
        type: "spawn_unit",
        rarity: "jackpot",
        weight: 120,
        unitId: "url0402",
        unitCount: 1,
        reels: ["🌟", "🌟", "🌟"],
        desc: "Miracle! Survives trap and rewards a Cybran Monkeylord Spider!"
      }
    ];
    saveState();
    showToast("Anarchy & Mercenaries preset loaded!");
  });

  btnResetDefault.addEventListener("click", () => {
    lootboxConfig = JSON.parse(JSON.stringify(ForgeStore.DEFAULT_LOOTBOX));
    saveState();
    initFormValues();
    showToast("Reset to default quantum casino.");
  });

  // Export Standalone Mod
  btnExportLootbox.addEventListener("click", async () => {
    saveState();
    saveMeta();

    btnExportLootbox.disabled = true;
    btnExportLootbox.textContent = "⚙️ Packing Mod...";
    exportFeedback.style.display = "none";

    const payload = {
      modName: modMeta.modName,
      author: modMeta.author,
      version: modMeta.version,
      targetMode: modMeta.targetMode,
      playerName: modMeta.playerName,
      lootboxConfig: lootboxConfig
    };

    try {
      const res = await fetch("/api/export-lootbox", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (data.success) {
        exportFeedback.className = "feedback-card success";
        exportFeedback.style.display = "block";
        exportFeedback.innerHTML = `
          <strong>✅ Mod Successfully Deployed!</strong><br>
          Folder: <code>${data.folderName}</code><br>
          Saved directly to your FAF mods directory and ready to play!
        `;
        showToast("Casino Mod Packaged & Installed!");
      } else {
        exportFeedback.className = "feedback-card error";
        exportFeedback.style.display = "block";
        exportFeedback.textContent = "Error: " + (data.error || "Failed to export mod.");
      }
    } catch (err) {
      exportFeedback.className = "feedback-card error";
      exportFeedback.style.display = "block";
      exportFeedback.textContent = "Request failed: " + err.message;
    } finally {
      btnExportLootbox.disabled = false;
      btnExportLootbox.textContent = "🚀 Pack & Export Casino Mod";
    }
  });

  btnOpenFolder.addEventListener("click", async () => {
    try {
      await fetch("/api/open-folder", { method: "POST" });
    } catch (e) {
      console.warn(e);
    }
  });

  function showToast(msg) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = msg;
    toast.className = "toast show";
    setTimeout(() => {
      toast.className = "toast";
    }, 2500);
  }

  // Initial render
  initFormValues();
  renderDropTable();
});
