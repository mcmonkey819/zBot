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
        self.trial_reaction_cache = {}  # announcement_message_id -> Trial

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
        await self._load_trial_reaction_cache()

    ####################################################################################################################
    async def _load_trial_reaction_cache(self):
        self.trial_reaction_cache = {}
        try:
            trials = get_all_tracked_trials()
            for trial in trials:
                self.trial_reaction_cache[trial.announcement_message_id] = trial
            logging.info(f"Loaded {len(self.trial_reaction_cache)} trial(s) into reaction cache")
        except Exception as e:
            logging.warning(f"Failed to load trial reaction cache: {e}")

    ####################################################################################################################
    async def _notify_trial_organizer(self, trial, guild, count):
        try:
            member = guild.get_member(trial.organizer_user_id)
            if member is None:
                member = await guild.fetch_member(trial.organizer_user_id)
            msg_text = (f"The minimum signup threshold of {trial.min_signups} has been reached "
                        f"for **{trial.display_name}**! Current signups: {count}")
            notified = False
            try:
                await member.send(msg_text)
                notified = True
            except Exception:
                pass
            if not notified and trial.announcement_channel_id:
                channel = guild.get_channel(trial.announcement_channel_id)
                if channel:
                    await channel.send(f"<@{trial.organizer_user_id}> {msg_text}")
        except Exception as e:
            logging.warning(f"Failed to notify trial organizer for trial {trial.id}: {e}")
        trial.min_signups_notified = True
        trial.save()

    ####################################################################################################################
    @commands.Cog.listener("on_raw_reaction_add")
    async def on_raw_reaction_add_handler(self, payload):
        if payload.message_id not in self.trial_reaction_cache:
            return
        trial = self.trial_reaction_cache[payload.message_id]
        if payload.user_id == self.bot.user.id:
            return
        if not trial.accept_signups:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except Exception:
                return
        role = guild.get_role(trial.participant_role_id)
        if role is None:
            return
        try:
            await member.add_roles(role, reason="Trial signup reaction")
        except Exception as e:
            logging.warning(f"Failed to add participant role to {payload.user_id}: {e}")
            return
        if trial.current_race_id_id is not None:
            try:
                assign_racer(member.id, trial.current_race_id_id)
            except Exception as e:
                logging.warning(f"Failed to assign trial racer {payload.user_id} to race {trial.current_race_id_id}: {e}")
        if trial.min_signups is not None and not trial.min_signups_notified:
            count = len(role.members)
            if count >= trial.min_signups:
                await self._notify_trial_organizer(trial, guild, count)

    ####################################################################################################################
    @commands.Cog.listener("on_raw_reaction_remove")
    async def on_raw_reaction_remove_handler(self, payload):
        if payload.message_id not in self.trial_reaction_cache:
            return
        trial = self.trial_reaction_cache[payload.message_id]
        if payload.user_id == self.bot.user.id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except Exception:
                return
        role = guild.get_role(trial.participant_role_id)
        if role is not None:
            try:
                await member.remove_roles(role, reason="Trial signup reaction removed")
            except Exception as e:
                logging.warning(f"Failed to remove participant role from {payload.user_id}: {e}")
        if trial.accept_signups and trial.current_race_id_id is not None:
            assignment = get_race_assignment(payload.user_id, trial.current_race_id_id)
            if assignment is not None:
                submission = get_race_submission(payload.user_id, trial.current_race_id_id)
                if submission is None:
                    assignment.delete_instance()

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
            default=None),
        server_id: str = nextcord.SlashOption(
            description="Server ID to start up (CoolestGuy only; ignores mod_channel/racer_channel)",
            required=False,
            default=None)):
        self.log_command(interaction.user, "STARTUP")

        await interaction.response.defer(ephemeral=True)

        if server_id is not None:
            if interaction.user.id != bot_config.CoolestGuy:
                await send_message(interaction, "You are not authorized to run startup for another server.", ephemeral=True)
                return
            server_id = int(server_id)
            discord_server = interaction.client.get_guild(server_id)
            if discord_server is None:
                await send_message(interaction, f"Cannot find server with ID {server_id}.", ephemeral=True)
                return
            mod_channel = None
            racer_channel = None
        else:
            server_id = interaction.guild_id
            # Check if this server is in the DB and that the user is an admin
            server = self.get_server(interaction)
            if server is None:
                if interaction.user.id == bot_config.CoolestGuy:
                    server = AsyncRaceServer(id=interaction.guild_id, name=interaction.guild.name)
                    try:
                        server.save(force_insert=True)
                    except Exception as e:
                        await send_message(interaction, f"**ERROR** Could not save server information: {e}")
                        return
                    await send_message(interaction, "Server registered with no roles configured. Run `/async_admin server_config` to set up roles before using.", ephemeral=True)
                else:
                    await send_message(interaction, "**ERROR** This server is not setup for use with this bot, please contact the bot owner")
                    return
            if not user_is_admin(interaction.guild, interaction.user):
                await send_message(interaction, "Only Race Admins can use this command", ephemeral=True)
                return
            discord_server = get_server_from_interaction(interaction)

        restore_rows = get_restore_state(server_id)

        if not restore_rows and not mod_channel and not racer_channel:
            await send_message(interaction, "Nothing to restore. Provide mod_channel and racer_channel for fresh setup.", ephemeral=True)
            return

        # Remove restore entries overridden by explicit channel params
        if restore_rows and mod_channel:
            restore_rows = [r for r in restore_rows if r.message_type != RaceMessageType.ModMenu]
        if restore_rows and racer_channel:
            restore_rows = [r for r in restore_rows if r.message_type != RaceMessageType.RacerMenu]

        # Build summary counts across restore rows and explicit channel overrides
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

        failures = await self._do_startup(server_id, discord_server, interaction, restore_rows)

        if mod_channel:
            try:
                msg = await send_moderator_menu(interaction, mod_channel)
                save_message(server_id, mod_channel.id, msg.id, message_type=RaceMessageType.ModMenu)
            except Exception as e:
                failures.append(f"Failed to create mod menu in <#{mod_channel.id}>: {e}")

        if racer_channel:
            try:
                msg = await send_racer_menu(interaction, racer_channel)
                save_message(server_id, racer_channel.id, msg.id, message_type=RaceMessageType.RacerMenu)
            except Exception as e:
                failures.append(f"Failed to create racer menu in <#{racer_channel.id}>: {e}")

        if failures:
            failure_list = "\n".join(failures)
            await send_message(interaction, f"Complete with errors:\n{failure_list}", ephemeral=True)
        else:
            await send_message(interaction, "Done!", ephemeral=True)
        


    ####################################################################################################################
    @async_admin.subcommand(description="View and update server configuration (roles, VC, trials)")
    async def server_config(self, interaction):
        if not user_is_admin(interaction.guild, interaction.user):
            await interaction.response.send_message("Only Race Admins can use this command.", ephemeral=True)
            return
        self.log_command(interaction.user, "SERVER_CONFIG")
        await interaction.response.defer(ephemeral=True)
        server = self.get_server(interaction)
        if server is None:
            await interaction.followup.send("This server is not registered. Run `/async_admin startup` first.", ephemeral=True)
            return
        discord_server = get_server_from_interaction(interaction)
        view = ServerConfigView(server, discord_server, interaction)
        await interaction.followup.send(embed=view.build_embed(), view=view, ephemeral=True)

    ####################################################################################################################
    async def _do_shutdown(self, server_id, discord_server):
        """Core shutdown logic. Saves restore state and deletes all tracked messages for the server."""
        RESTORABLE_TYPES = {RaceMessageType.ModMenu, RaceMessageType.RacerMenu,
                            RaceMessageType.Leaderboard, RaceMessageType.RaceInfo}

        clear_restore_state(server_id)
        message_list = get_server_messages(server_id)
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

    ####################################################################################################################
    async def _do_startup(self, server_id, discord_server, interaction, restore_rows=None):
        """Core startup logic. Restores messages from saved state. Returns list of failure strings."""
        if restore_rows is None:
            restore_rows = get_restore_state(server_id)
        if not restore_rows:
            return []

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
                    save_message(server_id, channel.id, msg.id, message_type=RaceMessageType.ModMenu)
                elif row.message_type == RaceMessageType.RacerMenu:
                    msg = await send_racer_menu(interaction, channel)
                    save_message(server_id, channel.id, msg.id, message_type=RaceMessageType.RacerMenu)
            except Exception as e:
                failures.append(f"Failed to restore message type {row.message_type} in <#{row.channel_id}>: {e}")

        for row in content_rows:
            try:
                channel = discord_server.get_channel(row.channel_id)
                if channel is None:
                    failures.append(f"Channel <#{row.channel_id}> not found (type {row.message_type})")
                    continue
                if row.message_type == RaceMessageType.Leaderboard:
                    await post_channel_category_leaderboard(interaction, channel, row.category_id_id,
                                                            interaction.client, server_id=server_id)
                elif row.message_type == RaceMessageType.RaceInfo:
                    race = get_race(row.race_id_id)
                    if race is None:
                        failures.append(f"Race #{row.race_id_id} not found for race info in <#{row.channel_id}>")
                        continue
                    await post_race_info_message(race, channel)
            except Exception as e:
                failures.append(f"Failed to restore message type {row.message_type} in <#{row.channel_id}>: {e}")

        clear_restore_state(server_id)
        return failures

    ####################################################################################################################
    @async_admin.subcommand(description="Cleans up menu messages in preparation for bot shutdown")
    async def shutdown(
        self,
        interaction,
        server_id: str = nextcord.SlashOption(
            description="Server ID to shut down (CoolestGuy only)",
            required=False,
            default=None)):
        self.log_command(interaction.user, "SHUTDOWN")

        await interaction.response.defer(ephemeral=True)

        if server_id is not None:
            if interaction.user.id != bot_config.CoolestGuy:
                await send_message(interaction, "You are not authorized to run shutdown for another server.", ephemeral=True)
                return
            server_id = int(server_id)
            discord_server = interaction.client.get_guild(server_id)
            if discord_server is None:
                await send_message(interaction, f"Cannot find server with ID {server_id}.", ephemeral=True)
                return
        else:
            server_id = interaction.guild_id
            server = self.get_server(interaction)
            if server is not None:
                if not user_is_admin(interaction.guild, interaction.user):
                    await send_message(interaction, "Only Race Admins can use this command", ephemeral=True)
                    return
            discord_server = get_server_from_interaction(interaction)

        await self._do_shutdown(server_id, discord_server)
        await send_message(interaction, "Done!", ephemeral=True)

    ####################################################################################################################
    @async_admin.subcommand(description="Restarts the bot across all configured servers (CoolestGuy only)")
    async def restart(self, interaction):
        if interaction.user.id != bot_config.CoolestGuy:
            await interaction.response.send_message("You are not authorized to run this command.", ephemeral=True)
            return

        self.log_command(interaction.user, "RESTART")
        await interaction.response.defer(ephemeral=True)

        servers = list(AsyncRaceServer.select())
        total = len(servers)

        if total == 0:
            await interaction.edit_original_message(content="No servers found in the database.")
            return

        restarted = []
        skipped   = []
        errors    = []

        for i, server in enumerate(servers):
            await interaction.edit_original_message(content=f"Processing **{server.name}** ({i + 1}/{total})...")

            discord_server = interaction.client.get_guild(server.id)
            if discord_server is None:
                errors.append(f"**{server.name}** — bot is not in this server")
                continue

            await self._do_shutdown(server.id, discord_server)

            restore_rows = get_restore_state(server.id)
            has_mod_menu   = any(r.message_type == RaceMessageType.ModMenu   for r in restore_rows)
            has_racer_menu = any(r.message_type == RaceMessageType.RacerMenu for r in restore_rows)

            if not has_mod_menu or not has_racer_menu:
                skipped.append(f"**{server.name}**")
                clear_restore_state(server.id)
                continue

            failures = await self._do_startup(server.id, discord_server, interaction)
            restarted.append(f"**{server.name}**")
            for f in failures:
                errors.append(f"**{server.name}** — {f}")

        lines = ["Restart complete.\n"]
        if restarted:
            lines.append(f"Restarted ({len(restarted)}): {', '.join(restarted)}")
        if skipped:
            lines.append(f"Skipped ({len(skipped)}): {', '.join(skipped)}")
        if errors:
            lines.append(f"Errors ({len(errors)}):")
            for e in errors:
                lines.append(f"  {e}")

        await interaction.edit_original_message(content="\n".join(lines))

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

########################################################################################################################
# ASYNC_MOD
########################################################################################################################
    @nextcord.slash_command()
    async def async_mod(self, interaction):
        pass

    ####################################################################################################################
    @async_mod.subcommand(description="Post trial signup announcement and begin tracking reactions")
    async def announce_trial(
        self,
        interaction,
        message_id: str = nextcord.SlashOption(
            description="ID of an existing announcement message to attach to (optional)",
            required=False,
            default=None)):

        if not user_is_mod(interaction.guild, interaction.user):
            await interaction.response.send_message("Only Race Mods can use this command.", ephemeral=True)
            return

        self.log_command(interaction.user, "ANNOUNCE_TRIAL")

        db_server = self.get_server(interaction)
        if db_server is None:
            await interaction.response.send_message("Server not registered. Run `/async_admin startup` first.", ephemeral=True)
            return

        if not db_server.trials_enabled:
            await interaction.response.send_message("Trials are not enabled for this server. Run `/async_admin server_config`.", ephemeral=True)
            return

        if db_server.trials_announcement_channel_id is None:
            await interaction.response.send_message("No announcement channel configured. Run `/async_admin server_config`.", ephemeral=True)
            return

        discord_server = get_server_from_interaction(interaction)
        existing_message_id = None
        if message_id is not None:
            try:
                existing_message_id = int(message_id)
                channel = discord_server.get_channel(db_server.trials_announcement_channel_id)
                await channel.fetch_message(existing_message_id)
            except Exception:
                await interaction.response.send_message(
                    "Could not find the specified message in the announcements channel.", ephemeral=True)
                return

        flow = TrialAnnounceFlow(db_server, discord_server, existing_message_id, self.trial_reaction_cache)
        await flow.start(interaction)

    ####################################################################################################################
    @async_mod.subcommand(description="Cancel an unstarted trial and clean up created objects")
    async def cancel_trial(self, interaction):
        if not user_is_mod(interaction.guild, interaction.user):
            await interaction.response.send_message("Only Race Mods can use this command.", ephemeral=True)
            return

        self.log_command(interaction.user, "CANCEL_TRIAL")
        await interaction.response.defer(ephemeral=True)

        db_server = self.get_server(interaction)
        if db_server is None:
            await send_message(interaction, "Server not registered. Run `/async_admin startup` first.")
            return

        trials = get_announcing_trials(db_server.id)
        if not trials:
            await send_message(interaction, "No trials in Announcing state to cancel.")
            return

        discord_server = get_server_from_interaction(interaction)

        if len(trials) == 1:
            await send_cancel_trial_confirm(interaction, trials[0], discord_server, self.trial_reaction_cache)
        else:
            select_list = [
                nextcord.SelectOption(
                    label=t.display_name,
                    value=str(t.id))
                for t in trials
            ]
            view = zSingleSelectView(select_list, None, "Select trial to cancel...")
            await send_message(interaction, view=view)
            await view.wait()
            trial_id = view.get_selected_value()
            if trial_id is not None:
                trial = get_trial(int(trial_id))
                if trial is not None:
                    await send_cancel_trial_confirm(
                        interaction, trial, discord_server, self.trial_reaction_cache)

    ####################################################################################################################
    @async_mod.subcommand(description="Create channels, finisher role, and bot category; transition trial to Active")
    async def start_trial(self, interaction):
        self.log_command(interaction.user, "START_TRIAL")
        await interaction.response.defer(ephemeral=True)

        db_server = self.get_server(interaction)
        if db_server is None:
            await send_message(interaction, "Server not registered. Run `/async_admin startup` first.")
            return

        if db_server.trials_discord_category_id is None:
            await send_message(interaction, "No Discord category configured for trials. Run `/async_admin server_config`.")
            return

        trials = get_announcing_trials(db_server.id)
        if not user_is_mod(interaction.guild, interaction.user):
            trials = [t for t in trials if t.organizer_user_id == interaction.user.id]
        if not trials:
            await send_message(interaction, "No trials in Announcing state that you have permission to start.")
            return

        discord_server = get_server_from_interaction(interaction)

        if len(trials) == 1:
            trial = trials[0]
        else:
            select_list = [
                nextcord.SelectOption(label=t.display_name, value=str(t.id))
                for t in trials
            ]
            view = zSingleSelectView(select_list, None, "Select trial to start...")
            await send_message(interaction, view=view)
            await view.wait()
            trial_id = view.get_selected_value()
            if trial_id is None:
                return
            trial = get_trial(trial_id)
            if trial is None:
                await send_message(interaction, "Trial not found.")
                return

        # Detect partial start (objects created in a previous session that was abandoned)
        partial_ids = [trial.general_channel_id, trial.spoilers_channel_id,
                       trial.finisher_role_id, trial.category_id]
        if any(v is not None for v in partial_ids):
            lines = [f"**{trial.display_name}** has a partial start from a previous session:"]
            if trial.general_channel_id:
                lines.append(f"• General channel: <#{trial.general_channel_id}>")
            if trial.spoilers_channel_id:
                lines.append(f"• Spoilers channel: <#{trial.spoilers_channel_id}>")
            if trial.finisher_role_id:
                lines.append(f"• Finisher role: <@&{trial.finisher_role_id}>")
            if trial.category_id:
                lines.append(f"• Bot category ID: {trial.category_id}")
            lines.append("\nUse **Rollback Partial Start** to clean up and restart, or **Continue Setup** to proceed from the extra info step.")
            view = TrialPartialStartView(trial, db_server, discord_server)
            await send_message(interaction, "\n".join(lines), view=view)
            return

        flow = TrialStartFlow(trial, db_server, discord_server)
        await flow.start(interaction)

    @async_mod.subcommand(description="End the current race and start a new one for an active trial")
    async def start_trial_race(self, interaction):
        self.log_command(interaction.user, "START_TRIAL_RACE")
        await interaction.response.defer(ephemeral=True)

        db_server = self.get_server(interaction)
        if db_server is None:
            await send_message(interaction, "Server not registered. Run `/async_admin startup` first.")
            return

        trials = get_active_trials(db_server.id)
        if not user_is_mod(interaction.guild, interaction.user):
            trials = [t for t in trials if t.organizer_user_id == interaction.user.id]
        if not trials:
            await send_message(interaction, "No active trials that you have permission to manage.")
            return

        discord_server = get_server_from_interaction(interaction)

        if len(trials) == 1:
            trial = trials[0]
        else:
            select_list = [
                nextcord.SelectOption(label=t.display_name, value=str(t.id))
                for t in trials
            ]
            view = zSingleSelectView(select_list, None, "Select trial...")
            await send_message(interaction, view=view)
            await view.wait()
            trial_id = view.get_selected_value()
            if trial_id is None:
                return
            trial = get_trial(trial_id)
            if trial is None:
                await send_message(interaction, "Trial not found.")
                return

        flow = TrialStartRaceFlow(trial, db_server, discord_server)
        await flow.start(interaction)

    ####################################################################################################################
    @async_mod.subcommand(description="End an active trial, scoring the final race and stopping reaction tracking")
    async def end_trial(self, interaction):
        self.log_command(interaction.user, "END_TRIAL")
        await interaction.response.defer(ephemeral=True)

        db_server = self.get_server(interaction)
        if db_server is None:
            await send_message(interaction, "Server not registered. Run `/async_admin startup` first.")
            return

        trials = get_active_trials(db_server.id)
        if not user_is_mod(interaction.guild, interaction.user):
            trials = [t for t in trials if t.organizer_user_id == interaction.user.id]
        if not trials:
            await send_message(interaction, "No active trials that you have permission to end.")
            return

        if len(trials) == 1:
            trial = trials[0]
        else:
            select_list = [
                nextcord.SelectOption(label=t.display_name, value=str(t.id))
                for t in trials
            ]
            view = zSingleSelectView(select_list, None, "Select trial to end...")
            await send_message(interaction, view=view)
            await view.wait()
            trial_id = view.get_selected_value()
            if trial_id is None:
                return
            trial = get_trial(trial_id)
            if trial is None:
                await send_message(interaction, "Trial not found.")
                return

        await send_end_trial_confirm(interaction, trial, self.trial_reaction_cache)

    ####################################################################################################################
    @async_mod.subcommand(description="Remove channels, roles, and archive a trial that has ended")
    async def archive_trial(self, interaction):
        self.log_command(interaction.user, "ARCHIVE_TRIAL")
        await interaction.response.defer(ephemeral=True)

        db_server = self.get_server(interaction)
        if db_server is None:
            await send_message(interaction, "Server not registered. Run `/async_admin startup` first.")
            return

        trials = get_ended_trials(db_server.id)
        if not user_is_mod(interaction.guild, interaction.user):
            trials = [t for t in trials if t.organizer_user_id == interaction.user.id]
        if not trials:
            await send_message(interaction, "No ended trials that you have permission to archive.")
            return

        discord_server = get_server_from_interaction(interaction)

        if len(trials) == 1:
            trial = trials[0]
        else:
            select_list = [
                nextcord.SelectOption(label=t.display_name, value=str(t.id))
                for t in trials
            ]
            view = zSingleSelectView(select_list, None, "Select trial to archive...")
            await send_message(interaction, view=view)
            await view.wait()
            trial_id = view.get_selected_value()
            if trial_id is None:
                return
            trial = get_trial(trial_id)
            if trial is None:
                await send_message(interaction, "Trial not found.")
                return

        await send_archive_trial_prompt(interaction, trial, discord_server, self.trial_reaction_cache)


def setup(bot):
    bot.add_cog(AsyncRaces(bot))