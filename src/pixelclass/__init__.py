"""pixelclass：给中小学课堂用的 2D 游戏引擎。

实现进度见 `docs/spec/README.md`（里程碑在 spec 00 §7）。
当前处于 **M1**：场景、可注入时钟、固定步长与自适应子步、主循环。
实体 / 视觉 / 物理组件在 M2–M4 接入，公共名字逐步补齐到 spec 08 的清单。
"""

import types

from pygame import locals as _pygame_locals
from pygame.locals import *  # noqa: F401,F403  —— 事件与按键常量（学生不写前缀也能用）

from ._version import __version__
from .camera import Camera
from .context import global_var
from .physics import Body, BodiesGroup, TiledMapBodies, TiledMapBodiesGroup
from .runtime import (
    cwd,
    done,
    draw_line,
    init,
    save_screen,
    set_gravity,
    setup,
    title,
    update,
)
from .scene import Group, Scene
from .vec import Cartesian2pygame, pygame2Cartesian, sign, to_cp, vec
from .window import Window

# 讲义兼容别名（spec 08 §2.1）
World = Scene
Screen = Window  # 兼容名：窗口对象（相机相关构造参数在相机里程碑补齐）

_FRAMEWORK_NAMES = [
    # 场景与主循环（spec 01）
    "Scene",
    "World",
    "setup",
    "update",
    "done",
    "title",
    "save_screen",
    "global_var",
    "init",
    "cwd",
    "Group",
    # 窗口与相机
    "Window",
    "Screen",
    "Camera",
    # 物理（spec 03）
    "Body",
    "BodiesGroup",
    "TiledMapBodies",
    "TiledMapBodiesGroup",
    # 工具（spec 01 / 07）
    "draw_line",
    "set_gravity",
    "sign",
    "Cartesian2pygame",
    "pygame2Cartesian",
    "to_cp",
    "vec",
    "__version__",
]

_PYGAME_CONSTANTS = [
    _name
    for _name in dir(_pygame_locals)
    if not _name.startswith("_") and not isinstance(getattr(_pygame_locals, _name), types.ModuleType)
]

__all__ = [*_FRAMEWORK_NAMES, *_PYGAME_CONSTANTS]
