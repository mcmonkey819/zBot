# Async Races Testing Checklist

This checklist organizes testing tasks by complexity phase, focusing on high and medium priority areas. Check off items as tests are implemented.

---

## Phase 1: Pure Functions & Simple Utils (No Dependencies)

Pure functions with deterministic outputs and no external dependencies.

### String & Formatting Functions

- [X] `get_place_str()` - `ui/ui_util.py:145` ✅
  - Test 1st, 2nd, 3rd, 11th, 12th, 13th, 21st, etc.
  - Edge case: 0 (error case)
  - *Requires: Basic pytest setup[1]*
  - **COMPLETED**: 26 tests passing, **1 critical bug fixed!**
    - Fixed modulo logic for "teens" pattern (11th, 12th, 13th)
    - Bug caused incorrect suffixes for 111th→"111st", 112th→"112nd", 113th→"113rd"
    - Now correctly handles all numbers ending in 11/12/13 (e.g., 211th, 1011th)

- [x] `format_points_str()` - `ui/ui_util.py:418` ✅
  - Test integer points (100.000 → "100")
  - Test decimal points (95.750 → "95.750")
  - Test edge cases (0.000, negative if applicable)
  - **COMPLETED**: 11 tests passing in test_ui_util_formatters.py

- [x] `build_response_message_list()` - `ui/ui_util.py:224` ✅
  - Test under character limit (simple case)
  - Test over limit requiring line splits
  - Test edge case with extremely long single line
  - Test None input
  - **COMPLETED**: 13 tests passing, **2 critical bugs fixed!**
    - Fixed undefined variable `charLimit` → `discord_api_char_limit`
    - Fixed logic order causing sentence splitting to be skipped
    - Fixed double newline issue with trailing newlines
  - **REFACTORED**: Function renamed to snake_case, improved logging with proper levels and context

- [x] `get_user_name_str()` - `ui/ui_util.py:537` ✅
  - Test with valid user having global_name
  - Test with valid user having only display_name
  - Test with None user (fallback to user_id)
  - *Requires: Discord mock factory[2]*
  - **COMPLETED**: 29 tests passing
    - Created Discord mock factory in `test/test_utils/discord_mocks.py`
    - Tests cover all name preference scenarios including edge case of "None" string
    - **Unicode/Emoji tests added**: 17 additional tests for international characters
      - Emoji support (😎🎮🏎️💨🔥🎭🎪🎨🏆👑♠️♥️♣️♦️)
      - Japanese (さくら桜子, チャンピオン)
      - Chinese (用户名), Korean (사용자), Thai (ผู้ใช้)
      - Cyrillic (Александр), Arabic (محمد), Greek (Αλέξανδρος)
      - European special chars (Ñoño, Müller, Søren)
      - Special Unicode symbols (★彡[ᴜsᴇʀ]彡★)

### Validation Functions

- [ ] ~~`game_time_is_valid()` - `db/db_util.py`~~ **SKIPPED** (DB utility, low priority)
- [ ] ~~`datetime_is_valid()` - `db/db_util.py`~~ **SKIPPED** (DB utility, low priority)

### Simple Data Transformation

- [x] `get_race_embed_field_value()` - `ui/ui_util.py:344` ✅
  - Test with user_id provided (shows place)
  - Test without user_id (shows description)
  - Test with different submission counts
  - *Requires: Race model fixtures[4]*
  - **COMPLETED**: 10 tests passing
    - Created database fixtures in `test/test_utils/db_fixtures.py`
    - Mock factories for Race, Category, Submission, ExtraInfo objects
    - Tests use `@patch` decorator to mock database query functions
    - Verified proper handling of user place display vs race description
    - Unicode/emoji support verified in category names

---

## Phase 2: Business Logic with Mocked Dependencies

Functions with business logic requiring mocked Discord objects or database models.

### Permission & Access Control (HIGH PRIORITY)

- [x] `user_has_role()` - `ui/ui_util.py:39` ✅
  - Test user with specified role
  - Test user without role
  - *Requires: Server/Role mock factory[2]*
  - **COMPLETED**: 11 tests passing
    - Tests cover role presence/absence scenarios
    - Edge cases: role not found on server, user with no roles
    - Verified role check uses ID not name (important security check!)
    - Multiple users with same role verified
    - Emoji in role names handled correctly

- [x] `user_is_admin()` - `ui/ui_util.py:45` ✅
  - Test bot owner (CoolestGuy)
  - Test user with admin role
  - Test regular user
  - *Requires: Server model mock[3]*
  - **COMPLETED**: 6 tests passing
    - Bot owner check with `@patch('config.bot_config.CoolestGuy')`
    - Database server mock for admin_role_id lookup
    - Verified early return optimization for bot owner
    - Non-owner with admin role tested
    - Wrong admin role edge case (security check!)
    - Regular user and no-role scenarios

- [x] `user_is_mod()` - `ui/ui_util.py:54` ✅
  - Test admin (inherits mod permissions)
  - Test user with mod role
  - Test regular user
  - **COMPLETED**: 9 tests passing
    - Verified inheritance: Admin → Mod → Regular hierarchy
    - Bot owner is mod (via admin inheritance)
    - Mod role grants mod permissions
    - Admin doesn't need mod role (inheritance tested)
    - Permission hierarchy test: Owner > Admin > Mod > Regular
    - User with both admin and mod roles
    - Mod-only users are mod but not admin

- [x] `can_view_race_leaderboard()` - `ui/ui_util.py:515` ✅
  - Test completed race (always viewable)
  - Test active race with user submission
  - Test active race without submission (mod can view if enabled)
  - Test active race without submission (regular user cannot view)
  - *Requires: Race submission fixtures[4]*
  - **COMPLETED**: 13 tests passing
    - Added RaceState constants to db_fixtures.py
    - Tests cover all three viewing conditions (completed, submission, mod permission)
    - OR logic verified: any single condition allows viewing
    - Edge cases: race not found, all conditions true, all conditions false
    - Different race states tested (Inactive, Active, Completed)
    - Bot owner can view via mod permission
    - Category setting mod_can_view_leaderboard respected

### Submission & Race Management (HIGH PRIORITY)

- [ ] `forfeit_race()` - `ui/ui_util.py:132`
  - Test forfeit creates submission with ForfeitFinishTime
  - Test proper timestamp setting
  - *Requires: DB mock/patch[3]*

- [ ] `get_submission_details_dict()` - `ui/ui_util.py:349`
  - Test with complete submission data
  - Test with minimal data (optional fields empty)
  - Test with extra info assignments
  - Test points formatting

- [ ] `save_message()` - `ui/ui_util.py:71`
  - Test successful save
  - Test save with different message types
  - Test save with category_id vs race_id
  - Test error handling on failed save

### Race State & Scoring (HIGH PRIORITY)

- [ ] `race_change_state()` - `ui/menus.py:1627`
  - Test Inactive → Active transition
  - Test Active → Completed transition with scoring
  - Test invalid transition (Completed → Inactive with points)
  - Test confirmation prompts for edge cases
  - Test post-state-change actions (leaderboard updates)
  - *Requires: Interaction mock with response capability[5]*

- [ ] `handle_activate_race()` - `ui/menus.py:3074`
  - Test announcement message sending (open races)
  - Test role removal logic
  - Test race pinning when category specifies
  - Test leaderboard update trigger
  - *Requires: Guild mock with members/roles[2]*

- [ ] `do_post_submit_actions()` - `ui/menus.py:3096`
  - Test role application on submission
  - Test leaderboard update trigger
  - Test with category submit role
  - Test with race-specific submit role

### Leaderboard & Display Logic (MEDIUM PRIORITY)

- [ ] `get_race_leaderboard_table()` - `ui/ui_util.py:177`
  - Test with multiple submissions
  - Test with extra info assignments
  - Test with no submissions (empty race)
  - Test proper sorting
  - *Requires: Submission fixtures with extra info[4]*

- [ ] `get_sorted_team_submissions()` - `ui/ui_util.py:543`
  - Test matched teammates (both submitted)
  - Test unmatched teammate (only one submitted)
  - Test team name from faster racer
  - Test team name fallback
  - Test average finish time calculation
  - Test proper sorting

- [ ] `export_race()` - `ui/ui_util.py:611`
  - Test CSV generation with submissions
  - Test with extra info columns
  - Test with points (completed race)
  - Test team race export
  - Test file creation and format
  - *Requires: File I/O mocking[6]*

### Message & Embed Building (MEDIUM PRIORITY)

- [ ] `get_race_info_message()` - `ui/ui_util.py:279`
  - Test embed creation with seed URL extraction
  - Test with thumbnail URL
  - Test with hash field
  - Test with additional instructions

- [ ] `get_race_leaderboard_embed()` - `ui/ui_util.py:371`
  - Test embed with submission details
  - Test pagination (current_page, per_page)
  - Test with/without show_details flag
  - *Requires: Bot client mock[7]*

- [ ] `get_category_leaderboard_embed()` - `ui/ui_util.py:433`
  - Test with points list
  - Test pagination
  - Test proper place calculation with offset

---

## Phase 3: Complex Async Interactions & UI Components

Complex functions with multiple dependencies, state management, and Discord UI interactions.

### Modal & Form Handlers (HIGH PRIORITY)

- [ ] `zRaceSubmitHandler` class - `ui/menus.py:595`
  - Test modal field generation (finish_time, comment, points)
  - Test extra info field inclusion
  - Test edit vs create scenarios
  - *Requires: Modal mock framework[8]*

- [ ] `zRaceSubmitHandler.on_submit()` - `ui/menus.py:654`
  - Test new submission creation
  - Test submission editing
  - Test validation error handling
  - Test team race teammate selection
  - Test post-submit action trigger
  - *Requires: Multi-step interaction mocking[5]*

- [ ] `zRaceSubmitHandler.save_extra_info()` - `ui/menus.py:709`
  - Test string type validation
  - Test int type validation and error
  - Test float type validation
  - Test GameTime validation
  - Test DateTime validation
  - Test optional field handling (empty values)

### Complex UI Views & Interactions (MEDIUM PRIORITY)

- [ ] `zRaceInfoButtonView` - `ui/menus.py:467`
  - Test submit_time_button logic
  - Test forfeit_button logic
  - Test leaderboard_button with permissions
  - Test team_leaderboard_button (team races only)
  - *Requires: Button callback testing framework[9]*

- [ ] `zRaceInfoButtonView.check_can_submit()` - `ui/menus.py:481`
  - Test inactive race rejection
  - Test completed race with allow_completed_submit
  - Test edit time window (4 hours)
  - Test assigned race validation
  - Test seed access time limit enforcement

- [ ] `zSingleSelectView` - `ui/ui_util.py:739`
  - Test single selection handling
  - Test "Show More" pagination (>25 items)
  - Test callback with payload
  - Test prompt() method flow

- [ ] `zMultiPageModalSender` - `ui/ui_util.py:860`
  - Test single page modal
  - Test multi-page modal (>4 fields)
  - Test field indexing across pages
  - Test continue/cancel between pages
  - Test final submission
  - *Requires: Modal pagination framework[8]*

### Command Workflows (MEDIUM PRIORITY)

- [ ] `show_race_details()` - `ui/menus.py:2249`
  - Test assigned race seed confirmation
  - Test seed_time recording on first view
  - Test cancellation handling
  - Test embed and view sending
  - *Requires: Full interaction flow mocking[5]*

- [ ] `show_race_leaderboard()` - `ui/menus.py:2390`
  - Test paginated menu creation
  - Test with various submission counts
  - Test title and description generation

- [ ] `show_category_leaderboard()` - `ui/menus.py:2523`
  - Test RecentRace leaderboard type
  - Test Points leaderboard type
  - Test no points scenario

- [ ] `race_edit_submission()` - `ui/menus.py:1764`
  - Test inactive race rejection
  - Test submission list generation
  - Test create new submission flow
  - Test edit existing submission flow
  - Test user selection for new submission
  - *Requires: Select menu interaction mocking[9]*

### Leaderboard Updates & Channel Operations (MEDIUM PRIORITY)

- [ ] `update_race_leaderboard()` - `ui/menus.py:2838`
  - Test with no submissions (early return)
  - Test message deletion and recreation
  - Test category leaderboard cascade update

- [ ] `update_category_leaderboard()` - `ui/menus.py:2820`
  - Test message lookup by category
  - Test message deletion
  - Test new leaderboard posting

- [ ] `post_channel_race_leaderboard()` - `ui/menus.py:2401`
  - Test multi-page leaderboard posting
  - Test message saving to DB
  - Test empty submissions case
  - Test save_as_category_message flag
  - *Requires: Channel mock with send()[7]*

- [ ] `post_channel_category_leaderboard()` - `ui/menus.py:2485`
  - Test RecentRace type posting
  - Test Points type posting
  - Test no races scenario

### Toggle & Configuration Functions (LOWER PRIORITY)

- [ ] `toggle_category_leaderboard_type()` - `ui/menus.py:2543`
  - Test RecentRace ↔ Points toggle
  - Test menu embed update
  - Test database persistence

- [ ] `toggle_required_extra_info()` - `ui/menus.py:2669`
  - Test required ↔ optional toggle
  - Test button style update
  - Test menu embed update

---

## Reference Section

### [1] Basic Pytest Setup
```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov
```
Create `test/conftest.py` with basic configuration.

### [2] Discord Mock Factory
Create `test/test_utils/discord_mocks.py` with factories for:
- `create_mock_user(user_id, global_name, display_name)`
- `create_mock_member(user_id, roles)`
- `create_mock_guild(guild_id, members, roles, channels)`
- `create_mock_role(role_id, name)`
- `create_mock_channel(channel_id, name)`

### [3] Database Model Mocks
Create `test/test_utils/db_fixtures.py` with:
- Mock database models (AsyncRace, AsyncRaceSubmission, etc.)
- `create_mock_race(id, state, category_id, ...)`
- `create_mock_submission(id, race_id, user_id, finish_time, ...)`
- `create_mock_category(id, name, points_type, ...)`
- Patch database query methods

### [4] Race & Submission Fixtures
Extend `db_fixtures.py` with:
- `create_race_with_submissions(num_submissions)`
- `create_team_race_with_submissions()`
- `create_extra_info_assignment(race_id, info_type_id)`
- `create_extra_info(submission_id, info_type_id, data)`

### [5] Interaction Mock Framework
Create `test/test_utils/interaction_helpers.py`:
- `create_mock_interaction(user, guild, channel, ...)`
- Mock `interaction.response.defer()`
- Mock `interaction.response.send_modal()`
- Mock `interaction.send()`
- Track calls to verify behavior

### [6] File I/O Mocking
Use `unittest.mock` or `pytest-mock`:
- Mock `open()` for CSV generation tests
- Mock `nextcord.File()` for file attachments
- Use `io.StringIO` for in-memory file operations

### [7] Bot Client Mock
Create bot client mock in `discord_mocks.py`:
- `create_mock_bot_client()`
- Mock `client.fetch_user(user_id)`
- Mock `client.get_guild(guild_id)`
- Support async operations

### [8] Modal Mock Framework
Extend `interaction_helpers.py`:
- `simulate_modal_submit(modal, field_values)`
- Mock `nextcord.ui.Modal` behavior
- Track modal.callback() invocations
- Support multi-page modal testing

### [9] Button & Select Menu Testing
Extend `interaction_helpers.py`:
- `simulate_button_click(view, button_custom_id, interaction)`
- `simulate_select_choice(view, select_custom_id, values, interaction)`
- Mock callback chains
- Verify view state changes

### Test Infrastructure Files

```
test/
├── conftest.py                    # Pytest configuration & shared fixtures
├── test_utils/
│   ├── __init__.py
│   ├── discord_mocks.py           # Discord object factories [2, 7]
│   ├── db_fixtures.py             # Database model mocks [3, 4]
│   └── interaction_helpers.py     # Interaction & UI mocks [5, 8, 9]
├── unit/
│   ├── test_ui_util_formatters.py # Phase 1 tests
│   ├── test_ui_util_permissions.py # Phase 2 permissions
│   └── test_ui_util_race_logic.py # Phase 2 race logic
├── integration/
│   ├── test_submission_flows.py   # Phase 2 & 3 submission tests
│   ├── test_race_state_flows.py   # Phase 2 state transitions
│   └── test_leaderboard_flows.py  # Phase 2 & 3 leaderboard tests
└── e2e/
    └── test_ui_interactions.py    # Phase 3 UI component tests
```

### Running Tests

```bash
# Run all tests
pytest test/

# Run with coverage
pytest --cov=ui --cov=cogs test/

# Run specific phase
pytest test/unit/  # Phase 1 mostly

# Run with verbose output
pytest -v test/
```

---

## Progress Tracking

- **Phase 1**: ✅ 5/5 tests implemented (100%) ✨ **PHASE COMPLETE!** - 2 items skipped
  - ✅ get_place_str (26 tests, 1 bug fixed)
  - ✅ format_points_str (11 tests)
  - ✅ build_response_message_list (13 tests, 2 bugs fixed, refactored to snake_case)
  - ✅ get_user_name_str (29 tests, Discord mock factory created, Unicode/emoji support verified)
  - ✅ get_race_embed_field_value (10 tests, database fixtures created)
  - ⏭️ game_time_is_valid (SKIPPED - DB utility)
  - ⏭️ datetime_is_valid (SKIPPED - DB utility)
- **Phase 2**: ✅ 4/24 tests implemented (17%)
  - ✅ user_has_role (11 tests, permission checking)
  - ✅ user_is_admin (6 tests, bot owner + role-based admin)
  - ✅ user_is_mod (9 tests, inheritance hierarchy verified)
  - ✅ can_view_race_leaderboard (13 tests, complex OR logic with multiple conditions)
- **Phase 3**: ☐ 0/21 tests implemented
- **Total**: ✅ 9/54 tests implemented (17%) - 2 items skipped from total
- **Total Tests Written**: 128 tests passing ✅ 🎯
- **Bugs Found**: 3 bugs caught and fixed by tests! 🎯
- **Test Infrastructure Created**:
  - Discord mock factory (`test/test_utils/discord_mocks.py`)
  - Database fixtures (`test/test_utils/db_fixtures.py`)
  - Permission tests (`test/unit/test_ui_util_permissions.py`)

**Last Updated**: can_view_race_leaderboard completed (128 total tests)

