# resources.py

import os
import sys
import json


if not os.path.isfile(f"{os.path.realpath(os.path.dirname(__file__))}/../../config.json"):
    sys.exit("'config.json' not found! Please add it and try again.")
else:
    with open(f"{os.path.realpath(os.path.dirname(__file__))}/../../config.json") as file:
        config = json.load(file)


class Config:
    prefix = config['bot']['prefix']
    token = config['bot']['token']
    guild_id = config['bot']['guild_id']
    sync_commands_globally = config['bot']['sync_commands_globally']
    debug = config['bot']['debug']
    base_url = config['web']['base_url']
    api_key = config['web']['api_key']
    POSTGRESQL_USER = config['db']['user']
    POSTGRESQL_PASSWORD = config['db']['password']
    POSTGRESQL_DB = config['db']['database']
    POSTGRESQL_HOST = config['db']['host']
    POSTGRESQL_PORT = config['db']['port']
