# FIFA World Cup 2026 Simulation Engine

Este projeto simula a Copa do Mundo FIFA 2026 em duas etapas conectadas:

1. fase de grupos via Monte Carlo
2. mata-mata como continuação direta de cada cenário de grupos

O resultado final são 100.000 Copas completas, com grupos, classificados, combinação dos terceiros colocados, chaveamento, probabilidades de confronto e campeão.

## Visão Geral

O pipeline atual funciona assim:

1. `models/groups.py`
   Gera 100.000 simulações da fase de grupos.
   Também determina os 24 classificados diretos e os 8 terceiros que avançam.

2. `models/elimination.py`
   Lê `classified.json` e continua cada uma das 100.000 simulações no mata-mata.
   O encaixe dos terceiros é feito com base em `data/combinacoes.json`.

3. `models/build_group_scenarios_ndjson.py`
   Converte os grupos para `ndjson`, para o dashboard carregar uma simulação específica com mais eficiência.

4. `dash/worldcup_dashboard.py`
   Dashboard em Streamlit para explorar os cenários completos.

## Estrutura Principal

### Scripts

- [models/groups.py](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/models/groups.py)
- [models/elimination.py](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/models/elimination.py)
- [models/build_group_scenarios_ndjson.py](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/models/build_group_scenarios_ndjson.py)
- [dash/worldcup_dashboard.py](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/dash/worldcup_dashboard.py)

### Dados de Entrada

- [data/bet365_group.json](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/data/bet365_group.json)
  Odds e probabilidades implícitas para a fase de grupos.

- [data/bet365_champions.json](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/data/bet365_champions.json)
  Odds e probabilidades implícitas de título.

- [data/combinacoes.json](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/data/combinacoes.json)
  Tabela de combinações oficiais dos terceiros colocados para os slots do bracket.

## Pré-Requisitos

Recomendado usar `python3.11+`.

Instale as dependências:

```bash
pip install -r requirements.txt
pip install streamlit plotly scipy numpy
```

O projeto também usa `jq` em alguns scripts auxiliares. No macOS:

```bash
brew install jq
```

## Ordem de Execução

Se você quiser regenerar tudo do zero, a ordem correta é esta:

### 1. Simular a fase de grupos

```bash
python3 models/groups.py
```

Esse script gera:

- `data/group_scenarios.json`
- `data/classified.json`
- `data/best_thirds.json`
- `data/eliminated.json`
- `data/final_probabilities.json`

### 2. Simular o mata-mata como continuação dos grupos

```bash
python3 models/elimination.py
```

Esse script:

- lê `data/classified.json`
- identifica os 8 terceiros classificados daquele cenário
- encontra a combinação correta em `data/combinacoes.json`
- monta o bracket oficial da FIFA 2026
- simula R32, R16, quartas, semi, 3º lugar e final

Esse script gera:

- `data/worldcup_2026_full_bracket.json`
- `data/worldcup_2026_full_bracket.ndjson`
- `data/worldcup_2026_dashboard_index.json`
- `data/knockout_tree_statistics.json`
- `data/elimination_probabilities.json`
- `data/knockout_tree_scenarios.json`

### 3. Gerar o formato auxiliar dos grupos para o dashboard

```bash
python3 models/build_group_scenarios_ndjson.py
```

Esse script gera:

- `data/group_scenarios.ndjson`

### 4. Abrir o dashboard

```bash
streamlit run dash/worldcup_dashboard.py
```

## Site Web

Além do dashboard em Streamlit, o projeto agora tem uma versão web mais leve em HTML/CSS/JS:

- [dash/site/index.html](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/dash/site/index.html)
- [dash/site/styles.css](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/dash/site/styles.css)
- [dash/site/app.js](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/dash/site/app.js)

Ela consome:

- `data/worldcup_2026_dashboard_index.json`
- `data/worldcup_2026_full_bracket.ndjson`
- `data/group_scenarios.ndjson`

### Opção A: servidor Python

```bash
python3 dash/site_server.py
```

Depois abra:

```text
http://127.0.0.1:8000
```

Observação:
Se você encerrar com `Ctrl+C`, o servidor agora fecha de forma limpa. O `KeyboardInterrupt` que aparecia antes não era um erro de execução do site, era apenas a interrupção manual do processo.

### Opção B: servidor Node.js

Se você preferir não usar Python para servir o site:

```bash
node dash/site_server.mjs
```

Depois abra:

```text
http://127.0.0.1:8000
```

Essa opção usa apenas recursos nativos do Node.js.

## Fluxo Rápido

Se os dados brutos já estiverem corretos e você quiser executar o pipeline completo:

```bash
python3 models/groups.py
python3 models/elimination.py
python3 models/build_group_scenarios_ndjson.py
streamlit run dash/worldcup_dashboard.py
```

## Quando Rodar Cada Script

### Rode `models/groups.py` quando:

- mudar as odds da fase de grupos
- mudar a modelagem da fase de grupos
- quiser recomputar os classificados

### Rode `models/elimination.py` quando:

- mudar a lógica do mata-mata
- mudar as odds de campeão
- mudar `combinacoes.json`
- regenerar o bracket completo

### Rode `models/build_group_scenarios_ndjson.py` quando:

- `group_scenarios.json` for regenerado
- quiser atualizar o dashboard

## O Que Há no `worldcup_2026_full_bracket.json`

Cada item representa uma Copa completa.

Campos importantes:

- `simulation`
  Número da simulação.

- `slot_combination`
  Número da combinação dos terceiros colocados usada naquele cenário.

- `third_place_groups`
  Quais grupos tiveram terceiros classificados.

- `third_slot_map`
  Mapa do slot oficial do bracket para o terceiro correspondente.

- `classified_teams`
  Todos os classificados daquele universo.

- `rounds`
  Confrontos completos de `R32`, `R16`, `QF`, `SF`, `THIRD_PLACE` e `FINAL`.

- `champion`
  Campeão final da simulação.

## Como o Encaixe dos Terceiros Funciona

O comportamento correto hoje é:

1. a fase de grupos define quais 8 terceiros avançam
2. o conjunto desses grupos é comparado com `data/combinacoes.json`
3. a combinação encontrada define qual terceiro vai para cada slot especial do bracket
4. o mata-mata é simulado preservando exatamente essa estrutura

Ou seja, o mata-mata não sorteia terceiros de novo e não reordena terceiros por fora do cenário já gerado.

## Dashboard

O dashboard em [dash/worldcup_dashboard.py](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/dash/worldcup_dashboard.py) permite:

- filtrar por campeão
- filtrar por combinação de terceiros
- filtrar por grupos dos terceiros classificados
- filtrar por time e estágio alcançado
- escolher uma simulação específica
- ver o bracket completo
- ver grupos e classificados daquele universo
- comparar probabilidades agregadas das seleções

## Arquivos Auxiliares

Estes scripts existem, mas não fazem parte do fluxo principal atual:

- [dash/dash_deepseek.py](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/dash/dash_deepseek.py)
  Dashboard anterior.

- [dash/dash_gpt.py](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/dash/dash_gpt.py)
  Dashboard anterior.

- [models/build_dashboard_db.py](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/models/build_dashboard_db.py)
  Experimento com SQLite, não é necessário para o fluxo atual.

- [models/build_dashboard_index.py](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/models/build_dashboard_index.py)
  Reconstrói o índice resumido do dashboard a partir do bracket, se necessário.

- [models/enrich_worldcup_bracket_with_groups.py](/Users/lucasceschini/Documents/FIFA-World-Cup-2026/models/enrich_worldcup_bracket_with_groups.py)
  Utilitário legado para enriquecer o bracket com metadados de grupo.

## Troubleshooting

### `ModuleNotFoundError`

Instale dependências faltantes com:

```bash
pip install -r requirements.txt
pip install streamlit plotly scipy numpy
```

### `jq: command not found`

Instale o `jq`:

```bash
brew install jq
```

### O dashboard não abre

Confirme que estes arquivos existem:

- `data/worldcup_2026_dashboard_index.json`
- `data/worldcup_2026_full_bracket.ndjson`
- `data/group_scenarios.ndjson`

Se faltar algum deles, rode novamente:

```bash
python3 models/elimination.py
python3 models/build_group_scenarios_ndjson.py
```

## Comando Recomendado Para Uso Diário

Se os grupos já foram gerados e você só quer atualizar o mata-mata e o dashboard:

```bash
python3 models/elimination.py
python3 models/build_group_scenarios_ndjson.py
streamlit run dash/worldcup_dashboard.py
```
