"""
Drop not null in steam_id
"""

from yoyo import step

__depends__ = {'20220524_01_DA8sh'}

steps = [
    step(
        (
            'ALTER TABLE users\n'
            '    DROP CONSTRAINT users_pkey,\n'
            '    ALTER COLUMN steam_id DROP NOT NULL\n'
            ';'
        )
    )
]
