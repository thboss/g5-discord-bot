"""

"""

from yoyo import step

__depends__ = {'20220602_01_67ISe'}

steps = [
    step(
        (
            'CREATE TABLE private_lobby_users(\n'
            '    lobby_id INTEGER REFERENCES lobbies (id) ON DELETE CASCADE,\n'
            '    user_id BIGINT REFERENCES users (discord_id) ON DELETE CASCADE,\n'
            '    CONSTRAINT private_lobby_user_pkey PRIMARY KEY (lobby_id, user_id)\n'
            ');'
        ),
        'DROP TABLE private_lobby_users;'
    )
]
