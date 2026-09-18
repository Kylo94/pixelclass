"""相机（spec 06 §1）：跟随、死区、抖动、平滑缩放。

每个场景一个相机（不是全局单例）。相机只影响**绘制**，不改变任何对象坐标。
抖动与缩放按真实经过时间推进（测试可注入时钟）。
"""

import random
from typing import Any, Optional, Tuple

from .vec import vec


class Camera:
    """场景的取景器。"""

    def __init__(self, size: Optional[Tuple[int, int]] = None, world: Any = None) -> None:
        self.world = world
        self.size = (int(size[0]), int(size[1])) if size else (800, 600)
        self._position = vec(0, 0)
        self._subject: Any = None

        self.zoom = 1.0
        self.smooth_zoom = False  # 缩放时用平滑重采样（观感更好，成本更高）
        self._zoom_target: Optional[float] = None
        self._zoom_speed = 2.0

        self._deadzone = (0.0, 0.0)
        self._shake_left = 0.0
        self._shake_amount = 0.0
        self._shake_offset = vec(0, 0)

    # ---------------------------------------------------------------- 位置与目标
    @property
    def pos(self) -> Any:
        return self._position

    @pos.setter
    def pos(self, value: Any) -> None:
        self._position = vec(value)

    @property
    def x(self) -> float:
        return float(self._position[0])

    @x.setter
    def x(self, value: float) -> None:
        self._position = vec(float(value), self._position[1])

    @property
    def y(self) -> float:
        return float(self._position[1])

    @y.setter
    def y(self, value: float) -> None:
        self._position = vec(self._position[0], float(value))

    def follow(self, subject: Any) -> None:
        """跟随某个对象（传 ``None`` 解除跟随）。"""
        self._subject = subject

    def deadzone(self, width: float = 0.0, height: float = 0.0) -> None:
        """死区：目标在死区内时相机不动（避免呼吸式抖动）。"""
        self._deadzone = (abs(float(width)), abs(float(height)))

    # ---------------------------------------------------------------- 抖动与缩放
    def shake(self, amount: float = 8.0, duration: float = 0.3) -> None:
        """抖动一段时间后自动停。"""
        self._shake_amount = abs(float(amount))
        self._shake_left = max(0.0, float(duration))

    def stop_shake(self) -> None:
        self._shake_left = 0.0
        self._shake_offset = vec(0, 0)

    def zoom_to(self, scale: float, speed: float = 2.0) -> None:
        """平滑缩放到目标倍数。"""
        self._zoom_target = max(0.01, float(scale))
        self._zoom_speed = max(0.0, float(speed))

    def advance(self, dt: float) -> None:
        """按帧间隔推进抖动与缩放效果（spec 06 §1：按真实经过时间）。"""
        dt = max(0.0, float(dt))

        if self._shake_left > 0.0:
            self._shake_left = max(0.0, self._shake_left - dt)
            if self._shake_left > 0.0:
                self._shake_offset = vec(
                    random.uniform(-self._shake_amount, self._shake_amount),
                    random.uniform(-self._shake_amount, self._shake_amount),
                )
            else:
                self._shake_offset = vec(0, 0)

        if self._zoom_target is not None:
            step = self._zoom_speed * dt
            difference = self._zoom_target - self.zoom
            if abs(difference) <= step or step == 0.0:
                self.zoom = self._zoom_target
                self._zoom_target = None
            else:
                self.zoom += step if difference > 0 else -step

    def reset(self, size: Tuple[int, int]) -> None:
        """场景重新初始化时回到初始状态（位置 / 跟随目标 / 死区 / 抖动 / 缩放都复位）。"""
        self.size = (int(size[0]), int(size[1]))
        self._position = vec(0, 0)
        self._subject = None
        self._deadzone = (0.0, 0.0)
        self.zoom = 1.0
        self._zoom_target = None
        self.stop_shake()

    # ---------------------------------------------------------------- 每帧
    def _sync_to_subject(self) -> None:
        if self._subject is None:
            return
        target = vec(getattr(self._subject, "pos", self._position))
        dead_x, dead_y = self._deadzone
        dx = target[0] - self._position[0]
        dy = target[1] - self._position[1]
        if abs(dx) > dead_x:
            self._position = vec(target[0] - (dead_x if dx > 0 else -dead_x), self._position[1])
        if abs(dy) > dead_y:
            self._position = vec(self._position[0], target[1] - (dead_y if dy > 0 else -dead_y))

    def to_screen(self, point: Any) -> Tuple[float, float]:
        """数学坐标 → 屏幕坐标（含相机位置、缩放、y 轴翻转与抖动偏移）。"""
        dx = (float(point[0]) - self._position[0]) * self.zoom
        dy = (self._position[1] - float(point[1])) * self.zoom
        return (
            self.size[0] / 2 + dx + self._shake_offset[0],
            self.size[1] / 2 + dy + self._shake_offset[1],
        )

    def screen_offset(self) -> Tuple[float, float]:
        """数学坐标 → 屏幕坐标的平移量（供调试/兼容使用）。"""
        return (self.size[0] / 2 - self._position[0], self.size[1] / 2 + self._position[1])
