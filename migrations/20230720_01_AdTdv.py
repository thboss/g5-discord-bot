"""
Add teams table
"""

from yoyo import step

__depends__ = {'20230707_01_71bBL'}

steps = [
    step(
        (
            'CREATE TABLE teams(\n'
            '    id INTEGER PRIMARY KEY,\n'
            '    guild BIGINT DEFAULT NULL REFERENCES guilds (id) ON DELETE CASCADE,\n'
            '    name VARCHAR(32) DEFAULT NULL,\n'
            '    flag VARCHAR(3) DEFAULT NULL,\n'
            '    captain BIGINT DEFAULT NULL,\n'
            '    role BIGINT DEFAULT NULL\n'
            ');'
        ),
        'DROP TABLE teams;'
    ),
    step(
        (
            'CREATE TABLE team_users(\n'
            '    team_id INTEGER REFERENCES teams (id) ON DELETE CASCADE,\n'
            '    user_id BIGINT REFERENCES users (discord_id) ON DELETE CASCADE,\n'
            '    CONSTRAINT team_user_pkey PRIMARY KEY (team_id, user_id)\n'
            ');'
        ),
        'DROP TABLE team_users;'
    )
]
