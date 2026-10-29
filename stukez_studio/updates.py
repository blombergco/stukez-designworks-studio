"""Updates: look for a newer release on GitHub, download its installer, check it, run it.

A release carries the installer (StukeZ-Designworks-Studio-<version>-Setup.exe) and a file next to it with its SHA-256
(<installer name>.sha256). The installer is only run when its checksum matches and it came from GitHub over https.
"""
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from . import __version__

REPO = "blombergco/stukez-designworks-studio"     # the repository whose releases carry the installers; "" turns the check off
API = "https://api.github.com"
SUFFIX = "-Setup.exe"
ALLOWED_HOSTS = ("github.com", "githubusercontent.com")
USER_AGENT = f"StukeZ-Designworks-Studio/{__version__}"
ALLOW_LOOPBACK = False        # only the tests switch this on, to talk to a local fake release server


class UpdateError(Exception):
    """Something to tell the user in plain words (no network, no release yet, a bad checksum)."""


def parse(v):
    """'v1.2.3' -> (1, 2, 3); missing parts count as 0."""
    nums = [int(n) for n in re.findall(r"\d+", str(v).split("-")[0])[:3]]
    return tuple(nums + [0] * (3 - len(nums)))


def is_newer(candidate, current=__version__):
    return parse(candidate) > parse(current)


def _open(url, timeout):
    host = urlparse(url).hostname or ""
    loop = ALLOW_LOOPBACK and host in ("127.0.0.1", "localhost")
    if urlparse(url).scheme != "https" and not loop:
        raise UpdateError("Refusing a download that is not https.")
    if not (loop or any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)):
        raise UpdateError(f"Refusing a download from {host}.")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    return urllib.request.urlopen(req, timeout=timeout)


def latest(repo=REPO, api=API, timeout=8):
    """The newest published release: dict(version, notes, page, name, url, sha256). Raises UpdateError with a readable message."""
    if not repo:
        raise UpdateError("No update channel is set up for this copy.")
    try:
        with _open(f"{api}/repos/{repo}/releases/latest", timeout) as r:
            rel = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise UpdateError("No release has been published yet." if e.code == 404 else f"GitHub answered with error {e.code}.") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise UpdateError("Could not reach GitHub. Check the internet connection.") from e
    assets = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
    name = next((n for n in assets if n.endswith(SUFFIX)), None)
    if not name or name + ".sha256" not in assets:
        raise UpdateError("The newest release has no installer with a checksum file.")
    try:
        with _open(assets[name + ".sha256"], timeout) as r:
            sha = r.read().decode("utf-8").split()[0].lower()
    except (urllib.error.URLError, TimeoutError, OSError, IndexError) as e:
        raise UpdateError("Could not read the checksum of the installer.") from e
    return dict(version=str(rel.get("tag_name", "")).lstrip("vV"), notes=(rel.get("body") or "").strip(), page=rel.get("html_url", ""),
                name=name, url=assets[name], sha256=sha)


def download(info, folder, progress=None, timeout=30):
    """Download the installer to `folder` and verify it. progress(done_bytes, total_bytes) is optional."""
    dest = Path(folder) / info["name"]
    h = hashlib.sha256()
    try:
        with _open(info["url"], timeout) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
                h.update(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        dest.unlink(missing_ok=True)
        raise UpdateError("The download was interrupted. Try again.") from e
    if h.hexdigest() != info["sha256"]:
        dest.unlink(missing_ok=True)
        raise UpdateError("The downloaded file does not match its checksum, so it was deleted. Try again later.")
    return dest


def install(path):
    """Start the installer (silent, it closes and restarts the program) and return; the caller quits the program."""
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen([str(path), "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"], creationflags=flags, close_fds=True)


def can_self_update():
    """Only an installed copy updates itself; a copy that runs from source does not."""
    return bool(getattr(sys, "frozen", False))
