"""脚本自检：门禁与发布脚本里那些"容易写错"的纯函数（不真的构建/上传）。"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import check  # noqa: E402
import release  # noqa: E402


# ------------------------------------------------------------------ 门禁脚本
def test_check_plan_covers_the_five_gates():
    plan = check.steps(include_matrix=False)
    names = " ".join(name for name, _command, _env in plan)
    for expected in ("black", "flake8", "mypy", "pytest", "行为验收"):
        assert expected in names, expected


def test_check_matrix_adds_both_pymunk_versions():
    plan = check.steps(include_matrix=True)
    matrix = [name for name, _command, _env in plan if "矩阵" in name]
    assert len(matrix) == 2
    assert any("6.11.1" in name for name in matrix)


def test_check_list_does_not_run_anything(capsys):
    assert check.main(["--list"]) == 0
    output = capsys.readouterr().out
    assert "black" in output and "行为验收" in output


# ------------------------------------------------------------------ 发布脚本
def test_read_version_from_version_file():
    version = release.read_version()
    assert version and version[0].isdigit(), version


def test_read_version_reports_unparsable_file(tmp_path):
    broken = tmp_path / "_version.py"
    broken.write_text("nothing here", encoding="utf-8")
    with pytest.raises(release.Abort):
        release.read_version(str(broken))


def test_changelog_helpers(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# 更新日志\n\n## [未发布]\n\n- 内容\n", encoding="utf-8")
    assert release.unreleased_heading(str(changelog)) == "## [未发布]"
    assert release.changelog_heading("9.9.9", str(changelog)) is None

    release.replace_first_heading("## [未发布]", "## [9.9.9] - 2026-01-01", str(changelog))
    text = changelog.read_text(encoding="utf-8")
    assert "## [9.9.9] - 2026-01-01" in text and "未发布" not in text
    assert release.changelog_heading("9.9.9", str(changelog)) == "## [9.9.9] - 2026-01-01"


def test_discover_tests_finds_pytest_files():
    names = release.discover_tests()
    assert names, "应当能发现测试文件"
    assert all(name.startswith("test_") and name.endswith(".py") for name in names)
    assert "conftest.py" not in names, "conftest 不是测试文件"


def test_release_repositories_are_configured():
    assert release.REPOS["pypi"]["token_file"] == ".pypi-token"
    assert release.REPOS["testpypi"]["token_file"] == ".pypi-token-test"
    assert release.REPOS["pypi"]["url"].startswith("https://upload.pypi.org")


def test_remote_has_version_handles_network_failure(monkeypatch):
    def boom(*_args, **_kwargs):
        raise OSError("no network")

    monkeypatch.setattr(release.urllib.request, "urlopen", boom)
    assert release.remote_has_version("0.0.1") is None, "网络问题不该被当成'版本不存在'"
