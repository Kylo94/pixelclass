"""净室审计：本项目里不许出现旧项目/公司的名字，旧类名只能以"兼容别名"的形式存在。

这是把**过程纪律变成可执行断言**：规则写在 `CONTRIBUTING.md` 里，这里让它在门禁里生效。
"""

import os
import re

import pixelclass as pc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: 允许出现旧项目名的地方：记录净室过程的文档（它们是"没抄代码"的证据），
#: 以及本审计脚本自己（它必须写出要匹配的模式）。
BRAND_WHITELIST = {"CONTRIBUTING.md", "docs/spec/00-overview.md", "tests/test_clean_room.py"}

#: 这些目录不属于项目内容（缓存 / 环境 / 构建产物）
SKIP_DIRS = {".git", ".venv", ".mypy_cache", ".pytest_cache", "__pycache__", "dist", "build", "node_modules"}

BRAND_PATTERN = re.compile(r"walimaker|瓦力", re.IGNORECASE)


def _iter_project_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS and not name.endswith(".egg-info")]
        for name in files:
            if name.endswith((".pyc", ".whl", ".gz", ".png", ".ttc", ".ttf")):
                continue
            yield os.path.relpath(os.path.join(base, name), ROOT)


def test_no_old_brand_anywhere_but_the_process_docs():
    hits = set()
    for relative in _iter_project_files():
        try:
            with open(os.path.join(ROOT, relative), encoding="utf-8") as handle:
                text = handle.read()
        except (UnicodeDecodeError, OSError):
            continue
        if BRAND_PATTERN.search(text):
            hits.add(relative.replace(os.sep, "/"))
    assert hits <= BRAND_WHITELIST, f"旧项目名出现在不该出现的地方：{sorted(hits - BRAND_WHITELIST)}"
    assert hits == BRAND_WHITELIST, "过程文档应当保留净室说明（它们是有意为之的证据）"


def test_legacy_class_names_are_only_compatibility_aliases():
    assert pc.GameObject is pc.Entity
    assert pc.NewGameObject is pc.Entity
    # 旧项目里那个"内部载体"名字不再单独存在（新项目根类叫 Entity）
    assert not hasattr(pc, "Object") or getattr(pc, "Object", None) is None


def test_public_names_do_not_include_module_objects():
    import types

    for name in pc.__all__:
        value = getattr(pc, name, None)
        assert not isinstance(value, types.ModuleType), f"{name} 不该导出模块对象"
    assert "pygame" not in pc.__all__ and "pymunk" not in pc.__all__


def test_spec_questions_records_conclusions_not_code():
    path = os.path.join(ROOT, "SPEC-QUESTIONS.md")
    assert os.path.isfile(path), "净室规则要求保留查证登记表"
    text = open(path, encoding="utf-8").read()
    assert "```" not in text, "登记表只记问题与行为结论，不贴代码"
    assert "|" in text, "应当是一张表格"


def test_readme_has_no_old_brand():
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    assert not BRAND_PATTERN.search(readme), "面向使用者的 README 不应出现旧项目名"
