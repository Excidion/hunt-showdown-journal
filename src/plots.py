from plotly import express as px
import plotly.graph_objects as go
import pandas as pd
from matplotlib import pyplot as plt
from match_utils import simplify_scoreboard, get_my_matches, get_own_team, get_up_to_n_last_matches, get_profileid_map, predict_mmr
import streamlit as st
import statsmodels.api as sm
import numpy as np


def display_mmr(df, trend_window=3):
    mmr = predict_mmr(df)
    mmr_old = get_my_matches(df)["mmr"].iloc[-(trend_window-1)]
    st.metric(
        "MMR",
        f"~{mmr}",
        f"{mmr - mmr_old} in last {trend_window} matches",
        help = "The data only contains the MMR before a match start. But based on your last match, your current MMR can be eastimated."
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

def get_KD(df, split=False):
    df = simplify_scoreboard(df)
    killed = df["shotbyme"].sum()
    died = max(df["shotme"].sum(), 1) # treat zero deaths as one to avoid dividing by zero
    if split:
        return killed, died
    else:
        return killed / died


def plot_mmr_hisotry(matches, xaxis, mmr_out=False):
    df = get_my_matches(matches)
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
    # show mmr at match start or at match end
    if mmr_out:
        df["mmr"] = df["mmr"].shift(-1)
        df["mmr"].iloc[-1] = predict_mmr(matches)
    mmr = px.scatter(
        df, 
        x = xaxis, 
        y = "mmr", 
        symbol="numplayers",
        symbol_map={1:"circle", 2:"diamond-wide", 3:"star-triangle-up"},
        color_discrete_sequence=["white"],
        hover_name = xaxis, 
        hover_data = ["mmr"],
    )
    mmr_lines = px.line(
        df, 
        x = xaxis, 
        y = "mmr", 
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
    fig = go.Figure(data = mmr_brackets.data + mmr_lines.data + mmr.data)
    fig.update_yaxes(range=[df.mmr.min()*0.99, df.mmr.max()*1.01], autorange=False)
    fig.update_layout(showlegend = False)
    return fig


def effect_on_extraction_chance(matches):
    style_pyplot()
    own = matches.loc[matches["ownteam"]].set_index("matchno")
    y = own.groupby("matchno")["bountyextracted"].max() >= 1
    X = pd.get_dummies(own["profileid"]).groupby("matchno").sum()
    model = sm.Logit(y,X)
    try:
        results = model.fit()
    except Exception as e:
        st.error(f"Error performing analysis: {e}")
        return plt.gcf() 
    plt.barh(
        results.params.index,
        results.params,
        color = ["green" if v>=0 else "red" for v in results.params],
        label = "effect"
    )
    conf_int = results.conf_int()
    plt.errorbar(
        y=results.params.index,
        x=results.params,
        fmt='o',
        capsize=5,
        xerr=((results.params-conf_int[0]).abs(), conf_int[1]-results.params),
        color = "white",
        label = "uncertainty",
    )
    plt.legend()
    plt.xlabel("Odds of extracting with a bounty")
    xticks = plt.gca().get_xticks()
    plt.xticks(xticks, [f"{round(v)}:1" if v >=1 else f"1:{round(1/v)}" for v in np.exp(xticks)])
    id_map = get_profileid_map(matches)
    plt.yticks(plt.gca().get_yticks(), [id_map.get(i) for i in results.params.index])
    return plt.gcf()

def style_pyplot():
    plt.style.use("dark_background")
    fig = plt.gcf()
    fig.patch.set_facecolor('b')
    fig.patch.set_alpha(0)
    ax = plt.gca()
    ax.patch.set_facecolor('b')
    ax.patch.set_alpha(0)
    