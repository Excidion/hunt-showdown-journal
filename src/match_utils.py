from datetime import datetime
from sklearn.linear_model import LinearRegression
import pandas as pd


MMR_BRACKETS = { # upper boundaries
    0: 0,
    1: 2000,
    2: 2300,
    3: 2600,
    4: 2750,
    5: 3000,
    6: 5000,
}


def get_mmr_bracket(mmr):
    for bracket in sorted(MMR_BRACKETS.keys()):
        if MMR_BRACKETS[bracket] > mmr:
            return bracket

def construct_match_name(subset, my_id=""):
    teammates = subset[subset.ownteam & (subset.profileid != my_id)]
    return " ".join([
        {
            1: "Quickplay",
            2: "Duos",
            3: "Trios",
        }[subset.numplayers.max()],
        "on",
        datetime.ctime(subset.datetime_match_ended.iloc[0]),
        ("with " + " & ".join(teammates.blood_line_name) if subset.ownteam.sum() > 1 else "")
    ])


def simplify_scoreboard(data):   
    data["shotbyme"] = data[["downedbyme", "killedbyme"]].sum(axis=1)
    data["shotme"] = data[["downedme", "killedme",]].sum(axis=1)
    data["shotbyteammate"] = data[["downedbyteammate", "killedbyteammate"]].sum(axis=1)
    data["shotteammate"] = data[["downedteammate", "killedteammate"]].sum(axis=1)
    data = data.reset_index(drop=True)[[
        "blood_line_name",
        "mmr",
        "bountyextracted",
        "shotbyme",
        "shotme",
        "shotbyteammate",
        "shotteammate",
    ]]
    return data


def get_own_team(df):
    return df.loc[df["ownteam"]]

def get_my_matches(matches):
    my_id = find_my_id(matches)
    df = matches.loc[matches.profileid == my_id]
    return df

def find_my_id(matches):
    for func in [find_my_id_by_flags, find_my_id_from_solo_matches, find_my_id_by_most_frequnt_player]:
        try:
            return func(matches)
        except Exception as e:
            print(f"Error with {func.__name__}: {e}")
    else: # if by now no heuristic has found a defintive id
        raise ValueError("Could not unambiguously determine your ID. Playing a solo match will fix this.")

def find_my_id_by_flags(matches):
    my_team_and_not_partner = matches.loc[matches["ownteam"] & (~matches["ispartner"])]
    return get_unique_id(my_team_and_not_partner)

def find_my_id_from_solo_matches(matches):
    solo = matches.loc[matches["ownteam"] & (matches["numplayers"] == 1)]
    assert len(solo) > 1, "No solo matches found."
    return get_unique_id(solo)

def get_unique_id(df):
    ids =  df.profileid.unique()
    assert len(ids) == 1, "Ambiguous profileid."
    return ids[0]

def find_my_id_by_most_frequnt_player(matches):
    player_frequency = matches.groupby("profileid").size()
    most_frequent_players = player_frequency.loc[player_frequency == player_frequency.max()]
    assert len(most_frequent_players) == 1, "Most frequent player is ambiguous."
    return most_frequent_players.index[0]

def get_n_last_matches(df, n):
    return df.loc[df["matchno"] >= df["matchno"].max() - n]

def get_up_to_n_last_matches(df, n):
    return df.loc[df["matchno"] <= df["matchno"].max() - n]

def get_profileid_map(matches):
    return matches.groupby("profileid")["blood_line_name"].last().to_dict()


def predict_mmr(matches, method="elo"):
    match method:
        case "elo":
            return predict_mmr_elo(matches)
        case "linreg":
            return predict_mmr_linreg(matches)
        case _:
            raise ValueError(f"Unknown method: {method}")

def predict_mmr_linreg(matches):
    matches = matches.set_index("matchno")
    mine = get_my_matches(matches)
    mmr_in = mine["mmr"]
    mmr_in.name = "mmr_in"
    mmr_out = mine["mmr"].shift(-1)
    mmr_out.name = "mmr_out"
    # unite downed and killed
    matches["shotbyme"] = matches[["downedbyme", "killedbyme"]].sum(axis=1)
    matches["shotme"] = matches[["downedme", "killedme",]].sum(axis=1)
    # mmr of people shot  relative to own
    shotbyme = matches.loc[matches["shotbyme"]>0]
    shotbyme = shotbyme.join(mmr_in, rsuffix="_in")
    shotbyme = (shotbyme["mmr"] / shotbyme["mmr_in"]) * shotbyme["shotbyme"]
    shotbyme = shotbyme.groupby("matchno").sum()
    shotbyme.name = "shotbyme"
    # mmr of people shooting me relative to own
    shotme = matches.loc[matches["shotme"]>0]
    shotme = shotme.join(mmr_in, rsuffix="_in")
    shotme = (shotme["mmr"] / shotme["mmr_in"]) * shotme["shotme"]
    shotme = shotme.groupby("matchno").sum()
    shotme.name = "shotme"
    # extractions
    own = get_own_team(matches)
    bounty = (own.groupby("matchno")["bountyextracted"].sum() > 0).astype(int)
    bounty.name = "bounties_extracted"
    # join and fillna
    data = pd.concat([mmr_out, mmr_in, shotbyme, shotme, bounty], axis=1).fillna(0)
    data = data.loc[data["mmr_in"] != 0]
    new_data = data.loc[data["mmr_out"] == 0] # for later prediction
    data = data.loc[data["mmr_out"] != 0]
    # make model
    y = data["mmr_out"] - data["mmr_in"]
    X = data[data.columns.difference(["mmr_out", "mmr_in"])]
    model = LinearRegression(fit_intercept=False)
    model.fit(X,y)
    newest_match = (model.predict(new_data[data.columns.difference(["mmr_out", "mmr_in"])]) + new_data["mmr_in"]).astype(int)
    return newest_match.values[0]

def predict_mmr_elo(matches):
    last_match_nr = matches["matchno"].max()
    matches = matches.set_index("matchno")
    mine = get_my_matches(matches)
    mmr = mine.loc[last_match_nr, "mmr"]
    lastmatch = matches.loc[last_match_nr]
    # unite downed and killed
    lastmatch["shotbyme"] = lastmatch[["downedbyme", "killedbyme"]].sum(axis=1)
    lastmatch["shotme"] = lastmatch[["downedme", "killedme",]].sum(axis=1)
    change = 0
    for _, row in lastmatch.groupby("profileid"):
        kills = update_elo_scores(mmr, row["mmr"], 1, return_updated=False) * row["shotbyme"]
        deaths = update_elo_scores(mmr, row["mmr"], 0, return_updated=False) * row["shotme"]
        change += kills + deaths
    return int(mmr + change)

def update_elo_scores(p1, p2, result=1, k=32, return_updated=True):
    assert (result >= 0) and (result <= 1) # 1: p1 wins, 0: p2 wins
    expected = 1 / (1 + 10**((p2 - p1) / 400))
    adjust = k * (result - expected)
    adjust = round(adjust) # ensure integers
    if return_updated:
        p1 += adjust
        p2 -= adjust
        return p1, p2
    else:
        return adjust # sign always in relation to p1