"""中文字体查找（spec 07 §3）。

查找顺序：包内字体目录 → 系统常见中文字体 → pygame 默认字体。
**包内不打包任何商业字体**（微软 / 中易等），找不到就用系统或默认字体，
并且只提示一次——中文显示成方块时学生至少知道原因。
"""

import os
import sys
from typing import Iterable, List, Optional

import pygame

#: 包内字体目录（保持存在，便于老师自行放一个可再分发的字体）
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "fonts")

#: 各平台常见中文字体（按优先级）
SYSTEM_FONTS = {
    "win32": [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyh.ttf",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\simkai.ttf",
    ],
    "darwin": [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ],
    "linux": [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
    ],
}

_warned = False
_cached: Optional[str] = None
_missing = object()


def _package_fonts() -> List[str]:
    if not os.path.isdir(FONT_DIR):
        return []
    return [
        os.path.join(FONT_DIR, name)
        for name in sorted(os.listdir(FONT_DIR))
        if name.lower().endswith((".ttf", ".ttc", ".otf"))
    ]


def _system_fonts() -> Iterable[str]:
    platform = (
        "win32" if sys.platform.startswith("win") else "darwin" if sys.platform == "darwin" else "linux"
    )
    return SYSTEM_FONTS.get(platform, [])


def find_font() -> Optional[str]:
    """返回可用的中文字体路径；都没有时返回 ``None``（表示用 pygame 默认字体）。"""
    global _cached
    if _cached is not None:
        return _cached if _cached is not _missing else None
    for path in list(_package_fonts()) + list(_system_fonts()):
        if os.path.isfile(path):
            _cached = path
            return path
    _cached = _missing  # type: ignore[assignment]
    return None


def _warn_once() -> None:
    global _warned
    if _warned:
        return
    _warned = True
    print(
        "[pixelclass] 没有找到可用的中文字体，将使用 pygame 默认字体（中文可能显示为方块）。\n"
        "            可以在 static/fonts/ 放一个可再分发的字体，或显式指定字体路径。\n"
        "[pixelclass] No Chinese font found; falling back to pygame's default font."
    )


def load_font(size: int, path: Optional[str] = None) -> pygame.font.Font:
    """载入字体：显式路径优先；否则按顺序查找；最后退回 pygame 默认字体。"""
    if not pygame.font.get_init():
        pygame.font.init()
    if path:
        if not os.path.isfile(path):
            raise FileNotFoundError(
                f"找不到字体文件：{os.path.abspath(path)}\nFont file not found: {os.path.abspath(path)}"
            )
        return pygame.font.Font(path, int(size))
    found = find_font()
    if found is None:
        _warn_once()
        return pygame.font.Font(None, int(size))
    return pygame.font.Font(found, int(size))


def reset_cache() -> None:
    """清空查找缓存（测试用）。"""
    global _cached, _warned
    _cached = None
    _warned = False


__all__ = ["find_font", "load_font", "reset_cache", "FONT_DIR", "SYSTEM_FONTS"]
