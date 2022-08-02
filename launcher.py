# launcher.py

from bot.resources import Config, G5

import asyncio
import asyncpg
import logging
import argparse
from dotenv import load_dotenv
import os

load_dotenv()  # Load the environment variables in the local .env file

db_connect_url = 'postgresql://{POSTGRESQL_USER}:{POSTGRESQL_PASSWORD}@{POSTGRESQL_HOST}:{POSTGRESQL_PORT}/{POSTGRESQL_DB}'
db_connect_url = db_connect_url.format(**os.environ)
loop = asyncio.get_event_loop()
pool = loop.run_until_complete(asyncpg.create_pool(db_connect_url))
logger = logging.getLogger('G5.db')


class DBHelper:
    """"""
    logger.info('Creating database connection pool')

    @staticmethod
    async def close():
        """"""
        logger.info('Closing database connection pool')
        await pool.close()

    @staticmethod
    async def query(sql, *args):
        """"""
        async with pool.acquire() as connection:
            async with connection.transaction():
                rows = await connection.fetch(sql) if not args else await connection.fetch(sql, *args)
                return [{col: val for col, val in row.items()} for row in rows]

    @staticmethod
    async def sync_guilds(*guild_ids):
        """"""
        count_cols_stmt = (
            "SELECT COUNT(*)\n"
            "FROM INFORMATION_SCHEMA.COLUMNS\n"
            "WHERE table_name = 'guilds';"
        )
        result = await DBHelper.query(count_cols_stmt)

        insert_rows = [tuple([guild_id] + [None] * (result[0]['count'] - 1))
                       for guild_id in guild_ids]

        insert_statement = (
            'INSERT INTO guilds (id)\n'
            '    (SELECT id FROM unnest($1::guilds[]))\n'
            '    ON CONFLICT (id) DO NOTHING\n'
            '    RETURNING id;'
        )
        delete_statement = (
            'DELETE FROM guilds\n'
            '    WHERE id::BIGINT != ALL($1::BIGINT[])\n'
            '    RETURNING id;'
        )

        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.fetch(insert_statement, insert_rows)
                await connection.fetch(delete_statement, guild_ids)


def run_bot():
    """ Parse the config file and run the bot. """
    # Get environment variables and set configs

    api_url = os.environ['G5API_URL']
    g5v_url = os.environ['G5V_URL']
    Config.api_url = api_url[:-1] if api_url.endswith('/') else api_url
    Config.g5v_url = g5v_url[:-1] if g5v_url.endswith('/') else g5v_url
    Config.discord_token = os.environ['DISCORD_BOT_TOKEN']
    Config.prefixes = os.environ['DISCORD_BOT_PREFIXES'].split()
    Config.lang = os.environ['DISCORD_BOT_LANGUAGE']
    G5.db = DBHelper

    # Instantiate bot and run
    from bot.bot import G5Bot
    bot = G5Bot()
    bot.run()


if __name__ == '__main__':
    argparse.ArgumentParser(description='Run the G5 bot')
    run_bot()
