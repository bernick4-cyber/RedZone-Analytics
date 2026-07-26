from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# ---------------------------------------------------------
# PAGE SETTINGS
# ---------------------------------------------------------
st.set_page_config(
    page_title="Top Weekly Performances",
    page_icon="🔥",
    layout="wide",
)


# ---------------------------------------------------------
# FILE SETTINGS
# ---------------------------------------------------------
EXCEL_FILE = Path(__file__).parent.parent / "NFL Project 2025.xlsx"


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
@st.cache_data
def load_player_data(file_modified_time):
    if not EXCEL_FILE.exists():
        raise FileNotFoundError(
            f"Could not find '{EXCEL_FILE.name}'."
        )

    players = pd.read_excel(
        EXCEL_FILE,
        sheet_name="2025 Week by Week",
    )

    players.columns = (
        players.columns
        .map(str)
        .str.strip()
    )

    players["Player"] = (
        players["Player"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    players["Position"] = (
        players["Position"]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    players["Team"] = (
        players["Team"]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
        .replace(
            {
                "JAC": "JAX",
            }
        )
    )

    if "ADP" in players.columns:
        players["ADP"] = pd.to_numeric(
            players["ADP"],
            errors="coerce",
        )

    return players


try:
    players = load_player_data(
        EXCEL_FILE.stat().st_mtime
    )

except FileNotFoundError as error:
    st.error(str(error))
    st.stop()

except Exception as error:
    st.error(
        "The weekly player data could not be loaded."
    )
    st.exception(error)
    st.stop()


# ---------------------------------------------------------
# CONVERT WIDE WEEKLY DATA TO LONG FORMAT
# ---------------------------------------------------------
week_columns = [
    str(week)
    for week in range(1, 18)
    if str(week) in players.columns
]

if not week_columns:
    st.error(
        "No Week 1-17 columns were found in the player sheet."
    )
    st.stop()


weekly_long = players.melt(
    id_vars=[
        column
        for column in [
            "Player",
            "Position",
            "Team",
            "ADP",
        ]
        if column in players.columns
    ],
    value_vars=week_columns,
    var_name="Week",
    value_name="Fantasy Pts",
)

weekly_long["Week"] = pd.to_numeric(
    weekly_long["Week"],
    errors="coerce",
)

weekly_long["Fantasy Pts"] = pd.to_numeric(
    weekly_long["Fantasy Pts"],
    errors="coerce",
)

weekly_long = weekly_long.dropna(
    subset=[
        "Player",
        "Week",
        "Fantasy Pts",
    ]
)

weekly_long["Week"] = (
    weekly_long["Week"]
    .astype(int)
)

weekly_long["Fantasy Pts"] = (
    weekly_long["Fantasy Pts"]
    .round(1)
)


# ---------------------------------------------------------
# PAGE HEADER
# ---------------------------------------------------------
st.title("🔥 Top Weekly Performances")

st.caption(
    "Search the highest fantasy-scoring performances "
    "by NFL week and position."
)


# ---------------------------------------------------------
# FILTERS
# ---------------------------------------------------------
filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    selected_week = st.selectbox(
        "NFL Week",
        options=list(range(1, 18)),
        index=0,
    )

with filter_col2:
    position_options = [
        "Overall"
    ] + sorted(
        weekly_long["Position"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_position = st.selectbox(
        "Position",
        options=position_options,
    )

with filter_col3:
    selected_top_n = st.selectbox(
        "Number of Players",
        options=[5, 10, 20, 25],
        index=1,
    )


# ---------------------------------------------------------
# APPLY FILTERS
# ---------------------------------------------------------
performance_table = weekly_long[
    weekly_long["Week"] == selected_week
].copy()

if selected_position != "Overall":
    performance_table = performance_table[
        performance_table["Position"]
        == selected_position
    ].copy()


performance_table = (
    performance_table
    .sort_values(
        [
            "Fantasy Pts",
            "Player",
        ],
        ascending=[
            False,
            True,
        ],
    )
    .head(selected_top_n)
    .reset_index(drop=True)
)

performance_table.index = (
    performance_table.index + 1
)

performance_table.insert(
    0,
    "Rank",
    performance_table.index,
)


# ---------------------------------------------------------
# RESULTS
# ---------------------------------------------------------
st.subheader(
    f"Top {selected_top_n} – Week {selected_week}"
)

if selected_position == "Overall":
    st.caption("All positions")
else:
    st.caption(f"Position: {selected_position}")


if performance_table.empty:
    st.warning(
        "No performances were found for these filters."
    )
    st.stop()


leader = performance_table.iloc[0]

metric_col1, metric_col2, metric_col3 = st.columns(3)

with metric_col1:
    st.metric(
        "Top Performer",
        leader["Player"],
    )

with metric_col2:
    st.metric(
        "Fantasy Points",
        f"{leader['Fantasy Pts']:.1f}",
    )

with metric_col3:
    st.metric(
        "Team / Position",
        f"{leader['Team']} / {leader['Position']}",
    )


# ---------------------------------------------------------
# BAR CHART
# ---------------------------------------------------------
chart_table = performance_table.sort_values(
    "Fantasy Pts",
    ascending=True,
)

fig = px.bar(
    chart_table,
    x="Fantasy Pts",
    y="Player",
    orientation="h",
    text="Fantasy Pts",
    hover_data={
        "Rank": True,
        "Team": True,
        "Position": True,
        "Fantasy Pts": ":.1f",
    },
    labels={
        "Fantasy Pts": "Fantasy Points",
        "Player": "Player",
    },
    title=(
        f"Week {selected_week} Top "
        f"{selected_position} Performances"
    ),
)

fig.update_traces(
    texttemplate="%{text:.1f}",
    textposition="outside",
    cliponaxis=False,
)

fig.update_layout(
    showlegend=False,
    yaxis_title="",
    xaxis_title="Fantasy Points",
    margin={
        "l": 20,
        "r": 40,
        "t": 60,
        "b": 20,
    },
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ---------------------------------------------------------
# RESULTS TABLE
# ---------------------------------------------------------
st.subheader("Performance Rankings")

display_columns = [
    "Rank",
    "Player",
    "Position",
    "Team",
    "Fantasy Pts",
]

if "ADP" in performance_table.columns:
    display_columns.insert(
        4,
        "ADP",
    )

display_table = performance_table[
    display_columns
].copy()

format_columns = {
    "Fantasy Pts": "{:.1f}",
}

if "ADP" in display_table.columns:
    format_columns["ADP"] = "{:.1f}"


st.dataframe(
    display_table.style.format(
        format_columns,
        na_rep="—",
    ),
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# DOWNLOAD
# ---------------------------------------------------------
csv_data = display_table.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    label="Download Rankings as CSV",
    data=csv_data,
    file_name=(
        f"week_{selected_week}_"
        f"{selected_position.lower()}_"
        f"top_{selected_top_n}.csv"
    ),
    mime="text/csv",
)
