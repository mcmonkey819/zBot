from nextcord.ext import commands
from db.zBot_db_orm import *
import nextcord
import logging
import re
import asyncio
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

    ####################################################################################################################
    # Provides a list of categories as choices for a SlashOption
    async def get_category_choices(self, server_id):
        categories = AsyncRaceCategory.select().where(AsyncRaceCategory == server_id)

    ####################################################################################################################
    async def send_server_mod_message(self, channel):
        return await channel.send("> \n> Click below to add or edit a race category", view=zServerAdminView())

    ####################################################################################################################
    async def send_category_mod_message(self, channel):
        return await channel.send("> \n> Click below to add or edit a race category", view=zCategoryModView())

    ####################################################################################################################
    async def send_race_mod_message(self, channel):
        return await channel.send("> \n> Click below to add or edit a races", view=zRaceModView())

    ####################################################################################################################
    async def send_racer_info_message(self, channel):
        return await channel.send("> \n> Click below to see available races or check your stats", view=zRacerButtonView())

    #####################################################################################################################
    async def get_nextcord_server(self, server_id):
        return await self.bot.fetch_guild(server_id)

    ####################################################################################################################
    # Called on shut down, deletes the messages posted by the bot for race and category moderation
    async def cleanup_server_bot_messages(self, guild):
        server = get_server(guild.id)
        if server is not None:
            # Clean up the server mod message
            if server.server_mod_message is not None:
                await delete_message(guild, server.server_mod_message, True)
            
            # And the category mod message
            if server.category_mod_message is not None:
                await delete_message(guild, server.category_mod_message, True)

            # And the race mod message
            if server.race_mod_message is not None:
                await delete_message(guild, server.race_mod_message, True)

            # And the racer info message
            if server.racer_info_message is not None:
                await delete_message(guild, server.racer_info_message, True)

            # And finally any pinned races
            try:
                race_list = AsyncRace.select().where(AsyncRace.server_id == server.id)
            except:
                race_list = []
            for r in race_list:
                if r.race_info_message is not None and r.race_info_message != 0:
                    await delete_message(guild, r.race_info_message, True)

    ####################################################################################################################
    async def recreate_button_view(self, guild, db_msg_id, message_type: MessageType):
        err = False
        if db_msg_id is not None:
            db_msg = get_race_message(db_msg_id)
            if db_msg is not None:
                channel = guild.get_channel(db_msg.channel_id)
                if channel is not None:
                    if await has_text_channel_permission(self.bot.user.id, guild, channel):
                        match message_type:
                            case MessageType.CATEGORY_MOD:
                                new_msg = await self.send_category_mod_message(channel)
                            case MessageType.RACE_MOD:
                                new_msg = await self.send_race_mod_message(channel)
                            case MessageType.RACER_INFO:
                                new_msg = await self.send_racer_info_message(channel)
                            case MessageType.SERVER_MOD:
                                new_msg = await self.send_server_mod_message(channel)
                            case _:
                                logging.info(f"Error: unrecognized MessageType: {message_type}")
                                err = True
                        db_msg.message_id = new_msg.id
                        db_msg.save()
                else:
                    # We can't find the channel or no longer have permissions, so we can't create a new message. Instead
                    # remove the DB entry
                    logging.info(f"Can't recreate mod message in server ID {guild.id} channel ID {db_msg.channel_id}")
                    db_msg.delete_instance()
                    err = True
            else:
                err = True

        if err:
            match message_type:
                case MessageType.CATEGORY_MOD:
                    server.category_mod_message = None
                case MessageType.RACE_MOD:
                    server.race_mod_message = None
                case MessageType.RACER_INFO:
                    server.racer_info_message = None
                case MessageType.SERVER_MOD:
                    server.server_mod_message = None
            server.save()

    ####################################################################################################################
    async def recreate_race_info_message(self, guild, race):
        err = False
        if race is not None and race.race_info_message is not None:
            db_msg = get_race_message(race.race_info_message)
            if db_msg is not None:
                channel = guild.get_channel(db_msg.channel_id)
                if channel is not None:
                    if await has_text_channel_permission(self.bot.user.id, guild, channel):
                        new_msg = await post_race_info_message(race, channel)
                        db_msg.message_id = new_msg.id
                        db_msg.save()
                else:
                    # We can't find the channel or no longer have permissions, so we can't create a new message. Instead
                    # remove the DB entry
                    logging.info(f"Can't recreate race info message in server ID {guild.id} channel ID {db_msg.channel_id}")
                    db_msg.delete_instance()
                    err = True
            else:
                err = True

            if err:
                race.race_info_message = None
                race.save()

    ####################################################################################################################
    # Called on start up, recreates the messages posted by the bot for race and category moderation
    async def recreate_server_bot_messages(self, guild):
        server = get_server(guild.id)
        if server is not None:
            # Try to recreate the server mod message
            await self.recreate_button_view(guild, server.server_mod_message, MessageType.SERVER_MOD)

            # And then the category mod message
            await self.recreate_button_view(guild, server.category_mod_message, MessageType.CATEGORY_MOD)

            # And then the race mod message
            await self.recreate_button_view(guild, server.race_mod_message, MessageType.RACE_MOD)

            # And the racer info message
            await self.recreate_button_view(guild, server.racer_info_message, MessageType.RACER_INFO)

            # And finally any pinned races
            try:
                race_list = AsyncRace.select().where(AsyncRace.server_id == guild.id)
            except:
                race_list = []
            for race in race_list:
                if race.race_info_message is not None and race.race_info_message != 0:
                    await self.recreate_race_info_message(guild, race)

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
    #        await send_message(interaction, f"Added category {name} with id {cat.id}")
    #    except:
    #        await send_message(interaction, f"FAILED to add category {name}")
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
    #        await send_message(interaction, f"Successfully edited category id {cat.id}")
    #    except:
    #        await send_message(interaction, f"FAILED to edit category {name}")

########################################################################################################################
# EVENTS
########################################################################################################################
    @commands.Cog.listener("on_ready")
    async def on_ready_handler(self):
        if self.test_mode:
            logging.info("  Running in test mode")
        logging.info("AsyncRaces cog Ready")

    ####################################################################################################################
    @commands.Cog.listener("on_guild_available")
    async def on_guild_available_handler(self, guild):
        await self.recreate_server_bot_messages(guild)

    ####################################################################################################################
    @commands.Cog.listener("on_guild_unavailable")
    async def on_guild_unavailable_handler(self, guild):
        await self.cleanup_server_bot_messages(guild)

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
    async def create_server_admin_buttons(
        self,
        interaction,
        channel: nextcord.TextChannel = nextcord.SlashOption(
            description="Channel to post the button view in",
            required=True),
        replace : bool = nextcord.SlashOption(
            description="If a message already exists, whether it should be replaced",
            required=False,
            default=False)):

        self.log_command(interaction.user, "CREATE_SERVER_ADMIN_BUTTONS")

        if await check_user_is_admin(interaction) == False:
            return

        db_server = self.get_server(interaction)
        if db_server is None:
            await send_message(interaction, "Server not found")
            return

        # Just save the message ID for now, we'll delete and update the DB after we're sure the new message worked
        old_mod_message_id = db_server.server_mod_message
        if old_mod_message_id is not None and replace == False:
            await send_message(interaction, "Server admin message already exists, set `replace` to True to replace")
            return

        # Check if the bot has permission in the chosen channel
        server = get_server_from_interaction(interaction)
        has_permission = await has_text_channel_permission(self.bot.user.id, server, channel)
        if has_permission == False:
            await send_message(interaction, f"Failed: Bot does not have permission for channel {channel.name}")
            return

        # Construct message w/ button view
        new_mod_message = await self.send_server_mod_message(channel)

        # Save message ID
        try:
            new_db_message = AsyncRaceMessage(
                server_id=interaction.guild_id, 
                channel_id=channel.id, 
                message_id=new_mod_message.id)
            new_db_message.save()
            await send_message(interaction, "Successfully created server admin buttons")
        except:
            await send_message(interaction, "Failed to create server admin buttons")
            # Since we failed to save the message info, we'll delete the message to prevent orphaning it
            await new_mod_message.delete()
            old_mod_message_id = None

        db_server.server_mod_message = new_db_message.id
        db_server.save()

        # Now remove the old message, if it exists
        await delete_message(server, old_mod_message_id)

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

        if await check_user_is_admin(interaction) == False:
            return

        db_server = self.get_server(interaction)
        if db_server is None:
            await send_message(interaction, "Server not found")
            return

        # Just save the message ID for now, we'll delete and update the DB after we're sure the new message worked
        old_mod_message_id = db_server.category_mod_message
        if old_mod_message_id is not None and replace == False:
            await send_message(interaction, "Category mod message already exists, set `replace` to True to replace")
            return

        # Check if the bot has permission in the chosen channel
        server = get_server_from_interaction(interaction)
        has_permission = await has_text_channel_permission(self.bot.user.id, server, channel)
        if has_permission == False:
            await send_message(interaction, f"Failed: Bot does not have permission for channel {channel.name}")
            return

        # Construct message w/ button view
        new_mod_message = await self.send_category_mod_message(channel)

        # Save message ID
        try:
            new_db_message = AsyncRaceMessage(
                server_id=interaction.guild_id, 
                channel_id=channel.id, 
                message_id=new_mod_message.id)
            new_db_message.save()
            await send_message(interaction, "Successfully created category mod buttons")
        except:
            await send_message(interaction, "Failed to create category mod buttons")
            # Since we failed to save the message info, we'll delete the message to prevent orphaning it
            await new_mod_message.delete()
            old_mod_message_id = None

        db_server.category_mod_message = new_db_message.id
        db_server.save()

        # Now remove the old message, if it exists
        await delete_message(server, old_mod_message_id)

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

        if await check_user_is_admin(interaction) == False:
            return

        db_server = self.get_server(interaction)
        if db_server is None:
            await send_message(interaction, "Server not found")
            return

        # Just save the message ID for now, we'll delete and update the DB after we're sure the new message worked
        old_mod_message_id = db_server.race_mod_message
        if old_mod_message_id is not None and replace == False:
            await send_message(interaction, "Race mod message already exists, set `replace` to True to replace")
            return

        # Check if the bot has permission in the chosen channel
        server = get_server_from_interaction(interaction)
        has_permission = await has_text_channel_permission(self.bot.user.id, server, channel)
        if has_permission == False:
            await send_message(interaction, f"Failed: Bot does not have permission for channel {channel.name}")
            return

        # Construct message w/ button view
        new_mod_message = await self.send_race_mod_message(channel)

        # Save message ID
        try:
            new_db_message = AsyncRaceMessage(
                server_id=interaction.guild_id, 
                channel_id=channel.id, 
                message_id=new_mod_message.id)
            new_db_message.save()
            await send_message(interaction, "Successfully created race mod buttons")
        except:
            await send_message(interaction, "Failed to create race mod buttons")
            # Since we failed to save the message info, we'll delete the message to prevent orphaning it
            await new_mod_message.delete()
            old_mod_message_id = None

        db_server.race_mod_message = new_db_message.id
        db_server.save()

        # Now remove the old message, if it exists
        await delete_message(server, old_mod_message_id)

    ####################################################################################################################
    @async_admin.subcommand(description="Creates and pins a message with buttons for the racer info functions")
    async def create_racer_info_buttons(
        self,
        interaction,
        channel: nextcord.TextChannel = nextcord.SlashOption(
            description="Channel to post the button view in",
            required=True),
        replace : bool = nextcord.SlashOption(
            description="If a message already exists, whether it should be replaced",
            required=False,
            default=False)):

        self.log_command(interaction.user, "CREATE_RACER_INFO_BUTTONS")

        if await check_user_is_admin(interaction) == False:
            return

        db_server = self.get_server(interaction)
        if db_server is None:
            await send_message(interaction, "Server not found")
            return

        # Just save the message ID for now, we'll delete and update the DB after we're sure the new message worked
        old_message_id = db_server.racer_info_message
        if old_message_id is not None and replace == False:
            await send_message(interaction, "Racer info message already exists, set `replace` to True to replace")
            return

        # Check if the bot has permission in the chosen channel
        server = get_server_from_interaction(interaction)
        has_permission = await has_text_channel_permission(self.bot.user.id, server, channel)
        if has_permission == False:
            await send_message(interaction, f"Failed: Bot does not have permission for channel {channel.name}")
            return

        # Construct message w/ button view
        new_message = await self.send_racer_info_message(channel)

        # Save message ID
        try:
            new_db_message = AsyncRaceMessage(
                server_id=interaction.guild_id, 
                channel_id=channel.id, 
                message_id=new_message.id)
            new_db_message.save()
            await send_message(interaction, "Successfully created racer info buttons")
        except:
            await send_message(interaction, "Failed to create racer info buttons")
            # Since we failed to save the message info, we'll delete the message to prevent orphaning it
            await new_message.delete()
            old_message_id = None

        db_server.racer_info_message = new_db_message.id
        db_server.save()

        # Now remove the old message, if it exists
        await delete_message(server, old_message_id)

    ####################################################################################################################
    @async_admin.subcommand(description="Cleans up bot created messages: race info, category and race moderation")
    async def cleanup_bot_messages(self,
        interaction,
        cleanup_all : bool = nextcord.SlashOption(
            description="Whether to cleanup all servers or just the one this command is run from",
            required=False,
            default=False)):

        self.log_command(interaction.user, "CLEANUP_BOT_MESSAGES")

        if await check_user_is_admin(interaction) == False:
            return

        if cleanup_all:
            # Only the bot owner is allowed to purge all
            if interaction.user.id == CoolestGuy:
                server_list = AsyncRaceServer.select()
                for s in server_list:
                    guild = await self.get_nextcord_server(s.id)
                    if guild is not None:
                        await self.cleanup_server_bot_messages(guild)
            else:
                await send_message(interaction, "Only the bot owner is allowed to cleanup all servers")
        else:
            await self.cleanup_server_bot_messages(interaction.guild)
            await send_message(interaction, "Done!")

    ####################################################################################################################
    @async_admin.subcommand(description="For development purposes only, creates/recreates the specified database table")
    async def recreate_db_table(
        self,
        interaction,
        table_name: str):

        # Only allow this function in test mode for now
        if self.test_mode:
            result = recreate_table(table_name)
            if result:
                await send_message(interaction, f"Successfully recreated {table_name}")
            else:
                await send_message(interaction, f"ERROR: {table_name} not recognized")
        else:
            await send_message(interaction, "Command only available in test mode")

    ####################################################################################################################
    @async_admin.subcommand(description="Menu test")
    async def test_menu(
        self,
        interaction,
        type: int = nextcord.SlashOption(required=False, default=0, choices={"Category": 0, "Race": 1}),
        id: int = 0):
        
        if type == 0:
            await send_category_menu(interaction, 10 if id == 0 else id)
        elif type == 1:
            await send_race_menu(interaction, 466 if id == 0 else id)

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
#        await send_message(interaction, message)

########################################################################################################################
## MODAL_TESTS
#########################################################################################################################
    #@async_race.subcommand(description="Modal Test Function")
    #async def modal_test(self, interaction):
    #    self.modal_test_fields = {}
    #    self.modal_test_fields['igt'] = nextcord.ui.TextInput(label="Enter IGT in format `H:MM:SS`", required=True)
    #    self.modal_test_fields['comment'] = nextcord.ui.TextInput(label="Funny Comments", required=False)

    #    modal = zModal(self.modal_test_fields, self.modal_submit_func, "Test Modal")
    #    await interaction.response.send_modal(modal)

    #async def modal_submit_func(self, modal, interaction):
    #    comment = "" if modal.fields['comment'].value is None else f" with comment {modal.fields['comment'].value}"
    #    msg = f"{interaction.user} submitted time {modal.fields['igt'].value}{comment}"
    #    await send_message(interaction, msg)

    #@async_race.subcommand(description="Multi-Page Modal Test Function")
    #async def multi_page_modal_test(self, interaction):
    #    self.multi_page_modal_test_fields = [
    #        zField('igt',         "Enter IGT in format `H:MM:SS`", None,   True),
    #        zField('comment',     "Funny Comments",                "KEKW", False),
    #        zField('vod_link',    "VoD",                           None,   False),
    #        zField('death_count', "# of Deaths",                   69,     False),
    #        zField('bonks',       "# of Bonks",                    216,    True),
    #        zField('route',       "Route Description",             None,   False),
    #    ]

    #    modal_sender = zMultiPageModalSender()
    #    await modal_sender.send_modal(interaction,
    #                                  self.multi_page_modal_test_fields,
    #                                  self.multi_page_modal_test_fields_submit_func,
    #                                  "Multi-Page Test Modal")

    #async def multi_page_modal_test_fields_submit_func(self, interaction, submitted_values):
    #    if submitted_values is None:
    #        msg = "User Cancelled"
    #    else:
    #        msg = "Submitted Values: \n"
    #        for i, v in enumerate(submitted_values):
    #            msg += f"\n  {self.multi_page_modal_test_fields[i].name}: {v}"
    #    await send_message(interaction, msg)

    ########################################################################################################################
    #@async_race.subcommand(description="Race Modal Test Function")
    #async def race_modal_test(self, interaction, race_id: int = None):
    #    race = None
    #    if race_id is not None:
    #        try:
    #            race = AsyncRace.select().where(AsyncRace.id == race_id).get()
    #        except:
    #            race = None
#
    #    # If no race id is provided we will prompt for a category first
    #    if race is None:
    #        await send_message(interaction, view=zSingleSelectView(
    #            get_category_select_list(interaction.guild_id),
    #            self.send_race_modal,
    #            "Select Race Category"))
    #    else:
    #        # Otherwise we can just send the modal
    #        await self.send_race_modal(race, race.category_id, interaction)

    ########################################################################################################################
    @async_race.subcommand(description="Race Submission Modal Test Function")
    async def race_submit_modal_test(self, interaction, submission_id: int = None):
        submission = None
        if submission_id is not None:
            try:
                submission = AsyncRaceSubmission.select().where(AsyncRaceSubmission.id == submission_id).get()
            except:
                submission = None

        # If no race id is provided we will prompt for a race first
        if submission is None:
            await interaction.send(
                view=zSingleSelectView(get_race_select_list(interaction.guild_id),
                                       self.send_submit_modal,
                                       "Select Race"), ephemeral=True)
        else:
            # Otherwise we can just send the modal
            await self.send_submit_modal(submission, submission.race_id, interaction)

    async def send_submit_modal(self, submission, race_id, interaction):
        await interaction.response.send_modal(zRaceSubmissionModal(race_id, submission))


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
#            await interaction.send(view=zMultiSelectView(options, num_selections, self.multi_select_submit_func))
#        else:
#            await interaction.send(view=zSingleSelectView(options, self.select_submit_func))
#
#    async def select_submit_func(self, selected_value, interaction):
#        msg = f"{interaction.user} selected value {selected_value}"
#        await send_message(interaction, msg)
#
#    async def multi_select_submit_func(self, selected_values, interaction):
#        msg = f"{interaction.user} selected values: "
#        for v in selected_values:
#            msg += f"{v} "
#        await send_message(interaction, msg)

#    @async_race.subcommand(description="User Select Test Function")
#    async def user_select_test(self, 
#                               interaction):
#        await interaction.send(view=zUserSelectView(self.user_select_submit_func, placeholder="Pick a name, any name..."), ephemeral=True)
#
#    async def user_select_submit_func(self, selected_value, interaction):
#        if selected_value is not None and len(selected_values) > 0:
#            msg = f"{interaction.user} selected member {selected_value.name} also known as {selected_value.nick}"
#        else:
#            msg = "No user selected"
#        await send_message(interaction, msg)

def setup(bot):
    bot.add_cog(AsyncRaces(bot))