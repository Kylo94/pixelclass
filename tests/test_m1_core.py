"""M1 核心测试：时钟累积、固定步与自适应子步、场景与主循环（spec 01）。

全部在 headless 环境跑（conftest 已设置 dummy 驱动）。
"""

import math

import pygame
import pymunk
import pytest

import pixelclass as pc
from pixelclass.clock import PHYSICS_DT, Clock
from pixelclass.stepping import fastest_speed, substeps_for
from pixelclass.vec import Cartesian2pygame, pygame2Cartesian, to_cp, vec


# ------------------------------------------------------------------ 子步公式（spec 01 §3.2）
def test_substeps_slow_scene_is_one():
    assert substeps_for(0.0, PHYSICS_DT, 8.0, 16) == 1
    assert substeps_for(100.0, PHYSICS_DT, 8.0, 16) == 1  # 100*1/60 = 1.67 < 8


def test_substeps_uses_floor_plus_one():
    # 2400 px/s、dt=1/60、阈值 8 -> 商 5.0 -> 6 步（恰好整除也要多切一步）
    assert substeps_for(2400.0, PHYSICS_DT, 8.0, 16) == 6
    # 2000 -> 4.166 -> floor 4 + 1 = 5
    assert substeps_for(2000.0, PHYSICS_DT, 8.0, 16) == 5


def test_substeps_respects_cap_and_off_switch():
    assert substeps_for(100000.0, PHYSICS_DT, 8.0, 16) == 16  # 上限
    assert substeps_for(2400.0, PHYSICS_DT, 0.0, 16) == 1  # 阈值 0 = 关闭子步


def test_fastest_speed_ignores_static_bodies():
    space = pymunk.Space()
    static = pymunk.Body(body_type=pymunk.Body.STATIC)
    static.position = (0, 0)
    space.add(static, pymunk.Circle(static, 5))
    assert fastest_speed(space) == 0.0

    dynamic = pymunk.Body(1.0, 100.0)  # pymunk 7 要求动态刚体给出 mass / moment
    dynamic.velocity = (30.0, 40.0)
    space.add(dynamic, pymunk.Circle(dynamic, 5))
    assert fastest_speed(space) == pytest.approx(50.0)


# ------------------------------------------------------------------ 时钟（spec 01 §3.1）
def test_clock_accumulates_fixed_steps():
    ticks = iter([17] * 100)
    clock = Clock(ticker=lambda: next(ticks))
    total = sum(clock.tick() for _ in range(100))
    # 100 帧 × 17ms = 1.7s，按 1/60 步长应当推进 102 步
    assert total == 102
    assert clock.accumulator < PHYSICS_DT


def test_clock_clamps_huge_frame_time():
    clock = Clock(ticker=lambda: 5000)  # 5 秒（断点调试后的典型情况）
    steps = clock.tick()
    assert steps == math.floor(0.25 / PHYSICS_DT)  # 被 MAX_FRAME_TIME 截断
    assert clock.dt == 0.25


def test_clock_without_ticker_is_realtime():
    clock = Clock()
    clock.tick()  # 不应抛异常（内部用 pygame 的时钟）


# ------------------------------------------------------------------ 坐标（spec 01 §1）
def test_coordinate_round_trip_and_to_cp():
    size = (640, 480)
    point = (12.5, -30.25)
    assert pygame2Cartesian(Cartesian2pygame(point, size), size) == pytest.approx(point)
    assert Cartesian2pygame((0, 0), size) == (320.0, 240.0)
    assert to_cp(vec(1, 2)) == (1.0, 2.0)
    assert isinstance(to_cp(vec(1, 2))[0], float)


# ------------------------------------------------------------------ 场景与主循环（spec 01 §2、§3）
def test_setup_defaults_and_gravity():
    scene = pc.setup(320, 240)
    assert tuple(scene.gravity) == (0, 0), "默认无重力"
    assert tuple(scene.space.gravity) == (0, 0)
    pc.set_gravity(0, -1200)
    assert tuple(scene.space.gravity) == (0, -1200)


def test_update_advances_physics_with_fixed_steps():
    scene = pc.setup(320, 240)
    pc.set_gravity(0, -1200)
    ticks = iter([17] * 60)
    scene.clock = Clock(ticker=lambda: next(ticks))

    body = pymunk.Body(1.0, 100.0)
    body.position = (0, 0)
    scene.space.add(body, pymunk.Circle(body, 8))

    for _ in range(60):
        pc.update()

    # 60 帧 × 17ms = 1.02s ≈ 61 个物理步；速度应当约等于 -1200 × 1.0167
    assert body.velocity.y < -1100, body.velocity
    assert body.position.y < 0


def test_multiple_scenes_are_independent():
    first = pc.Scene()
    second = pc.Scene()
    pc.setup(320, 240, world=first)
    pc.setup(320, 240, world=second)
    pc.set_gravity(0, -1200, world=first)
    pc.set_gravity(0, 0, world=second)

    first.clock = Clock(ticker=lambda: 17)
    second.clock = Clock(ticker=lambda: 17)

    body_first = pymunk.Body(1.0, 100.0)
    body_second = pymunk.Body(1.0, 100.0)
    first.space.add(body_first, pymunk.Circle(body_first, 8))
    second.space.add(body_second, pymunk.Circle(body_second, 8))

    for _ in range(30):
        pc.update(first)

    assert body_first.position.y < 0, "第一个场景里的刚体应当下落"
    assert body_second.position.y == 0, "第二个场景不受影响"


def test_group_update_order_and_removal():
    log = []

    class Item:
        alive = True

        def _update(self):
            log.append("internal")

        def update(self):
            log.append("public")

    group = pc.Group()
    item = Item()
    group.add(item)
    group.update()
    assert log == ["internal", "public"]

    item.alive = False
    log.clear()
    group.update()
    assert log == [] and len(group) == 0, "已销毁对象应从集合里移除"


def test_screen_offset_math():
    scene = pc.Scene()
    scene.camera.size = (640, 480)
    scene.camera.pos = (100, 50)
    # 相机所在的数学点应当被画在屏幕中心
    assert scene.camera.to_screen((100, 50)) == (320.0, 240.0)
    # y 轴向上：数学点 y 更大 -> 屏幕 y 更小
    assert scene.camera.to_screen((100, 60))[1] == 230.0


def test_draw_line_then_frame_clears_it():
    scene = pc.setup(320, 240)
    pc.draw_line((0, 0), (10, 10), (255, 0, 0), 2)
    assert len(scene.lines) == 1
    pc.update()
    assert len(scene.lines) == 0, "线段只画一帧"


def test_public_subset_from_spec_08():
    """M1 已实现的公共名字必须在 __all__ 里（完整清单在 M4 补齐）。"""
    for name in (
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
        "Camera",
        "draw_line",
        "set_gravity",
        "sign",
        "Cartesian2pygame",
        "pygame2Cartesian",
        "to_cp",
        "vec",
        "K_SPACE",
    ):
        assert name in pc.__all__, f"{name} 应在 __all__ 里"
        assert getattr(pc, name) is not None
    assert pc.World is pc.Scene
    for leaked in ("pygame", "pymunk", "os", "sys", "types"):
        assert leaked not in pc.__all__, f"不应导出模块对象 {leaked}"


def test_pygame_initialised_headless():
    assert pygame.get_init()


def test_setup_after_done_recreates_the_window():
    pc.setup(320, 240)
    pc.done()
    scene = pc.setup(320, 240)  # 关掉之后再开：不应拿到失效的表面
    assert pygame.display.get_surface() is not None, "窗口应当被重新建立"
    pc.update(scene)
    assert scene.clock is not None
