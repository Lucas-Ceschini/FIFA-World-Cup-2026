import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GROUPS_PATH = ROOT / "data/group_scenarios.json"
OUTPUT_PATH = ROOT / "data/group_scenarios.ndjson"


def build_ndjson():
    with OUTPUT_PATH.open("w", encoding="utf-8") as out:
        process = subprocess.run(
            ["jq", "-c", ".simulations[]", str(GROUPS_PATH)],
            stdout=out,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )

    print(f"✅ NDJSON de grupos salvo em {OUTPUT_PATH}")


if __name__ == "__main__":
    build_ndjson()
