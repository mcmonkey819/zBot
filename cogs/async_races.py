from nextcord.ext import commands
from db.zBot_db_orm import *
import nextcord
import logging
import re
import asyncio
import config.bot_config as bot_config
from ui.ui_elements import *


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

    ####################################################################################################################
    # Takes an AsyncRaceMessage, finds the corresponding Discord message and deletes it
    async def delete_message(self, guild_id, async_race_msg_id):
        async_race_msg = None
        if async_race_msg_id is not None:
            try:
                async_race_msg = AsyncRaceMessage.select().where(AsyncRaceMessage.id == async_race_msg_id).get()
            except:
                logging.info(f"Failed to find AsyncRaceMessage with ID {async_race_msg_id}")

        if async_race_msg is not None:
            logging.info(f"Delete message server ID is {async_race_msg.server_id}")
            guild = self.bot.get_guild(guild_id)
            channel = guild.get_channel(async_race_msg.channel_id)
            try:
                msg = await channel.fetch_message(async_race_msg.message_id)
                await msg.delete()
            except:
                logging.info(f"Failed to find message with message ID {async_race_msg.message_id}")

    ####################################################################################################################
    # Provides a list of categories as choices for a SlashOption
    async def get_category_choices(self, server_id):
        categories = AsyncRaceCategory.select().where(AsyncRaceCategory == server_id)

########################################################################################################################
# ASYNC_MOD
########################################################################################################################
# This is the main slash command that will be the prefix of all of the race moderation commands below
    @nextcord.slash_command()
    async def async_mod(self, interaction):
        pass

########################################################################################################################
# RACE COMMANDS
########################################################################################################################


########################################################################################################################
# CATEGORY COMMANDS
########################################################################################################################
    #@async_mod.subcommand(description="Adds a race category")
    #async def add_category(
    #    self,
    #    interaction,
    #    name: str = nextcord.SlashOption(description="Name of the category to be added", required=True),
    #    description: str = nextcord.SlashOption(description="Description of the category to be added",
    #                                            required=False,
    #                                            default=None)):
    #    self.log_command(interaction.user, "ADD_CATEGORY")
    #    cat = AsyncRaceCategory()
    #    cat.name = name
    #    cat.description = description
    #    cat.server_id = interaction.guild_id
    #    try:
    #        cat.save()
    #        await interaction.send(f"Added category {name} with id {cat.id}", ephemeral=True)
    #    except:
    #        await interaction.send(f"FAILED to add category {name}", ephemeral=True)
#
    #####################################################################################################################
    #@async_mod.subcommand(description="Edits an existing race category")
    #async def edit_category(
    #    self,
    #    interaction,
    #    id: int = nextcord.SlashOption(description="ID of the category to be edited", required=True),
    #    name: str = nextcord.SlashOption(description="New name of the category",
    #                                     required=False,
    #                                     default=None),
    #    description: str = nextcord.SlashOption(description="New description of the category",
    #                                            required=False,
    #                                            default=None)):
    #    self.log_command(interaction.user, "EDIT_CATEGORY")
    #    try:
    #        cat = AsyncRaceCategory.select().where(AsyncRaceCategory.id == id).get()
    #    except:
    #        cat = None
    #    if name is not None:
    #        cat.name = name
    #    if description is not None:
    #        cat.description = description
    #
    #    try:
    #        cat.save()
    #        await interaction.send(f"Successfully edited category id {cat.id}", ephemeral=True)
    #    except:
    #        await interaction.send(f"FAILED to edit category {name}", ephemeral=True)

########################################################################################################################
# STARTUP and SHUTDOWN
########################################################################################################################
    @commands.Cog.listener("on_ready")
    async def on_ready_handler(self):
        logging.info("AsyncRaces cog Ready")
        if self.test_mode:
            logging.info("  Running in test mode")
            # check_add_db_tables()
            self.execution_count = 0

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
    @async_admin.subcommand(description="Creates and pins a message with buttons for the category mod functions")
    async def create_category_mod_buttons(
        self,
        interaction,
        channel: nextcord.TextChannel = nextcord.SlashOption(
            description="Channel to post the button view in",
            required=True),
        replace : bool = nextcord.SlashOption(
            description="If a message already exists, whether it should be replaced",
            required=False,
            default=False)):

        self.log_command(interaction.user, "CREATE_CATEGORY_MOD_BUTTONS")
        server = self.get_server(interaction)
        if server is None:
            await interaction.send("Server not found", ephemeral=True)
            return

        # Just save the message ID for now, we'll delete and update the DB after we're sure the new message worked
        old_mod_message_id = server.category_mod_message
        if old_mod_message_id is not None and replace == False:
            await interaction.send("Category mod message already exists, set `replace` to True to replace", ephemeral=True)
            return

        # Construct message w/ button view
        try:
            new_mod_message = await channel.send(
                "Click below to add or edit a race category", 
                view=zCategoryModView())
        except nextcord.Forbidden:
            await interaction.send(f"Failed: Bot does not have permission for channel {channel.name}", ephemeral=True)
            return
        except:
            pass

        # Save message ID
        try:
            new_db_message = AsyncRaceMessage(
                server_id=interaction.guild_id, 
                channel_id=channel.id, 
                message_id=new_mod_message.id)
            new_db_message.save()
            await interaction.send("Successfully created category mod buttons", ephemeral=True)
        except:
            await interaction.send("Failed to create category mod buttons", ephemeral=True)
            # Since we failed to save the message info, we'll delete the message to prevent orphaning it
            await new_mod_message.delete()
            old_mod_message_id = None

        server.category_mod_message = new_db_message.id
        server.save()

        # Now remove the old message, if it exists
        await self.delete_message(interaction.guild_id, old_mod_message_id)

    ####################################################################################################################
    @async_admin.subcommand(description="Creates and pins a message with buttons for the race mod functions")
    async def create_race_mod_buttons(
        self,
        interaction,
        channel: nextcord.TextChannel = nextcord.SlashOption(
            description="Channel to post the button view in",
            required=True),
        replace : bool = nextcord.SlashOption(
            description="If a message already exists, whether it should be replaced",
            required=False,
            default=False)):

        self.log_command(interaction.user, "CREATE_RACE_MOD_BUTTONS")

        server = self.get_server(interaction)
        if server is None:
            await interaction.send("Server not found", ephemeral=True)
            return

        # Just save the message ID for now, we'll delete and update the DB after we're sure the new message worked
        old_mod_message_id = server.race_mod_message
        if old_mod_message_id is not None and replace == False:
            await interaction.send("Race mod message already exists, set `replace` to True to replace", ephemeral=True)
            return

        # Construct message w/ button view
        try:
            new_mod_message = await channel.send(
                "Click below to add or edit a races", 
                view=zRaceModView())
        except nextcord.Forbidden:
            await interaction.send(f"Failed: Bot does not have permission for channel {channel.name}", ephemeral=True)
            return
        except:
            pass

        # Save message ID
        try:
            new_db_message = AsyncRaceMessage(
                server_id=interaction.guild_id, 
                channel_id=channel.id, 
                message_id=new_mod_message.id)
            new_db_message.save()
            await interaction.send("Successfully created race mod buttons", ephemeral=True)
        except:
            await interaction.send("Failed to create race mod buttons", ephemeral=True)
            # Since we failed to save the message info, we'll delete the message to prevent orphaning it
            await new_mod_message.delete()
            old_mod_message_id = None

        server.race_mod_message = new_db_message.id
        server.save()

        # Now remove the old message, if it exists
        await self.delete_message(interaction.guild_id, old_mod_message_id)

########################################################################################################################
# ASYNC_RACE
########################################################################################################################
# This is the main slash command that will be the prefix of all of the race commands below
    @nextcord.slash_command()
    async def async_race(self, interaction):
        pass

########################################################################################################################
# ECHO_TEST
########################################################################################################################
#    @async_race.subcommand(description="Test command, simply echos the text provided with the command")
#    async def echo_test(self, interaction, message):
#        self.log_command(interaction.user, "echo_test")
#        await interaction.send(message, ephemeral=True)

########################################################################################################################
## MODAL_TESTS
#########################################################################################################################
    #@async_race.subcommand(description="Modal Test Function")
    #async def modal_test(self, interaction):
    #    self.modal_test_fields = {}
    #    self.modal_test_fields['igt'] = nextcord.ui.TextInput(label="Enter IGT in format `H:MM:SS`", required=True)
    #    self.modal_test_fields['comment'] = nextcord.ui.TextInput(label="Funny Comments", required=False)

    #    modal = zModal(self.modal_test_fields, self.modal_submit_func, "Test Modal", self)
    #    await interaction.response.send_modal(modal)

    #async def modal_submit_func(self, caller_data, modal, interaction):
    #    comment = "" if modal.fields['comment'].value is None else f" with comment {modal.fields['comment'].value}"
    #    msg = f"{interaction.user} submitted time {modal.fields['igt'].value}{comment}"
    #    await interaction.send(msg, ephemeral=True)

    @async_race.subcommand(description="Race Modal Test Function")
    async def race_modal_test(self, interaction, race_id: int = None):
        race = None
        if race_id is not None:
            try:
                race = AsyncRace.select().where(AsyncRace.id == race_id).get()
            except:
                race = None

        # If no race id is provided we will prompt for a category first
        if race is None:
            await interaction.send(view=zSingleSelectView(
                get_category_select_list(interaction.guild_id),
                self.send_race_modal,
                "Select Race Category",
                None), ephemeral=True)
        else:
            # Otherwise we can just send the modal
            await self.send_race_modal(race, race.category_id, interaction)


########################################################################################################################
# SELECT_TEST
########################################################################################################################
#    @async_race.subcommand(description="Select Test Function")
#    async def select_test(self, 
#                          interaction, 
#                          num_selections: int = nextcord.SlashOption(description="Number of selections allowed", required=True, min_value=1, max_value=3)):
#        options = []
#        options.append(nextcord.SelectOption(label="Test 1", description="First Test Value", value=1))
#        options.append(nextcord.SelectOption(label="Test 2", description="Second Test Value", value=2))
#        options.append(nextcord.SelectOption(label="Test 3", description="Third Test Value", value=3))
#
#        if num_selections > 1:
#            await interaction.send(view=zMultiSelectView(options, num_selections, self.multi_select_submit_func, self), ephemeral=True)
#        else:
#            await interaction.send(view=zSingleSelectView(options, self.select_submit_func, self), ephemeral=True)
#
#    async def select_submit_func(self, caller_data, selected_value, interaction):
#        msg = f"{interaction.user} selected value {selected_value}"
#        await interaction.send(msg, ephemeral=True)
#
#    async def multi_select_submit_func(self, caller_data, selected_values, interaction):
#        msg = f"{interaction.user} selected values: "
#        for v in selected_values:
#            msg += f"{v} "
#        await interaction.send(msg, ephemeral=True)

def setup(bot):
    bot.add_cog(AsyncRaces(bot))