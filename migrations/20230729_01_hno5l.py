"""

"""

from yoyo import step

__depends__ = {'20230720_01_AdTdv'}

steps = [
    step(
        (
            'ALTER TABLE matches\n'
            '    DROP COLUMN lobby,\n'
            '    ADD COLUMN channel BIGINT DEFAULT NULL\n'
            ';'
        ),
        (
            'ALTER TABLE matches\n'
            '    ADD COLUMN lobby INTEGER DEFAULT NULL,\n'
            '    DROP COLUMN channel\n'
            ';'
        )
    )
]
