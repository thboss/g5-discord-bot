"""
Create base tables
"""

from yoyo import step

__depends__ = {}

steps = [
    step(
        'CREATE TYPE team_method AS ENUM(\'captains\', \'autobalance\', \'random\');',
        'DROP TYPE team_method;'
    ),
    step(
        'CREATE TYPE captain_method AS ENUM(\'volunteer\', \'rank\', \'random\');',
        'DROP TYPE captain_method;'
    ),
    step(
        'CREATE TYPE series_type AS ENUM(\'bo1\', \'bo2\', \'bo3\');',
        'DROP TYPE series_type;'
    ),
    step(
        (
            'CREATE TABLE guilds(\n'
            '    id BIGSERIAL PRIMARY KEY,\n'
            '    linked_role BIGINT DEFAULT NULL,\n'
            '    prematch_channel BIGINT DEFAULT NULL,\n'
            '    category BIGINT DEFAULT NULL\n,'
            '    results_channel BIGINT DEFAULT NULL\n'
            ');'
        ),
        'DROP TABLE guilds;'
    ),
    step(
        (
            'CREATE TABLE lobbies(\n'
            '    id SERIAL PRIMARY KEY,\n'
            '    guild BIGINT DEFAULT NULL REFERENCES guilds (id) ON DELETE CASCADE,\n'
            '    series_type series_type DEFAULT \'bo1\',\n'
            '    team_method team_method DEFAULT \'captains\',\n'
            '    captain_method captain_method DEFAULT \'volunteer\',\n'
            '    capacity SMALLINT DEFAULT 10,\n'
            '    category BIGINT DEFAULT NULL,\n'
            '    queue_channel BIGINT DEFAULT NULL,\n'
            '    lobby_channel BIGINT DEFAULT NULL,\n'
            '    last_message BIGINT DEFAULT NULL,\n'
            '    autoready BOOL DEFAULT FALSE\n'
            ');'
        ),
        'DROP TABLE lobbies;'
    ),
    step(
        (
            'CREATE TABLE matches(\n'
            '    id INTEGER PRIMARY KEY,\n'
            '    guild BIGINT DEFAULT NULL REFERENCES guilds (id) ON DELETE CASCADE,\n'
            '    message BIGINT DEFAULT NULL,\n'
            '    category BIGINT DEFAULT NULL,\n'
            '    lobby INTEGER DEFAULT NULL,\n'
            '    team1_channel BIGINT DEFAULT NULL,\n'
            '    team2_channel BIGINT DEFAULT NULL,\n'
            '    team1_id INTEGER DEFAULT NULL,\n'
            '    team2_id INTEGER DEFAULT NULL\n'
            ');'
        ),
        'DROP TABLE matches;'
    ),
    step(
        (
            'CREATE TABLE users('
            '    discord_id BIGSERIAL UNIQUE,\n'
            '    steam_id VARCHAR(18) UNIQUE,\n'
            '    flag VARCHAR(3) DEFAULT NULL,\n'
            '    PRIMARY KEY (discord_id, steam_id)\n'
            ');'
        ),
        'DROP TABLE users;'
    ),
    step(
        (
            'CREATE TABLE queued_users(\n'
            '    lobby_id INTEGER REFERENCES lobbies (id) ON DELETE CASCADE,\n'
            '    user_id BIGINT REFERENCES users (discord_id) ON DELETE CASCADE,\n'
            '    CONSTRAINT queued_user_pkey PRIMARY KEY (lobby_id, user_id)\n'
            ');'
        ),
        'DROP TABLE queued_users;'
    ),
    step(
        (
            'CREATE TABLE match_users(\n'
            '    match_id INTEGER REFERENCES matches (id) ON DELETE CASCADE,\n'
            '    user_id BIGINT REFERENCES users (discord_id),\n'
            '    CONSTRAINT match_user_pkey PRIMARY KEY (match_id, user_id)\n'
            ');'
        ),
        'DROP TABLE match_users;'
    )
]
