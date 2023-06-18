"""
Add game_mode type to the lobby
"""

from yoyo import step

__depends__ = {'20230617_01_g1wTL'}

steps = [
    step(
        'CREATE TYPE game_mode AS ENUM(\'competitive\', \'wingman\');',
        'DROP TYPE game_mode;'
    ),
    step(
        (
            'ALTER TABLE lobbies\n'
            '    ADD COLUMN game_mode game_mode DEFAULT \'competitive\'\n'
            ';'
        )
    )
]
