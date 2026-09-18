"""应用层：窗口/场景的创建、主循环与面向课堂的模块级函数（spec 01 §2、§3）。

这里是"学生直接调用"的那一层：``setup()`` / ``update()`` / ``done()`` 等。
"""

import os
from typing import Any, Optional, Tuple

import pygame

from . import stepping
from .clock import PHYSICS_DT
from .context import resolve_world
from .scene import Scene
from .window import Window
from .vec import vec

cwd = os.getcwd()  # 资源相对路径的基准（导入时确定；不随运行中 chdir 变化）

_window: Optional[Window] = None


def init() -> None:
    """初始化 pygame（可重复调用）。音频不可用时保持静默，不影响运行。"""
    if not pygame.get_init():
        pygame.init()
    else:
        pygame.display.init()


def get_window() -> Optional[Window]:
    return _window


def _ensure_window(size: Tuple[int, int], caption: str = "pixelclass") -> Window:
    global _window
    if _window is None:
        _window = Window(size, caption)
    else:
        _window.set_size(size)
    return _window


# ---------------------------------------------------------------------- 生命周期
def setup(width: int, height: int, world: Any = None) -> Scene:
    """创建/复用窗口并初始化场景（spec 01 §2.1）。"""
    init()
    scene = resolve_world(world)
    window = _ensure_window((int(width), int(height)))
    scene.reset(window.size)
    return scene


def update(world: Any = None) -> None:
    """推进一帧（spec 01 §3.3）：事件 -> 物理（固定步 + 子步）-> 更新 -> 绘制。"""
    scene = resolve_world(world)
    pygame.event.pump()

    # 帧序（spec 01 §3.3）：先把物理状态同步到显示层，再推进本帧的物理。
    # 因此**绘制的是上一帧物理的结果**——这样一次 update() 内不会出现"已经画过又被物理改写"
    # 的中间态，同时让显示状态与验收基线的时序一致。
    steps = scene.clock.tick()
    scene.sync_display()
    scene.entities.update()
    scene.visuals.update()
    scene.camera._sync_to_subject()

    for _ in range(steps):
        stepping.step_space(scene.space, PHYSICS_DT, scene.max_step_distance, scene.max_substeps)

    window = get_window()
    if window is not None:
        window.draw(scene)
    else:
        pygame.display.flip() if pygame.display.get_init() else None
    scene.is_updated = True


def done() -> None:
    """结束程序：关闭窗口与 pygame。"""
    global _window
    pygame.quit()
    _window = None


# ---------------------------------------------------------------------- 场景级工具（M1 子集）
def title(text: str) -> None:
    window = get_window()
    if window is not None:
        window.set_title(text)


def save_screen(path: str) -> str:
    window = get_window()
    if window is None:
        raise RuntimeError("还没有窗口：请先调用 setup(宽, 高)")
    return window.save(path)


def draw_line(p1: Any, p2: Any, color: Any = (255, 255, 255), width: int = 1, world: Any = None) -> None:
    """画一条线段（下一帧自动清除）。坐标是数学坐标。"""
    scene = resolve_world(world)
    scene.lines.append((vec(p1), vec(p2), tuple(color), int(width)))


def speed(value: int, world: Any = None) -> int:
    """限制每帧位移的步长（"慢动作"，方便课堂观察移动过程）。"""
    scene = resolve_world(world)
    scene.speed_limit = max(1, int(value))
    return scene.speed_limit


def set_gravity(x: Any, *y: Any, world: Any = None) -> None:
    """设置重力。支持 ``set_gravity(0, -1200)`` 与 ``set_gravity((0, -1200))``。"""
    scene = resolve_world(world)
    if y:
        scene.set_gravity(float(x), float(y[0]))
    else:
        scene.set_gravity(float(x[0]), float(x[1]))
