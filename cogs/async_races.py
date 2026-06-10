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
            description="Channel for race moderation (overrides saved state; required for first-time setup)",
            required=False,
            default=None),
        racer_channel: nextcord.TextChannel = nextcord.SlashOption(
            description="Channel for racers to interact with the bot (overrides saved state; required for first-time setup)",
            required=False,
            default=None)):
        self.log_command(interaction.user, "STARTUP")

        await interaction.response.defer(ephemeral=True)

        # Check if this server is in the DB and that the user is an admin
        server = self.get_server(interaction)
        if server is None:
            if interaction.user.id == bot_config.CoolestGuy:
                admin_role = await prompt_for_role(interaction, placeholder="Select Race Admin Role...")
                mod_role = await prompt_for_role(interaction, placeholder="Select Race Moderator Role...")
                server = AsyncRaceServer(id=interaction.guild_id, admin_role=admin_role, mod_role=mod_role)
                try:
                    server.save()
                except:
                    await send_message(interaction, "**ERROR** Could not save server information")
                    return
            else:
                await send_message(interaction, "**ERROR** This server is not setup for use with this bot, please contact the bot owner")
                return

        if not user_is_admin(interaction.guild, interaction.user):
            await send_message(interaction, "Only Race Admins can use this command", ephemeral=True)
            return

        restore_rows = get_restore_state(interaction.guild_id)
        discord_server = get_server_from_interaction(interaction)

        if not restore_rows and not mod_channel and not racer_channel:
            await send_message(interaction, "Nothing to restore. Provide mod_channel and racer_channel for fresh setup.", ephemeral=True)
            return

        # Remove restore entries overridden by explicit channel params
        if restore_rows and mod_channel:
            restore_rows = [r for r in restore_rows if r.message_type != RaceMessageType.ModMenu]
        if restore_rows and racer_channel:
            restore_rows = [r for r in restore_rows if r.message_type != RaceMessageType.RacerMenu]

        # Build summary counts across both restore rows and explicit channel overrides
        leaderboard_count = sum(1 for r in restore_rows if r.message_type == RaceMessageType.Leaderboard)
        race_info_count   = sum(1 for r in restore_rows if r.message_type == RaceMessageType.RaceInfo)
        mod_menu_count    = sum(1 for r in restore_rows if r.message_type == RaceMessageType.ModMenu) + (1 if mod_channel else 0)
        racer_menu_count  = sum(1 for r in restore_rows if r.message_type == RaceMessageType.RacerMenu) + (1 if racer_channel else 0)
        total = leaderboard_count + race_info_count + mod_menu_count + racer_menu_count

        parts = []
        if leaderboard_count: parts.append(f"{leaderboard_count} category leaderboard(s)")
        if race_info_count:   parts.append(f"{race_info_count} pinned race info message(s)")
        if mod_menu_count:    parts.append(f"{mod_menu_count} mod menu(s)")
        if racer_menu_count:  parts.append(f"{racer_menu_count} racer menu(s)")
        await send_message(interaction, f"Restoring {total} message(s): {', '.join(parts)}...", ephemeral=True)

        MENU_TYPES = {RaceMessageType.ModMenu, RaceMessageType.RacerMenu}
        menu_rows    = [r for r in restore_rows if r.message_type in MENU_TYPES]
        content_rows = [r for r in restore_rows if r.message_type not in MENU_TYPES]

        failures = []

        for row in menu_rows:
            try:
                channel = discord_server.get_channel(row.channel_id)
                if channel is None:
                    failures.append(f"Channel <#{row.channel_id}> not found (type {row.message_type})")
                    continue
                if row.message_type == RaceMessageType.ModMenu:
                    msg = await send_moderator_menu(interaction, channel)
                    save_message(interaction.guild_id, channel.id, msg.id, message_type=RaceMessageType.ModMenu)
                elif row.message_type == RaceMessageType.RacerMenu:
                    msg = await send_racer_menu(interaction, channel)
                    save_message(interaction.guild_id, channel.id, msg.id, message_type=RaceMessageType.RacerMenu)
            except Exception as e:
                failures.append(f"Failed to restore message type {row.message_type} in <#{row.channel_id}>: {e}")

        if mod_channel:
            try:
                msg = await send_moderator_menu(interaction, mod_channel)
                save_message(interaction.guild_id, mod_channel.id, msg.id, message_type=RaceMessageType.ModMenu)
            except Exception as e:
                failures.append(f"Failed to create mod menu in <#{mod_channel.id}>: {e}")

        if racer_channel:
            try:
                msg = await send_racer_menu(interaction, racer_channel)
                save_message(interaction.guild_id, racer_channel.id, msg.id, message_type=RaceMessageType.RacerMenu)
            except Exception as e:
                failures.append(f"Failed to create racer menu in <#{racer_channel.id}>: {e}")

        for row in content_rows:
            try:
                channel = discord_server.get_channel(row.channel_id)
                if channel is None:
                    failures.append(f"Channel <#{row.channel_id}> not found (type {row.message_type})")
                    continue
                if row.message_type == RaceMessageType.Leaderboard:
                    await post_channel_category_leaderboard(interaction, channel, row.category_id_id, interaction.client)
                elif row.message_type == RaceMessageType.RaceInfo:
                    race = get_race(row.race_id_id)
                    if race is None:
                        failures.append(f"Race #{row.race_id_id} not found for race info in <#{row.channel_id}>")
                        continue
                    await pin_race_info(channel.id, race, interaction)
            except Exception as e:
                failures.append(f"Failed to restore message type {row.message_type} in <#{row.channel_id}>: {e}")

        clear_restore_state(interaction.guild_id)

        if failures:
            failure_list = "\n".join(failures)
            await send_message(interaction, f"Complete with errors:\n{failure_list}", ephemeral=True)
        else:
            await send_message(interaction, "Done!", ephemeral=True)
        


    ####################################################################################################################
    @async_admin.subcommand(description="Cleans up menu messages in preparation for bot shutdown")
    async def shutdown(
        self,
        interaction):
        self.log_command(interaction.user, "SHUTDOWN")

        await interaction.response.defer(ephemeral=True)

        server = self.get_server(interaction)
        if server is not None:
            if not user_is_admin(interaction.guild, interaction.user):
                await send_message(interaction, "Only Race Admins can use this command", ephemeral=True)
                return

        RESTORABLE_TYPES = {RaceMessageType.ModMenu, RaceMessageType.RacerMenu,
                            RaceMessageType.Leaderboard, RaceMessageType.RaceInfo}

        discord_server = get_server_from_interaction(interaction)
        message_list = get_server_messages(interaction.guild_id)
        seen_leaderboards = set()
        for m in message_list:
            if m.message_type == RaceMessageType.Announcement:
                continue
            if m.message_type in RESTORABLE_TYPES:
                if m.message_type == RaceMessageType.Leaderboard:
                    key = (m.category_id_id, m.race_id_id)
                    if key not in seen_leaderboards:
                        seen_leaderboards.add(key)
                        save_restore_state(
                            m.server_id, m.channel_id, m.message_type,
                            category_id=m.category_id_id,
                            race_id=m.race_id_id)
                else:
                    save_restore_state(
                        m.server_id, m.channel_id, m.message_type,
                        category_id=m.category_id_id,
                        race_id=m.race_id_id)
            await delete_message(discord_server, m.id)

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