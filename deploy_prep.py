#!/usr/bin/env python3
"""
deploy_prep.py - zBot deployment preparation helper.

Commands:
  prep      Reads DEPLOY_LOG.json, diffs since last deploy, clears deploy/,
            copies changed files (excluding migrations, db files, gitignored),
            writes .deploy_state.json, prints JSON summary.

            Options:
              --target COMMIT       Target commit/branch (default: HEAD)
              --branch BRANCH       Branch name override
              --from-commit COMMIT  Override from-commit (default: last log entry)

  finalize  --description-file PATH
            Reads description from file, tags target commit as Deploy_YYYY_MM_DD_HH-MM,
            appends entry to DEPLOY_LOG.json, removes state files, prints JSON confirmation.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
LOG_FILE = ROOT / "DEPLOY_LOG.json"
DEPLOY_DIR = ROOT / "deploy"
STATE_FILE = ROOT / ".deploy_state.json"

EXCLUDE_PATTERNS = [
    r"^db/migrations/",
    r"\.db$",
    r"^deploy/",
    r"^\.git",
    r"^deploy_prep\.py$",
    r"^DEPLOY_LOG\.json$",
    r"^\.deploy",
]


def git_run(*args):
    result = subprocess.run(
        ["git", "-C", str(ROOT)] + list(args),
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def is_gitignored(path):
    result = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "-q", path],
        capture_output=True
    )
    return result.returncode == 0


def should_exclude(path):
    normalized = path.replace("\\", "/")
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, normalized):
            return True
    if is_gitignored(path):
        return True
    return False


def read_log():
    if not LOG_FILE.exists():
        return None, "DEPLOY_LOG.json not found in project root."
    try:
        with open(LOG_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list) or len(data) == 0:
            return None, "DEPLOY_LOG.json must be a non-empty JSON array."
        return data, None
    except json.JSONDecodeError as e:
        return None, f"DEPLOY_LOG.json parse error: {e}"


def write_log(entries):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
        f.write("\n")


def get_changed_files(from_commit, to_commit):
    output = git_run("diff", "--name-only", "--diff-filter=ACMR",
                     f"{from_commit}..{to_commit}")
    if not output:
        return [], []
    all_files = [f.replace("\\", "/") for f in output.splitlines()]
    deployable = [f for f in all_files if not should_exclude(f)]
    migrations = [f for f in all_files if re.search(r"^db/migrations/", f)]
    return deployable, migrations


def clean_deploy_dir():
    if not DEPLOY_DIR.exists():
        DEPLOY_DIR.mkdir()
        return
    for item in DEPLOY_DIR.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        elif item.is_file():
            item.unlink()


def copy_files(files):
    copied, errors = [], []
    for f in files:
        src = ROOT / f
        dst = DEPLOY_DIR / f
        if not src.exists():
            errors.append(f"Source not found: {f}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(f)
    return copied, errors


def files_from_deploy_dir():
    files = []
    for p in DEPLOY_DIR.rglob("*"):
        if p.is_file():
            files.append(str(p.relative_to(DEPLOY_DIR)).replace("\\", "/"))
    return sorted(files)


def cmd_prep(args):
    log, err = read_log()
    if err:
        print(json.dumps({"error": err}))
        sys.exit(1)

    from_commit = args.from_commit or log[-1]["commit"]

    try:
        git_run("rev-parse", "--verify", from_commit)
    except RuntimeError:
        print(json.dumps({"error": f"from_commit '{from_commit}' not found in repo."}))
        sys.exit(1)

    try:
        raw_target = args.target if args.target else "HEAD"
        target_commit = git_run("rev-parse", "--short", raw_target)
    except RuntimeError as e:
        print(json.dumps({"error": f"Cannot resolve target commit '{raw_target}': {e}"}))
        sys.exit(1)

    branch = args.branch or git_run("rev-parse", "--abbrev-ref", "HEAD")

    deployable, migrations = get_changed_files(from_commit, target_commit)

    if not deployable:
        print(json.dumps({
            "error": "No deployable files changed since last deploy.",
            "from_commit": from_commit,
            "target_commit": target_commit,
            "migration_files": migrations,
        }))
        sys.exit(1)

    clean_deploy_dir()
    copied, errors = copy_files(deployable)

    if errors:
        print(json.dumps({"error": "File copy errors occurred.", "details": errors}))
        sys.exit(1)

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"from_commit": from_commit, "target_commit": target_commit,
                   "branch": branch}, f, indent=2)

    commit_log = git_run("log", "--oneline", f"{from_commit}..{target_commit}")

    print(json.dumps({
        "from_commit": from_commit,
        "target_commit": target_commit,
        "branch": branch,
        "files": copied,
        "migration_files": migrations,
        "commits": commit_log.splitlines() if commit_log else [],
    }, indent=2))


def cmd_finalize(args):
    if not STATE_FILE.exists():
        print(json.dumps({"error": ".deploy_state.json not found. Run 'prep' first."}))
        sys.exit(1)

    desc_path = Path(args.description_file)
    if not desc_path.exists():
        print(json.dumps({"error": f"Description file '{args.description_file}' not found."}))
        sys.exit(1)

    with open(STATE_FILE, encoding="utf-8") as f:
        state = json.load(f)

    description = desc_path.read_text(encoding="utf-8").strip()
    if not description:
        print(json.dumps({"error": "Description file is empty."}))
        sys.exit(1)

    log, err = read_log()
    if err:
        print(json.dumps({"error": err}))
        sys.exit(1)

    now = datetime.now()
    tag = f"Deploy_{now.strftime('%Y_%m_%d_%H-%M')}"

    try:
        git_run("tag", tag, state["target_commit"])
    except RuntimeError as e:
        print(json.dumps({"error": f"Failed to create tag '{tag}': {e}"}))
        sys.exit(1)

    entry = {
        "datetime": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "branch": state["branch"],
        "commit": state["target_commit"],
        "from_commit": state["from_commit"],
        "description": description,
        "files": files_from_deploy_dir(),
    }
    log.append(entry)
    write_log(log)

    STATE_FILE.unlink()
    desc_path.unlink()

    print(json.dumps({"tag": tag, "commit": state["target_commit"], "log_entry": entry},
                     indent=2))


def main():
    parser = argparse.ArgumentParser(description="zBot deploy preparation helper")
    sub = parser.add_subparsers(dest="command", required=True)

    prep_p = sub.add_parser("prep", help="Stage files for deployment")
    prep_p.add_argument("--target", help="Target commit or branch (default: HEAD)")
    prep_p.add_argument("--branch", help="Branch name override")
    prep_p.add_argument("--from-commit", dest="from_commit",
                        help="Override from-commit (default: last DEPLOY_LOG entry)")

    fin_p = sub.add_parser("finalize", help="Tag commit and update DEPLOY_LOG.json")
    fin_p.add_argument("--description-file", required=True,
                       help="Path to file containing the deploy description")

    parsed = parser.parse_args()
    if parsed.command == "prep":
        cmd_prep(parsed)
    elif parsed.command == "finalize":
        cmd_finalize(parsed)


if __name__ == "__main__":
    main()
