from imports import *

# =========================================================
# CONFIG
# =========================================================

INPUT_FILE   = "data/bet365_group.json"
N_SIMULATIONS = 100_000
SEED         = 42

np.random.seed(SEED)

# =========================================================
# LOAD DATA
# =========================================================

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

groups = data["groups"]   # lista de grupos A-L

# =========================================================
# AUX
# =========================================================

def logit(p, eps=1e-9):
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p))

def normalize(x):
    x = np.array(x, dtype=float)
    std = x.std()
    return (x - x.mean()) / (std + 1e-9)

# =========================================================
# 1. ESTIMAR alpha, beta, gamma (REGRESSÃO LINEAR)
#
# Problema original: estimativa de sigma estava errada.
# A calibração buscava minimizar variância do RANKING (inteiro
# 0-3), que converge para o mesmo valor independente do sigma.
# Corrigido: calibra sigma minimizando o erro entre a
# probabilidade de classificação simulada e a do mercado.
# =========================================================

def build_training_matrix():
    X, y = [], []
    for g in groups:
        for team in g["teams"]:
            p_win = team["odds"]["win_group_prob"]
            p_yes = team["odds"]["group_qual_yes_prob"]
            p_no  = team["odds"]["group_qual_no_prob"]
            X.append([p_win, p_yes, p_no])
            y.append(logit(p_win))
    X, y = np.array(X), np.array(y)
    print(f"[✓] Matriz de treinamento: {len(X)} amostras", file=sys.stderr)
    return X, y

X, y = build_training_matrix()

def loss(params):
    alpha, beta, gamma = params
    pred = alpha * X[:, 0] + beta * X[:, 1] - gamma * X[:, 2]
    return np.mean((pred - y) ** 2)

res   = minimize(loss, x0=[0.5, 0.3, 0.2])
alpha, beta, gamma = res.x
print(f"[✓] alpha={alpha:.4f}  beta={beta:.4f}  gamma={gamma:.4f}", file=sys.stderr)

# =========================================================
# 2. FORÇA DOS TIMES
# =========================================================

for g in groups:
    for t in g["teams"]:
        t["strength"] = (
            alpha * t["odds"]["win_group_prob"]
            + beta  * t["odds"]["group_qual_yes_prob"]
            - gamma * t["odds"]["group_qual_no_prob"]
        )

# =========================================================
# 3. CALIBRAR SIGMA
#
# CORREÇÃO: a função anterior minimizava var(rank), que é
# praticamente constante para qualquer sigma positivo.
# Correto: para cada sigma candidato, simula 500 vezes cada
# grupo e compara a probabilidade de classificação simulada
# (pos ≤ 2) com a probabilidade implícita do mercado (p_yes).
# Escolhe o sigma que minimiza essa diferença (RMSE).
# =========================================================

def estimate_sigma(n_calib=500):
    candidates  = np.linspace(0.1, 2.0, 20)
    best_sigma  = 0.5
    best_rmse   = 1e9

    for sigma in candidates:
        errors = []
        for g in groups:
            strengths    = normalize([t["strength"] for t in g["teams"]])
            market_probs = [t["odds"]["group_qual_yes_prob"] for t in g["teams"]]
            classified_counts = np.zeros(len(g["teams"]))

            for _ in range(n_calib):
                perf  = strengths + sigma * np.random.standard_t(df=5, size=len(strengths))
                order = np.argsort(-perf)
                for rank_idx, team_idx in enumerate(order):
                    if rank_idx < 2:
                        classified_counts[team_idx] += 1

            sim_probs = classified_counts / n_calib
            errors.append(np.mean((sim_probs - market_probs) ** 2))

        rmse = np.sqrt(np.mean(errors))
        if rmse < best_rmse:
            best_rmse  = rmse
            best_sigma = sigma

    print(f"[✓] SIGMA={best_sigma:.3f}  (RMSE={best_rmse:.5f})", file=sys.stderr)
    return best_sigma

SIGMA = estimate_sigma()

# =========================================================
# TABELA DE COMBINAÇÕES DE TERCEIROS COLOCADOS
#
# Define, para cada combinação possível de 8 terceiros
# classificados, em qual slot de R32 cada terceiro entra.
# Fonte: regra oficial FIFA 2026 (tabela de combinações).
#
# Estrutura do JSON esperado (third_combinations.json):
# [
#   {
#     "no": 1,
#     "groups_advancing": ["E","F","G","H","I","J","K","L"],
#     "third_placed": ["3E","3J","3I","3F","3H","3G","3L","3K"]
#   }, ...
# ]
#
# Onde "third_placed"[i] é o terceiro que ocupa o slot i:
#   slot 0 → Jogo 74  (3º dos grupos A/B/C/D/F)
#   slot 1 → Jogo 77  (3º dos grupos C/D/F/G/H)
#   slot 2 → Jogo 79  (3º dos grupos C/E/F/H/I)
#   slot 3 → Jogo 80  (3º dos grupos E/H/I/J/K)
#   slot 4 → Jogo 81  (3º dos grupos B/E/F/I/J)
#   slot 5 → Jogo 82  (3º dos grupos A/E/H/I/J)
#   slot 6 → Jogo 85  (3º dos grupos E/F/G/I/J)
#   slot 7 → Jogo 87  (3º dos grupos D/E/I/J/L)
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

try:
    with open("data/third_combinations.json", "r") as f:
        THIRD_COMBINATIONS = json.load(f)
    print(f"[✓] {len(THIRD_COMBINATIONS)} combinações de terceiros carregadas", file=sys.stderr)
except FileNotFoundError:
    THIRD_COMBINATIONS = []
    print("[!] third_combinations.json não encontrado — slots de terceiros serão nulos", file=sys.stderr)

def get_third_slot_map(advancing_groups):
    """
    Dado o conjunto de grupos cujos terceiros avançaram (ex: {"E","F","G","H","I","J","K","L"}),
    retorna um dict { slot_key: grupo_de_origem } consultando a tabela de combinações.

    Se não encontrar a combinação exata, retorna mapeamento vazio.
    """
    key = frozenset(advancing_groups)
    for combo in THIRD_COMBINATIONS:
        if frozenset(combo["groups_advancing"]) == key:
            # third_placed[i] = "3X" onde X é a letra do grupo
            return {
                THIRD_SLOTS[i]: combo["third_placed"][i][1]   # extrai a letra do grupo: "3E" → "E"
                for i in range(min(8, len(combo["third_placed"])))
            }
    return {}

# =========================================================
# MONTE CARLO — FASE DE GRUPOS
# =========================================================

group_scenarios = []
best_thirds_all = []
eliminated_all  = []
classified_all  = []

stats = defaultdict(lambda: defaultdict(int))

for sim in range(N_SIMULATIONS):

    sim_groups = []
    all_thirds = []   # [{country, group, score}, ...]
    all_elim   = []
    classified = []   # [{country, group, position, type, score}, ...]

    for g in groups:

        # Extrai a letra do grupo: "Group A" → "A"
        group_letter = g["group"].replace("Group ", "").strip()

        strengths        = [t["strength"] for t in g["teams"]]
        normed_strengths = normalize(strengths)

        names, perf = [], []
        for t, s in zip(g["teams"], normed_strengths):
            p = float(s + SIGMA * np.random.standard_t(df=5))
            names.append(t["country"])
            perf.append(p)

        order  = np.argsort(-np.array(perf))
        ranked = [
            {
                "position": i + 1,
                "country":  names[idx],
                "score":    float(perf[idx]),
                "group":    group_letter,
            }
            for i, idx in enumerate(order)
        ]

        sim_groups.append({"group": g["group"], "ranking": ranked})

        for r in ranked:
            if r["position"] in (1, 2):
                classified.append({
                    "country":  r["country"],
                    "group":    group_letter,
                    "position": r["position"],
                    "type":     "direct",
                    "score":    r["score"],
                })
            elif r["position"] == 3:
                all_thirds.append({
                    "country": r["country"],
                    "group":   group_letter,
                    "score":   r["score"],
                })
            else:
                all_elim.append({
                    "country":  r["country"],
                    "group":    group_letter,
                    "position": r["position"],
                    "score":    r["score"],
                })

    # ── Best 8 thirds ────────────────────────────────────────
    all_thirds.sort(key=lambda x: x["score"], reverse=True)
    best8 = all_thirds[:8]
    worst = all_thirds[8:]

    advancing_groups = {t["group"] for t in best8}
    slot_map = get_third_slot_map(advancing_groups)   # slot → letra do grupo

    for t in best8:
        # Descobre em qual slot de terceiro este time entra
        # (qual THIRD_SLOTS aponta para o grupo deste terceiro)
        slot_key = next(
            (k for k, grp in slot_map.items() if grp == t["group"]),
            None
        )
        classified.append({
            "country":  t["country"],
            "group":    t["group"],
            "position": 3,
            "type":     "best_third",
            "score":    t["score"],
            "third_slot": slot_key,   # ex: "3rd_ABCDF" → informa ao elimination.py onde encaixar
        })

    for t in worst:
        all_elim.append({
            "country":  t["country"],
            "group":    t["group"],
            "position": 3,
            "score":    t["score"],
        })

    # ── Stats ────────────────────────────────────────────────
    for c in classified:
        stats[c["country"]][c["type"]] += 1
    for e in all_elim:
        stats[e["country"]]["eliminated"] += 1

    # ── Armazena ─────────────────────────────────────────────
    group_scenarios.append({
        "simulation":  sim,
        "probability": 1 / N_SIMULATIONS,
        "groups":      sim_groups,
    })
    best_thirds_all.append({"simulation": sim, "best_thirds": best8})
    eliminated_all.append({"simulation":  sim, "eliminated":  all_elim})
    classified_all.append({"simulation":  sim, "classified":  classified})

    if (sim + 1) % 10_000 == 0:
        print(f"  [{sim+1:>7,}/{N_SIMULATIONS:,}] simulações de grupo completas...", file=sys.stderr)

# =========================================================
# PROBABILIDADES FINAIS
# =========================================================

final = {}
for country, v in stats.items():
    final[country] = {
        "direct":             v.get("direct",     0) / N_SIMULATIONS,
        "best_third":         v.get("best_third", 0) / N_SIMULATIONS,
        "eliminated":         v.get("eliminated", 0) / N_SIMULATIONS,
        "direct_count":       v.get("direct",     0),
        "best_third_count":   v.get("best_third", 0),
        "eliminated_count":   v.get("eliminated", 0),
    }

# =========================================================
# SAVE
# =========================================================

json.dump({"simulations": group_scenarios}, open("data/group_scenarios.json",   "w"), indent=2)
json.dump(best_thirds_all,                  open("data/best_thirds.json",        "w"), indent=2)
json.dump(eliminated_all,                   open("data/eliminated.json",         "w"), indent=2)
json.dump(classified_all,                   open("data/classified.json",         "w"), indent=2)
json.dump(final,                            open("data/final_probabilities.json","w"), indent=2)

print("\nDONE")
print(f"alpha={alpha:.4f}  beta={beta:.4f}  gamma={gamma:.4f}")
print(f"sigma={SIGMA:.3f}")

# ── Ranking rápido de classificação ───────────────────────
ranking = sorted(final.items(), key=lambda x: x[1]["direct"] + x[1]["best_third"], reverse=True)
print("\n── Top 16 por prob. de classificação ──────────────────")
for country, v in ranking[:16]:
    print(f"  {country:<22}  direto={v['direct']:.1%}  3º={v['best_third']:.1%}  elim={v['eliminated']:.1%}")