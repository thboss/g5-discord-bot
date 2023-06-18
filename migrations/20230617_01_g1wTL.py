"""
Add map_method
"""

from yoyo import step

__depends__ = {'20220804_01_nUHpL'}

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
        )
    )
]
