def simplify_scoreboard(data):   
    data["shotbyme"] = data[["downedbyme", "killedbyme"]].sum(axis=1)
    data["shotme"] = data[["downedme", "killedme",]].sum(axis=1)
    data["shotbyteammate"] = data[["downedbyteammate", "killedbyteammate"]].sum(axis=1)
    data["shotteammate"] = data[["downedteammate", "killedteammate"]].sum(axis=1)
    data = data.reset_index(drop=True)[[
        "blood_line_name",
        "mmr",
        "isinvite",
        "hadbounty",
        "bountyextracted",
        "shotbyme",
        "shotme",
        "shotbyteammate",
        "shotteammate",
    ]]
    return data


def get_own_team(df):
    return df.loc[df["ownteam"]]

def get_me(matches):
    solo = matches.loc[matches["ownteam"] & (matches["numplayers"] == 1)]
    me = solo.profileid.unique()[0]
    df = matches.loc[matches.profileid == me]
    return df

def get_n_last_matches(df, n):
    return df.loc[df["matchno"] >= df["matchno"].max() - n]

def get_up_to_n_last_matches(df, n):
    return df.loc[df["matchno"] < df["matchno"].max() - n]
