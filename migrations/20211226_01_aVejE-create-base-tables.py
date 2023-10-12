"""
Create base tables
"""

from yoyo import step

__depends__ = {}

steps = [
    step(
        'CREATE TYPE team_method AS ENUM(\'captains\', \'random\');',
        'DROP TYPE team_method;'
    ),
    step(
        'CREATE TYPE captain_method AS ENUM(\'volunteer\', \'random\');',
        'DROP TYPE captain_method;'
    ),
    step(
        'CREATE TYPE map_method AS ENUM(\'veto\', \'random\');',
        'DROP TYPE map_method;'
    ),
    step(
        'CREATE TYPE game_mode AS ENUM(\'competitive\', \'wingman\');',
        'DROP TYPE game_mode;'
    ),
    step(
        (
            'CREATE TABLE guilds(\n'
            '    id BIGSERIAL PRIMARY KEY,\n'
            '    linked_role BIGINT DEFAULT NULL,\n'
            '    waiting_channel BIGINT DEFAULT NULL,\n'
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
            '    team_method team_method DEFAULT \'captains\',\n'
            '    map_method map_method DEFAULT \'veto\',\n'
            '    captain_method captain_method DEFAULT \'volunteer\',\n'
            '    capacity SMALLINT DEFAULT 10,\n'
            '    category BIGINT DEFAULT NULL,\n'
            '    queue_channel BIGINT DEFAULT NULL,\n'
            '    lobby_channel BIGINT DEFAULT NULL,\n'
            '    last_message BIGINT DEFAULT NULL,\n'
            '    game_mode game_mode DEFAULT \'competitive\'\n'
            ');'
        ),
        'DROP TABLE lobbies;'
    ),
    step(
        (
            'CREATE TABLE matches(\n'
            '    id VARCHAR(64) PRIMARY KEY,\n'
            '    game_server_id VARCHAR(64) DEFAULT NULL,\n'
            '    guild BIGINT DEFAULT NULL REFERENCES guilds (id) ON DELETE CASCADE,\n'
            '    channel BIGINT DEFAULT NULL,\n'
            '    message BIGINT DEFAULT NULL,\n'
            '    category BIGINT DEFAULT NULL,\n'
            '    team1_channel BIGINT DEFAULT NULL,\n'
            '    team2_channel BIGINT DEFAULT NULL\n'
            ');'
        ),
        'DROP TABLE matches;'
    ),
    step(
        (
            'CREATE TABLE users(\n'
            '    discord_id BIGSERIAL UNIQUE,\n'
            '    steam_id VARCHAR(18) UNIQUE\n'
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
            '    match_id VARCHAR(64) REFERENCES matches (id) ON DELETE CASCADE,\n'
            '    user_id BIGINT REFERENCES users (discord_id),\n'
            '    CONSTRAINT match_user_pkey PRIMARY KEY (match_id, user_id)\n'
            ');'
        ),
        'DROP TABLE match_users;'
    ),
    step(
        (
            'CREATE TABLE lobby_maps(\n'
            '    map_name VARCHAR(32) NOT NULL,\n'
            '    lobby_id INTEGER REFERENCES lobbies (id) ON DELETE CASCADE,\n'
            '    CONSTRAINT lobby_maps_pkey PRIMARY KEY (lobby_id, map_name)\n'
            ');'
        ),
        'DROP TABLE lobby_maps;'
    ),
    step(
        (
            'CREATE TABLE spectators(\n'
            '    guild_id BIGINT REFERENCES guilds (id) ON DELETE CASCADE,\n'
            '    user_id BIGINT REFERENCES users (discord_id) ON DELETE CASCADE,\n'
            '    CONSTRAINT spectator_pkey PRIMARY KEY (guild_id, user_id)\n'
            ');'
        ),
        'DROP TABLE spectators;'
    )
]
