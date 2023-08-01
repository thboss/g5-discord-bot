# team.py

from discord.ext import commands
from discord import app_commands, Interaction, Embed, SelectOption
from discord.interactions import Interaction


from bot.helpers.errors import CustomError
from bot.helpers.db import db
from bot.helpers.api import api
from bot.views import ConfirmView, DropDownView


class TeamCog(commands.Cog, name="Team"):
    """"""

    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="create-team", description="Create a new team")
    @app_commands.describe(name="Team name")
    async def create_team(self, interaction: Interaction, name: str):
        """"""
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild
        team_name = name[:25]

        user_model = await db.get_user_by_discord_id(user.id, self.bot)
        if not user_model or not user_model.steam:
            raise CustomError(f"You must be linked to create a team.")

        user_team = await db.get_user_team(user.id, guild)
        if user_team:
            raise CustomError(f"You already belong to team **{user_team.name}**")
        
        dict_user = { user_model.steam: {
            'nickname': user.display_name,
            'captain': True
        }}
        team_id = await api.create_team(team_name, dict_user)

        team_role = await guild.create_role(name="team_" + team_name)

        await db.insert_team({
            'id': team_id,
            'name': f'\'{team_name}\'',
            'guild': guild.id,
            'role': team_role.id,
            'captain': user.id
        })
        await db.insert_team_users(team_id, [user])
        await user.add_roles(team_role)

        embed = Embed(description=f"Team **{team_name}** created successfully")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="join-team", description="Join a team")
    @app_commands.checks.cooldown(1, 300)
    async def join_team(self, interaction: Interaction):
        """"""
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild
        embed = Embed()

        user_model = await db.get_user_by_discord_id(user.id, self.bot)
        if not user_model or not user_model.steam:
            raise CustomError(f"You must be linked to join a team.")
        
        user_team = await db.get_user_team(user.id, guild)
        if user_team:
            raise CustomError(f"You already in team **{user_team.name}**")
        
        guild_teams = await db.get_guild_teams(guild)
        if not guild_teams:
            raise CustomError("No teams found in the server.")
    
        placeholder = "Choose a team"
        options = [SelectOption(label=f"Team {team.name}", value=team.id) for team in guild_teams]
        dropdown = DropDownView(user, placeholder, options, 1, 1)
        message = await interaction.followup.send(view=dropdown, wait=True)
        await dropdown.wait()

        if not dropdown.selected_options:
            embed.description = f"Timeout! haven't selected team in time."
            await message.edit(embed=embed, view=None)
            return

        team_model = await db.get_team_by_id(int(dropdown.selected_options[0]), self.bot)
        if not team_model:
            embed.description = "Team not found!"
            await message.edit(embed=embed, view=None)
            return

        team_users = await db.get_team_users(team_model.id, guild)
        if len(team_users) > 5:
            embed.description = "Team **{}** is full!"
            await message.edit(embed=embed, view=None)
            return

        embed.description = f"User {user.mention} wants to join your team **{team_model.name}**"
        confirm_view = ConfirmView(team_model.captain)
        mention_msg = await interaction.channel.send(content=team_model.captain.mention)
        await message.edit(embed=embed, view=confirm_view)
        await confirm_view.wait()
        await mention_msg.delete()

        if confirm_view.accepted is None:
            embed.description = "Timeout! The join request was not accepted."
        elif confirm_view.accepted:
            user_model = await db.get_user_by_discord_id(user.id, self.bot)
            if not user_model or not user_model.steam:
                embed.description = "You must be linked to join a team."
                await message.edit(embed=embed, view=None)
                return
            
            user_team = await db.get_user_team(user.id, guild)
            if user_team:
                embed.description = f"You already in team **{user_team.name}**"
                await message.edit(embed=embed, view=None)
                return
            
            team_model = await db.get_team_by_id(int(dropdown.selected_options[0]), self.bot)
            if not team_model:
                embed.description = "Team not found!"
                await message.edit(embed=embed, view=None)
                return
            
            team_users = await db.get_team_users(team_model.id, guild)
            if len(team_users) > 5:
                embed.description = f"Team **{team_model.name}** is full!"
                await message.edit(embed=embed, view=None)
                return

            added = await api.add_team_member(team_model.id, user_model.steam, user.display_name)
            if added:
                await db.insert_team_users(team_model.id, [user])
                try:
                    await user.add_roles(team_model.role)
                except: pass
                embed.description = f"{user.mention} You have joined team **{team_model.name}**."
            else:
                embed.description = "Something went wrong in API call. Please try again later."
        else:
            embed.description = "Join team request rejected. Maybe next time!"

        await message.edit(embed=embed, view=None)
    
    @app_commands.command(name="leave-team", description="Leave your team")
    async def leave_team(self, interaction: Interaction):
        """"""
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild
        embed = Embed()

        user_team = await db.get_user_team(user.id, guild)
        if not user_team:
            raise CustomError("You are not belong to any team.")
        
        team_match = await db.get_team_match(user_team.id, guild)
        if team_match:
            raise CustomError(f"You cannot leave right now. Your team **{user_team.name}** belongs to match **#{team_match.id}**")
        
        user_model = await db.get_user_by_discord_id(user.id, self.bot)
        removed = await api.remove_team_member(user_team.id, user_model.steam)
        if removed:
            await db.delete_team_users(user_team.id, [user])
            try:
                await user.remove_roles(user_team.role)
            except: pass
            if user_team.captain:
                embed.description = f"User {user.mention} just left your team **{user_team.name}**"
                await interaction.channel.send(content=user_team.captain.mention, embed=embed)
            embed.description = f"You have been removed from team **{user_team.name}**."
        else:
            embed.description = "Something went wrong in API call. Please try again later."

        await interaction.followup.send(embed=embed, view=None)

    @app_commands.command(name="kick-teammate", description="Kick a user from your team")
    async def kick_teammate(self, interaction: Interaction):
        """"""
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild
        embed = Embed()

        team_model = await db.get_user_team(user.id, guild)
        if not team_model or team_model.captain != user:
            raise CustomError("Only team captains can access this!")
        
        team_users = await db.get_team_users(team_model.id, guild)
        team_users = [u for u in team_users if u != user]

        if not team_users:
            raise CustomError("Your team is empty!")

        placeholder = "Choose players to be kicked from your team"
        options = [SelectOption(label=user.display_name, value=user.id) for user in team_users]
        dropdown = DropDownView(user, placeholder, options, 1, len(team_users))
        message = await interaction.followup.send(view=dropdown, wait=True)
        await dropdown.wait()

        if not dropdown.selected_options:
            embed.description = f"Timeout! haven't selected players in time."
            await message.edit(embed=embed, view=None)
            return
        
        team_match = await db.get_team_match(team_model.id, guild)
        if team_match:
            embed.description = f"Unable to kick your team players while your team belongs to live match **#{team_match.id}**"
            await message.edit(embed=embed, view=None)
            return
        
        users_to_kick = list(filter(lambda x: str(x.id) in dropdown.selected_options, team_users))
        kicked_users = []
        users_model = await db.get_users(users_to_kick)
        for usr in users_model:
            try:
                deleted = await api.remove_team_member(team_model.id, usr.steam)
                if deleted:
                    await db.delete_team_users(team_model.id, [usr.user])
                    kicked_users.append(usr.user)
                    await usr.user.remove_roles(team_model.role)
            except Exception as e:
                self.bot.log_exception("Error: ", e)

        mention_users = ', '.join(u.mention for u in kicked_users)
        if kicked_users:
            await interaction.channel.send(mention_users)
            embed.description = f"Players {mention_users} have been kicked from team **{team_model.name}**"
        else:
            embed.description = "Something went wrong in API call. Please try again later."

        await message.edit(embed=embed, view=None)

    @app_commands.command(name="delete-team", description="Delete your team")
    async def delete_team(self, interaction: Interaction):
        """"""
        await interaction.response.defer()
        user = interaction.user
        guild = interaction.guild
        embed = Embed()

        user_team = await db.get_user_team(user.id, guild)
        if not user_team or user_team.captain != user:
            raise CustomError("Only team captains can access this!")
        
        embed.description = f"Are you sure you want to delete your team **{user_team.name}**?"
        confirm = ConfirmView(user)
        message = await interaction.followup.send(embed=embed, view=confirm, wait=True)
        await confirm.wait()

        if confirm.accepted is None:
            embed.description = "Timeout! You haven't decided in time."
        elif confirm.accepted:
            team_match = await db.get_team_match(user_team.id, guild)
            if team_match:
                embed.description = f"Unable to delete your team while it belongs to live match **#{team_match.id}**"
                await message.edit(embed=embed, view=None)
                return

            team_users = await db.get_team_users(user_team.id, guild)
            status_code = await api.delete_team(user_team.id)
            if status_code < 400 or status_code == 404:
                await db.delete_team(user_team.id, guild)
                try:
                    await user_team.role.delete()
                except: pass
                embed.description = f"Your team **{user_team.name}** has been deleted."
                teammate_mentions = ''.join(u.mention for u in team_users)
                await interaction.channel.send(teammate_mentions)
            else:
                embed.description = "Something went wrong in API call. Please try again later."
        else:
            embed.description = "Delete team cancelled."
        
        await message.edit(embed=embed, view=None)


async def setup(bot):
    await bot.add_cog(TeamCog(bot))