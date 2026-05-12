// ============================================================
// FIFA WORLD CUP 2026 - SIMULATION CENTER v5.1 (FINAL)
// ============================================================

const state = {
  meta: null,
  stats: {},
  statsFull: {},
  filtered: [],
  selectedSimulation: 0,
  currentSimulation: null,
  activeTab: 'overview',
  isLoading: false,
  abortController: null,
  cache: new Map(),
};

const FLAGS = {
  "Spain":"🇪🇸","England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","France":"🇫🇷","Argentina":"🇦🇷","Brazil":"🇧🇷",
  "Germany":"🇩🇪","Portugal":"🇵🇹","Netherlands":"🇳🇱","Belgium":"🇧🇪","Italy":"🇮🇹",
  "Uruguay":"🇺🇾","USA":"🇺🇸","Mexico":"🇲🇽","Colombia":"🇨🇴","Japan":"🇯🇵",
  "Morocco":"🇲🇦","Senegal":"🇸🇳","Australia":"🇦🇺","Croatia":"🇭🇷","Switzerland":"🇨🇭",
  "Sweden":"🇸🇪","Norway":"🇳🇴","Denmark":"🇩🇰","Poland":"🇵🇱","Serbia":"🇷🇸",
  "Canada":"🇨🇦","Ecuador":"🇪🇨","Tunisia":"🇹🇳","South Korea":"🇰🇷","Algeria":"🇩🇿",
  "Scotland":"🏴󠁧󠁢󠁳󠁣󠁴󠁿","Türkiye":"🇹🇷","Iran":"🇮🇷","Ghana":"🇬🇭","DR Congo":"🇨🇩",
  "Bosnia-Herzegovina":"🇧🇦","Ivory Coast":"🇨🇮","Austria":"🇦🇹","Paraguay":"🇵🇾",
  "Saudi Arabia":"🇸🇦","Panama":"🇵🇦","Iraq":"🇮🇶","Uzbekistan":"🇺🇿","Egypt":"🇪🇬",
  "Cape Verde":"🇨🇻","Jordan":"🇯🇴","South Africa":"🇿🇦","Qatar":"🇶🇦","Haiti":"🇭🇹",
  "New Zealand":"🇳🇿","Curacao":"🇨🇼","Czechia":"🇨🇿"
};

const flag = (t) => FLAGS[t] || "🏳️";
const $ = (id) => document.getElementById(id);
const $$ = (s, p = document) => Array.from(p.querySelectorAll(s));
const fm = (n) => (n || 0).toLocaleString("pt-BR");

// ============================================================
// API
// ============================================================

async function fetchJSON(url, opts = {}) {
  if (state.abortController) state.abortController.abort();
  state.abortController = new AbortController();
  const key = url;
  if (!opts.force && state.cache.has(key)) return state.cache.get(key);
  try {
    const res = await fetch(url, { signal: state.abortController.signal, headers: { 'Accept': 'application/json' }, ...opts });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.cache.set(key, data);
    return data;
  } catch (err) {
    if (err.name === 'AbortError') return null;
    throw err;
  }
}

// ============================================================
// NORMALIZAÇÃO
// ============================================================

function normalizeStats(raw) {
  console.log('📊 Normalizando stats...', typeof raw, raw ? Object.keys(raw).slice(0, 4) : 'null');
  if (!raw) return {};
  
  if (raw.team_stats && typeof raw.team_stats === 'object' && !Array.isArray(raw.team_stats)) {
    const ts = raw.team_stats;
    const keys = Object.keys(ts);
    if (keys.length > 0) {
      const firstVal = ts[keys[0]];
      if (firstVal && typeof firstVal === 'object' && 'champion_prob' in firstVal) {
        console.log('✅ Usando team_stats diretamente');
        return ts;
      }
      if (firstVal && typeof firstVal === 'object' && 'R32_prob' in firstVal) {
        const out = {};
        keys.forEach(k => {
          const t = ts[k];
          out[k] = {
            champion_prob: t.champion_prob ?? t.CHAMPION / 100000 ?? 0,
            final_prob: t.FINAL_prob ?? 0,
            semifinal_prob: t.SF_prob ?? 0,
            quarterfinal_prob: t.QF_prob ?? 0,
            r16_prob: t.R16_prob ?? 0,
            r32_prob: t.R32_prob ?? 1,
            counts: t.counts ?? {}
          };
        });
        return out;
      }
    }
  }
  
  if (raw.team_stats && Array.isArray(raw.team_stats) && raw.team_stats.length > 0 && typeof raw.team_stats[0] === 'string') {
    const fp = raw.final_probabilities || {};
    const out = {};
    raw.team_stats.forEach(team => {
      const t = fp[team];
      out[team] = t && typeof t === 'object' ? {
        champion_prob: t.champion_prob ?? t.champion ?? 0,
        final_prob: t.final_prob ?? t.final ?? 0,
        semifinal_prob: t.semifinal_prob ?? t.semifinal ?? t.semi ?? 0,
        quarterfinal_prob: t.quarterfinal_prob ?? t.quarterfinal ?? t.qf ?? 0,
        r16_prob: t.r16_prob ?? t.r16 ?? 0,
        r32_prob: t.r32_prob ?? t.r32 ?? 1,
        counts: t.counts ?? t.count ?? {}
      } : { champion_prob: 0, final_prob: 0, semifinal_prob: 0, quarterfinal_prob: 0, r16_prob: 0, r32_prob: 1, counts: {} };
    });
    console.log('✅ Stats via array+fp:', Object.keys(out).length, 'times');
    return out;
  }
  
  if (raw.final_probabilities && typeof raw.final_probabilities === 'object') {
    const fp = raw.final_probabilities;
    const keys = Object.keys(fp);
    if (keys.length > 0 && typeof fp[keys[0]] === 'object') {
      const out = {};
      keys.forEach(k => {
        const t = fp[k];
        out[k] = {
          champion_prob: t.champion_prob ?? t.champion ?? 0,
          final_prob: t.final_prob ?? t.final ?? 0,
          semifinal_prob: t.semifinal_prob ?? t.semifinal ?? t.semi ?? 0,
          quarterfinal_prob: t.quarterfinal_prob ?? t.quarterfinal ?? t.qf ?? 0,
          r16_prob: t.r16_prob ?? t.r16 ?? 0,
          r32_prob: t.r32_prob ?? t.r32 ?? 1,
          counts: t.counts ?? t.count ?? {}
        };
      });
      console.log('✅ Usando final_probabilities:', keys.length, 'times');
      return out;
    }
  }
  
  if (typeof raw === 'object' && !Array.isArray(raw)) {
    const keys = Object.keys(raw).filter(k => !['team_stats', 'final_probabilities'].includes(k));
    if (keys.length > 0 && typeof raw[keys[0]] === 'object' && ('champion_prob' in raw[keys[0]] || 'R32_prob' in raw[keys[0]])) {
      console.log('✅ Raw já é normalizado:', keys.length, 'times');
      return raw;
    }
  }
  
  console.warn('⚠️ Formato não reconhecido');
  return {};
}

// ============================================================
// FILTROS
// ============================================================

function selectedVals(sel) { return sel ? Array.from(sel.selectedOptions).map(o => o.value).filter(Boolean) : []; }

function buildFilterQuery() {
  const p = new URLSearchParams();
  selectedVals($('championFilter')).forEach(v => p.append('champion', v));
  selectedVals($('combinationFilter')).forEach(v => p.append('combination', v));
  selectedVals($('thirdGroupFilter')).forEach(v => p.append('third_group', v));
  const team = $('teamFilter')?.value;
  if (team) { p.append('team', team); p.append('stage', $('stageFilter')?.value || 'qualified'); }
  p.append('limit', '100.000');
  return p.toString();
}

function setMultiOptions(sel, vals) {
  if (!sel || !vals) return;
  sel.innerHTML = vals.map(v => `<option value="${v}">${v}</option>`).join('');
}

function setSingleOptions(sel, vals, empty = false) {
  if (!sel || !vals) return;
  let html = empty ? '<option value="">Todos</option>' : '';
  html += vals.map(v => `<option value="${v}">${v}</option>`).join('');
  sel.innerHTML = html;
}

// ============================================================
// RENDER
// ============================================================

function renderTierChart() {
  const el = document.getElementById('tierChart');
  if (!el || !state.statsFull) return;
  const tiers = [
    { min: 5, max: 100, label: '🏆 Favoritos (5%+)', color: '#E61D25' },
    { min: 1, max: 5, label: '🥈 Candidatos (1-5%)', color: '#F0D078' },
    { min: 0.1, max: 1, label: '🥉 Zebras (0.1-1%)', color: '#0aa6a6' },
    { min: 0, max: 0.1, label: '📊 Sem chance (<0.1%)', color: '#6b7280' },
  ];
  const counts = tiers.map(t => ({
    ...t,
    count: Object.values(state.statsFull).filter(s => {
      const p = (s.champion_prob||0)*100;
      return p >= t.min && p < t.max;
    }).length
  }));
  const maxCount = Math.max(...counts.map(t=>t.count), 1);
  el.innerHTML = counts.map(t => `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;font-size:0.85rem">
      <span style="width:160px;text-align:right;color:var(--text)">${t.label}</span>
      <div style="flex:1;height:24px;background:var(--surface-soft);border-radius:6px;overflow:hidden">
        <div style="width:${(t.count/maxCount*100).toFixed(0)}%;height:100%;background:${t.color};border-radius:6px;display:flex;align-items:center;padding-left:8px;color:#fff;font-weight:700;font-size:0.75rem">${t.count} times</div>
      </div>
    </div>`).join('');
}

function renderMetrics(summary) {
  const el = $('metrics');
  if (!el) return;
  const totalSims = 100000;
  const filteredCount = state.filtered.length;
  const cards = [
    { label: '🔍 Cenários', value: fm(totalSims), sub: `Filtrados: ${fm(filteredCount)}` },
    { label: '🎲 Simulação', value: `#${summary?.simulation ?? '—'}`, sub: `Comb. ${summary?.slot_combination ?? '—'}` },
    { label: '🏆 Campeão', value: `${flag(summary?.champion)} ${summary?.champion ?? '—'}`, sub: 'Desfecho', gold: true },
    { label: '🥈 Vice', value: `${flag(summary?.runner_up)} ${summary?.runner_up ?? '—'}`, sub: 'Finalista' },
    { label: '🥉 3º Lugar', value: `${flag(summary?.third_place)} ${summary?.third_place ?? '—'}`, sub: (summary?.third_place_groups || []).join(', ') || '—' },
  ];
  el.innerHTML = cards.map(c => `<article class="metric-card ${c.gold ? 'gold' : ''}"><div class="metric-label">${c.label}</div><div class="metric-value">${c.value}</div><div class="metric-sub">${c.sub}</div></article>`).join('');
}

function renderMainSummary(summary, bracket) {
  const el = $('summaryContent');
  if (!el) return;
  const fmatch = bracket?.rounds?.FINAL;
  const items = [
    { label: '🏆 Campeão', value: `${flag(summary?.champion)} ${summary?.champion ?? '—'}`, highlight: true },
    { label: '🥈 Vice', value: `${flag(summary?.runner_up)} ${summary?.runner_up ?? '—'}` },
    { label: '🥉 3º Lugar', value: `${flag(summary?.third_place)} ${summary?.third_place ?? '—'}` },
    { label: '📊 Combinação', value: summary?.slot_combination ?? '—' },
    { label: '👥 Grupos 3ºs', value: (summary?.third_place_groups || []).join(', ') || '—' },
    { label: '🎯 Final', value: fmatch ? `${flag(fmatch.team_a)} vs ${flag(fmatch.team_b)}` : '—' },
  ];
  
  const statsToUse = state.statsFull && Object.keys(state.statsFull).length > 0 ? state.statsFull : state.stats;
  
  if (statsToUse && Object.keys(statsToUse).length > 0) {
    const top3 = Object.entries(statsToUse).sort(([,a], [,b]) => (b.champion_prob || 0) - (a.champion_prob || 0)).slice(0, 3);
    el.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
        <div style="display:grid;gap:8px">
          ${items.map(i => `<div class="summary-item ${i.highlight ? 'summary-highlight' : ''}"><div class="summary-item-label">${i.label}</div><div class="summary-item-value">${i.value}</div></div>`).join('')}
        </div>
        <div class="stats-section" style="margin:0">
          <h4>🏆 Top 3 Probabilidades</h4>
          ${top3.map(([team, s], i) => {
            const pct = ((s.champion_prob || 0) * 100).toFixed(1);
            return `<div class="bar-row" style="margin-bottom:8px"><div class="bar-head"><span>${['🥇','🥈','🥉'][i]} ${flag(team)} ${team}</span><span><strong>${pct}%</strong></span></div><div class="bar-track"><div class="bar-fill" style="width:${Math.min(pct * 3, 100)}%"></div></div></div>`;
          }).join('')}
        </div>
      </div>`;
    return;
  }
  
  el.innerHTML = items.map(i => `<div class="summary-item ${i.highlight ? 'summary-highlight' : ''}"><div class="summary-item-label">${i.label}</div><div class="summary-item-value">${i.value}</div></div>`).join('');
}

function renderResultsTable() {
  const tbody = $('resultsTable')?.querySelector('tbody');
  if (!tbody) return;
  if (!state.filtered.length) { tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Aplique os filtros</td></tr>'; return; }
  tbody.innerHTML = state.filtered.map(r => `
    <tr data-simulation="${r.simulation}" class="${r.simulation === state.selectedSimulation ? 'active' : ''}" tabindex="0" role="button">
      <td>#${r.simulation}</td><td>${r.slot_combination ?? '—'}</td><td>${flag(r.champion)} ${r.champion}</td>
      <td>${flag(r.runner_up)} ${r.runner_up}</td><td>${flag(r.third_place)} ${r.third_place}</td><td>${(r.third_place_groups || []).join(', ')}</td>
    </tr>`).join('');
  tbody.querySelectorAll('tr').forEach(tr => {
    tr.addEventListener('click', () => selectSim(Number(tr.dataset.simulation)));
    tr.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectSim(Number(tr.dataset.simulation)); } });
  });
  const cnt = $('resultCount');
  if (cnt) cnt.textContent = state.filtered.length;
}

function selectSim(id) {
  state.selectedSimulation = id;
  const sel = $('simulationSelect');
  if (sel) sel.value = String(id);
  $$('tr[data-simulation]').forEach(tr => tr.classList.toggle('active', Number(tr.dataset.simulation) === id));
  loadSimulation(id);
  setTimeout(updateSimInfo, 100);
}

function updateSimInfo() {
  const info = $('simulationInfo');
  if (!info) return;
  const idx = state.filtered.findIndex(r => r.simulation === state.selectedSimulation);
  const totalFiltered = state.filtered.length;
  const simNumber = state.selectedSimulation;
  info.textContent = `Simulação #${simNumber} · ${idx + 1} de ${totalFiltered} exibidas (100.000 total)`;
}

function renderChampionDist() {
  const el = $('championDistribution');
  if (!el) return;
  if (!state.filtered.length) { el.innerHTML = '<div class="empty-state"><p>Sem dados</p></div>'; return; }
  const counts = new Map();
  state.filtered.forEach(r => counts.set(r.champion, (counts.get(r.champion) || 0) + 1));
  const rows = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10);
  const total = state.filtered.length;
  el.innerHTML = rows.map(([team, count]) => {
    const perc = ((count / total) * 100).toFixed(1);
    return `<div class="bar-row"><div class="bar-head"><span>${flag(team)} ${team}</span><span><strong>${count}</strong> (${perc}%)</span></div><div class="bar-track"><div class="bar-fill" style="width:${perc}%"></div></div></div>`;
  }).join('');
}

// ============================================================
// BRACKET
// ============================================================
function renderBracket(rounds) {
  const grid = $('bracketGrid');
  if (!grid) return;
  if (!rounds || !Object.keys(rounds).length) { 
    grid.innerHTML = '<div class="empty-state"><p>Selecione uma simulação</p></div>'; 
    return; 
  }
  
  const r32 = rounds.R32 || [];
  const r16 = rounds.R16 || [];
  const qf = rounds.QF || [];
  const sf = rounds.SF || [];
  const finalMatch = rounds.FINAL || {};
  const thirdPlace = rounds.THIRD_PLACE || {};
  const champ = finalMatch.winner || state.currentSimulation?.summary?.champion || '—';
  
  const matchPair = (m) => {
    const probA = m.probability_a != null ? (m.probability_a * 100).toFixed(1) : null;
    const probB = m.probability_b != null ? (m.probability_b * 100).toFixed(1) : null;
    const teamA = m.team_a || '—';
    const teamB = m.team_b || '—';
    const groupA = m.team_a_group || m.team_a_slot || '';
    const groupB = m.team_b_group || m.team_b_slot || '';
    
    return `
    <div class="match-pair">
      <div class="team-slot ${m.winner === teamA ? 'winner' : 'loser'}">
        <span class="slot-flag">${flag(teamA)}</span>
        <div class="slot-info"><span class="slot-name">${teamA}</span><span class="slot-group">${groupA}</span></div>
        ${probA ? `<span class="slot-prob">${probA}%</span>` : ''}${m.winner === teamA ? '<span class="win-mark">✓</span>' : ''}
      </div>
      <div class="match-divider"></div>
      <div class="team-slot ${m.winner === teamB ? 'winner' : 'loser'}">
        <span class="slot-flag">${flag(teamB)}</span>
        <div class="slot-info"><span class="slot-name">${teamB}</span><span class="slot-group">${groupB}</span></div>
        ${probB ? `<span class="slot-prob">${probB}%</span>` : ''}${m.winner === teamB ? '<span class="win-mark">✓</span>' : ''}
      </div>
    </div>`;
  };
  
  let html = '<div class="knockouts">';
  
  // R32
  html += '<div class="phase phase--r32"><div class="phase-title">32 avos</div><div class="confront">';
  r32.forEach(m => { html += matchPair(m); });
  html += '</div></div>';
  
  // R16
  html += '<div class="phase phase--r16"><div class="phase-title">Oitavas</div><div class="confront">';
  r16.forEach(m => { html += matchPair(m); });
  html += '</div></div>';
  
  // QF
  html += '<div class="phase phase--qf"><div class="phase-title">Quartas</div><div class="confront">';
  qf.forEach(m => { html += matchPair(m); });
  html += '</div></div>';
  
  // SF
  html += '<div class="phase phase--sf"><div class="phase-title">Semi</div><div class="confront">';
  sf.forEach(m => { html += matchPair(m); });
  html += '</div></div>';
  
  // Final
  html += '<div class="phase phase--final"><div class="phase-title">Final</div><div class="confront">';
  if (finalMatch.team_a || finalMatch.team_b) html += matchPair(finalMatch);
  html += '</div></div>';
  
  // 3º Lugar
  if (thirdPlace.winner) {
    html += '<div class="phase phase--third"><div class="phase-title">3º Lugar</div><div class="confront">';
    html += matchPair(thirdPlace);
    html += '</div></div>';
  }
  
  // Campeão
  html += `<div class="phase phase--champion"><div class="phase-title">🏆 Campeão</div><div class="confront">
    <div class="champion-slot">
      <span class="slot-flag">${flag(champ)}</span>
      <div class="slot-info"><span class="slot-name">${champ}</span><span class="slot-label">Campeão Mundial</span></div>
    </div>
  </div></div>`;
  
  html += '</div>';
  grid.innerHTML = html;
}

// ============================================================
// GROUPS
// ============================================================

function renderGroups(groups, classified) {
  const grid = $('groupsGrid');
  if (!grid) return;
  let arr = [];
  if (Array.isArray(groups)) { arr = groups; }
  else if (groups && typeof groups === 'object') {
    for (const [key, value] of Object.entries(groups)) {
      if (key.length === 1 && key === key.toUpperCase()) { const ranking = Array.isArray(value) ? value : (value?.standings || value?.ranking || []); arr.push({ group: key, ranking }); }
    }
    if (arr.length === 0 && groups.groups) {
      if (Array.isArray(groups.groups)) { arr = groups.groups; }
      else { for (const [key, value] of Object.entries(groups.groups)) { if (key.length === 1 && key === key.toUpperCase()) { const ranking = Array.isArray(value) ? value : (value?.standings || value?.ranking || []); arr.push({ group: key, ranking }); } } }
    }
    if (arr.length === 0) { for (const [key, value] of Object.entries(groups)) { if (key.startsWith('Group ')) { const letter = key.replace('Group ', ''); const ranking = Array.isArray(value) ? value : (value?.standings || value?.ranking || []); arr.push({ group: letter, ranking }); } } }
  }
  if (!arr.length) { grid.innerHTML = '<div class="empty-state"><p>Selecione uma simulação para ver os grupos</p></div>'; return; }
  arr.sort((a, b) => (a.group || '').localeCompare(b.group || ''));
  const cmap = new Map((classified || []).map(t => [t.country, t.type]));
  const statusLabels = { 'direct': 'Classificado', 'best_third': 'Melhor 3º', 'third_playoff': '3º Classificado', 'eliminated': 'Eliminado' };
  const statsToUse = state.statsFull && Object.keys(state.statsFull).length > 0 ? state.statsFull : state.stats;
  
  grid.innerHTML = arr.map(g => {
    const groupLetter = String(g.group || '').replace(/^Group\s+/i, '').trim();
    const ranking = g.ranking || g.standings || [];
    return `
    <article class="group-card">
      <div class="group-header"><h4>Grupo ${groupLetter}</h4><span class="group-badge">${groupLetter}</span></div>
      <div class="group-standings">
        ${ranking.map((t, i) => {
          const country = t.country || t.team || '—';
          const status = cmap.get(country) || (t.position <= 2 ? 'direct' : t.position === 3 ? 'best_third' : 'eliminated');
          const pos = t.position ?? (i + 1);
          const posClass = pos === 1 ? 'pos-1' : pos === 2 ? 'pos-2' : pos === 3 ? 'pos-3' : 'pos-4';
          const rowClass = pos <= 2 ? 'qualified' : pos === 3 ? 'third' : '';
          const statusLabel = statusLabels[status] || status;
          return `
          <div class="group-row ${rowClass}">
            <span class="group-pos ${posClass}">${pos}</span>
            <span class="group-flag">${flag(country)}</span>
            <div class="group-team-info">
              <span class="group-team-name">${country}</span>
              <span class="group-team-stats">${statsToUse && statsToUse[country] ? `🏆 ${((statsToUse[country].champion_prob || 0) * 100).toFixed(1)}% | Final: ${((statsToUse[country].final_prob || 0) * 100).toFixed(1)}%` : '—'}</span>
            </div>
            <span class="tag ${status}" title="${statusLabel}">${statusLabel}</span>
          </div>`;
        }).join('')}
      </div>
    </article>`;
  }).join('');
}

function renderClassified(teams) {
  const tbody = $('classifiedTable')?.querySelector('tbody');
  if (!tbody) return;
  if (!teams?.length) { tbody.innerHTML = '<tr><td colspan="4" class="empty-state">Selecione uma simulação</td></tr>'; return; }
  tbody.innerHTML = teams.map(t => `<tr><td>${flag(t.country)} ${t.country}</td><td>${t.group}</td><td>${t.position}</td><td><span class="tag ${t.type}">${t.type}</span></td></tr>`).join('');
}

// ============================================================
// ESTATÍSTICAS
// ============================================================

function renderStats() {
  const tbody = $('statsTable')?.querySelector('tbody');
  if (!tbody) return;
  const statsToUse = state.statsFull && Object.keys(state.statsFull).length > 0 ? state.statsFull : state.stats;
  if (!statsToUse || Object.keys(statsToUse).length === 0) { tbody.innerHTML = '<tr><td colspan="7" class="empty-state">⏳ Estatísticas não carregadas.</td></tr>'; return; }
  const entries = Object.entries(statsToUse).sort(([,a], [,b]) => (b.champion_prob || 0) - (a.champion_prob || 0));
  tbody.innerHTML = entries.map(([team, s], i) => {
    const cp = ((s.champion_prob || 0) * 100).toFixed(1);
    const fp = ((s.final_prob || 0) * 100).toFixed(1);
    const sp = ((s.semifinal_prob || 0) * 100).toFixed(1);
    const qp = ((s.quarterfinal_prob || 0) * 100).toFixed(1);
    const rp = ((s.r16_prob || 0) * 100).toFixed(1);
    const r32p = ((s.r32_prob || 0) * 100).toFixed(1);
    return `<tr><td><span class="team-rank">#${i+1}</span> ${flag(team)} ${team}</td><td><strong>${cp}%</strong><div class="stat-bar-mini"><div class="stat-bar-fill" style="width:${Math.min(cp,100)}%"></div></div></td><td>${fp}%<div class="stat-bar-mini"><div class="stat-bar-fill" style="width:${Math.min(fp,100)}%"></div></div></td><td>${sp}%<div class="stat-bar-mini"><div class="stat-bar-fill" style="width:${Math.min(sp,100)}%"></div></div></td><td>${qp}%<div class="stat-bar-mini"><div class="stat-bar-fill" style="width:${Math.min(qp,100)}%"></div></div></td><td>${rp}%<div class="stat-bar-mini"><div class="stat-bar-fill" style="width:${Math.min(rp,100)}%"></div></div></td><td>${r32p}%<div class="stat-bar-mini"><div class="stat-bar-fill" style="width:${Math.min(r32p,100)}%"></div></div></td></tr>`;
  }).join('');
}

function renderH2HStats() {
  const el = $('h2hStats');
  if (!el) return;
  const statsToUse = state.statsFull && Object.keys(state.statsFull).length > 0 ? state.statsFull : state.stats;
  if (!statsToUse || Object.keys(statsToUse).length === 0) { el.innerHTML = '<div class="empty-state"><p>⏳ Estatísticas não carregadas.</p></div>'; return; }
  const sorted = Object.entries(statsToUse).sort(([,a], [,b]) => (b.champion_prob || 0) - (a.champion_prob || 0));
  const top5 = sorted.slice(0, 5);
  const topSemi = sorted.filter(([,s]) => (s.semifinal_prob || 0) > 0.1).slice(0, 5);
  const total = 100000;
  
  el.innerHTML = `
    <div style="display:grid;gap:14px">
      <div class="stats-section"><h4>🏆 Top 5 Favoritos ao Título</h4><div class="bar-list">
        ${top5.map(([team, s], i) => { const pct = ((s.champion_prob || 0) * 100).toFixed(1); return `<div class="bar-row"><div class="bar-head"><span>${i+1}. ${flag(team)} ${team}</span><span><strong>${pct}%</strong></span></div><div class="bar-track"><div class="bar-fill" style="width:${Math.min(pct * 3, 100)}%"></div></div></div>`; }).join('')}
      </div></div>
      <div class="stats-section"><h4>🎯 Maiores Chances de Semi</h4><div class="bar-list">
        ${topSemi.map(([team, s]) => { const pct = ((s.semifinal_prob || 0) * 100).toFixed(1); return `<div class="bar-row"><div class="bar-head"><span>${flag(team)} ${team}</span><span>${pct}%</span></div><div class="bar-track"><div class="bar-fill" style="width:${Math.min(pct * 1.5, 100)}%;background:linear-gradient(90deg,#2A398D,#E61D25)"></div></div></div>`; }).join('')}
      </div></div>
      <div class="stats-section"><h4>📈 Distribuição de Probabilidades</h4><div style="display:grid;gap:6px;font-size:0.75rem">
        ${[{ min: 10, max: 100, label: 'Favoritos (10%+)', color: '#138d61', icon: '🟢' },{ min: 5, max: 10, label: 'Candidatos (5-10%)', color: '#0aa6a6', icon: '🔵' },{ min: 1, max: 5, label: 'Possíveis (1-5%)', color: '#e3b23c', icon: '🟡' },{ min: 0.1, max: 1, label: 'Zebras (0.1-1%)', color: '#c44545', icon: '🟠' },{ min: 0, max: 0.1, label: 'Sem chance (<0.1%)', color: '#6b7280', icon: '⚫' }].map(r => {
          const count = sorted.filter(([,s]) => { const p = (s.champion_prob || 0) * 100; return p >= r.min && p < r.max; }).length;
          const barPct = sorted.length ? ((count / sorted.length) * 100).toFixed(1) : 0;
          return `<div style="display:flex;align-items:center;gap:8px"><span style="width:130px;text-align:right;color:#9CA3AF;font-size:0.7rem">${r.icon} ${r.label}</span><div style="flex:1;height:16px;background:rgba(255,255,255,0.05);border-radius:8px;overflow:hidden"><div style="width:${barPct}%;height:100%;background:${r.color};border-radius:8px"></div></div><span style="width:50px;font-weight:700;text-align:right">${count}</span></div>`;
        }).join('')}
      </div></div>
      <div class="stats-section"><h4>📊 Resumo</h4><div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.8rem">
        <div class="stat-item"><span class="stat-item-label">Total simulações</span><span class="stat-item-value">${fm(total)}</span></div>
        <div class="stat-item"><span class="stat-item-label">Times analisados</span><span class="stat-item-value">${sorted.length}</span></div>
        <div class="stat-item"><span class="stat-item-label">Maior favorito</span><span class="stat-item-value">${flag(top5[0]?.[0])} ${top5[0]?.[0] || '—'}</span></div>
        <div class="stat-item"><span class="stat-item-label">Chance do top 1</span><span class="stat-item-value">${top5[0] ? ((top5[0][1].champion_prob||0)*100).toFixed(1) + '%' : '—'}</span></div>
        <div class="stat-item"><span class="stat-item-label">Média de título</span><span class="stat-item-value">${(sorted.reduce((a,[,s]) => a + (s.champion_prob||0), 0) / sorted.length * 100).toFixed(2)}%</span></div>
        <div class="stat-item"><span class="stat-item-label">Times com >1%</span><span class="stat-item-value">${sorted.filter(([,s]) => (s.champion_prob||0) > 0.01).length}</span></div>
      </div></div>
    </div>`;
}

function renderHeatmap() {
  const container = document.getElementById('heatmapGrid');
  if (!container) return;
  const statsToUse = state.statsFull?.keys?.length ? state.statsFull : state.stats;
  if (!statsToUse || !Object.keys(statsToUse).length) return;
  
  const metric = $('heatmapMetric')?.value || 'champion_prob';
  const labels = { champion_prob:'🏆 Título', final_prob:'🥈 Final', semifinal_prob:'🥉 Semi', quarterfinal_prob:'🏟️ Quartas', r16_prob:'📊 Oitavas' };
  
  const items = Object.entries(statsToUse)
    .sort(([,a], [,b]) => (b[metric]||0) - (a[metric]||0))
    .slice(0, 12); // Só top 12 para não poluir
  
  const max = items[0]?.[1]?.[metric] || 0.3;
  
  container.innerHTML = `
    <div style="display:flex;flex-wrap:wrap;gap:10px;justify-content:center">
      ${items.map(([team, s], i) => {
        const pct = ((s[metric]||0)*100).toFixed(1);
        const intensity = (s[metric]||0) / (max||0.01);
        // Cores mais claras para modo escuro
        const r = Math.round(42 + 188*intensity);
        const g = Math.round(57 + 150*intensity);
        const b = Math.round(141 - 100*intensity);
        const bg = `rgb(${r},${g},${b})`;
        const txt = intensity > 0.45 ? '#fff' : '#0a0f1a';
        return `
          <div style="background:${bg};border-radius:12px;padding:12px;text-align:center;min-width:90px;color:${txt};box-shadow:0 2px 8px rgba(0,0,0,0.15);transition:transform 0.2s"
               onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
            <div style="font-size:1.3rem">${flag(team)}</div>
            <div style="font-weight:700;font-size:0.75rem">${team}</div>
            <div style="font-size:1.1rem;font-weight:800">${pct}%</div>
            <div style="font-size:0.6rem;opacity:0.8">${labels[metric]}</div>
          </div>`;
      }).join('')}
    </div>`;
}

function renderRadarChart(t1, t2) {
  const container = document.getElementById('radarContainer');
  if (!container) return;
  
  const statsToUse = state.statsFull && Object.keys(state.statsFull).length > 0 ? state.statsFull : state.stats;
  if (!statsToUse || !t1 || !t2) {
    container.innerHTML = '<p style="color:var(--muted);font-size:.85rem;padding:40px;text-align:center">Selecione dois times e clique em Comparar</p>';
    return;
  }
  
  const s1 = statsToUse[t1];
  const s2 = statsToUse[t2];
  if (!s1 || !s2) {
    container.innerHTML = '<p style="color:var(--muted);font-size:.85rem;padding:40px;text-align:center">Dados não disponíveis</p>';
    return;
  }
  
  // 5 eixos: R32, R16, QF, SF, Final (omitimos campeão para não sobrecarregar)
  const axes = [
    { key: 'r32_prob', label: 'R32' },
    { key: 'r16_prob', label: 'Oitavas' },
    { key: 'quarterfinal_prob', label: 'Quartas' },
    { key: 'semifinal_prob', label: 'Semi' },
    { key: 'final_prob', label: 'Final' },
  ];
  
  const cx = 150, cy = 150, r = 110;
  const angleStep = (2 * Math.PI) / axes.length;
  
  // Função para converter valor em coordenada
  const getPoint = (val, index) => {
    const angle = angleStep * index - Math.PI / 2;
    const dist = (val || 0) * r;
    return {
      x: cx + dist * Math.cos(angle),
      y: cy + dist * Math.sin(angle),
    };
  };
  
  // Gerar polígono para um time
  const polygonPoints = (stats) => {
    return axes.map((ax, i) => {
      const pt = getPoint(stats[ax.key], i);
      return `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`;
    }).join(' ');
  };
  
  // Gerar linhas de grade
  const gridLevels = [0.2, 0.4, 0.6, 0.8, 1.0];
  const gridPolygons = gridLevels.map(level => {
    return axes.map((_, i) => {
      const pt = getPoint(level, i);
      return `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`;
    }).join(' ');
  });
  
  // Gerar eixos
  const axisLines = axes.map((ax, i) => {
    const pt = getPoint(1.0, i);
    return `<line x1="${cx}" y1="${cy}" x2="${pt.x.toFixed(1)}" y2="${pt.y.toFixed(1)}" stroke="var(--muted)" stroke-width="0.5" opacity="0.3"/>`;
  }).join('');
  
  // Labels dos eixos
  const axisLabels = axes.map((ax, i) => {
    const pt = getPoint(1.15, i);
    return `<text x="${pt.x.toFixed(1)}" y="${pt.y.toFixed(1)}" text-anchor="middle" dominant-baseline="middle" fill="var(--text)" font-size="9" font-family="'Space Grotesk',sans-serif">${ax.label}</text>`;
  }).join('');
  
  // Labels dos valores (percentuais)
  const valueLabels1 = axes.map((ax, i) => {
    const pt = getPoint(s1[ax.key] || 0, i);
    const pct = ((s1[ax.key] || 0) * 100).toFixed(1);
    return `<text x="${pt.x.toFixed(1)}" y="${(pt.y - 8).toFixed(1)}" text-anchor="middle" fill="#E61D25" font-size="8" font-weight="700">${pct}%</text>`;
  }).join('');
  
  const valueLabels2 = axes.map((ax, i) => {
    const pt = getPoint(s2[ax.key] || 0, i);
    const pct = ((s2[ax.key] || 0) * 100).toFixed(1);
    return `<text x="${pt.x.toFixed(1)}" y="${(pt.y + 14).toFixed(1)}" text-anchor="middle" fill="#2A398D" font-size="8" font-weight="700">${pct}%</text>`;
  }).join('');
  
  const legendY = cy + r + 40;
  
  container.innerHTML = `
    <div style="text-align:center">
      <svg viewBox="0 0 300 340" style="max-width:350px;width:100%;height:auto">
        <!-- Grades -->
        ${gridPolygons.map((pts, i) => `<polygon points="${pts}" fill="none" stroke="var(--line)" stroke-width="0.5" opacity="${0.3 + i * 0.1}"/>`).join('')}
        
        <!-- Eixos -->
        ${axisLines}
        ${axisLabels}
        
        <!-- Time 1 (vermelho) -->
        <polygon points="${polygonPoints(s1)}" fill="rgba(230,29,37,0.2)" stroke="#E61D25" stroke-width="2"/>
        ${valueLabels1}
        
        <!-- Time 2 (azul) -->
        <polygon points="${polygonPoints(s2)}" fill="rgba(42,57,141,0.2)" stroke="#2A398D" stroke-width="2"/>
        ${valueLabels2}
        
        <!-- Centro -->
        <circle cx="${cx}" cy="${cy}" r="3" fill="var(--muted)"/>
        
        <!-- Legenda -->
        <rect x="40" y="${legendY}" width="12" height="12" fill="#E61D25" rx="2"/>
        <text x="56" y="${legendY + 10}" fill="var(--text)" font-size="11" font-family="'Space Grotesk',sans-serif">${t1}</text>
        <rect x="160" y="${legendY}" width="12" height="12" fill="#2A398D" rx="2"/>
        <text x="176" y="${legendY + 10}" fill="var(--text)" font-size="11" font-family="'Space Grotesk',sans-serif">${t2}</text>
      </svg>
    </div>`;
}

function renderFunnelChart() {
   const el = $('funnelChart');
  if (!el) return;
  const statsToUse = state.statsFull && Object.keys(state.statsFull).length > 0 ? state.statsFull : state.stats;
  if (!statsToUse) return;
  
  const phases = [
    { key: 'r32_prob', label: 'Fase de Grupos' },
    { key: 'r16_prob', label: 'Oitavas' },
    { key: 'quarterfinal_prob', label: 'Quartas' },
    { key: 'semifinal_prob', label: 'Semifinal' },
    { key: 'final_prob', label: 'Final' },
    { key: 'champion_prob', label: 'Título' },
  ];
  
  const top10 = Object.entries(statsToUse)
    .sort(([,a], [,b]) => (b.champion_prob || 0) - (a.champion_prob || 0))
    .slice(0, 10);

  el.innerHTML = `<div style="display:flex;gap:8px;overflow-x:auto;padding:8px 0">${phases.map(phase => `
    <div style="flex:1;min-width:80px;text-align:center">
      <div style="font-size:0.65rem;color:var(--muted);margin-bottom:4px">${phase.label}</div>
      <div style="background:var(--surface-soft);border-radius:8px;padding:8px 4px">
        ${top10.map(([team, s]) => { const pct = ((s[phase.key] || 0) * 100).toFixed(1); return `<div style="display:flex;align-items:center;gap:4px;padding:2px 0;font-size:0.7rem"><span style="width:16px;text-align:center">${flag(team)}</span><div style="flex:1;height:4px;background:rgba(0,0,0,0.05);border-radius:2px"><div style="width:${Math.min(pct,100)}%;height:100%;background:linear-gradient(90deg,var(--wc-blue),var(--wc-red));border-radius:2px"></div></div><span style="width:32px;text-align:right;font-weight:600">${pct}%</span></div>`; }).join('')}
      </div>
    </div>`).join('')}</div>`;
}

function renderBubbleChart() {
  const el = $('bubbleChart');
  if (!el) return;
  const statsToUse = state.statsFull && Object.keys(state.statsFull).length > 0 ? state.statsFull : state.stats;
  if (!statsToUse) return;
  
  const top16 = Object.entries(statsToUse)
    .sort(([,a], [,b]) => (b.champion_prob || 0) - (a.champion_prob || 0))
    .slice(0, 16);
  
  const maxChamp = top16[0]?.[1]?.champion_prob || 0.3;
  
  // Paleta vibrante: Azul → Verde → Amarelo → Laranja → Vermelho
  const getBubbleColor = (intensity) => {
    if (intensity < 0.25) {
      const t = intensity / 0.25;
      return `rgba(${Math.round(42 + 18*t)}, ${Math.round(57 + 115*t)}, ${Math.round(141 - 82*t)}, 0.85)`;
    } else if (intensity < 0.5) {
      const t = (intensity - 0.25) / 0.25;
      return `rgba(${Math.round(60 + 180*t)}, ${Math.round(172 + 36*t)}, ${Math.round(59 + 61*t)}, 0.85)`;
    } else if (intensity < 0.75) {
      const t = (intensity - 0.5) / 0.25;
      return `rgba(240, ${Math.round(208 - 179*t)}, ${Math.round(120 - 83*t)}, 0.85)`;
    } else {
      return `rgba(230, 29, 37, 0.85)`;
    }
  };
  
  el.innerHTML = `
    <div style="display:flex;flex-wrap:wrap;gap:16px;justify-content:center;align-items:flex-end;padding:8px">
      ${top16.map(([team, s]) => {
        const champPct = (s.champion_prob || 0) * 100;
        const size = Math.max(50, (s.champion_prob || 0) / maxChamp * 130);
        const intensity = (s.champion_prob || 0) / maxChamp;
        const bgColor = getBubbleColor(intensity);
        const isLight = intensity < 0.4;
        
        return `
          <div class="bubble-item" style="text-align:center;cursor:pointer;transition:transform 0.25s ease" 
               onmouseover="this.style.transform='translateY(-6px)'" 
               onmouseout="this.style.transform='translateY(0)'"
               title="${team}: ${champPct.toFixed(1)}%">
            <div class="bubble-circle" style="
              width:${size}px;
              height:${size}px;
              border-radius:50%;
              background:radial-gradient(circle at 40% 38%, rgba(255,255,255,0.5) 0%, ${bgColor} 70%);
              display:flex;
              align-items:center;
              justify-content:center;
              margin:0 auto 6px;
              font-size:${size > 80 ? '1.6rem' : '1.1rem'};
              box-shadow:0 6px 20px ${bgColor.replace('0.85', '0.3')};
              border:2px solid rgba(255,255,255,0.3);
              transition:box-shadow 0.25s ease;
            ">
              ${flag(team)}
            </div>
            <div style="font-size:0.7rem;font-weight:600;color:var(--text);line-height:1.2">${team}</div>
            <div style="font-size:0.8rem;font-weight:800;color:var(--text-strong)">${champPct.toFixed(1)}%</div>
          </div>`;
      }).join('')}
    </div>`;
}

// ============================================================
// COMPARAR
// ============================================================

function compareTeams() {
  const el = $('compareResults');
  const t1 = $('compareTeam1')?.value;
  const t2 = $('compareTeam2')?.value;
  if (!el) return;
  if (!t1 || !t2) { el.innerHTML = '<p style="color:#10293d;text-align:center;padding:40px">Selecione dois times para comparar</p>'; return; }
  if (t1 === t2) { el.innerHTML = '<p style="color:#10293d;text-align:center;padding:40px">Selecione times diferentes</p>'; return; }
  const statsToUse = state.statsFull && Object.keys(state.statsFull).length > 0 ? state.statsFull : state.stats;
  if (!statsToUse || Object.keys(statsToUse).length === 0) { el.innerHTML = '<p style="color:#10293d;text-align:center;padding:40px">⏳ Estatísticas não carregadas.</p>'; return; }
  const s1 = statsToUse[t1];
  const s2 = statsToUse[t2];
  if (!s1 || !s2) { el.innerHTML = '<p style="color:#10293d;text-align:center;padding:40px">Dados não encontrados.</p>'; return; }
  const fp = (v) => v != null ? ((v || 0) * 100).toFixed(1) + '%' : '0.0%';
  const c1 = (s1.champion_prob || 0), c2 = (s2.champion_prob || 0);
  const diff = ((c1 - c2) * 100).toFixed(1);
  const advantage = c1 > c2 ? t1 : c2 > c1 ? t2 : null;
  el.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:20px;align-items:start">
      <div class="compare-team-card"><div style="font-size:3rem;margin-bottom:8px">${flag(t1)}</div><h4 style="color:#10293d!important;margin:0 0 16px">${t1}</h4>
        <div class="compare-stat"><span class="compare-stat-label">🏆 Campeão</span><span class="compare-stat-value highlight">${fp(s1.champion_prob)}</span></div>
        <div class="compare-stat"><span class="compare-stat-label">🥈 Final</span><span class="compare-stat-value">${fp(s1.final_prob)}</span></div>
        <div class="compare-stat"><span class="compare-stat-label">🥉 Semifinal</span><span class="compare-stat-value">${fp(s1.semifinal_prob)}</span></div>
        <div class="compare-stat"><span class="compare-stat-label">🏟️ Quartas</span><span class="compare-stat-value">${fp(s1.quarterfinal_prob)}</span></div>
        <div class="compare-stat"><span class="compare-stat-label">📊 Oitavas</span><span class="compare-stat-value">${fp(s1.r16_prob)}</span></div>
      </div>
      <div style="text-align:center;align-self:center"><div style="font-size:1.5rem;font-weight:700;color:#5d7689">VS</div><div style="font-size:0.7rem;color:#5d7689;margin-top:4px">Diferença</div><div style="font-size:0.9rem;color:#0aa6a6;margin-top:4px;font-weight:600">${diff}%</div></div>
      <div class="compare-team-card"><div style="font-size:3rem;margin-bottom:8px">${flag(t2)}</div><h4 style="color:#10293d!important;margin:0 0 16px">${t2}</h4>
        <div class="compare-stat"><span class="compare-stat-label">🏆 Campeão</span><span class="compare-stat-value highlight">${fp(s2.champion_prob)}</span></div>
        <div class="compare-stat"><span class="compare-stat-label">🥈 Final</span><span class="compare-stat-value">${fp(s2.final_prob)}</span></div>
        <div class="compare-stat"><span class="compare-stat-label">🥉 Semifinal</span><span class="compare-stat-value">${fp(s2.semifinal_prob)}</span></div>
        <div class="compare-stat"><span class="compare-stat-label">🏟️ Quartas</span><span class="compare-stat-value">${fp(s2.quarterfinal_prob)}</span></div>
        <div class="compare-stat"><span class="compare-stat-label">📊 Oitavas</span><span class="compare-stat-value">${fp(s2.r16_prob)}</span></div>
      </div>
    </div>
    <div style="margin-top:20px;padding:16px;background:#f7fbfc;border-radius:12px;text-align:center;border:1px solid rgba(9,34,53,0.1)">
      <p style="color:#10293d;margin:0;font-size:0.9rem">${advantage ? `📊 <strong>${flag(advantage)} ${advantage}</strong> é favorito com ${fp(advantage === t1 ? s1.champion_prob : s2.champion_prob)} de chance de título` : '🤝 <strong>Equilíbrio total</strong>'}</p>
      <p style="color:#5d7689;margin:8px 0 0 0;font-size:0.75rem">Baseado em 100.000 simulações</p>
    </div>`;
  renderRadarChart(t1, t2);
}

// ============================================================
// SIMULAÇÃO
// ============================================================

function renderSimulation(payload) {
  if (!payload) return;
  state.currentSimulation = payload;
  const { summary, bracket, groups } = payload;
  renderMetrics(summary);
  renderMainSummary(summary, bracket);
  renderResultsTable();
  renderBracket(bracket?.rounds);
  renderGroups(groups, bracket?.classified_teams);
  renderClassified(bracket?.classified_teams);
  const tag = $('selectedSimulationTag');
  if (tag) tag.textContent = `#${summary?.simulation ?? '—'} · ${summary?.slot_combination ?? '—'}`;
}

async function loadSimulation(id) {
  if (id == null) return;
  try { const data = await fetchJSON(`/api/simulation/${id}`, { force: true }); if (data) renderSimulation(data); }
  catch (err) { console.error(err); }
}

// ============================================================
// FILTROS
// ============================================================

async function applyFilters() {
  try {
    const data = await fetchJSON(`/api/filter?${buildFilterQuery()}`);
    state.filtered = data?.results || [];
    const fs = $('filterSummary'); if (fs) fs.textContent = `${fm(data?.total || 0)} cenários`;
    if (!state.filtered.length) {
      const tbody = $('resultsTable')?.querySelector('tbody'); if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Nenhum cenário encontrado</td></tr>';
      const cd = $('championDistribution'); if (cd) cd.innerHTML = '<div class="empty-state"><p>—</p></div>';
      return;
    }
    const avail = state.filtered.some(r => r.simulation === state.selectedSimulation);
    if (!avail) state.selectedSimulation = state.filtered[0].simulation;
    renderResultsTable(); renderChampionDist(); updateSimSelect();
    await loadSimulation(state.selectedSimulation);
  } catch (err) { console.error('Erro ao filtrar:', err); }
}

function updateSimSelect() {
  const sel = $('simulationSelect'); if (!sel) return;
  sel.innerHTML = state.filtered.map(r => `<option value="${r.simulation}">#${r.simulation} · ${r.champion}</option>`).join('');
  sel.value = String(state.selectedSimulation);
}

function resetFilters() {
  ['championFilter','combinationFilter','thirdGroupFilter'].forEach(id => { const sel = $(id); if (sel) $$('option', sel).forEach(o => o.selected = false); });
  const tf = $('teamFilter'); if (tf) tf.value = '';
  const sf = $('stageFilter'); if (sf) sf.value = 'qualified';
  const qs = $('quickSearch'); if (qs) qs.value = '';
  applyFilters();
}

// ============================================================
// SIDEBAR
// ============================================================

function setupSidebarToggle() {
  const sidebar = document.querySelector('.sidebar');
  const toggleBtn = document.getElementById('sidebarToggle');
  if (!sidebar || !toggleBtn) return;
  const saved = localStorage.getItem('sidebar-collapsed');
  if (saved === 'true') { sidebar.classList.add('collapsed'); toggleBtn.textContent = '▶'; }
  toggleBtn.addEventListener('click', () => {
    const collapsed = sidebar.classList.toggle('collapsed');
    toggleBtn.textContent = collapsed ? '▶' : '◀';
    localStorage.setItem('sidebar-collapsed', collapsed);
  });
}

// ============================================================
// TABS
// ============================================================

function switchTab(tabId) {
  state.activeTab = tabId;
  $$('.tab-btn').forEach(b => { const active = b.dataset.tab === tabId; b.classList.toggle('active', active); b.setAttribute('aria-selected', active); });
  $$('.tab-panel').forEach(p => p.classList.toggle('active', p.id === `tab-${tabId}`));
  if (tabId === 'stats') { renderStats(); renderH2HStats(); renderBubbleChart(); }
  if (tabId === 'heatmap') { renderHeatmap(); }
  if (tabId === 'overview') { renderFunnelChart(); }
}

// ============================================================
// MOBILE
// ============================================================

function setupMobile() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.sidebar-overlay');
  const open = () => { sidebar?.classList.add('open'); overlay?.classList.add('visible'); document.body.style.overflow = 'hidden'; };
  const close = () => { sidebar?.classList.remove('open'); overlay?.classList.remove('visible'); document.body.style.overflow = ''; };
  document.querySelector('.mobile-menu-btn')?.addEventListener('click', open);
  document.querySelector('.sidebar-close')?.addEventListener('click', close);
  overlay?.addEventListener('click', close);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
}

// ============================================================
// MODO ESCURO
// ============================================================

function setupThemeToggle() {
  const toggle = document.getElementById('themeToggle');
  if (!toggle) return;
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'dark') { document.body.classList.add('dark-mode'); toggle.textContent = '☀️'; toggle.setAttribute('data-tooltip', 'Modo claro'); }
  if (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches) { document.body.classList.add('dark-mode'); toggle.textContent = '☀️'; toggle.setAttribute('data-tooltip', 'Modo claro'); }
  toggle.addEventListener('click', () => {
    const isDark = document.body.classList.toggle('dark-mode');
    toggle.textContent = isDark ? '☀️' : '🌙';
    toggle.setAttribute('data-tooltip', isDark ? 'Modo claro' : 'Modo escuro');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  });
}

// ============================================================
// INIT
// ============================================================

async function init() {
  console.log('🚀 Iniciando...');
  try {
    document.body.classList.add('is-initializing');
    
    // Carregar meta
    const meta = await fetchJSON('/api/meta');
    if (!meta) throw new Error('Meta não carregado');
    state.meta = meta;
    console.log('✅ Meta:', meta.champions?.length, 'campeões,', meta.teams?.length, 'times');
    
    // ═══════════════════════════════════════════
    // CARREGAR STATS COM AWAIT (não .then)
    // ═══════════════════════════════════════════
    try {
      const rawStats = await fetchJSON('/api/stats');
      if (rawStats) {
        const normalized = normalizeStats(rawStats);
        state.statsFull = normalized;
        state.stats = normalized;
        console.log('✅ Stats completos carregados:', Object.keys(state.statsFull).length, 'times');
        
        // Verificar se tem dados reais
        const sample = Object.values(normalized)[0];
        if (sample) {
          console.log('  → Exemplo:', Object.keys(sample).slice(0, 5));
          console.log('  → champion_prob:', sample.champion_prob);
          console.log('  → final_prob:', sample.final_prob);
        }
      } else {
        console.warn('⚠️ Stats retornaram vazio');
      }
    } catch (statsErr) {
      console.warn('⚠️ Erro ao carregar stats:', statsErr.message);
    }
    
    // Quick stats
    const qs = $('quickStats');
    if (qs) {
      qs.innerHTML = `
        <div class="stat-mini">
          <span class="stat-mini-value">${fm(meta.total_simulations || 100000)}</span>
          <span class="stat-mini-label">Cenários</span>
        </div>
        <div class="stat-mini">
          <span class="stat-mini-value">${meta.teams?.length || 48}</span>
          <span class="stat-mini-label">Times</span>
        </div>`;
    }
    
    // Preencher selects
    setMultiOptions($('championFilter'), meta.champions || []);
    setMultiOptions($('combinationFilter'), meta.combinations || []);
    setMultiOptions($('thirdGroupFilter'), meta.third_groups || []);
    setSingleOptions($('teamFilter'), meta.teams || [], true);
    setSingleOptions($('compareTeam1'), meta.teams || [], true);
    setSingleOptions($('compareTeam2'), meta.teams || [], true);
    setupSidebarToggle();
    
    // Eventos
    $('applyFilters')?.addEventListener('click', e => { e.preventDefault(); applyFilters(); });
    $('resetFilters')?.addEventListener('click', e => { e.preventDefault(); resetFilters(); });
    $('simulationSelect')?.addEventListener('change', e => { const v = Number(e.target.value); if (!isNaN(v)) selectSim(v); });
    $('compareBtn')?.addEventListener('click', () => compareTeams());
    
    $$('.tab-btn').forEach(btn => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));
    
    ['championFilter', 'combinationFilter', 'thirdGroupFilter'].forEach(id => {
      $(id)?.addEventListener('change', () => setTimeout(applyFilters, 200));
    });
    
    setupMobile();
    setupThemeToggle();
    
    // Navegação entre simulações
    $('prevSim')?.addEventListener('click', () => {
      const idx = state.filtered.findIndex(r => r.simulation === state.selectedSimulation);
      if (idx > 0) selectSim(state.filtered[idx - 1].simulation);
    });

    $('nextSim')?.addEventListener('click', () => {
      const idx = state.filtered.findIndex(r => r.simulation === state.selectedSimulation);
      if (idx < state.filtered.length - 1) selectSim(state.filtered[idx + 1].simulation);
    });
    
    // Heatmap metric
    $('heatmapMetric')?.addEventListener('change', () => renderHeatmap());
    
    // Chips de favoritos
    $$('.filter-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const team = chip.dataset.team;
        chip.classList.toggle('active');
        const champSelect = $('championFilter');
        if (champSelect) {
          const option = Array.from(champSelect.options).find(o => o.value === team);
          if (option) {
            option.selected = chip.classList.contains('active');
            applyFilters();
          }
        }
      });
    });
    
    // Aplicar filtros iniciais
    await applyFilters();
    
    // ═══════════════════════════════════════════
    // DEBUG: Verificar estado final
    // ═══════════════════════════════════════════
    console.log('📊 Estado final:');
    console.log('  - statsFull:', Object.keys(state.statsFull).length, 'times');
    console.log('  - stats:', Object.keys(state.stats).length, 'times');
    console.log('  - filtered:', state.filtered.length, 'resultados');
    const firstTeam = Object.keys(state.statsFull)[0];
    if (firstTeam) {
      console.log('  - Exemplo', firstTeam + ':', state.statsFull[firstTeam]);
    }
    
    console.log('✅ Pronto!');
  } catch (err) {
    console.error('❌ Erro na inicialização:', err);
  } finally {
    document.body.classList.remove('is-initializing');
    document.body.classList.add('loaded');
  }
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();