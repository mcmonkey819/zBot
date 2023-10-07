# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime, date
import logging
import math
import nextcord
import re
import validators

from db.zBot_db_orm import *

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

########################################################################################################################
# UTILITY FUNCTIONS
########################################################################################################################
# Takes an AsyncRaceMessage, finds the corresponding Discord message and deletes message and optionally deletes or 
# zeroes the DB entry
async def delete_message(server, async_race_msg_id, zero_db = False):
    async_race_msg = None
    if async_race_msg_id is not None:
        try:
            async_race_msg = AsyncRaceMessage.select().where(AsyncRaceMessage.id == async_race_msg_id).get()
        except:
            logging.info(f"Failed to find AsyncRaceMessage with ID {async_race_msg_id}")

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
    select_list = []
    for r in server.roles:
        select_list.append(nextcord.SelectOption(label=r.name, value=r.id, description=r.name))
    return select_list

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
        await self.submit_handler(interaction, self)

#####################################################################################################################
# This Select (drop down selection) will display a drop down with the string options provided. This variant will
# only allow the user to select a single option from the list. On completion it will call the provided
# submit_handler function, passing the value for the option chosen and the interaction object.
class zSingleSelect(nextcord.ui.Select):
    def __init__(self, select_list: SelectList, submit_handler, placeholder):
        super().__init__(min_values=1, max_values=1, options=select_list, placeholder=placeholder)
        self.submit_handler = submit_handler

    async def callback(self, interaction: nextcord.Interaction) -> None:
        await self.submit_handler(int(interaction.data['values'][0]), interaction)

#####################################################################################################################
# View which contains a zSingleSelect
class zSingleSelectView(nextcord.ui.View):
    def __init__(self, select_list: SelectList, submit_handler, placeholder = None):
        super().__init__(timeout=None)
        self.category_select = zSingleSelect(select_list, submit_handler, placeholder)
        self.add_item(self.category_select)

#####################################################################################################################
# This Select (drop down selection) will display a drop down with the string options provided. This variant will
# allow the user to select up to `max_values` from the list. On completion it will call the provided submit_handler
# function, passing a list of the values chosen and the interaction object.
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
        self.category_select = zMultiSelect(select_list, max_values, submit_handler, placeholder)
        self.add_item(self.category_select)

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
            await interaction.send("Additional information required",
                                   view=zContinueCancelButtonView(self.send_modal_page, self.cancel_submit),
                                   ephemeral=True)
        else:
            # Otherwise we're done, so call the originally provided submit handler
            await self.submit_handler(interaction, self.submit_values)

    ####################################################################################################################
    async def cancel_submit(self, interaction):
        await self.submit_handler(interaction, None)
