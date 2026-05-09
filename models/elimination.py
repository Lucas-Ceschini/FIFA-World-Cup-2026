from imports import *

# =========================================================
# CONFIG
# =========================================================

SEED = 42
np.random.seed(SEED)

N_SIM = 1

# =========================================================
# LOAD DATA
# =========================================================

with open("data/bet365_champions.json", "r") as f:
    market = json.load(f)

with open("data/classified.json", "r") as f:
    classified_data = json.load(f)

with open("data/combinacoes.json", "r") as f:
    third_combos = json.load(f)

if isinstance(third_combos, dict):
    third_combos = third_combos["combinations"]

# =========================================================
# PRIOR
# =========================================================

market_prob = {t["team"]: t["odds_prob"] for t in market["teams"]}

def strength(team):
    return np.log(market_prob.get(team, 1e-6))

# =========================================================
# PHASE DIFFICULTY
# =========================================================

PHASE_DIFF = {
    "R32": 1.0,
    "R16": 1.3,
    "QF": 1.6,
    "SF": 2.4,
    "FINAL": 3.5
}

def phase_adjust(phase):
    return np.log(PHASE_DIFF[phase])

# =========================================================
# MATCH MODEL
# =========================================================

def win_prob(a, b, phase):
    sa = strength(a) + phase_adjust(phase)
    sb = strength(b) + phase_adjust(phase)

    ea = np.exp(sa)
    eb = np.exp(sb)

    pa = ea / (ea + eb)
    pb = 1 - pa

    return pa, pb


def play(a, b, phase):
    pa, pb = win_prob(a, b, phase)
    winner = a if np.random.rand() < pa else b
    return winner, pa, pb

# =========================================================
# SLOT BUILDER
# =========================================================

def build_slots(sim_id):
    classified = classified_data[sim_id]["classified"]

    slots = {}
    team_slots = {}
    for t in classified:
        key = f"{t['position']}{t['group']}"
        slots[key] = t["country"]
        team_slots[t["country"]] = key

    return slots, team_slots

# =========================================================
# THIRD COMBINATION (CORRETO FIFA)
# =========================================================

THIRD_SLOTS = [
    "3rd_ABCDF",   # slot 0 → J74
    "3rd_CDFGH",   # slot 1 → J77
    "3rd_CEFHI",   # slot 2 → J79
    "3rd_EHIJK",   # slot 3 → J80
    "3rd_BEFIJ",   # slot 4 → J81
    "3rd_AEHIJ",   # slot 5 → J82
    "3rd_EFGIJ",   # slot 6 → J85
    "3rd_DEIJL",   # slot 7 → J87
]

R32_TEMPLATE = [
    ("2A", "2B"),           # 73
    ("1E", "3rd_ABCDF"),    # 74
    ("1F", "2C"),           # 75
    ("1C", "2F"),           # 76
    ("1I", "3rd_CDFGH"),    # 77
    ("2E", "2I"),           # 78
    ("1A", "3rd_CEFHI"),    # 79
    ("1L", "3rd_EHIJK"),    # 80
    ("1D", "3rd_BEFIJ"),    # 81
    ("1G", "3rd_AEHIJ"),    # 82
    ("2K", "2L"),           # 83
    ("1H", "2J"),           # 84
    ("1B", "3rd_EFGIJ"),    # 85
    ("1J", "2H"),           # 86
    ("1K", "3rd_DEIJL"),    # 87
    ("2D", "2G"),           # 88
]

def build_third_slots(sim_id, classified):

    thirds = [t for t in classified if t["type"] == "best_third"]
    third_groups = {t["group"] for t in thirds}

    combo = next(
        (c for c in third_combos
         if set(g[1] for g in c["third_placed"]) == third_groups),
        None
    )

    if combo is None:
        raise ValueError(
            f"Combinação de terceiros não encontrada para grupos: {sorted(third_groups)}"
        )

    group_to_country = {t["group"]: t["country"] for t in thirds}
    third_slots = {}

    for i, slot in enumerate(THIRD_SLOTS):
        if i >= len(combo["third_placed"]):
            continue

        group = combo["third_placed"][i][1]
        if group not in group_to_country:
            raise ValueError(
                f"Terceiro colocado esperado de grupo {group} não encontrado nas melhores terceiras"
            )

        third_slots[slot] = group_to_country[group]

    return third_slots, combo["no"]

# =========================================================
# SLOT RESOLVER
# =========================================================

def get_team(slot, slots, third_slots):

    if slot in slots:
        return slots[slot]

    if slot in third_slots:
        return third_slots[slot]

    raise ValueError(f"Slot inválido: {slot}")


# =========================================================
# STORAGE
# =========================================================

scenario_results = []

# =========================================================
# MAIN LOOP
# =========================================================

for sim_id in range(N_SIM):

    used = set()

    classified = classified_data[sim_id]["classified"]

    slots, team_slots = build_slots(sim_id)
    third_slots, combo_no = build_third_slots(sim_id, classified)

    scenario = {
        "simulation": sim_id,
        "slot_combination": combo_no,
        "rounds": {
            "R32": [],
            "R16": [],
            "QF": [],
            "SF": [],
            "THIRD_PLACE": [],
            "FINAL": []
        },
        "champion": None
    }

    # =====================================================
    # R32
    # =====================================================

    r32 = []

    for i, (sa, sb) in enumerate(R32_TEMPLATE):

        a = get_team(sa, slots, third_slots)
        b = get_team(sb, slots, third_slots)

        if a in used or b in used:
            raise ValueError(f"DUPLICAÇÃO R32: {a} vs {b}")

        used.add(a)
        used.add(b)

        w, pa, pb = play(a, b, "R32")

        scenario["rounds"]["R32"].append({
            "game": 73 + i,
            "team_a": a,
            "team_b": b,
            "team_a_slot": team_slots[a],
            "team_b_slot": team_slots[b],
            "probability_a": pa,
            "probability_b": pb,
            "winner": w
        })

        r32.append(w)

    # =====================================================
    # R16
    # =====================================================

    r16 = []

    for i in range(0, 16, 2):

        a, b = r32[i], r32[i + 1]

        w, pa, pb = play(a, b, "R16")

        r16.append(w)

        scenario["rounds"]["R16"].append({
            "game": 89 + i // 2,
            "team_a": a,
            "team_b": b,            
            "team_a_slot": team_slots[a],
            "team_b_slot": team_slots[b],            
            "probability_a": pa,
            "probability_b": pb,
            "winner": w
        })

    # =====================================================
    # QF
    # =====================================================

    qf = []

    for i in range(0, 8, 2):

        a, b = r16[i], r16[i + 1]

        w, pa, pb = play(a, b, "QF")

        qf.append(w)

        scenario["rounds"]["QF"].append({
            "game": 97 + i // 2,
            "team_a": a,
            "team_b": b,            
            "team_a_slot": team_slots[a],
            "team_b_slot": team_slots[b],            
            "probability_a": pa,
            "probability_b": pb,
            "winner": w
        })

    # =====================================================
    # SF
    # =====================================================

    finalists = []
    losers = []

    for i in range(0, 4, 2):

        a, b = qf[i], qf[i + 1]

        w, pa, pb = play(a, b, "SF")

        finalists.append(w)
        losers.append(b if w == a else a)

        scenario["rounds"]["SF"].append({
            "game": 101 + i // 2,
            "team_a": a,
            "team_b": b,            
            "team_a_slot": team_slots[a],
            "team_b_slot": team_slots[b],            
            "probability_a": pa,
            "probability_b": pb,
            "winner": w
        })

    # =====================================================
    # THIRD PLACE
    # =====================================================

    a, b = losers

    w, pa, pb = play(a, b, "SF")

    scenario["rounds"]["THIRD_PLACE"] = {
        "game": 103,
        "team_a": a,
        "team_b": b,
        "team_a_slot": team_slots[a],
        "team_b_slot": team_slots[b],
        "probability_a": pa,
        "probability_b": pb,
        "winner": w
    }

    # =====================================================
    # FINAL
    # =====================================================

    a, b = finalists

    champ, pa, pb = play(a, b, "FINAL")

    scenario["rounds"]["FINAL"] = {
        "game": 104,
        "team_a": a,
        "team_b": b,
        "team_a_slot": team_slots[a],
        "team_b_slot": team_slots[b],
        "probability_a": pa,
        "probability_b": pb,
        "winner": champ
    }

    scenario["champion"] = champ

    scenario_results.append(scenario)

# =========================================================
# SAVE
# =========================================================

with open("data/worldcup_2026_full_bracket.json", "w") as f:
    json.dump(scenario_results, f, indent=2)

print("DONE")