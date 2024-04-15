from nextcord.ext import commands
import nextcord
import logging
import asyncio
from datetime import datetime
import random
import config.bot_config as config
from db.db_util import *

class ServerUtils(commands.Cog, name='ServerUtils'):
    '''Cog which creates voice channels on demand.'''

    def __init__(self, bot):
        self.bot = bot
        self.test_mode = False

########################################################################################################################
# Utility Functions
########################################################################################################################
    def set_test_mode(self):
        self.test_mode = True

    async def close(self):
        pass

########################################################################################################################
# ON_READY
########################################################################################################################
    @commands.Cog.listener("on_ready")
    async def on_ready_handler(self):
        logging.info("Server Utils Ready")
        if self.test_mode:
            logging.info("  Running in test mode")

########################################################################################################################
# SERVER_UTILS_ADMIN
########################################################################################################################
# This is the main slash command that will be the prefix of all of the commands below
    @nextcord.slash_command()
    async def server_utils_admin(self, interaction):
        pass

    ####################################################################################################################
    @server_utils_admin.subcommand(description="Adds/Removes a voice channel to this server's ignore or permanent VC list")
    async def modify_vc(
        self,
        interaction,
        voice_channel: nextcord.VoiceChannel = nextcord.SlashOption(
            description="Channel to be added to the ignore list",
            required=True),
        type: int = nextcord.SlashOption(name="type",
                                         description="Type of channel to add",
                                         required=True,
                                         choices={"Ignore": 0, "Permanent": 1, "Remove": -1})):
        
        # Make sure the user has permission to run this command, for now this is just the bot owner
        if interaction.user.id != config.CoolestGuy:
            await interaction.send("You do not have permission to run this command", ephemeral=True)
            return
        
        # Remove the channel from the database if the type is -1
        if type == -1:
            # First check that this channel is in the database
            db_vc = get_vc_channel(interaction.guild_id, voice_channel.id)
            if db_vc is None:
                await interaction.send(f"Channel '{voice_channel.name}' is not in the database", ephemeral=True)
                return
            
            db_vc.delete_instance()
            await interaction.send(f"Channel '{voice_channel.name}' removed from database", ephemeral=True)
        else:
            # Otherwise we're adding as either permanent or ignore

            # First check if this channel is already in the database
            db_vc = get_vc_channel(interaction.guild_id, voice_channel.id)
            if db_vc is not None:
                await interaction.send(f"Channel '{voice_channel.name}' is already in the database as a {VcChannelType.to_str(db_vc.channel_type)} channel", ephemeral=True)
                return
            
            db_vc = ServerUtilsVcList()
            db_vc.server_id = interaction.guild_id
            db_vc.channel_id = voice_channel.id
            db_vc.channel_type = type
            db_vc.save()
            await interaction.send(f"Added Channel '{voice_channel.name}'", ephemeral=True)

    ####################################################################################################################
    @server_utils_admin.subcommand(description="Enables or disables dynamic voice channel creation")
    async def toggle_vc_create(self, interaction):
        # Make sure the user has permission to run this command, for now this is just the bot owner
        if interaction.user.id != config.CoolestGuy:
            await interaction.send("You do not have permission to run this command", ephemeral=True)
            return
        
        # Get the server from the database
        db_server = get_server(interaction.guild_id)
        if db_server is None:
            await interaction.send("Server not found in database", ephemeral=True)
            return
        
        # Toggle the enable_vc_create flag
        db_server.enable_vc_create = not db_server.enable_vc_create
        db_server.save()

        state_str = "Enabled" if db_server.enable_vc_create else "Disabled"
        await interaction.send(f"VC Creation is now {state_str} on this server", ephemeral=True)

########################################################################################################################
# ON_VOICE_STATE_UPDATE
#
# When a user joins a voice channel, this will check to make sure there is at least one empty voice channel remaining,
# if not it will add a new one. It will also clean up extra voice channels that have been created on demand when they
# are empty.
########################################################################################################################
    @commands.Cog.listener("on_voice_state_update")
    async def on_vc_update_handler(self, member, before, after):
        # Make sure this is a state change that we care about
        join_channel = after.channel
        leave_channel = before.channel
        if join_channel is None and leave_channel is None:
            logging.info("No channel change detected (before and after channels are both None)")
            return
        if join_channel == leave_channel:
            logging.info("No channel change detected (before and after are the same)")
            return
        
        # Get the server from the database to make sure dynamic VC creation is enabled
        guild = before.channel.guild if before.channel is not None else after.channel.guild
        db_server = get_server(guild.id)
       
        # If this server doesn't have dynamic VC creation enabled just return
        if db_server is None:
            logging.error(f"Server not found in database for guild ID {guild.id}")
            return
            
        if not db_server.enable_vc_create:
            logging.info("Dynamic VC creation is disabled for this server")
            return
        
        # Fetch the server ignore list and permanent VC IDs
        db_ignore_list = get_vc_ignore_list(guild.id)
        ignore_list = [vc.channel_id for vc in db_ignore_list]
        
        db_permanent_vc_list = get_vc_permanent_list(guild.id)
        permanent_vc_list = [vc.channel_id for vc in db_permanent_vc_list]

        # Make sure there's at least one permanent VC
        if len(permanent_vc_list) == 0:
            logging.error("No permanent VCs found")
            return

        # On a channel join, we'll check if there are any empty channels to join, if not we'll create a new one
        if join_channel is not None and join_channel.id not in ignore_list:
            # Check if there is at least one empty voice channel remaining, not including the ignore list or the permanent VCs
            found_empty = False
            logging.info("Channel join, checking for empty channels")
            for vc in guild.voice_channels:
                if vc.id in ignore_list: continue
                if not vc.members:
                    found_empty = True
                    logging.info(f"Found empty channel {vc.name}")
                    break

                # If no empty channels were found, create a new one by cloning the first permananent one
                if not found_empty:
                    logging.info("No empty channels, creating a new one")
                    perm_vc = guild.get_channel(permanent_vc_list[0])
                    adj = random.choice(adjectives)
                    noun = random.choice(nouns)
                    new_channel = await perm_vc.clone(name=f"{adj} {noun}")
                    new_db_channel = ServerUtilsVcList()
                    new_db_channel.server_id = guild.id
                    new_db_channel.channel_id = new_channel.id
                    new_db_channel.channel_type = VcChannelType.OnDemand
                    new_db_channel.save()

        # If the member is leaving a channel, check for empty channels to clean up
        if leave_channel is not None and leave_channel.id not in ignore_list:
            logging.info("Channel leave, checking for empty channels to clean up")
            
            # Sleep for a few seconds (in case the member accidentally disconnected and will reconnect soon)
            await asyncio.sleep(5)

            # Check for empty channels in the on demand list
            on_demand_channels = get_vc_on_demand_list(guild.id)

            # For each channel in the on demand list, check if it's empty
            # If so we'll delete it if there's at least one other empty channel
            for od in on_demand_channels:
                od_channel = guild.get_channel(od.channel_id)
                if od_channel is not None and not od_channel.members:
                    # The on demand channel is empty, check if there's another empty channel
                    for vc in guild.voice_channels:
                        if vc.id in ignore_list: continue
                        if vc.id == od.channel_id: continue
                        if not vc.members:
                            # We found another empty channel, so we can remove the on demand one we're checking
                            logging.info(f"Removing empty channel '{od_channel.name}'")
                            try:
                                await od_channel.delete()
                                od.delete_instance()
                            except:
                                logging.info(f"Failed to delete channel '{od_channel.name}'")
                            break

def setup(bot):
    bot.add_cog(ServerUtils(bot))

########################################################################################################################
# Zelda themed word lists used to generate on-demand VC names
adjectives = [
"Fast",
"Slow",
"Early",
"Late",
"Missing",
"Pointless",
"Required",
"Missing",
"Never-ending",
"Easy",
"Impossible",
"Clean",
"Terrible",
"Hidden",
"Obvious",
"Underrated",
"Convenient",
"Helpful",
"Annoying",
"Fun",
"Cute",
"Ok",
"Immediate",
"Worthless",
"Important",
"Scary",
"Beautiful",
"Funny",
"Interesting",
"Confusing",
"Unusual",
"Big",
"Swaggy",
"Fancy",
"Imaginary",
"Smart",
"Drunk",
"Angry",
"Embarrassing",
"Greedy",
"Brave",
"Suspicious",
"Satisfying",
"Organic",
"Hideous",
"Inconclusive",
"Absurd",
"Hapless",
"Successful",
"Dead"
]

nouns = [
"Sword",
"Shield",
"Moon Pearl",
"Bow",
"Boomerang",
"Hookshot",
"Bombs",
"Mushroom",
"Powder",
"Fire Rod",
"Ice Rod",
"Bombos",
"Ether",
"Quake",
"Lamp",
"Hammer",
"Shovel",
"Flute",
"Bug Net",
"Book",
"Bottle",
"Cane Of Somaria",
"Cane Of Byrna",
"Cape",
"Mirror",
"Boots",
"Gloves",
"Mitts",
"Flippers",
"Aga",
"Armos",
"Eastern",
"Lanmo",
"Desert",
"Moldorm",
"Hera",
"Helma",
"PoD",
"Arrghus",
"Swamp",
"Mothula",
"Skull Woods",
"Blind",
"Thieves Town",
"Kholdstare",
"Ice Palace",
"Vitty",
"Mire",
"Trinexx",
"Turtle Rock",
"GT",
"Ganon",
"Lost Woods",
"Kakariko",
"Bottle Vendor",
"Sick Kid",
"Smiths",
"Sanctuary",
"Zelda",
"Saha",
"Hyrule Castle",
"South Shore",
"Village of Outcasts",
"Lake Hylia",
"Death Mountain",
"Dark Death Mountain",
"Light World",
"Dark World",
"Library",
"Tavern",
"Well",
"Bonk Rocks",
"GYL",
"King's Tomb",
"Potion Shop",
"Catfish",
"Zora",
"Dam",
"Aginah",
"Maze Race",
"Dig Game",
"Stumpy",
"Big Bomb",
"Spike Cave",
"Hera Basement",
"Left Side Swamp",
"Tile Room"
]