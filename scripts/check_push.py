"""Pre-push guard for the public repo: stop commits with private material from leaving the machine.

Git runs this from .githooks/pre-push and passes one line per ref on stdin:
    <local ref> <local sha> <remote ref> <remote sha>
Only commits that are about to be pushed are checked, so history that is already public is not re-checked.
"""

import re
import subprocess
import sys

ZERO = "0" * 40
THIS_FILE = "scripts/check_push.py"

# Paths that never go to the public repo (the author's cars, sponsor database, prompts and personal folders).
# (stukez_studio/builtin/ holds the two built-in preview cars; the author chose to publish them with 1.3.0.)
FORBIDDEN_PATHS = (
    "Drift Sponsor Database/",
    "Sponsor Lists/",
    "Project Library/Car Templates/",
    "Project Library/Sponsor Logo Library/Logo masters/",
    "Studier/",
    "Gemini Prompt/",
    "CV/",
)

# Personal details that must not appear in added lines.
PRIVATE_TEXT = (
    re.compile(r"robinblombergco@gmail\.com", re.IGNORECASE),
    re.compile(r"C:[\\/]+Users[\\/]+robin", re.IGNORECASE),
    re.compile(r"\bD:[\\/]"),
    re.compile(r"Obsidian stuff", re.IGNORECASE),
)


def git(*args):
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True
    ).stdout


def commits_to_push(local_sha, remote_sha):
    if remote_sha != ZERO:
        try:
            return git("rev-list", local_sha, f"^{remote_sha}").split()
        except subprocess.CalledProcessError:
            pass  # remote commit not known here, fall through to the branch-wide list
    return git("rev-list", local_sha, "--not", "--remotes").split()


def check_commit(sha):
    problems = []
    for path in git("diff-tree", "--root", "--no-commit-id", "--name-only", "--diff-filter=d", "-r", "-z", sha).split("\0"):
        if path.startswith(FORBIDDEN_PATHS):
            problems.append(f"{sha[:8]} {path}: forbidden path")

    current = ""
    for line in git("show", "--format=", "--unified=0", "--no-color", sha).splitlines():
        if line.startswith("diff --git "):
            current = line.rsplit(" b/", 1)[-1]
        elif line.startswith("+") and not line.startswith("+++") and current != THIS_FILE:
            for pattern in PRIVATE_TEXT:
                if pattern.search(line):
                    problems.append(f"{sha[:8]} {current}: personal text matches {pattern.pattern!r}")
                    break
    return problems


def main():
    problems = []
    seen = set()
    for line in sys.stdin:
        parts = line.split()
        if len(parts) != 4:
            continue
        local_ref, local_sha, remote_ref, remote_sha = parts
        if local_sha == ZERO:
            continue  # branch deletion pushes no commits
        for sha in commits_to_push(local_sha, remote_sha):
            if sha not in seen:
                seen.add(sha)
                problems += check_commit(sha)

    if problems:
        print("pre-push: blocked, private material in the commits being pushed:")
        for problem in problems:
            print("  " + problem)
        print("Rewrite those commits, or push with --no-verify after checking the content yourself.")
        return 1
    print(f"pre-push: {len(seen)} commit(s) checked, nothing private found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
