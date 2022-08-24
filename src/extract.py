import xmltodict
import pandas as pd
from glob import glob
from datetime import datetime
import os
from watcher import TIMESTAMP_FORMAT


def main():
    matches = pd.DataFrame()
    files = sorted([filepath for filepath in glob("./data/raw/*.xml")])
    matchno = 0
    for i, path in enumerate(files):
        yield (i/len(files), path)
        with open(path, "r", errors="ignore") as infile:
            xml = infile.read()
        try:
            data = parse_xml(xml)
            sanity_check(data)
        except Exception as e:
            print(f"Could not parse match info from file {path}: {e}")
        else:
            data["matchno"] = matchno
            matchno += 1
            # read timestamp from filename
            timestamp = os.path.splitext(os.path.basename(path))[0].split("_")[-1]
            data["datetime_match_ended"] = datetime.strptime(timestamp, TIMESTAMP_FORMAT)
            matches = pd.concat([matches, data.reset_index()], ignore_index=True)
    # drop duplicates
    matches = matches.drop_duplicates(subset=matches.columns.difference(["matchno", "datetime_match_ended"]))
    matches["matchno"] = matches["matchno"].factorize()[0]
    # finish and save
    matches = matches.set_index(["matchno", "teamno", "playerno"])
    matches.to_parquet("data/processed/matches.pq")

def parse_xml(xml):
    data = xmltodict.parse(xml)
    # cleanup names and transform to usable dict
    data = {x["@name"]: x["@value"] for x in data["Attributes"]["Attr"]}
    match = get_matche_data(data)
    return match

def get_matche_data(data):
    kw = "MissionBag"
    data = {x.replace(kw, ""): data[x] for x in data.keys() if kw in x}
    teams = get_teams_data(data)
    players = get_players_data(data, teams)
    match = players.join(teams, rsuffix="_team")
    return match

def get_teams_data(data):
    n_teams = int(data["NumTeams"])
    teams = pd.DataFrame()
    for team in range(n_teams):
        tdata = {"_".join(x.split("_")[2::]): data[x] for x in data.keys() if f"Team_{team}" in x}
        if tdata[""] == "1":
            del tdata[""] # will be needed anymore
            tdata["teamno"] = team
            # transform values to lists of length one to ease creating pandas from dict
            tdata = pd.DataFrame.from_dict({key: [tdata[key]] for key in tdata.keys()})
            teams = pd.concat([teams, pd.DataFrame.from_dict(tdata)])
    teams = teams.set_index("teamno")
    # dtype conversions
    teams["mmr"] = teams["mmr"].astype(int)
    teams["handicap"] = teams["handicap"].astype(int)
    teams["numplayers"] = teams["numplayers"].astype(int)
    teams["ownteam"] = teams["ownteam"].apply(string_to_bool)
    teams["isinvite"] = teams["isinvite"].apply(string_to_bool)
    return teams

def get_players_data(data, teams):
    players = pd.DataFrame()
    for team, subset in teams.groupby("teamno"):
        for player in range(subset["numplayers"].unique()[0]):
            pdata = {"_".join(x.split("_")[3::]): data[x] for x in data.keys() if f"Player_{team}_{player}" in x}
            if len(pdata) != 0:
                pdata["teamno"] = team
                pdata["playerno"] = player
                # transform values to lists of length one to ease creating pandas from dict
                pdata = pd.DataFrame.from_dict({key: [pdata[key]] for key in pdata.keys()})
                players = pd.concat([players, pdata], ignore_index=True)
    # dtype conversions
    players["bountyextracted"] = players["bountyextracted"].astype(int)
    players["bountypickedup"] = players["bountypickedup"].astype(int)
    players["downedbyme"] = players["downedbyme"].astype(int)
    players["downedbyteammate"] = players["downedbyteammate"].astype(int)
    players["downedme"] = players["downedme"].astype(int)
    players["downedteammate"] = players["downedteammate"].astype(int)
    players["killedbyme"] = players["killedbyme"].astype(int)
    players["killedbyteammate"] = players["killedbyteammate"].astype(int)
    players["killedme"] = players["killedme"].astype(int)
    players["killedteammate"] = players["killedteammate"].astype(int)
    players["mmr"] = players["mmr"].astype(int)
    players["hadWellspring"] = players["hadWellspring"].apply(string_to_bool)
    players["hadbounty"] = players["hadbounty"].apply(string_to_bool)
    players["ispartner"] = players["ispartner"].apply(string_to_bool)
    players["issoulsurvivor"] = players["issoulsurvivor"].apply(string_to_bool)
    players["proximity"] = players["proximity"].apply(string_to_bool)
    players["proximitytome"] = players["proximitytome"].apply(string_to_bool)
    players["proximitytoteammate"] = players["proximitytoteammate"].apply(string_to_bool)
    players["skillbased"] = players["skillbased"].apply(string_to_bool)
    players["teamextraction"] = players["teamextraction"].apply(string_to_bool)
    # join team metatadata
    players = players.set_index(["teamno", "playerno"])
    return players


def sanity_check(data):
    data = data.reset_index()
    # counting players
    assert data["profileid"].nunique() <= 12, "Too many players."
    assert all(data.groupby("profileid")["teamno"].nunique() == 1), "Same player in multiple teams."
    assert all(data.groupby("teamno")["playerno"].nunique() == data.groupby("teamno")["profileid"].nunique()), "Player-indicies don't match team size."
    largest_teamsize = data.groupby("teamno")["profileid"].nunique().max()
    assert largest_teamsize <= 3, "Team too large."
    assert data["ispartner"].sum() <= largest_teamsize, "Too many teammates."
    # couting bounties
    assert data["bountyextracted"].dropna().astype(int).sum() <= 4, "Too many extracted bounties."


def string_to_bool(string: str) -> bool:
    match(string.casefold()):
        case 'true':
            return True
        case 'false':
            return False


if __name__ == "__main__":
    main()