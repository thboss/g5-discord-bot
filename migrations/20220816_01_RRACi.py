"""
Drop unused column: private
"""

from yoyo import step

__depends__ = {'20220804_01_nUHpL'}

steps = [
    step(
        (
            'ALTER TABLE lobbies\n'
            '    DROP COLUMN private\n'
            ';'
        )
    )
]
