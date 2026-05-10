import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRACKET_PATH = ROOT / "data/worldcup_2026_full_bracket.json"
INDEX_PATH = ROOT / "data/worldcup_2026_dashboard_index.json"

JQ_QUERY = """
[
  .[] | {
    simulation,
    slot_combination,
    champion,
    runner_up,
    third_place,
    third_place_groups,
    qualified_teams: [.classified_teams[].country],
    third_teams: [.classified_teams[] | select(.position == 3) | .country],
    r16_teams: ((.rounds.R16 | map([.team_a, .team_b])) | add | unique),
    qf_teams: ((.rounds.QF | map([.team_a, .team_b])) | add | unique),
    sf_teams: ((.rounds.SF | map([.team_a, .team_b])) | add | unique),
    final_teams: [.rounds.FINAL.team_a, .rounds.FINAL.team_b]
  }
]
"""


def build_index():
    print("Construindo índice resumido do dashboard...")
    result = subprocess.run(
        ["jq", JQ_QUERY, str(BRACKET_PATH)],
        capture_output=True,
        text=True,
        check=True,
    )

    data = json.loads(result.stdout)
    with INDEX_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Índice salvo em {INDEX_PATH}")
    print(f"✅ Simulações indexadas: {len(data):,}")


if __name__ == "__main__":
    build_index()
