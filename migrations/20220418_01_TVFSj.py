"""
Create guild maps
"""

from yoyo import step

__depends__ = {'20211226_01_aVejE-create-base-tables'}

steps = [
    step(
        (
            'CREATE TABLE guild_maps(\n'
            '    guild_id BIGINT REFERENCES guilds (id) ON DELETE CASCADE,\n'
            '    emoji_id BIGSERIAL PRIMARY KEY,\n'
            '    display_name VARCHAR(65) DEFAULT NULL,\n'
            '    dev_name VARCHAR(65) DEFAULT NULL\n'
            ');'
        ),
        'DROP TABLE guild_maps;'
    ),
    step(
        (
            'CREATE TABLE lobby_maps(\n'
            '    lobby_id INTEGER REFERENCES lobbies (id) ON DELETE CASCADE,\n'
            '    emoji_id BIGINT REFERENCES guild_maps (emoji_id) ON DELETE CASCADE,\n'
            '    CONSTRAINT lobby_maps_pkey PRIMARY KEY (lobby_id, emoji_id)\n'
            ');'
        ),
        'DROP TABLE lobby_maps;'
    )
]
