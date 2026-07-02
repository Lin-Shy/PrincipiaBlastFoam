from __future__ import annotations

import argparse
from pathlib import Path

from scripts import migrate_legacy_entrypoints as migrate


def test_wrapper_text_points_to_deepagents_src(tmp_path: Path) -> None:
    text = migrate.wrapper_text("run_workflow.py", tmp_path)

    assert "PRINCIPIA_DEEPAGENTS_ROOT" in text
    assert str(tmp_path) in text
    assert 'DEEPAGENTS_ROOT / ".venv" / "bin" / "python"' in text
    assert "os.execv" in text
    assert 'DEEPAGENTS_ROOT / "src"' in text
    assert "from principia_deepagents.legacy_cli import workflow_main" in text


def test_backup_path_for_uses_unique_backup_name(tmp_path: Path) -> None:
    destination = tmp_path / "run_workflow.py"
    destination.write_text("current", encoding="utf-8")
    first_backup = tmp_path / "run_workflow.py.legacy-langgraph.bak"
    first_backup.write_text("old backup", encoding="utf-8")

    backup = migrate.backup_path_for(destination)

    assert backup == tmp_path / "run_workflow.py.legacy-langgraph.1.bak"


def test_migration_refuses_dirty_entrypoints_by_default(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "legacy"
    deepagents = tmp_path / "deepagents"
    (target).mkdir()
    (deepagents / "src" / "principia_deepagents").mkdir(parents=True)
    monkeypatch.setattr(
        migrate,
        "git_status_for_paths",
        lambda *_args, **_kwargs: [" M run_workflow.py"],
    )
    args = argparse.Namespace(
        target_project=target,
        deepagents_root=deepagents,
        apply=True,
        allow_dirty=False,
        backup=True,
    )

    return_code = migrate.migrate(args)

    output = capsys.readouterr().out
    assert return_code == 1
    assert "Refusing to overwrite dirty legacy entrypoint files" in output
    assert not (target / "run_workflow.py").exists()
