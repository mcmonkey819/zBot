# -*- coding: utf-8 -*-
"""
Mock factories for Discord objects used in testing.
"""
from unittest.mock import Mock, MagicMock, AsyncMock
import nextcord


def create_mock_user(user_id=123456789, global_name=None, display_name=None, username=None):
    """
    Creates a mock Discord User object.
    
    Args:
        user_id: Discord user ID (int)
        global_name: User's global display name (str or None)
        display_name: User's server-specific display name (str or None)
        username: User's username (str or None)
    
    Returns:
        Mock User object with the specified attributes
    """
    user = Mock(spec=nextcord.User)
    user.id = user_id
    user.global_name = global_name
    user.display_name = display_name if display_name is not None else f"User{user_id}"
    user.username = username if username is not None else f"user{user_id}"
    user.mention = f"<@{user_id}>"
    return user


def create_mock_member(user_id=123456789, global_name=None, display_name=None, username=None, roles=None):
    """
    Creates a mock Discord Member object (guild-specific user).
    
    Args:
        user_id: Discord user ID (int)
        global_name: User's global display name (str or None)
        display_name: User's server-specific display name (str or None)
        username: User's username (str or None)
        roles: List of role IDs the member has
    
    Returns:
        Mock Member object with the specified attributes
    """
    member = Mock(spec=nextcord.Member)
    member.id = user_id
    member.global_name = global_name
    member.display_name = display_name if display_name is not None else f"Member{user_id}"
    member.username = username if username is not None else f"member{user_id}"
    member.mention = f"<@{user_id}>"
    member.roles = roles if roles is not None else []
    return member


def create_mock_role(role_id=987654321, name="TestRole"):
    """
    Creates a mock Discord Role object.
    
    Args:
        role_id: Discord role ID (int)
        name: Role name (str)
    
    Returns:
        Mock Role object with the specified attributes
    """
    role = Mock(spec=nextcord.Role)
    role.id = role_id
    role.name = name
    role.mention = f"<@&{role_id}>"
    return role


def create_mock_guild(guild_id=111222333, name="Test Server", members=None, roles=None, channels=None):
    """
    Creates a mock Discord Guild (server) object.
    
    Args:
        guild_id: Discord guild ID (int)
        name: Server name (str)
        members: List of Member objects
        roles: List of Role objects
        channels: List of Channel objects
    
    Returns:
        Mock Guild object with the specified attributes
    """
    guild = Mock(spec=nextcord.Guild)
    guild.id = guild_id
    guild.name = name
    guild.members = members if members is not None else []
    guild.roles = roles if roles is not None else []
    guild.channels = channels if channels is not None else []
    
    # Add helper method to get role by ID
    def get_role(role_id):
        for role in guild.roles:
            if role.id == role_id:
                return role
        return None
    
    guild.get_role = get_role
    
    # Add helper method to get member by ID
    def get_member(member_id):
        for member in guild.members:
            if member.id == member_id:
                return member
        return None
    
    guild.get_member = get_member
    
    # Add helper method to get channel by ID
    def get_channel(channel_id):
        for channel in guild.channels:
            if channel.id == channel_id:
                return channel
        return None
    
    guild.get_channel = get_channel
    
    return guild


def create_mock_text_channel(channel_id=555666777, name="test-channel", guild=None):
    """
    Creates a mock Discord TextChannel object.
    
    Args:
        channel_id: Discord channel ID (int)
        name: Channel name (str)
        guild: Parent guild object
    
    Returns:
        Mock TextChannel object with the specified attributes
    """
    channel = Mock(spec=nextcord.TextChannel)
    channel.id = channel_id
    channel.name = name
    channel.guild = guild
    channel.mention = f"<#{channel_id}>"
    return channel


def create_mock_interaction(user=None, guild=None, channel=None, guild_id=None, user_id=None):
    """
    Creates a mock Discord Interaction object.
    
    Args:
        user: User object (created if None)
        guild: Guild object (created if None)
        channel: Channel object (created if None)
        guild_id: Guild ID to use if creating new guild
        user_id: User ID to use if creating new user
    
    Returns:
        Mock Interaction object with the specified attributes
    """
    interaction = Mock(spec=nextcord.Interaction)
    
    # Create user if not provided
    if user is None:
        user = create_mock_user(user_id=user_id if user_id is not None else 123456789)
    interaction.user = user
    
    # Create guild if not provided
    if guild is None:
        guild = create_mock_guild(guild_id=guild_id if guild_id is not None else 111222333)
    interaction.guild = guild
    interaction.guild_id = guild.id
    
    # Create channel if not provided
    if channel is None:
        channel = create_mock_text_channel(guild=guild)
    interaction.channel = channel
    interaction.channel_id = channel.id
    
    # Add mock response object
    interaction.response = MagicMock()
    interaction.response.defer = AsyncMock()
    interaction.send = MagicMock()
    interaction.original_message = MagicMock()
    
    # Add client reference
    interaction.client = MagicMock()
    
    return interaction

