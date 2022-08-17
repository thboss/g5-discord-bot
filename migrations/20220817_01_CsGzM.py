"""
Add autoready for lobby
"""

from yoyo import step

__depends__ = {'20220816_01_RRACi'}

steps = [
    step(
        (
            'ALTER TABLE lobbies\n'
            '    ADD COLUMN autoready BOOL DEFAULT FALSE\n'
            ';'
        ),
        (
            'ALTER TABLE lobbies\n'
            '    DROP COLUMN autoready\n'
            ';'
        )
    )
]
