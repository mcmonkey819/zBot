# Trials Bot Commands — Organizer Guide

This guide covers the slash commands that automate the full lifecycle of a Trial: from announcing
signups through weekly races to final archival. It assumes you are familiar with how Trials work
and focuses on the bot commands that replace the previously manual setup steps.

Trial management commands start with the prefix `/async_mod`. However, Discord will show a list of
commands if you just type `/` and the command name. For example, typing `/announce` will show an
autocomplete list that includes the full announce trial command that you can click to autocomplete.

---

## Quick Reference

| Command | Who Can Use | Purpose |
|---|---|---|
| `/async_mod announce_trial` | Mods | Post signup announcement, create participant role, begin reaction tracking |
| `/async_mod cancel_trial` | Mods | Cancel an unstarted trial, delete participant role and announcement message |
| `/async_mod start_trial` | Organizer, Mods | Create general channel, spoilers channel, finisher role, and bot race category |
| `/async_mod start_trial_race` | Organizer, Mods | End the previous race (if any), manage participant list, and start the next race |
| `/async_mod end_trial` | Organizer, Mods | Mark the trial as ended and close the final race |
| `/async_mod archive_trial` | Organizer, Mods | Remove Discord channels/roles and archive the trial category |

---

## Key Concepts

**Participant role** — A Discord role created when the trial is announced. Users receive this role
automatically when they react to the announcement message, and lose it when they un-react. The
participant role is how the bot tracks who is signed up and is used to auto-assign racers to each
weekly race. The organizer can also manually add or remove participants each time a new race is
started using the bot's participant management step.

**Finisher role** — A Discord role that grants access to the spoilers channel. It is assigned to a
racer automatically when they submit their time for the current race. When the next race starts, the
role is stripped from everyone, closing spoilers access until they submit again. This ensures only
racers who have finished the current week's seed can see spoiler discussion.

**Bot race category** — An internal bot construct (separate from a Discord channel category) that
holds the trial's scoring settings, extra info fields, and race history. All races created for the
trial belong to this category. The category is deactivated (but not deleted) when the trial is
archived, preserving the full race record permanently.

---

## Full Lifecycle

### Step 1 — Announcing the Trial

> *Run by a Mod.*

Run `/async_mod announce_trial`. The bot walks you through:

1. **Select organizer** — choose the Discord member who will run this trial, or click
   **No Organizer** to leave it unassigned. The organizer is notified when minimum signups are
   reached and can run start/race/end commands on their own trial without needing a mod role.
   Mods can always run trial commands for any trial regardless of who the organizer is.

2. **Trial details** — a form asking for:
   - **Trial Name** — used for display, channel names, and role names. It will be converted to
     lowercase with spaces replaced by dashes for channel and role naming (e.g. `TTP Season 4`
     becomes `ttp-season-4`), so keep it concise.
   - **Short Description** — shown in the bot race category
   - **Minimum Signups** — how many signups trigger an organizer notification (leave blank to disable)
   - **Announcement Text** — the text of the signup post. Supports multiple lines and Discord
     formatting such as bold, italic, links, and spoiler tags. Omit if attaching to an existing
     message (see below).

3. **Participant role name** — the bot proposes a name based on the trial name. Click **Edit Name**
   to change it or **Next** to accept.

4. The bot creates the participant role, posts the announcement to the server configured announcement
   channel, and begins tracking reactions. Users who react to the announcement are automatically
   assigned the participant role; users who un-react have it removed.

> **Attaching to an existing announcement:** If a signup post was already made manually, pass its
> message ID as the optional `message_id` parameter. The bot will attach to that message instead of
> posting a new one. The announcement text field is omitted from the form in this case.

---

### Step 2 — Cancelling (If Needed)

> *Run by a Mod. Only available while the trial is in Announcing state.*

Run `/async_mod cancel_trial`. If there is only one announcing trial the bot selects it
automatically; otherwise you choose from a list. A confirmation embed is shown before anything is
deleted. On confirm, the bot removes the participant role, deletes the announcement message, and
removes the trial record. This command is blocked if the trial already has any races with
submissions — use `/async_mod end_trial` and `/async_mod archive_trial` instead.

---

### Step 3 — Starting the Trial

> *Run by the organizer or a Mod. Transitions the trial from Announcing → Active.*

Run `/async_mod start_trial`. If you have permission to start multiple trials a selection prompt
appears; otherwise the bot proceeds directly. The flow:

1. **Channel names** — the bot proposes a general channel name based on the trial name (e.g.
   `#ttp-season-4`) and a spoilers channel (e.g. `#ttp-season-4-spoilers`). Click **Edit** to adjust
   either name, then **Next** to confirm.

   - The **general channel** is visible to everyone and is where race info is posted each week.
   - The **spoilers channel** is hidden by default; access is gated by the finisher role.

2. **Finisher role name** — the bot proposes a name. Edit or accept with **Next**.

3. **Scoring type** — select how races in this trial will be scored:

   | Scoring Type | Description |
   |---|---|
   | **No Scoring** | Races are tracked but no points are assigned. Use when standings are not needed. |
   | **MarioKart** | Points assigned by finishing position (1st earns the most). The most common choice for Trials. |
   | **Trueskill** | Microsoft's TrueSkill rating system. Adjusts ratings based on expected vs. actual finishing order, accounting for skill differences between participants. |
   | **Par Time** | Points based on how close a racer's time is to a par time calculated from the top finishers. Rewards faster times rather than just relative placement. |
   | **Fixed** | 3 points for a win, 1 point for a tie or close loss. Point values are configurable. |

4. **Bot category settings** — review and adjust the race category settings using the toggle
   buttons. Most defaults are appropriate for Trials. Click **Confirm Settings** when done.

   | Setting | Description |
   |---|---|
   | **Post Leaderboard** | When enabled, the bot posts and automatically updates a standings message in a channel after each race. |
   | **Leaderboard Type** | *(Shown only when Post Leaderboard is enabled)* **Points** shows cumulative totals across all races. **Most Recent Race** shows only the latest race results. |
   | **Mods View LB** | When enabled, mods can view the leaderboard embed in addition to regular participants. |
   | **Disable Edit Timeout** | Normally racers have a 4-hour window to edit their submission. Enabling this removes the time limit. |
   | **Disable Auto-Forfeit** | Normally racers who have not submitted when a race closes are auto-forfeited. Enabling this skips auto-forfeit. Defaults to **ON** for Trials. |

5. **Extra info fields** — optionally assign additional submission fields (e.g. VoD link, attempt
   count). Click **Edit Extra Info** to open the selection menu:
   - Existing types can be selected from the dropdown. Fields already assigned show a ✅.
   - Selecting an assigned field removes it.
   - Choose **Create New...** to define a new field type (name, description, data type).
   - When adding a field, you are asked whether it should be **Required** or **Optional**.
   - Click **Done** when finished.

The bot then creates the general channel, spoilers channel, finisher role, and bot race category in
Discord and database. The trial is now **Active** and ready for races.

> **If the flow is interrupted mid-way:** The bot saves progress after each Discord object is
> created. If you run `/async_mod start_trial` again on the same trial, it will detect the partial
> state and offer two options: **Rollback Partial Start** (delete what was created and start over)
> or **Continue Setup** (resume from where it left off).

---

### Step 4 — Starting a Race

> *Run by the organizer or a Mod. Repeat each week.*

Run `/async_mod start_trial_race`. The flow:

1. **End previous race** *(if one exists)* — the bot automatically ends and scores the previous
   race before proceeding.

2. **Signup decision** — choose whether to **Close Signups** (prevent new participants from joining
   via the announcement) or **Keep Signups Open** (allow new reactions to grant the participant role
   during the race).

3. **Participant management** — review and adjust who is in the race before it is created. Three
   buttons are available:

   - **Add Racer** — opens a Discord member picker. The selected member receives the participant
     role and will be auto-assigned to the race.
   - **Remove Racer** — presents a list of current participants. The selected member has their
     participant role removed and will not be assigned to the race.
   - **Done** — proceed to race creation.

4. **Race details** — a form asking for:
   - **Race Description** — label for this week's race (e.g. `Week 3 — Open World Keysanity`)
   - **Seed** — the seed number, link, or identifier
   - **Hash** *(optional)* — hash string for the seed

5. The bot creates the race, auto-assigns every current participant role holder, activates the race,
   and posts the race info message to the general channel. The finisher role is
   stripped from all members at this point, resetting spoilers channel access for the new race.

Racers interact with the bot through the race info message in the general channel to submit times,
view race details, or forfeit. After submitting or forfeiting, they are automatically granted the finisher role
and can access the spoilers channel.

---

### Step 5 — Ending the Trial

> *Run by the organizer or a Mod. Used after the final race of the trial.*

Run `/async_mod end_trial`. A confirmation embed is shown describing what will happen. On confirm:

- The current active race is ended and scored
- The trial is marked **Ended**
- Reaction tracking stops if signups haven't already been closed (signups can no longer be accepted)

Channels and roles are left in place at this stage so post-trial discussion can continue in the
general and spoilers channels. The final leaderboard remains accessible.

---

### Step 6 — Archiving the Trial

> *Run by the organizer or a Mod.*

Run `/async_mod archive_trial`. The bot shows a summary of all Discord objects associated with the
trial (channels, roles, and bot category) and presents four cleanup options:

| Button | What is removed |
|---|---|
| **Category Only** | Deactivates the bot race category; leaves channels and roles untouched |
| **Remove Roles & Category** | Deletes participant and finisher roles; deactivates category |
| **Remove Channels & Category** | Deletes general and spoilers channels; deactivates category |
| **Remove All** | Deletes channels and roles; deactivates category |

The bot race category is always **deactivated** (never deleted), preserving the full race history,
submission records, and standings permanently. The trial is marked **Archived** and no further
commands can be run on it.

Dismiss the message without clicking a button to abort with no changes made.
