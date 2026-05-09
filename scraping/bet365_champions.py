"""
Scraper de odds da Copa do Mundo 2026 — Bet365
Fonte: arquivo bet365_champions.html salvo manualmente (Ctrl+C / Ctrl+V ou Salvar Página)

Uso rápido (padrão — lê bet365_champions.html na mesma pasta):
    python bet365_champions.py

Outros modos:
    python bet365_champions.py --file outro_arquivo.html
    python bet365_champions.py --output odds.json --normalize
    python bet365_champions.py --diag           # inspeciona estrutura do HTML
    python bet365_champions.py --url https://...   # requer Playwright

Com Playwright (para scraping ao vivo):
    pip install playwright && playwright install chromium
"""
from imports import *


# ── Configurações ────────────────────────────────────────────────────────────
DEFAULT_FILE = "scraping/htmls/bet365_champions.html"   # arquivo padrão na mesma pasta do script
DEFAULT_DATA_SAVE = "data/bet365_champions.json"  # arquivo JSON de saída padrão
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
        ("span.gl-ParticipantBorderless_Name",       "Nomes dos participantes"),
        ("span.gl-ParticipantBorderless_Odds",       "Odds dos participantes")
    ]

    all_ok = True
    for selector, descricao in checks:
        elements = soup.select(selector)
        status = "✓" if elements else "✗"
        if not elements:
            all_ok = False
        print(f"  [{status}] {descricao:45s} → {len(elements):3d} elemento(s)", file=sys.stderr)

    # Amostra das odds
    odds_els = soup.select("span.gl-ParticipantBorderless_Odds")
    if odds_els:
        sample = [o.get_text(strip=True) for o in odds_els[:8]]
        print(f"  Primeiras odds: {sample}", file=sys.stderr)
    
    # Amostra dos participantes
    names_els = soup.select("span.gl-ParticipantBorderless_Name")
    if names_els:
        sample = [n.get_text(strip=True) for n in names_els[:8]]
        print(f"  Primeiros nomes: {sample}", file=sys.stderr)

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
    Extrai times e odds de campeões do HTML da Bet365.

    Estrutura DOM esperada:
        .gl-MarketGroupContainer
          ├─ .gl-ParticipantBorderless_Name    ← Nome do time
          ├─ .gl-ParticipantBorderless_Odds    ← Odds do time

    Retorna dict com estrutura:
        {
          "teams": [
            {
              "team": "Team A",
              "odds": 10.50
            }, 
            {
              "team": "Team B",
              "odds": 8.25
            }
          ] 
        }
    """
    soup = BeautifulSoup(html, "html.parser")
    result = []
    seen = set()  # evita duplicatas

    # Localiza o container principal
    containers = soup.select("div.gl-MarketGroupContainer") or [soup]

    for container in containers:
        # Extrai todos os participantes e odds
        names = container.select("span.gl-ParticipantBorderless_Name")
        odds = container.select("span.gl-ParticipantBorderless_Odds")

        # Agrupa nomes e odds em pares
        for i, name_el in enumerate(names):
            team_name = name_el.get_text(strip=True)
            
            if team_name in seen:
                continue

            # Busca a odd correspondente
            odd_value = None
            if i < len(odds):
                try:
                    odd_value = float(odds[i].get_text(strip=True))
                except ValueError:
                    odd_value = None

            result.append({
                "team": team_name,
                "odds": odd_value
            })
            seen.add(team_name)

    return {"teams": result}


# ── Normalização de probabilidades ───────────────────────────────────────────
def normalize_odds(data: dict) -> dict:
    """
    Converte odds decimais em probabilidades normalizadas (overround removido).

        P_raw(i)  = 1 / odd(i)
        P_norm(i) = P_raw(i) / Σ P_raw   → soma = 1.0

    Adiciona campo odds_prob ao lado de cada odd.
    """
    teams = data.get("teams", [])
    odds = [t["odds"] for t in teams if t["odds"] and t["odds"] > 0]
    
    if odds:
        raw = [1 / o for o in odds]
        total = sum(raw)
        j = 0
        for i, team in enumerate(teams):
            if team["odds"] and team["odds"] > 0:
                team["odds_prob"] = round(raw[j] / total, 4)
                j += 1
            else:
                team["odds_prob"] = None
    
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
    n = len(data.get("teams", []))
    if n == 0:
        print(
            "\n[!] Nenhum time extraído. Rode com --diag para investigar:\n"
            f"    python bet365_champions.py --file {args.file} --diag\n",
            file=sys.stderr,
        )
    else:
        print(f"[✓] {n} time(s) extraído(s) com sucesso", file=sys.stderr)

    output_json = json.dumps(data, ensure_ascii=False, indent=2)
    print(output_json)

    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
        print(f"[✓] Salvo em: {args.output}", file=sys.stderr)
    else:
        print(output_json)