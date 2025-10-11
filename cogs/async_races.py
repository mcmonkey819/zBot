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

        # Check if this server is in the DB and that the user is an admin
        db_server = self.get_server(interaction)
        if db_server is None:
            if interaction.user.id == bot_config.CoolestGuy:
                # Query for the moderator and admin roles and then create a DB entry for this server
                admin_role = await prompt_for_role(interaction, placeholder="Select Race Admin Role...")
                mod_role = await prompt_for_role(interaction, placeholder="Select Race Moderator Role...")
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
                except:
                    await send_message(interaction, "**ERROR** Could not save server information")
                    return
            else:
                await send_message(interaction, "**ERROR** This server is not setup for use with this bot, please contact the bot owner")
                return

        if not user_is_admin(interaction.guild, interaction.user):
            await send_message(interaction, "Only Race Admins can use this command", ephemeral=True)
            return

        mod_message = await send_moderator_menu(interaction, mod_channel)
        save_message(interaction.guild_id, mod_channel.id, mod_message.id, message_type=RaceMessageType.Menu)
        
        racer_message = await send_racer_menu(interaction, racer_channel)
        save_message(interaction.guild_id, racer_channel.id, racer_message.id, message_type=RaceMessageType.Menu)
        
        await send_message(interaction, "Done!", ephemeral=True)
        


    ####################################################################################################################
    @async_admin.subcommand(description="Cleans up menu messages in preparation for bot shutdown")
    async def shutdown(
        self,
        interaction):
        self.log_command(interaction.user, "SHUTDOWN")

        await interaction.response.defer(ephemeral=True)

        # Check if this server is in the DB and that the user is an admin
        server = self.get_server(interaction)
        if server is not None:
            if not user_is_admin(interaction.guild, interaction.user):
                await send_message(interaction, "Only Race Admins can use this command", ephemeral=True)
                return

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

    ####################################################################################################################
    @async_admin.subcommand(description="Generate custom report")
    async def custom_report(
        self,
        interaction,
        type: int):

        server = get_server_from_interaction(interaction)
        report_name = "custom_report.csv"
        f = open(report_name, "w", encoding="utf-8")

        if type == 1:
            #role_id = await prompt_for_role(interaction)
            role_id = 1230196277279719445
            role = interaction.guild.get_role(role_id)

            column_headings = '"username", "user_id", "Race ID", "Finish Time", "Comment", "CR", "VoD"\n'
            f.write(column_headings)
            no_race_doods = ""
            
            by_race_id = False
            if by_race_id:
                racers = []
                for race_id in [367, 368, 369, 370, 371]:
                    submissions = AsyncRaceSubmission.select().where(AsyncRaceSubmission.race_id == race_id)
                    for s in submissions:
                        logging.info(f"Handling Submission ID {s.id}")
                        user = interaction.guild.get_member(s.user_id)
                        username = get_user_name_str(user.id, user) if user is not None else "Unknown"
                        user_data_str = f"{username}, {s.user_id},"
                        line_str = user_data_str + f'{s.race_id}, {s.finish_time}, "{s.comment}",'
                        try:
                            db_cr = AsyncRaceExtraInfo.select().where((AsyncRaceExtraInfo.submission_id == s.id) & (AsyncRaceExtraInfo.info_type_id == 10)).get()
                            cr = int(db_cr.data)
                        except:
                            cr = 0
                        try:
                            db_vod = AsyncRaceExtraInfo.select().where((AsyncRaceExtraInfo.submission_id == s.id) & (AsyncRaceExtraInfo.info_type_id == 11)).get()
                            vod =  db_vod.data
                        except:
                            vod = "Forfeit"
                        line_str += f"{cr}, {vod},"
                        line_str += "\n"
                        f.write(line_str)
                        if s.id not in racers:
                            racers.append(s.user_id)
                for m in role.members:
                    if m.id not in racers:
                        user = interaction.guild.get_member(m.id)
                        username = get_user_name_str(m.id, user) if user is not None else "Unknown"
                        f.write(f"{username}, {m.id},\n")
            else:
                for m in role.members:
                    username = get_user_name_str(m.id, m)
                    user_data_str = f"{username}, {m.id},"
                    submissions = AsyncRaceSubmission.select().where((AsyncRaceSubmission.race_id == 367) | (AsyncRaceSubmission.race_id == 368) | (AsyncRaceSubmission.race_id == 369) | (AsyncRaceSubmission.race_id == 370) | (AsyncRaceSubmission.race_id == 371))
                    submissions = list(filter(lambda s: s.user_id == m.id, submissions))
                    logging.info(f"Processing {len(submissions)} total submissions")
                    if submissions is not None and len(submissions) > 0:
                        for s in submissions:
                            logging.info(f"Handling Submission ID {s.id}")
                            line_str = user_data_str + f'{s.race_id}, {s.finish_time}, "{s.comment}",'
                            try:
                                db_cr = AsyncRaceExtraInfo.select().where((AsyncRaceExtraInfo.submission_id == s.id) & (AsyncRaceExtraInfo.info_type_id == 10)).get()
                                cr = int(db_cr.data)
                            except:
                                cr = 0
                            try:
                                db_vod = AsyncRaceExtraInfo.select().where((AsyncRaceExtraInfo.submission_id == s.id) & (AsyncRaceExtraInfo.info_type_id == 11)).get()
                                vod =  db_vod.data
                            except:
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
                submissions = get_sorted_race_submissions(race_id)
                par_time_seconds = calculate_par_time(submissions)
                par_time_str = finish_time_seconds_to_str(int(par_time_seconds))
                for s in submissions:
                    user = interaction.guild.get_member(s.user_id)
                    username = get_user_name_str(s.user_id, user) if user is not None else "Unknown"
                    points = (2.0 - (float(finish_time_to_seconds(s.finish_time) / par_time_seconds))) * 100.0
                    if points > 105.0:
                        points = 105.0
                    logging.info(f"Submission ID: {s.id} - {points}")
                    try:
                        db_cr = AsyncRaceExtraInfo.select().where((AsyncRaceExtraInfo.submission_id == s.id) & (AsyncRaceExtraInfo.info_type_id == 10)).get()
                        cr = int(db_cr.data)
                    except:
                        cr = 0
                    try:
                        db_vod = AsyncRaceExtraInfo.select().where((AsyncRaceExtraInfo.submission_id == s.id) & (AsyncRaceExtraInfo.info_type_id == 11)).get()
                        vod =  db_vod.data
                    except:
                        vod = "Forfeit"
                    f.write(f"{race_id}, , {username}, {s.finish_time}, {par_time_str}, {points}, {cr}, {vod}, {s.comment}\n")
        f.close()
        await send_message(interaction, "Done!")


def setup(bot):
    bot.add_cog(AsyncRaces(bot))