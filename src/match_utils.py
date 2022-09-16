from datetime import datetime


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
