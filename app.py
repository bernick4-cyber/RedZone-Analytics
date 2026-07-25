from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# ---------------------------------------------------------
# PAGE SETTINGS
# ---------------------------------------------------------
st.set_page_config(
    page_title="2025 NFL Player Personnel",
    page_icon="🏈",
    layout="wide",
)


# ---------------------------------------------------------
# FILE SETTINGS
# ---------------------------------------------------------
EXCEL_FILE = Path(__file__).parent / "NFL Project 2025.xlsx"


# Full NFL team name to abbreviation
TEAM_ABBREVIATIONS = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LAR",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS",
}
# ---------------------------------------------------------
# LOAD WORKBOOK
# ---------------------------------------------------------
@st.cache_data
def load_data():
    if not EXCEL_FILE.exists():
        raise FileNotFoundError(
            f"Could not find '{EXCEL_FILE.name}' in:\n{EXCEL_FILE.parent}"
        )

    players = pd.read_excel(
        EXCEL_FILE,
        sheet_name="2025 Week by Week",
    )

    schedule = pd.read_excel(
        EXCEL_FILE,
        sheet_name="2025 Schedule",
    )

    rankings = pd.read_excel(
        EXCEL_FILE,
        sheet_name="Defense Rankings",
    )

    # Clean column names
    players.columns = players.columns.map(str).str.strip()
    schedule.columns = schedule.columns.map(str).str.strip()
    rankings.columns = rankings.columns.map(str).str.strip()

    # Clean player fields
    players["Player"] = (
        players["Player"]
        .astype(str)
        .str.strip()
    )

    players["Position"] = (
        players["Position"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    players["Team"] = (
        players["Team"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # Clean schedule fields
    schedule["Team"] = (
        schedule["Team"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    schedule["Opp"] = (
        schedule["Opp"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    schedule["Week"] = pd.to_numeric(
        schedule["Week"],
        errors="coerce",
    )

    if "Home/Away" in schedule.columns:
        schedule["Home/Away"] = (
            schedule["Home/Away"]
            .astype(str)
            .str.strip()
        )

    # Add team abbreviations to defensive rankings
    rankings["Abbreviation"] = (
        rankings["Team"]
        .astype(str)
        .str.strip()
        .map(TEAM_ABBREVIATIONS)
    )

    # Convert player numeric columns
    for column in ["ADP", "AVG"]:
        if column in players.columns:
            players[column] = pd.to_numeric(
                players[column],
                errors="coerce",
            )

    # Convert defensive rank columns to numbers
    for column in ["RB Rank", "WR Rank", "TE Rank"]:
        if column in rankings.columns:
            rankings[column] = pd.to_numeric(
                rankings[column],
                errors="coerce",
            )

    return players, schedule, rankings
# ---------------------------------------------------------
# POSITION-BASED MATCHUP SETTINGS
# ---------------------------------------------------------
def get_matchup_columns(position):
    """
    Select the correct defensive ranking based on player position.
    """

    position = str(position).upper().strip()

    if position == "RB":
        return {
            "rank_column": "RB Rank",
            "rank_label": "RB D Rank",
        }

    if position == "TE":
        return {
            "rank_column": "TE Rank",
            "rank_label": "TE D Rank",
        }

    # WR uses WR defensive rank.
    # QB temporarily uses WR defensive rank
    # as a passing-defense proxy.
    return {
        "rank_column": "WR Rank",
        "rank_label": (
            "WR D Rank"
            if position == "WR"
            else "Pass D Rank"
        ),
    }
# ---------------------------------------------------------
# CREATE ONE PLAYER'S WEEKLY TABLE
# ---------------------------------------------------------
def create_player_table(player_row, schedule, rankings):
    player_position = player_row["Position"]
    player_team = player_row["Team"]

    matchup_columns = get_matchup_columns(player_position)

    # Get Weeks 1-17 for the player's NFL team
    player_schedule = schedule[
        schedule["Team"] == player_team
    ].copy()

    player_schedule = player_schedule[
        player_schedule["Week"].between(1, 17)
    ].copy()

    player_schedule = player_schedule.sort_values("Week")

    # Merge the correct defensive rank onto each opponent
    ranking_lookup = rankings[
        [
            "Abbreviation",
            matchup_columns["rank_column"],
        ]
    ].drop_duplicates(
        subset="Abbreviation"
    )

    ranking_lookup = ranking_lookup.rename(
        columns={
            "Abbreviation": "Opp",
            matchup_columns["rank_column"]:
                matchup_columns["rank_label"],
        }
    )

    result = player_schedule.merge(
        ranking_lookup,
        on="Opp",
        how="left",
    )

    # Pull the player's fantasy score for each week
    fantasy_points = []

    for week in result["Week"]:
        possible_columns = [
            str(int(week)),
            int(week),
        ]

        week_value = 0

        for column in possible_columns:
            if column in player_row.index:
                week_value = player_row[column]
                break

        week_value = pd.to_numeric(
            week_value,
            errors="coerce",
        )

        if pd.isna(week_value):
            week_value = 0

        fantasy_points.append(
            round(float(week_value), 1)
        )

    result["Fantasy Pts"] = fantasy_points

    # Clear matchup data for bye weeks
    bye_mask = result["Opp"] == "BYE"

    result.loc[
        bye_mask,
        matchup_columns["rank_label"],
    ] = pd.NA

    result.loc[
        bye_mask,
        "Fantasy Pts",
    ] = 0

    # Create readable home/away matchup labels
    result["Matchup"] = result.apply(
        lambda row: (
            "BYE"
            if row["Opp"] == "BYE"
            else (
                f"✈️ @ {row['Opp']}"
                if str(
                    row.get("Home/Away", "")
                ).lower() == "away"
                else f"🏠 vs {row['Opp']}"
            )
        ),
        axis=1,
    )

    final_columns = [
        "Week",
        "Matchup",
        matchup_columns["rank_label"],
        "Fantasy Pts",
    ]

    return (
        result[final_columns],
        matchup_columns,
    )
# ---------------------------------------------------------
# CALCULATE HOME / AWAY PERFORMANCE
# ---------------------------------------------------------
def calculate_home_away_stats(weekly_table):
    """
    Calculate the player's average fantasy points
    in home games and away games.
    """

    home_games = weekly_table[
        weekly_table["Matchup"].str.contains(
            "vs",
            case=False,
            na=False,
        )
    ].copy()

    away_games = weekly_table[
        weekly_table["Matchup"].str.contains(
            "@",
            case=False,
            na=False,
        )
    ].copy()

    home_average = home_games["Fantasy Pts"].mean()
    away_average = away_games["Fantasy Pts"].mean()

    if pd.isna(home_average):
        home_average = 0

    if pd.isna(away_average):
        away_average = 0

    home_average = round(float(home_average), 1)
    away_average = round(float(away_average), 1)

    if home_average > away_average:
        better_split = "Home"
    elif away_average > home_average:
        better_split = "Away"
    else:
        better_split = "Even"

    return {
        "home_average": home_average,
        "away_average": away_average,
        "better_split": better_split,
        "home_games": len(home_games),
        "away_games": len(away_games),
    }
# ---------------------------------------------------------
# CALCULATE POSITION-WIDE RANKINGS
# ---------------------------------------------------------
@st.cache_data
def calculate_position_rankings(
    players,
    schedule,
    rankings,
    selected_position,
):
    """
    Compare every player at the selected position.

    Rankings produced:
    - Home fantasy average rank
    - Away fantasy average rank
    - Hardest schedule rank
    """

    position_players = players[
        players["Position"] == selected_position
    ].copy()

    ranking_rows = []

    for _, player_row in position_players.iterrows():
        try:
            weekly_table, matchup_columns = create_player_table(
                player_row,
                schedule,
                rankings,
            )

            split_stats = calculate_home_away_stats(
                weekly_table
            )

            rank_column = matchup_columns["rank_label"]

            defensive_ranks = pd.to_numeric(
                weekly_table[rank_column],
                errors="coerce",
            )

            average_defensive_rank = (
                defensive_ranks.mean()
            )

            if pd.isna(average_defensive_rank):
                average_defensive_rank = 99

            ranking_rows.append(
                {
                    "Player": player_row["Player"],
                    "Team": player_row["Team"],
                    "Position": player_row["Position"],
                    "Home Avg": split_stats[
                        "home_average"
                    ],
                    "Away Avg": split_stats[
                        "away_average"
                    ],
                    "Average Defensive Rank": round(
                        float(average_defensive_rank),
                        2,
                    ),
                }
            )

        except Exception:
            continue

    ranking_table = pd.DataFrame(ranking_rows)

    if ranking_table.empty:
        return ranking_table

    # Higher fantasy average is better
    ranking_table["Home League Rank"] = (
        ranking_table["Home Avg"]
        .rank(
            method="min",
            ascending=False,
        )
        .astype(int)
    )

    ranking_table["Away League Rank"] = (
        ranking_table["Away Avg"]
        .rank(
            method="min",
            ascending=False,
        )
        .astype(int)
    )

    # Lower defensive rank means tougher opponents.
    # Example:
    # Average opponent rank of 8 is harder than 24.
    ranking_table["Hardest Schedule Rank"] = (
        ranking_table["Average Defensive Rank"]
        .rank(
            method="min",
            ascending=True,
        )
        .astype(int)
    )

    ranking_table = ranking_table.sort_values(
        [
            "Hardest Schedule Rank",
            "Home League Rank",
        ]
    ).reset_index(drop=True)

    return ranking_table
# ---------------------------------------------------------
# APP HEADER
# ---------------------------------------------------------
st.title("🏈 2025 NFL Player Personnel Dashboard")

st.caption(
    "Review weekly fantasy production, matchup difficulty, "
    "home/away splits, and position-wide rankings."
)


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
try:
    players, schedule, rankings = load_data()

except FileNotFoundError as error:
    st.error(str(error))
    st.stop()

except Exception as error:
    st.error(
        "The workbook could not be loaded. "
        "Check the sheet names and column names."
    )

    st.exception(error)
    st.stop()


# ---------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------
st.sidebar.header("Player Filters")

available_positions = sorted(
    players["Position"]
    .dropna()
    .astype(str)
    .unique()
)

selected_position = st.sidebar.selectbox(
    "Position",
    available_positions,
)

position_players = players[
    players["Position"] == selected_position
].copy()


available_teams = sorted(
    position_players["Team"]
    .dropna()
    .astype(str)
    .unique()
)

team_options = ["All Teams"] + available_teams

selected_team = st.sidebar.selectbox(
    "Team",
    team_options,
)


if selected_team != "All Teams":
    position_players = position_players[
        position_players["Team"] == selected_team
    ].copy()


position_players = position_players.sort_values(
    ["ADP", "Player"],
    na_position="last",
)


available_players = (
    position_players["Player"]
    .dropna()
    .astype(str)
    .tolist()
)

if not available_players:
    st.warning(
        "No players were found for the selected filters."
    )
    st.stop()


selected_player = st.sidebar.selectbox(
    "Player",
    available_players,
)


# ---------------------------------------------------------
# GET SELECTED PLAYER
# ---------------------------------------------------------
selected_player_rows = position_players[
    position_players["Player"] == selected_player
]

if selected_player_rows.empty:
    st.error("The selected player could not be found.")
    st.stop()

player_row = selected_player_rows.iloc[0]


# ---------------------------------------------------------
# BUILD SELECTED PLAYER TABLE
# ---------------------------------------------------------
try:
    weekly_table, matchup_columns = create_player_table(
        player_row,
        schedule,
        rankings,
    )

    split_stats = calculate_home_away_stats(
        weekly_table
    )

    position_ranking_table = calculate_position_rankings(
        players,
        schedule,
        rankings,
        selected_position,
    )

except Exception as error:
    st.error(
        "The player dashboard could not be created."
    )

    st.exception(error)
    st.stop()
    # ---------------------------------------------------------
# SELECTED PLAYER RANKINGS
# ---------------------------------------------------------
selected_ranking_row = position_ranking_table[
    position_ranking_table["Player"] == selected_player
]

if not selected_ranking_row.empty:
    selected_ranking_row = selected_ranking_row.iloc[0]

    home_league_rank = int(
        selected_ranking_row["Home League Rank"]
    )

    away_league_rank = int(
        selected_ranking_row["Away League Rank"]
    )

    hardest_schedule_rank = int(
        selected_ranking_row["Hardest Schedule Rank"]
    )

    average_defensive_rank = round(
        float(
            selected_ranking_row[
                "Average Defensive Rank"
            ]
        ),
        1,
    )

else:
    home_league_rank = None
    away_league_rank = None
    hardest_schedule_rank = None
    average_defensive_rank = None


# ---------------------------------------------------------
# PLAYER HEADER
# ---------------------------------------------------------
st.header(selected_player)

st.caption(
    f"{player_row['Position']} | "
    f"{player_row['Team']}"
)


# ---------------------------------------------------------
# BASIC PLAYER INFORMATION
# ---------------------------------------------------------
info_col1, info_col2, info_col3, info_col4 = st.columns(4)

with info_col1:
    st.metric(
        "Position",
        player_row["Position"],
    )

with info_col2:
    st.metric(
        "Team",
        player_row["Team"],
    )

with info_col3:
    adp_value = player_row.get("ADP", pd.NA)

    if pd.isna(adp_value):
        adp_display = "N/A"
    else:
        adp_display = round(
            float(adp_value),
            1,
        )

    st.metric(
        "ADP",
        adp_display,
    )

with info_col4:
    fantasy_average = player_row.get("AVG", pd.NA)

    if pd.isna(fantasy_average):
        fantasy_average = weekly_table[
            "Fantasy Pts"
        ].mean()

    if pd.isna(fantasy_average):
        fantasy_average_display = "N/A"
    else:
        fantasy_average_display = round(
            float(fantasy_average),
            1,
        )

    st.metric(
        "Fantasy Average",
        fantasy_average_display,
    )


st.divider()


# ---------------------------------------------------------
# HOME / AWAY SPLIT CARDS
# ---------------------------------------------------------
st.subheader("Home and Away Performance")

split_col1, split_col2, split_col3 = st.columns(3)

with split_col1:
    st.metric(
        "🏠 Home Avg",
        split_stats["home_average"],
        help=(
            f"Average fantasy points across "
            f"{split_stats['home_games']} home games."
        ),
    )

    if home_league_rank is not None:
        st.caption(
            f"League Rank: #{home_league_rank} "
            f"among {selected_position}s"
        )

with split_col2:
    st.metric(
        "✈️ Away Avg",
        split_stats["away_average"],
        help=(
            f"Average fantasy points across "
            f"{split_stats['away_games']} away games."
        ),
    )

    if away_league_rank is not None:
        st.caption(
            f"League Rank: #{away_league_rank} "
            f"among {selected_position}s"
        )

with split_col3:
    better_split = split_stats["better_split"]

    if better_split == "Home":
        better_split_display = "🏠 Home"
    elif better_split == "Away":
        better_split_display = "✈️ Away"
    else:
        better_split_display = "Even"

    st.metric(
        "Better Split",
        better_split_display,
    )


st.divider()


# ---------------------------------------------------------
# SCHEDULE DIFFICULTY CARDS
# ---------------------------------------------------------
st.subheader("Schedule Difficulty")

schedule_col1, schedule_col2 = st.columns(2)

with schedule_col1:
    if hardest_schedule_rank is None:
        hardest_schedule_display = "N/A"
    else:
        hardest_schedule_display = (
            f"#{hardest_schedule_rank}"
        )

    st.metric(
        "Hardest Schedule Rank",
        hardest_schedule_display,
        help=(
            "Ranked against players at the same position. "
            "#1 represents the hardest schedule."
        ),
    )

    if hardest_schedule_rank is not None:
        st.caption(
            f"Compared with all "
            f"{selected_position}s in the data."
        )

with schedule_col2:
    if average_defensive_rank is None:
        average_defensive_rank_display = "N/A"
    else:
        average_defensive_rank_display = (
            average_defensive_rank
        )

    st.metric(
        "Average Opponent Defensive Rank",
        average_defensive_rank_display,
        help=(
            "A lower number means the player faced "
            "stronger defenses on average."
        ),
    )
    # ---------------------------------------------------------
# WEEKLY MATCHUP TABLE
# ---------------------------------------------------------
st.divider()

st.subheader(f"{selected_player}: Weekly Matchups")

rank_column = matchup_columns["rank_label"]


def color_defensive_rank(value):
    """
    Color defensive rankings.

    Lower rank = tougher defense
    Higher rank = easier defense
    """

    if pd.isna(value):
        return ""

    try:
        value = float(value)
    except Exception:
        return ""

    if value <= 5:
        return "background-color:#8B0000;color:white"

    elif value <= 10:
        return "background-color:#CD5C5C;color:white"

    elif value <= 16:
        return "background-color:#FFF3CD"

    elif value <= 24:
        return "background-color:#D4EDDA"

    else:
        return "background-color:#28A745;color:white"


styled_table = (
    weekly_table.style
    .map(
        color_defensive_rank,
        subset=[rank_column],
    )
    .format(
        {
            rank_column: "{:.0f}",
            "Fantasy Pts": "{:.1f}",
        }
    )
)

st.dataframe(
    styled_table,
    use_container_width=True,
    hide_index=True,
)
# ---------------------------------------------------------
# WEEKLY FANTASY POINTS CHART
# ---------------------------------------------------------
st.divider()

st.subheader(f"{selected_player}: Weekly Fantasy Production")

chart_data = weekly_table.copy()

chart_data["Week"] = pd.to_numeric(
    chart_data["Week"],
    errors="coerce",
)

chart_data["Fantasy Pts"] = pd.to_numeric(
    chart_data["Fantasy Pts"],
    errors="coerce",
).fillna(0)

chart_data = chart_data.dropna(
    subset=["Week"]
)

chart_data["Week"] = chart_data["Week"].astype(int)

chart_data["Week Label"] = (
    "Week " + chart_data["Week"].astype(str)
)

chart_data["Defensive Rank"] = pd.to_numeric(
    chart_data[rank_column],
    errors="coerce",
)


fig = px.bar(
    chart_data,
    x="Week",
    y="Fantasy Pts",
    text="Fantasy Pts",
    hover_data={
        "Week": True,
        "Matchup": True,
        "Fantasy Pts": ":.1f",
        "Defensive Rank": True,
        "Week Label": False,
    },
    labels={
        "Week": "NFL Week",
        "Fantasy Pts": "Fantasy Points",
    },
    title=(
        f"{selected_player} Weekly Fantasy Points"
    ),
)


fig.update_traces(
    texttemplate="%{text:.1f}",
    textposition="outside",
    cliponaxis=False,
)


fig.update_layout(
    xaxis={
        "tickmode": "linear",
        "tick0": 1,
        "dtick": 1,
        "range": [0.5, 17.5],
    },
    yaxis={
        "rangemode": "tozero",
    },
    hovermode="x unified",
    showlegend=False,
    margin={
        "l": 20,
        "r": 20,
        "t": 60,
        "b": 20,
    },
)


st.plotly_chart(
    fig,
    use_container_width=True,
) 
# ---------------------------------------------------------
# DOWNLOAD WEEKLY MATCHUP DATA
# ---------------------------------------------------------
st.divider()

st.subheader("Download Player Data")

download_table = weekly_table.copy()

download_table.insert(
    0,
    "Player",
    selected_player,
)

download_table.insert(
    1,
    "Position",
    player_row["Position"],
)

download_table.insert(
    2,
    "Team",
    player_row["Team"],
)

csv_data = download_table.to_csv(
    index=False,
).encode("utf-8")


st.download_button(
    label="Download Weekly Matchups as CSV",
    data=csv_data,
    file_name=(
        f"{selected_player.replace(' ', '_')}"
        "_weekly_matchups.csv"
    ),
    mime="text/csv",
)


# ---------------------------------------------------------
# OPTIONAL POSITION RANKINGS TABLE
# ---------------------------------------------------------
with st.expander(
    f"View All {selected_position} Rankings"
):
    ranking_display = position_ranking_table[
        [
            "Player",
            "Team",
            "Home Avg",
            "Home League Rank",
            "Away Avg",
            "Away League Rank",
            "Average Defensive Rank",
            "Hardest Schedule Rank",
        ]
    ].copy()

    ranking_display = ranking_display.sort_values(
        "Hardest Schedule Rank"
    )

    st.dataframe(
        ranking_display,
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------
st.caption(
    "Defensive schedule rankings compare players only "
    "with others at the same position."
)