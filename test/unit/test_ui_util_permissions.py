# -*- coding: utf-8 -*-
"""
Unit tests for UI utility permission functions.
Tests permission checking logic from ui/ui_util.py with mocked Discord objects.
"""
import pytest
from unittest.mock import patch, Mock
from ui.ui_util import user_has_role, user_is_admin, user_is_mod
from test.test_utils.discord_mocks import create_mock_user, create_mock_member, create_mock_role, create_mock_guild


@pytest.mark.unit
class TestUserHasRole:
    """Tests for user_has_role() function - ui/ui_util.py:39"""

    def test_user_has_role_returns_true(self):
        """Test user with the specified role returns True."""
        # Setup
        role_id = 999888777
        target_role = create_mock_role(role_id=role_id, name="Admin")
        other_role = create_mock_role(role_id=111222333, name="Member")
        
        user = create_mock_member(user_id=123456789, roles=[other_role, target_role])
        server = create_mock_guild(roles=[target_role, other_role])
        
        # Execute
        result = user_has_role(server, user, role_id)
        
        # Verify
        assert result is True

    def test_user_without_role_returns_false(self):
        """Test user without the specified role returns False."""
        # Setup
        role_id = 999888777
        target_role = create_mock_role(role_id=role_id, name="Admin")
        other_role = create_mock_role(role_id=111222333, name="Member")
        
        user = create_mock_member(user_id=123456789, roles=[other_role])  # Only has other_role
        server = create_mock_guild(roles=[target_role, other_role])
        
        # Execute
        result = user_has_role(server, user, role_id)
        
        # Verify
        assert result is False

    def test_user_with_no_roles_returns_false(self):
        """Test user with no roles returns False."""
        # Setup
        role_id = 999888777
        target_role = create_mock_role(role_id=role_id, name="Admin")
        
        user = create_mock_member(user_id=123456789, roles=[])  # No roles
        server = create_mock_guild(roles=[target_role])
        
        # Execute
        result = user_has_role(server, user, role_id)
        
        # Verify
        assert result is False

    def test_role_not_found_on_server_returns_false(self):
        """Test when role_id doesn't exist on server returns False."""
        # Setup
        role_id = 999888777  # This role doesn't exist
        other_role = create_mock_role(role_id=111222333, name="Member")
        
        user = create_mock_member(user_id=123456789, roles=[other_role])
        server = create_mock_guild(roles=[other_role])  # target_role not in server
        
        # Execute
        result = user_has_role(server, user, role_id)
        
        # Verify
        # When server.get_role returns None, the check "None in user.roles" should be False
        assert result is False

    def test_user_has_multiple_roles_including_target(self):
        """Test user with multiple roles including the target role."""
        # Setup
        role_id = 999888777
        role1 = create_mock_role(role_id=111, name="Role1")
        role2 = create_mock_role(role_id=222, name="Role2")
        target_role = create_mock_role(role_id=role_id, name="TargetRole")
        role3 = create_mock_role(role_id=333, name="Role3")
        
        user = create_mock_member(user_id=123456789, roles=[role1, role2, target_role, role3])
        server = create_mock_guild(roles=[role1, role2, target_role, role3])
        
        # Execute
        result = user_has_role(server, user, role_id)
        
        # Verify
        assert result is True

    def test_user_has_only_target_role(self):
        """Test user with only the target role (no other roles)."""
        # Setup
        role_id = 999888777
        target_role = create_mock_role(role_id=role_id, name="OnlyRole")
        
        user = create_mock_member(user_id=123456789, roles=[target_role])
        server = create_mock_guild(roles=[target_role])
        
        # Execute
        result = user_has_role(server, user, role_id)
        
        # Verify
        assert result is True

    def test_different_role_same_name(self):
        """Test that role check uses ID not name (two roles with same name)."""
        # Setup
        target_role_id = 999888777
        decoy_role_id = 888777666
        
        target_role = create_mock_role(role_id=target_role_id, name="Admin")
        decoy_role = create_mock_role(role_id=decoy_role_id, name="Admin")  # Same name, different ID
        
        user = create_mock_member(user_id=123456789, roles=[decoy_role])  # Has the decoy, not target
        server = create_mock_guild(roles=[target_role, decoy_role])
        
        # Execute
        result = user_has_role(server, user, target_role_id)
        
        # Verify - should be False because it checks by ID, not name
        assert result is False

    @pytest.mark.parametrize("has_role,expected", [
        (True, True),
        (False, False),
    ])
    def test_user_has_role_parametrized(self, has_role, expected):
        """Parametrized test for basic role checking."""
        role_id = 999888777
        target_role = create_mock_role(role_id=role_id, name="TestRole")
        
        if has_role:
            user = create_mock_member(user_id=123, roles=[target_role])
        else:
            user = create_mock_member(user_id=123, roles=[])
        
        server = create_mock_guild(roles=[target_role])
        
        result = user_has_role(server, user, role_id)
        assert result is expected

    def test_role_check_with_emoji_name(self):
        """Test role checking works with emoji in role name."""
        # Setup
        role_id = 555666777
        emoji_role = create_mock_role(role_id=role_id, name="🎮 Gamer 🎮")
        
        user = create_mock_member(user_id=123456789, roles=[emoji_role])
        server = create_mock_guild(roles=[emoji_role])
        
        # Execute
        result = user_has_role(server, user, role_id)
        
        # Verify
        assert result is True

    def test_multiple_users_same_role(self):
        """Test multiple different users can have the same role."""
        # Setup
        role_id = 999888777
        shared_role = create_mock_role(role_id=role_id, name="SharedRole")
        server = create_mock_guild(roles=[shared_role])
        
        user1 = create_mock_member(user_id=111, roles=[shared_role])
        user2 = create_mock_member(user_id=222, roles=[shared_role])
        user3 = create_mock_member(user_id=333, roles=[])
        
        # Execute & Verify
        assert user_has_role(server, user1, role_id) is True
        assert user_has_role(server, user2, role_id) is True
        assert user_has_role(server, user3, role_id) is False


@pytest.mark.unit
class TestUserIsAdmin:
    """Tests for user_is_admin() function - ui/ui_util.py:45"""

    @patch('ui.ui_util.get_server')
    @patch('config.bot_config.CoolestGuy', 999999999)
    def test_bot_owner_is_admin(self, mock_get_server):
        """Test that the bot owner (CoolestGuy) is always admin."""
        # Setup
        server = create_mock_guild(guild_id=123456)
        user = create_mock_member(user_id=999999999)  # Bot owner ID
        
        # Execute
        result = user_is_admin(server, user)
        
        # Verify
        assert result is True
        # get_server should NOT be called for bot owner (early return)
        mock_get_server.assert_not_called()

    @patch('ui.ui_util.get_server')
    @patch('config.bot_config.CoolestGuy', 999999999)
    def test_user_with_admin_role_is_admin(self, mock_get_server):
        """Test user with admin role is admin."""
        # Setup
        admin_role_id = 888777666
        admin_role = create_mock_role(role_id=admin_role_id, name="Admin")
        
        server = create_mock_guild(guild_id=123456, roles=[admin_role])
        user = create_mock_member(user_id=123456789, roles=[admin_role])  # Not bot owner, but has admin role
        
        # Mock the database server lookup
        mock_db_server = Mock()
        mock_db_server.admin_role_id = admin_role_id
        mock_get_server.return_value = mock_db_server
        
        # Execute
        result = user_is_admin(server, user)
        
        # Verify
        assert result is True
        mock_get_server.assert_called_once_with(server.id)

    @patch('ui.ui_util.get_server')
    @patch('config.bot_config.CoolestGuy', 999999999)
    def test_regular_user_is_not_admin(self, mock_get_server):
        """Test regular user without admin role is not admin."""
        # Setup
        admin_role_id = 888777666
        admin_role = create_mock_role(role_id=admin_role_id, name="Admin")
        member_role = create_mock_role(role_id=111222333, name="Member")
        
        server = create_mock_guild(guild_id=123456, roles=[admin_role, member_role])
        user = create_mock_member(user_id=123456789, roles=[member_role])  # Not bot owner, no admin role
        
        # Mock the database server lookup
        mock_db_server = Mock()
        mock_db_server.admin_role_id = admin_role_id
        mock_get_server.return_value = mock_db_server
        
        # Execute
        result = user_is_admin(server, user)
        
        # Verify
        assert result is False
        mock_get_server.assert_called_once_with(server.id)

    @patch('ui.ui_util.get_server')
    @patch('config.bot_config.CoolestGuy', 999999999)
    def test_user_with_no_roles_is_not_admin(self, mock_get_server):
        """Test regular user with no roles is not admin (but bot owner would be)."""
        # Setup
        admin_role_id = 888777666
        admin_role = create_mock_role(role_id=admin_role_id, name="Admin")
        
        server = create_mock_guild(guild_id=123456, roles=[admin_role])
        user = create_mock_member(user_id=123456789, roles=[])  # Regular user, no roles
        
        # Mock the database server lookup
        mock_db_server = Mock()
        mock_db_server.admin_role_id = admin_role_id
        mock_get_server.return_value = mock_db_server
        
        # Execute
        result = user_is_admin(server, user)
        
        # Verify
        assert result is False
        # Should check database since not bot owner
        mock_get_server.assert_called_once_with(server.id)

    @patch('ui.ui_util.get_server')
    @patch('config.bot_config.CoolestGuy', 111111111)  # Different bot owner
    def test_non_owner_with_admin_role(self, mock_get_server):
        """Test that non-owner can still be admin with admin role."""
        # Setup
        admin_role_id = 888777666
        admin_role = create_mock_role(role_id=admin_role_id, name="Admin")
        
        server = create_mock_guild(guild_id=123456, roles=[admin_role])
        user = create_mock_member(user_id=987654321, roles=[admin_role])  # Not the bot owner
        
        # Mock the database server lookup
        mock_db_server = Mock()
        mock_db_server.admin_role_id = admin_role_id
        mock_get_server.return_value = mock_db_server
        
        # Execute
        result = user_is_admin(server, user)
        
        # Verify
        assert result is True

    @patch('ui.ui_util.get_server')
    @patch('config.bot_config.CoolestGuy', 999999999)
    def test_user_with_wrong_admin_role(self, mock_get_server):
        """Test user with an admin role that's not the configured admin role."""
        # Setup
        configured_admin_role_id = 888777666
        wrong_admin_role_id = 666555444
        
        configured_admin_role = create_mock_role(role_id=configured_admin_role_id, name="RaceAdmin")
        wrong_admin_role = create_mock_role(role_id=wrong_admin_role_id, name="ServerAdmin")
        
        server = create_mock_guild(guild_id=123456, roles=[configured_admin_role, wrong_admin_role])
        user = create_mock_member(user_id=123456789, roles=[wrong_admin_role])
        
        # Mock the database server lookup
        mock_db_server = Mock()
        mock_db_server.admin_role_id = configured_admin_role_id  # Only this role grants race admin
        mock_get_server.return_value = mock_db_server
        
        # Execute
        result = user_is_admin(server, user)
        
        # Verify - should be False because they have the wrong admin role
        assert result is False


@pytest.mark.unit
class TestUserIsMod:
    """Tests for user_is_mod() function - ui/ui_util.py:54"""

    @patch('ui.ui_util.get_server')
    @patch('config.bot_config.CoolestGuy', 999999999)
    def test_admin_is_also_mod(self, mock_get_server):
        """Test that admins inherit moderator permissions."""
        # Setup
        admin_role_id = 888777666
        admin_role = create_mock_role(role_id=admin_role_id, name="Admin")
        
        server = create_mock_guild(guild_id=123456, roles=[admin_role])
        user = create_mock_member(user_id=123456789, roles=[admin_role])
        
        # Mock the database server lookup
        mock_db_server = Mock()
        mock_db_server.admin_role_id = admin_role_id
        mock_db_server.mod_role_id = 777666555
        mock_get_server.return_value = mock_db_server
        
        # Execute
        result = user_is_mod(server, user)
        
        # Verify - admin should be mod without having mod role
        assert result is True

    @patch('ui.ui_util.get_server')
    @patch('config.bot_config.CoolestGuy', 999999999)
    def test_bot_owner_is_mod(self, mock_get_server):
        """Test that bot owner is also a moderator."""
        # Setup
        server = create_mock_guild(guild_id=123456)
        user = create_mock_member(user_id=999999999, roles=[])  # Bot owner
        
        # Execute
        result = user_is_mod(server, user)
        
        # Verify
        assert result is True
        # Should return True via user_is_admin before checking mod role
        mock_get_server.assert_not_called()

    @patch('ui.ui_util.get_server')
    @patch('config.bot_config.CoolestGuy', 999999999)
    def test_user_with_mod_role_is_mod(self, mock_get_server):
        """Test user with moderator role is mod."""
        # Setup
        admin_role_id = 888777666
        mod_role_id = 777666555
        mod_role = create_mock_role(role_id=mod_role_id, name="Moderator")
        
        server = create_mock_guild(guild_id=123456, roles=[mod_role])
        user = create_mock_member(user_id=123456789, roles=[mod_role])  # Not admin, has mod role
        
        # Mock the database server lookup
        mock_db_server = Mock()
        mock_db_server.admin_role_id = admin_role_id
        mock_db_server.mod_role_id = mod_role_id
        mock_get_server.return_value = mock_db_server
        
        # Execute
        result = user_is_mod(server, user)
        
        # Verify
        assert result is True
        # Should be called twice (once in user_is_admin, once in user_is_mod)
        assert mock_get_server.call_count == 2

    @patch('ui.ui_util.get_server')
    @patch('config.bot_config.CoolestGuy', 999999999)
    def test_regular_user_is_not_mod(self, mock_get_server):
        """Test regular user without mod or admin role is not mod."""
        # Setup
        admin_role_id = 888777666
        mod_role_id = 777666555
        member_role = create_mock_role(role_id=111222333, name="Member")
        
        server = create_mock_guild(guild_id=123456, roles=[member_role])
        user = create_mock_member(user_id=123456789, roles=[member_role])
        
        # Mock the database server lookup
        mock_db_server = Mock()
        mock_db_server.admin_role_id = admin_role_id
        mock_db_server.mod_role_id = mod_role_id
        mock_get_server.return_value = mock_db_server
        
        # Execute
        result = user_is_mod(server, user)
        
        # Verify
        assert result is False

    @patch('ui.ui_util.get_server')
    @patch('config.bot_config.CoolestGuy', 999999999)
    def test_user_with_both_admin_and_mod_roles(self, mock_get_server):
        """Test user with both admin and mod roles is recognized as mod."""
        # Setup
        admin_role_id = 888777666
        mod_role_id = 777666555
        admin_role = create_mock_role(role_id=admin_role_id, name="Admin")
        mod_role = create_mock_role(role_id=mod_role_id, name="Moderator")
        
        server = create_mock_guild(guild_id=123456, roles=[admin_role, mod_role])
        user = create_mock_member(user_id=123456789, roles=[admin_role, mod_role])
        
        # Mock the database server lookup
        mock_db_server = Mock()
        mock_db_server.admin_role_id = admin_role_id
        mock_db_server.mod_role_id = mod_role_id
        mock_get_server.return_value = mock_db_server
        
        # Execute
        result = user_is_mod(server, user)
        
        # Verify
        assert result is True

    @patch('ui.ui_util.get_server')
    @patch('config.bot_config.CoolestGuy', 999999999)
    def test_mod_role_only_is_mod_not_admin(self, mock_get_server):
        """Test user with only mod role is mod but not admin."""
        # Setup
        admin_role_id = 888777666
        mod_role_id = 777666555
        admin_role = create_mock_role(role_id=admin_role_id, name="Admin")
        mod_role = create_mock_role(role_id=mod_role_id, name="Moderator")
        
        server = create_mock_guild(guild_id=123456, roles=[admin_role, mod_role])
        user = create_mock_member(user_id=123456789, roles=[mod_role])  # Only mod role
        
        # Mock the database server lookup
        mock_db_server = Mock()
        mock_db_server.admin_role_id = admin_role_id
        mock_db_server.mod_role_id = mod_role_id
        mock_get_server.return_value = mock_db_server
        
        # Execute & Verify
        assert user_is_mod(server, user) is True  # Is mod
        assert user_is_admin(server, user) is False  # But NOT admin

    @patch('ui.ui_util.get_server')
    @patch('config.bot_config.CoolestGuy', 999999999)
    def test_permission_hierarchy(self, mock_get_server):
        """Test the permission hierarchy: Owner > Admin > Mod > Regular."""
        # Setup
        admin_role_id = 888777666
        mod_role_id = 777666555
        admin_role = create_mock_role(role_id=admin_role_id, name="Admin")
        mod_role = create_mock_role(role_id=mod_role_id, name="Moderator")
        member_role = create_mock_role(role_id=111222333, name="Member")
        
        server = create_mock_guild(guild_id=123456, roles=[admin_role, mod_role, member_role])
        
        # Mock the database server lookup
        mock_db_server = Mock()
        mock_db_server.admin_role_id = admin_role_id
        mock_db_server.mod_role_id = mod_role_id
        mock_get_server.return_value = mock_db_server
        
        # Test Owner
        owner = create_mock_member(user_id=999999999, roles=[])
        assert user_is_admin(server, owner) is True
        assert user_is_mod(server, owner) is True
        
        # Test Admin
        admin = create_mock_member(user_id=111, roles=[admin_role])
        assert user_is_admin(server, admin) is True
        assert user_is_mod(server, admin) is True
        
        # Test Mod
        mod = create_mock_member(user_id=222, roles=[mod_role])
        assert user_is_admin(server, mod) is False
        assert user_is_mod(server, mod) is True
        
        # Test Regular User
        regular = create_mock_member(user_id=333, roles=[member_role])
        assert user_is_admin(server, regular) is False
        assert user_is_mod(server, regular) is False

    @patch('ui.ui_util.get_server')
    @patch('config.bot_config.CoolestGuy', 999999999)
    def test_user_no_roles_is_not_mod(self, mock_get_server):
        """Test user with no roles is not moderator."""
        # Setup
        admin_role_id = 888777666
        mod_role_id = 777666555
        
        server = create_mock_guild(guild_id=123456)
        user = create_mock_member(user_id=123456789, roles=[])
        
        # Mock the database server lookup
        mock_db_server = Mock()
        mock_db_server.admin_role_id = admin_role_id
        mock_db_server.mod_role_id = mod_role_id
        mock_get_server.return_value = mock_db_server
        
        # Execute
        result = user_is_mod(server, user)
        
        # Verify
        assert result is False

    @patch('ui.ui_util.get_server')
    @patch('config.bot_config.CoolestGuy', 999999999)
    def test_admin_doesnt_need_mod_role(self, mock_get_server):
        """Test admin is mod even without having the mod role."""
        # Setup
        admin_role_id = 888777666
        mod_role_id = 777666555
        admin_role = create_mock_role(role_id=admin_role_id, name="Admin")
        mod_role = create_mock_role(role_id=mod_role_id, name="Mod")
        
        server = create_mock_guild(guild_id=123456, roles=[admin_role, mod_role])
        user = create_mock_member(user_id=123456789, roles=[admin_role])  # Admin but NOT mod role
        
        # Mock the database server lookup
        mock_db_server = Mock()
        mock_db_server.admin_role_id = admin_role_id
        mock_db_server.mod_role_id = mod_role_id
        mock_get_server.return_value = mock_db_server
        
        # Execute
        result = user_is_mod(server, user)
        
        # Verify - admin should be mod without mod role
        assert result is True

