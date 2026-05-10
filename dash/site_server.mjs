import fs from "node:fs";
import path from "node:path";
import http from "node:http";
import { fileURLToPath } from "node:url";
import { execFile } from "node:child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "..");
const SITE_ROOT = path.join(__dirname, "site");
const DATA_ROOT = path.join(ROOT, "data");

const INDEX_PATH = path.join(DATA_ROOT, "worldcup_2026_dashboard_index.json");
const STATS_PATH = path.join(DATA_ROOT, "knockout_tree_statistics.json");
const FINAL_PROBS_PATH = path.join(DATA_ROOT, "final_probabilities.json");
const BRACKET_NDJSON_PATH = path.join(DATA_ROOT, "worldcup_2026_full_bracket.ndjson");
const GROUPS_NDJSON_PATH = path.join(DATA_ROOT, "group_scenarios.ndjson");

const HOST = "127.0.0.1";
const PORT = 8000;

const INDEX = JSON.parse(fs.readFileSync(INDEX_PATH, "utf8"));
const TEAM_STATS = JSON.parse(fs.readFileSync(STATS_PATH, "utf8"));
const FINAL_PROBS = JSON.parse(fs.readFileSync(FINAL_PROBS_PATH, "utf8"));

const ALL_TEAMS = [...new Set(INDEX.flatMap((entry) => entry.qualified_teams))].sort();
const ALL_CHAMPIONS = [...new Set(INDEX.map((entry) => entry.champion))].sort();
const ALL_COMBINATIONS = [...new Set(INDEX.map((entry) => entry.slot_combination))].sort((a, b) => a - b);
const ALL_THIRD_GROUPS = [...new Set(INDEX.flatMap((entry) => entry.third_place_groups))].sort();

function sendJson(res, payload, status = 200) {
  const body = Buffer.from(JSON.stringify(payload), "utf8");
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": body.length,
    "Cache-Control": "no-store",
  });
  res.end(body);
}

function sendFile(res, filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const contentTypes = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
  };

  if (!fs.existsSync(filePath)) {
    sendJson(res, { error: "arquivo não encontrado" }, 404);
    return;
  }

  res.writeHead(200, {
    "Content-Type": contentTypes[ext] || "application/octet-stream",
  });
  fs.createReadStream(filePath).pipe(res);
}

function sedLine(filePath, lineNumber) {
  return new Promise((resolve, reject) => {
    execFile("sed", ["-n", `${lineNumber}p`, filePath], { maxBuffer: 50 * 1024 * 1024 }, (error, stdout) => {
      if (error) {
        reject(error);
        return;
      }
      if (!stdout.trim()) {
        reject(new Error(`Linha ${lineNumber} não encontrada em ${filePath}`));
        return;
      }
      resolve(JSON.parse(stdout));
    });
  });
}

function containsTeam(entry, stage, teamName) {
  if (stage === "qualified") return entry.qualified_teams.includes(teamName);
  if (stage === "r16") return entry.r16_teams.includes(teamName);
  if (stage === "qf") return entry.qf_teams.includes(teamName);
  if (stage === "sf") return entry.sf_teams.includes(teamName);
  if (stage === "final") return entry.final_teams.includes(teamName);
  if (stage === "champion") return entry.champion === teamName;
  return true;
}

function filterIndex(searchParams) {
  const champions = new Set(searchParams.getAll("champion"));
  const combinations = new Set(searchParams.getAll("combination").map((value) => Number(value)));
  const thirdGroups = new Set(searchParams.getAll("third_group"));
  const team = searchParams.get("team") || "";
  const stage = searchParams.get("stage") || "qualified";
  const limit = Math.min(Number(searchParams.get("limit") || 250), 500);

  const rows = INDEX.filter((entry) => {
    if (champions.size && !champions.has(entry.champion)) return false;
    if (combinations.size && !combinations.has(entry.slot_combination)) return false;
    if (thirdGroups.size && ![...thirdGroups].every((group) => entry.third_place_groups.includes(group))) return false;
    if (team && !containsTeam(entry, stage, team)) return false;
    return true;
  });

  return { total: rows.length, results: rows.slice(0, limit) };
}

async function getSimulationPayload(simulationId) {
  const summary = INDEX[simulationId];
  const lineNumber = summary.ndjson_line;
  const [bracket, groups] = await Promise.all([
    sedLine(BRACKET_NDJSON_PATH, lineNumber),
    sedLine(GROUPS_NDJSON_PATH, lineNumber),
  ]);
  return { summary, bracket, groups };
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${HOST}:${PORT}`);

  if (url.pathname === "/api/meta") {
    sendJson(res, {
      total_simulations: INDEX.length,
      teams: ALL_TEAMS,
      champions: ALL_CHAMPIONS,
      combinations: ALL_COMBINATIONS,
      third_groups: ALL_THIRD_GROUPS,
    });
    return;
  }

  if (url.pathname === "/api/stats") {
    sendJson(res, {
      team_stats: TEAM_STATS,
      final_probabilities: FINAL_PROBS,
    });
    return;
  }

  if (url.pathname === "/api/filter") {
    sendJson(res, filterIndex(url.searchParams));
    return;
  }

  if (url.pathname.startsWith("/api/simulation/")) {
    const simulationId = Number(url.pathname.split("/").pop());
    if (!Number.isInteger(simulationId) || simulationId < 0 || simulationId >= INDEX.length) {
      sendJson(res, { error: "simulation id inválido" }, 404);
      return;
    }

    try {
      sendJson(res, await getSimulationPayload(simulationId));
    } catch (error) {
      sendJson(res, { error: error.message }, 500);
    }
    return;
  }

  const route = url.pathname === "/" ? "/index.html" : url.pathname;
  const filePath = path.normalize(path.join(SITE_ROOT, route));
  if (!filePath.startsWith(SITE_ROOT)) {
    sendJson(res, { error: "rota inválida" }, 400);
    return;
  }

  sendFile(res, filePath);
});

server.listen(PORT, HOST, () => {
  console.log(`Site disponível em http://${HOST}:${PORT}`);
});

process.on("SIGINT", () => {
  console.log("\nServidor encerrado pelo usuário.");
  server.close(() => process.exit(0));
});
