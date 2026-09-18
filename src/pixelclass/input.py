"""输入（spec 06 §2，M3 先做鼠标位置相关的最小集）。

坐标一律返回**数学坐标**；"刚按下 / 刚松开"等事件语义在输入里程碑补齐。
"""

from typing import Any, Tuple

import pygame

from .context import resolve_world
from .vec import pygame2Cartesian


def _scene_size(world: Any = None) -> Tuple[int, int]:
    scene = resolve_world(world)
    size = getattr(scene.camera, "size", None)
    return (int(size[0]), int(size[1])) if size else (800, 600)


def get_mouse_pos(world: Any = None) -> Tuple[float, float]:
    """鼠标位置的数学坐标。"""
    return pygame2Cartesian(pygame.mouse.get_pos(), _scene_size(world))


def get_mouse_rel() -> Tuple[float, float]:
    """自上一帧起的鼠标相对位移（屏幕坐标下的位移，y 取反以符合数学坐标习惯）。"""
    dx, dy = pygame.mouse.get_rel()
    return (float(dx), -float(dy))


def set_mouse_visible(visible: bool = True) -> None:
    pygame.mouse.set_visible(bool(visible))
