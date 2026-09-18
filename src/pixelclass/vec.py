"""向量与坐标换算（spec 01 §1）。

对外一律使用**数学坐标**：原点在窗口中心、x 向右、y 向上。屏幕坐标只在绘制与
鼠标事件换算时使用。
"""

from typing import Any, Tuple

import pygame

# 对外暴露的向量类型：直接用 pygame 的 Vector2（课堂上够用，且和鼠标事件一致）
vec = pygame.math.Vector2


def to_cp(value: Any) -> Tuple[float, float]:
    """把坐标 / 向量转成 pymunk 能接受的普通二元组。

    pygame 的 ``Vector2`` 直接传给 pymunk 会报 ctype 类型错误，所有跨边界的坐标
    都要经过这里。
    """
    return (float(value[0]), float(value[1]))


def Cartesian2pygame(pos: Any, size: Tuple[int, int]) -> Tuple[float, float]:
    """数学坐标 -> 屏幕坐标（原点左上、y 向下）。"""
    width, height = size
    return (float(pos[0]) + width / 2, height / 2 - float(pos[1]))


def pygame2Cartesian(pos: Any, size: Tuple[int, int]) -> Tuple[float, float]:
    """屏幕坐标 -> 数学坐标。"""
    width, height = size
    return (float(pos[0]) - width / 2, height / 2 - float(pos[1]))


def sign(value: float) -> int:
    """符号函数：正数 1、负数 -1、0 为 0。"""
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0
