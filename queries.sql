-- ============================================================
-- IPL Performance Analytics - SQL analysis
-- Database: ipl_analytics   Tables: matches (1,095), deliveries (260,920)
-- ============================================================
USE ipl_analytics;

-- ------------------------------------------------------------
-- BATTING
-- ------------------------------------------------------------

-- 1. Top run scorers of all time
SELECT batter,
       SUM(batsman_runs) AS runs,
       COUNT(DISTINCT match_id) AS matches_played
FROM deliveries
GROUP BY batter
ORDER BY runs DESC
LIMIT 15;

-- 2. Strike rate (min 500 balls faced)
--    Balls faced excludes wides only - a no-ball IS faced by the batter.
SELECT batter,
       SUM(batsman_runs) AS runs,
       SUM(CASE WHEN extras_type = 'wides' THEN 0 ELSE 1 END) AS balls_faced,
       ROUND(SUM(batsman_runs) * 100.0
             / SUM(CASE WHEN extras_type = 'wides' THEN 0 ELSE 1 END), 2) AS strike_rate
FROM deliveries
GROUP BY batter
HAVING balls_faced >= 500
ORDER BY strike_rate DESC
LIMIT 15;

-- 3. Most sixes
SELECT batter, COUNT(*) AS sixes
FROM deliveries
WHERE batsman_runs = 6
GROUP BY batter
ORDER BY sixes DESC
LIMIT 15;

-- 4. Boundary percentage - share of runs from 4s and 6s (min 1000 runs)
SELECT batter,
       SUM(batsman_runs) AS runs,
       SUM(CASE WHEN batsman_runs IN (4, 6) THEN batsman_runs ELSE 0 END) AS boundary_runs,
       ROUND(SUM(CASE WHEN batsman_runs IN (4, 6) THEN batsman_runs ELSE 0 END)
             * 100.0 / SUM(batsman_runs), 1) AS boundary_pct
FROM deliveries
GROUP BY batter
HAVING runs >= 1000
ORDER BY boundary_pct DESC
LIMIT 15;

-- 5. Strike rate by match phase (min 300 balls in that phase)
SELECT batter, phase,
       SUM(batsman_runs) AS runs,
       SUM(CASE WHEN extras_type = 'wides' THEN 0 ELSE 1 END) AS balls_faced,
       ROUND(SUM(batsman_runs) * 100.0
             / SUM(CASE WHEN extras_type = 'wides' THEN 0 ELSE 1 END), 2) AS strike_rate
FROM deliveries
GROUP BY batter, phase
HAVING balls_faced >= 300
ORDER BY strike_rate DESC
LIMIT 20;

-- ------------------------------------------------------------
-- BOWLING
-- ------------------------------------------------------------

-- 6. Top wicket takers
--    is_bowler_wicket excludes run-outs / retired / obstructing.
SELECT bowler,
       SUM(is_bowler_wicket) AS wickets,
       COUNT(DISTINCT match_id) AS matches_played
FROM deliveries
GROUP BY bowler
ORDER BY wickets DESC
LIMIT 15;

-- 7. Economy rate (min 1000 legal balls)
--    Runs charged to the bowler exclude byes, legbyes and penalties.
--    Legal balls exclude BOTH wides and no-balls - they are re-bowled.
SELECT bowler,
       SUM(total_runs) - SUM(CASE WHEN extras_type IN ('byes', 'legbyes', 'penalty')
                                  THEN extra_runs ELSE 0 END) AS runs_conceded,
       SUM(is_legal_ball) AS legal_balls,
       ROUND((SUM(total_runs) - SUM(CASE WHEN extras_type IN ('byes', 'legbyes', 'penalty')
                                         THEN extra_runs ELSE 0 END)) * 6.0
             / SUM(is_legal_ball), 2) AS economy
FROM deliveries
GROUP BY bowler
HAVING legal_balls >= 1000
ORDER BY economy ASC
LIMIT 15;

-- 8. Best death-over bowlers (overs 16-20, min 300 legal balls)
SELECT bowler,
       SUM(is_bowler_wicket) AS wickets,
       SUM(is_legal_ball) AS legal_balls,
       ROUND((SUM(total_runs) - SUM(CASE WHEN extras_type IN ('byes', 'legbyes', 'penalty')
                                         THEN extra_runs ELSE 0 END)) * 6.0
             / SUM(is_legal_ball), 2) AS death_economy
FROM deliveries
WHERE phase = 'Death'
GROUP BY bowler
HAVING legal_balls >= 300
ORDER BY death_economy ASC
LIMIT 15;

-- 9. Bowling strike rate - balls per wicket (min 50 wickets)
SELECT bowler,
       SUM(is_bowler_wicket) AS wickets,
       SUM(is_legal_ball) AS legal_balls,
       ROUND(SUM(is_legal_ball) * 1.0 / SUM(is_bowler_wicket), 1) AS balls_per_wicket
FROM deliveries
GROUP BY bowler
HAVING wickets >= 50
ORDER BY balls_per_wicket ASC
LIMIT 15;

-- 10. Dismissal type breakdown
SELECT dismissal_kind, COUNT(*) AS n
FROM deliveries
WHERE is_wicket = 1
GROUP BY dismissal_kind
ORDER BY n DESC;

-- ------------------------------------------------------------
-- TEAM
-- ------------------------------------------------------------

-- 11. Team win percentage (excludes the 5 no-result matches)
SELECT t.team,
       COUNT(*) AS played,
       SUM(CASE WHEN m.winner = t.team THEN 1 ELSE 0 END) AS won,
       ROUND(SUM(CASE WHEN m.winner = t.team THEN 1 ELSE 0 END) * 100.0
             / COUNT(*), 1) AS win_pct
FROM matches m
JOIN (SELECT id, team1 AS team FROM matches
      UNION ALL
      SELECT id, team2 AS team FROM matches) t
  ON m.id = t.id
WHERE m.winner IS NOT NULL
GROUP BY t.team
HAVING played >= 50
ORDER BY win_pct DESC;

-- 12. Does winning the toss matter?
SELECT COUNT(*) AS decided_matches,
       SUM(CASE WHEN toss_winner = winner THEN 1 ELSE 0 END) AS toss_winner_won,
       ROUND(SUM(CASE WHEN toss_winner = winner THEN 1 ELSE 0 END) * 100.0
             / COUNT(*), 1) AS toss_win_pct
FROM matches
WHERE winner IS NOT NULL;

-- 13. Bat first vs chase - win rate by toss decision
SELECT toss_decision,
       COUNT(*) AS matches,
       SUM(CASE WHEN toss_winner = winner THEN 1 ELSE 0 END) AS toss_winner_won,
       ROUND(SUM(CASE WHEN toss_winner = winner THEN 1 ELSE 0 END) * 100.0
             / COUNT(*), 1) AS win_pct
FROM matches
WHERE winner IS NOT NULL
GROUP BY toss_decision;

-- 14. Highest team innings totals
SELECT d.match_id, m.season, d.batting_team, d.inning,
       SUM(d.total_runs) AS total
FROM deliveries d
JOIN matches m ON m.id = d.match_id
GROUP BY d.match_id, m.season, d.batting_team, d.inning
ORDER BY total DESC
LIMIT 15;

-- ------------------------------------------------------------
-- SEASON & VENUE
-- ------------------------------------------------------------

-- 15. Scoring rate by season - has IPL got faster?
SELECT m.season,
       COUNT(DISTINCT m.id) AS matches,
       SUM(d.total_runs) AS runs,
       SUM(d.is_legal_ball) AS legal_balls,
       ROUND(SUM(d.total_runs) * 6.0 / SUM(d.is_legal_ball), 2) AS runs_per_over
FROM matches m
JOIN deliveries d ON d.match_id = m.id
GROUP BY m.season
ORDER BY m.season;

-- 16. Runs per over by phase and season - where did the acceleration happen?
SELECT m.season, d.phase,
       ROUND(SUM(d.total_runs) * 6.0 / SUM(d.is_legal_ball), 2) AS runs_per_over
FROM matches m
JOIN deliveries d ON d.match_id = m.id
GROUP BY m.season, d.phase
ORDER BY m.season, FIELD(d.phase, 'Powerplay', 'Middle', 'Death');

-- 17. Venue scoring - which grounds are batting friendly? (min 20 matches)
SELECT m.venue,
       COUNT(DISTINCT m.id) AS matches,
       ROUND(SUM(d.total_runs) * 6.0 / SUM(d.is_legal_ball), 2) AS runs_per_over
FROM matches m
JOIN deliveries d ON d.match_id = m.id
GROUP BY m.venue
HAVING matches >= 20
ORDER BY runs_per_over DESC;

-- 18. Most Player of the Match awards
SELECT player_of_match, COUNT(*) AS awards
FROM matches
WHERE player_of_match IS NOT NULL
GROUP BY player_of_match
ORDER BY awards DESC
LIMIT 15;

SET SQL_SAFE_UPDATES = 0;
ALTER TABLE deliveries ADD COLUMN is_ball_faced TINYINT;
UPDATE deliveries SET is_ball_faced = CASE WHEN extras_type = 'wides' THEN 0 ELSE 1 END;
ALTER TABLE deliveries ADD COLUMN runs_conceded SMALLINT;
UPDATE deliveries SET runs_conceded = total_runs - CASE WHEN extras_type IN ('byes','legbyes','penalty') THEN extra_runs ELSE 0 END;


CREATE VIEW team_results AS
SELECT id AS match_id, season, venue, team1 AS team,
       CASE WHEN winner = team1 THEN 1 ELSE 0 END AS won
FROM matches WHERE winner IS NOT NULL
UNION ALL
SELECT id, season, venue, team2,
       CASE WHEN winner = team2 THEN 1 ELSE 0 END
FROM matches WHERE winner IS NOT NULL;