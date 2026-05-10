import json
import sqlite3
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRACKET_PATH = ROOT / "data/worldcup_2026_full_bracket.json"
GROUPS_PATH = ROOT / "data/group_scenarios.json"
DB_PATH = ROOT / "data/worldcup_2026_dashboard.db"


def iter_jq(path: Path, query: str):
    process = subprocess.Popen(
        ["jq", "-c", query, str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert process.stdout is not None

    try:
        for line in process.stdout:
            line = line.strip()
            if line:
                yield json.loads(line)
    finally:
        if process.stdout:
            process.stdout.close()
        stderr = process.stderr.read().strip() if process.stderr else ""
        if process.stderr:
            process.stderr.close()
        code = process.wait()
        if code != 0:
            raise RuntimeError(f"jq falhou em {path}: {stderr}")


def create_schema(conn: sqlite3.Connection):
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=OFF;
        PRAGMA temp_store=MEMORY;
        PRAGMA cache_size=-200000;

        DROP TABLE IF EXISTS simulations;
        DROP TABLE IF EXISTS matches;
        DROP TABLE IF EXISTS classified;
        DROP TABLE IF EXISTS group_rankings;

        CREATE TABLE simulations (
            simulation INTEGER PRIMARY KEY,
            slot_combination INTEGER NOT NULL,
            champion TEXT NOT NULL,
            runner_up TEXT NOT NULL,
            third_place TEXT NOT NULL,
            finalist_a TEXT NOT NULL,
            finalist_b TEXT NOT NULL,
            finalist_a_group TEXT,
            finalist_b_group TEXT,
            final_probability_a REAL,
            final_probability_b REAL,
            third_groups TEXT,
            r32_count INTEGER,
            r16_count INTEGER,
            qf_count INTEGER,
            sf_count INTEGER
        );

        CREATE TABLE matches (
            simulation INTEGER NOT NULL,
            phase TEXT NOT NULL,
            game INTEGER NOT NULL,
            team_a TEXT NOT NULL,
            team_b TEXT NOT NULL,
            team_a_slot TEXT,
            team_b_slot TEXT,
            team_a_group TEXT,
            team_b_group TEXT,
            team_a_position INTEGER,
            team_b_position INTEGER,
            team_a_qualification_type TEXT,
            team_b_qualification_type TEXT,
            probability_a REAL,
            probability_b REAL,
            winner TEXT,
            loser TEXT,
            winner_slot TEXT,
            loser_slot TEXT,
            winner_group TEXT,
            loser_group TEXT,
            winner_position INTEGER,
            loser_position INTEGER,
            winner_qualification_type TEXT,
            loser_qualification_type TEXT,
            PRIMARY KEY (simulation, game)
        );

        CREATE TABLE classified (
            simulation INTEGER NOT NULL,
            team TEXT NOT NULL,
            group_letter TEXT NOT NULL,
            position INTEGER NOT NULL,
            qualification_type TEXT NOT NULL,
            score REAL,
            third_slot TEXT,
            PRIMARY KEY (simulation, team)
        );

        CREATE TABLE group_rankings (
            simulation INTEGER NOT NULL,
            group_letter TEXT NOT NULL,
            group_name TEXT NOT NULL,
            position INTEGER NOT NULL,
            team TEXT NOT NULL,
            score REAL,
            PRIMARY KEY (simulation, group_letter, position)
        );

        CREATE INDEX idx_simulations_champion ON simulations (champion);
        CREATE INDEX idx_simulations_runner_up ON simulations (runner_up);
        CREATE INDEX idx_matches_team_a ON matches (team_a);
        CREATE INDEX idx_matches_team_b ON matches (team_b);
        CREATE INDEX idx_matches_winner ON matches (winner);
        CREATE INDEX idx_matches_phase ON matches (phase);
        CREATE INDEX idx_classified_team ON classified (team);
        CREATE INDEX idx_group_rankings_team ON group_rankings (team);
        """
    )


def build_database():
    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)

    simulation_rows = []
    match_rows = []
    classified_rows = []
    group_rows = []

    with conn:
        for index, simulation in enumerate(iter_jq(BRACKET_PATH, ".[]"), start=1):
            final_match = simulation["rounds"]["FINAL"]

            simulation_rows.append(
                (
                    simulation["simulation"],
                    simulation["slot_combination"],
                    simulation["champion"],
                    simulation["runner_up"],
                    simulation["third_place"],
                    final_match["team_a"],
                    final_match["team_b"],
                    final_match.get("team_a_group"),
                    final_match.get("team_b_group"),
                    final_match["probability_a"],
                    final_match["probability_b"],
                    json.dumps(simulation["third_place_groups"], ensure_ascii=False),
                    len(simulation["rounds"]["R32"]),
                    len(simulation["rounds"]["R16"]),
                    len(simulation["rounds"]["QF"]),
                    len(simulation["rounds"]["SF"]),
                )
            )

            for phase_name, round_data in simulation["rounds"].items():
                matches = round_data if isinstance(round_data, list) else [round_data]
                for match in matches:
                    match_rows.append(
                        (
                            simulation["simulation"],
                            phase_name,
                            match["game"],
                            match["team_a"],
                            match["team_b"],
                            match.get("team_a_slot"),
                            match.get("team_b_slot"),
                            match.get("team_a_group"),
                            match.get("team_b_group"),
                            match.get("team_a_position"),
                            match.get("team_b_position"),
                            match.get("team_a_qualification_type"),
                            match.get("team_b_qualification_type"),
                            match.get("probability_a"),
                            match.get("probability_b"),
                            match.get("winner"),
                            match.get("loser"),
                            match.get("winner_slot"),
                            match.get("loser_slot"),
                            match.get("winner_group"),
                            match.get("loser_group"),
                            match.get("winner_position"),
                            match.get("loser_position"),
                            match.get("winner_qualification_type"),
                            match.get("loser_qualification_type"),
                        )
                    )

            for team in simulation["classified_teams"]:
                classified_rows.append(
                    (
                        simulation["simulation"],
                        team["country"],
                        team["group"],
                        team["position"],
                        team["type"],
                        team.get("score"),
                        team.get("third_slot"),
                    )
                )

            if index % 500 == 0:
                conn.executemany(
                    """
                    INSERT INTO simulations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    simulation_rows,
                )
                conn.executemany(
                    """
                    INSERT INTO matches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    match_rows,
                )
                conn.executemany(
                    """
                    INSERT INTO classified VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    classified_rows,
                )
                simulation_rows.clear()
                match_rows.clear()
                classified_rows.clear()
                print(f"  [{index:,}] simulações do bracket indexadas...")

        if simulation_rows:
            conn.executemany(
                "INSERT INTO simulations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                simulation_rows,
            )
        if match_rows:
            conn.executemany(
                "INSERT INTO matches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                match_rows,
            )
        if classified_rows:
            conn.executemany(
                "INSERT INTO classified VALUES (?, ?, ?, ?, ?, ?, ?)",
                classified_rows,
            )

    print("✅ Bracket indexado no SQLite")

    with conn:
        for index, scenario in enumerate(iter_jq(GROUPS_PATH, ".simulations[]"), start=1):
            simulation = scenario["simulation"]
            for group in scenario["groups"]:
                group_name = group["group"]
                group_letter = group_name.replace("Group ", "").strip()
                for team in group["ranking"]:
                    group_rows.append(
                        (
                            simulation,
                            group_letter,
                            group_name,
                            team["position"],
                            team["country"],
                            team.get("score"),
                        )
                    )

            if index % 1000 == 0:
                conn.executemany(
                    "INSERT INTO group_rankings VALUES (?, ?, ?, ?, ?, ?)",
                    group_rows,
                )
                group_rows.clear()
                print(f"  [{index:,}] simulações de grupos indexadas...")

        if group_rows:
            conn.executemany(
                "INSERT INTO group_rankings VALUES (?, ?, ?, ?, ?, ?)",
                group_rows,
            )

    conn.close()
    print(f"✅ Banco do dashboard salvo em {DB_PATH}")


if __name__ == "__main__":
    build_database()
