from nextcord.ext import commands
from db.zBot_db_orm import *
import asyncio
import nextcord
import logging
import re
import config.bot_config as bot_config
from ui.ui_elements import *
from ui.menus import *

class AsyncRaces(commands.Cog, name='AsyncRaces'):
    '''Cog which handles commands related to Async Races.'''

    def __init__(self, bot):
        self.bot = bot
        self.test_mode = False

    def set_test_mode(self):
        self.test_mode = True

    ####################################################################################################################
    # Logs a user command
    def log_command(self, user, command):
        logging.info(f"User {user.name} ran command `{command}`")

    ####################################################################################################################
    # Gets the server object from the DB
    def get_server(self, interaction):
        try:
            server = AsyncRaceServer.select().where(AsyncRaceServer.id == interaction.guild_id).get()
        except:
            server = None
        return server

########################################################################################################################
# EVENTS
########################################################################################################################
    @commands.Cog.listener("on_ready")
    async def on_ready_handler(self):
        if self.test_mode:
            logging.info("  Running in test mode")
        logging.info("AsyncRaces cog Ready")

    ####################################################################################################################
    async def close(self):
        logging.info("Shutting down AsyncRaces cog")

########################################################################################################################
###### MOD & TEST FUNCTIONS ##################################################################################################
########################################################################################################################

########################################################################################################################
# ASYNC_ADMIN
########################################################################################################################
# This is the main slash command that will be the prefix of all of the bot admin commands below
    @nextcord.slash_command()
    async def async_admin(self, interaction):
        pass

    ####################################################################################################################
    @async_admin.subcommand(description="Creates and pins a message with buttons for server administration functions")
    async def startup(
        self,
        interaction,
        mod_channel: nextcord.TextChannel = nextcord.SlashOption(
            description="Channel that will be used for race moderation",
            required=True),
        racer_channel: nextcord.TextChannel = nextcord.SlashOption(
            description="Channel that racers will use to interact with the bot",
            required=True)):
        self.log_command(interaction.user, "STARTUP")

        await interaction.response.defer(ephemeral=True)
        mod_message = await send_moderator_menu(interaction, mod_channel)
        await mod_message.pin()
        save_message(interaction.guild_id, mod_channel.id, mod_message.id, message_type=RaceMessageType.Menu)
        
        racer_message = await send_racer_menu(interaction, racer_channel)
        await racer_message.pin()
        save_message(interaction.guild_id, racer_channel.id, racer_message.id, message_type=RaceMessageType.Menu)
        
        await send_message(interaction, "Done!", ephemeral=True)

    ####################################################################################################################
    @async_admin.subcommand(description="Cleans up menu messages in preparation for bot shutdown")
    async def shutdown(
        self,
        interaction):
        self.log_command(interaction.user, "SHUTDOWN")

        await interaction.response.defer(ephemeral=True)

        message_list = get_server_messages(interaction.guild_id)
        for m in message_list:
            await delete_message(get_server_from_interaction(interaction), m.id)
        
        await send_message(interaction, "Done!", ephemeral=True)
    
    ####################################################################################################################
    @async_admin.subcommand(description="For development purposes only, creates/recreates the specified database table")
    async def recreate_db_table(
        self,
        interaction,
        table_name: str):

        # Only allow this function in test mode
        if self.test_mode:
            if interaction.user.id != bot_config.CoolestGuy:
                await send_message(interaction, "You are not authorized to run this command", ephemeral=True)
                return

            result = recreate_table(table_name)
            if result:
                await send_message(interaction, f"Successfully recreated {table_name}")
            else:
                await send_message(interaction, f"ERROR: {table_name} not recognized")
        else:
            await send_message(interaction, "Command only available in test mode")

    ####################################################################################################################
    @async_admin.subcommand(description="Purges all messages from the specified channel")
    async def purge_channel(
        self,
        interaction,
        channel: nextcord.TextChannel = nextcord.SlashOption(
            description="Channel to purge",
            required=True)):

        if interaction.user.id != bot_config.CoolestGuy:
            await send_message(interaction, "You are not authorized to run this command", ephemeral=True)
            return

        self.log_command(interaction.user, "PURGE_CHANNEL")

        await interaction.response.defer(ephemeral=True)

        message_list = await channel.history(limit=100).flatten()
        for message in message_list:
            await message.delete()
        await send_message(interaction, "Done!", ephemeral=True)

def setup(bot):
    bot.add_cog(AsyncRaces(bot))