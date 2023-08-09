"""
Add season_id field to the lobby table
"""

from yoyo import step

__depends__ = {'20230808_01_BHZAz'}

steps = [
    step(
        (
            'ALTER TABLE lobbies\n' \
            '    ADD COLUMN season_id INTEGER DEFAULT NULL\n' \
            ';'
        ),
        (
            'ALTER TABLE lobbies\n' \
            '    DROP COLUMN season_id\n' \
            ';'
        )
    )
]
