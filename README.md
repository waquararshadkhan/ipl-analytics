# IPL Performance Analytics

Ball-by-ball analysis of every Indian Premier League match from **2008 to 2024** —
1,095 matches and 260,920 deliveries. Raw data is cleaned in **Python/Pandas**,
loaded into **MySQL**, analysed with **SQL**, and presented in a three-page
**Power BI** dashboard.

**Stack:** Python (Pandas, SQLAlchemy) → MySQL 8 → Power BI Desktop

![Power BI dashboard](images/dashboard.png)

---

## Dataset

[IPL Complete Dataset (2008–2024)](https://www.kaggle.com/datasets/patrickb1912/ipl-complete-dataset-20082020) — Kaggle.

| File | Rows | Grain |
|---|---|---|
| `matches.csv` | 1,095 | One row per match — teams, venue, toss, result, player of the match |
| `deliveries.csv` | 260,920 | **One row per ball bowled** — batter, bowler, runs, extras, wickets |

The join on `matches.id = deliveries.match_id` is clean: 1,095 unique IDs on both
sides, **zero orphans** in either direction.

---

## The interesting part: the data doesn't contain the metrics

Nothing in the source says "strike rate" or "economy". Every meaningful number has
to be derived from ball-level events, and each one has a cricket rule attached that
a naive `COUNT(*)` gets wrong.

### 1. `over` is zero-indexed

The column runs **0–19**, not 1–20. Filtering `over BETWEEN 1 AND 6` for the
powerplay silently returns overs 2–7. The cleaning step shifts it to `over_no`
(1–20) so no downstream query has to remember.

### 2. Balls faced ≠ row count

An over can contain up to **11** deliveries because wides and no-balls are
re-bowled. The two rules differ by discipline:

| Metric | Excludes | Column |
|---|---|---|
| Bowling (economy, overs) | wides **and** no-balls | `is_legal_ball` |
| Batting (strike rate) | wides **only** — a no-ball *is* faced | `is_ball_faced` |

### 3. Not every wicket belongs to the bowler

Of 12,950 dismissals, **1,135 are not credited to the bowler**: 1,114 run outs,
15 retired hurt, 3 obstructing the field, 3 retired out. Ranking bowlers on
`SUM(is_wicket)` overstates anyone who played in run-out-heavy matches. The
`is_bowler_wicket` flag counts only bowled, caught, LBW, stumped, caught-and-bowled
and hit wicket — **11,815** wickets.

### 4. Runs conceded ≠ runs scored

Byes, legbyes and penalty runs are not charged to the bowler; wides and no-balls
are. The `runs_conceded` column applies that rule.

### 5. Nulls are structural, not missing

95% of `dismissal_kind` is null — because no wicket fell on those balls. Running
`dropna()` on this dataset would delete almost everything.

| Column | Nulls | Meaning |
|---|---|---|
| `extras_type` | 246,795 | Not an extra (14,125 were: 8,380 wides, 4,001 legbyes, 1,069 no-balls, 673 byes) |
| `player_dismissed` | 247,970 | No wicket fell |
| `fielder` | 251,566 | No fielder involved — bowled and LBW have none |
| `method` (matches) | 1,074 | Normal match; only 21 were D/L affected |
| `winner` (matches) | 5 | The 5 abandoned "no result" matches |

---

## Cleaning

### Season labels

The source mixes formats — `2007/08`, `2009`, `2020/21`. Mapped to single years by
checking the **actual match dates**, not by parsing the label:

| Label | Matches played | Mapped to |
|---|---|---|
| `2007/08` | Apr–Jun 2008 | 2008 |
| `2009/10` | Mar–Apr 2010 | **2010** |
| `2020/21` | Sep–Nov 2020 | 2020 |

`2009/10` maps to 2010, which is not what the label suggests — the reason for
verifying against dates.

### Team names: 19 → 15

Franchises were renamed and one name is a source-data typo:

| Source | Canonical |
|---|---|
| Delhi Daredevils | Delhi Capitals |
| Kings XI Punjab | Punjab Kings |
| Rising Pune Supergiant**s** | Rising Pune Supergiant *(typo)* |
| Royal Challengers Bangalore | Royal Challengers Bengaluru |

### Venue names: 58 → 40

Three separate problems mixed together — inconsistent city suffixes
("Eden Gardens" vs "Eden Gardens, Kolkata"), punctuation variants
("M Chinnaswamy" vs "M.Chinnaswamy"), and genuine renames
(Feroz Shah Kotla → Arun Jaitley Stadium, 2019).

Left unfixed, M Chinnaswamy Stadium splits into three bars of 65, 15 and 14
matches instead of one bar of 94.

> **Documented decision:** "Sardar Patel Stadium, Motera" is merged into
> "Narendra Modi Stadium". The ground was demolished and rebuilt on the same site,
> so this is arguably two different stadiums with different dimensions. Merged for
> venue-lineage continuity; separating them is equally defensible.

---

## Database

Two tables plus one view in the `ipl_analytics` schema.

Column types are declared explicitly on load rather than left to Pandas. `to_sql`
maps text columns to MySQL `TEXT`, which **cannot be indexed without a prefix
length** — so `CREATE INDEX idx_batter ON deliveries (batter)` would fail. Declaring
`VARCHAR(60)` makes the indexes possible.

Indexes on `match_id`, `batter`, `bowler`, `phase` and `season`. Without them,
every join scans all 260,920 rows.

The `team_results` view solves a shape problem: a team appears as either `team1` or
`team2`, so win rate cannot be computed by grouping on one column. The view
`UNION ALL`s both into a single team column.

---

## Findings

### 1. Winning the toss is worthless — the decision is not

The toss winner wins **50.8%** of matches (554 of 1,090 decided). A coin flip.

But split by what they chose to do with it:

| Decision | Matches | Won | Win rate |
|---|---|---|---|
| Chose to **field** | 700 | 377 | **53.9%** |
| Chose to **bat** | 390 | 177 | **45.4%** |

An **8.5-point swing**, and it holds in every era:

| Era | Bat | Field |
|---|---|---|
| 2008–13 | 46.6% | 53.9% |
| 2014–18 | 43.4% | 56.8% |
| 2019–24 | 44.4% | 51.6% |

Teams adapted: fielding was chosen **48%** of the time in 2008–13 and **73%** in
2019–24. The headline number says the toss doesn't matter; the split says the
decision does.

### 2. T20 accelerated in the powerplay, not at the death

Overall scoring went 8.31 → 9.56 runs per over (+15%) between 2008 and 2024. By
phase the movement is very uneven:

| Phase | 2008 | 2024 | Change |
|---|---|---|---|
| **Powerplay** (1–6) | 7.70 | 9.46 | **+22.9%** |
| Death (16–20) | 9.95 | 11.21 | +12.7% |
| Middle (7–15) | 7.99 | 8.83 | +10.5% |

The common assumption is that death-over hitting drove the change. It didn't —
the powerplay did. By 2024 teams open at 9.46, close to what death overs produced
in 2008.

The rise is recent and steep: 8.54 → 8.99 → 9.56 across 2022–24, the fastest
three-year increase in IPL history. The **Impact Player rule (2023)** lets teams
bat deeper, which plausibly supports more powerplay risk — a hypothesis, not a
demonstrated cause, since there is no counterfactual in this data.

### 3. Sunil Narine is a structural outlier

| Metric | Narine | Rank |
|---|---|---|
| Career economy | 6.74 | 2nd (1,000+ balls) |
| **Death-over economy** | **7.40** | **1st** (300+ balls) |
| Boundary % as batter | 80.7% | 1st (1,000+ runs) |

A spinner with the best death-over economy in IPL history, ahead of Malinga (7.86)
and Bumrah (8.29) — the two bowlers usually named as the format's best finishers.

### 4. Leaderboards

| Category | Leader | Value |
|---|---|---|
| Runs | V Kohli | 8,014 |
| Wickets | YS Chahal | 205 |
| Strike rate (500+ balls) | AD Russell | 174.8 |
| Economy (1,000+ balls) | M Muralitharan | 6.70 |
| Sixes | CH Gayle | 359 |
| Player of the Match | AB de Villiers | 25 |

### 5. Teams

| Team | Played | Win % | Titles |
|---|---|---|---|
| Chennai Super Kings | 237 | **58.2%** | 5 |
| Mumbai Indians | 261 | 55.2% | 5 |
| Kolkata Knight Riders | 251 | 52.2% | 3 |
| Royal Challengers Bengaluru | 252 | 48.8% | **0** |

Gujarat Titans actually posts the highest rate at 62.2%, but over only 45 matches —
reported with the caveat rather than ranked first. Every rate metric in this project
carries a minimum-volume threshold for the same reason.

RCB have the most prolific batter (Kohli, 8,014 runs), the most Player of the Match
awards (de Villiers, 25) and the most sixes (Gayle, 359) — and no title.

---

## Dashboard

Three pages:

1. **Overview** — season scoring trend, team win rates, venue scoring, title history
2. **Players** — batting and bowling leaderboards with season and team slicers
3. **Insights** — toss decision impact, phase evolution, dismissal breakdown

Phase ordering is controlled by a `phase_order` calculated column derived from
`over_no` (not from `phase` — that creates a circular dependency in Power BI).

---

## Repository

```
ipl-analytics/
├── data/
│   ├── matches.csv                 # raw (Kaggle)
│   ├── deliveries.csv              # raw (Kaggle)
│   ├── cleaned_matches.csv
│   └── cleaned_deliveries.csv
├── images/
│   └── dashboard.png
├── inspect_data.py                 # profiling: shape, dtypes, nulls, team/venue variants
├── clean_data.py                   # season, team, venue standardisation + derived flags
├── load_to_mysql.py                # typed load with indexes
├── reload_matches.py               # partial reload after the venue fix
├── queries.sql                     # 18 analysis queries
├── ipl.pbix                        # Power BI dashboard
├── ipl-theme-dark.json             # Power BI theme
├── .gitignore
└── README.md
```

## Reproducing

```bash
pip install pandas sqlalchemy pymysql
```

```sql
CREATE DATABASE ipl_analytics;
```

```powershell
$env:MYSQL_PWD="your_password"
python clean_data.py
python load_to_mysql.py
```

Then create the `team_results` view (see `queries.sql`), and connect Power BI via an
ODBC DSN named `ipl_dsn` pointing at `ipl_analytics`.

## Note on the dashboard theme

Category colours were validated for colour-vision deficiency rather than chosen by
eye: worst-case separation is ΔE 9.4 under deuteranopia simulation against a target
of ≥8, measured on the dark chart surface. This matters most on the phase-evolution
chart, where three overlapping lines in similar hues would be unreadable.
