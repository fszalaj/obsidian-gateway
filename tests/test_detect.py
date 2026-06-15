import pytest

from gateway.detect import VaultDetectionError, detect_vault


def mkvault(p):
    p.mkdir(parents=True, exist_ok=True)
    (p / "index.md").write_text("x")
    return p


def test_cwd_is_vault(tmp_path):
    (tmp_path / ".obsidian").mkdir()
    assert detect_vault(tmp_path) == tmp_path


def test_cwd_obsidian_wins_over_wiki_subfolder(tmp_path):
    (tmp_path / ".obsidian").mkdir()
    (tmp_path / "wiki").mkdir(); (tmp_path / "wiki" / "a.md").write_text("x")
    assert detect_vault(tmp_path) == tmp_path


def test_wiki_with_md(tmp_path):
    (tmp_path / "wiki").mkdir(); (tmp_path / "wiki" / "a.md").write_text("x")
    assert detect_vault(tmp_path) == tmp_path / "wiki"


def test_empty_wiki_falls_through(tmp_path):
    (tmp_path / "wiki").mkdir()  # empty 'wiki' = not a vault
    mkvault(tmp_path / "proj-obsidian-vault")
    assert detect_vault(tmp_path) == tmp_path / "proj-obsidian-vault"


def test_empty_obsidian_vault_not_picked(tmp_path):
    (tmp_path / "stale-obsidian-vault").mkdir()  # empty = not real
    mkvault(tmp_path / "real-obsidian-vault")
    assert detect_vault(tmp_path) == tmp_path / "real-obsidian-vault"


def test_ambiguous_real_obsidian_vaults(tmp_path):
    mkvault(tmp_path / "a-obsidian-vault")
    mkvault(tmp_path / "b-obsidian-vault")
    with pytest.raises(VaultDetectionError):
        detect_vault(tmp_path)


def test_single_child_with_obsidian(tmp_path):
    (tmp_path / "notes").mkdir(); (tmp_path / "notes" / ".obsidian").mkdir()
    assert detect_vault(tmp_path) == tmp_path / "notes"


def test_top_level_md_alone_is_not_a_vault(tmp_path):
    (tmp_path / "README.md").write_text("x")  # a project root, not a vault
    with pytest.raises(VaultDetectionError):
        detect_vault(tmp_path)


def test_nothing_found(tmp_path):
    (tmp_path / "src").mkdir()
    with pytest.raises(VaultDetectionError):
        detect_vault(tmp_path)
