import json
from pathlib import Path
from textwrap import dedent

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "data/worldcup_2026_dashboard_index.json"
BRACKET_NDJSON_PATH = ROOT / "data/worldcup_2026_full_bracket.ndjson"
GROUPS_NDJSON_PATH = ROOT / "data/group_scenarios.ndjson"
STATS_PATH = ROOT / "data/knockout_tree_statistics.json"
FINAL_PROBS_PATH = ROOT / "data/final_probabilities.json"

st.set_page_config(
    page_title="FIFA World Cup 2026 Dashboard",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
    }

    .hero {
        background:
            radial-gradient(circle at top left, rgba(255,201,74,0.32), transparent 24%),
            radial-gradient(circle at bottom right, rgba(31,149,212,0.28), transparent 26%),
            linear-gradient(135deg, #081827 0%, #0f3044 52%, #16516b 100%);
        color: white;
        border-radius: 28px;
        padding: 2.4rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 24px 56px rgba(0,0,0,0.22);
    }

    .hero h1 {
        margin: 0;
        font-size: 3rem;
        letter-spacing: -0.06em;
    }

    .hero p {
        margin: 0.85rem 0 0 0;
        max-width: 960px;
        color: rgba(255,255,255,0.82);
        font-size: 1.04rem;
    }

    .metric-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(242,247,250,0.98));
        border-radius: 22px;
        border: 1px solid rgba(5,30,48,0.08);
        padding: 1rem 1.15rem;
        box-shadow: 0 12px 28px rgba(10,31,48,0.08);
        min-height: 120px;
    }

    .metric-card.gold {
        background: linear-gradient(135deg, #ffcb47, #ff8a00);
        color: #1a1a1a;
    }

    .metric-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.11em;
        color: #597287;
        margin-bottom: 0.4rem;
    }

    .gold .metric-label {
        color: rgba(0,0,0,0.66);
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        line-height: 1.1;
        color: #0d2b3f;
    }

    .gold .metric-value {
        color: #1a1a1a;
    }

    .metric-sub {
        margin-top: 0.4rem;
        color: #5a7488;
        font-size: 0.9rem;
    }

    .gold .metric-sub {
        color: rgba(0,0,0,0.68);
    }

    .panel {
        background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(244,249,251,0.98));
        border-radius: 24px;
        border: 1px solid rgba(5,30,48,0.08);
        padding: 1rem 1.1rem;
        box-shadow: 0 14px 32px rgba(10,31,48,0.08);
    }

    .group-card {
        background: linear-gradient(180deg, #f8fbfd, #edf4f7);
        border-radius: 18px;
        border: 1px solid rgba(5,30,48,0.08);
        padding: 1rem;
    }

    .group-card h4 {
        margin: 0 0 0.75rem 0;
        color: #0f3044;
    }

    .bracket-shell { overflow-x: auto; padding-bottom: 0.5rem; }
    .bracket-grid {
        display: grid;
        grid-template-columns: repeat(6, minmax(220px, 1fr));
        gap: 16px;
        min-width: 1380px;
        align-items: start;
    }

    .bracket-col {
        background: linear-gradient(180deg, rgba(247,250,252,0.92), rgba(236,244,247,0.96));
        border: 1px solid rgba(5,30,48,0.08);
        border-radius: 22px;
        padding: 0.9rem;
    }

    .bracket-col h4 {
        margin: 0 0 0.8rem 0;
        color: #10334a;
    }

    .match-card {
        background: white;
        border: 1px solid rgba(5,30,48,0.08);
        border-radius: 16px;
        padding: 0.82rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 10px 20px rgba(10,31,48,0.06);
    }

    .match-topline {
        display: flex;
        justify-content: space-between;
        margin-bottom: 0.5rem;
        font-size: 0.74rem;
        color: #5d7687;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .team-line {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 0.6rem;
        margin: 0.35rem 0;
    }

    .team-name {
        font-weight: 600;
        color: #112f42;
    }

    .team-name.winner {
        color: #03644a;
    }

    .team-meta {
        font-size: 0.8rem;
        color: #5a7386;
        white-space: nowrap;
    }

    .winner-pill {
        display: inline-block;
        margin-top: 0.5rem;
        padding: 0.22rem 0.62rem;
        border-radius: 999px;
        background: linear-gradient(135deg, #ffcb47, #ff8a00);
        color: #171717;
        font-size: 0.78rem;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_index():
    with INDEX_PATH.open("r", encoding="utf-8") as f:
        return pd.DataFrame(json.load(f))


@st.cache_data
def load_stats():
    with STATS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_final_probs():
    with FINAL_PROBS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_ndjson_line(path: Path, line_number: int):
    with path.open("r", encoding="utf-8") as f:
        for current_line, line in enumerate(f, start=1):
            if current_line == line_number:
                return json.loads(line)
    raise ValueError(f"Linha {line_number} não encontrada em {path}")


@st.cache_data(show_spinner=False)
def fetch_bracket_simulation(line_number):
    return read_ndjson_line(BRACKET_NDJSON_PATH, line_number)


@st.cache_data(show_spinner=False)
def fetch_group_simulation(line_number):
    return read_ndjson_line(GROUPS_NDJSON_PATH, line_number)


def contains_team(teams, team_name):
    return team_name in teams


def metric_card(label, value, subtext="", gold=False):
    css_class = "metric-card gold" if gold else "metric-card"
    st.markdown(
        f"""
        <div class="{css_class}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_group_tables(group_scenario, bracket_sim):
    classified_status = {
        team["country"]: team["type"] for team in bracket_sim["classified_teams"]
    }

    cols = st.columns(3)
    for idx, group in enumerate(group_scenario["groups"]):
        group_df = pd.DataFrame(group["ranking"]).copy()
        group_df["status"] = group_df["country"].map(lambda team: classified_status.get(team, "eliminated"))
        with cols[idx % 3]:
            st.markdown(f'<div class="group-card"><h4>{group["group"]}</h4>', unsafe_allow_html=True)
            st.dataframe(
                group_df[["position", "country", "score", "status"]].rename(
                    columns={
                        "position": "Pos",
                        "country": "Seleção",
                        "score": "Score",
                        "status": "Status",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)


def render_bracket(rounds):
    phase_titles = [
        ("R32", "Rodada de 32"),
        ("R16", "Oitavas"),
        ("QF", "Quartas"),
        ("SF", "Semifinais"),
        ("THIRD_PLACE", "3º Lugar"),
        ("FINAL", "Final"),
    ]

    def match_html(match):
        if not match:
            return ""
        team_a_class = "team-name winner" if match["winner"] == match["team_a"] else "team-name"
        team_b_class = "team-name winner" if match["winner"] == match["team_b"] else "team-name"
        return dedent(f"""
            <div class="match-card">
                <div class="match-topline">
                    <span>Jogo {match['game']}</span>
                    <span>{match['phase']}</span>
                </div>
                <div class="team-line">
                    <span class="{team_a_class}">{match['team_a']}</span>
                    <span class="team-meta">{match['team_a_slot']} · {match['team_a_group']} · {match['probability_a']:.1%}</span>
                </div>
                <div class="team-line">
                    <span class="{team_b_class}">{match['team_b']}</span>
                    <span class="team-meta">{match['team_b_slot']} · {match['team_b_group']} · {match['probability_b']:.1%}</span>
                </div>
                <span class="winner-pill">Vencedor: {match['winner']}</span>
            </div>
        """).strip()

    columns_html = []
    for phase, title in phase_titles:
        phase_matches = rounds[phase]
        if isinstance(phase_matches, list):
            body = "".join(match_html(match) for match in phase_matches)
        else:
            body = match_html(phase_matches)
        columns_html.append(f'<div class="bracket-col"><h4>{title}</h4>{body}</div>')

    st.markdown(
        dedent(f"""
        <div class="bracket-shell">
          <div class="bracket-grid">{"".join(columns_html)}</div>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )


def render_team_section(stats, final_probs):
    stats_df = (
        pd.DataFrame(stats)
        .T.reset_index()
        .rename(columns={"index": "team"})
        .sort_values("champion_prob", ascending=False)
    )
    numeric_cols = [
        "champion_prob",
        "final_prob",
        "semifinal_prob",
        "quarterfinal_prob",
        "r16_prob",
        "r32_prob",
    ]
    stats_df[numeric_cols] = stats_df[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    stats_df["champion_pct"] = stats_df["champion_prob"] * 100
    stats_df["final_pct"] = stats_df["final_prob"] * 100
    stats_df["semi_pct"] = stats_df["semifinal_prob"] * 100

    top_fig = px.bar(
        stats_df.head(15),
        x="champion_pct",
        y="team",
        orientation="h",
        color="champion_pct",
        color_continuous_scale=["#0b4f6c", "#ffcb47"],
        title="Probabilidade de título",
        labels={"champion_pct": "% campeão", "team": ""},
    )
    top_fig.update_layout(height=520, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(top_fig, use_container_width=True)

    final_df = pd.DataFrame(final_probs).T.reset_index().rename(columns={"index": "team"})
    final_numeric_cols = ["direct", "best_third", "third_playoff", "eliminated"]
    available_numeric_cols = [col for col in final_numeric_cols if col in final_df.columns]
    final_df[available_numeric_cols] = final_df[available_numeric_cols].apply(
        pd.to_numeric, errors="coerce"
    ).fillna(0.0)
    merged = stats_df.merge(
        final_df[["team", "direct", "best_third", "third_playoff"]],
        on="team",
        how="left",
    )
    merged[["direct", "best_third", "third_playoff"]] = merged[
        ["direct", "best_third", "third_playoff"]
    ].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    merged["group_advance_pct"] = (
        merged["direct"] + merged["best_third"] + merged["third_playoff"]
    ) * 100
    merged["semi_pct"] = pd.to_numeric(merged["semi_pct"], errors="coerce").fillna(0.0)
    merged["final_pct"] = pd.to_numeric(merged["final_pct"], errors="coerce").fillna(0.0)
    merged["champion_pct"] = pd.to_numeric(merged["champion_pct"], errors="coerce").fillna(0.0)

    scatter = px.scatter(
        merged,
        x="group_advance_pct",
        y="champion_pct",
        size="semi_pct",
        color="final_pct",
        hover_name="team",
        color_continuous_scale=["#8bd3dd", "#f582ae", "#f3d2c1"],
        title="Classificação de grupos vs. chance de título",
        labels={"group_advance_pct": "% classificação", "champion_pct": "% campeão"},
    )
    scatter.update_layout(height=560)
    st.plotly_chart(scatter, use_container_width=True)

    st.dataframe(
        stats_df[
            ["team", "champion_prob", "final_prob", "semifinal_prob", "quarterfinal_prob", "r16_prob"]
        ].rename(
            columns={
                "team": "Seleção",
                "champion_prob": "% Campeão",
                "final_prob": "% Final",
                "semifinal_prob": "% Semi",
                "quarterfinal_prob": "% Quartas",
                "r16_prob": "% Oitavas",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


if not INDEX_PATH.exists() or not BRACKET_NDJSON_PATH.exists() or not GROUPS_NDJSON_PATH.exists():
    st.error(
        "Arquivos auxiliares do dashboard não encontrados. Rode "
        "`python3 models/elimination.py` e `python3 models/build_group_scenarios_ndjson.py` primeiro."
    )
    st.stop()

index_df = load_index()
stats = load_stats()
final_probs = load_final_probs()

all_teams = sorted({team for teams in index_df["qualified_teams"] for team in teams})
all_champions = sorted(index_df["champion"].unique().tolist())
all_combinations = sorted(index_df["slot_combination"].unique().tolist())
all_third_groups = sorted({group for groups in index_df["third_place_groups"] for group in groups})

st.markdown(
    """
    <div class="hero">
        <h1>FIFA World Cup 2026 Simulation Center</h1>
        <p>
            100.000 Copas completas conectando grupos e mata-mata, com encaixe explícito dos terceiros colocados via
            <code>combinacoes.json</code>, filtros por cenário e um chaveamento visual para explorar qualquer universo simulado.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Filtros")
    champion_filter = st.multiselect("Campeão", all_champions)
    combination_filter = st.multiselect("Combinação de terceiros", all_combinations)
    third_group_filter = st.multiselect("Grupos entre os terceiros classificados", all_third_groups)
    team_focus = st.selectbox("Time em foco", [""] + all_teams)
    stage_focus = st.selectbox(
        "Condição do time",
        [
            "Qualificado",
            "Chegou às oitavas",
            "Chegou às quartas",
            "Chegou à semi",
            "Chegou à final",
            "Campeão",
        ],
    )

filtered_df = index_df.copy()

if champion_filter:
    filtered_df = filtered_df[filtered_df["champion"].isin(champion_filter)]

if combination_filter:
    filtered_df = filtered_df[filtered_df["slot_combination"].isin(combination_filter)]

if third_group_filter:
    filtered_df = filtered_df[
        filtered_df["third_place_groups"].apply(
            lambda groups: all(group in groups for group in third_group_filter)
        )
    ]

if team_focus:
    if stage_focus == "Qualificado":
        filtered_df = filtered_df[filtered_df["qualified_teams"].apply(contains_team, args=(team_focus,))]
    elif stage_focus == "Chegou às oitavas":
        filtered_df = filtered_df[filtered_df["r16_teams"].apply(contains_team, args=(team_focus,))]
    elif stage_focus == "Chegou às quartas":
        filtered_df = filtered_df[filtered_df["qf_teams"].apply(contains_team, args=(team_focus,))]
    elif stage_focus == "Chegou à semi":
        filtered_df = filtered_df[filtered_df["sf_teams"].apply(contains_team, args=(team_focus,))]
    elif stage_focus == "Chegou à final":
        filtered_df = filtered_df[filtered_df["final_teams"].apply(contains_team, args=(team_focus,))]
    elif stage_focus == "Campeão":
        filtered_df = filtered_df[filtered_df["champion"] == team_focus]

if filtered_df.empty:
    st.warning("Nenhuma simulação atende aos filtros atuais.")
    st.stop()

selected_simulation = st.sidebar.selectbox(
    "Simulação",
    filtered_df["simulation"].tolist(),
)

selected_row = filtered_df.loc[filtered_df["simulation"] == selected_simulation].iloc[0]
line_number = int(selected_row["ndjson_line"])
bracket_sim = fetch_bracket_simulation(line_number)
group_scenario = fetch_group_simulation(line_number)

metric_cols = st.columns(5)
with metric_cols[0]:
    metric_card("Cenários filtrados", f"{len(filtered_df):,}", "Escopo ativo")
with metric_cols[1]:
    metric_card("Simulação", f"#{selected_simulation}", f"Combinação {selected_row['slot_combination']}")
with metric_cols[2]:
    metric_card("Campeão", selected_row["champion"], "Desfecho desta Copa", gold=True)
with metric_cols[3]:
    metric_card("Vice", selected_row["runner_up"], "Finalista derrotado")
with metric_cols[4]:
    metric_card("3º Lugar", selected_row["third_place"], f"Grupos: {', '.join(selected_row['third_place_groups'])}")

tab_overview, tab_simulation, tab_teams = st.tabs(
    ["Panorama", "Explorador da Simulação", "Inteligência das Seleções"]
)

with tab_overview:
    st.markdown("### Distribuição do recorte atual")
    col1, col2 = st.columns([1.2, 1])

    champion_dist = (
        filtered_df.groupby("champion")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(12)
    )
    champion_dist["share"] = champion_dist["count"] / champion_dist["count"].sum() * 100

    with col1:
        champion_fig = px.bar(
            champion_dist,
            x="share",
            y="champion",
            orientation="h",
            color="share",
            color_continuous_scale=["#0b4f6c", "#ffcb47"],
            title="Campeões mais frequentes",
            labels={"share": "% do recorte", "champion": ""},
        )
        champion_fig.update_layout(height=430, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(champion_fig, use_container_width=True)

    with col2:
        combo_dist = (
            filtered_df.groupby("slot_combination")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
            .head(15)
        )
        combo_fig = px.bar(
            combo_dist,
            x="slot_combination",
            y="count",
            color="count",
            color_continuous_scale=["#8bd3dd", "#f582ae"],
            title="Combinações mais recorrentes",
            labels={"slot_combination": "Combinação", "count": "Qtd."},
        )
        combo_fig.update_layout(height=430)
        st.plotly_chart(combo_fig, use_container_width=True)

    st.markdown("### Lista de simulações do recorte")
    st.dataframe(
        filtered_df[
            ["simulation", "slot_combination", "champion", "runner_up", "third_place", "third_place_groups"]
        ].rename(
            columns={
                "simulation": "Simulação",
                "slot_combination": "Combinação",
                "champion": "Campeão",
                "runner_up": "Vice",
                "third_place": "3º Lugar",
                "third_place_groups": "Grupos dos terceiros",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

with tab_simulation:
    col_top, col_side = st.columns([1.25, 0.75])

    with col_top:
        st.markdown("### Chaveamento completo")
        render_bracket(bracket_sim["rounds"])

    with col_side:
        st.markdown("### Final da Copa")
        final_df = pd.DataFrame([bracket_sim["rounds"]["FINAL"]]).rename(
            columns={
                "team_a": "Seleção A",
                "team_b": "Seleção B",
                "probability_a": "Prob. A",
                "probability_b": "Prob. B",
                "winner": "Vencedor",
                "loser": "Derrotado",
            }
        )
        st.dataframe(
            final_df[["Seleção A", "Seleção B", "Prob. A", "Prob. B", "Vencedor", "Derrotado"]],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Classificados")
        classified_df = pd.DataFrame(bracket_sim["classified_teams"]).rename(
            columns={
                "country": "Seleção",
                "group": "Grupo",
                "position": "Pos",
                "type": "Via",
                "score": "Score",
                "third_slot": "Slot 3º",
            }
        )
        st.dataframe(classified_df, use_container_width=True, hide_index=True)

    st.markdown("### Grupos desta simulação")
    render_group_tables(group_scenario, bracket_sim)

with tab_teams:
    render_team_section(stats, final_probs)
