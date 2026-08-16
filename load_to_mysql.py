# %% Setup
import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.types import Integer, String, Date, Float

matches = pd.read_csv("data/cleaned_matches.csv", parse_dates=["date"])
deliveries = pd.read_csv("data/cleaned_deliveries.csv")

engine = create_engine(
    f"mysql+pymysql://root:{os.environ['MYSQL_PWD']}@localhost:3306/ipl_analytics"
)
print("engine created")

# %% 1. Explicit column types
# Without this, pandas maps every text column to TEXT, which MySQL cannot
# index without a prefix length. VARCHAR is indexable and much faster.
matches_dtype = {
    "id": Integer(), "season": Integer(), "city": String(50),
    "date": Date(), "match_type": String(20), "player_of_match": String(60),
    "venue": String(120), "team1": String(60), "team2": String(60),
    "toss_winner": String(60), "toss_decision": String(10),
    "winner": String(60), "result": String(20), "result_margin": Float(),
    "target_runs": Float(), "target_overs": Float(), "super_over": String(5),
    "method": String(10), "umpire1": String(60), "umpire2": String(60),
}

deliveries_dtype = {
    "match_id": Integer(), "inning": Integer(),
    "batting_team": String(60), "bowling_team": String(60),
    "over": Integer(), "ball": Integer(),
    "batter": String(60), "bowler": String(60), "non_striker": String(60),
    "batsman_runs": Integer(), "extra_runs": Integer(), "total_runs": Integer(),
    "extras_type": String(20), "is_wicket": Integer(),
    "player_dismissed": String(60), "dismissal_kind": String(30),
    "fielder": String(60), "over_no": Integer(), "phase": String(15),
    "is_legal_ball": Integer(), "is_bowler_wicket": Integer(),
}

# %% 2. Load matches (small - single shot)
matches.to_sql("matches", engine, if_exists="replace", index=False,
               dtype=matches_dtype)
print("matches loaded")

# %% 3. Load deliveries in chunks (260k rows - takes a minute)
deliveries.to_sql("deliveries", engine, if_exists="replace", index=False,
                  dtype=deliveries_dtype, chunksize=10000, method="multi")
print("deliveries loaded")

# %% 4. Add indexes - without these, joins on 260k rows crawl
index_sql = [
    "CREATE INDEX idx_match_id  ON deliveries (match_id)",
    "CREATE INDEX idx_batter    ON deliveries (batter)",
    "CREATE INDEX idx_bowler    ON deliveries (bowler)",
    "CREATE INDEX idx_phase     ON deliveries (phase)",
    "ALTER TABLE matches ADD PRIMARY KEY (id)",
    "CREATE INDEX idx_season    ON matches (season)",
]

with engine.begin() as conn:
    for stmt in index_sql:
        try:
            conn.execute(text(stmt))
            print("ok  :", stmt)
        except Exception as e:
            print("skip:", stmt, "->", str(e)[:60])

# %% 5. Verify
with engine.connect() as conn:
    for t in ["matches", "deliveries"]:
        n = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        print(f"{t}: {n:,} rows")
