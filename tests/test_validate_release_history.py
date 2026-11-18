import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ci" / "validate_release_history.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("validate_release_history", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate_release_history = load_script()


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)  # noqa: S603, S607


def commit(repo: Path, message: str) -> None:
    git(repo, "commit", "--allow-empty", "-m", message)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.name", "test")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "commit.gpgsign", "false")
    git(tmp_path, "config", "tag.gpgsign", "false")
    commit(tmp_path, "chore: initial")
    return tmp_path


def test_tag_in_history_passes(repo: Path) -> None:
    git(repo, "tag", "v0.3.3")
    commit(repo, "feat: new feature")
    assert validate_release_history.validate(repo) is None
    assert validate_release_history.main(["--repo", str(repo)]) == 0


def test_no_tags_fails(repo: Path) -> None:
    assert "no vX.Y.Z tags" in validate_release_history.validate(repo)
    assert validate_release_history.main(["--repo", str(repo)]) == 1


def test_tag_outside_history_fails(repo: Path) -> None:
    git(repo, "checkout", "-q", "-b", "lost")
    commit(repo, "fix: on a branch that will be thrown away")
    git(repo, "tag", "v0.4.0")
    git(repo, "checkout", "-q", "main")
    assert "not an ancestor of HEAD" in validate_release_history.validate(repo)


def test_latest_tag_uses_version_order_and_ignores_other_tags(repo: Path) -> None:
    for tag in ("v0.9.0", "v0.10.0", "v0.2.1", "release-candidate", "v1.0"):
        git(repo, "tag", tag)
    assert validate_release_history.latest_version_tag(repo) == "v0.10.0"
