import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


def load_json(name):
    path = DATA_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_probability_sums(final_probs, tolerance=1e-3):
    failures = []
    for team, scores in final_probs.items():
        total = 0.0
        for key in ("direct", "best_third", "third_playoff", "eliminated"):
            total += scores.get(key, 0.0)
        if abs(total - 1.0) > tolerance:
            failures.append((team, total))
    return failures


def check_elimination_monotonicity(elimination_probs):
    failures = []
    for team, scores in elimination_probs.items():
        phases = [scores.get(k, 0.0) for k in ("r32", "r16", "qf", "sf", "final", "champion")]
        for earlier, later, name in zip(phases, phases[1:], ("r16", "qf", "sf", "final", "champion")):
            if later > earlier + 1e-9:
                failures.append((team, earlier, later, name))
                break
    return failures


def check_counts_consistency(elimination_probs, n_sim):
    failures = []
    for team, scores in elimination_probs.items():
        for key, count_key in [("r32", "r32_count"), ("r16", "r16_count"), ("qf", "qf_count"), ("sf", "sf_count"), ("final", "final_count"), ("champion", "champion_count")]:
            ratio = scores.get(count_key, 0) / n_sim
            prob = scores.get(key, 0.0)
            if abs(ratio - prob) > 1e-6:
                failures.append((team, key, prob, ratio))
    return failures


def load_market_champion_probabilities():
    path = DATA_DIR / "bet365_champions.json"
    with open(path, "r", encoding="utf-8") as f:
        market = json.load(f)
    return {item["team"]: item["odds_prob"] for item in market.get("teams", [])}


def pearson_corr(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size == 0 or y.size == 0 or x.size != y.size:
        return float("nan")
    xm = x.mean()
    ym = y.mean()
    num = np.sum((x - xm) * (y - ym))
    den = np.sqrt(np.sum((x - xm) ** 2) * np.sum((y - ym) ** 2))
    return float(num / den) if den != 0 else float("nan")


def run_validation(n_sim):
    final_probs = load_json("final_probabilities.json")
    elimination_probs = load_json("elimination_probabilities.json")

    print("Validando consistência dos outputs do modelo...")

    sum_failures = compare_probability_sums(final_probs)
    if sum_failures:
        print(f"✗ {len(sum_failures)} times com soma de probabilidades ≠ 1")
        for team, total in sum_failures[:10]:
            print(f"  - {team}: soma={total:.5f}")
    else:
        print("✓ Todas as somas de probabilidades de classificação estão corretas")

    monotonic_failures = check_elimination_monotonicity(elimination_probs)
    if monotonic_failures:
        print(f"✗ {len(monotonic_failures)} times violam a monotonicidade de fases")
        for team, earlier, later, phase in monotonic_failures[:10]:
            print(f"  - {team}: {phase}={later:.5f} > anterior={earlier:.5f}")
    else:
        print("✓ Probabilidades de eliminação seguem ordem decrescente por fase")

    count_failures = check_counts_consistency(elimination_probs, n_sim)
    if count_failures:
        print(f"✗ {len(count_failures)} inconsistências entre probabilidades e contagens")
        for team, key, prob, ratio in count_failures[:10]:
            print(f"  - {team}: {key}={prob:.6f}, count_ratio={ratio:.6f}")
    else:
        print("✓ Contagens e probabilidades de eliminação estão consistentes")

    if any(v.get("third_playoff", 0) > 0 for v in final_probs.values()):
        print("✓ Há times com probabilidade de avançar via third_playoff")
    else:
        print("⚠️ Nenhum time tem probabilidade de third_playoff — verifique se a lógica foi aplicada")


def run_hypothesis_test(name):
    final_probs = load_json("final_probabilities.json")
    elimination_probs = load_json("elimination_probabilities.json")
    market_probs = load_market_champion_probabilities()

    if name == "market_champion_corr":
        teams = []
        market = []
        champ = []
        for team, data in elimination_probs.items():
            if team in market_probs:
                teams.append(team)
                market.append(market_probs[team])
                champ.append(data.get("champion", 0.0))
        corr = pearson_corr(market, champ)
        print("Hipótese: probabilidade de campeão simulada correlaciona com odds de mercado")
        print(f"  Pearson r = {corr:.4f} para {len(teams)} times")
        top_pairs = sorted(
            ((team, market_probs[team], final_probs[team].get("champion", 0.0)) for team in teams),
            key=lambda x: x[1],
            reverse=True,
        )[:10]
        print("  Exemplo top 10 pelo mercado:")
        for team, m, c in top_pairs:
            print(f"    - {team}: mercado={m:.3f}, sim={c:.3f}")
    elif name == "phase_decay":
        print("Hipótese: as probabilidades decrescem a cada fase do mata-mata")
        ratios = defaultdict(list)
        for team, data in elimination_probs.items():
            for earlier, later, label in [
                ("r32", "r16", "r16/r32"),
                ("r16", "qf", "qf/r16"),
                ("qf", "sf", "sf/qf"),
                ("sf", "final", "final/sf"),
                ("final", "champion", "champion/final"),
            ]:
                denom = data.get(earlier, 0.0)
                ratios[label].append(data.get(later, 0.0) / denom if denom > 0 else 0.0)
        for label, values in ratios.items():
            print(f"  - {label}: média={np.mean(values):.4f}, mediana={np.median(values):.4f}")
    else:
        raise ValueError(f"Hipótese desconhecida: {name}")


def print_summary():
    final_probs = load_json("final_probabilities.json")
    elimination_probs = load_json("elimination_probabilities.json")
    print("Resumo rápido de validação:")
    print(f"  Times em final_probabilities.json: {len(final_probs)}")
    print(f"  Times em elimination_probabilities.json: {len(elimination_probs)}")
    print(f"  Probabilidade média de champion: {np.mean([v.get('champion', 0.0) for v in elimination_probs.values()]):.4f}")
    print(f"  Probabilidade média de direct: {np.mean([v.get('direct', 0.0) for v in final_probs.values()]):.4f}")


def main():
    parser = argparse.ArgumentParser(description="Teste de modelo e validação de hipóteses para a simulação FIFA 2026")
    parser.add_argument("action", choices=["validate", "hypothesis", "summary"], help="Ação a executar")
    parser.add_argument("--hypothesis", choices=["market_champion_corr", "phase_decay"], default="market_champion_corr", help="Hipótese a testar")
    parser.add_argument("--n-sim", type=int, default=10000, help="Número de simulações usado nos contadores (default 10000)")

    args = parser.parse_args()

    if args.action == "validate":
        run_validation(args.n_sim)
    elif args.action == "hypothesis":
        run_hypothesis_test(args.hypothesis)
    elif args.action == "summary":
        print_summary()


if __name__ == "__main__":
    main()
