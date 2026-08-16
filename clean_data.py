# %% Setup
import pandas as pd

matches = pd.read_csv("data/matches.csv", parse_dates=["date"])
deliveries = pd.read_csv("data/deliveries.csv")

print("raw:", matches.shape, deliveries.shape)

# %% 1. Standardise season labels to a single year (verified against actual dates)
season_map = {"2007/08": 2008, "2009/10": 2010, "2020/21": 2020}
matches["season"] = (
    matches["season"].replace(season_map).astype(int)
)
print(sorted(matches["season"].unique()))

# %% 2. Merge renamed franchises: 19 names -> 15
team_map = {
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
    "Rising Pune Supergiants": "Rising Pune Supergiant",
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
}

for col in ["team1", "team2", "toss_winner", "winner"]:
    matches[col] = matches[col].replace(team_map)

for col in ["batting_team", "bowling_team"]:
    deliveries[col] = deliveries[col].replace(team_map)

print("distinct teams now:",
      len(set(matches["team1"]) | set(matches["team2"])))

# %% 2b. Standardise venue names: 58 labels -> ~40 actual grounds
# Three separate problems: inconsistent city suffixes, punctuation variants,
# and genuine stadium renames (Feroz Shah Kotla -> Arun Jaitley, 2019).
venue_map = {
    "Eden Gardens, Kolkata": "Eden Gardens",
    "Wankhede Stadium, Mumbai": "Wankhede Stadium",
    "M.Chinnaswamy Stadium": "M Chinnaswamy Stadium",
    "M Chinnaswamy Stadium, Bengaluru": "M Chinnaswamy Stadium",
    "MA Chidambaram Stadium, Chepauk": "MA Chidambaram Stadium",
    "MA Chidambaram Stadium, Chepauk, Chennai": "MA Chidambaram Stadium",
    "Rajiv Gandhi International Stadium, Uppal": "Rajiv Gandhi International Stadium",
    "Rajiv Gandhi International Stadium, Uppal, Hyderabad": "Rajiv Gandhi International Stadium",
    "Sawai Mansingh Stadium, Jaipur": "Sawai Mansingh Stadium",
    # Renamed in 2019 - same ground
    "Feroz Shah Kotla": "Arun Jaitley Stadium",
    "Arun Jaitley Stadium, Delhi": "Arun Jaitley Stadium",
    "Punjab Cricket Association Stadium, Mohali": "PCA IS Bindra Stadium",
    "Punjab Cricket Association IS Bindra Stadium": "PCA IS Bindra Stadium",
    "Punjab Cricket Association IS Bindra Stadium, Mohali": "PCA IS Bindra Stadium",
    "Punjab Cricket Association IS Bindra Stadium, Mohali, Chandigarh": "PCA IS Bindra Stadium",
    "Dr DY Patil Sports Academy, Mumbai": "Dr DY Patil Sports Academy",
    # Renamed - same ground in Pune
    "Subrata Roy Sahara Stadium": "Maharashtra Cricket Association Stadium",
    "Maharashtra Cricket Association Stadium, Pune": "Maharashtra Cricket Association Stadium",
    "Brabourne Stadium, Mumbai": "Brabourne Stadium",
    "Zayed Cricket Stadium, Abu Dhabi": "Sheikh Zayed Stadium",
    # Demolished and rebuilt on the same site, reopened 2021
    "Sardar Patel Stadium, Motera": "Narendra Modi Stadium",
    "Narendra Modi Stadium, Ahmedabad": "Narendra Modi Stadium",
    "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow": "Ekana Cricket Stadium",
    "Himachal Pradesh Cricket Association Stadium, Dharamsala": "Himachal Pradesh Cricket Association Stadium",
    "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium, Visakhapatnam": "ACA-VDCA Cricket Stadium",
    "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium": "ACA-VDCA Cricket Stadium",
    "Vidarbha Cricket Association Stadium, Jamtha": "Vidarbha Cricket Association Stadium",
    "Barsapara Cricket Stadium, Guwahati": "Barsapara Cricket Stadium",
    "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur": "Maharaja Yadavindra Singh Stadium",
}

print("venues before:", matches["venue"].nunique())
matches["venue"] = matches["venue"].replace(venue_map)
print("venues after :", matches["venue"].nunique())
print(matches["venue"].value_counts().head(10))

# %% 3. Convert over to 1-indexed and tag match phase
# Source data is 0-indexed (0-19). Shift to 1-20 so it reads like cricket does.
deliveries["over_no"] = deliveries["over"] + 1

def phase(over_no):
    if over_no <= 6:
        return "Powerplay"
    elif over_no <= 15:
        return "Middle"
    return "Death"

deliveries["phase"] = deliveries["over_no"].apply(phase)
print(deliveries["phase"].value_counts())

# %% 4. Flag legal deliveries (wides and no-balls are NOT balls faced/bowled)
deliveries["is_legal_ball"] = (
    ~deliveries["extras_type"].isin(["wides", "noballs"])
).astype(int)

print("total rows :", len(deliveries))
print("legal balls:", deliveries["is_legal_ball"].sum())
print("illegal    :", (1 - deliveries["is_legal_ball"]).sum())

# %% 5. Flag batter-credited dismissals (run-outs are not the bowler's wicket)
bowler_wickets = ["bowled", "caught", "lbw", "stumped", "caught and bowled",
                  "hit wicket"]
deliveries["is_bowler_wicket"] = (
    deliveries["dismissal_kind"].isin(bowler_wickets)
).astype(int)

print(deliveries["dismissal_kind"].value_counts(dropna=False).head(12))
print("\ntotal wickets       :", deliveries["is_wicket"].sum())
print("credited to bowler  :", deliveries["is_bowler_wicket"].sum())

# %% 6. Sanity checks before export
assert deliveries["match_id"].nunique() == matches["id"].nunique(), "join broken"
assert deliveries["over_no"].between(1, 20).all(), "over out of range"
print("matches   :", matches.shape)
print("deliveries:", deliveries.shape)

# %% 7. Export cleaned files
matches.to_csv("data/cleaned_matches.csv", index=False)
deliveries.to_csv("data/cleaned_deliveries.csv", index=False)
print("saved cleaned_matches.csv and cleaned_deliveries.csv")
