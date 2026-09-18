"""几何判定（spec 03 §5）。

为什么不用 pymunk 的 ``shapes_collide``：它在**深度重叠**（接触点超过两个）时会抛内部断言，
而"两个物体叠在一起"恰恰是课堂里最常见的情况。这里用标准几何算法自己实现：

* 圆-圆：圆心距与半径和比较；
* 圆-多边形：圆心在多边形内，或圆心到任一边的距离 ≤ 半径；
* 多边形-多边形：分离轴定理（SAT，适用于凸多边形）。

点查询仍走 pymunk 的 ``point_query``（它没有上述问题，且两个支持的版本行为一致）。
"""

import math
from typing import Any, List, Sequence, Tuple

import pymunk

from ..vec import to_cp

EPS = 1e-9


# ------------------------------------------------------------------ 世界坐标
def world_vertices(shape: Any) -> List[Tuple[float, float]]:
    """形状顶点转成**世界坐标**（``get_vertices`` 给的是本体局部坐标）。"""
    body = shape.body
    assert body is not None
    cos_a, sin_a = math.cos(body.angle), math.sin(body.angle)
    px, py = float(body.position[0]), float(body.position[1])
    points = []
    for vertex in shape.get_vertices():
        vx, vy = float(vertex[0]), float(vertex[1])
        points.append((vx * cos_a - vy * sin_a + px, vx * sin_a + vy * cos_a + py))
    return points


def circle_center(shape: Any) -> Tuple[float, float]:
    """圆心的世界坐标（考虑 ``offset`` 与本体旋转）。"""
    body = shape.body
    assert body is not None
    offset = getattr(shape, "offset", (0, 0)) or (0, 0)
    cos_a, sin_a = math.cos(body.angle), math.sin(body.angle)
    ox, oy = float(offset[0]), float(offset[1])
    return (
        ox * cos_a - oy * sin_a + float(body.position[0]),
        ox * sin_a + oy * cos_a + float(body.position[1]),
    )


def shape_bounds(shape: Any) -> Tuple[float, float, float, float]:
    """轴对齐包围盒 ``(left, bottom, right, top)``（世界坐标，自己算，不依赖缓存）。"""
    if isinstance(shape, pymunk.Circle):
        cx, cy = circle_center(shape)
        radius = float(shape.radius)
        return (cx - radius, cy - radius, cx + radius, cy + radius)
    vertices = world_vertices(shape)
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    return (min(xs), min(ys), max(xs), max(ys))


def bounds_center(shape: Any) -> List[float]:
    left, bottom, right, top = shape_bounds(shape)
    return [(left + right) / 2, (bottom + top) / 2]


def bounds_size(shape: Any) -> Tuple[float, float]:
    left, bottom, right, top = shape_bounds(shape)
    return (right - left, top - bottom)


# ------------------------------------------------------------------ 点查询
def point_in_shape(shape: Any, point: Any) -> bool:
    """点是否落在形状内部（含边界）：``point_query`` 的距离在内部为负。"""
    info = shape.point_query(to_cp(point))
    distance = getattr(info, "distance", None)
    if distance is None:  # 老版本把结果当序列用
        try:
            distance = float(info[0])
        except (TypeError, IndexError):
            return False
    return float(distance) <= 0.0


# ------------------------------------------------------------------ 形状重叠
def _point_segment_distance(
    point: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]
) -> float:
    px, py = point
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= EPS:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def point_in_polygon(point: Tuple[float, float], vertices: Sequence[Tuple[float, float]]) -> bool:
    """射线法（支持凸/凹多边形）。"""
    px, py = point
    inside = False
    count = len(vertices)
    for index in range(count):
        x1, y1 = vertices[index]
        x2, y2 = vertices[(index + 1) % count]
        if (y1 > py) != (y2 > py):
            cross_x = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
            if px < cross_x:
                inside = not inside
    return inside


def _circle_polygon_overlap(
    center: Tuple[float, float], radius: float, vertices: Sequence[Tuple[float, float]]
) -> bool:
    if point_in_polygon(center, vertices):
        return True
    count = len(vertices)
    for index in range(count):
        a = vertices[index]
        b = vertices[(index + 1) % count]
        if _point_segment_distance(center, a, b) <= radius:
            return True
    return False


def _project(vertices: Sequence[Tuple[float, float]], axis: Tuple[float, float]) -> Tuple[float, float]:
    dots = [v[0] * axis[0] + v[1] * axis[1] for v in vertices]
    return (min(dots), max(dots))


def polygons_overlap(first: Sequence[Tuple[float, float]], second: Sequence[Tuple[float, float]]) -> bool:
    """分离轴定理：能找到一条分离轴就说明不重叠。"""
    for vertices in (first, second):
        count = len(vertices)
        for index in range(count):
            x1, y1 = vertices[index]
            x2, y2 = vertices[(index + 1) % count]
            axis = (-(y2 - y1), x2 - x1)
            length = math.hypot(axis[0], axis[1])
            if length <= EPS:
                continue
            axis = (axis[0] / length, axis[1] / length)
            min_a, max_a = _project(first, axis)
            min_b, max_b = _project(second, axis)
            if max_a < min_b - EPS or max_b < min_a - EPS:
                return False
    return True


def shapes_overlap(first: Any, second: Any) -> bool:
    """两个形状是否接触 / 重叠（覆盖圆-圆、圆-多边形、多边形-多边形）。"""
    first_is_circle = isinstance(first, pymunk.Circle)
    second_is_circle = isinstance(second, pymunk.Circle)

    if first_is_circle and second_is_circle:
        (x1, y1), (x2, y2) = circle_center(first), circle_center(second)
        return math.hypot(x2 - x1, y2 - y1) <= float(first.radius) + float(second.radius)

    if first_is_circle:
        return _circle_polygon_overlap(circle_center(first), float(first.radius), world_vertices(second))
    if second_is_circle:
        return _circle_polygon_overlap(circle_center(second), float(second.radius), world_vertices(first))

    return polygons_overlap(world_vertices(first), world_vertices(second))
