"""
Scraper de odds da Copa do Mundo 2026 — Bet365
Fonte: arquivo bet365.html salvo manualmente (Ctrl+C / Ctrl+V ou Salvar Página)

Uso rápido (padrão — lê bet365.html na mesma pasta):
    python bet365_group.py

Outros modos:
    python bet365_group.py --file outro_arquivo.html
    python bet365_group.py --output odds.json --normalize
    python bet365_group.py --diag           # inspeciona estrutura do HTML
    python bet365_group.py --url https://...   # requer Playwright

Dependências mínimas (sem Playwright):
    pip install beautifulsoup4

Com Playwright (para scraping ao vivo):
    pip install playwright && playwright install chromium
"""
from imports import *


# ── Configurações ────────────────────────────────────────────────────────────
DEFAULT_FILE = "scraping/htmls/bet365_group.html"   # arquivo padrão na mesma pasta do script
DEFAULT_DATA_SAVE = "data/bet365_group.json"  # arquivo JSON de saída padrão
BET365_URL   = "https://www.bet365.bet.br/#/AC/B1/C1/D1002/E131901075/G40/K%5E4/"


# ── Leitura robusta do arquivo ───────────────────────────────────────────────
def read_file(filepath: str) -> str:
    """
    Lê o arquivo com detecção automática de encoding.
    Suporta:
      - Ctrl+C / Ctrl+V em editor de texto  → geralmente UTF-8
      - Salvar página Chrome (Ctrl+S)        → UTF-8 com BOM ou latin-1
      - Copiar innerHTML via DevTools        → UTF-8
    """
    path = Path(filepath)

    if not path.exists():
        print(f"\n[✗] Arquivo não encontrado: {filepath}", file=sys.stderr)
        print(
            "    Salve o HTML da Bet365 como 'bet365.html' na mesma pasta do script.\n"
            "    Como salvar:\n"
            "      Opção A) Abra a página no Chrome → Ctrl+U → Ctrl+A → Ctrl+C → cole num .html\n"
            "      Opção B) Chrome → F12 → Console → copie: document.documentElement.outerHTML\n"
            "      Opção C) Chrome → Ctrl+S → 'Página da Web, somente HTML'\n",
            file=sys.stderr,
        )
        sys.exit(1)

    size = path.stat().st_size
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            content = path.read_text(encoding=enc)
            print(f"[✓] {filepath}  ({size:,} bytes, encoding: {enc})", file=sys.stderr)
            return content
        except UnicodeDecodeError:
            continue

    # Último recurso: ignora bytes inválidos
    content = path.read_bytes().decode("utf-8", errors="replace")
    print(f"[!] Encoding desconhecido — alguns caracteres podem estar corrompidos.",
          file=sys.stderr)
    return content


# ── Diagnóstico da estrutura do HTML ────────────────────────────────────────
def diagnostico(html: str):
    """Verifica quais seletores-chave existem no HTML — útil para depuração."""
    soup = BeautifulSoup(html, "html.parser")

    print("\n=== DIAGNÓSTICO DO HTML ===", file=sys.stderr)
    print(f"Tamanho: {len(html):,} caracteres", file=sys.stderr)

    checks = [
        ("div.gl-MarketGroupContainer",              "Container principal"),
        ("div.pml-MarketLeagueStatistics",           "Blocos de grupo (estatísticas)"),
        (".pml-MarketLeagueStatisticsHeader_LabelText", "Labels de grupo (ex: 'Group A')"),
        ("div.pml-ParticipantLeagueStatistics",      "Linhas de times"),
        (".pml-ParticipantLeagueStatistics_Name",    "Nomes dos times"),
        ("div.pml-MarketLeagueOdds",                 "Colunas de odds"),
        ("span.pml-ParticipantLeagueOddsOnly_Odds",  "Valores das odds"),
    ]

    all_ok = True
    for selector, descricao in checks:
        elements = soup.select(selector)
        status = "✓" if elements else "✗"
        if not elements:
            all_ok = False
        print(f"  [{status}] {descricao:45s} → {len(elements):3d} elemento(s)", file=sys.stderr)

    # Mostra grupos encontrados
    groups = soup.select(".pml-MarketLeagueStatisticsHeader_LabelText")
    if groups:
        names = list(dict.fromkeys(g.get_text(strip=True) for g in groups))
        print(f"\n  Grupos encontrados ({len(names)}): {names}", file=sys.stderr)

    # Amostra das odds
    odds_els = soup.select("span.pml-ParticipantLeagueOddsOnly_Odds")
    if odds_els:
        sample = [o.get_text(strip=True) for o in odds_els[:8]]
        print(f"  Primeiras odds: {sample}", file=sys.stderr)

    if not all_ok:
        print(
            "\n  [!] Alguns seletores não foram encontrados.\n"
            "  Possíveis causas:\n"
            "  1. O HTML foi salvo antes da página carregar completamente\n"
            "     → Aguarde os dados aparecerem na tela antes de salvar\n"
            "  2. O Ctrl+C/V capturou apenas texto (sem tags HTML)\n"
            "     → Use F12 > Console > document.documentElement.outerHTML\n"
            "  3. A Bet365 mudou as classes CSS\n"
            "     → Inspecione o elemento no DevTools e atualize os seletores\n",
            file=sys.stderr,
        )
    else:
        print("\n  [✓] Estrutura OK — pronto para parsear.", file=sys.stderr)

    print("===========================\n", file=sys.stderr)


# ── Parser principal ─────────────────────────────────────────────────────────
def parse_html(html: str) -> dict:
    """
    Extrai grupos, países e as três colunas de odds do HTML da Bet365.

    Estrutura DOM esperada:
        .gl-MarketGroupContainer
          ├─ .pml-MarketLeagueStatistics      ← Grupo A (times + posições)
          ├─ .pml-MarketLeagueOdds-col1       ← Win Group
          ├─ .pml-MarketLeagueOdds-col2       ← Group Qual Yes
          ├─ .pml-MarketLeagueOdds-col3       ← Group Qual No
          ├─ .pml-MarketLeagueStatistics      ← Grupo B
          ...

    Retorna dict com estrutura:
        {
          "groups": [
            {
              "group": "Group A",
              "teams": [
                {
                  "position": 1,
                  "country": "Mexico",
                  "odds": {
                    "win_group": 2.00,
                    "group_qual_yes": 1.11,
                    "group_qual_no": 6.50
                  }
                }, ...
              ]
            }, ...
          ]
        }
    """
    soup = BeautifulSoup(html, "html.parser")
    result   = []
    seen     = set()   # evita duplicatas (Bet365 repete blocos para mobile/desktop)

    # Localiza o container principal; usa o documento inteiro como fallback
    containers = soup.select("div.gl-MarketGroupContainer") or [soup]

    for container in containers:
        for stats_block in container.select("div.pml-MarketLeagueStatistics"):

            # ── Nome do grupo ────────────────────────────────────────────────
            lbl = stats_block.select_one(".pml-MarketLeagueStatisticsHeader_LabelText")
            if not lbl:
                continue
            group_name = lbl.get_text(strip=True)   # "Group A", " Group A" etc.
            group_name = group_name.strip()

            if group_name in seen:
                continue

            # ── Times ────────────────────────────────────────────────────────
            teams_raw = []
            for row in stats_block.select("div.pml-ParticipantLeagueStatistics"):
                pos_el  = row.select_one(".pml-ParticipantLeagueStatistics_Number")
                name_el = row.select_one(".pml-ParticipantLeagueStatistics_Name")
                if pos_el and name_el:
                    try:
                        pos = int(pos_el.get_text(strip=True))
                    except ValueError:
                        pos = len(teams_raw) + 1
                    teams_raw.append({"position": pos,
                                      "country":  name_el.get_text(strip=True)})
            if not teams_raw:
                continue

            # ── Colunas de odds (siblings imediatos do stats_block) ───────────
            parent   = stats_block.parent
            children = list(parent.children)
            try:
                idx = children.index(stats_block)
            except ValueError:
                continue

            odds_cols = {}
            i = idx + 1
            while i < len(children):
                sib = children[i]
                if not hasattr(sib, "get"):
                    i += 1; continue

                cls = sib.get("class", [])
                if "pml-MarketLeagueStatistics" in cls:
                    break   # próximo grupo — para

                if "pml-MarketLeagueOdds" in cls:
                    hdr  = sib.select_one(".pml-MarketLeagueOddsHeader")
                    name = hdr.get_text(strip=True) if hdr else "unknown"
                    vals = []
                    for el in sib.select(".pml-ParticipantLeagueOddsOnly_Odds"):
                        try:
                            vals.append(float(el.get_text(strip=True)))
                        except ValueError:
                            vals.append(None)
                    odds_cols[name] = vals
                i += 1

            # ── Monta saída ──────────────────────────────────────────────────
            col_map = {
                "Win Group":      "win_group",
                "Group Qual Yes": "group_qual_yes",
                "Group Qual No":  "group_qual_no",
            }
            teams_out = []
            for j, team in enumerate(teams_raw):
                o = {}
                for display, key in col_map.items():
                    if display in odds_cols and j < len(odds_cols[display]):
                        o[key] = odds_cols[display][j]
                    else:
                        o[key] = None
                teams_out.append({"position": team["position"],
                                  "country":  team["country"],
                                  "odds":     o})

            seen.add(group_name)
            result.append({"group": group_name, "teams": teams_out})

    # Ordena A → L
    result.sort(key=lambda g: g["group"])
    return {"groups": result}


# ── Normalização de probabilidades ───────────────────────────────────────────
def normalize_odds(data: dict) -> dict:
    """
    Converte odds decimais em probabilidades normalizadas (overround removido).

        P_raw(i)  = 1 / odd(i)
        P_norm(i) = P_raw(i) / Σ P_raw   → soma = 1.0

    Adiciona campos *_prob ao lado de cada odd.
    Útil como entrada direta para o modelo Dixon-Coles.
    """
    for group in data.get("groups", []):
        for key in ("win_group", "group_qual_yes", "group_qual_no"):
            odds = [t["odds"].get(key) for t in group["teams"]]
            if all(o and o > 0 for o in odds):
                raw   = [1 / o for o in odds]
                total = sum(raw)
                for i, team in enumerate(group["teams"]):
                    team["odds"][key + "_prob"] = round(raw[i] / total, 4)
    return data


# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Extrai odds de grupos da Copa 2026 do HTML da Bet365",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
exemplos:
  # Lê bet365.html na pasta atual (padrão)
  python bet365_group.py

  # Arquivo com outro nome
  python bet365_group.py --file pagina.html

  # Salva JSON + adiciona probabilidades sem overround
  python bet365_group.py --output odds.json --normalize

  # Inspeciona a estrutura do HTML antes de parsear
  python bet365_group.py --diag

  # Scraping ao vivo (requer Playwright)
  python bet365_group.py --url https://www.bet365.bet.br/#/AC/...
        """,
    )

    src = ap.add_mutually_exclusive_group() # Cria grupo exclusivo para evitar --file + --url juntos
    src.add_argument("--file", default=DEFAULT_FILE,
                     help=f"Arquivo HTML (padrão: {DEFAULT_FILE})")
    src.add_argument("--url",  default=None,
                     help="Scraping ao vivo via Playwright")

    ap.add_argument("--output",    default=DEFAULT_DATA_SAVE, help="Arquivo JSON de saída")
    ap.add_argument("--diag",      action="store_true", help="Diagnóstico da estrutura do HTML")
    ap.add_argument("--debug",     action="store_true", help="(Playwright) salva screenshot+HTML")
    ap.add_argument("--timeout",   type=int, default=30000, help="(Playwright) timeout em ms")

    args = ap.parse_args() # processa argumentos da linha de comando

    # ── Coleta ──────────────────────────────────────────────────────────────
    
    html = read_file(args.file)
    if args.diag:
        diagnostico(html)
    data = parse_html(html)

    # ── Normalização ─────────────────────────────────────────────────────────
    data = normalize_odds(data)
    print("[✓] Probabilidades normalizadas adicionadas", file=sys.stderr)

    # ── Resultado ────────────────────────────────────────────────────────────
    n = len(data.get("groups", []))
    if n == 0:
        print(
            "\n[!] Nenhum grupo extraído. Rode com --diag para investigar:\n"
            f"    python bet365_group.py --file {args.file} --diag\n",
            file=sys.stderr,
        )
    else:
        print(f"[✓] {n} grupo(s) extraído(s) com sucesso", file=sys.stderr)

    output_json = json.dumps(data, ensure_ascii=False, indent=2)
    print(output_json)

    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
        print(f"[✓] Salvo em: {args.output}", file=sys.stderr)
    else:
        print(output_json)