# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime, date
from enum import Enum
import logging
import math
import nextcord
import re
from tabulate import tabulate
import validators

from db.zBot_db_orm import *
from db.db_util import *

tabulate.PRESERVE_WHITESPACE = True

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
ModalDataList = dict[str, str]
SelectList = list[nextcord.SelectOption]

class MessageType(Enum):
    RACER_INFO   = 1
    SERVER_MOD   = 2

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
    logging.info(f"Server ID: {server.id}")
    db_server = get_server(server.id)
    return user_has_role(server, user, db_server.admin_role_id)

########################################################################################################################
# Checks if a user is a race moderator on the server
def user_is_mod(server, user):
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
async def check_user_is_mod(interaction):
    server = get_server_from_interaction(interaction)
    user = await server.fetch_member(interaction.user.id)
    is_mod = user_is_mod(server, user)
    if is_mod == False:
        await send_message(interaction, f"Only Race Moderators have permission for this function")
    return is_mod


########################################################################################################################
# Takes an AsyncRaceMessage, finds the corresponding Discord message and deletes message and optionally deletes or
# zeroes the DB entry
async def delete_message(server, async_race_msg_id, zero_db = False):
    async_race_msg = get_race_message(async_race_msg_id)

    if async_race_msg is not None:
        if async_race_msg.message_id is not None:
            channel = server.get_channel(async_race_msg.channel_id)
            try:
                msg = await channel.fetch_message(async_race_msg.message_id)
                await msg.delete()
            except:
                logging.info(f"Failed to find message with message ID {async_race_msg.message_id}")
        if zero_db:
            async_race_msg.message_id = 0
            async_race_msg.save()
        else:
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
        tens = 0
        while (tens + 10) < place:
            tens += 10
        ones_digit = place - tens
        if ones_digit == 1:
            if tens == 10:
                place_str += "th"
            else:
                place_str += "st"
        elif ones_digit == 2:
            if tens == 10:
                place_str += "th"
            else:
                place_str += "nd"
        elif ones_digit == 3:
            if tens == 10:
                place_str += "th"
            else:
                place_str += "rd"
        else:
            place_str += "th"

    return place_str

########################################################################################################################
def get_race_leaderboard_table(interaction, race_id):
    # Get the race submissions for this race, sorted by finish_time
    race_submissions = AsyncRaceSubmission.select().where(AsyncRaceSubmission.race_id == race_id)

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
            username = "" if user is None else user.display_name
            table_row = [username, s.finish_time]
            for a in extra_info_assignments:
                # Lookup the extra infos for this submission and add them to the table
                info = get_extra_info(s, a.info_type_id)
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

#####################################################################################################################
async def update_race_leaderboard(interaction, race, channel_id):
    # Remove the old message if it exists
    if race.leaderboard_message is not None:
        server = get_server(race.server_id)
        await delete_message(race.leaderboard_message.id, False)
    
    # Get the leaderboard table
    table_text = get_race_leaderboard_table(interaction, race.id)

    # Post new leaderboard message
    guild = get_server_from_interaction(interaction)
    if guild is None:
        await send_message(interaction, f"**ERROR** fetching server ID {interaction.guild_id} for race leaderboard update. Please notify a bot admin.")
        return
    channel = guild.get_channel(channel_id)
    new_msg = None
    if channel is not None:
        msg_text = f"**Leaderboard for `Race #{race.id}`**\n```\n{table_text}\n```"
        new_msg = await channel.send(msg_text)
    else:
        await send_message(interaction, f"**ERROR** fetching channel ID {channel_id} for race leaderboard update. Please notify a bot admin.")
        return

    # Update the DB with the new message info
    if new_msg is not None:
        if race.leaderboard_message is None:
            race.leaderboard_message = AsyncRaceMessage(server_id=race.server_id, channel_id=channel_id)

        race.leaderboard_message.message_id = new_msg.id
        race.leaderboard_message.save()
        await send_message(interaction, f"Race leaderboard updated for `Race #{race.id}`")
    else:
        await send_message(interaction, f"**ERROR** on race leaderboard update for `Race #{race.id}`")

########################################################################################################################
async def update_category_leaderboard(interaction, category, channel_id):
    # Get the points list, it comes pre-sorted by points high to low
    points_list = get_category_points(category.id)

    if points_list is None or len(points_list) == 0:
        await send_message(interaction, f"Could not update category leaderboard. There are no points logged for Category `{category.name}` Typically this means there are no completed races yet.")
        return
    
    # Remove the old message if it exists
    if category.leaderboard_message is not None:
        server = get_server(category.server_id)
        await delete_message(server, category.leaderboard_message.id, False)

    # Post new leaderboard message
    guild = get_server_from_interaction(interaction)
    if guild is None:
        await send_message(interaction, f"**ERROR** fetching server ID {interaction.guild_id} for category leaderboard update. Please notify a bot admin.")
        return
    channel = guild.get_channel(channel_id)
    new_msg = None
    if channel is not None:
        # Initialize the table with the labels row
        table_data = [["Name", "Points"]]
        places = []

        for i, p in enumerate(points_list):
            places.append(get_place_str(i+1))
            # Get the username
            user = interaction.client.get_user(p.user_id)
            username = "" if user is None else user.display_name
            table_data.append([username, p.points])
        
        # Tablulate the data
        table_text = tabulate(table_data, headers="firstrow", showindex=places, tablefmt="double_grid")
        msg_text = f"**Leaderboard for `{category.name}` Category**\n```\n{table_text}\n```"
        new_msg = await channel.send(msg_text)
    else:
        await send_message(interaction, f"**ERROR** fetching channel ID {db_msg.channel_id} for category leaderboard update. Please notify a bot admin.")
        return

    # Update the DB with the new message info
    if new_msg is not None:
        if category.leaderboard_message is None:
            category.leaderboard_message = AsyncRaceMessage(server_id=category.server_id, channel_id=channel_id)

        category.leaderboard_message.message_id = new_msg.id
        category.leaderboard_message.save()
        await send_message(interaction, f"Category leaderboard updated for `{category.name}`")
    else:
        await send_message(interaction, f"**ERROR** on category leaderboard update for `{category.name}`")

####################################################################################################################
# This function breaks a response into multiple messages that meet the Discord API character limit
def buildResponseMessageList(message):
    DiscordApiCharLimit = 2000 - 10
    message_list = []
    # If we're under the character limit, just send the message
    if len(message) <= DiscordApiCharLimit:
        message_list.append(message)
    else:
        # Otherwise we'll build a list of lines, then build messages from that list
        # until we hit the message limit.
        line_list = message.split("\n")
        if line_list is not None:
            curr_message = ""
            curr_message_len = 0

            for line in line_list:
                # If adding this line would put us over the limit, add the current message to the list and start over
                if curr_message_len + len(line) > DiscordApiCharLimit:
                    if curr_message == "":
                        logging.error("ERROR in buildResponseMessageList")
                        continue
                    message_list.append(curr_message)
                    curr_message = ""
                    curr_message_len = 0

                # If this single line is > 2000 characters, break it into sentences.
                if len(line) > DiscordApiCharLimit:
                    sentences = re.split('[.?!;]', line)
                    for s in sentences:
                        if curr_message_len + len(s) > charLimit:
                            if curr_message == "":
                                logging.error("ERROR in buildResponseMessageList")
                                continue
                            message_list.append(curr_message)
                            curr_message = ""
                            curr_message_len = 0
                        curr_message += s
                        curr_message_len += len(s)
                else:
                    curr_message += line + "\n"
                    curr_message_len += len(line) + 1
            if curr_message != "":
                message_list.append(curr_message)
    return message_list

#####################################################################################################################
def get_race_info_message(race):
    race_info_msg_text = "> \n"
    race_info_msg_text += f"> Use the buttons below for Race ID {race.id}\n"
    race_info_msg_text += f"> Created On: {race.create_datetime}\n"
    race_info_msg_text += "> \n"
    race_info_msg_text += f"> {race.description}\n"
    if race.additional_instructions is not None:
        race_info_msg_text += f"> {race.additional_instructions}\n"
    race_info_msg_text += "> \n"
    race_info_msg_text +=  f">        {race.seed}\n"
    race_info_msg_text += "> \n"
    if race.hash is not None and race.hash != "":
        race_info_msg_text += f"> Hash: **{race.hash}**\n"

    # Check the seed to see if it contains a link that we can embed
    seed_embed = None
    seed_parts = race.seed.split()
    seed_url = None
    for p in seed_parts:
        if validators.url(p) == True:
            seed_url = p
            break
    if seed_url is not None:
        seed_embed = nextcord.Embed(title="{}".format(race.description), url=seed_url, color=nextcord.Colour.random())
        # Add generic, creative commons licensed download thumbnail
        seed_embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/1/1e/Download-Icon.png")

    return race_info_msg_text, seed_embed

#####################################################################################################################
async def defer(interaction):
    await interaction.response.defer(with_message=True, ephemeral=True)

#####################################################################################################################
async def send_message(interaction, msg="", ephemeral=True, codeblock=False, view=None, embed=None):
    msgList = buildResponseMessageList(msg)

    for m in msgList:
        if codeblock:
            m = f"```\n{m}\n```"

        # Add the embed and view to the last message if there is one provided
        if m == msgList[-1]:
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


#################################################################################################################
async def unpin_race(race_id, interaction):
    # Get the pin message from the DB
    race = get_race(race_id)
    if race is not None:
        await delete_message(get_server_from_interaction(interaction), race.race_info_message)
        db_msg = get_race_message(race.race_info_message)
        if db_msg is not None:
            db_msg.delete_instance()
        race.race_info_message_id = None
        race.save()
    await send_message(interaction, f"Unpinned race ID {race_id}")

#################################################################################################################
def get_race_list_table(races, server_id):
    labels = ["ID", "Category", "Race Description", "# Submissions"]

    categories = AsyncRaceCategory.select().where(AsyncRaceCategory.server_id == server_id)
    if len(categories) == 0:
        logging.info(f"Error in get_race_list_table: no categories found for server ID {server_id}")
        return "An error occurred, please contact a bot admin"

    category_name_lookup = {}
    for c in categories:
        category_name_lookup[c.id] = c.name

    table_data = [labels]
    for r in races:
        num_submissions = AsyncRaceSubmission.select().where(AsyncRaceSubmission.race_id == r.id).count()
        table_data.append([str(r.id), category_name_lookup[r.category_id.id], r.description, num_submissions])

    return tabulate(table_data, headers="firstrow", tablefmt="double_grid")

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
    def __init__(self, select_list: SelectList, submit_handler, placeholder):
        self.timeout = None
        if len(select_list) > 25:
            self.orig_placeholder = placeholder
            self.orig_select_list = select_list
            self.show_more_id = -1
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
                placeholder = self.orig_placeholder))
        else:
            await self.submit_handler(int(interaction.data['values'][0]), interaction)

#####################################################################################################################
# View which contains a zSingleSelect
class zSingleSelectView(nextcord.ui.View):
    def __init__(self, select_list: SelectList, submit_handler, placeholder = None):
        super().__init__(timeout=None)
        self.selected_value = None
        self.submit_handler = submit_handler
        self.select = zSingleSelect(select_list, self.save_selected_value, placeholder)
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
# View which contains a zSingleSelect and confirm/cancel buttons
class zSingleSelectConfirmView(nextcord.ui.View):
    def __init__(self, select_list: SelectList, placeholder = None):
        super().__init__(timeout=None)
        self.selected_value = None
        self.interaction = None
        self.select = zSingleSelect(select_list, self.save_selected_value, placeholder)
        self.add_item(self.select)

    @nextcord.ui.button(style=nextcord.ButtonStyle.red, label='❌ Cancel', row=2)
    async def cancel_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.selected_value = None
        self.stop()

    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='➡️️ Continue', row=2)
    async def continue_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.interaction = interaction
        self.stop()

    async def save_selected_value(self, value, interaction):
        self.selected_value = value

    def get_selected_value(self):
        return self.selected_value
    
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
        self.selected_value = None
        self.submit_handler = submit_handler
        self.category_select = zMultiSelect(select_list, max_values, self.save_selected_value, placeholder)
        self.add_item(self.category_select)

    async def save_selected_value(self, value, interaction):
        self.interaction = interaction
        self.selected_value = value
        if self.submit_handler is not None:
            await self.submit_handler(value, interaction)
        self.stop()

    def get_selected_value(self):
        return self.selected_value
    
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

########################################################################################################################
# View which contains buttons for a yes or no question
class zYesNoCancelButtonView(nextcord.ui.View):
    def __init__(self, yes_func, no_func, cancel_func):
        super().__init__(timeout=None)
        self.yes_func = yes_func
        self.no_func = no_func
        self.cancel_func = cancel_func

    @nextcord.ui.button(style=nextcord.ButtonStyle.red, label='❌ Cancel')
    async def cancel_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.cancel_func(interaction)

    @nextcord.ui.button(style=nextcord.ButtonStyle.red, label='👎🏾 No')
    async def no_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.no_func(interaction)

    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='👍🏾 Yes')
    async def yes_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.yes_func(interaction)

########################################################################################################################
# View which contains buttons for yes, no or cancel
class zYesNoButtonView(nextcord.ui.View):
    def __init__(self, yes_func, no_func):
        super().__init__(timeout=None)
        self.yes_func = yes_func
        self.no_func = no_func

    @nextcord.ui.button(style=nextcord.ButtonStyle.red, label='👎🏾 No')
    async def no_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.no_func(interaction)

    @nextcord.ui.button(style=nextcord.ButtonStyle.blurple, label='👍🏾 Yes')
    async def yes_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.yes_func(interaction)

#####################################################################################################################
# This Select (drop down selection) will display a drop down with the string options provided. This variant will
# allow selecting a User from a list of users
class zUserSelect(nextcord.ui.UserSelect):
    def __init__(self, submit_handler, placeholder):
        super().__init__(min_values=1, max_values=1, placeholder=placeholder)
        self.submit_handler = submit_handler

    async def callback(self, interaction: nextcord.Interaction) -> None:
        await self.submit_handler(self.values[0], interaction)

#####################################################################################################################
# View which contains a zUserSelect
class zUserSelectView(nextcord.ui.View):
    def __init__(self, submit_handler, placeholder = "Select User..."):
        super().__init__(timeout=None)
        self.submit_handler = submit_handler
        self.user_select = zUserSelect(self.on_select, placeholder)
        self.add_item(self.user_select)

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
# as a ModalDataList using the same keys used in the original FieldList.
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
                logging.info(f"ERROR: Index not found for modal field {c.custom_id}\n  Fields: {self.fields}")

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
