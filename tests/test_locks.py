import subprocess
import threading
import time

from gateway import gitops
from gateway.locks import write_lock
from gateway.vaults import Vault


def test_write_lock_serializes_rmw(tmp_path):
    # Without the lock, the read-sleep-write window loses updates; with it, all land.
    (tmp_path / ".git").mkdir()
    counter = tmp_path / "counter.txt"
    counter.write_text("0")
    n = 20

    def inc():
        with write_lock(tmp_path):
            val = int(counter.read_text())
            time.sleep(0.002)  # widen the RMW window so a missing lock would lose updates
            counter.write_text(str(val + 1))

    threads = [threading.Thread(target=inc) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert int(counter.read_text()) == n


def _git(d, *a):
    subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True)


def test_commit_paths_scoping(tmp_path):
    # commit(paths=[...]) commits only those paths; an unrelated pending change is left
    # uncommitted (so a concurrent commit cannot sweep + mis-attribute it).
    repo = tmp_path
    _git(repo, "init")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    wiki = repo / "wiki"
    wiki.mkdir()
    (wiki / "a.md").write_text("a")
    (wiki / "b.md").write_text("b")
    v = Vault(name="w", path=wiki, repo_root=repo, subdir="wiki")

    res = gitops.commit(v, "add a", paths=["wiki/a.md"])
    assert res["committed"] is True

    tracked = subprocess.run(
        ["git", "-C", str(repo), "ls-files"], capture_output=True, text=True
    ).stdout
    assert "wiki/a.md" in tracked
    assert "wiki/b.md" not in tracked  # left pending, not swept into this commit
