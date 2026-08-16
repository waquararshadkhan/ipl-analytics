# %% Setup
import pandas as pd

matches = pd.read_csv("data/matches.csv")
deliveries = pd.read_csv("data/deliveries.csv")

# %% 1. Standard profile of both files
for name, df in [("matches", matches), ("deliveries", deliveries)]:
    print("=" * 60)
    print(f"DATASET: {name}   shape={df.shape}")
    print("=" * 60)
    print("\nColumns:\n", list(df.columns))
    print("\nDtypes:\n", df.dtypes)
    print("\nMissing values (only columns with nulls):")
    nulls = df.isnull().sum()
    print(nulls[nulls > 0] if nulls.sum() else "  none")
    print("\nDuplicate rows:", df.duplicated().sum())
    print("\nHead:\n", df.head(3))
    print()

# %% 2. Team name consistency — the classic IPL data problem
teams = sorted(set(matches["team1"].dropna()) | set(matches["team2"].dropna()))
print(f"Distinct team names: {len(teams)}")
for t in teams:
    print("  ", t)

# %% 3. Season coverage
season_col = "season" if "season" in matches.columns else "year"
print(matches[season_col].value_counts().sort_index())

# %% 4. Can the two tables be joined?
mid = "id" if "id" in matches.columns else matches.columns[0]
print("matches key column:", mid)
print("matches: unique ids      =", matches[mid].nunique())
print("deliveries: unique match_id =", deliveries["match_id"].nunique())
print("in deliveries not matches =", len(set(deliveries["match_id"]) - set(matches[mid])))
print("in matches not deliveries =", len(set(matches[mid]) - set(deliveries["match_id"])))

# %% 5. Grain check — what does one deliveries row mean?
print(deliveries.head(8)[["match_id", "inning", "over", "ball", "batter",
                          "bowler", "batsman_runs", "total_runs"]])
print("\nballs per match (avg):", round(len(deliveries) / deliveries['match_id'].nunique(), 1))
