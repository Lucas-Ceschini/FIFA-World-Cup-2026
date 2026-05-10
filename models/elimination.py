from imports import *


# =========================================================
# CONFIG
# =========================================================

SEED = 42
N_SIM = 100_000

BET365_CHAMPIONS_FILE = Path("data/bet365_champions.json")
CLASSIFIED_FILE = Path("data/classified.json")
COMBINATIONS_FILE = Path("data/combinacoes.json")
OUTPUT_BRACKET_FILE = Path("data/worldcup_2026_full_bracket.json")
OUTPUT_BRACKET_NDJSON_FILE = Path("data/worldcup_2026_full_bracket.ndjson")
OUTPUT_STATS_FILE = Path("data/knockout_tree_statistics.json")
OUTPUT_ELIM_PROBS_FILE = Path("data/elimination_probabilities.json")
OUTPUT_SCENARIOS_FILE = Path("data/knockout_tree_scenarios.json")
OUTPUT_DASHBOARD_INDEX_FILE = Path("data/worldcup_2026_dashboard_index.json")

np.random.seed(SEED)


# =========================================================
# BRACKET STRUCTURE
# =========================================================

THIRD_SLOT_ORDER = [
    "3rd_ABCDF",  # J74
    "3rd_CDFGH",  # J77
    "3rd_CEFHI",  # J79
    "3rd_EHIJK",  # J80
    "3rd_BEFIJ",  # J81
    "3rd_AEHIJ",  # J82
    "3rd_EFGIJ",  # J85
    "3rd_DEIJL",  # J87
]

R32_SLOTS = [
    ("1E", "3rd_ABCDF"),
    ("1F", "2C"),
    ("1C", "2F"),
    ("1I", "3rd_CDFGH"),
    ("2E", "2I"),
    ("1A", "3rd_CEFHI"),
    ("1L", "3rd_EHIJK"),
    ("1D", "3rd_BEFIJ"),
    ("1G", "3rd_AEHIJ"),
    ("2K", "2L"),
    ("1H", "2J"),
    ("1B", "3rd_EFGIJ"),
    ("1J", "2H"),
    ("1K", "3rd_DEIJL"),
    ("2D", "2G"),
    ("2A", "2B"),
]

R16_PAIRS = [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9), (10, 11), (12, 13), (14, 15)]
QF_PAIRS = [(0, 1), (2, 3), (4, 5), (6, 7)]
SF_PAIRS = [(0, 1), (2, 3)]

PHASE_SCALE = {
    "R32": 0.90,
    "R16": 1.00,
    "QF": 1.15,
    "SF": 1.30,
    "THIRD_PLACE": 1.20,
    "FINAL": 1.45,
}

GAME_IDS = {
    "R32": list(range(73, 89)),
    "R16": list(range(89, 97)),
    "QF": list(range(97, 101)),
    "SF": list(range(101, 103)),
    "THIRD_PLACE": 103,
    "FINAL": 104,
}


# =========================================================
# LOAD DATA
# =========================================================

with BET365_CHAMPIONS_FILE.open("r", encoding="utf-8") as f:
    market = json.load(f)

with CLASSIFIED_FILE.open("r", encoding="utf-8") as f:
    classified_scenarios = json.load(f)

with COMBINATIONS_FILE.open("r", encoding="utf-8") as f:
    third_combinations = json.load(f)

if len(classified_scenarios) != N_SIM:
    print(
        f"[!] classified.json possui {len(classified_scenarios):,} simulações; "
        f"o script irá usar esse total em vez de {N_SIM:,}.",
        file=sys.stderr,
    )
    N_SIM = len(classified_scenarios)

print(f"[✓] Cenários classificados carregados: {len(classified_scenarios):,}")
print(f"[✓] Combinações de terceiros carregadas: {len(third_combinations):,}")


# =========================================================
# MARKET STRENGTH
# =========================================================

market_prob = {team["team"]: team["odds_prob"] for team in market["teams"]}
MIN_PROB = min(market_prob.values()) * 0.5


def strength(team_name):
    return np.log(market_prob.get(team_name, MIN_PROB))


def win_prob(team_a, team_b, phase):
    scale = PHASE_SCALE[phase]
    logit = scale * (strength(team_a["name"]) - strength(team_b["name"]))
    return 1.0 / (1.0 + np.exp(-logit))


def play(team_a, team_b, phase):
    return team_a if np.random.rand() < win_prob(team_a, team_b, phase) else team_b


# =========================================================
# COMBINATIONS
# =========================================================

def combination_groups(combo):
    if "groups_advancing" in combo:
        return combo["groups_advancing"]
    return [item[1] for item in combo["third_placed"]]


COMBINATION_BY_GROUP_SET = {
    frozenset(combination_groups(combo)): combo for combo in third_combinations
}


# =========================================================
# CLASSIFIED SCENARIO HELPERS
# =========================================================

def normalize_team_entry(team):
    return {
        "name": team["country"],
        "group": team["group"],
        "position": team["position"],
        "qualification_type": team["type"],
        "score": team.get("score"),
        "third_slot": team.get("third_slot"),
    }


def build_team_maps(classified_entry):
    teams = [normalize_team_entry(team) for team in classified_entry["classified"]]

    firsts = {}
    seconds = {}
    qualified_thirds = []
    all_teams = {}

    for team in teams:
        all_teams[team["name"]] = team
        if team["position"] == 1:
            firsts[team["group"]] = team
        elif team["position"] == 2:
            seconds[team["group"]] = team
        elif team["position"] == 3:
            qualified_thirds.append(team)

    return firsts, seconds, qualified_thirds, all_teams


def resolve_third_slot_map(qualified_thirds):
    third_groups = frozenset(team["group"] for team in qualified_thirds)
    combo = COMBINATION_BY_GROUP_SET.get(third_groups)

    if combo is None:
        raise ValueError(
            "Nenhuma combinação encontrada para os terceiros classificados "
            f"{sorted(third_groups)}"
        )

    slot_map = {}
    for slot_name, token in zip(THIRD_SLOT_ORDER, combo["third_placed"]):
        group_letter = token[1]
        team = next((item for item in qualified_thirds if item["group"] == group_letter), None)
        if team is None:
            raise ValueError(
                f"Combinação {combo['no']} exige grupo {group_letter} em {slot_name}, "
                "mas esse terceiro não está classificado no cenário."
            )
        slot_map[slot_name] = team

    return combo, slot_map


def assign_slots(firsts, seconds, slot_map):
    assignments = {}

    for group, team in firsts.items():
        entry = dict(team)
        entry["slot"] = f"1{group}"
        assignments[entry["slot"]] = entry

    for group, team in seconds.items():
        entry = dict(team)
        entry["slot"] = f"2{group}"
        assignments[entry["slot"]] = entry

    for _, team in slot_map.items():
        entry = dict(team)
        entry["slot"] = f"3{team['group']}"
        entry["third_slot"] = next(slot for slot, mapped in slot_map.items() if mapped["group"] == team["group"])
        assignments[entry["slot"]] = entry

    return assignments


def resolve_slot(slot_token, slot_assignments, third_slot_map):
    if slot_token.startswith("3rd_"):
        team = third_slot_map[slot_token]
        return dict(slot_assignments[f"3{team['group']}"])
    return dict(slot_assignments[slot_token])


def make_match(game, phase, team_a, team_b):
    probability_a = win_prob(team_a, team_b, phase)
    probability_b = 1.0 - probability_a
    winner = play(team_a, team_b, phase)
    loser = team_b if winner["name"] == team_a["name"] else team_a

    return {
        "game": game,
        "phase": phase,
        "team_a": team_a["name"],
        "team_b": team_b["name"],
        "team_a_slot": team_a["slot"],
        "team_b_slot": team_b["slot"],
        "team_a_group": team_a["group"],
        "team_b_group": team_b["group"],
        "team_a_position": team_a["position"],
        "team_b_position": team_b["position"],
        "team_a_qualification_type": team_a["qualification_type"],
        "team_b_qualification_type": team_b["qualification_type"],
        "probability_a": round(probability_a, 6),
        "probability_b": round(probability_b, 6),
        "winner": winner["name"],
        "winner_slot": winner["slot"],
        "winner_group": winner["group"],
        "winner_position": winner["position"],
        "winner_qualification_type": winner["qualification_type"],
        "loser": loser["name"],
        "loser_slot": loser["slot"],
        "loser_group": loser["group"],
        "loser_position": loser["position"],
        "loser_qualification_type": loser["qualification_type"],
    }, dict(winner), dict(loser)


def build_r32_matches(slot_assignments, third_slot_map):
    matches = []
    winners = []

    for index, (slot_a, slot_b) in enumerate(R32_SLOTS):
        team_a = resolve_slot(slot_a, slot_assignments, third_slot_map)
        team_b = resolve_slot(slot_b, slot_assignments, third_slot_map)
        match, winner, _ = make_match(GAME_IDS["R32"][index], "R32", team_a, team_b)
        matches.append(match)
        winners.append(winner)

    return matches, winners


def build_round(previous_winners, pairs, phase, game_ids):
    matches = []
    winners = []
    losers = []

    for index, (left_idx, right_idx) in enumerate(pairs):
        team_a = previous_winners[left_idx]
        team_b = previous_winners[right_idx]
        match, winner, loser = make_match(game_ids[index], phase, team_a, team_b)
        matches.append(match)
        winners.append(winner)
        losers.append(loser)

    return matches, winners, losers


def build_simulation(classified_entry):
    simulation_id = classified_entry["simulation"]
    firsts, seconds, qualified_thirds, all_teams = build_team_maps(classified_entry)

    if len(firsts) != 12 or len(seconds) != 12 or len(qualified_thirds) != 8:
        raise ValueError(
            f"Simulação {simulation_id} inválida: "
            f"{len(firsts)} primeiros, {len(seconds)} segundos, {len(qualified_thirds)} terceiros classificados."
        )

    combo, third_slot_map = resolve_third_slot_map(qualified_thirds)
    slot_assignments = assign_slots(firsts, seconds, third_slot_map)

    r32_matches, r32_winners = build_r32_matches(slot_assignments, third_slot_map)
    r16_matches, r16_winners, _ = build_round(r32_winners, R16_PAIRS, "R16", GAME_IDS["R16"])
    qf_matches, qf_winners, _ = build_round(r16_winners, QF_PAIRS, "QF", GAME_IDS["QF"])
    sf_matches, sf_winners, sf_losers = build_round(qf_winners, SF_PAIRS, "SF", GAME_IDS["SF"])

    third_place_match, third_place_winner, _ = make_match(
        GAME_IDS["THIRD_PLACE"],
        "THIRD_PLACE",
        sf_losers[0],
        sf_losers[1],
    )
    final_match, champion, runner_up = make_match(
        GAME_IDS["FINAL"],
        "FINAL",
        sf_winners[0],
        sf_winners[1],
    )

    return {
        "simulation": simulation_id,
        "slot_combination": combo["no"],
        "third_place_groups": sorted(team["group"] for team in qualified_thirds),
        "third_slot_map": {
            slot: {
                "team": team["name"],
                "group": team["group"],
                "slot": f"3{team['group']}",
            }
            for slot, team in third_slot_map.items()
        },
        "classified_teams": sorted(
            classified_entry["classified"],
            key=lambda team: (team["position"], team["group"], team["country"]),
        ),
        "rounds": {
            "R32": r32_matches,
            "R16": r16_matches,
            "QF": qf_matches,
            "SF": sf_matches,
            "THIRD_PLACE": third_place_match,
            "FINAL": final_match,
        },
        "champion": champion["name"],
        "runner_up": runner_up["name"],
        "third_place": third_place_winner["name"],
        "semifinalists": [match["team_a"] for match in sf_matches] + [sf_matches[-1]["team_b"]],
        "team_lookup": {
            team_name: {
                "group": team["group"],
                "position": team["position"],
                "qualification_type": team["qualification_type"],
                "slot": team.get("slot") or (
                    team.get("third_slot") if team["position"] == 3 else f"{team['position']}{team['group']}"
                ),
                "score": team.get("score"),
            }
            for team_name, team in all_teams.items()
        },
    }


# =========================================================
# AGGREGATE STATS
# =========================================================

team_stats = defaultdict(
    lambda: {
        "championships": 0,
        "finals": 0,
        "third_places": 0,
        "semifinals": 0,
        "quarterfinals": 0,
        "r16_appearances": 0,
        "r32_appearances": 0,
    }
)

slot_combination_counts = Counter()
scenario_snapshots = []
dashboard_index = []


def update_stats(simulation):
    champion = simulation["champion"]
    runner_up = simulation["runner_up"]
    third_place = simulation["third_place"]

    team_stats[champion]["championships"] += 1
    team_stats[champion]["finals"] += 1
    team_stats[runner_up]["finals"] += 1
    team_stats[third_place]["third_places"] += 1

    for match in simulation["rounds"]["SF"]:
        team_stats[match["team_a"]]["semifinals"] += 1
        team_stats[match["team_b"]]["semifinals"] += 1

    for match in simulation["rounds"]["QF"]:
        team_stats[match["team_a"]]["quarterfinals"] += 1
        team_stats[match["team_b"]]["quarterfinals"] += 1

    for match in simulation["rounds"]["R16"]:
        team_stats[match["team_a"]]["r16_appearances"] += 1
        team_stats[match["team_b"]]["r16_appearances"] += 1

    for match in simulation["rounds"]["R32"]:
        team_stats[match["team_a"]]["r32_appearances"] += 1
        team_stats[match["team_b"]]["r32_appearances"] += 1


def build_team_probabilities():
    probabilities = {}

    for team, stats in team_stats.items():
        probabilities[team] = {
            "champion_prob": stats["championships"] / N_SIM,
            "final_prob": stats["finals"] / N_SIM,
            "third_place_prob": stats["third_places"] / N_SIM,
            "semifinal_prob": stats["semifinals"] / N_SIM,
            "quarterfinal_prob": stats["quarterfinals"] / N_SIM,
            "r16_prob": stats["r16_appearances"] / N_SIM,
            "r32_prob": stats["r32_appearances"] / N_SIM,
            "counts": {
                "championships": stats["championships"],
                "finals": stats["finals"],
                "third_places": stats["third_places"],
                "semifinals": stats["semifinals"],
                "quarterfinals": stats["quarterfinals"],
                "r16": stats["r16_appearances"],
                "r32": stats["r32_appearances"],
            },
        }

    return probabilities


# =========================================================
# MAIN SIMULATION LOOP
# =========================================================

print(f"\nIniciando continuação do mata-mata para {N_SIM:,} simulações de grupos...")

with OUTPUT_BRACKET_FILE.open("w", encoding="utf-8") as f:
    with OUTPUT_BRACKET_NDJSON_FILE.open("w", encoding="utf-8") as ndjson_file:
        f.write("[\n")

        for index, classified_entry in enumerate(classified_scenarios):
            simulation = build_simulation(classified_entry)
            slot_combination_counts[simulation["slot_combination"]] += 1
            update_stats(simulation)

            if len(scenario_snapshots) < 500:
                scenario_snapshots.append(
                    {
                        "simulation": simulation["simulation"],
                        "slot_combination": simulation["slot_combination"],
                        "champion": simulation["champion"],
                        "runner_up": simulation["runner_up"],
                        "third_place": simulation["third_place"],
                        "third_place_groups": simulation["third_place_groups"],
                        "semi_a": simulation["rounds"]["SF"][0]["team_a"],
                        "semi_b": simulation["rounds"]["SF"][0]["team_b"],
                        "semi_c": simulation["rounds"]["SF"][1]["team_a"],
                        "semi_d": simulation["rounds"]["SF"][1]["team_b"],
                    }
                )

            dashboard_index.append(
                {
                    "simulation": simulation["simulation"],
                    "slot_combination": simulation["slot_combination"],
                    "champion": simulation["champion"],
                    "runner_up": simulation["runner_up"],
                    "third_place": simulation["third_place"],
                    "third_place_groups": simulation["third_place_groups"],
                    "qualified_teams": [team["country"] for team in simulation["classified_teams"]],
                    "third_teams": [
                        team["country"] for team in simulation["classified_teams"] if team["position"] == 3
                    ],
                    "r16_teams": sorted(
                        {
                            team
                            for match in simulation["rounds"]["R16"]
                            for team in (match["team_a"], match["team_b"])
                        }
                    ),
                    "qf_teams": sorted(
                        {
                            team
                            for match in simulation["rounds"]["QF"]
                            for team in (match["team_a"], match["team_b"])
                        }
                    ),
                    "sf_teams": sorted(
                        {
                            team
                            for match in simulation["rounds"]["SF"]
                            for team in (match["team_a"], match["team_b"])
                        }
                    ),
                    "final_teams": [
                        simulation["rounds"]["FINAL"]["team_a"],
                        simulation["rounds"]["FINAL"]["team_b"],
                    ],
                    "ndjson_line": index + 1,
                }
            )

            if index > 0:
                f.write(",\n")
            json.dump(simulation, f, ensure_ascii=False, indent=2)
            ndjson_file.write(json.dumps(simulation, ensure_ascii=False) + "\n")

            if (index + 1) % 10000 == 0:
                print(
                    f"  [{index + 1:>6,}/{N_SIM:,}] simulações completas | "
                    f"último campeão: {simulation['champion']}"
                )

        f.write("\n]\n")

print("✅ worldcup_2026_full_bracket.json salvo")


# =========================================================
# SAVE AGGREGATES
# =========================================================

team_probabilities = build_team_probabilities()

with OUTPUT_STATS_FILE.open("w", encoding="utf-8") as f:
    json.dump(team_probabilities, f, ensure_ascii=False, indent=2)
print("✅ knockout_tree_statistics.json salvo")

elimination_probs = {}
for team, probabilities in team_probabilities.items():
    elimination_probs[team] = {
        "r32": probabilities["r32_prob"],
        "r16": probabilities["r16_prob"],
        "qf": probabilities["quarterfinal_prob"],
        "sf": probabilities["semifinal_prob"],
        "third_place": probabilities["third_place_prob"],
        "final": probabilities["final_prob"],
        "champion": probabilities["champion_prob"],
        "counts": probabilities["counts"],
    }

with OUTPUT_ELIM_PROBS_FILE.open("w", encoding="utf-8") as f:
    json.dump(elimination_probs, f, ensure_ascii=False, indent=2)
print("✅ elimination_probabilities.json salvo")

with OUTPUT_SCENARIOS_FILE.open("w", encoding="utf-8") as f:
    json.dump(
        {
            "sample_scenarios": scenario_snapshots,
            "slot_combination_distribution": dict(slot_combination_counts.most_common()),
        },
        f,
        ensure_ascii=False,
        indent=2,
    )
print("✅ knockout_tree_scenarios.json salvo")

with OUTPUT_DASHBOARD_INDEX_FILE.open("w", encoding="utf-8") as f:
    json.dump(dashboard_index, f, ensure_ascii=False, indent=2)
print("✅ worldcup_2026_dashboard_index.json salvo")


# =========================================================
# LOG SUMMARY
# =========================================================

ranking = sorted(
    team_probabilities.items(),
    key=lambda item: item[1]["champion_prob"],
    reverse=True,
)

print(f"\n── Top 10 Campeões (de {len(team_probabilities)} times) ──")
for index, (team, probabilities) in enumerate(ranking[:10], start=1):
    print(
        f"  {index:2}. {team:<22} "
        f"🏆 {probabilities['champion_prob']:.1%}  "
        f"Final: {probabilities['final_prob']:.1%}  "
        f"Semi: {probabilities['semifinal_prob']:.1%}  "
        f"QF: {probabilities['quarterfinal_prob']:.1%}"
    )

print("\n── Combinações de terceiros mais frequentes ──")
for combo_no, count in slot_combination_counts.most_common(10):
    print(f"  Combinação {combo_no:>3}: {count:>7,} vezes ({count / N_SIM:.1%})")

print(f"\n✅ SIMULAÇÃO COMPLETA — {N_SIM:,} Copas simuladas com sucesso!")
