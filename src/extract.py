import xmltodict
import pandas as pd
import hashlib
from glob import glob
from datetime import datetime
import os
from watcher import TIMESTAMP_FORMAT, BACKUP_DIR


RESULT_DIR = os.path.join("data", "processed")


def main():
    matches = pd.DataFrame()
    files = sorted([filepath for filepath in glob(os.path.join(BACKUP_DIR, "*.xml"))])
    match_history = set()
    for i, path in enumerate(files):
        yield (i/len(files), path)
        with open(path, "r", errors="ignore", encoding="utf-8") as infile:
            xml = infile.read()
        try:
            data = parse_xml(xml)
            match_hash = create_match_hash(data)
            if match_hash in match_history:
                continue
            sanity_check(data)
        except Exception as e:
            print(f"Could not parse match info from file {path}: {e}")
        else:
            matchno = len(match_history)
            data["matchno"] = matchno
            match_history.add(match_hash)
            # read timestamp from filename
            timestamp = os.path.splitext(os.path.basename(path))[0].split("_")[-1]
            data["datetime_match_ended"] = datetime.strptime(timestamp, TIMESTAMP_FORMAT)
            matches = pd.concat([matches, data.reset_index()], ignore_index=True)
            print(f"Successfully extracted matchdata from file: {path}")
    # finish and save
    matches = matches.set_index(["matchno", "teamno", "playerno"])
    matches.to_parquet(os.path.join(RESULT_DIR, "matches.pq"))

def parse_xml(xml):
    data = xmltodict.parse(xml)
    # cleanup names and transform to usable dict
    data = {x["@name"]: x["@value"] for x in data["Attributes"]["Attr"]}
    assert not string_to_bool(data["MissionBagIsQuickPlay"]), "Skipping quickplay match."
    match = get_match_data(data)
    match["survival"] = check_survival(data)
    return match

def get_match_data(data):
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


def create_match_hash(data):
    return hashlib.sha256(pd.util.hash_pandas_object(data, index=True).values).hexdigest()


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


def check_survival(data):
    return not string_to_bool(data["MissionBagIsHunterDead"])

def get_accolades(data):
    accolades = pd.DataFrame()
    for a in range(int(data["MissionBagNumAccolades"])):
        adata = {"_".join(x.split("_")[2::]): data[x] for x in data.keys() if f"MissionAccoladeEntry_{a}" in x}
        adata = pd.DataFrame.from_dict({key: [adata[key]] for key in adata.keys()})
        adata["entry"] = f"Accolade #{a}"
        accolades = pd.concat([accolades, adata], ignore_index=True)
    del accolades[""]
    del accolades["iconPath"]
    del accolades["header"]
    # bagentries = pd.DataFrame()
    # for b in range(int(data["MissionBagNumEntries"])):
    #     bdata = {"_".join(x.split("_")[2::]): data[x] for x in data.keys() if f"MissionBagEntry_{a}" in x}
    #     bdata = pd.DataFrame.from_dict({key: [bdata[key]] for key in bdata.keys()})
    #     bdata["entry"] = f"BagEntry #{b}"
    #     bagentries = pd.concat([bagentries, bdata], ignore_index=True)
    # return pd.concat([accolades, bagentries])
    return accolades


if __name__ == "__main__":
    [print(path) for _, path in main()]
