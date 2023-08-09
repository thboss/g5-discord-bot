"""
Add lobby regions
"""

from yoyo import step

__depends__ = {'20211226_01_aVejE-create-base-tables'}

steps = [
    step(
        (
            'ALTER TABLE lobbies\n'
            'ADD COLUMN region VARCHAR(3) DEFAULT NULL\n'
            ';'
        ),
        (
            'ALTER TABLE lobbies\n'
            'DROP COLUMN region\n'
            ';'
        )
    )
]
