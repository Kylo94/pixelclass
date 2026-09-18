"""应用层：窗口/场景的创建、主循环与面向课堂的模块级函数（spec 01 §2、§3）。

这里是"学生直接调用"的那一层：``setup()`` / ``update()`` / ``done()`` 等。
"""

import os
import random
import warnings
from typing import Any, Optional, Tuple

import pygame

from . import input as input_state
from . import stepping
from .clock import PHYSICS_DT
from .context import resolve_world
from .scene import Scene
from .window import Window
from .vec import vec

cwd = os.getcwd()  # 资源相对路径的基准（导入时确定；不随运行中 chdir 变化）

_window: Optional[Window] = None
_tracer_frames = 0
_tracer_started: Optional[int] = None


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
    if _window is None or pygame.display.get_surface() is None:
        # 显示被 done()/display.quit() 关掉之后要能重新建立窗口，
        # 否则窗口对象还在、表面却已失效（再次 setup() 会拿到坏表面）
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
    """推进一帧（spec 01 §3.3）：事件 -> 物理（固定步 + 子步）-> 更新 -> 绘制。

    如果上一次 `update()` 收到了关窗请求（点了窗口的关闭按钮），这里先收尾再抛
    `SystemExit`——`while True: update()` 于是会自然结束（spec 01 §2.1）。
    想自己处理退出（比如弹"确认关闭"），在循环里看到 `should_quit()` 为真时
    调用 `reset_quit()` 把它拦下来。
    """
    scene = resolve_world(world)
    if input_state.should_quit():
        done()
        raise SystemExit(0)
    input_state.process_events(scene)  # 复位"刚发生"标记并消费事件队列

    # 帧序（spec 01 §3.3）：先把物理状态同步到显示层，再推进本帧的物理。
    # 因此**绘制的是上一帧物理的结果**——这样一次 update() 内不会出现"已经画过又被物理改写"
    # 的中间态，同时让显示状态与验收基线的时序一致。
    steps = scene.clock.tick()
    scene.sync_display()
    scene.entities.update()
    scene.visuals.update()
    scene.camera.advance(scene.clock.dt)  # 抖动/缩放按真实经过时间推进
    scene.camera._sync_to_subject()

    for _ in range(steps):
        stepping.step_space(scene.space, PHYSICS_DT, scene.max_step_distance, scene.max_substeps)

    window = get_window()
    if window is not None:
        window.draw(scene)

    if scene.tracer:
        global _tracer_frames, _tracer_started
        _tracer_frames += 1
        now = pygame.time.get_ticks()
        if _tracer_started is None:
            _tracer_started = now
        elif now - _tracer_started >= 1000:
            print(f"[pixelclass] FPS ≈ {_tracer_frames * 1000 / (now - _tracer_started):.0f}")
            _tracer_frames = 0
            _tracer_started = now
    else:
        pygame.display.flip() if pygame.display.get_init() else None
    scene.is_updated = True


def done() -> None:
    """结束程序：拆掉物理空间，再关闭窗口与 pygame。

    必须先把物理对象从空间里移除：留给解释器退出时销毁在 Python 3.12 上会段错误。
    """
    global _window
    from .scene import dispose_all

    dispose_all()
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


def bgpic(img: Any, world: Any = None) -> Any:
    """把一张图 / Surface / 瓦片地图作为背景铺开，并把相机尺寸设成它的大小。

    返回背景对象，便于后续移动或销毁（``bgpic("bg.png").kill()``）。
    """
    from .entity import Character  # 延迟导入：entity 依赖 runtime

    scene = resolve_world(world)
    background = Character(img, world=scene)
    if background.visual is not None:
        scene.camera.size = (background.width, background.height)
    return background


def speed(value: int, world: Any = None) -> int:
    """限制每帧位移的步长（"慢动作"，方便课堂观察移动过程）。"""
    scene = resolve_world(world)
    scene.speed_limit = max(1, int(value))
    return scene.speed_limit


def debug(enabled: bool = True, world: Any = None) -> bool:
    """调试绘制开关（刚体轮廓、相机中心），课堂演示"碰撞体到底在哪"很有用。"""
    scene = resolve_world(world)
    scene.debug = bool(enabled)
    return scene.debug


def tracer(enabled: bool = True, world: Any = None) -> bool:
    """帧率跟踪开关：每隔约一秒打印一次 FPS。"""
    scene = resolve_world(world)
    scene.tracer = bool(enabled)
    return scene.tracer


def random_pos(margin: int = 0, world: Any = None) -> Any:
    """在当前可视区域里随机取一个坐标（撒道具 / 出题用）。"""
    scene = resolve_world(world)
    width, height = scene.camera.size
    half_w = max(1.0, width / 2 - margin)
    half_h = max(1.0, height / 2 - margin)
    return vec(
        scene.camera.x + random.uniform(-half_w, half_w), scene.camera.y + random.uniform(-half_h, half_h)
    )


def set_depth(level: int = 1) -> str:
    """返回"上 level 层目录"的路径。

    历史行为会真的把进程工作目录切走（`os.chdir`），那会让之后所有相对路径都失效；
    现在只返回路径并给出弃用提示，需要切换时请自己 `os.chdir(set_depth(1))`。
    """
    path = os.path.abspath(os.path.join(cwd, *([os.pardir] * max(0, int(level)))))
    warnings.warn(
        "set_depth() 不再改变进程工作目录，只返回路径；需要切换请显式调用 os.chdir(set_depth(1))",
        DeprecationWarning,
        stacklevel=2,
    )
    return path


def set_gravity(x: Any, *y: Any, world: Any = None) -> None:
    """设置重力。支持 ``set_gravity(0, -1200)`` 与 ``set_gravity((0, -1200))``。"""
    scene = resolve_world(world)
    if y:
        scene.set_gravity(float(x), float(y[0]))
    else:
        scene.set_gravity(float(x[0]), float(x[1]))
