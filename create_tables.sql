-- Teams
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
);

-- Players
CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    positions TEXT[],
    date_of_birth DATE,
    height INT,
    weight INT,
    birthplace VARCHAR(255),
    nickname VARCHAR(255),
    junior_club VARCHAR(255),
    biography TEXT,
    debut JSONB,
    career JSONB
);

-- Matches
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    round INT NOT NULL,
    date TIMESTAMP WITH TIME ZONE,
    venue VARCHAR(255),
    home_team_id INT NOT NULL REFERENCES teams(id),
    away_team_id INT REFERENCES teams(id),
    score_home INT,
    score_away INT,
    attendance INT,
    weather VARCHAR(255),
    ground_conditions VARCHAR(255)
);

-- Team Membership (player-team history)
CREATE TABLE team_membership (
    id SERIAL PRIMARY KEY,
    player_id INT NOT NULL REFERENCES players(id),
    team_id INT NOT NULL REFERENCES teams(id),
    start_date DATE NOT NULL,
    end_date DATE
);

-- Player Appearance in Matches
CREATE TABLE player_appearance (
    id SERIAL PRIMARY KEY,
    player_id INT NOT NULL REFERENCES players(id),
    match_id INT NOT NULL REFERENCES matches(id),
    team_id INT NOT NULL REFERENCES teams(id),
    jersey_number INT,
    stats JSONB
);

-- Event Types Lookup Table
CREATE TABLE event_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

-- Roles Lookup Table for event_players.role
CREATE TABLE event_roles (
    id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE
);

-- Events Table
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    match_id INT NOT NULL REFERENCES matches(id),
    team_id INT REFERENCES teams(id),
    player_id INT REFERENCES players(id),
    event_type_id INT NOT NULL REFERENCES event_types(id),
    game_time_sec INT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Junction table for players involved in events (many-to-many)
CREATE TABLE event_players (
    event_id INT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    player_id INT NOT NULL REFERENCES players(id),
    role_id INT REFERENCES event_roles(id),
    PRIMARY KEY (event_id, player_id)
);

-- Indexes to speed up common queries
CREATE INDEX idx_events_match_time ON events(match_id, game_time_sec);
CREATE INDEX idx_player_appearance_match_team ON player_appearance(match_id, team_id);
CREATE INDEX idx_team_membership_player ON team_membership(player_id);


-- Event roles
INSERT INTO event_roles (role_name) VALUES
('primary'),
('on'),
('off'),
('dangerous tackle'),
('professional foul'),
('escorts'),
('flop'),
('slow peel'),
('obstruction'),
('early tackle'),
('captain"s challenge - successful'),
('captain"s challenge - unsuccessful');


ALTER TABLE matches
ADD CONSTRAINT unique_match
  UNIQUE NULLS NOT DISTINCT (round, away_team_id, date, venue, home_team_id, score_home, score_away);

-- basic matches
CREATE OR REPLACE VIEW match_summaries AS
SELECT
    m.date,
    ht.name as home_team,
    m.score_home,
    at.name as away_team,
    m.score_away,
    m.venue,
    m.round
FROM matches m
LEFT JOIN teams ht ON m.home_team_id = ht.id
LEFT JOIN teams AT ON m.away_team_id = at.id;

-- Create the ladder view
CREATE OR REPLACE VIEW ladder AS
WITH 
wins AS (
  SELECT home_team AS team, 2 AS pts, score_home as team_for, score_away as team_against, 'win' as home_match_status
  FROM match_summaries
  WHERE away_team IS NOT NULL AND score_home > score_away

  UNION ALL

  SELECT away_team AS team, 2 AS pts, score_away as team_for, score_home as team_against, 'win' as home_match_status
  FROM match_summaries
  WHERE away_team IS NOT NULL AND score_away > score_home
),
losses AS (
  SELECT away_team AS team, 0 AS pts, score_away as team_for, score_home as team_against, 'loss' as home_match_status
  FROM match_summaries
  WHERE away_team IS NOT NULL AND score_away < score_home

  UNION ALL

  SELECT home_team AS team, 0 AS pts, score_home as team_for, score_away as team_against, 'loss' as home_match_status
  FROM match_summaries
  WHERE away_team IS NOT NULL AND score_home < score_away
),
draws AS (
  SELECT home_team AS team, 1 AS pts, score_home as team_for, score_away as team_against, 'draw' as home_match_status
  FROM match_summaries
  WHERE away_team IS NOT NULL AND score_home = score_away

  UNION ALL

  SELECT away_team AS team, 1 AS pts, score_away as team_for, score_home as team_against, 'draw' as home_match_status
  FROM match_summaries
  WHERE away_team IS NOT NULL AND score_home = score_away
),
byes AS (
  SELECT home_team AS team, 2 AS pts, 0 AS team_for, 0 AS team_against, 'bye' as home_match_status
  FROM match_summaries
  WHERE away_team IS NULL
),
combined AS (
  SELECT * FROM wins
  UNION ALL
  SELECT * FROM byes
  UNION ALL
  SELECT * FROM losses
  UNION ALL
  SELECT * FROM draws
),
team_stats AS (
  SELECT 
    team,
    COUNT(*) FILTER (WHERE home_match_status IN ('win', 'loss', 'draw')) AS games_played,
    SUM(CASE WHEN home_match_status = 'win'  THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN home_match_status = 'loss' THEN 1 ELSE 0 END) AS losses,
    SUM(CASE WHEN home_match_status = 'draw' THEN 1 ELSE 0 END) AS draws,
    SUM(CASE WHEN home_match_status = 'bye'  THEN 1 ELSE 0 END) AS byes,
    SUM(team_for)                   AS points_for,
    SUM(team_against)              AS points_against,
    SUM(team_for) - SUM(team_against) AS points_diff,
    SUM(pts)                        AS total_points
  FROM combined
  GROUP BY team
)
SELECT 
  RANK() OVER (
    ORDER BY total_points DESC, points_diff DESC, points_for DESC
  ) AS ladder_position,
  *
FROM team_stats
ORDER BY ladder_position;

--  Join in team, player, and event type names
CREATE OR REPLACE VIEW basic_events AS
SELECT 
    p.name AS player,
    e.game_time_sec,
    et.name AS event,
    e.description,
    m.round
FROM events e
INNER JOIN event_types et ON et.id = e.event_type_id
LEFT JOIN players p ON p.id = e.player_id
INNER JOIN matches m ON m.id = e.match_id;

-- copy production to a test database
CREATE DATABASE test
WITH TEMPLATE nrldb
OWNER nrluser;
