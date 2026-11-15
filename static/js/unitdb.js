/**
 * FAF Unit Database & Raptor Swarm Roster
 * Client controller for browsing unit catalogs, filtering factions and tiers,
 * and comparing units side-by-side with full FAF blueprint metrics.
 */

(function () {
  'use strict';

  // --- State ---
  let allUnits = [];
  let raptorUnits = [];
  let selectedUnitIds = new Set();
  let activeInspectedId = null;
  let currentView = 'grid'; // 'grid' | 'compare' | 'agent'

  const filters = {
    search: '',
    faction: 'ALL',
    tech: 'ALL',
    utype: 'ALL'
  };

  const FACTIONS = [
    { key: 'UEF', name: 'UEF', color: '#2d78b2', icon: '/textures/ui/common/faction_icon-sm/uef_ico.png' },
    { key: 'Cybran', name: 'Cybran', color: '#df2d0e', icon: '/textures/ui/common/faction_icon-sm/cybran_ico.png' },
    { key: 'Aeon', name: 'Aeon', color: '#0a9d2f', icon: '/textures/ui/common/faction_icon-sm/aeon_ico.png' },
    { key: 'Seraphim', name: 'Seraphim', color: '#d4a017', icon: '/textures/ui/common/faction_icon-sm/seraphim_ico.png' },
    { key: 'Nomads', name: 'Nomads', color: '#e17d23', icon: '/textures/ui/common/faction_icon-sm/nomads_ico.png' },
    { key: 'Raptor', name: 'Raptor Swarm', color: '#ff4d00', icon: '/static/img/raptor_ico.png' }
  ];

  const TIERS = ['T1', 'T2', 'T3', 'EXP'];

  // DOM Elements
  const containerEl = document.getElementById('unitdb-main-container');
  const searchInput = document.getElementById('unitdb-search');
  const compareCountEl = document.getElementById('compare-count-display');
  const btnCompareAction = document.getElementById('btn-compare-action');
  const btnClearSelection = document.getElementById('btn-clear-selection');
  const totalUnitsBadge = document.getElementById('total-units-badge');
  const raptorUnitsBadge = document.getElementById('raptor-units-badge');
  const modePills = document.querySelectorAll('.mode-pill');

  // --- Initialization ---
  async function init() {
    setupEventListeners();
    readUrlParams();
    await loadUnitData();
    applyState();
  }

  function setupEventListeners() {
    // Search
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        filters.search = e.target.value.toLowerCase().trim();
        renderActiveView();
      });
    }

    // Compare button in sidebar
    if (btnCompareAction) {
      btnCompareAction.addEventListener('click', () => {
        if (selectedUnitIds.size > 0 || activeInspectedId) {
          switchView('compare');
        }
      });
    }

    // Clear selection
    if (btnClearSelection) {
      btnClearSelection.addEventListener('click', () => {
        selectedUnitIds.clear();
        updateCompareCounters();
        renderActiveView();
      });
    }

    // View mode pills
    modePills.forEach((pill) => {
      pill.addEventListener('click', () => {
        const mode = pill.dataset.mode;
        switchView(mode);
      });
    });

    // Faction & Type & Tech Filter buttons
    document.querySelectorAll('.filter-btn[data-filter]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const type = btn.dataset.filter;
        const val = btn.dataset.val;

        // Toggle active state in group
        const group = btn.closest('.sidebar-button-group');
        if (group) {
          group.querySelectorAll('.filter-btn').forEach((b) => b.classList.remove('active'));
          btn.classList.add('active');
        }

        filters[type] = val;
        renderActiveView();
      });
    });

    // Quick Presets
    document.querySelectorAll('.preset-chip[data-preset]').forEach((chip) => {
      chip.addEventListener('click', () => {
        applyPreset(chip.dataset.preset);
      });
    });
  }

  function readUrlParams() {
    const params = new URLSearchParams(window.location.search);
    if (params.has('faction')) filters.faction = params.get('faction');
    if (params.has('tier')) filters.tech = params.get('tier');
    if (params.has('type')) filters.utype = params.get('type');
    if (params.has('view')) currentView = params.get('view');
    if (params.has('unit')) {
      const u = params.get('unit').toUpperCase();
      selectedUnitIds.add(u);
      activeInspectedId = u;
      currentView = 'compare';
    }
    if (params.has('compare')) {
      params.get('compare').split(',').forEach((id) => {
        const clean = id.trim().toUpperCase();
        if (clean) selectedUnitIds.add(clean);
      });
      currentView = 'compare';
    }
  }

  async function loadUnitData() {
    try {
      // 1. Fetch Raptor units first (guaranteed complete with weapons and stats)
      const raptorRes = await fetch('/api/raptors');
      if (raptorRes.ok) {
        raptorUnits = await raptorRes.json();
      }
    } catch (err) {
      console.warn('Could not load /api/raptors, will rely on /api/unitdb', err);
    }

    try {
      // 2. Fetch full unitdb catalog (FAF units + Raptor units)
      const fullRes = await fetch('/api/unitdb');
      if (fullRes.ok) {
        allUnits = await fullRes.json();
      } else {
        // Fallback: fetch /api/units
        const unitsRes = await fetch('/api/units');
        if (unitsRes.ok) {
          allUnits = await unitsRes.json();
        }
      }
    } catch (err) {
      console.error('Error fetching unit database:', err);
      allUnits = raptorUnits;
    }

    // Ensure Raptor units are indexed and merged
    if (raptorUnits.length > 0 && !allUnits.some((u) => u.id === 'XRA0401')) {
      allUnits = allUnits.concat(raptorUnits);
    }

    if (totalUnitsBadge) totalUnitsBadge.textContent = allUnits.length;
    if (raptorUnitsBadge) raptorUnitsBadge.textContent = raptorUnits.length || 31;
    updateSidebarCounts();
  }

  function updateSidebarCounts() {
    document.querySelectorAll('.filter-btn[data-filter="faction"]').forEach((btn) => {
      const f = btn.dataset.val;
      const countEl = btn.querySelector('.filter-count');
      if (countEl) {
        if (f === 'ALL') {
          countEl.textContent = allUnits.length;
        } else {
          const count = allUnits.filter((u) => (u.faction || '').toLowerCase() === f.toLowerCase()).length;
          countEl.textContent = count;
        }
      }
    });
  }

  function applyPreset(preset) {
    if (preset === 'raptors-all') {
      filters.faction = 'Raptor';
      filters.tech = 'ALL';
      filters.utype = 'ALL';
      filters.search = '';
      currentView = 'grid';
    } else if (preset === 'raptors-land') {
      filters.faction = 'Raptor';
      filters.utype = 'LAND';
      filters.tech = 'ALL';
      filters.search = '';
      currentView = 'grid';
    } else if (preset === 'raptors-air') {
      filters.faction = 'Raptor';
      filters.utype = 'AIR';
      filters.tech = 'ALL';
      filters.search = '';
      currentView = 'grid';
    } else if (preset === 'raptors-artillery') {
      filters.faction = 'Raptor';
      filters.search = 'spire';
      filters.tech = 'ALL';
      filters.utype = 'ALL';
      currentView = 'grid';
    } else if (preset === 'compare-queens') {
      // Compare Queen Titan vs Galactic Colossus vs Monkeylord vs Fatboy
      selectedUnitIds.clear();
      ['XRA0401', 'UAL0401', 'URL0402', 'UEL0401'].forEach((id) => selectedUnitIds.add(id));
      currentView = 'compare';
    } else if (preset === 'compare-swarmer') {
      // Compare Raptor Swarmer vs Cybran Mantis vs UEF Striker vs Aeon Aurora
      selectedUnitIds.clear();
      ['XRA0101', 'URL0106', 'UEL0201', 'UAL0201'].forEach((id) => selectedUnitIds.add(id));
      currentView = 'compare';
    }
    applyState();
  }

  function switchView(viewName) {
    currentView = viewName;
    modePills.forEach((p) => {
      p.classList.toggle('active', p.dataset.mode === viewName);
    });
    renderActiveView();
  }

  function applyState() {
    modePills.forEach((p) => {
      p.classList.toggle('active', p.dataset.mode === currentView);
    });

    // Update active filter buttons
    document.querySelectorAll('.filter-btn[data-filter="faction"]').forEach((b) => {
      b.classList.toggle('active', b.dataset.val.toLowerCase() === filters.faction.toLowerCase());
    });
    document.querySelectorAll('.filter-btn[data-filter="tech"]').forEach((b) => {
      b.classList.toggle('active', b.dataset.val === filters.tech);
    });
    document.querySelectorAll('.filter-btn[data-filter="utype"]').forEach((b) => {
      b.classList.toggle('active', b.dataset.val === filters.utype);
    });

    updateCompareCounters();
    renderActiveView();
  }

  function updateCompareCounters() {
    const count = selectedUnitIds.size;
    if (compareCountEl) compareCountEl.textContent = count;
    if (btnCompareAction) {
      btnCompareAction.disabled = (count === 0 && !activeInspectedId);
      btnCompareAction.innerHTML = `⚡ Compare (${count})`;
    }
  }

  function renderActiveView() {
    if (!containerEl) return;
    if (currentView === 'grid') {
      renderGridView();
    } else if (currentView === 'compare') {
      renderCompareView();
    } else if (currentView === 'agent') {
      renderAgentView();
    }
  }

  // Filter unit helper
  function matchesFilter(u) {
    if (filters.faction !== 'ALL' && (u.faction || '').toLowerCase() !== filters.faction.toLowerCase()) {
      return false;
    }
    if (filters.tech !== 'ALL' && (u.tech || '') !== filters.tech) {
      return false;
    }
    if (filters.utype !== 'ALL' && (u.type || '') !== filters.utype) {
      return false;
    }
    if (filters.search) {
      const q = filters.search;
      const idMatch = (u.id || '').toLowerCase().includes(q);
      const nameMatch = (u.name || '').toLowerCase().includes(q);
      const descMatch = (u.description || u.desc || '').toLowerCase().includes(q);
      const roleMatch = (u.role || '').toLowerCase().includes(q);
      if (!idMatch && !nameMatch && !descMatch && !roleMatch) return false;
    }
    return true;
  }

  // ==========================================================================
  // RENDER GRID VIEW (Image 1 Layout)
  // ==========================================================================
  function renderGridView() {
    const visibleFactions = filters.faction === 'ALL'
      ? FACTIONS
      : FACTIONS.filter((f) => f.key.toLowerCase() === filters.faction.toLowerCase());

    let html = `<div class="factions-grid-container">`;

    visibleFactions.forEach((fac) => {
      const facUnits = allUnits.filter((u) => (u.faction || '').toLowerCase() === fac.key.toLowerCase() && matchesFilter(u));

      html += `
        <div class="faction-column ${fac.key.toLowerCase()}">
          <div class="faction-header">
            <img class="f-icon" src="${fac.icon}" alt="${fac.name}" onerror="this.style.display='none'">
            <span>${fac.name} (${facUnits.length})</span>
          </div>
      `;

      // Group by Tier
      TIERS.forEach((tier) => {
        const tierUnits = facUnits.filter((u) => u.tech === tier);
        if (tierUnits.length === 0 && filters.tech !== 'ALL' && filters.tech !== tier) return;

        const pipCount = tier === 'T1' ? 1 : tier === 'T2' ? 2 : tier === 'T3' ? 3 : 4;
        let pipsHtml = `<div class="tier-pips ${tier.toLowerCase()}">`;
        for (let i = 0; i < (tier === 'EXP' ? 1 : pipCount); i++) {
          pipsHtml += `<div class="tier-pip"></div>`;
        }
        pipsHtml += `</div>`;

        html += `
          <div class="tier-section">
            <div class="tier-section-title">
              ${pipsHtml}
              <span>${tier === 'EXP' ? 'Experimental (T4)' : tier} (${tierUnits.length})</span>
            </div>
            <div class="units-subgrid">
        `;

        tierUnits.forEach((u) => {
          const isSelected = selectedUnitIds.has(u.id);
          const isInspecting = activeInspectedId === u.id;

          // Icon resolution
          let iconUrl = u.icon || `/static/img/units/${u.id.toLowerCase()}.png`;

          html += `
            <div class="unit-thumb ${isSelected ? 'selected' : ''} ${isInspecting ? 'inspecting' : ''}" 
                 data-id="${u.id}" 
                 title="${u.name} [${u.id}]\nHP: ${u.stats?.health || u.hp || 0} | Mass: ${u.stats?.mass || u.mass || 0}\n${u.role || u.description || ''}">
              <img class="unit-thumb-img" src="${iconUrl}" alt="${u.id}" onerror="this.src='/static/img/units/xra0101.png'">
              <span class="tier-badge">${u.tech}</span>
              <div class="thumb-checkbox" data-checkbox-id="${u.id}">✓</div>
            </div>
          `;
        });

        html += `
            </div>
          </div>
        `;
      });

      html += `</div>`;
    });

    html += `</div>`;
    containerEl.innerHTML = html;

    // Attach click events on thumbnails
    containerEl.querySelectorAll('.unit-thumb').forEach((thumb) => {
      const uid = thumb.dataset.id;

      // Click on checkbox directly toggles selection
      const cb = thumb.querySelector('.thumb-checkbox');
      cb.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleUnitSelection(uid);
      });

      // Click on card inspects or compares
      thumb.addEventListener('click', () => {
        activeInspectedId = uid;
        if (!selectedUnitIds.has(uid)) {
          selectedUnitIds.add(uid);
        }
        updateCompareCounters();
        switchView('compare');
      });
    });
  }

  function toggleUnitSelection(unitId) {
    if (selectedUnitIds.has(unitId)) {
      selectedUnitIds.delete(unitId);
    } else {
      selectedUnitIds.add(unitId);
    }
    updateCompareCounters();
    renderGridView();
  }

  // ==========================================================================
  // RENDER COMPARE VIEW (Image 2 Layout)
  // ==========================================================================
  function renderCompareView() {
    let compareIds = Array.from(selectedUnitIds);

    // If none selected, fallback to active inspected or sample comparison
    if (compareIds.length === 0) {
      if (activeInspectedId) {
        compareIds = [activeInspectedId];
      } else {
        compareIds = ['XRA0401', 'XRA0101', 'UEL0201'];
      }
    }

    const unitsToCompare = compareIds
      .map((id) => allUnits.find((u) => u.id === id) || raptorUnits.find((u) => u.id === id))
      .filter(Boolean);

    let html = `
      <div class="compare-view-container">
        <div class="compare-top-actions">
          <div class="compare-title-heading">
            <span>⚡ FAF Unit Comparator (${unitsToCompare.length} Units Active)</span>
          </div>
          <div style="display:flex; gap:10px; align-items:center;">
            <button class="btn-clear-selection" id="btn-back-to-grid" style="font-size:12px; color:#38bdf8; text-decoration:none; cursor:pointer;">
              ← Back to Grid View
            </button>
            <button class="preset-chip" id="btn-add-unit-dialog">
              + Add Unit to Compare
            </button>
          </div>
        </div>

        <div class="compare-cards-wrapper">
    `;

    unitsToCompare.forEach((u) => {
      html += renderSingleUnitCard(u);
    });

    html += `
        </div>
      </div>
    `;

    containerEl.innerHTML = html;

    // Attach close button events
    containerEl.querySelectorAll('.detail-close-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const uid = btn.dataset.removeId;
        selectedUnitIds.delete(uid);
        if (activeInspectedId === uid) activeInspectedId = null;
        updateCompareCounters();
        renderCompareView();
      });
    });

    // Back to grid
    const btnBack = document.getElementById('btn-back-to-grid');
    if (btnBack) {
      btnBack.addEventListener('click', () => switchView('grid'));
    }

    // Add unit dialog
    const btnAdd = document.getElementById('btn-add-unit-dialog');
    if (btnAdd) {
      btnAdd.addEventListener('click', promptAddUnit);
    }
  }

  function promptAddUnit() {
    const search = prompt('Enter Unit ID to add to comparison (e.g. XRA0401, XRA0101, UEL0201, UAL0401):');
    if (search) {
      const clean = search.trim().toUpperCase();
      const found = allUnits.find((u) => u.id === clean);
      if (found) {
        selectedUnitIds.add(clean);
        updateCompareCounters();
        renderCompareView();
      } else {
        alert(`Unit ID '${clean}' not found in database.`);
      }
    }
  }

  // Renders a single unit card matching Image 2
  function renderSingleUnitCard(u) {
    const s = u.stats || {};
    const hp = s.health || u.hp || 0;
    const regen = s.regen || u.regen || 0;
    const mass = s.mass || u.mass || 0;
    const energy = s.energy || u.energy || 0;
    const time = s.buildTime || u.buildTime || 0;
    const speed = s.speed || u.speed || 0;
    const turnRate = s.turnRate || u.turnRate || 0;
    const buildRate = s.buildRate || u.buildRate || 0;
    const massProd = s.massProd || u.massProd || 0;
    const energyProd = s.energyProd || u.energyProd || 0;
    const vision = s.vision || u.vision || 0;
    const waterVision = s.waterVision || vision;
    const radar = s.radar || u.radar || 0;
    const sonar = s.sonar || 0;
    const omni = s.omni || 0;
    const wreckageHp = s.wreckageHealth || Math.round(hp * 0.9);
    const wreckageMass = s.wreckageMass || Math.round(mass * 0.81);

    const factionLower = (u.faction || 'raptor').toLowerCase();
    const iconUrl = u.icon || `/static/img/units/${u.id.toLowerCase()}.png`;

    // Format numbers with k suffix if > 1000
    const fmtK = (num) => (num >= 1000 ? `${(num / 1000).toFixed(num >= 10000 ? 0 : 1)}k` : num);

    // Abilities HTML
    const abilities = u.abilities || [];
    let abilitiesHtml = abilities.length > 0
      ? abilities.map((ab) => `<span class="ability-tag ${ab.includes('Titan') || ab.includes('Kamikaze') ? 'highlight' : ''}">${ab}</span>`).join('')
      : '<span style="color:#64748b; font-style:italic;">None</span>';

    // Veterancy Table HTML
    let vetHtml = '';
    if (u.veterancy && u.veterancy.length > 0) {
      vetHtml = `
        <table class="vet-table">
          <thead>
            <tr><th>Vet</th><th>Kills</th><th>Health</th><th>Regen</th></tr>
          </thead>
          <tbody>
      `;
      u.veterancy.forEach((v) => {
        vetHtml += `
          <tr>
            <td>L${v.level}</td>
            <td>${v.kills}</td>
            <td>${fmtK(v.health)}</td>
            <td>+${v.regen}</td>
          </tr>
        `;
      });
      vetHtml += `</tbody></table>`;
    } else {
      vetHtml = `
        <table class="vet-table">
          <thead><tr><th>Vet</th><th>Health</th><th>Regen</th></tr></thead>
          <tbody>
            <tr><td>L1</td><td>+10%</td><td>+3 hp/s</td></tr>
            <tr><td>L2</td><td>+20%</td><td>+6 hp/s</td></tr>
            <tr><td>L3</td><td>+30%</td><td>+9 hp/s</td></tr>
            <tr><td>L4</td><td>+40%</td><td>+12 hp/s</td></tr>
            <tr><td>L5</td><td>+50%</td><td>+15 hp/s</td></tr>
          </tbody>
        </table>
      `;
    }

    // Weapons HTML matching Screenshot 2
    const weapons = u.weapons || [];
    let weaponsHtml = '';
    if (weapons.length > 0) {
      weapons.forEach((w) => {
        weaponsHtml += `
          <div class="weapon-block">
            <div class="weapon-title-bar">
              <span class="weapon-name-text">${w.name || 'Weapon'}</span>
              <span class="weapon-dps-badge">${Math.round(w.dps || 0)} dps</span>
            </div>
            <div class="weapon-category-tag">${w.type || w.category || 'Direct Fire'}</div>
            <div class="weapon-meta-grid">
              <div class="w-meta-item"><span class="w-meta-label">Damage:</span><span class="w-meta-val">${w.damage || 0} dmg</span></div>
              <div class="w-meta-item"><span class="w-meta-label">Range:</span><span class="w-meta-val">${w.rangeStr || (w.rangeMax ? `0 - ${w.rangeMax}` : '0')}</span></div>
              <div class="w-meta-item"><span class="w-meta-label">Muzzle Vel:</span><span class="w-meta-val">${w.muzzleVelocity || 0}</span></div>
              <div class="w-meta-item"><span class="w-meta-label">Fire Cycle:</span><span class="w-meta-val">${w.fireCycle || (w.rateOfFire ? `${w.rateOfFire} rof` : '1 shot')}</span></div>
              <div class="w-meta-item"><span class="w-meta-label">Turret Pitch:</span><span class="w-meta-val">${w.turretPitch || 'Fixed'}</span></div>
              <div class="w-meta-item"><span class="w-meta-label">Turret Yaw:</span><span class="w-meta-val">${w.turretYaw || 'Fixed'}</span></div>
              <div class="w-meta-item"><span class="w-meta-label">Tolerance:</span><span class="w-meta-val">${w.firingTolerance || 0}</span></div>
              <div class="w-meta-item"><span class="w-meta-label">AoE Radius:</span><span class="w-meta-val">${w.damageRadius || 0}</span></div>
            </div>
          </div>
        `;
      });
    } else {
      weaponsHtml = `<div style="padding: 10px 14px; color:#64748b; font-style:italic;">No offensive weapons (Support / Construction Unit)</div>`;
    }

    return `
      <div class="unit-detail-card ${factionLower}">
        <!-- Header -->
        <div class="detail-card-header ${factionLower}">
          <button class="detail-close-btn" data-remove-id="${u.id}" title="Remove from compare">✕</button>
          <img class="detail-header-portrait" src="${iconUrl}" alt="${u.id}" onerror="this.src='/static/img/units/xra0101.png'">
          <div class="detail-header-info">
            <div class="detail-header-name">${u.name}</div>
            <div class="detail-header-role">${u.tech} ${u.role || u.description || ''}</div>
            <div class="detail-header-id">${u.id} (${u.faction})</div>
          </div>
        </div>

        <!-- Quick Summary Ribbon -->
        <div class="detail-quick-bar">
          <div class="quick-stat-item health" title="Max Health"><span>+${fmtK(hp)}</span></div>
          <div class="quick-stat-item mass" title="Mass Cost"><span>🪙 ${fmtK(mass)}</span></div>
          <div class="quick-stat-item energy" title="Energy Cost"><span>⚡ ${fmtK(energy)}</span></div>
          <div class="quick-stat-item time" title="Build Time"><span>⏱️ ${fmtK(time)}</span></div>
        </div>

        <!-- Economy Section -->
        <div class="detail-section">
          <div class="detail-section-header">Economy</div>
          <table class="detail-stats-table">
            ${buildRate > 0 ? `<tr><td>Build rate</td><td>${buildRate}</td></tr>` : ''}
            <tr><td>Mass cost</td><td>${mass.toLocaleString()}</td></tr>
            <tr><td>Energy cost</td><td>${energy.toLocaleString()}</td></tr>
            <tr><td>Build time</td><td>${time.toLocaleString()}</td></tr>
            ${massProd > 0 ? `<tr><td>Mass yield</td><td>+${massProd}/s</td></tr>` : ''}
            ${energyProd > 0 ? `<tr><td>Energy yield</td><td>+${energyProd}/s</td></tr>` : ''}
          </table>
        </div>

        <!-- Abilities Section -->
        <div class="detail-section">
          <div class="detail-section-header">Abilities</div>
          <div class="abilities-container">
            ${abilitiesHtml}
          </div>
        </div>

        <!-- Intel Section -->
        <div class="detail-section">
          <div class="detail-section-header">Intel</div>
          <table class="detail-stats-table">
            <tr><td>Vision radius</td><td>${vision}</td></tr>
            ${waterVision !== vision ? `<tr><td>Water vision radius</td><td>${waterVision}</td></tr>` : ''}
            ${radar > 0 ? `<tr><td>Radar radius</td><td>${radar}</td></tr>` : ''}
            ${sonar > 0 ? `<tr><td>Sonar radius</td><td>${sonar}</td></tr>` : ''}
            ${omni > 0 ? `<tr><td>Omni radius</td><td>${omni}</td></tr>` : ''}
          </table>
        </div>

        <!-- Physics Section -->
        <div class="detail-section">
          <div class="detail-section-header">Physics</div>
          <table class="detail-stats-table">
            <tr><td>Max speed</td><td>${speed}</td></tr>
            <tr><td>Turn rate</td><td>${turnRate}</td></tr>
            ${s.motionType ? `<tr><td>Motion type</td><td>${s.motionType.replace('RULEUMT_', '')}</td></tr>` : ''}
          </table>
        </div>

        <!-- Wreckage Section -->
        <div class="detail-section">
          <div class="detail-section-header">Wreckage</div>
          <table class="detail-stats-table">
            <tr><td>Health</td><td>${fmtK(wreckageHp)}</td></tr>
            <tr><td>Mass</td><td>${fmtK(wreckageMass)}</td></tr>
          </table>
        </div>

        <!-- Veterancy Section -->
        <div class="detail-section">
          <div class="detail-section-header">Veterancy</div>
          <div style="padding: 0 14px;">
            ${vetHtml}
          </div>
        </div>

        <!-- Weapons Section -->
        <div class="detail-section">
          <div class="detail-section-header">Weapons (${weapons.length})</div>
          ${weaponsHtml}
        </div>
      </div>
    `;
  }

  // ==========================================================================
  // RENDER AGENT / DEVELOPER VIEW
  // ==========================================================================
  function renderAgentView() {
    let md = `### Raptor Swarm Faction - Full Unit Roster (31 Units)\n\n`;
    md += `| ID | Tier | Name | Role | Health | Regen | Mass Cost | Speed | Total DPS | Key Weapon & Range | Key Abilities |\n`;
    md += `| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |\n`;

    raptorUnits.forEach((u) => {
      const s = u.stats || {};
      const w = (u.weapons && u.weapons[0]) || null;
      const wInfo = w ? `${w.name} (${w.rangeStr} r, ${Math.round(w.dps)} dps)` : 'None (Support)';
      const ab = (u.abilities || []).slice(0, 2).join(', ') || 'None';

      md += `| \`${u.id}\` | **${u.tech}** | **${u.name}** | ${u.role || u.description} | ${(s.health || u.hp || 0).toLocaleString()} | +${s.regen || u.regen || 0}/s | ${(s.mass || u.mass || 0).toLocaleString()} | ${s.speed || u.speed || 0} | ${Math.round(s.totalDps || 0)} | ${wInfo} | ${ab} |\n`;
    });

    const html = `
      <div class="agent-summary-container">
        <div class="agent-toolbar">
          <button class="btn btn-sm btn-outline" id="btn-copy-agent-md">📋 Copy Markdown Table for Agent</button>
          <button class="btn btn-sm btn-outline" id="btn-copy-curl">🌐 Copy API cURL Command</button>
          <a href="/api/raptors" target="_blank" class="btn btn-sm btn-ghost">🔗 Raw JSON API</a>
        </div>
        <div class="agent-md-box" id="agent-md-content">${escapeHtml(md)}</div>
      </div>
    `;

    containerEl.innerHTML = html;

    const btnCopyMd = document.getElementById('btn-copy-agent-md');
    if (btnCopyMd) {
      btnCopyMd.addEventListener('click', () => {
        navigator.clipboard.writeText(md).then(() => {
          btnCopyMd.textContent = '✓ Copied Markdown to Clipboard!';
          setTimeout(() => { btnCopyMd.textContent = '📋 Copy Markdown Table for Agent'; }, 2000);
        });
      });
    }

    const btnCopyCurl = document.getElementById('btn-copy-curl');
    if (btnCopyCurl) {
      btnCopyCurl.addEventListener('click', () => {
        const curlCmd = `curl -X GET "http://127.0.0.1:5055/api/raptor-roster"`;
        navigator.clipboard.writeText(curlCmd).then(() => {
          btnCopyCurl.textContent = '✓ Copied cURL Command!';
          setTimeout(() => { btnCopyCurl.textContent = '🌐 Copy API cURL Command'; }, 2000);
        });
      });
    }
  }

  function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // Run when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
