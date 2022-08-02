"""
Add lobby cvars
"""

from yoyo import step

__depends__ = {'20220418_01_TVFSj'}

steps = [
    step(
        (
            'CREATE TABLE lobby_cvars(\n'
            '    name VARCHAR(128) NOT NULL,\n'
            '    value VARCHAR(256) NOT NULL,\n'
            '    lobby_id INTEGER REFERENCES lobbies (id) ON DELETE CASCADE\n'
            ');'
        ),
        'DROP TABLE lobby_cvars;'
    )
]
