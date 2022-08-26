from plotly import express as px
import plotly.graph_objects as go
import pandas as pd
from matplotlib import pyplot as plt
from match_utils import simplify_scoreboard, get_me, get_own_team, get_up_to_n_last_matches
import streamlit as st


def display_mmr(df, trend_window=3):
    df = get_me(df)
    mmr = df["mmr"].iloc[-1]
    mmr_old = df["mmr"].iloc[-trend_window]
    st.metric(
        "MMR",
        mmr,
        f"{mmr - mmr_old} in last {trend_window} matches"
    )

def display_extraction_rate(df, trend_window=3):
    df = get_own_team(df)
    df_old = get_up_to_n_last_matches(df, trend_window)
    er = get_extraction_rate(df)
    er_old = get_extraction_rate(df_old)
    st.metric(
        "Min. one bounty extracted",
        f"{round(er * 100)}%",
        f"{round((er - er_old) * 100)}% in last {trend_window} matches"
    )

def get_extraction_rate(df):
    return df.groupby("matchno")["bountyextracted"].sum().astype(bool).sum() / df["matchno"].nunique()

def display_KD(df, trend_window=3):
    kd_old = get_KD(get_up_to_n_last_matches(df, trend_window))
    kd = get_KD(df)
    st.metric(
        "K/D Ratio",
        round(kd, 2),
        f"{round(kd - kd_old, 2)} in last {trend_window} matches"
    )

def get_KD(df):
    df = simplify_scoreboard(df)
    killed = df["shotbyme"].sum()
    died = max(df["shotme"].sum(), 1) # treat zero deaths as one to avoid dividing by zero
    return killed / died


def plot_mmr_hisotry(matches, xaxis):
    df = get_me(matches)
    df["matchno"] += 1
    # star rating
    levels = pd.DataFrame()
    levels[xaxis] = df[xaxis]
    levels = levels.loc[(levels[xaxis] == levels[xaxis].min()) | (levels[xaxis] == levels[xaxis].max())]
    levels = levels.reset_index(drop=True)
    levels["0"] = 0
    levels["1"] = 2000
    levels["2"] = 2300
    levels["3"] = 2600
    levels["4"] = 2750
    levels["5"] = 3000
    levels["6"] = 5000
    levels = levels.set_index(xaxis).stack().reset_index().rename({"level_1":"Stars", 0:"mmr"}, axis=1)
    levels["delta"] = levels["mmr"].diff()
    levels.loc[levels["delta"] < 0, "delta"] = None
    mmr = px.line(
        df, 
        x=xaxis, 
        y="mmr", 
        markers=True, 
        color_discrete_sequence=["black"],
        hover_name = xaxis, 
        hover_data = ["mmr"],
    ) 
    colors = px.colors.sequential.Turbo
    mmr_brackets = px.area(
        levels, 
        x = xaxis, 
        y = "delta", 
        color = "Stars", 
        color_discrete_sequence = colors[::(len(colors)//levels["Stars"].nunique())],
        hover_name = "Stars", 
        hover_data = ["mmr"],
    )
    fig = go.Figure(data = mmr_brackets.data + mmr.data)
    fig.update_yaxes(range=[df.mmr.min()*0.99, df.mmr.max()*1.01], autorange=False)
    return fig
