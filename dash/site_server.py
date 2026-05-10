import json
from functools import lru_cache
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = ROOT / "dash" / "site"
DATA_ROOT = ROOT / "data"

INDEX_PATH = DATA_ROOT / "worldcup_2026_dashboard_index.json"
BRACKET_NDJSON_PATH = DATA_ROOT / "worldcup_2026_full_bracket.ndjson"
GROUPS_NDJSON_PATH = DATA_ROOT / "group_scenarios.ndjson"
STATS_PATH = DATA_ROOT / "knockout_tree_statistics.json"
FINAL_PROBS_PATH = DATA_ROOT / "final_probabilities.json"

BRACKET_OFFSETS_PATH = DATA_ROOT / "worldcup_2026_full_bracket.offsets.json"
GROUP_OFFSETS_PATH = DATA_ROOT / "group_scenarios.offsets.json"

HOST = "127.0.0.1"
PORT = 8000


def build_offsets(ndjson_path: Path, offsets_path: Path):
    if offsets_path.exists():
        with offsets_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    offsets = []
    offset = 0
    with ndjson_path.open("rb") as f:
        for line in f:
            offsets.append(offset)
            offset += len(line)

    with offsets_path.open("w", encoding="utf-8") as f:
        json.dump(offsets, f)

    return offsets


def read_ndjson_at_offset(path: Path, offset: int):
    with path.open("rb") as f:
        f.seek(offset)
        line = f.readline()
    return json.loads(line.decode("utf-8"))


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


INDEX = load_json(INDEX_PATH)
TEAM_STATS = load_json(STATS_PATH)
FINAL_PROBS = load_json(FINAL_PROBS_PATH)
BRACKET_OFFSETS = build_offsets(BRACKET_NDJSON_PATH, BRACKET_OFFSETS_PATH)
GROUP_OFFSETS = build_offsets(GROUPS_NDJSON_PATH, GROUP_OFFSETS_PATH)

ALL_TEAMS = sorted({team for entry in INDEX for team in entry["qualified_teams"]})
ALL_CHAMPIONS = sorted({entry["champion"] for entry in INDEX})
ALL_COMBINATIONS = sorted({entry["slot_combination"] for entry in INDEX})
ALL_THIRD_GROUPS = sorted({group for entry in INDEX for group in entry["third_place_groups"]})


def contains_team(entry, stage, team_name):
    if stage == "qualified":
        return team_name in entry["qualified_teams"]
    if stage == "r16":
        return team_name in entry["r16_teams"]
    if stage == "qf":
        return team_name in entry["qf_teams"]
    if stage == "sf":
        return team_name in entry["sf_teams"]
    if stage == "final":
        return team_name in entry["final_teams"]
    if stage == "champion":
        return team_name == entry["champion"]
    return True


def filter_index(query):
    champions = set(query.get("champion", []))
    combinations = {int(value) for value in query.get("combination", []) if value}
    third_groups = set(query.get("third_group", []))
    team = query.get("team", [""])[0]
    stage = query.get("stage", ["qualified"])[0]
    limit = min(int(query.get("limit", ["200"])[0]), 500)

    rows = []
    for entry in INDEX:
        if champions and entry["champion"] not in champions:
            continue
        if combinations and entry["slot_combination"] not in combinations:
            continue
        if third_groups and not third_groups.issubset(set(entry["third_place_groups"])):
            continue
        if team and not contains_team(entry, stage, team):
            continue
        rows.append(entry)

    return {
        "total": len(rows),
        "results": rows[:limit],
    }


@lru_cache(maxsize=1024)
def get_simulation_payload(simulation_id: int):
    entry = INDEX[simulation_id]
    line_index = entry["ndjson_line"] - 1
    bracket = read_ndjson_at_offset(BRACKET_NDJSON_PATH, BRACKET_OFFSETS[line_index])
    groups = read_ndjson_at_offset(GROUPS_NDJSON_PATH, GROUP_OFFSETS[line_index])
    return {"summary": entry, "bracket": bracket, "groups": groups}


class SiteHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_ROOT), **kwargs)

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/meta":
            self.send_json(
                {
                    "total_simulations": len(INDEX),
                    "teams": ALL_TEAMS,
                    "champions": ALL_CHAMPIONS,
                    "combinations": ALL_COMBINATIONS,
                    "third_groups": ALL_THIRD_GROUPS,
                }
            )
            return

        if parsed.path == "/api/stats":
            self.send_json({"team_stats": TEAM_STATS, "final_probabilities": FINAL_PROBS})
            return

        if parsed.path == "/api/filter":
            self.send_json(filter_index(parse_qs(parsed.query)))
            return

        if parsed.path.startswith("/api/simulation/"):
            try:
                simulation_id = int(parsed.path.rsplit("/", 1)[-1])
            except ValueError:
                self.send_json({"error": "simulation id inválido"}, status=400)
                return

            if simulation_id < 0 or simulation_id >= len(INDEX):
                self.send_json({"error": "simulation id fora do intervalo"}, status=404)
                return

            self.send_json(get_simulation_payload(simulation_id))
            return

        if parsed.path == "/":
            self.path = "/index.html"

        return super().do_GET()


def main():
    print(f"Site disponível em http://{HOST}:{PORT}")
    server = ThreadingHTTPServer((HOST, PORT), SiteHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado pelo usuário.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
