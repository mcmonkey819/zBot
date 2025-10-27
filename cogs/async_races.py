from nextcord.ext import commands
from db.zBot_db_orm import *
import asyncio
import nextcord
import logging
import re
import config.bot_config as bot_config
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
# ASYNC_RACE
########################################################################################################################
# This is the main slash command that will be the prefix of all of the bot slash commands below
    @nextcord.slash_command()
    async def async_race(self, interaction):
        pass

    ####################################################################################################################
    @async_race.subcommand(description="Exports a race leaderboard to a CSV file")
    async def export_race(
        self,
        interaction,
        race_id: int = nextcord.SlashOption(
            description="ID of the race to export.",
            required=True)):
        self.log_command(interaction.user, "EXPORT_RACE")

        await interaction.response.defer()

        # Determine if the user has access to this race leaderboard
        if can_view_race_leaderboard(interaction.guild, race_id, interaction.user):
            # If they do generate the CSV file and attach it to a response message
            file_path = f"./race_{race_id}.csv"
            file_created = export_race(interaction, race_id, file_path)
            if file_created:
                await interaction.send(f"Export of Race #{race_id}", file=nextcord.File(file_path))
            else:
                await interaction.send("Error exporting Race")
        else:
            await interaction.send(f"You do not have permission to view leaderboard of race #{race_id}")

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

        # Validate channel access permissions
        try:
            # Check if bot has permission to send messages in both channels
            if not mod_channel.permissions_for(interaction.guild.me).send_messages:
                await send_message(interaction, "**ERROR** Bot does not have permission to send messages in the moderator channel. Please check channel permissions.")
                return
                
            if not racer_channel.permissions_for(interaction.guild.me).send_messages:
                await send_message(interaction, "**ERROR** Bot does not have permission to send messages in the racer channel. Please check channel permissions.")
                return
                
            # Check if bot has permission to embed links (needed for rich embeds)
            if not mod_channel.permissions_for(interaction.guild.me).embed_links:
                await send_message(interaction, "**ERROR** Bot does not have permission to embed links in the moderator channel. Please check channel permissions.")
                return
                
            if not racer_channel.permissions_for(interaction.guild.me).embed_links:
                await send_message(interaction, "**ERROR** Bot does not have permission to embed links in the racer channel. Please check channel permissions.")
                return
                
            logging.info(f"Channel permission validation passed for server {interaction.guild_id}")
            
        except Exception as e:
            logging.error(f"Error validating channel permissions for server {interaction.guild_id}: {e}")
            await send_message(interaction, "**ERROR** Failed to validate channel permissions. Please try again.")
            return

        # Check if this server is in the DB and that the user is an admin
        db_server = self.get_server(interaction)
        if db_server is None:
            if interaction.user.id == bot_config.CoolestGuy:
                logging.info(f"Setting up new server {interaction.guild_id} ({interaction.guild.name})")
                # Query for the moderator and admin roles and then create a DB entry for this server
                admin_role = await prompt_for_role(interaction, placeholder="Select Race Admin Role...")
                if admin_role is None:
                    logging.warning(f"Admin role selection cancelled for server {interaction.guild_id}")
                    await send_message(interaction, "**ERROR** Admin role selection failed. Server setup cancelled.")
                    return
                    
                mod_role = await prompt_for_role(interaction, placeholder="Select Race Moderator Role...")
                if mod_role is None:
                    logging.warning(f"Moderator role selection cancelled for server {interaction.guild_id}")
                    await send_message(interaction, "**ERROR** Moderator role selection failed. Server setup cancelled.")
                    return
                    
                db_server = AsyncRaceServer()
                
                db_server.id = interaction.guild.id
                db_server.admin_role_id = admin_role
                db_server.mod_role_id = mod_role
                db_server.name = interaction.guild.name
                db_server.enable_vc_create = False
                try:
                    logging.info(f"Saving server [{db_server.id}] {db_server.name} to DB")
                    # Need to do a force insert since the primary key is the server ID which is not an auto-incrementing ID
                    db_server.save(force_insert=True)
                    logging.info(f"Successfully saved server {db_server.id} to database")
                except Exception as e:
                    logging.error(f"Failed to save server {interaction.guild_id} to database: {e}")
                    await send_message(interaction, "**ERROR** Could not save server information to database. Please try again.")
                    return
            else:
                logging.warning(f"Unauthorized startup attempt by user {interaction.user.id} on server {interaction.guild_id}")
                await send_message(interaction, "**ERROR** This server is not setup for use with this bot, please contact the bot owner")
                return

        if not user_is_admin(interaction.guild, interaction.user):
            logging.warning(f"Non-admin user {interaction.user.id} attempted startup on server {interaction.guild_id}")
            await send_message(interaction, "Only Race Admins can use this command", ephemeral=True)
            return

        # Create moderator menu
        logging.info(f"Creating moderator menu for server {interaction.guild_id} in channel {mod_channel.id}")
        mod_message = await send_moderator_menu(interaction, mod_channel)
        if mod_message is None:
            logging.error(f"Failed to create moderator menu for server {interaction.guild_id}")
            await send_message(interaction, "**ERROR** Failed to create moderator menu. Server setup incomplete.")
            return
            
        if not save_message(interaction.guild_id, mod_channel.id, mod_message.id, message_type=RaceMessageType.Menu):
            logging.error(f"Failed to save moderator menu to database for server {interaction.guild_id}")
            await send_message(interaction, "**ERROR** Failed to save moderator menu to database. Server setup incomplete.")
            return
        logging.info(f"Successfully created and saved moderator menu for server {interaction.guild_id}")
        
        # Create racer menu
        logging.info(f"Creating racer menu for server {interaction.guild_id} in channel {racer_channel.id}")
        racer_message = await send_racer_menu(interaction, racer_channel)
        if racer_message is None:
            logging.error(f"Failed to create racer menu for server {interaction.guild_id}")
            await send_message(interaction, "**ERROR** Failed to create racer menu. Server setup incomplete.")
            return
            
        if not save_message(interaction.guild_id, racer_channel.id, racer_message.id, message_type=RaceMessageType.Menu):
            logging.error(f"Failed to save racer menu to database for server {interaction.guild_id}")
            await send_message(interaction, "**ERROR** Failed to save racer menu to database. Server setup incomplete.")
            return
        logging.info(f"Successfully created and saved racer menu for server {interaction.guild_id}")
        
        # Restore pinned race states after creating admin menus
        logging.info(f"Restoring pinned race states for server {interaction.guild_id}")
        if not await self.restore_pinned_race_states(interaction):
            logging.warning(f"Some pinned race states could not be restored for server {interaction.guild_id}")
            await send_message(interaction, "**WARNING** Some pinned race states could not be restored. Check the restoration summary for details.")
        else:
            logging.info(f"Successfully restored pinned race states for server {interaction.guild_id}")
        
        # Final success message
        logging.info(f"Startup completed successfully for server {interaction.guild_id}")
        await send_message(interaction, "✅ **Server setup completed successfully!**\n\nModerator and racer menus have been created and pinned race states have been restored.")
        


    ####################################################################################################################
    @async_admin.subcommand(description="Cleans up menu messages in preparation for bot shutdown")
    async def shutdown(
        self,
        interaction):
        self.log_command(interaction.user, "SHUTDOWN")

        await interaction.response.defer(ephemeral=True)

        # Check if this server is in the DB and that the user is an admin
        server = self.get_server(interaction)
        if server is None:
            logging.error(f"Shutdown attempted on non-configured server {interaction.guild_id}")
            await send_message(interaction, "**ERROR** This server is not configured for use with this bot.", ephemeral=True)
            return
            
        if not user_is_admin(interaction.guild, interaction.user):
            logging.warning(f"Non-admin user {interaction.user.id} attempted shutdown on server {interaction.guild_id}")
            await send_message(interaction, "Only Race Admins can use this command", ephemeral=True)
            return

        # First, save pinned race states before deleting messages
        saved_count, failed_count = await self.save_pinned_race_states(interaction)
        if failed_count > 0:
            logging.warning(
                f"Shutdown: Saved {saved_count} pinned race states with "
                f"{failed_count} failures for server {interaction.guild_id}")
        
        # Then proceed with normal message cleanup
        message_list = get_server_messages(interaction.guild_id)
        deleted_count = 0
        failed_deletes = 0
        
        for m in message_list:
            result = await delete_message(get_server_from_interaction(interaction), m.id)
            if result:
                deleted_count += 1
            else:
                failed_deletes += 1
        
        if failed_deletes > 0:
            logging.warning(
                f"Shutdown: Deleted {deleted_count} messages with "
                f"{failed_deletes} failures for server {interaction.guild_id}")
            await send_message(
                interaction,
                f"**Partial cleanup completed.**\n"
                f"Saved: {saved_count} pinned states\n"
                f"Deleted: {deleted_count} messages\n"
                f"Failures: {failed_deletes}",
                ephemeral=True)
        else:
            await send_message(
                interaction,
                f"✅ **Done!**\n"
                f"Saved: {saved_count} pinned states\n"
                f"Deleted: {deleted_count} messages",
                ephemeral=True)
    
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

    ####################################################################################################################
    @async_admin.subcommand(description="Generate custom report")
    async def custom_report(
        self,
        interaction,
        type: int):
        
        self.log_command(interaction.user, "CUSTOM_REPORT")
        await interaction.response.defer(ephemeral=True)

        server = get_server_from_interaction(interaction)
        report_name = "custom_report.csv"

        try:
            with open(report_name, "w", encoding="utf-8") as f:
                if type == 1:
                    role_id = 1230196277279719445
                    
                    # Add exception handling for get_role call with validation
                    try:
                        role = interaction.guild.get_role(role_id)
                        if role is None:
                            logging.error(f"Role {role_id} not found in guild {interaction.guild_id}")
                            await send_message(
                                interaction, 
                                f"**ERROR:** Role not found. Please verify the role ID and try again.",
                                ephemeral=True)
                            return
                    except Exception as e:
                        logging.error(f"Failed to get role {role_id} from guild {interaction.guild_id}: {e}")
                        await send_message(
                            interaction, 
                            f"**ERROR:** Failed to retrieve role. Please verify the role exists and try again.",
                            ephemeral=True)
                        return

                    column_headings = '"username", "user_id", "Race ID", "Finish Time", "Comment", "CR", "VoD"\n'
                    f.write(column_headings)
                    no_race_doods = ""
                    
                    by_race_id = False
                    if by_race_id:
                        racers = []
                        for race_id in [367, 368, 369, 370, 371]:
                            try:
                                submissions = AsyncRaceSubmission.select().where(AsyncRaceSubmission.race_id == race_id)
                            except Exception as e:
                                logging.error(f"Database query failed for race_id {race_id}: {e}")
                                continue
                            
                            for s in submissions:
                                logging.info(f"Handling Submission ID {s.id}")
                                # Add exception handling for get_member calls
                                user = None
                                try:
                                    user = interaction.guild.get_member(s.user_id)
                                except Exception as e:
                                    logging.warning(f"Failed to get member {s.user_id}: {e}")
                                username = get_user_name_str(s.user_id, user) if user is not None else "Unknown"
                                user_data_str = f"{username}, {s.user_id},"
                                line_str = user_data_str + f'{s.race_id}, {s.finish_time}, "{s.comment}",'
                                try:
                                    db_cr = AsyncRaceExtraInfo.select().where((AsyncRaceExtraInfo.submission_id == s.id) & (AsyncRaceExtraInfo.info_type_id == 10)).get()
                                    cr = int(db_cr.data)
                                except Exception as e:
                                    logging.warning(f"Could not retrieve CR for submission {s.id}: {e}")
                                    cr = 0
                                try:
                                    db_vod = AsyncRaceExtraInfo.select().where((AsyncRaceExtraInfo.submission_id == s.id) & (AsyncRaceExtraInfo.info_type_id == 11)).get()
                                    vod =  db_vod.data
                                except Exception as e:
                                    logging.warning(f"Could not retrieve VoD for submission {s.id}: {e}")
                                    vod = "Forfeit"
                                line_str += f"{cr}, {vod},"
                                line_str += "\n"
                                f.write(line_str)
                                if s.id not in racers:
                                    racers.append(s.user_id)
                        
                        for m in role.members:
                            if m.id not in racers:
                                # Add exception handling for get_member calls
                                user = None
                                try:
                                    user = interaction.guild.get_member(m.id)
                                except Exception as e:
                                    logging.warning(f"Failed to get member {m.id}: {e}")
                                username = get_user_name_str(m.id, user) if user is not None else "Unknown"
                                f.write(f"{username}, {m.id},\n")
                    else:
                        for m in role.members:
                            username = get_user_name_str(m.id, m)
                            user_data_str = f"{username}, {m.id},"
                            try:
                                submissions = AsyncRaceSubmission.select().where((AsyncRaceSubmission.race_id == 367) | (AsyncRaceSubmission.race_id == 368) | (AsyncRaceSubmission.race_id == 369) | (AsyncRaceSubmission.race_id == 370) | (AsyncRaceSubmission.race_id == 371))
                                submissions = list(filter(lambda s: s.user_id == m.id, submissions))
                                logging.info(f"Processing {len(submissions)} total submissions")
                            except Exception as e:
                                logging.error(f"Database query failed when processing member {m.id}: {e}")
                                continue
                            
                            if submissions is not None and len(submissions) > 0:
                                for s in submissions:
                                    logging.info(f"Handling Submission ID {s.id}")
                                    line_str = user_data_str + f'{s.race_id}, {s.finish_time}, "{s.comment}",'
                                    try:
                                        db_cr = AsyncRaceExtraInfo.select().where((AsyncRaceExtraInfo.submission_id == s.id) & (AsyncRaceExtraInfo.info_type_id == 10)).get()
                                        cr = int(db_cr.data)
                                    except Exception as e:
                                        logging.warning(f"Could not retrieve CR for submission {s.id}: {e}")
                                        cr = 0
                                    try:
                                        db_vod = AsyncRaceExtraInfo.select().where((AsyncRaceExtraInfo.submission_id == s.id) & (AsyncRaceExtraInfo.info_type_id == 11)).get()
                                        vod =  db_vod.data
                                    except Exception as e:
                                        logging.warning(f"Could not retrieve VoD for submission {s.id}: {e}")
                                        vod = "Forfeit"
                                    line_str += f"{cr}, {vod},"
                                    line_str += "\n"
                                    f.write(line_str)
                            else:
                                no_race_doods += user_data_str + "\n"
                        f.write(no_race_doods)
                
                elif type == 2:
                    f.write("Race ID, Place, Racer Name, Finish Time, Par Time, Points, CR, VoD, Comment  \n")
                    for race_id in [367, 368, 369, 370, 371]:
                        f.write(",,,,,,\n")
                        try:
                            submissions = get_sorted_race_submissions(race_id)
                            par_time_seconds = calculate_par_time(submissions)
                            par_time_str = finish_time_seconds_to_str(int(par_time_seconds))
                        except Exception as e:
                            logging.error(f"Failed to get sorted submissions or calculate par time for race_id {race_id}: {e}")
                            continue
                        
                        for s in submissions:
                            # Add exception handling for get_member calls
                            user = None
                            try:
                                user = interaction.guild.get_member(s.user_id)
                            except Exception as e:
                                logging.warning(f"Failed to get member {s.user_id}: {e}")
                            username = get_user_name_str(s.user_id, user) if user is not None else "Unknown"
                            try:
                                points = (2.0 - (float(finish_time_to_seconds(s.finish_time) / par_time_seconds))) * 100.0
                                if points > 105.0:
                                    points = 105.0
                                logging.info(f"Submission ID: {s.id} - {points}")
                            except Exception as e:
                                logging.warning(f"Failed to calculate points for submission {s.id}: {e}")
                                points = 0
                            
                            try:
                                db_cr = AsyncRaceExtraInfo.select().where((AsyncRaceExtraInfo.submission_id == s.id) & (AsyncRaceExtraInfo.info_type_id == 10)).get()
                                cr = int(db_cr.data)
                            except Exception as e:
                                logging.warning(f"Could not retrieve CR for submission {s.id}: {e}")
                                cr = 0
                            try:
                                db_vod = AsyncRaceExtraInfo.select().where((AsyncRaceExtraInfo.submission_id == s.id) & (AsyncRaceExtraInfo.info_type_id == 11)).get()
                                vod =  db_vod.data
                            except Exception as e:
                                logging.warning(f"Could not retrieve VoD for submission {s.id}: {e}")
                                vod = "Forfeit"
                            f.write(f"{race_id}, , {username}, {s.finish_time}, {par_time_str}, {points}, {cr}, {vod}, {s.comment}\n")
            
            await send_message(interaction, "✅ Report generated successfully!")
            
        except Exception as e:
            logging.error(f"Error generating custom report: {e}")
            await send_message(
                interaction, 
                f"**ERROR:** Failed to generate report: {str(e)}. Please check logs for details.",
                ephemeral=True)

    ####################################################################################################################
    async def save_pinned_race_states(self, interaction):
        """Save pinned race states before shutdown."""
        from db.db_util import (save_pinned_race_state, clear_pinned_race_states, get_server_messages, PinType)
        
        try:
            # Clear any existing pinned states for this server
            clear_pinned_race_states(interaction.guild_id)
            logging.info(
                f"Cleared existing pinned race states for server "
                f"{interaction.guild_id}")
        except Exception as e:
            logging.error(
                f"Failed to clear existing pinned race states for server "
                f"{interaction.guild_id}: {e}")
            # Continue with the process - this is non-critical
        
        # Get all messages for this server
        message_list = get_server_messages(interaction.guild_id)
        
        saved_count = 0
        failed_count = 0
        for message in message_list:
            # Only process RaceInfo messages (pinned race info)
            if message.message_type == RaceMessageType.RaceInfo:
                try:
                    if message.race_id is not None:
                        # Individual race pin
                        save_pinned_race_state(
                            server_id=interaction.guild_id,
                            race_id=message.race_id,
                            category_id=None,
                            channel_id=message.channel_id,
                            pin_type=PinType.Individual
                        )
                        saved_count += 1
                    elif message.category_id is not None:
                        # Category pin
                        save_pinned_race_state(
                            server_id=interaction.guild_id,
                            race_id=None,
                            category_id=message.category_id,
                            channel_id=message.channel_id,
                            pin_type=PinType.Category
                        )
                        saved_count += 1
                except Exception as e:
                    failed_count += 1
                    logging.error(
                        f"Failed to save pinned race state for message "
                        f"{message.id}: {e}")
        
        logging.info(
            f"Saved {saved_count} pinned race states for server "
            f"{interaction.guild_id} (failed: {failed_count})")
        return saved_count, failed_count

    ####################################################################################################################
    async def restore_pinned_race_states(self, interaction):
        """Restore pinned race states after startup"""
        from ui.ui_util import restore_pinned_race_states
        
        # Call the restoration function from ui_util
        await restore_pinned_race_states(interaction.guild_id, interaction)


def setup(bot):
    bot.add_cog(AsyncRaces(bot))