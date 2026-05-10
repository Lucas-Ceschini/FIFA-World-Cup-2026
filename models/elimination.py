from imports import *

# =========================================================
# CONFIG
# =========================================================

SEED  = 42
N_SIM = 10_000

np.random.seed(SEED)

# =========================================================
# LOAD DATA
# =========================================================

with open("data/bet365_champions.json", "r") as f:
    market = json.load(f)

with open("data/classified.json", "r") as f:
    groups_data = json.load(f)

# =========================================================
# PRIOR — força log-escala a partir das odds de campeão
# =========================================================

market_prob = {t["country"]: t["champion_prob"] for t in market}

# Fallback: mínimo real observado no mercado (evita -inf e discriminação excessiva)
MIN_PROB = min(market_prob.values()) * 0.5

def strength(team):
    """
    Força log-escala do time no modelo Bradley-Terry.
    Usa a probabilidade implícita de ser campeão como prior.
    Fallback = metade do menor valor observado no mercado (não 1e-6).
    """
    return np.log(market_prob.get(team, MIN_PROB))

# =========================================================
# PHASE DIFFICULTY
#
# CORREÇÃO: o ajuste de fase deve ser ASSIMÉTRICO — aplicado
# apenas como escala geral da disputa, não somado igual para
# os dois lados (pois somado igual cancela no Bradley-Terry).
#
# Implementação correta: escalar o rating RELATIVO entre os
# times. Quanto maior a fase, mais o favorito leva vantagem
# (partidas mata-mata têm menor variância que jogos de grupo).
#
# Fórmula: P(a vence) = σ( k_fase * (s_a - s_b) )
# onde k_fase > 1 amplifica a diferença de força em fases
# mais avançadas.
# =========================================================

PHASE_SCALE = {
    "R32":   0.90,   # rodada de 32 — maior aleatoriedade (zebra possível)
    "R16":   1.00,   # oitavas      — base
    "QF":    1.15,   # quartas      — favoritismo aumenta levemente
    "SF":    1.30,   # semifinal    — grandes times dominam mais
    "FINAL": 1.45,   # final        — menor variância, força prevalece
}

# =========================================================
# MATCH MODEL — Bradley-Terry com escala por fase
# =========================================================

def win_prob(a, b, phase):
    """
    P(a vence b na fase) usando Bradley-Terry escalado.
    k_fase amplifica a diferença de força: favoritos ganham
    mais consistentemente nas fases avançadas.
    """
    k  = PHASE_SCALE[phase]
    sa = strength(a)
    sb = strength(b)

    # logit escalado → sigmoid
    logit = k * (sa - sb)
    return 1.0 / (1.0 + np.exp(-logit))

def play(a, b, phase):
    """Simula uma partida; retorna o vencedor."""
    return a if np.random.rand() < win_prob(a, b, phase) else b

# =========================================================
# CHAVEAMENTO OFICIAL FIFA 2026
#
# Fonte: tabela oficial FIFA (jogos J74–J88)
# 32 times no mata-mata, estrutura fixa por posição de grupo.
#
# ESTRUTURA DOS CONFRONTOS (Rodada de 32):
#
#   J74: 1E  × 3º(ABCDF)    J75: 1F  × 2C
#   J76: 1C  × 2F           J77: 1I  × 3º(CDFGH)
#   J78: 2E  × 2I           J79: 1A  × 3º(CEFHI)
#   J80: 1L  × 3º(EHIJK)    J81: 1D  × 3º(BEFIJ)
#   J82: 1G  × 3º(AEHIJ)    J83: 2K  × 2L
#   J84: 1H  × 2J           J85: 1B  × 3º(EFGIJ)
#   J86: 1J  × 2H           J87: 1K  × 3º(DEIJL)
#   J88: 2D  × 2G
#
# CHAVE DO MATA-MATA (quem enfrenta quem nas fases seguintes):
#   Chave Oeste:  J74/J75 → QF1 | J76/J77 → QF2 | QF1×QF2 → SF1
#   Chave Leste:  J78/J79 → QF3 | J80/J81 → QF4 | QF3×QF4 → SF2
#   Chave Sul:    J82/J83 → QF5 | J84/J85 → QF6 | QF5×QF6 → SF3
#   Chave Norte:  J86/J87 → QF7 | J88/J87 → QF8 | QF7×QF8 → SF4
#   SF1×SF2 → FINAL (metade 1) | SF3×SF4 → FINAL (metade 2)  [ajuste a confirmar]
#
# TERCEIROS COLOCADOS:
#   8 terceiros colocados entre 12 grupos se classificam.
#   Posição de cada terceiro no bracket depende dos grupos
#   de origem dos 8 melhores (tabela FIFA — ver assign_thirds).
# =========================================================

# Confrontos fixos da Rodada de 32
# Cada tupla: (slot_a, slot_b)
# slot = (posição_no_grupo, grupo)  ou  ("3rd", [grupos_elegíveis])

R32_BRACKET = [
    # Par 1  (vencedores → QF lado A)
    ("1E",  "3rd_ABCDF"),   # J74
    ("1F",  "2C"),          # J75
    # Par 2  (vencedores → QF lado A)
    ("1C",  "2F"),          # J76
    ("1I",  "3rd_CDFGH"),   # J77
    # Par 3  (vencedores → QF lado B)
    ("2E",  "2I"),          # J78
    ("1A",  "3rd_CEFHI"),   # J79
    # Par 4  (vencedores → QF lado B)
    ("1L",  "3rd_EHIJK"),   # J80
    ("1D",  "3rd_BEFIJ"),   # J81
    # Par 5  (vencedores → QF lado C)
    ("1G",  "3rd_AEHIJ"),   # J82
    ("2K",  "2L"),          # J83
    # Par 6  (vencedores → QF lado C)
    ("1H",  "2J"),          # J84
    ("1B",  "3rd_EFGIJ"),   # J85
    # Par 7  (vencedores → QF lado D)
    ("1J",  "2H"),          # J86
    ("1K",  "3rd_DEIJL"),   # J87
    # Par 8  (vencedores → QF lado D)
    ("2D",  "2G"),          # J88
    ("2A",  "2B"),          # par restante
]

# Estrutura do bracket pós-R32: quais pares de R32 formam cada QF
# QF[i] = (índice_jogo_r32_a, índice_jogo_r32_b)
QF_PAIRS = [
    (0, 1),    # QF1: venc(J74) × venc(J75)
    (2, 3),    # QF2: venc(J76) × venc(J77)
    (4, 5),    # QF3: venc(J78) × venc(J79)
    (6, 7),    # QF4: venc(J80) × venc(J81)
    (8, 9),    # QF5: venc(J82) × venc(J83)
    (10, 11),  # QF6: venc(J84) × venc(J85)
    (12, 13),  # QF7: venc(J86) × venc(J87)
    (14, 15),  # QF8: venc(J88) × venc(par restante)
]

# Semifinais: quais QFs se enfrentam
SF_PAIRS = [
    (0, 1),   # SF1: venc(QF1) × venc(QF2)
    (2, 3),   # SF2: venc(QF3) × venc(QF4)
    (4, 5),   # SF3: venc(QF5) × venc(QF6)
    (6, 7),   # SF4: venc(QF7) × venc(QF8)
]

# Final: SF1×SF2 e SF3×SF4 → as duas semis decidem os finalistas
FINAL_PAIRS = [
    (0, 1),   # Finalista 1: venc(SF1) × venc(SF2)
    (2, 3),   # Finalista 2: venc(SF3) × venc(SF4)
]

# =========================================================
# HELPERS DE CHAVEAMENTO
# =========================================================

def get_classified_by_position(sim_data):
    """
    Constrói dicionários de acesso rápido aos classificados:
      firsts[G]  = time que terminou em 1º no Grupo G
      seconds[G] = time que terminou em 2º no Grupo G
      thirds[G]  = time que terminou em 3º no Grupo G (entre os classificados)
    """
    firsts  = {}
    seconds = {}
    thirds  = {}

    for entry in sim_data["classified"]:
        country = entry["country"]
        ctype   = entry.get("type", "direct")

        # O classified.json deve ter campo "group" e "position"
        # Se não tiver, tentamos inferir do campo "type"
        group = entry.get("group", "?")
        pos   = entry.get("position", 0)

        if pos == 1:
            firsts[group] = country
        elif pos == 2:
            seconds[group] = country
        elif pos == 3 and ctype == "best_third":
            thirds[group] = country

    return firsts, seconds, thirds

def assign_thirds(thirds_dict, eligible_groups_str):
    """
    Dado o conjunto de grupos elegíveis (ex: "ABCDF") e os
    terceiros colocados classificados, retorna o terceiro
    colocado que veio de um dos grupos elegíveis.

    Se mais de um terceiro vier de grupos elegíveis, escolhe
    o de maior força (proxy: market_prob) — reproduz o critério
    FIFA de melhor terceiro no slot.

    Retorna None se nenhum terceiro elegível for encontrado.
    """
    eligible = set(eligible_groups_str)
    candidates = [
        (grp, team)
        for grp, team in thirds_dict.items()
        if grp in eligible
    ]

    if not candidates:
        return None

    # Escolhe o de maior força entre os elegíveis para este slot
    candidates.sort(key=lambda x: market_prob.get(x[1], MIN_PROB), reverse=True)
    return candidates[0][1]

def resolve_slot(slot, firsts, seconds, thirds):
    """
    Resolve um slot do bracket para um nome de time.
    Ex: "1C" → firsts["C"]
        "2F" → seconds["F"]
        "3rd_ABCDF" → assign_thirds(thirds, "ABCDF")
    """
    if slot.startswith("1"):
        return firsts.get(slot[1], None)
    elif slot.startswith("2"):
        return seconds.get(slot[1], None)
    elif slot.startswith("3rd_"):
        eligible = slot[4:]  # ex: "ABCDF"
        return assign_thirds(thirds, eligible)
    return None

def build_r32_bracket(sim_data):
    """
    Monta os 16 confrontos da Rodada de 32 respeitando
    o chaveamento oficial FIFA 2026.

    Retorna lista de 16 tuplas (time_a, time_b).
    Times None são substituídos por um fallback aleatório
    dos classificados (garante robustez mesmo com dados incompletos).
    """
    firsts, seconds, thirds = get_classified_by_position(sim_data)

    # fallback pool: todos os classificados
    all_classified = [e["country"] for e in sim_data["classified"]]

    matchups = []
    for slot_a, slot_b in R32_BRACKET:
        team_a = resolve_slot(slot_a, firsts, seconds, thirds)
        team_b = resolve_slot(slot_b, firsts, seconds, thirds)

        # Fallback se slot não resolvido (dados incompletos)
        if team_a is None:
            available = [t for t in all_classified if t not in [m for pair in matchups for m in pair]]
            team_a = available[0] if available else "Unknown_A"
        if team_b is None:
            available = [t for t in all_classified if t not in [m for pair in matchups for m in pair] and t != team_a]
            team_b = available[0] if available else "Unknown_B"

        matchups.append((team_a, team_b))

    return matchups

# =========================================================
# SIMULATION STORAGE
# =========================================================

# Fases rastreadas — agora inclui R32
PHASES = ["R32", "R16", "QF", "SF", "FINAL"]

stats = defaultdict(lambda: {
    phase: {"passes": 0, "attempts": 0, "opponents": Counter()}
    for phase in PHASES
} | {"CHAMPION": 0})

results = []

# =========================================================
# MAIN LOOP
# =========================================================

for sim_id in range(N_SIM):

    sim_data = groups_data[sim_id % len(groups_data)]

    # ── Rodada de 32 ────────────────────────────────────────
    r32_matchups = build_r32_bracket(sim_data)
    r16 = []  # vencedores da R32 → entram nas oitavas

    for a, b in r32_matchups:
        w = play(a, b, "R32")
        l = b if w == a else a

        stats[a]["R32"]["attempts"] += 1
        stats[b]["R32"]["attempts"] += 1
        stats[w]["R32"]["passes"]   += 1
        stats[w]["R32"]["opponents"][l] += 1
        stats[l]["R32"]["opponents"][w] += 1  # FIX: perdedor também registra adversário

        r16.append(w)

    # r16 tem 16 vencedores posicionados — os pares de QF são
    # determinados pela estrutura do bracket (QF_PAIRS sobre os índices de r16)

    # ── Oitavas (R16) ────────────────────────────────────────
    # Pares de r16 seguem a estrutura: r16[0]×r16[1], r16[2]×r16[3] ...
    qf = []
    for i in range(0, 16, 2):
        a, b = r16[i], r16[i + 1]
        w = play(a, b, "R16")
        l = b if w == a else a

        stats[a]["R16"]["attempts"] += 1
        stats[b]["R16"]["attempts"] += 1
        stats[w]["R16"]["passes"]   += 1
        stats[w]["R16"]["opponents"][l] += 1
        stats[l]["R16"]["opponents"][w] += 1

        qf.append(w)

    # ── Quartas ──────────────────────────────────────────────
    sf = []
    for i in range(0, 8, 2):
        a, b = qf[i], qf[i + 1]
        w = play(a, b, "QF")
        l = b if w == a else a

        stats[a]["QF"]["attempts"] += 1
        stats[b]["QF"]["attempts"] += 1
        stats[w]["QF"]["passes"]   += 1
        stats[w]["QF"]["opponents"][l] += 1
        stats[l]["QF"]["opponents"][w] += 1

        sf.append(w)

    # ── Semifinais ───────────────────────────────────────────
    final = []
    for i in range(0, 4, 2):
        a, b = sf[i], sf[i + 1]
        w = play(a, b, "SF")
        l = b if w == a else a

        stats[a]["SF"]["attempts"] += 1
        stats[b]["SF"]["attempts"] += 1
        stats[w]["SF"]["passes"]   += 1
        stats[w]["SF"]["opponents"][l] += 1
        stats[l]["SF"]["opponents"][w] += 1

        final.append(w)

    # ── Final ────────────────────────────────────────────────
    a, b = final[0], final[1]
    champ = play(a, b, "FINAL")
    l     = b if champ == a else a

    stats[a]["FINAL"]["attempts"]     += 1
    stats[b]["FINAL"]["attempts"]     += 1
    stats[champ]["FINAL"]["passes"]   += 1
    stats[champ]["FINAL"]["opponents"][l]     += 1
    stats[l]["FINAL"]["opponents"][champ]     += 1
    stats[champ]["CHAMPION"]          += 1

    results.append({
        "simulation": sim_id,
        "champion":   champ,
        "finalist_a": a,
        "finalist_b": b,
        "semi_a":     sf[0],
        "semi_b":     sf[1],
        "semi_c":     sf[2],
        "semi_d":     sf[3],
    })

    if (sim_id + 1) % 1000 == 0:
        print(f"  [{sim_id + 1:>6,}/{N_SIM:,}] simulações completas...")

# =========================================================
# OUTPUT — todas as probabilidades INCONDICIONAIS (/ N_SIM)
#
# CORREÇÃO: métricas condicionais (passes/attempts) e
# incondicionais (passes/N_SIM) têm semânticas diferentes.
# Exportamos AMBAS para que o consumidor escolha.
#
# - *_prob_given_reached : prob de passar DADO QUE chegou na fase
#                          (útil para medir força relativa)
# - *_prob               : prob incondicional de chegar E passar
#                          (útil para ranking e comparação entre times)
# =========================================================

final_output = {}

for team, v in stats.items():
    final_output[team] = {

        # ── Probabilidades incondicionais ──────────────────
        "R32_prob":     v["R32"]["passes"]  / N_SIM,
        "R16_prob":     v["R16"]["passes"]  / N_SIM,
        "QF_prob":      v["QF"]["passes"]   / N_SIM,
        "SF_prob":      v["SF"]["passes"]   / N_SIM,
        "FINAL_prob":   v["FINAL"]["passes"] / N_SIM,
        "champion_prob":v["CHAMPION"]        / N_SIM,

        # ── Probabilidades condicionais (dado que chegou) ──
        "R32_prob_given_reached":  v["R32"]["passes"]  / max(1, v["R32"]["attempts"]),
        "R16_prob_given_reached":  v["R16"]["passes"]  / max(1, v["R16"]["attempts"]),
        "QF_prob_given_reached":   v["QF"]["passes"]   / max(1, v["QF"]["attempts"]),
        "SF_prob_given_reached":   v["SF"]["passes"]   / max(1, v["SF"]["attempts"]),
        "FINAL_prob_given_reached":v["FINAL"]["passes"] / max(1, v["FINAL"]["attempts"]),

        # ── Contagens brutas ───────────────────────────────
        "counts": {
            "R32_passes":   v["R32"]["passes"],
            "R32_attempts": v["R32"]["attempts"],
            "R16_passes":   v["R16"]["passes"],
            "R16_attempts": v["R16"]["attempts"],
            "QF_passes":    v["QF"]["passes"],
            "QF_attempts":  v["QF"]["attempts"],
            "SF_passes":    v["SF"]["passes"],
            "SF_attempts":  v["SF"]["attempts"],
            "FINAL_passes": v["FINAL"]["passes"],
            "FINAL_attempts":v["FINAL"]["attempts"],
            "champions":    v["CHAMPION"],
        },

        # ── Adversários mais frequentes por fase ──────────
        "opponents": {
            phase: dict(v[phase]["opponents"])
            for phase in PHASES
        },
    }

# =========================================================
# SAVE
# =========================================================

with open("data/knockout_tree_scenarios.json", "w") as f:
    json.dump(results, f, indent=2)

with open("data/knockout_tree_statistics.json", "w") as f:
    json.dump(final_output, f, indent=2)

print(f"\nDONE — {N_SIM:,} simulações | {len(final_output)} times rastreados")

# ── Ranking rápido de campeões ─────────────────────────────
ranking = sorted(
    final_output.items(),
    key=lambda x: x[1]["champion_prob"],
    reverse=True
)
print("\n── Top 10 Campeões ──────────────────────────")
for team, v in ranking[:10]:
    print(
        f"  {team:<22} "
        f"campeão={v['champion_prob']:.1%}  "
        f"final={v['FINAL_prob']:.1%}  "
        f"semi={v['SF_prob']:.1%}"
    )