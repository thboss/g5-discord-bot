# guild.py

import discord
from discord.ext import commands
import os

from ..utils import Utils
from .map import Map
from bot.resources import G5


class Guild:
    """"""

    def __init__(
        self,
        guild,
        headers,
        linked_role,
        prematch_channel,
        leaders_channel,
        teams_channel,
        results_channel,
        category
    ):
        """"""
        self.guild = guild
        self.headers = headers
        self.linked_role = linked_role
        self.prematch_channel = prematch_channel
        self.leaders_channel = leaders_channel
        self.teams_channel = teams_channel
        self.results_channel = results_channel
        self.category = category
        self.is_setup = headers and linked_role

    @classmethod
    def from_dict(cls, guild_data: dict):
        """"""
        guild = G5.bot.get_guild(guild_data['id'])
        headers = {'user-api': guild_data['api_key']}
        return cls(
            guild,
            headers,
            guild.get_role(guild_data['linked_role']),
            guild.get_channel(guild_data['prematch_channel']),
            guild.get_channel(guild_data['leaders_channel']),
            guild.get_channel(guild_data['teams_channel']),
            guild.get_channel(guild_data['results_channel']),
            guild.get_channel(guild_data['category'])
        )

    @staticmethod
    async def get_guild_by_id(guild_id: int):
        """"""
        sql = "SELECT * FROM guilds\n" \
            f"    WHERE id =  $1;"
        guild_data = await G5.db.query(sql, guild_id)
        if guild_data:
            return Guild.from_dict(guild_data[0])

    async def update(self, data: dict):
        """"""
        col_vals = ",\n    ".join(
            f"{key} = {val}" for key, val in data.items())
        sql = 'UPDATE guilds\n' \
            f'    SET {col_vals}\n' \
            f'    WHERE id = $1;'
        await G5.db.query(sql, self.guild.id)

    async def get_maps(self):
        """"""
        sql = "SELECT * FROM guild_maps\n" \
              f"    WHERE guild_id = $1;"
        maps_data = await G5.db.query(sql, self.guild.id)
        guild_maps = [Map.from_dict(map_data, self.guild)
                      for map_data in maps_data]
        exist_maps = [m for m in guild_maps if m.emoji]

        if len(guild_maps) != len(exist_maps):
            exist_emojis_ids = ','.join([f'{m.emoji.id}' for m in exist_maps])
            sql = f"DELETE FROM guild_maps\n" \
                f"    WHERE guild_id = $1 AND emoji_id NOT IN ({exist_emojis_ids});"
            await G5.db.query(sql, self.guild.id)

        return exist_maps

    async def insert_maps(self, maps):
        """"""
        values = f", ".join(
            f"('{m.display_name}', '{m.dev_name}', {self.guild.id}, {m.emoji.id})" for m in maps)
        sql = "INSERT INTO guild_maps (display_name, dev_name, guild_id, emoji_id) \n" \
            f"VALUES {values};"
        await G5.db.query(sql)

    async def delete_maps(self, maps):
        """"""
        maps_str = ','.join([f"'{m.dev_name}'" for m in maps])
        sql = f"DELETE FROM guild_maps WHERE dev_name IN ({maps_str}) AND guild_id = $1;"
        await G5.db.query(sql, self.guild.id)

    async def create_custom_map(self, display_name, emoji):
        """"""
        exist_maps = await self.get_maps()
        new_maps = [Map(
            display_name,
            emoji.name,
            self.guild,
            emoji,
            f'<:{emoji.name}:{emoji.id}>'
        )]

        new_maps = [m for m in new_maps if m not in exist_maps]
        if new_maps:
            await self.delete_maps(new_maps)
            await self.insert_maps(new_maps)
            return True

    async def create_default_maps(self):
        """ Upload custom map emojis to guilds. """
        icons_dic = 'assets/maps/icons/'
        icons = os.listdir(icons_dic)
        guild_emojis_str = [e.name for e in self.guild.emojis]
        exist_maps = await self.get_maps()
        new_maps = []

        for icon in icons:
            if icon.endswith('.png') and os.stat(icons_dic + icon).st_size < 256000:
                display_name = icon.split('-')[0]
                dev_name = icon.split('-')[1].split('.')[0]

                if dev_name in guild_emojis_str:
                    emoji = discord.utils.get(self.guild.emojis, name=dev_name)
                else:
                    with open(icons_dic + icon, 'rb') as image:
                        try:
                            emoji = await self.guild.create_custom_emoji(name=dev_name, image=image.read())
                            G5.bot.logger.info(
                                f'Emoji "{emoji.name}" created successfully in server "{self.guild.name}"')
                        except discord.Forbidden:
                            msg = 'Setup Failed: Bot does not have permission to create custom emojis in this server!'
                            raise commands.CommandInvokeError(msg)
                        except discord.HTTPException as e:
                            msg = f'Setup Failed: {e.text}'
                            raise commands.CommandInvokeError(msg)
                        except Exception as e:
                            msg = f'Exception {e} occurred on creating custom emoji for icon "{dev_name}"'
                            raise commands.CommandInvokeError(msg)

                new_maps.append(Map(
                    display_name,
                    dev_name,
                    self.guild,
                    emoji,
                    f'<:{dev_name}:{emoji.id}>'
                ))

        new_maps = [m for m in new_maps if m not in exist_maps]
        if new_maps:
            await self.delete_maps(new_maps)
            await self.insert_maps(new_maps)

    def is_guild_setup():
        async def predicate(ctx):
            db_guild = await Guild.get_guild_by_id(ctx.guild.id)
            if not db_guild.is_setup:
                title = Utils.trans('bot-not-setup', G5.bot.command_prefix[0])
                embed = G5.bot.embed_template(title=title, color=0xFF0000)
                await ctx.message.reply(embed=embed)
                return False
            return True

        return commands.check(predicate)
