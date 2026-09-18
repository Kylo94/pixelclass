"""帧时钟与固定物理步长（spec 01 §3.1）。

设计要点：**时间来源可注入**。课堂演示用真实时间，自动化测试注入固定步进，
这样"同一段场景每次运行结果完全一致"。
"""

from typing import Callable, Optional

import pygame

PHYSICS_DT = 1 / 60  # 固定物理步长：秒
MAX_FRAME_TIME = 0.25  # 单帧最多累积的真实时间（防止断点调试后一次补上百步）
DEFAULT_FPS = 60


class Clock:
    """把真实经过时间切成整数个固定物理步。

    :param fps: 未注入 ``ticker`` 时限制的帧率
    :param ticker: 返回"本帧经过的毫秒数"的可调用对象（测试注入固定值即可复现结果）
    """

    def __init__(self, fps: int = DEFAULT_FPS, ticker: Optional[Callable[[], float]] = None) -> None:
        self.fps = fps
        self._ticker = ticker
        self._clock = None if ticker is not None else pygame.time.Clock()
        self._accumulator = 0.0
        self.dt = 0.0  # 上一帧真实时间（已被 MAX_FRAME_TIME 截断）
        self.steps = 0  # 上一帧推进的物理步数

    @property
    def accumulator(self) -> float:
        """尚未凑够一整步的剩余时间（秒）。"""
        return self._accumulator

    def _elapsed(self) -> float:
        if self._ticker is not None:
            return self._ticker() / 1000.0
        assert self._clock is not None
        return self._clock.tick(self.fps) / 1000.0

    def tick(self) -> int:
        """推进一帧，返回本帧应当执行的物理步数（不足一步时为 0）。"""
        self.dt = min(max(self._elapsed(), 0.0), MAX_FRAME_TIME)
        self._accumulator += self.dt
        steps = 0
        while self._accumulator >= PHYSICS_DT:
            self._accumulator -= PHYSICS_DT
            steps += 1
        self.steps = steps
        return steps
