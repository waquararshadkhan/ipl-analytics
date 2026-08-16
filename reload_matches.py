"""Reload only the matches table after the venue-name fix.

deliveries is untouched (it has no venue column), so this runs in seconds
instead of re-uploading 260k rows.
"""
import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.types import Integer, String, Date, Float

engine = create_engine(
    f"mysql+pymysql://root:{os.environ['MYSQL_PWD']}@localhost:3306/ipl_analytics"
)

matches = pd.read_csv("data/cleaned_matches.csv", parse_dates=["date"])
print("venues:", matches["venue"].nunique())

matches_dtype = {
    "id": Integer(), "season": Integer(), "city": String(50),
    "date": Date(), "match_type": String(20), "player_of_match": String(60),
    "venue": String(120), "team1": String(60), "team2": String(60),
    "toss_winner": String(60), "toss_decision": String(10),
    "winner": String(60), "result": String(20), "result_margin": Float(),
    "target_runs": Float(), "target_overs": Float(), "super_over": String(5),
    "method": String(10), "umpire1": String(60), "umpire2": String(60),
}

# The view depends on matches, so it must be dropped before the table is replaced
with engine.begin() as conn:
    conn.execute(text("DROP VIEW IF EXISTS team_results"))
    print("dropped view team_results")

matches.to_sql("matches", engine, if_exists="replace", index=False,
               dtype=matches_dtype)
print("matches reloaded")

# to_sql drops the key and indexes, so rebuild them
rebuild = [
    "ALTER TABLE matches ADD PRIMARY KEY (id)",
    "CREATE INDEX idx_season ON matches (season)",
    """CREATE VIEW team_results AS
       SELECT id AS match_id, season, venue, team1 AS team,
              CASE WHEN winner = team1 THEN 1 ELSE 0 END AS won
       FROM matches WHERE winner IS NOT NULL
       UNION ALL
       SELECT id, season, venue, team2,
              CASE WHEN winner = team2 THEN 1 ELSE 0 END
       FROM matches WHERE winner IS NOT NULL""",
]

with engine.begin() as conn:
    for stmt in rebuild:
        conn.execute(text(stmt))
        print("ok:", stmt.split("\n")[0].strip()[:60])

# Verify
with engine.connect() as conn:
    print("\nmatches rows :", conn.execute(text("SELECT COUNT(*) FROM matches")).scalar())
    print("view rows    :", conn.execute(text("SELECT COUNT(*) FROM team_results")).scalar())
    print("distinct venues:", conn.execute(text("SELECT COUNT(DISTINCT venue) FROM matches")).scalar())
