"""

"""

from yoyo import step

__depends__ = {'20231114_01_NN4Kb'}

steps = [
    step(
      (
        'ALTER TABLE matches\n'
        '   ADD COLUMN team1_name VARCHAR(32) DEFAULT NULL,\n'
        '   ADD COLUMN team2_name VARCHAR(32) DEFAULT NULL,\n'
        '   ADD COLUMN map_name VARCHAR(32) DEFAULT NULL,\n'
        '   ADD COLUMN rounds_played SMALLINT NOT NULL DEFAULT 0,\n'
        '   ADD COLUMN team1_score SMALLINT NOT NULL DEFAULT 0,\n'
        '   ADD COLUMN team2_score SMALLINT NOT NULL DEFAULT 0,\n'
        '   ADD COLUMN connect_time SMALLINT NOT NULL DEFAULT 300,\n'
        '   ADD COLUMN canceled BOOL NOT NULL DEFAULT false,\n'
        '   ADD COLUMN finished BOOL NOT NULL DEFAULT false\n'
        ';'
      )
    ),
    step(
      (
        'CREATE TABLE player_stats(\n'
        '   match_id VARCHAR(32) DEFAULT NULL REFERENCES matches (id) ON DELETE CASCADE,\n'
        '   user_id BIGINT DEFAULT NULL REFERENCES users (id) ON DELETE CASCADE,\n'
        '   steam_id BIGINT DEFAULT NULL,\n'
        '   team VARCHAR(5) DEFAULT NULL,\n'
        '   kills SMALLINT DEFAULT 0,\n'
        '   deaths SMALLINT DEFAULT 0,\n'
        '   assists SMALLINT DEFAULT 0,\n'
        '   mvps SMALLINT DEFAULT 0,\n'
        '   headshots SMALLINT DEFAULT 0,\n'
        '   k2 SMALLINT DEFAULT 0,\n'
        '   k3 SMALLINT DEFAULT 0,\n'
        '   k4 SMALLINT DEFAULT 0,\n'
        '   k5 SMALLINT DEFAULT 0,\n'
        '   score SMALLINT DEFAULT 0\n'
        ');'
      )
    )
]
