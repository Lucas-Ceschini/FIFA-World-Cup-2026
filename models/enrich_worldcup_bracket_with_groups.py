import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRACKET_PATH = ROOT / "data/worldcup_2026_full_bracket.json"
CLASSIFIED_PATH = ROOT / "data/classified.json"


def iter_json_array(path: Path):
    """Itera um array JSON grande via jq para evitar carregar tudo em memória."""
    process = subprocess.Popen(
        ["jq", "-c", ".[]", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert process.stdout is not None
    fully_consumed = False

    try:
        for line in process.stdout:
            line = line.strip()
            if line:
                yield json.loads(line)
        fully_consumed = True
    finally:
        if process.stdout:
            process.stdout.close()

        stderr = ""
        if process.stderr:
            stderr = process.stderr.read().strip()
            process.stderr.close()

        if not fully_consumed and process.poll() is None:
            process.terminate()

        return_code = process.wait()
        if return_code != 0 and fully_consumed:
            raise RuntimeError(f"jq falhou ao ler {path}: {stderr}")


def build_team_lookup(classified_entry: dict) -> dict:
    lookup = {}

    for team in classified_entry.get("classified", []):
        lookup[team["country"]] = {
            "group": team.get("group"),
            "position": team.get("position"),
            "qualification_type": team.get("type"),
            "third_slot": team.get("third_slot"),
        }

    return lookup


def enrich_match(match: dict, team_lookup: dict) -> dict:
    enriched = dict(match)

    for side in ("a", "b"):
        team_name = match.get(f"team_{side}")
        meta = team_lookup.get(team_name, {})

        enriched[f"team_{side}_group"] = meta.get("group")
        enriched[f"team_{side}_position"] = meta.get("position")
        enriched[f"team_{side}_qualification_type"] = meta.get("qualification_type")

    winner = match.get("winner")
    winner_meta = team_lookup.get(winner, {})
    enriched["winner_group"] = winner_meta.get("group")
    enriched["winner_position"] = winner_meta.get("position")
    enriched["winner_qualification_type"] = winner_meta.get("qualification_type")

    return enriched


def enrich_rounds(rounds: dict, team_lookup: dict) -> dict:
    enriched_rounds = {}

    for round_name, round_data in rounds.items():
        if isinstance(round_data, list):
            enriched_rounds[round_name] = [
                enrich_match(match, team_lookup) for match in round_data
            ]
        elif isinstance(round_data, dict):
            enriched_rounds[round_name] = enrich_match(round_data, team_lookup)
        else:
            enriched_rounds[round_name] = round_data

    return enriched_rounds


def align_classified_entry(classified_iter, simulation_id: int):
    for classified_entry in classified_iter:
        current_sim = classified_entry.get("simulation")
        if current_sim == simulation_id:
            return classified_entry
        if current_sim is not None and current_sim > simulation_id:
            raise ValueError(
                f"classified.json pulou a simulação {simulation_id}; próximo valor foi {current_sim}"
            )

    raise ValueError(f"Simulação {simulation_id} não encontrada em classified.json")


def main():
    bracket_iter = iter_json_array(BRACKET_PATH)
    classified_iter = iter_json_array(CLASSIFIED_PATH)

    total = 0

    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=BRACKET_PATH.parent, suffix=".json"
    ) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write("[\n")

        first_item = True

        for bracket_entry in bracket_iter:
            simulation_id = bracket_entry.get("simulation")
            classified_entry = align_classified_entry(classified_iter, simulation_id)
            team_lookup = build_team_lookup(classified_entry)

            enriched_entry = dict(bracket_entry)
            enriched_entry["rounds"] = enrich_rounds(
                bracket_entry.get("rounds", {}),
                team_lookup,
            )
            enriched_entry["team_lookup"] = team_lookup
            enriched_entry["classified_teams"] = classified_entry.get("classified", [])

            if not first_item:
                tmp.write(",\n")

            json.dump(enriched_entry, tmp, ensure_ascii=False, indent=2)
            first_item = False
            total += 1

            if total % 1000 == 0:
                print(f"  [{total:,}] simulações enriquecidas...")

        tmp.write("\n]\n")

    tmp_path.replace(BRACKET_PATH)
    print(f"✅ Arquivo enriquecido salvo em {BRACKET_PATH}")
    print(f"✅ Total de simulações processadas: {total:,}")


if __name__ == "__main__":
    main()
