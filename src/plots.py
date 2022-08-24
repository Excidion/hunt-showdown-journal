from plotly import express as px
import plotly.graph_objects as go
import pandas as pd


def plot_mmr_hisotry(matches, xaxis):
     # mmr history
    solo = matches.loc[matches["ownteam"] & (matches["numplayers"] == 1)]
    me = solo.profileid.unique()[0]
    df = matches.loc[matches.profileid == me]
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
