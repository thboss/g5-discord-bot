"""
Add map_method for lobby
"""

from yoyo import step

__depends__ = {'20220817_01_CsGzM'}

steps = [
    step(
        'CREATE TYPE map_method AS ENUM(\'veto\', \'random\');',
        'DROP TYPE map_method;'
    ),
    step(
        (
            'ALTER TABLE lobbies\n'
            '    ADD COLUMN map_method map_method DEFAULT \'veto\'\n'
            ';'
        ),
        (
            'ALTER TABLE lobbies\n'
            '    DROP COLUMN map_method\n'
            ';'
        )
    )
]
