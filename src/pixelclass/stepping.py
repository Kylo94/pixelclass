"""固定步长内的自适应子步：防高速穿透（spec 01 §3.2）。

pymunk 没有连续碰撞检测：一步内位移超过碰撞体厚度，物体就直接穿过去了。
这里把固定步长按"最快物体一步走多远"切分成若干子步，使每个子步的位移小于阈值。
"""

from typing import Any, Tuple

import pymunk

DEFAULT_MAX_STEP_DISTANCE = 8.0  # 像素：单个子步允许的最大位移
DEFAULT_MAX_SUBSTEPS = 16  # 子步上限（防止极端速度把一帧切成几百步）


def substeps_for(fastest_speed: float, dt: float, limit: float, cap: int) -> int:
    """由最快速度算出子步数（纯函数，方便单测与说明）。

    * ``limit <= 0``：关闭子步，恒为 1；
    * 慢速（``最快速度 × dt <= limit``）：恒为 1，行为与性能都不变；
    * 否则为 ``floor(最快速度 × dt / limit) + 1`` —— 注意是"向下取整再 +1"，
      恰好整除时也多切一步，保证每个子步位移**严格小于**阈值。
    """
    if limit <= 0:
        return 1
    travelled = fastest_speed * dt
    if travelled <= limit:
        return 1
    needed = int(travelled / limit) + 1
    return max(1, min(int(cap), needed))


def fastest_speed(space: Any) -> float:
    """空间内所有**非静态**刚体的最大速度（静态物体不参与）。"""
    fastest = 0.0
    for body in space.bodies:
        if body.body_type == pymunk.Body.STATIC:
            continue
        velocity = body.velocity
        speed = (velocity[0] ** 2 + velocity[1] ** 2) ** 0.5
        if speed > fastest:
            fastest = speed
    return fastest


def step_space(
    space: Any,
    dt: float,
    limit: float = DEFAULT_MAX_STEP_DISTANCE,
    cap: int = DEFAULT_MAX_SUBSTEPS,
) -> int:
    """推进一个固定物理步（必要时切成子步），返回实际使用的子步数。"""
    count = substeps_for(fastest_speed(space), dt, limit, cap)
    if count <= 1:
        space.step(dt)
        return 1
    sub_dt = dt / count
    for _ in range(count):
        space.step(sub_dt)
    return count


def measure(space: Any, dt: float, limit: float, cap: int) -> Tuple[float, int]:
    """返回 (最快速度, 子步数)，供调试与验收观测使用。"""
    speed = fastest_speed(space)
    return speed, substeps_for(speed, dt, limit, cap)
