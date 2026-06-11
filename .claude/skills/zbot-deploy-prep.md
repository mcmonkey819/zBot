---
name: zbot-deploy-prep
description: Prepare a zBot deployment package. Diffs since last deploy, stages changed files in deploy/, generates a deploy summary, tags the target commit, and updates DEPLOY_LOG.json.
---

# zBot Deploy Prep Skill

Prepare a deployment package for the zBot project. Any text provided after the skill invocation is treated as an optional target commit or branch (defaults to tip of `main`/`HEAD`).

All commands run from the project root (`C:\git\zBot`). The Python script `deploy_prep.py` handles all mechanical operations and outputs JSON. If any step produces an `"error"` key in its JSON output, stop immediately and report the error to the user before proceeding.

---

## Step 1 — Run prep

Run the following command, passing `--target <ARGUMENT>` if the user provided a target commit or branch, otherwise omit `--target`:

```
python deploy_prep.py prep [--target <commit_or_branch>]
```

Parse the JSON output. On error, stop and report to the user.

The output fields are:
- `from_commit` — the last deployed commit being diffed against
- `target_commit` — the short hash being deployed
- `branch` — the branch being deployed
- `files` — list of files staged in `deploy/` (relative paths from project root)
- `migration_files` — migration scripts in the diff range (NOT staged; require manual execution)
- `commits` — one-line git log of commits included in this deploy

---

## Step 2 — Generate description and present summary

Using the `commits` list and `files` list from the prep output, write a 1–2 sentence natural language description of the changes included in this deployment. Be specific about features and fixes; avoid implementation jargon. Write the description to `.deploy_description.txt` using the Write tool (plain text, no markdown).

Then present the following deploy summary to the user:

```
Deploy Summary
==============
Branch:   <branch>
Commit:   <target_commit>  (from <from_commit>)

Files staged in deploy/:
  <file 1>
  <file 2>
  ...

DB Migrations:
  <list migration files if any, noting each must be run manually before starting the bot>
  — or —
  None required

Changes:
  <the 1–2 sentence description you generated>
```

---

## Step 3 — Finalize

Run:

```
python deploy_prep.py finalize --description-file .deploy_description.txt
```

Parse the JSON output. On error, stop and report to the user.

On success, confirm to the user:
- Git tag created: `<tag>` on commit `<commit>`
- DEPLOY_LOG.json updated with this deployment entry

---

## Error handling reference

| Situation | Action |
|---|---|
| `DEPLOY_LOG.json` missing or malformed | Stop, tell user to check the file |
| `from_commit` not found in repo | Stop, ask user to verify last deploy commit |
| No deployable files changed | Stop, inform user — nothing to deploy |
| File copy error (source not found) | Stop, report the missing file |
| Tag already exists | Stop, report conflict — user may need to delete the existing tag |
| Description file empty | Stop, do not proceed to finalize |
