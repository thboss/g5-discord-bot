# setup.py

from discord.ext import commands

from ..utils import Utils, DB, API
from ..resources import G5


class SetupCog(commands.Cog):
    """"""

    @commands.command(brief=Utils.trans('command-setup-brief'),
                      usage='setup <API Key>')
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx, *args):
        """"""
        try:
            api_key = args[0]
        except IndexError:
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        try:
            await API.check_auth({"user-api": api_key})
            db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)
            await db_guild.update({'api_key': f"'{api_key}'"})
            await self.prepare_server(ctx.guild, validate=True)
        except Exception as e:
            G5.bot.logger.error(str(e))
            raise commands.CommandInvokeError(str(e))

        embed = G5.bot.embed_template(title=Utils.trans('setup-bot-success'))
        await ctx.send(embed=embed)

    async def prepare_server(self, guild, validate=False):
        """"""
        if validate:
            db_guild = await DB.Guild.get_guild_by_id(guild.id)
            category = db_guild.category
            linked_role = db_guild.linked_role
            prematch_channel = db_guild.prematch_channel
            leaders_channel = db_guild.leaders_channel
            teams_channel = db_guild.teams_channel
            results_channel = db_guild.results_channel

            if not category:
                category = await guild.create_category_channel('G5')
            if not linked_role:
                linked_role = await guild.create_role(name='Linked')
            if not prematch_channel:
                prematch_channel = await guild.create_voice_channel(category=category, name='Pre-Match')
            if not leaders_channel:
                leaders_channel = await guild.create_text_channel(category=category, name='Leaderboard')
                await leaders_channel.set_permissions(guild.self_role, send_messages=True)
                await leaders_channel.set_permissions(guild.default_role, send_messages=False)
            if not teams_channel:
                teams_channel = await guild.create_text_channel(category=category, name='Teams')
                await teams_channel.set_permissions(guild.self_role, send_messages=True)
                await teams_channel.set_permissions(guild.default_role, send_messages=False)
            if not results_channel:
                results_channel = await guild.create_text_channel(category=category, name='Results')
                await results_channel.set_permissions(guild.self_role, send_messages=True)
                await results_channel.set_permissions(guild.default_role, send_messages=False)

            dict_data = {
                'category': category.id,
                'linked_role': linked_role.id,
                'prematch_channel': prematch_channel.id,
                'leaders_channel': leaders_channel.id,
                'teams_channel': teams_channel.id,
                'results_channel': results_channel.id
            }
            await db_guild.update(dict_data)
            await db_guild.create_default_maps()

        team_cog = G5.bot.get_cog('TeamCog')
        lobby_cog = G5.bot.get_cog('LobbyCog')
        await team_cog.setup_teams(guild)
        await lobby_cog.setup_lobbies(guild)

    @ commands.command(brief=Utils.trans('add-map-command-brief'),
                       usage='add-map <display_name> <custom_emoji>',
                       aliases=['add-map', 'addmap'])
    @ commands.has_permissions(administrator=True)
    @ DB.Guild.is_guild_setup()
    async def add_map(self, ctx, *args):
        """"""
        try:
            display_name = args[0]
            emoji_id = int(args[1].split(':')[2].strip('>'))
        except Exception:
            raise commands.CommandInvokeError(Utils.trans(
                'invalid-usage', G5.bot.command_prefix[0], ctx.command.usage))

        db_guild = await DB.Guild.get_guild_by_id(ctx.guild.id)
        emoji = await ctx.guild.fetch_emoji(emoji_id)
        map_added = await db_guild.create_custom_map(display_name, emoji)
        if not map_added:
            raise commands.CommandInvokeError(
                Utils.trans('map-already-exist', display_name))

        title = Utils.trans('map-added-successfully', display_name)
        embed = G5.bot.embed_template(title=title)
        await ctx.send(embed=embed)
