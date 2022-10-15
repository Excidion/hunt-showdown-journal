from plotly import express as px
import plotly.graph_objects as go
import pandas as pd
from matplotlib import pyplot as plt
from match_utils import (
    simplify_scoreboard, 
    get_my_matches, 
    get_own_team, 
    get_up_to_n_last_matches, 
    get_profileid_map, 
    predict_mmr,
    update_elo_scores,
    get_mmr_bracket,
    MMR_BRACKETS,
)
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
    died = df["shotme"].sum()
    if split:
        return killed, died
    else:
        died = max(died, 1) # treat zero deaths as one to avoid dividing by zero
        return killed / died


def display_mmr_taken(matches):
    matches = matches.set_index("matchno")
    mine = get_my_matches(matches)["mmr"]
    mine.name = "my_mmr"
    matches = matches.join(mine)
    matches["shotbyme"] = matches[["downedbyme", "killedbyme"]].sum(axis=1)
    matches["shotme"] = matches[["downedme", "killedme",]].sum(axis=1)
    matches = matches.loc[(matches["shotbyme"] + matches["shotme"]) > 0] # skip irrelevant
    total_mmr_taken = 0
    max_mmr_taken = 0
    max_mmr_taken_victim = ""
    ranks_taken = 0
    deranked = set()
    for (matchno, profileid), row in matches.groupby(["matchno", "profileid"]):
        mmr_taken = update_elo_scores(row["my_mmr"], row["mmr"], 1, return_updated=False) * row["shotbyme"]
        mmr_taken = mmr_taken.iloc[0]
        if mmr_taken > 0:
            mmr_lost = update_elo_scores(row["my_mmr"], row["mmr"], 0, return_updated=False) * row["shotme"]
            mmr_taken += mmr_lost.iloc[0] # correct for trades (sign is negative by default)
        if mmr_taken > 0:
            total_mmr_taken += mmr_taken
            if mmr_taken > max_mmr_taken:
                max_mmr_taken = mmr_taken
                max_mmr_taken_victim = row["blood_line_name"].iloc[0] + f" (#{matchno+1})"
            rank_before = get_mmr_bracket(row["mmr"].iloc[0]) 
            rank_after = get_mmr_bracket(row["mmr"].iloc[0] - mmr_taken)
            if rank_before > rank_after:
                ranks_taken += rank_before - rank_after
                deranked.add(row["blood_line_name"].iloc[0] + f" (#{matchno+1}) {rank_before}↘{rank_after}")
 
    columns = st.columns(3)
    with columns[0]:
        st.metric(
            "MMR taken from others",
            value = int(total_mmr_taken),
            help = f"Max. -{int(max_mmr_taken)} from {max_mmr_taken_victim}",
        )
    with columns[1]:
        st.metric(
            "Ruined someones day",
            value = f"{int(ranks_taken)}×",
            help = "\n\n".join(list(deranked)),
        )


def plot_mmr_hisotry(matches, xaxis, mmr_out=False):
    df = get_my_matches(matches)
    df["matchno"] += 1
    # star rating
    levels = pd.DataFrame()
    levels[xaxis] = df[xaxis]
    levels = levels.loc[(levels[xaxis] == levels[xaxis].min()) | (levels[xaxis] == levels[xaxis].max())]
    levels = levels.reset_index(drop=True)
    for bracket in MMR_BRACKETS.keys():
        levels[str(bracket)] = MMR_BRACKETS.get(bracket)
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
        color="survival",
        color_discrete_map={False:"black", True:"white"},
        hover_name = xaxis, 
        hover_data = ["mmr"],
    )
    mmr_lines = px.line(
        df, 
        x = xaxis, 
        y = "mmr", 
        color_discrete_sequence=["darkgrey"],
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



def effect_on_success_chance(matches, target="extracting with a bounty", minimum_matches=3):
    assert minimum_matches <= matches["matchno"].nunique(), "Not enough matches recorded."
    style_pyplot()
    own = matches.loc[matches["ownteam"]].set_index("matchno")
    if target == "extracting with a bounty":
        y = own.groupby("matchno")["bountyextracted"].max() >= 1
    elif target == "surviving":
        y = own.groupby("matchno")["survival"].sum() >= 1
    X = pd.get_dummies(own["profileid"]).groupby("matchno").sum()
    matches_per_player = X.sum()
    enough_matches = matches_per_player.loc[matches_per_player >= minimum_matches]
    X = X[enough_matches.index]
    model = sm.Logit(y,X)
    try:
        results = model.fit()
    except Exception as e:
        print(f"Error performing analysis with minimum_matches={minimum_matches}: {e}")
        return effect_on_success_chance(matches, target, minimum_matches+1)
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
    plt.xlabel(f"Odds of {target}")
    xticks = plt.gca().get_xticks()
    odds = np.exp(xticks)
    if (odds == 0).any() or not np.isfinite(odds).any(): # check if any odds are not sensible
        plt.close() # delete existing plot
        return effect_on_success_chance(matches, target, minimum_matches+1)
    plt.xticks(xticks, [f"{round(o)}:1" if o >=1 else f"1:{round(1/o)}" for o in odds])
    id_map = get_profileid_map(matches)
    plt.yticks(plt.gca().get_yticks(), [id_map.get(i) for i in results.params.index])
    plt.title(f"Teammates with at least {minimum_matches} matches together")
    return plt.gcf()

def style_pyplot():
    plt.style.use("dark_background")
    fig = plt.gcf()
    fig.patch.set_facecolor('b')
    fig.patch.set_alpha(0)
    ax = plt.gca()
    ax.patch.set_facecolor('b')
    ax.patch.set_alpha(0)
    