# lobby.py

from asyncpg.exceptions import UniqueViolationError
from typing import List
from collections import defaultdict

from discord.ext import commands
from discord import app_commands, Interaction, Embed, Member, VoiceState, HTTPException, VoiceChannel

from bot.helpers.db import db
from bot.helpers.models import GuildModel, LobbyModel
from bot.helpers.errors import CustomError
from bot.messages import ReadyView, MapPoolView
from bot.bot import G5Bot


CAPACITY_CHOICES = [
    app_commands.Choice(name="2 Players", value=2),
    app_commands.Choice(name="4 Players", value=4),
    app_commands.Choice(name="6 Players", value=6),
    app_commands.Choice(name="8 Players", value=8),
    app_commands.Choice(name="10 Players", value=10),
    app_commands.Choice(name="12 Players", value=12),
]

TEAM_SELECTION_CHOICES = [
    app_commands.Choice(name="Random", value="random"),
    app_commands.Choice(name="Auto balance", value="autobalance"),
    app_commands.Choice(name="Captains", value="captains"),
]

CAPTAIN_SELECTION_CHOICES = [
    app_commands.Choice(name="Random", value="random"),
    app_commands.Choice(name="Rank", value="rank"),
    app_commands.Choice(name="Volunteer", value="volunteer"),
]

MAP_SELECTION_CHOICES = [
    app_commands.Choice(name="Random", value="random"),
    app_commands.Choice(name="Veto", value="veto"),
]

AUTO_READY_CHOICES = [
    app_commands.Choice(name="ON", value=True),
    app_commands.Choice(name="OFF", value=False)
]

SERIES_CHOICES = [
    app_commands.Choice(name="Bo1", value="bo1"),
    app_commands.Choice(name="Bo2", value="bo2"),
    app_commands.Choice(name="Bo3", value="bo3")
]

GAME_MODE_CHOICES = [
    app_commands.Choice(name="Competitive", value="competitive"),
    app_commands.Choice(name="Wingman", value="wingman")
]


class JoinLobbyError(ValueError):
    """ Raised when a player can't join lobby for some reason. """

    def __init__(self, message):
        """ Set message parameter. """
        self.message = message


class LobbyCog(commands.Cog, name="Lobby"):
    """"""

    def __init__(self, bot: G5Bot):
        self.bot = bot
        self.awaiting = {}
        self.awaiting = defaultdict(lambda: False, self.awaiting)

    @app_commands.command(
        name='create-lobby',
        description='Create a new lobby.'
    )
    @app_commands.describe(
        capacity="Capacity of the lobby",
        teams_method="Teams selection method",
        captains_method="Captains selection method",
        map_method="Map selection method",
        series="Number of maps per match",
        game_mode="Set game mode"
    )
    @app_commands.choices(
        capacity=CAPACITY_CHOICES,
        teams_method=TEAM_SELECTION_CHOICES,
        captains_method=CAPTAIN_SELECTION_CHOICES,
        map_method=MAP_SELECTION_CHOICES,
        series=SERIES_CHOICES,
        game_mode=GAME_MODE_CHOICES,
        auto_ready=AUTO_READY_CHOICES
    )
    @commands.has_permissions(administrator=True)
    async def create_lobby(
        self,
        interaction: Interaction,
        capacity: app_commands.Choice[int],
        teams_method: app_commands.Choice[str],
        captains_method: app_commands.Choice[str],
        map_method: app_commands.Choice[str],
        series: app_commands.Choice[str],
        game_mode: app_commands.Choice[str],
        auto_ready: app_commands.Choice[int]
    ):
        """ Create a new lobby. """
        guild = interaction.guild
        guild_model = await db.get_guild_by_id(guild.id, self.bot)
        category = await guild.create_category(name="Lobby")
        text_channel = await guild.create_text_channel(category=category, name='Queue')
        voice_channel = await guild.create_voice_channel(
            category=category,
            name='Lobby',
            user_limit=capacity.value)

        await text_channel.set_permissions(guild.self_role, send_messages=True)
        await voice_channel.set_permissions(guild.self_role, connect=True)
        await text_channel.set_permissions(guild.default_role, send_messages=False)
        await voice_channel.set_permissions(guild.default_role, connect=False)
        await voice_channel.set_permissions(guild_model.linked_role, connect=True)

        lobby_id = await db.insert_lobby({
            'guild': guild.id,
            'capacity': capacity.value,
            'team_method': teams_method.value,
            'captain_method': captains_method.value,
            'map_method': map_method.value,
            'autoready': auto_ready.value,
            'series_type': series.value,
            'game_mode': game_mode.value,
            'category': category.id,
            'queue_channel': text_channel.id,
            'lobby_channel': voice_channel.id
        })

        await category.edit(name=f"Lobby #{lobby_id}")

        guild_maps = await db.get_guild_maps(guild)
        lobby_model = await db.get_lobby_by_id(lobby_id, self.bot)
        await db.insert_lobby_maps(lobby_id, guild_maps[:7])

        await self.update_queue_msg(lobby_model)

        embed = Embed(
            description=f"Lobby #{lobby_id} has been successfully created.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name='remove-lobby',
        description='Remove the provided lobby.'
    )
    @app_commands.describe(lobby_id="Lobby ID.")
    @commands.has_permissions(administrator=True)
    async def remove_lobby(self, interaction: Interaction, lobby_id: int):
        """"""
        guild = interaction.guild
        lobby_model = await db.get_lobby_by_id(lobby_id, self.bot)
        if not lobby_model:
            raise CustomError("Invalid Lobby ID")

        if lobby_model.guild.id != guild.id:
            raise CustomError("This lobby was not created in this server.")

        if lobby_model.text_channel and lobby_model.text_channel.id == interaction.channel.id:
            raise CustomError(
                "You can not use this command in the lobby's channel.")

        try:
            await db.delete_lobby(lobby_id)
        except Exception as e:
            self.bot.log_exception(f"Failed to remove lobby #{lobby_id}:", e)
            raise CustomError("Something went wrong! Please try again later.")

        for channel in [
            lobby_model.voice_channel,
            lobby_model.text_channel,
            lobby_model.category
        ]:
            if channel is not None:
                try:
                    await channel.delete()
                except HTTPException:
                    pass

        embed = Embed(description=f"Lobby #{lobby_model.id} has been removed.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name='modify-map-pool',
        description='Modify map pool.'
    )
    @app_commands.describe(lobby_id="Lobby ID.")
    @commands.has_permissions(administrator=True)
    async def mpool(self, interaction: Interaction, lobby_id: int):
        """"""
        guild = interaction.guild
        user = interaction.user
        lobby_model = await db.get_lobby_by_id(lobby_id, self.bot)
        if not lobby_model:
            raise CustomError("Invalid Lobby ID")

        if lobby_model.guild.id != guild.id:
            raise CustomError("This lobby was not created in this server.")

        guild_maps = await db.get_guild_maps(guild)
        lobby_maps = await db.get_lobby_maps(lobby_id)
        mpool_menu = MapPoolView(lobby_model.id, user, guild_maps, lobby_maps)
        await mpool_menu.start_mpool(interaction)

    @app_commands.command(
        name='add-custom-map',
        description='Add a custom map'
    )
    @app_commands.describe(display_name='Didsplay Name',
                           dev_name='Map name in CS:GO')
    @commands.has_permissions(administrator=True)
    async def add_custom_map(self, interaction: Interaction, display_name: str, dev_name: str):
        """"""
        map_added = await db.create_custom_guild_map(interaction.guild, display_name, dev_name)
        msg = 'Map added successfully' if map_added else 'Map already exists'
        await interaction.response.send_message(embed=Embed(description=msg))

    @commands.Cog.listener()
    async def on_voice_state_update(self, user: Member, before: VoiceState, after: VoiceState):
        """"""
        if before.channel == after.channel:
            return

        if before.channel is not None:
            lobby_model = await db.get_lobby_by_voice_channel(before.channel)
            if lobby_model and not self.awaiting[lobby_model.id]:
                self.awaiting[lobby_model.id] = True
                try:
                    await self._leave(user, lobby_model)
                except Exception as e:
                    self.bot.log_exception(
                        "Uncaght exception when handling 'cogs.lobby._leave()' method:", e)
                self.awaiting[lobby_model.id] = False

        if after.channel is not None:
            lobby_model = await db.get_lobby_by_voice_channel(after.channel)
            if lobby_model and not self.awaiting[lobby_model.id]:
                self.awaiting[lobby_model.id] = True
                try:
                    await self._join(user, lobby_model)
                except Exception as e:
                    self.bot.log_exception(
                        "Uncaught exception when handling 'cogs.lobby._join()' method:", e)
                self.awaiting[lobby_model.id] = False

    async def _leave(self, user: Member, lobby_model: LobbyModel):
        """"""
        removed = await db.delete_lobby_users(lobby_model.id, [user])
        if removed:
            title = f"User {user.display_name} removed from the lobby"
            await self.update_queue_msg(lobby_model, title)

    async def _join(self, user: Member, lobby_model: LobbyModel):
        """"""
        queued_users = await db.get_lobby_users(lobby_model.id, lobby_model.guild)
        try:
            await self.add_user_to_lobby(user, lobby_model, queued_users)
        except JoinLobbyError as e:
            title = e.message
        else:
            title = f"User **{user.display_name}** added to the queue."
            queued_users += [user]

            if len(queued_users) == lobby_model.capacity:
                guild_model = await db.get_guild_by_id(lobby_model.guild.id, self.bot)

                try:
                    queue_msg = await lobby_model.text_channel.fetch_message(lobby_model.message_id)
                    await queue_msg.delete()
                except Exception as e:
                    pass

                unreadied_users = []
                if not lobby_model.auto_ready:
                    menu = ReadyView(queued_users)
                    ready_users = await menu.ready_up(lobby_model.text_channel)
                    unreadied_users = set(queued_users) - ready_users

                if unreadied_users:
                    await db.delete_lobby_users(lobby_model.id, unreadied_users)
                    await self.move_to_channel(guild_model.prematch_channel, unreadied_users)
                else:
                    match_cog = self.bot.get_cog('Match')
                    match_msg = await lobby_model.text_channel.send(embed=Embed(description='Match Setup Process..'))
                    match_started = await match_cog.start_match(
                        queued_users,
                        lobby_model,
                        guild_model,
                        match_msg
                    )
                    if not match_started:
                        await self.move_to_channel(guild_model.prematch_channel, queued_users)

                    await db.clear_lobby_users(lobby_model.id)
                return

        await self.update_queue_msg(lobby_model, title)

    async def add_user_to_lobby(self, user: Member, lobby_model: LobbyModel, queued_users: List[Member]):
        """"""
        user_model = await db.get_user_by_discord_id(user.id, self.bot)
        match_data = await db.get_user_match(user.id, lobby_model.guild)

        if not user_model or not user_model.steam:
            raise JoinLobbyError(
                f"Unable to add **{user.display_name}**, User not linked.")
        if match_data:
            raise JoinLobbyError(
                f"Unable to add **{user.display_name}**, User in match.")
        if user in queued_users:
            raise JoinLobbyError(
                f"Unable to add **{user.display_name}**, User in lobby.")
        if len(queued_users) >= lobby_model.capacity:
            raise JoinLobbyError(
                f"Unable to add **{user.display_name}**, Lobby is full.")
        try:
            await db.insert_lobby_user(lobby_model.id, user)
        except UniqueViolationError:
            raise JoinLobbyError(
                f"Unable to add **{user.display_name}**, Please try again.")

    async def update_queue_msg(self, lobby_model: LobbyModel, title: str = None):
        """"""
        if not lobby_model.text_channel or not lobby_model.voice_channel:
            return

        queued_users = await db.get_lobby_users(lobby_model.id, lobby_model.guild)

        try:
            queue_message = await lobby_model.text_channel.fetch_message(lobby_model.message_id)
        except:
            queue_message = await lobby_model.text_channel.send(embed=Embed(description="New Queue Message"))
            await db.update_lobby_data(lobby_model.id, {'last_message': queue_message.id})

        embed = self._embed_queue(
            title, lobby_model, queued_users)
        await queue_message.edit(embed=embed)

    def _embed_queue(self, title: str, lobby_model: LobbyModel, queued_users: List[Member]):
        """"""
        embed = Embed(title=title)

        info_str = f"Game mode: *{lobby_model.game_mode.capitalize()}*\n" \
                   f"Teams method: *{lobby_model.team_method.capitalize()}*\n" \
                   f"Captains method: *{lobby_model.captain_method.capitalize()}*\n" \
                   f"Maps method: *{lobby_model.map_method.capitalize()}*\n" \
                   f"Series: *{lobby_model.series.capitalize()}*\n" \
                   f"Auto-ready: *{'ON' if lobby_model.auto_ready else 'OFF'}*"

        queued_players_str = "Lobby is empty" if not queued_users else ""
        for num, user in enumerate(queued_users, start=1):
            queued_players_str += f'{num}. {user.mention}\n'

        embed.add_field(name="**__Settings__**", value=info_str, inline=False)
        embed.add_field(
            name=f"**__Players__** `({len(queued_users)}/{lobby_model.capacity})`:",
            value=queued_players_str
        )
        embed.set_author(name=f"Lobby #{lobby_model.id}")
        return embed

    async def move_to_channel(self, channel: VoiceChannel, users: List[Member]):
        """"""
        for user in users:
            try:
                await user.move_to(channel)
            except HTTPException as e:
                self.bot.logger.warning(
                    f"Unable to move user \"{user.display_name}\" to voice channel \"{channel.name}\": {e.text}")
                pass


async def setup(bot: G5Bot):
    await bot.add_cog(LobbyCog(bot))
