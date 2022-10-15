import streamlit as st
import pandas as pd
import os
from watcher import BACKUP_DIR
from extract import main as parse_matchfiles
from extract import parse_xml, RESULT_DIR
from plots import (
    plot_mmr_hisotry, 
    display_KD,
    get_KD, 
    display_mmr, 
    display_extraction_rate, 
    effect_on_success_chance, 
    display_mmr_taken,
)
from dotenv import load_dotenv, set_key, find_dotenv
from glob import glob
from match_utils import find_my_id, simplify_scoreboard, construct_match_name, predict_mmr
import subprocess
import sys


# setup dotenv
if not os.path.exists(".env"):
    with open(".env", "w") as file:
        pass
load_dotenv()


def start_watcher_process():
    proc = subprocess.Popen( # opening via popen ensures running and traceability even when webapp is refreshed / closed
        [sys.executable, os.path.join("src", "watcher.py")],
        creationflags = subprocess.CREATE_NEW_CONSOLE, # so a separate window pops up that can be closed by the user
    )
    if proc.poll() is None: # process still running in mainloop
        st.success("Match Recorder started.")
    else:
        st.error("Match Recorder failed.")


st.title("Hunt Journal")


# starting the game and match recorder
tracked_file_is_setup = os.path.exists(os.getenv("watched_file") or "")
process_alive = st.session_state.get("watcher_process") is not None
col0, col1 = st.columns(2)
with col0: 
    start_game = st.button("Play Hunt: Showdown!")
    also_start_filewatcher = st.checkbox(
        label = "Start Match Recorder with Game", 
        value = tracked_file_is_setup,
        disabled = not tracked_file_is_setup,
        help = "Can only be used if matchfile is tracked."
    )
    if start_game:
        st.info("Game starting...")
        os.system("start steam://rungameid/594650")
        if also_start_filewatcher:
            start_watcher_process()
with col1:
    if st.button("Start Match Recorder", disabled = not tracked_file_is_setup):
        start_watcher_process()
    

st.markdown("-------")
st.caption("About the data collection")
col0, col1 = st.columns(2)  
with col0:
    st.write(
        "Results of matches are stored in an `attributes.xml` file within the games installation directory. ",
        "On the right you can set the path of that file according to where you installed the game. \n\n",
        "Sadly, only the results of the last match are stored at a time. ",
        "But to calculate the statistics we need a history of all matches. ",
        "Therefore the Match Recorder will backup every change to the file. ",
    )
with col1:
    filepath = st.text_input(
        "Set the path to Matchfile",
        value = os.getenv("watched_file") or os.path.join("C:", "Program Files (x86)", "Steam", "steamapps", "common", "Hunt Showdown", "user", "profiles", "default", "attributes.xml"),
        help = "The file will be somewhere like `/steamapps/common/Hunt Showdown/user/profiles/default/attributes.xml`"
    )
    try:
        with open(filepath, "r", errors="ignore") as infile:
            xml = infile.read()
        parse_xml(xml)
    except Exception as e:
        st.error(f"Invalid Matchfile: {e}")
    else:
        st.success("Valid Matchfile.")
        set_key(find_dotenv(), "watched_file", filepath) # write vars
        load_dotenv(override=True) # force reload env vars
    backup_dir = os.getenv("backup_dir") or BACKUP_DIR
    st.info(f"Backup Location: `{os.path.abspath(backup_dir)}`")


st.caption("After you collected some data")
col0, col1 = st.columns(2)  
with col0:
    st.write(
        "Once some matchfiles have been collect we can read them all in and calculate the statistics.",
        "Simply press the button on the right."
    )
with col1:
    parse_resultfiles = st.button(
        label = "Calculate Statistics",
        disabled = len(glob("data/raw/*.xml")) == 0,
        help = "Read data form copied matchfiles."
    )
if parse_resultfiles:
    placeholder = st.empty()
    with placeholder.container():
        st.write("Parsing Match result files...")
        bar = st.progress(0)
        for i, path in parse_matchfiles():
            bar.progress(i)
    placeholder.empty()
st.markdown("-------")


RESULTFILE = os.path.join(RESULT_DIR, "matches.pq")
if not os.path.exists(RESULTFILE):
    st.warning("No Match Data has been processed.")
else:
    matches = pd.read_parquet(RESULTFILE).reset_index()

    st.header("Overall Statistics")

    # metrics
    n_matches = int(matches["matchno"].nunique())
    if n_matches > 2:
        trend_window = st.slider(
            "# of new matches for trend",
            value = min(3, n_matches-2),
            min_value = 1,
            max_value = n_matches-1,
            step = 1,
        )
    else:
        trend_window = 1
    columns = st.columns(3)
    with columns[0]:
        display_mmr(matches, trend_window)
    with columns[1]:
        display_KD(matches, trend_window)
    with columns[2]:
        display_extraction_rate(matches, trend_window)
    display_mmr_taken(matches)

    # MMR history
    st.subheader("MMR History")
    a,b = st.columns(2)
    with a:
        xaxis = st.radio(
            "X-Axis",
            ["# of Match", "Time"],
        )
        xaxis = "datetime_match_ended" if xaxis == "Time" else "matchno"
    with b:
        mmr_out = st.radio(
            "MMR at Match...",
            ["End", "Start"],
            help = "With setting `End` the last MMR is eastimated."
        )
        mmr_out = mmr_out=="End"
    fig = plot_mmr_hisotry(matches, xaxis, mmr_out)
    st.plotly_chart(fig)

    st.subheader("Teammate Analysis")
    st.write(
        "The following analysis tries to give an indication which teammates are the most helpful to you.",
        "To calculate the odds for a whole team simply multiply the odds of the individuals.",
        "\n\n",
        "The amount of matches needed before a player shows up in this analysis can vary.",
        "The algorithm will try to set this requirement as low as possible, while making sure results can be calculated."
    )
    target = st.selectbox("Analyze Teammates influence on...", ["extracting with a bounty", "surviving"])
    st.pyplot(effect_on_success_chance(matches, target))


    st.markdown("---")
    st.header("Individual Match Statistics")
    # match table
    my_id = find_my_id(matches)
    match_display_names = {f"{matchno+1}: {construct_match_name(subset, my_id)}": matchno for matchno, subset in matches.groupby("matchno")}
    selected_match = st.selectbox(
        label = "Select a Match",
        options = reversed(match_display_names.keys()),
    )
    selection = matches.loc[matches["matchno"] == match_display_names[selected_match]]
    
    # single match KPIs
    my_game = selection.loc[(matches["profileid"] == my_id)]
    mmr_in = my_game["mmr"].iloc[0]
    try:
        mmr_out = matches.loc[
            (matches["matchno"] == match_display_names[selected_match] + 1) &
            (matches["profileid"] == my_id),
            "mmr"
        ].iloc[0]
        mmr_out_eastimated = False
    except IndexError:
        mmr_out = predict_mmr(matches)
        mmr_out_eastimated = True
    
    columns = st.columns(2)
    with columns[0]:
        st.metric(
            "MMR at match end",
            value  = int(mmr_out),
            delta = f"{int(mmr_out - mmr_in)} vs match start",
            help = "MMR eastimated" if mmr_out_eastimated else None,
        )
    kills, deaths = get_KD(selection, split = True)
    kd = round(kills/max(deaths, 1), 2)
    with columns[1]:
        st.metric(
            "Match K / D",
            value = f"{kills} / {deaths}",
        )

    # endscreen
    for team, subset in selection.groupby("teamno"):
        # style team display
        team_description = f"Team #{team+1} (MMR {subset.mmr_team.unique()[0]})"
        if subset.ownteam.sum() > 1:
            team_description += " - your Team"
        st.caption(team_description)
        subset = simplify_scoreboard(subset)
        st.dataframe(
            subset.style.applymap(
                lambda x: f"color: {'green' if x > 0 else 'grey'}",
            subset = ["shotbyme", "shotbyteammate"]
            ).applymap(
                lambda x: f"color: {'red' if x > 0 else 'grey'}",
                subset = ["shotme", "shotteammate"]
            ).applymap(
                lambda x: f"color: {'blue' if x > 0 else 'grey'}",
                subset = ["bountyextracted"]
            )
        )
