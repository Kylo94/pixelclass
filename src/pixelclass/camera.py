"""相机（spec 06 §1，M1 只实现"看得见场景"所需的最小部分）。

M1 提供：尺寸、位置、跟随目标、给绘制用的偏移。
死区 / 抖动 / 平滑缩放属于相机里程碑（spec 06），这里先不实现，避免半成品接口。
"""

from typing import Any, Optional, Tuple

from .vec import vec


class Camera:
    """每个场景一个相机（不是全局单例）。"""

    def __init__(self, size: Optional[Tuple[int, int]] = None, world: Any = None) -> None:
        self.world = world
        self.size = (int(size[0]), int(size[1])) if size else (800, 600)
        self._position = vec(0, 0)
        self._subject: Any = None

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

    def reset(self, size: Tuple[int, int]) -> None:
        """场景重新初始化时复位（保持跟随目标）。"""
        self.size = (int(size[0]), int(size[1]))
        self._position = vec(0, 0)

    def _sync_to_subject(self) -> None:
        if self._subject is not None:
            self._position = vec(self._subject.pos)

    def screen_offset(self) -> Tuple[float, float]:
        """数学坐标 -> 屏幕坐标的平移量（此时屏幕 y 向下，所以 y 项是加的）。"""
        return (self.size[0] / 2 - self._position[0], self.size[1] / 2 + self._position[1])

    def to_screen(self, point: Any) -> Tuple[float, float]:
        """数学坐标 -> 屏幕坐标（含相机偏移与 y 轴翻转）。

        可见区域的中心就是相机所在的数学点 ``C = camera.pos``。
        """
        return (
            float(point[0]) + self.size[0] / 2 - self._position[0],
            self.size[1] / 2 + self._position[1] - float(point[1]),
        )
