from __future__ import annotations

import contextlib
import hashlib
import os
import tempfile
import warnings
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows has no fcntl
    fcntl = None  # type: ignore[assignment]

_WARNED = False


def _lockfile(repo_root: Path) -> Path:
    # Inside .git: per-repo, never synced to Obsidian, never a note. Fall back to a
    # temp file keyed by the repo path when there is no writable .git.
    d = repo_root / ".git" / "obsidian-gateway-locks"
    try:
        d.mkdir(parents=True, exist_ok=True)
        return d / "write.lock"
    except OSError:
        h = hashlib.sha256(str(repo_root).encode()).hexdigest()[:16]
        d = Path(tempfile.gettempdir()) / "obsidian-gateway-locks"
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{h}.lock"


@contextlib.contextmanager
def write_lock(repo_root: Path):
    """Serialize writes AND the git commit per repository, across threads and across
    processes on this host, so read-modify-write tools and concurrent commits cannot
    race (lost updates, mixed/torn commits).

    flock is advisory and NON-reentrant: acquiring it twice for the same repo from one
    thread (via two fds) deadlocks. So the lock is taken once at the tool boundary and
    the inner gitops.commit never re-locks.
    """
    global _WARNED
    if fcntl is None:
        if not _WARNED:
            warnings.warn(
                "fcntl unavailable; obsidian-gateway write locking is disabled "
                "(concurrent writes may race)",
                stacklevel=2,
            )
            _WARNED = True
        yield
        return
    fd = os.open(_lockfile(repo_root), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
