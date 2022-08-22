import xmltodict
from itertools import product
import pandas as pd
from glob import glob


def parse_xml(xml):
    data = xmltodict.parse(xml)
    kw = "MissionBag"
    data = {x["@name"].replace(kw, ""): x["@value"] for x in data["Attributes"]["Attr"] if kw in x["@name"]}
    # extract player data
    players = pd.DataFrame()
    for team, player in product(range(20), range(5)):
        pdata = {"_".join(x.split("_")[3::]): [data[x]] for x in data.keys() if f"Player_{team}_{player}" in x}
        if len(pdata) != 0:
            pdata["teamno"] = team
            pdata["playerno"] = player
            players = pd.concat([players, pd.DataFrame.from_dict(pdata)])
    players = players.set_index(["teamno", "playerno"])
    # extract team data
    teams = pd.DataFrame()
    for team in range(20):
        tdata = {"_".join(x.split("_")[2::]): [data[x]] for x in data.keys() if f"Team_{team}" in x}
        if len(tdata) != 0:
            tdata["teamno"] = team
            teams = pd.concat([teams, pd.DataFrame.from_dict(tdata)])
    teams = teams.set_index("teamno")
    
    return players


def sanity_check(data):
    data = data.reset_index()
    # counting players
    assert data["profileid"].nunique() <= 12, "Too many players."
    assert all(data.groupby("profileid")["teamno"].nunique() == 1), "Same player in multiple teams."
    assert all(data.groupby("teamno")["playerno"].nunique() == data.groupby("teamno")["profileid"].nunique()), "Player-indicies don't match team size."
    largest_teamsize = data.groupby("teamno")["profileid"].nunique().max()
    assert largest_teamsize <= 3, "Team too large."
    #assert data["ispartner"].dropna().apply(string_to_bool).sum() <= largest_teamsize, "Too many teammates."
    # couting bounties
    assert data["bountyextracted"].dropna().astype(int).sum() <= 4, "Too many extracted bounties."


def string_to_bool(string: str) -> bool:
    match(string.casefold()):
        case 'true':
            return True
        case 'false':
            return False



matches = pd.DataFrame()
files = sorted([filepath for filepath in glob("./data/*.xml")])
matchno = 0
for i in range(len(files) - 1):
    path0 = files[0]
    with open(path0, "r", errors="ignore") as infile:
        file0 = infile.readlines()
    path1 = files[1]
    with open(files[i + 1], "r", errors="ignore") as infile:
        file1 = infile.readlines()

    # construct new xml form changes between files
    lines = [l1 for l0, l1 in zip(file0, file1) if l0 != l1]
    xml = "".join(lines)
    xml = f'<Attributes Version="37">\n{xml}</Attributes>\n'
    try:
        data = parse_xml(xml)
        sanity_check(data)
    except Exception as e:
        print(f"Could not parse match info from diff of files {path0} & {path1}: {e}")
    else:
        data["matchno"] = matchno
        matchno += 1
        data = data.reset_index()
        matches = pd.concat([matches, data])
else:
    matches = matches.set_index(["matchno", "teamno", "playerno"])
