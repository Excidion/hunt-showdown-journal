import streamlit as st
import pandas as pd
from datetime import datetime
import os
from watcher import FileBackupper
from extract import main as parse_matchfiles
from extract import parse_xml
from plots import plot_mmr_hisotry, display_KD, display_mmr, display_extraction_rate
from dotenv import load_dotenv
from glob import glob
from match_utils import find_my_id, simplify_scoreboard, construct_match_name

load_dotenv()

st.session_state["watched_file"] = os.getenv("watched_file") or "C:/Programs/Steam/steamapps/common/Hunt Showdown/user/profiles/default/attributes.xml"


def start_watcher_process():
    thread = st.session_state.get("watcher_process")
    if thread is not None:
        st.warning("Match Recorder already running.")
    else:
        thread = FileBackupper(st.session_state.get("watched_file"), "./data/raw")
        thread.start()
        st.session_state["watcher_process"] = thread
        st.success("Match Recorder started.")

def stop_watcher_process():
    thread = st.session_state.get("watcher_process")
    if thread is None:
        st.warning("Match Recorder already stopped.")
    else:
        thread.stop()
        st.session_state["watcher_process"] = None
        st.success("Match Recorder stopped.")


st.title("Hunt Journal")
tracked_file_is_setup = os.path.exists(st.session_state.get("watched_file"))
process_alive = st.session_state.get("watcher_process") is not None
col0, col1 = st.columns(2)
with col0:
    # start game
    start_game = st.button("Play Hunt: Showdown!")
    also_start_filewatcher = st.checkbox(
        label = "Start Match Recorder with Game", 
        value = True,
        disabled = not tracked_file_is_setup,
        help = "Can only be used if matchfile is tracked."
    )
    if start_game:
        st.info("Game starting...")
        os.system("start steam://rungameid/594650")
        if also_start_filewatcher:
            start_watcher_process()
with col1:
    # start watcher proces by hand
    if st.button("Start Match Recorder", disabled = not tracked_file_is_setup):
        start_watcher_process()
    # kill watcher process
    if st.button("Stop Match Recorder", disabled = not tracked_file_is_setup):
        stop_watcher_process()
    

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
        value = st.session_state.get("watched_file"),
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
        st.session_state["watched_file"] = filepath
    st.info(f"Backup Location: `{os.path.join(os.getcwd(), 'data', 'raw')}`")


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


RESULTFILE = "data/processed/matches.pq"
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
    columns = st.columns(4)
    with columns[0]:
        display_mmr(matches, trend_window)
    with columns[1]:
        display_KD(matches, trend_window)
    with columns[2]:
        display_extraction_rate(matches, trend_window)

    # MMR history
    st.subheader("MMR History")
    xaxis = st.radio(
        "X-Axis",
        ["Time", "# of Match"],
        help = "The MMR displayed is the one at match start."
    )
    xaxis = "datetime_match_ended" if xaxis == "Time" else "matchno"
    fig = plot_mmr_hisotry(matches, xaxis)
    st.plotly_chart(fig)


    st.header("Individual Match Statistics")
    # match table
    my_id = find_my_id(matches)
    match_display_names = {f"{matchno+1}: {construct_match_name(subset, my_id)}": matchno for matchno, subset in matches.groupby("matchno")}
    selected_match = st.selectbox(
        label = "Select a Match",
        options = reversed(match_display_names.keys()),
    )
    selection = matches.loc[matches["matchno"] == match_display_names[selected_match]]
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
