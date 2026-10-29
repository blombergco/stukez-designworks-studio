"""Back up the vault to its git remote (GitHub): commit everything that changed, then push.

The app only ever runs plain git commands in the vault folder. Nothing is rewritten and nothing is deleted: a backup
is a new commit on top of the history, pushed to `origin`.
"""
import subprocess
from datetime import datetime
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _git(root, *args, timeout=300):
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, creationflags=NO_WINDOW)
    return r.returncode, (r.stdout + r.stderr).strip()


def repo_root(vault_root):
    code, out = _git(vault_root, "rev-parse", "--show-toplevel")
    return Path(out) if code == 0 else None


def status(vault_root):
    """(ok, text): is there a repo and a remote, and how many files changed since the last backup."""
    root = repo_root(vault_root)
    if root is None:
        return False, "This folder is not a git repository yet."
    code, remote = _git(root, "remote", "get-url", "origin")
    if code != 0:
        return False, "No GitHub remote is set up yet (run the GitHub setup once)."
    _c, changed = _git(root, "status", "--porcelain")
    n = len([l for l in changed.splitlines() if l.strip()])
    return True, f"{n} changed file(s) since the last backup. Remote: {remote}"


def backup(vault_root, message=None):
    """Commit and push. Returns (ok, log text). Safe to call when nothing changed (then it only pushes)."""
    root = repo_root(vault_root)
    if root is None:
        return False, "This folder is not a git repository."
    log = []
    code, remote = _git(root, "remote", "get-url", "origin")
    if code != 0:
        return False, "No GitHub remote is set up yet."
    code, out = _git(root, "add", "-A")
    log.append("git add -A" + (f"\n{out}" if out else ""))
    if code != 0:
        return False, "\n".join(log)
    _c, changed = _git(root, "status", "--porcelain")
    if changed.strip():
        msg = message or f"Backup {datetime.now():%Y-%m-%d %H:%M}"
        code, out = _git(root, "commit", "-m", msg)
        log.append(f"git commit\n{out}")
        if code != 0:
            return False, "\n".join(log)
    else:
        log.append("Nothing new to commit.")
    code, out = _git(root, "push", "-u", "origin", "HEAD", timeout=900)
    log.append(f"git push\n{out}")
    return code == 0, "\n".join(log)
