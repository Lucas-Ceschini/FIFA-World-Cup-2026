const state = {
  meta: null,
  filtered: [],
  selectedSimulation: 0,
  currentSimulation: null,
  stats: null,
};

const FLAGS = {
  "Spain":"🇪🇸","England":"🏴","France":"🇫🇷","Argentina":"🇦🇷","Brazil":"🇧🇷",
  "Germany":"🇩🇪","Portugal":"🇵🇹","Netherlands":"🇳🇱","Belgium":"🇧🇪","Italy":"🇮🇹",
  "Uruguay":"🇺🇾","USA":"🇺🇸","Mexico":"🇲🇽","Colombia":"🇨🇴","Japan":"🇯🇵",
  "Morocco":"🇲🇦","Senegal":"🇸🇳","Australia":"🇦🇺","Croatia":"🇭🇷","Switzerland":"🇨🇭",
  "Sweden":"🇸🇪","Norway":"🇳🇴","Denmark":"🇩🇰","Poland":"🇵🇱","Serbia":"🇷🇸",
  "Canada":"🇨🇦","Ecuador":"🇪🇨","Tunisia":"🇹🇳","South Korea":"🇰🇷","Algeria":"🇩🇿",
  "Scotland":"🏴","Türkiye":"🇹🇷","Iran":"🇮🇷","Ghana":"🇬🇭","DR Congo":"🇨🇩",
  "Bosnia-Herzegovina":"🇧🇦","Ivory Coast":"🇨🇮","Austria":"🇦🇹","Paraguay":"🇵🇾",
  "Saudi Arabia":"🇸🇦","Panama":"🇵🇦","Iraq":"🇮🇶","Uzbekistan":"🇺🇿","Egypt":"🇪🇬",
  "Cape Verde":"🇨🇻","Jordan":"🇯🇴","South Africa":"🇿🇦","Qatar":"🇶🇦","Haiti":"🇭🇹",
  "New Zealand":"🇳🇿","Curacao":"🇨🇼","Czechia":"🇨🇿"
};

const PHASE_TITLES = {
  R32: "Rodada de 32",
  R16: "Oitavas",
  QF: "Quartas",
  SF: "Semifinais",
  THIRD_PLACE: "3º Lugar",
  FINAL: "Final"
};

function flag(team) {
  return FLAGS[team] || "🏳️";
}

function $(id) {
  return document.getElementById(id);
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Falha ao carregar ${url}`);
  }
  return response.json();
}

function setMultiOptions(selectEl, values) {
  selectEl.innerHTML = values
    .map((value) => `<option value="${value}">${value}</option>`)
    .join("");
}

function setSingleOptions(selectEl, values, includeEmpty = false) {
  const options = [];
  if (includeEmpty) {
    options.push('<option value="">Todos</option>');
  }
  options.push(...values.map((value) => `<option value="${value}">${value}</option>`));
  selectEl.innerHTML = options.join("");
}

function selectedValues(selectEl) {
  return Array.from(selectEl.selectedOptions).map((option) => option.value).filter(Boolean);
}

function buildFilterQuery() {
  const params = new URLSearchParams();
  selectedValues($("championFilter")).forEach((value) => params.append("champion", value));
  selectedValues($("combinationFilter")).forEach((value) => params.append("combination", value));
  selectedValues($("thirdGroupFilter")).forEach((value) => params.append("third_group", value));

  if ($("teamFilter").value) {
    params.append("team", $("teamFilter").value);
    params.append("stage", $("stageFilter").value);
  }

  params.append("limit", "250");
  return params.toString();
}

function renderMetrics(summary) {
  const metricsEl = $("metrics");
  const finalMatch = state.currentSimulation.bracket.rounds.FINAL;
  const cards = [
    {
      label: "Cenários filtrados",
      value: state.filtered.length.toLocaleString("pt-BR"),
      sub: "Escopo retornado para a consulta"
    },
    {
      label: "Simulação",
      value: `#${summary.simulation}`,
      sub: `Combinação ${summary.slot_combination}`
    },
    {
      label: "Campeão",
      value: `${flag(summary.champion)} ${summary.champion}`,
      sub: "Desfecho deste universo",
      gold: true
    },
    {
      label: "Vice",
      value: `${flag(summary.runner_up)} ${summary.runner_up}`,
      sub: `${flag(finalMatch.team_a)} ${finalMatch.team_a} x ${flag(finalMatch.team_b)} ${finalMatch.team_b}`
    },
    {
      label: "3º Lugar",
      value: `${flag(summary.third_place)} ${summary.third_place}`,
      sub: `Grupos dos 3ºs: ${summary.third_place_groups.join(", ")}`
    }
  ];

  metricsEl.innerHTML = cards.map((card) => `
    <article class="metric-card ${card.gold ? "gold" : ""}">
      <div class="metric-label">${card.label}</div>
      <div class="metric-value">${card.value}</div>
      <div class="metric-sub">${card.sub}</div>
    </article>
  `).join("");
}

function renderChampionDistribution() {
  const counts = new Map();
  state.filtered.forEach((row) => {
    counts.set(row.champion, (counts.get(row.champion) || 0) + 1);
  });

  const rows = Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const total = state.filtered.length || 1;

  $("championDistribution").innerHTML = rows.map(([team, count]) => {
    const pct = (count / total) * 100;
    return `
      <div class="bar-row">
        <div class="bar-head">
          <span>${flag(team)} ${team}</span>
          <span>${pct.toFixed(1)}%</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" style="width:${pct.toFixed(2)}%"></div>
        </div>
      </div>
    `;
  }).join("");
}

function renderResultsTable() {
  const tbody = $("resultsTable").querySelector("tbody");
  tbody.innerHTML = state.filtered.map((row) => `
    <tr data-simulation="${row.simulation}" class="${row.simulation === state.selectedSimulation ? "active" : ""}">
      <td>#${row.simulation}</td>
      <td>${row.slot_combination}</td>
      <td>${flag(row.champion)} ${row.champion}</td>
      <td>${flag(row.runner_up)} ${row.runner_up}</td>
      <td>${flag(row.third_place)} ${row.third_place}</td>
      <td>${row.third_place_groups.join(", ")}</td>
    </tr>
  `).join("");

  tbody.querySelectorAll("tr").forEach((row) => {
    row.addEventListener("click", () => {
      $("simulationSelect").value = row.dataset.simulation;
      state.selectedSimulation = Number(row.dataset.simulation);
      loadSimulation(state.selectedSimulation);
    });
  });
}

function renderSimulationOptions() {
  $("simulationSelect").innerHTML = state.filtered
    .map((row) => `<option value="${row.simulation}">#${row.simulation} · ${row.champion}</option>`)
    .join("");
  $("simulationSelect").value = String(state.selectedSimulation);
}

function renderClassifiedTable(classifiedTeams) {
  const tbody = $("classifiedTable").querySelector("tbody");
  tbody.innerHTML = classifiedTeams.map((team) => `
    <tr>
      <td>${flag(team.country)} ${team.country}</td>
      <td>${team.group}</td>
      <td>${team.position}</td>
      <td><span class="tag ${team.type}">${team.type}</span></td>
    </tr>
  `).join("");
}

function renderBracket(rounds) {
  const grid = $("bracketGrid");
  grid.innerHTML = Object.entries(PHASE_TITLES).map(([phase, title]) => {
    const phaseData = rounds[phase];
    const matches = Array.isArray(phaseData) ? phaseData : [phaseData];
    return `
      <section class="bracket-col">
        <h4>${title}</h4>
        ${matches.map((match) => `
          <article class="match-card">
            <div class="match-topline">
              <span>Jogo ${match.game}</span>
              <span>${match.phase}</span>
            </div>
            ${renderTeamLine(match, "a")}
            ${renderTeamLine(match, "b")}
            <div class="winner-pill">Vencedor: ${flag(match.winner)} ${match.winner}</div>
          </article>
        `).join("")}
      </section>
    `;
  }).join("");
}

function renderTeamLine(match, side) {
  const team = match[`team_${side}`];
  const isWinner = match.winner === team;
  return `
    <div class="team-line">
      <div class="team-main">
        <span class="flag">${flag(team)}</span>
        <span class="team-name ${isWinner ? "winner" : ""}">${team}</span>
      </div>
      <div class="team-meta">
        ${match[`team_${side}_slot`]} · ${match[`team_${side}_group`]} · ${(match[`probability_${side}`] * 100).toFixed(1)}%
      </div>
    </div>
  `;
}

function renderGroups(groups, classifiedTeams) {
  const classifiedMap = new Map(classifiedTeams.map((team) => [team.country, team.type]));
  $("groupsGrid").innerHTML = groups.map((group) => `
    <article class="group-card">
      <h4>${group.group}</h4>
      ${group.ranking.map((team) => {
        const status = classifiedMap.get(team.country) || "eliminated";
        return `
          <div class="group-row">
            <span class="group-pos pos-${team.position}">${team.position}</span>
            <div class="team-main">
              <span class="flag">${flag(team.country)}</span>
              <span class="team-name">${team.country}</span>
            </div>
            <span class="tag ${status}">${status}</span>
          </div>
        `;
      }).join("")}
    </article>
  `).join("");
}

function renderSimulation(payload) {
  state.currentSimulation = payload;
  const { summary, bracket, groups } = payload;
  renderMetrics(summary);
  renderResultsTable();
  renderClassifiedTable(bracket.classified_teams);
  renderBracket(bracket.rounds);
  renderGroups(groups.groups, bracket.classified_teams);
  $("selectedSimulationTag").textContent = `Simulação #${summary.simulation} · combinação ${summary.slot_combination}`;
}

async function loadSimulation(simulationId) {
  const payload = await fetchJson(`/api/simulation/${simulationId}`);
  renderSimulation(payload);
}

async function applyFilters() {
  const payload = await fetchJson(`/api/filter?${buildFilterQuery()}`);
  state.filtered = payload.results;
  $("filterSummary").textContent = `${payload.total.toLocaleString("pt-BR")} cenários encontrados`;

  if (!state.filtered.length) {
    $("resultsTable").querySelector("tbody").innerHTML = "";
    $("championDistribution").innerHTML = "<div>Nenhum cenário encontrado.</div>";
    $("simulationSelect").innerHTML = "";
    return;
  }

  const stillAvailable = state.filtered.some((row) => row.simulation === state.selectedSimulation);
  state.selectedSimulation = stillAvailable ? state.selectedSimulation : state.filtered[0].simulation;
  renderChampionDistribution();
  renderSimulationOptions();
  await loadSimulation(state.selectedSimulation);
}

function resetFilters() {
  ["championFilter", "combinationFilter", "thirdGroupFilter"].forEach((id) => {
    Array.from($(id).options).forEach((option) => {
      option.selected = false;
    });
  });
  $("teamFilter").value = "";
  $("stageFilter").value = "qualified";
  applyFilters();
}

async function init() {
  const [meta, stats] = await Promise.all([
    fetchJson("/api/meta"),
    fetchJson("/api/stats"),
  ]);

  state.meta = meta;
  state.stats = stats;

  setMultiOptions($("championFilter"), meta.champions);
  setMultiOptions($("combinationFilter"), meta.combinations);
  setMultiOptions($("thirdGroupFilter"), meta.third_groups);
  setSingleOptions($("teamFilter"), meta.teams, true);

  $("applyFilters").addEventListener("click", applyFilters);
  $("resetFilters").addEventListener("click", resetFilters);
  $("simulationSelect").addEventListener("change", (event) => {
    state.selectedSimulation = Number(event.target.value);
    loadSimulation(state.selectedSimulation);
  });

  await applyFilters();
}

init().catch((error) => {
  console.error(error);
  document.body.innerHTML = `<pre style="padding:24px;color:#b00020">${error.stack}</pre>`;
});
