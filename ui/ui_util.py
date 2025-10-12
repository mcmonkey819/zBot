# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime, date
from enum import Enum
import logging
import math
import nextcord
from nextcord.partial_emoji import PartialEmoji
import re
from tabulate import tabulate
tabulate.PRESERVE_WHITESPACE = True
import validators

from db.zBot_db_orm import *
from db.db_util import *
import config.bot_config as bot_config

########################################################################################################################
# UTILITY TYPES
########################################################################################################################
class zField():
    def __init__(self, custom_id: str, label: str, default_value, required: bool, placeholder=None):
        self.custom_id = custom_id
        self.label = label
        self.default_value = default_value
        self.required = required
        self.placeholder = placeholder

FieldList = list[zField]
FieldDict = dict[str, nextcord.ui.TextInput]
SelectList = list[nextcord.SelectOption]

########################################################################################################################
# UTILITY FUNCTIONS
########################################################################################################################

########################################################################################################################
# Checks if a user has the provided role
def user_has_role(server, user, role_id):
    role = server.get_role(role_id)
    return role in user.roles

########################################################################################################################
# Checks if a user is a race admin on the server
def user_is_admin(server, user):
    if user.id == bot_config.CoolestGuy:
        return True
    logging.info(f"Server ID: {server.id}")
    db_server = get_server(server.id)
    return user_has_role(server, user, db_server.admin_role_id)

########################################################################################################################
# Checks if a user is a race moderator on the server
def user_is_mod(server, user):
    # Admins are like super mods
    if user_is_admin(server, user):
        return True
    db_server = get_server(server.id)
    return user_has_role(server, user, db_server.mod_role_id)

########################################################################################################################
async def check_user_is_admin(interaction):
    server = get_server_from_interaction(interaction)
    user = await server.fetch_member(interaction.user.id)
    is_admin = user_is_admin(server, user)
    if is_admin == False:
        await send_message(interaction, f"Only Race Admins have permission for this function")
    return is_admin

########################################################################################################################
def save_message(server_id, channel_id, message_id, *, message_type=RaceMessageType.Leaderboard, category_id=None, race_id=None):
    msg = AsyncRaceMessage(server_id=server_id,
                           channel_id=channel_id,
                           message_id=message_id,
                           message_type=message_type,
                           category_id=category_id,
                           race_id=race_id)
    try:
        msg.save()
    except:
        logging.info(f"**ERROR** Failed to save cleanup message for server {server_id}, channel {channel_id}, message {message_id}")

########################################################################################################################
# Takes an AsyncRaceMessage, finds the corresponding Discord message and deletes message and optionally deletes or
# zeroes the DB entry
async def delete_message(server, async_race_msg_id):
    async_race_msg = get_race_message(async_race_msg_id)

    if async_race_msg is not None and server is not None:
        if async_race_msg.message_id is not None:
            channel = server.get_channel(async_race_msg.channel_id)
            try:
                msg = await channel.fetch_message(async_race_msg.message_id)
                await msg.delete()
            except:
                logging.info(f"Failed to find message with message ID {async_race_msg.message_id}")
            async_race_msg.delete_instance()

#####################################################################################################################
async def has_text_channel_permission(user_id, server, channel):
    ret = False

    member = await server.fetch_member(user_id)
    perms = channel.permissions_for(member)
    bot_text_permission = nextcord.Permissions.text()
    bot_text_permission.update(manage_messages=False, manage_threads=False, send_tts_messages=False)
    if perms.is_superset(bot_text_permission):
        ret = True

    return ret

#####################################################################################################################
async def get_permitted_channel_select_list(user_id, server):
    select_list = []
    for c in server.text_channels:
        if await has_text_channel_permission(user_id, server, c):
            select_list.append(nextcord.SelectOption(label=c.name, value=c.id, description=c.name))
    return select_list

#####################################################################################################################
def get_role_select_list(server):
    select_list = [nextcord.SelectOption(label="None..", value=0, description="No Role Desired")]
    for r in server.roles:
        select_list.append(nextcord.SelectOption(label=r.name, value=r.id, description=r.name))
    return select_list

#####################################################################################################################
def get_server_from_interaction(interaction):
    return interaction.client.get_guild(interaction.guild_id)

#####################################################################################################################
def forfeit_race(user_id, race_id):
    race = get_race(race_id)
    if race is not None:
        # Create a new race submission and save the core info
        submission = AsyncRaceSubmission()
        submission.race_id = race_id
        submission.user_id = user_id
        submission.submit_datetime = zBot_now()
        submission.finish_time = ForfeitFinishTime
        submission.save()

#####################################################################################################################
# Given a numeric place, returns the ordinal string. e.g. 1 returns "1st", 2 "2nd" etc
def get_place_str(place):
    place_str = ""
    if place == 0:
        # This is an error and should never be reached, if it is might as well have some fun with it
        place_str = "Worst"
    else:
        place_str += str(place)
        # Check the last two digits to handle teens (11, 12, 13, 111, 112, 113, etc.)
        last_two_digits = place % 100
        ones_digit = place % 10
        
        # Special case: if the last two digits are 11, 12, or 13, always use "th"
        if 11 <= last_two_digits <= 13:
            place_str += "th"
        elif ones_digit == 1:
            place_str += "st"
        elif ones_digit == 2:
            place_str += "nd"
        elif ones_digit == 3:
            place_str += "rd"
        else:
            place_str += "th"

    return place_str

########################################################################################################################
def get_race_leaderboard_table(interaction, race_id):
    # Get the race submissions for this race, sorted by finish_time
    race_submissions = get_sorted_race_submissions(race_id)

    # Get extra info types assigned to this race
    extra_info_assignments = AsyncRaceExtraInfoAssignment.select().where(AsyncRaceExtraInfoAssignment.race_id == race_id)

    table_data = []
    places = []
    # Create the labels row
    column_labels = ["Name", "Finish Time"]

    # Add the extra info labels
    if extra_info_assignments is not None:
        for a in extra_info_assignments:
            t = get_extra_info_type(a.info_type_id)
            if t is not None:
                column_labels.append(t.name)
    else:
        extra_info_assignments = []

    # Put the comment last
    column_labels.append("Comment")
    table_data.append(column_labels)

    if race_submissions is not None:
        for i, s in enumerate(race_submissions):
            places.append(get_place_str(i+1))
            # Get the username
            user = interaction.client.get_user(s.user_id)
            username = get_user_name_str(s.user_id, user)
            table_row = [username, s.finish_time]
            for a in extra_info_assignments:
                # Lookup the extra infos for this submission and add them to the table
                info = get_extra_info(s.id, a.info_type_id)
                if info is not None:
                    table_row.append(info.data)
            table_row.append(s.comment)
            table_data.append(table_row)

    # Tablulate the submission data
    return tabulate(table_data, headers="firstrow", showindex=places, tablefmt="double_grid")

#####################################################################################################################
async def display_ephemeral_leaderboard(interaction, race_id):
    # Get the leaderboard table
    table_text = get_race_leaderboard_table(interaction, race_id)    

    # Send the message
    await send_message(interaction, table_text, ephemeral=True, codeblock=True)

####################################################################################################################
# This function breaks a response into multiple messages that meet the Discord API character limit
def build_response_message_list(message):
    """
    Splits a message into multiple parts to comply with Discord's character limit.
    
    Args:
        message: String message to split, or None
        
    Returns:
        List of message strings, each under Discord's character limit (1990 chars)
    """
    if message is None:
        logging.debug("build_response_message_list called with None message")
        return [""]
    
    discord_api_char_limit = 2000 - 10  # Discord limit with safety buffer
    message_list = []

    # If we're under the character limit, just send the message
    if len(message) <= discord_api_char_limit:
        return [message]
    
    logging.info(f"Message exceeds character limit ({len(message)} chars), splitting into multiple messages")
    
    # Build a list of lines, then build messages from that list until we hit the message limit
    line_list = message.split("\n")
    curr_message = ""
    curr_message_len = 0

    for line_idx, line in enumerate(line_list):
        # First check if this single line is > limit and needs sentence splitting
        if len(line) > discord_api_char_limit:
            logging.warning(f"Line {line_idx} exceeds character limit ({len(line)} chars), attempting sentence split")
            sentences = re.split('[.?!;]', line)
            for sentence_idx, sentence in enumerate(sentences):
                if curr_message_len + len(sentence) > discord_api_char_limit:
                    if curr_message == "":
                        logging.error(f"Sentence {sentence_idx} in line {line_idx} is too long to fit in a single message ({len(sentence)} chars). This content will be skipped.")
                        continue
                    message_list.append(curr_message)
                    logging.debug(f"Created message part {len(message_list)} ({curr_message_len} chars)")
                    curr_message = ""
                    curr_message_len = 0
                curr_message += sentence
                curr_message_len += len(sentence)
        else:
            # Check if adding this line would put us over the limit
            if curr_message_len + len(line) + 1 > discord_api_char_limit:  # +1 for the newline
                if curr_message != "":
                    message_list.append(curr_message)
                    logging.debug(f"Created message part {len(message_list)} ({curr_message_len} chars)")
                    curr_message = ""
                    curr_message_len = 0
            
            # Only add newline back if the line isn't empty (empty line comes from trailing newline in split)
            if line:  # Skip empty strings from trailing newlines
                curr_message += line + "\n"
                curr_message_len += len(line) + 1
                
    if curr_message != "":
        message_list.append(curr_message)
        logging.debug(f"Created final message part {len(message_list)} ({curr_message_len} chars)")
    
    logging.info(f"Split message into {len(message_list)} parts")
    return message_list

#####################################################################################################################
def get_race_info_message(race):
    
    title = f"{race.description}"
    description = f"Use the buttons below for Race ID {race.id}\n  *Created On:* {race.create_datetime}"
    if race.additional_instructions is not None:
        description += f"\n\n{race.additional_instructions}"
    
    seed_parts = race.seed.split()
    seed_url = None
    for p in seed_parts:
        if validators.url(p) == True:
            seed_url = p
            break

    seed_embed = nextcord.Embed(title=title, description=description, url=seed_url, color=nextcord.Colour.random())
    if race.category_id.thumbnail_url is not None:
        try:
            seed_embed.set_thumbnail(url=race.category_id.thumbnail_url)
        except:
            logging.info(f"**ERROR** Failed to set thumbnail for category {race.category_id.name}")                       

    seed_embed.add_field(name="Seed", value=race.seed, inline=False)
    if race.hash is not None and race.hash != "":
        seed_embed.add_field(name="Hash", value=race.hash, inline=False)
    
    return seed_embed

#####################################################################################################################
async def defer(interaction):
    await interaction.response.defer(with_message=True, ephemeral=True)

#####################################################################################################################
async def send_message(interaction, msg="", ephemeral=True, codeblock=False, view=None, embed=None):
    msg_list = build_response_message_list(msg)

    for m in msg_list:
        if codeblock:
            m = f"```\n{m}\n```"

        # Add the embed and view to the last message if there is one provided
        if m == msg_list[-1]:
            if view is not None and embed is not None:
                await interaction.send(m, ephemeral=ephemeral, view=view, embed=embed)
            elif view is not None:
                await interaction.send(m, ephemeral=ephemeral, view=view)
            elif embed is not None:
                await interaction.send(m, ephemeral=ephemeral, embed=embed)
            else:
                await interaction.send(m, ephemeral=ephemeral)
        else:
            await interaction.send(m, ephemeral=ephemeral)


########################################################################################################################
def get_race_embed_field_value(race, user_id=None):
    category_name = race.category_id.name
    num_submissions = get_num_submissions(race.id)
    field_value = f"**Category:**\n{category_name}\n"
    field_value += f"**Submissions:** {num_submissions}\n"
    if user_id is not None:
        user_place = get_user_place(race.id, user_id)
        if user_place is not None:
            place = get_place_str(user_place)
            field_value += f"**Place:** {place}"
    else:
        field_value += f"**Description:**\n{race.description}"

    return field_value

###########################################################################################################################
def get_submission_details_dict(submission):
    details = {}
    details["Finish Time"] = "DNF" if submission.finish_time == ForfeitFinishTime else submission.finish_time
    if not is_value_empty(submission.comment):
        details["Comment"] = submission.comment
    
    # Get extra info types assigned to this race
    extra_info_assignments = AsyncRaceExtraInfoAssignment.select().where(AsyncRaceExtraInfoAssignment.race_id == submission.race_id)
    for a in extra_info_assignments:
        # Lookup the extra infos for this submission and add them to the table
        info = get_extra_info(submission.id, a.info_type_id)
        if info is not None:
            info_type = get_extra_info_type(a.info_type_id)
            if not is_value_empty(info.data):
                details[info_type.name] = info.data
    
    if not is_value_empty(submission.points):
        details["Points"] = format_points_str(submission.points)
   
    return details

########################################################################################################################
async def get_race_leaderboard_embed(title, body_text, submissions, current_page, per_page, bot_client, show_details = True):
    embed = nextcord.Embed(color=nextcord.Colour.random(), title=title, description=body_text)
        
    for i, s in enumerate(submissions):
        place_num = (current_page * per_page) + i + 1
        user = await bot_client.fetch_user(s.user_id)
        user_name = get_user_name_str(s.user_id, user)
        if show_details:
            value_text = f"**{user_name}**"
            details = get_submission_details_dict(s)
            for k, v in details.items():
                # Want to add points last
                if k == "Points":
                    continue
                value_text += f"\n--: {k}: {v}"
            if "Points" in details:
                value_text += f"\n--: Points: {details['Points']}"
        else:
            value_text = f"{s.finish_time} - {user_name}"
        embed.add_field(name=f"{get_place_str(place_num)}", value=value_text, inline=False)

    return embed

########################################################################################################################
class TeamSubmissionData:
    def __init__(self, team_name, user_ids, user_names, team_finish_time, finish_times):
        self.team_name = team_name
        self.team_finish_time = team_finish_time
        self.user_ids = user_ids
        self.user_names = user_names
        self.finish_times = finish_times

def get_team_race_leaderboard_embed(title, body_text, team_submissions: list[TeamSubmissionData], current_page, per_page, bot_client, show_details = True):
    embed = nextcord.Embed(color=nextcord.Colour.random(), title=title, description=body_text)

    for i, s in enumerate(team_submissions):
        place_num = (current_page * per_page) + i + 1
        value_text = f"{s.team_finish_time} - {s.team_name}"
        if show_details:
            for i, u in enumerate(s.user_names):
                value_text += f"\n--: {u} - {s.finish_times[i]}"
        embed.add_field(name=f"{get_place_str(place_num)}", value=value_text, inline=False)

    return embed


########################################################################################################################
def format_points_str(points) -> str:
    points_str = f"{points:0.3f}"
    # If there's no data after the decimal, remove it
    parts = points_str.split(".")
    if len(parts) > 1:
        found_significant_digit = False
        for c in parts[1]:
            if c != "0":
                found_significant_digit = True
                break
        if found_significant_digit == False:
            points_str = parts[0]
    return points_str

########################################################################################################################
async def get_category_leaderboard_embed(title, body_text, points_list, current_page, per_page, bot_client):
    embed = nextcord.Embed(color=nextcord.Colour.random(), title=title, description=body_text)
        
    for i, p in enumerate(points_list):
        place_num = (current_page * per_page) + i + 1
        user = await bot_client.fetch_user(p.user_id)
        user_name = get_user_name_str(p.user_id, user)
        num_submissions = get_num_category_submissions(p.user_id, p.category_id)
        embed.add_field(name=f"{get_place_str(place_num)} - {format_points_str(p.points)}", value=f"{user_name} ({num_submissions})", inline=False)

    return embed

########################################################################################################################
def get_race_leaderboard_description(race_id):
    description = f"Race `{race_id}`"
    race = get_race(race_id)
    if race is not None:
        description += f" created on {race.create_datetime}\nCategory: `{race.category_id.name}`\n\n{race.description}"
    return description

########################################################################################################################
def get_category_leaderboard_title(category_id):
    category = get_category(category_id)
    if category is None:
        return f"Leaderboard for Category ID `{category_id}`"
    else:   
        return f"Leaderboard for Category `{category.name}`"

########################################################################################################################
def get_category_leaderboard_description(category_id):
    category = get_category(category_id)
    if category is None:
        description =  f"Category `{category_id}`"
    else:
        completed_races = len(get_completed_races_by_category(category_id))
        description = f"Category `{category.name}`\nScoring Type: {PointsType.to_str(category.points_type)}"
        description += f"\nCompleted Races: {completed_races}\n\n{category.description}"
    description += f"\n(Note: Number of races run in parentheses)"
    return description

########################################################################################################################
def copy_embed(embed):
    new_embed = nextcord.Embed(
        title=embed.title,
        description=embed.description,
        color=embed.color
    )
    
    if embed.author is not None:
        new_embed.set_author(name=embed.author.name, icon_url=embed.author.icon_url, url=embed.author.url)
    if embed.footer is not None:
        new_embed.set_footer(text=embed.footer.text, icon_url=embed.footer.icon_url)
    if embed.image is not None:
        new_embed.set_image(url=embed.image.url)
    if embed.thumbnail is not None:
        new_embed.set_thumbnail(url=embed.thumbnail.url)
    if embed.url is not None:
        new_embed.url = embed.url

    return new_embed

########################################################################################################################
async def get_user_from_interaction(interaction, user_id):
    # First try to get the user from the guild
    user = interaction.guild.get_member(user_id)
    if user is None:
        # If that fails, try to get the user from the client
        user = await interaction.client.fetch_user(user_id)
    return user

########################################################################################################################
def can_view_race_leaderboard(server, race_id, user):
    # The user can view the leaderboard if the race is completed or if they have already submitted a time or they are
    # a moderator
    race = get_race(race_id)
    can_view = False
    
    if race is not None:
        # Check if the category allows mods to view leaderboards
        if race.category_id.mod_can_view_leaderboard:
            can_view = user_is_mod(server, user)

        # Can always view the leaderboard of a completed race
        if race.state == RaceState.Completed:
            can_view = True
    
    # Can also always view leaderboard if they've submitted a time
    if get_race_submission(user.id, race_id) is not None:
        can_view = True

    return can_view

########################################################################################################################
def get_user_name_str(user_id, user):
    user_name = str(user_id)
    if user is not None:
        if user.global_name is not None and user.global_name != "None":
            user_name = user.global_name
        else:
            user_name = user.display_name
    return user_name

########################################################################################################################
async def remove_role_from_members(guild, role):
    if role is not None:
        for m in guild.members:
            if role in m.roles:
                await m.remove_roles(role)

########################################################################################################################
def get_sorted_team_submissions(interaction, race_id):
    race = get_race(race_id)
    if not race.is_team_race:
        return None

    submissions = get_sorted_race_submissions(race_id)

    sub_ids = {}
    team_submissions = []
    for s in submissions:
        # If we've already handlled this submission, skip it
        if s.id in sub_ids:
            continue

        # Find the matching submission from teammate
        teammate_submission = None
        sub_ids[s.id] = True
        user_ids = [s.user_id]
        if s.teammate_id is not None:
            for t in submissions:
                if t.id not in sub_ids and t.user_id == s.teammate_id:
                    teammate_submission = t
                    if teammate_submission.teammate_id != s.user_id:
                        logging.info(f"**ERROR** Teammate ID mismatch for submission {s.id}")
                        teammate_submission = None
                    else:
                        sub_ids[t.id] = True
                        user_ids.append(t.user_id)
                    break
                
        # Get the team name, if it exists. Faster teammate gets to pick the team name
        team_name = get_extra_info(s.id, race.team_name_info_id)
        team_name_str = None
        if team_name is None and teammate_submission is not None:
            # But if the faster teammate doesn't specify a team name, check the teammate's submission for a valid name
            team_name = get_extra_info(teammate_submission.id, race.team_name_info_id)
            
        if team_name is not None:
            team_name_str = team_name.data

        total_finish_time_sec = 0
        # Get the username strings
        user_names = []
        user_names.append(get_user_name_str(s.user_id, interaction.guild.get_member(s.user_id)))
        if teammate_submission is not None:
            user_names.append(get_user_name_str(teammate_submission.user_id, interaction.guild.get_member(teammate_submission.user_id)))
        # If we still don't have a team name, just combine the usernames
        if team_name_str is None:
            team_name_str = f"Team {user_names[0]}"
            if teammate_submission is not None:
                team_name_str += f" & {user_names[1]}"
        # Calculate the average finish time
        if teammate_submission is not None:
            total_finish_time_sec = finish_time_to_seconds(s.finish_time) + finish_time_to_seconds(teammate_submission.finish_time)
            avg_finish_time_sec = int(total_finish_time_sec / 2)
        else:
            avg_finish_time_sec = finish_time_to_seconds(s.finish_time)

        avg_finish_time = finish_time_seconds_to_str(avg_finish_time_sec) 
        
        # Finally construct and add the team submission data object
        team_submissions.append(TeamSubmissionData(team_name_str, user_ids, user_names, avg_finish_time, [s.finish_time, teammate_submission.finish_time if teammate_submission is not None else None]))

    # Sort the list by finish time
    team_submissions.sort(key=lambda x: finish_time_to_seconds(x.team_finish_time))
    return team_submissions

########################################################################################################################
def export_race(interaction, race_id, filepath):
    race = get_race(race_id)
    subs = get_sorted_race_submissions(race_id)
    team_subs = None

    if race is None or subs is None or len(subs) == 0:
        if race is None:
            logging.error(f"Could not find race {race_id}")
        else:
            logging.error(f"No submissions for race {race_id}")
        return False
    
    # Get the extra info assignments for this race
    extra_info_assigns = get_race_extra_info_assignments(race_id)
    extra_info_types = [get_extra_info_type(e.info_type_id) for e in extra_info_assigns]

    include_points = race.state == RaceState.Completed and \
                     race.category_id.points_type != PointsType.NoScoring

    with open(filepath, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)

        # Create the header row
        header = ["User ID", "Username", "Finish Time"]
        header += [e.name for e in extra_info_types]
        if include_points:
            header += ["Points"]
        header += ["Comment"]
        if race.is_team_race:
            header += ["Teammate ID", "Teammate Username", "Team Finish Time (Avg)"]
            team_subs = get_sorted_team_submissions(interaction, race_id)
        csvwriter.writerow(header)

        # Create the data rows
        for s in subs:
            username = "Unknown"
            if interaction is not None:
                user = interaction.guild.get_member(s.user_id)
                username = get_user_name_str(user.id, user) if user is not None else "Unknown"
            data_row = [s.user_id, username, str(s.finish_time)]
            for e in extra_info_types:
                info = get_extra_info(s.id, e.id)
                if info is not None:
                    if e.var_type == VarType.Int:
                        data_row.append(int(info.data))
                    elif e.var_type == VarType.Float:
                        data_row.append(float(info.data))
                    else:
                        data_row.append(str(info.data))
                else:
                    data_row.append("")
            if include_points:
                data_row.append(s.points)
            data_row.append(s.comment)

            if race.is_team_race:
                # search the team submissions for the matching team
                for t in team_subs:
                    if s.user_id in t.user_ids:
                        idx = t.user_ids.index(s.user_id)
                        data_row += [t.user_ids[idx-1], t.user_names[idx-1], str(t.team_finish_time)]
                        break   

            csvwriter.writerow(data_row)

    return True

########################################################################################################################
# BASE CLASSES
########################################################################################################################
# This Modal (form) will display a form that has fields matching the provided item list. On completion it will call
# the provided submit_handler function, passing a pointer to itself and the interaction object.
class zModal(nextcord.ui.Modal):
    def __init__(self, fields: FieldDict, submit_handler, title: str):
        super().__init__(title, timeout=None)
        self.fields = fields
        self.submit_handler = submit_handler

        for v in self.fields.values():
            self.add_item(v)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        if self.submit_handler is not None:
            await self.submit_handler(interaction, self)
        self.stop()

#####################################################################################################################
# This Select (drop down selection) will display a drop down with the string options provided. This variant will
# only allow the user to select a single option from the list. On completion it will call the provided
# submit_handler function, passing the value for the option chosen and the interaction object.
# Discord Select objects can only accept 25 entires, if more than 25 are supplied in the select_list the
# zSingleSelect will display the first 24 and a "Show More..." entry which, if selected, will create and show
# another zSingleSelct with single_select[24:] slice of the list
class zSingleSelect(nextcord.ui.Select):
    def __init__(self, select_list: SelectList, submit_handler, placeholder, payload, show_more_id=-1):
        self.timeout = None
        self.payload = payload
        if len(select_list) > 25:
            self.orig_placeholder = placeholder
            self.orig_select_list = select_list
            self.show_more_id = -9999
            option_list = select_list[:24]
            option_list.append(nextcord.SelectOption(
                label="Show More...",
                description = "Show More Options",
                value = self.show_more_id))
        else:
            self.orig_select_list = None
            option_list = select_list
        super().__init__(min_values=1, max_values=1, options=option_list, placeholder=placeholder)
        self.submit_handler = submit_handler

    async def callback(self, interaction: nextcord.Interaction) -> None:
        if self.orig_select_list is not None and int(interaction.data['values'][0]) == self.show_more_id:
            # Send a Select view with the next entries
            await send_message(interaction, view=zSingleSelectView(
                submit_handler=self.submit_handler,
                select_list = self.orig_select_list[25:],
                placeholder = self.orig_placeholder,
                payload = self.payload))
        else:
            if self.payload is not None:
                await self.submit_handler((int(interaction.data['values'][0]), self.payload), interaction)
            else:
                await self.submit_handler(int(interaction.data['values'][0]), interaction)

#####################################################################################################################
# View which contains a zSingleSelect
class zSingleSelectView(nextcord.ui.View):
    def __init__(self, select_list: SelectList, submit_handler, placeholder = None, payload=None):
        super().__init__(timeout=None)
        self.selected_value = None
        self.submit_handler = submit_handler
        self.select = zSingleSelect(select_list, self.save_selected_value, placeholder, payload)
        self.add_item(self.select)

    async def save_selected_value(self, value, interaction):
        self.interaction = interaction
        self.selected_value = value
        if self.submit_handler is not None:
            await self.submit_handler(value, interaction)
        self.stop()

    def get_selected_value(self):
        return self.selected_value
    
    async def prompt(self, interaction: nextcord.Interaction, msg: str = ""):
        await send_message(interaction, "", view=self)
        await self.wait()
        return self.get_selected_value()
    
#####################################################################################################################
# This Select (drop down selection) will display a drop down with the string options provided. This variant will
# allow the user to select up to `max_values` from the list. On completion it will call the provided submit_handler
# function, passing a list of the values chosen and the interaction object.
# NOTE: Only 25 entries can be displayed in a Discord select, if more than 25 are supplied in the select_list
# then only the first 25 will be used
class zMultiSelect(nextcord.ui.Select):
    def __init__(self, select_list: SelectList, max_values: int, submit_handler, placeholder):
        super().__init__(min_values=1, max_values=max_values, options=select_list, placeholder=placeholder)
        self.submit_handler = submit_handler

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value_list = []
        for v in interaction.data['values']:
            value_list.append(int(v))
        await self.submit_handler(value_list, interaction)

#####################################################################################################################
# View which contains a zMultiSelect
class zMultiSelectView(nextcord.ui.View):
    def __init__(self, select_list: SelectList, max_values: int, submit_handler, placeholder = None):
        super().__init__(timeout=None)
        self.selected_values = None
        self.submit_handler = submit_handler
        self.category_select = zMultiSelect(select_list, max_values, self.save_selected_values, placeholder)
        self.add_item(self.category_select)

    async def save_selected_values(self, values, interaction):
        self.interaction = interaction
        self.selected_values = values
        if self.submit_handler is not None:
            await self.submit_handler(values, interaction)
        self.stop()

    async def prompt(self, interaction: nextcord.Interaction, msg: str = ""):
        await send_message(interaction, "", view=self)
        await self.wait()
        return self.selected_values

    def get_selected_values(self):
        return self.selected_values
    
########################################################################################################################
# View which contains buttons for continuing or cancelling
class zContinueCancelButtonView(nextcord.ui.View):
    def __init__(self, continue_func, cancel_func):
        super().__init__(timeout=None)
        self.continue_func = continue_func
        self.cancel_func = cancel_func

    @nextcord.ui.button(style=nextcord.ButtonStyle.red, label='❌ Cancel')
    async def cancel_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.cancel_func(interaction)

    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='➡️️ Continue')
    async def continue_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.continue_func(interaction)

#####################################################################################################################
# This Select (drop down selection) will display a drop down with the string options provided. This variant will
# allow selecting a User from a list of users
class zUserSelect(nextcord.ui.UserSelect):
    def __init__(self, submit_handler, placeholder, payload=None):
        super().__init__(min_values=1, max_values=1, placeholder=placeholder)
        self.submit_handler = submit_handler
        self.payload = payload

    async def callback(self, interaction: nextcord.Interaction) -> None:
        if self.payload is not None:
            await self.submit_handler((self.values[0], self.payload), interaction)
        else:
            await self.submit_handler(self.values[0], interaction)

#####################################################################################################################
# View which contains a zUserSelect
class zUserSelectView(nextcord.ui.View):
    def __init__(self, submit_handler, placeholder = "Select User...", payload = None):
        super().__init__(timeout=None)
        self.submit_handler = submit_handler
        self.user_select = zUserSelect(self.on_select, placeholder, payload=payload)
        self.add_item(self.user_select)
        self.selected_user = None

    async def on_select(self, user, interaction: nextcord.Interaction):
        self.selected_user = user
        if self.submit_handler is not None:
            await self.submit_handler(user, interaction)
        self.stop()

    async def prompt(self, interaction: nextcord.Interaction, msg: str = ""):
        await send_message(interaction, msg, view=self)
        await self.wait()
        return self.selected_user

########################################################################################################################
# This class is used to display a form that has fields matching the provided item list, using multiple
# modal pages if needed. The final set of data values will be sent to the provided `submit_handler` function
# as a list using the same order used in the original FieldList.
class zMultiPageModalSender():
    def __init__(self):
        pass

    ####################################################################################################################
    async def send_modal(self, interaction, fields: FieldList, submit_handler, title: str):
        self.fields = fields
        self.submit_handler = submit_handler
        self.title = title
        self.field_idx = 0
        self.submit_values = []
        for i in range(0, len(fields)):
            self.submit_values.append(None)
        await self.send_modal_page(interaction)

    ####################################################################################################################
    def get_field_index(self, custom_id):
        for (i, f) in enumerate(self.fields):
            if f.custom_id == custom_id:
                return i
        return None

    ####################################################################################################################
    async def send_modal_page(self, interaction):
        fieldDict = {}
        curr_row = 1
        # Fill in the field dictionary for the modal we're about to create and send
        while curr_row < 5 and self.field_idx < len(self.fields):
            f = self.fields[self.field_idx]
            fieldDict[f.custom_id] = nextcord.ui.TextInput(
                label=f.label,
                required=f.required,
                custom_id=f.custom_id,
                default_value=f.default_value,
                placeholder=f.placeholder,
                row=curr_row)
            curr_row += 1
            self.field_idx += 1
        # Create and send the modal
        page = math.trunc(self.field_idx / 4) + 1
        modal = zModal(fieldDict, self.on_page_submit, self.title + f" [pg. {page}]")
        await interaction.response.send_modal(modal)

    ####################################################################################################################
    async def on_page_submit(self, interaction, modal):
        # Pull out the submitted values
        for c in modal.children:
            index = self.get_field_index(c.custom_id)
            if index is not None:
                 self.submit_values[index] = c.value
            else:
                logging.info(f"**ERROR** Index not found for modal field {c.custom_id}\n  Fields: {self.fields}")

        if self.field_idx < len(self.fields):
            # If there are still fields to send, send a button message for the user to continue or cancel
            await send_message(
                interaction,
                "Continue to next page or cancel?",
                view=zContinueCancelButtonView(self.send_modal_page, self.cancel_submit))
        else:
            # Otherwise we're done, so call the originally provided submit handler
            await self.submit_handler(interaction, self.submit_values)

    ####################################################################################################################
    async def cancel_submit(self, interaction):
        await self.submit_handler(interaction, None)

########################################################################################################################
# View which contains buttons for yes and no. This is different from the zConfirmButtonView in that it calls a
# provided function with the interaction which has not been responded to. This is mostly to work around the limitation
# of send_modal not working for an interaction that's already been responded to or acknowledged 
# (zConfirmView will do the latter automatically)
class zYesNoButtonView(nextcord.ui.View):
    def __init__(self, func, payload=None):
        super().__init__(timeout=None)
        self.func = func
        self.payload = payload

    @nextcord.ui.button(style=nextcord.ButtonStyle.grey, emoji=PartialEmoji.from_str('✅'))
    async def yes_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await defer(interaction)
        await self.func(interaction, True, self.payload)
    
    @nextcord.ui.button(style=nextcord.ButtonStyle.grey, emoji=PartialEmoji.from_str('❌'))
    async def no_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await defer(interaction)
        await self.func(interaction, False, self.payload)
