# Trials Automation — Implementation Plan

## Overview

Add a suite of commands to automate the lifecycle of a Trial: announcing signups via
reaction tracking, creating the Discord and bot infrastructure, running weekly races with
auto-assignment, and cleaning up when the trial ends.

The "Trial" concept is server-agnostic — one server may call them "Triforce Trials", another
"Battle Royales". The bot uses "Trial" as the canonical internal name throughout.

All new trial commands are `async_mod` accessible. The prerequisite server configuration
command is `async_admin` only.

---

## Command List

| Command | Group | Description |
|---|---|---|
| `/async_admin server_config` | async_admin | Configure server-level settings (roles, VC, trials) |
| `/async_mod announce_trial` | async_mod | Post signup announcement, create participant role, begin reaction tracking |
| `/async_mod cancel_trial` | async_mod | Cancel an unstarted trial and clean up created objects |
| `/async_mod start_trial` | async_mod | Create channels, spoiler role, and bot category; transition to Active |
| `/async_mod start_trial_race` | async_mod | End previous race (if any), update racer list, create and activate next race |
| `/async_mod end_trial` | async_mod | Mark the final race complete; spoiler discussion continues |
| `/async_mod archive_trial` | async_mod | Remove channels, roles, and archive DB records |

---

## Prerequisites (implement first)

### 1. Bug fix: NULL admin/mod roles on startup
The startup command prompts for admin/mod roles when the DB fields are blank, but the prompt
does not save correctly — selecting roles and confirming leaves the fields blank in the DB,
causing the prompt to repeat on the next startup.

The fix has two independent parts:
- **Code bug:** The startup prompt flow has a save defect (likely not calling `.save()` on the
  server record after setting the fields). This is replaced entirely by the `server_config`
  command — the broken code path is simply removed.
- **Schema migration (still needed):** `mod_role_id` and `admin_role_id` are `IntegerField()`
  without `null=True`. Once the startup prompt is removed, a server can legitimately exist in
  the DB without roles configured yet. Without `null=True`, peewee generates `INTEGER NOT NULL`
  and a new server record cannot be inserted with roles unset. Making them nullable is required
  for the server_config approach to work correctly.

### 2. `/async_admin server_config`
A new command that presents a configuration interface for server-level settings. Replaces
the missing-role prompts in startup.

**Flow:**
1. Send ephemeral embed showing current config (roles show ✅ if set, ❌ if unset)
2. Row 1: [Set Admin Role] [Set Mod Role] buttons → each opens a Select flow to pick a role
3. Row 2: [VC Creation: ON/OFF toggle] button
4. Row 3: [Trials: Enabled/Disabled toggle] button
5. If Trials enabled: [Set Announcement Channel] [Set Trials Discord Category] buttons,
   each presenting a Select populated from server channels/categories
6. [Done] button to dismiss

**DB changes to `AsyncRaceServer`** (migration required):
- `mod_role_id` → nullable
- `admin_role_id` → nullable
- `trials_enabled` (BooleanField, default False)
- `trials_announcement_channel_id` (IntegerField, null=True)
- `trials_discord_category_id` (IntegerField, null=True) — Discord channel category ID

> Note: server `id` and `name` are Discord-owned and must not be editable here.

---

## Database Schema — New Table: `Trial`

```python
class TrialState:
    Announcing = 0   # announce_trial run, reactions being tracked
    Active     = 1   # start_trial run, channels/roles/category exist
    Ended      = 2   # end_trial run, final race complete
    Archived   = 3   # archive_trial run, cleanup done
    Cancelled  = 4   # cancel_trial run

class Trial(Model):
    id                      = IntegerField(primary_key=True)
    server_id               = ForeignKeyField(AsyncRaceServer, backref='trials')
    short_name              = CharField()           # e.g. "TTPFour-enzy" — used for channel/role names
    display_name            = CharField()           # e.g. "TTP Season 4 Frenzy" — used for bot category
    short_description       = CharField()           # bot category description (short)
    announcement_text       = TextField(null=True)  # full text posted in announcement; null if manually posted
    state                   = IntegerField(default=0)
    accept_signups          = BooleanField(default=True)  # False after first race closes
    announcement_message_id = IntegerField(null=True)
    announcement_channel_id = IntegerField(null=True)
    general_channel_id      = IntegerField(null=True)
    spoilers_channel_id     = IntegerField(null=True)
    participant_role_id     = IntegerField(null=True)   # assigned on reaction add
    finisher_role_id        = IntegerField(null=True)   # assigned on submission, cleared on next race
    category_id             = ForeignKeyField(AsyncRaceCategory, null=True)
    current_race_id         = ForeignKeyField(AsyncRace, null=True)
    organizer_user_id       = IntegerField(null=True)   # pinged/DMed when min_signups is reached
    min_signups             = IntegerField(null=True)   # minimum signups before organizer is notified
    min_signups_notified    = BooleanField(default=False)

    class Meta:
        table_name = 'trials'
        database = db
```

Migration required: create `trials` table and add new `AsyncRaceServer` columns.

---

## Reaction Tracking

The bot listens to `on_raw_reaction_add` and `on_raw_reaction_remove` events (cog listeners).
All reactions on all messages are received; filter by `payload.message_id` against active trial
`announcement_message_id` values.

**Cache strategy:** On bot startup, load all trials in `Announcing` or `Active` state with a
non-null `announcement_message_id` into a `dict[int, Trial]` keyed by message ID.
Update the cache on announce_trial, cancel_trial, and when `accept_signups` is set to False.

**on_raw_reaction_add:**
1. Check cache for message_id — ignore if not found
2. Ignore bot reactions
3. If trial `accept_signups` is False — ignore (race already closed)
4. Fetch member, assign `participant_role_id`
5. Save nothing extra — role membership IS the state
6. If `min_signups` is set and `min_signups_notified` is False:
   - Count members currently holding `participant_role_id`
   - If count >= `min_signups`: DM or ping `organizer_user_id` with a notification message,
     set `min_signups_notified = True` on the Trial record

**on_raw_reaction_remove:**
1. Check cache for message_id — ignore if not found
2. Fetch member, remove `participant_role_id`
3. If trial `accept_signups` is True and trial has a `current_race_id`:
   - Check if user is on the race roster with no submission
   - If so, remove from roster (week 1 only — late withdrawal after signups close does not
     unassign the racer)

---

## Command Flows

### `/async_mod announce_trial`

**Purpose:** Post signup announcement (or attach to an existing one), create participant role,
begin tracking reactions.

**Slash command parameter:** `message_id` (optional, type `str`) — the ID of an existing
announcement message already posted manually. Use `str` to avoid Discord INTEGER precision
loss on snowflake IDs (same pattern as `server_id` in startup/shutdown).

**Flow — without `message_id` (bot posts the announcement):**
1. Check `trials_announcement_channel_id` is configured — error if not
2. Modal A — trial identity (4 fields):
   - Short name (e.g. `TTPFour-enzy`) — used for channel/role naming
   - Display name (e.g. `TTP Season 4 Frenzy`) — used for bot category
   - Short description — for bot category (limit ~100 chars)
   - Announcement text — text for the post (up to 4000 chars)
3. Modal B — signup settings (2 fields):
   - Organizer (user mention or ID) — pinged/DMed at minimum signup threshold
   - Minimum signups to notify organizer (number; leave blank to disable)
4. Bot proposes participant role name: `"TTPFour-enzy"`
   - [Edit Name] [Create Role] buttons; Edit → modal with single pre-populated text field
5. Create role in Discord
6. Post announcement to `trials_announcement_channel_id`
7. Save `Trial` record (state=Announcing) with message ID, channel ID, role ID,
   organizer_user_id, min_signups
8. Add to reaction tracking cache
9. Confirm: "Announcement posted. Tracking reactions for signups."

**Flow — with `message_id` (attach to existing post):**
1. Parse `message_id` as `int`
2. Check `trials_announcement_channel_id` is configured — error if not
3. Fetch the message from `trials_announcement_channel_id` to verify it exists — error if not found
4. Modal A — trial identity (3 fields, no announcement text since post already exists):
   - Short name
   - Display name
   - Short description
5. Modal B — signup settings (same as above)
6. Bot proposes participant role name — same [Edit] / [Create Role] flow
7. Create role in Discord
8. Save `Trial` record with the provided message ID, `announcement_text = null`
9. Add to reaction tracking cache
10. Confirm: "Attached to existing message. Tracking reactions for signups."

**Error handling:**
- `message_id` provided but message not found in announcement channel → error, nothing created
- Role creation fails → report error, no DB record written
- Announcement post fails (bot-posted path) → delete created role, report error
- No partial state left on failure in either path

---

### `/async_mod cancel_trial`

**Purpose:** Cancel a trial that has not yet started (Announcing state).

**Flow:**
1. Select trial in Announcing state (error if none)
2. Check: any associated races with submissions → hard error, do nothing:
   `"Cannot cancel — this trial has races with submissions. Use /end_trial and /archive_trial instead."`
3. Confirm: `"Cancel '[Display Name]'? This will delete the participant role and announcement message."`
   [Confirm Cancel] [Abort] buttons
4. On confirm:
   a. Delete announcement message (warn if already deleted, continue)
   b. Remove participant role from all members, delete role (warn on failure, continue)
   c. Delete any races with zero submissions associated with the trial
   d. Delete bot category if created (no races with submissions, so safe)
   e. Delete `Trial` DB record
   f. Remove from reaction cache
5. Report summary of what was cleaned up

**Error handling:** Each step is independent. Failures are collected and reported at the end;
they do not stop the remaining cleanup.

---

### `/async_mod start_trial`

**Purpose:** Create the Discord channels, spoiler role, and bot category. Transitions trial
from Announcing → Active.

**Flow:**
1. Select trial in Announcing state (error if none)
2. Show current signup count (members with participant role)
3. Confirm channel names — bot proposes based on `short_name.lower()`:
   - General: `#ttpfour-enzy` → [Edit] [Create]
   - Spoilers: `#ttpfour-enzy-spoilers` → [Edit] [Create]
   - Channels created inside `trials_discord_category_id`
   - General: open to all (@everyone can view)
   - Spoilers: viewable only by `finisher_role_id` and `admin_role_id` (inherit category for server admins)
4. Confirm finisher role name — bot proposes `"TTPFour-enzy Finisher"` → [Edit] [Create]
5. Bot category settings — presented as standalone Select objects and an embed with toggle
   buttons (Selects are not supported inside modals; follow existing zBot UI patterns and
   reuse existing view classes where applicable):
   - Select: Scoring type (No Scoring / Points / TrueSkill)
   - Toggle: [Post Leaderboard to Channel ✅/❌]
   - Select: Leaderboard type — only shown if "Post Leaderboard to Channel" is enabled.
     If scoring type is No Scoring, leaderboard type is automatically set to "Recent Race"
     (cumulative scoring leaderboard is meaningless without points) and this Select is skipped.
   - Embed with emoji toggle buttons, each flipping between ✅/❌ on click:
     [Mods Can View Leaderboard] [Disable Edit Timeout] [Disable Auto-Forfeit]
     + [Done] button to confirm
   - `activate_new_races` and `pin_recent_race` are always False for trials — not shown
6. Create the bot category now with the collected settings, before extra info assignment,
   so extra info types can be assigned to the live category ID without caching.
7. Extra info assignment loop:
   - "Add extra fields beyond Finish Time and Comment?" [Yes] [No]
   - If Yes: Select populated with existing Extra Info types for this server + "Create New..."
     option at the top
     - If an existing type is selected: assign it to the category immediately
     - If "Create New..." is selected: walk through the ExtraInfo type creation workflow
       (matching the existing flow from the mod menu), then assign the new type to the category
   - After each assignment: "Add another extra field?" [Yes] [No]
   - Loop until No is selected
8. Update `Trial` record with channel IDs, role ID, category ID; set state=Active

**Error handling:**
- Each Discord object creation is attempted in order; on failure, any objects created in this
  run are deleted and the trial stays in Announcing state
- Partial progress tracking: record each created object ID before moving to the next step so
  rollback knows what to clean up
- User cancellation at any confirmation step → same rollback

---

### `/async_mod start_trial_race`

**Purpose:** End the previous race (if any), optionally update the racer list, then create
and activate the next race with auto-assignment.

**Flow:**
1. Select trial in Active state
2. If `current_race_id` exists:
   - Confirm: `"End current race '[Race Name]' before starting next?"` [Confirm] [Abort]
   - On confirm: mark race as Completed
   - Remove finisher role from all participants (clear slate for new race)
3. If this is the first race and `accept_signups` is True:
   - `"Continue accepting signups through this race, or close now?"` [Close Now] [Keep Open]
   - If Close Now: set `accept_signups = False`, remove from reaction cache
4. Racer removal loop:
   - `"Remove any racers from this race? [X racers currently signed up]"` [Remove a Racer] [No, Continue]
   - If Remove: Select of current participant role members → remove chosen member's participant role
   - Loop until user selects "No, Continue"
   - Note: adding racers is done manually (add participant role in Discord) before running this command
5. Modal: race details (seed, hash, description, additional instructions — match existing race creation fields)
6. Auto-assign all current participant role holders to the new race
7. Activate race (set state = Active)
8. Post race info message to `general_channel_id` (using `post_race_info_message`)
9. Update `Trial.current_race_id`
10. Report: `"Race '[Name]' started. [N] racers assigned."`

**Error handling:**
- Previous race end fails → abort, report error
- Race creation fails → report, no partial race saved
- Assignment failures: report each failure, then ask the user:
  `"Some racers could not be assigned. Continue to activate and pin, or stop?"` [Continue] [Stop]
  - If Stop: report errors, note that the organizer must manually check assignments, activate
    the race, and pin the race info. `Trial.current_race_id` is still updated (step 9) so the
    trial record is consistent.
  - If Continue: proceed to activate and pin as normal
- Pin failure reported as warning — race is active regardless

---

### `/async_mod end_trial`

**Purpose:** Mark the final race complete. Leaves channels and roles intact for post-trial
discussion. Transitions trial to Ended state.

**Flow:**
1. Select trial in Active state with a current race
2. Confirm: `"Mark '[Race Name]' as the final race and complete it?"` [Confirm] [Abort]
3. Mark `current_race_id` as Completed
4. Update `Trial.state = Ended`
5. Set `accept_signups = False`, remove from reaction cache
6. Report: `"Trial ended. Channels and roles remain until /archive_trial is run."`

> Leaderboard updates are handled automatically by the category's leaderboard type and channel
> settings — no manual post step is needed here.

**Error handling:**
- Race already Completed → idempotent; still update trial state and confirm

---

### `/async_mod archive_trial`

**Purpose:** Remove Discord channels and roles, archive bot category. Final cleanup.
Transitions trial to Archived state.

**Flow:**
1. Select trial in Ended state
2. Show ephemeral summary of objects associated with the trial:
   - Channels: `#ttpfour-enzy`, `#ttpfour-enzy-spoilers`
   - Roles: `TTPFour-enzy`, `TTPFour-enzy Finisher`
   - Bot category: `[Display Name]` (deactivated, not deleted — preserves history)
3. Present action buttons — user selects what to remove:
   - [Category Only] — deactivate bot category only; leave channels and roles
   - [Remove Roles & Category] — remove both roles + deactivate category; leave channels
   - [Remove Channels & Category] — delete both channels + deactivate category; leave roles
   - [Remove All] — remove channels, roles, and deactivate category
   - Abort is implicit: dismiss the ephemeral message without clicking
4. Execute selected actions:
   - Channel deletion: delete spoilers channel, then general channel
   - Role removal: remove finisher role from all members and delete it;
     remove participant role from all members and delete it
   - Category: deactivate (`active = False`) — preserves race/submission history
5. Update `Trial.state = Archived`
6. Report summary: what was done, what failed (failures are warnings, not blockers)

**Error handling:** Each step is independent. The trial is marked Archived even if some
Discord object deletions fail (e.g. channel already deleted). Failures listed in summary.

---

## Submission Hook: Assign Finisher Role

In the existing submission handler (`check_can_submit` / submission flow in `ui/menus.py`):
- After a successful submission, check if the race belongs to an Active trial
- If so, assign the trial's `finisher_role_id` to the submitting user
- This unlocks the spoilers channel for them

This requires a lookup: given a `race_id`, find the `Trial` with `current_race_id` matching.
A simple DB query on submission; no caching needed.

---

## Implementation Phases

### Phase 0 — Prerequisites
1. DB migration: make `mod_role_id` / `admin_role_id` nullable in `AsyncRaceServer`; create `trials` table; add new `AsyncRaceServer` fields
2. Remove automatic role prompt from startup command
3. Implement `/async_admin server_config`

### Phase 1 — Announcement & Signup Tracking
4. Implement `Trial` model in ORM and db_util helpers
5. Implement `/async_mod announce_trial`
6. Implement reaction tracking listeners (`on_raw_reaction_add` / `on_raw_reaction_remove`)
7. Implement `/async_mod cancel_trial`

### Phase 2 — Trial Start
8. Implement `/async_mod start_trial` (channels, roles, category)

### Phase 3 — Race Lifecycle
9. Implement `/async_mod start_trial_race` (end previous, update roster, create+activate+pin)
10. Implement finisher role assignment on submission
11. Implement `/async_mod end_trial`

### Phase 4 — Cleanup
12. Implement `/async_mod archive_trial`

---

## Implementation Notes

- **UI patterns:** Follow existing zBot conventions throughout. Reuse existing view/UI classes
  where applicable (e.g. race creation view for race detail modals, ExtraInfo creation view for
  the create-new extra info flow). For modal and Select limits, apply the same patterns already
  used elsewhere in the codebase — split across multiple steps with Continue buttons where
  needed for modals, and handle large option lists the same way existing Selects do.

---

## Post-Implementation Gaps & Enhancements

Identified after initial implementation and testing. All three items are unimplemented as of the
`feature/trials-phase0` merge.

---

### Gap 1 — Reaction Signup During Active Race

**Problem:** `on_raw_reaction_add_handler` assigns the participant role when a user reacts to the
announcement. However, if a race is already active and `accept_signups` is True (signups kept open
through the race), the new participant is not assigned to the current race. They will be picked up
on the next `start_trial_race` call but miss the current one.

**Fix:** In `on_raw_reaction_add_handler`, after assigning the participant role, check if
`trial.current_race_id` is set and `trial.accept_signups` is True. If so, call
`assign_racer(member.id, trial.current_race_id)` to immediately add them to the active race.

**Scope:** `cogs/async_races.py` — `on_raw_reaction_add_handler`. No DB changes needed.

---

### Gap 2 — Additional Instructions Field Missing from Trial Race Details Modal

**Problem:** `TrialRaceDetailsModal` has three fields (description, seed, hash) but the standard
race creation flow also includes an "Additional Instructions" optional field. Trial races have no
way to provide per-race instructions beyond the description.

**Fix:** Add a 4th `paragraph`-style `TextInput` field ("Additional Instructions", optional) to
`TrialRaceDetailsModal`. Read it in `TrialStartRaceFlow._on_race_details_submit`, store it on the
flow, and pass it to the race record in `_create_and_activate`. Verify the exact field name on
`AsyncRace` before implementing.

**Scope:** `ui/menus.py` — `TrialRaceDetailsModal`, `TrialStartRaceFlow`. No DB changes needed.

**Document update:** Add "Additional Instructions (optional)" to the Race Details form fields list
in Step 4 of `TRIALS_BOT_COMMANDS.md`.

---

### Enhancement — Leaderboard Channel Selection in `start_trial`

**Problem:** `start_trial` lets the organizer enable a leaderboard via the category settings, but
provides no way to set the leaderboard channel. Currently the organizer must set this manually
through the mod menu after the trial starts.

**Design:**

After the organizer clicks **Confirm Settings** in `TrialCategorySettingsView`:
- If `post_leaderboard` is False → proceed directly to extra info loop (no change)
- If `post_leaderboard` is True → show `TrialLeaderboardChannelView` with two buttons:
  - **Create New Channel** — bot creates a dedicated leaderboard channel and stores its ID on the
    trial record for archive cleanup
  - **Use Existing Channel** — presents a channel picker; selected channel is linked to the
    category but NOT stored on the trial record (it is not bot-owned and must not be deleted on
    archive)

After the channel decision, proceed to extra info loop as normal, then call `on_settings_confirmed`
where the channel is linked to the category.

**Channel creation — permissions by leaderboard type:**
- **Points leaderboard** — open to `@everyone` (read access); created inside
  `trials_discord_category_id`
- **Most Recent Race leaderboard** — same permissions as the spoilers channel: `@everyone:
  read_messages=False`, `finisher_role: read_messages=True`, `bot: read_messages=True`. Because
  the finisher role does not exist yet at the time the user makes this decision, the actual channel
  creation must happen inside `on_settings_confirmed` after the finisher role is created.

**Archive cleanup:**
- `Trial.leaderboard_channel_id` is only set when the bot created the channel (Create New path).
- `archive_trial` deletes this channel if the field is non-null, same as general/spoilers channels.
- If the field is null (Use Existing path), no channel deletion is attempted.
- The archive summary embed should include the leaderboard channel in the Channels field only when
  `leaderboard_channel_id` is non-null.

**DB changes:**
- Add `leaderboard_channel_id = IntegerField(null=True)` to the `Trial` table (migration required)
- Verify the field name for leaderboard channel on `AsyncRaceCategory` before implementing

**Scope:** `ui/menus.py` — `TrialCategorySettingsView`, `TrialStartFlow`, new
`TrialLeaderboardChannelView`; `db/db_util.py` — new helper if needed; migration script.

**Document update:** Add a new sub-step after Confirm Settings in Step 3 of
`TRIALS_BOT_COMMANDS.md` describing the leaderboard channel prompt. Update Step 6 (Archive) to
note that a bot-created leaderboard channel is included in the "Remove Channels" cleanup.
