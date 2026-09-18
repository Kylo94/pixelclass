"""打包配置自检：发行包必须带上 src/pixelclass 下的**所有**子包。

0.1.0 曾经只打包了顶层包，导致 pip 装完后 `import pixelclass` 直接
ModuleNotFoundError（子包 physics / worldmap / ui 全丢了）。这里静态守住。
"""

import os
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")


def _subpackages():
    """src/pixelclass 下所有含 __init__.py 的子包名（含顶层包）。"""
    root = os.path.join(SRC, "pixelclass")
    found = {"pixelclass"}
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name != "__pycache__"]
        if "__init__.py" in files:
            relative = os.path.relpath(base, SRC).replace(os.sep, ".")
            found.add(relative)
    return found


def test_all_subpackages_are_discovered_by_build_config():
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as handle:
        config = tomllib.load(handle)
    tool = config["tool"]["setuptools"]

    # 两种写法都接受：显式列表（packages = [...]），或自动发现（packages.find）
    packages = tool.get("packages")
    if isinstance(packages, list):
        configured = set(packages)
        assert configured == _subpackages(), f"手写列表漏了子包：{sorted(_subpackages() - configured)}"
        return

    find = (packages or {}).get("find")
    assert find, "必须配置 packages 或 packages.find，否则子包不会被打包"
    where = (find.get("where") or ["."])[0]
    assert os.path.isdir(os.path.join(ROOT, where)), f"packages.find.where 指向不存在的目录：{where}"
    include = find.get("include", ["*"])
    assert any(pattern.startswith("pixelclass") for pattern in include)
    # 所有子包都在 where 目录下（src 布局），自动发现会覆盖它们
    for name in _subpackages():
        path = os.path.join(ROOT, where, *name.split("."))
        assert os.path.isfile(os.path.join(path, "__init__.py")), f"{name} 不在 {where} 下"


def test_py_typed_marker_is_present():
    assert os.path.isfile(os.path.join(SRC, "pixelclass", "py.typed")), "PEP 561 标记要随包发布"
