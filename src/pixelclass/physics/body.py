"""刚体封装（spec 03 §1–§3）。

对外名字是 ``Body``。职责：
  * 按 ``shape`` / ``size`` 造出形状（圆 / 矩形 / 多边形）；
  * 代理速度、质量、摩擦、弹性等属性；
  * **位置 / 角度没变就不重排宽相**（每帧冗余重排是课堂演示卡顿的主因）；
  * 每帧把刚体状态同步给显示层——只改显示缓存，绝不反向写回（spec 01 §4）。
"""

# 注意：对"当前场景"的依赖在函数内延迟导入——
# context 在导入期就会构造 Scene，而 Scene 初始化时又会用到物理集合，模块级导入会成环。

import math
from typing import Any, Dict

import pymunk

from ..vec import to_cp, vec
from .geometry import point_in_shape, shapes_overlap

#: 字符串 -> pymunk 刚体类型（课堂写法用字符串更直观）
BODY_TYPES: Dict[str, int] = {
    "STATIC": pymunk.Body.STATIC,
    "DYNAMIC": pymunk.Body.DYNAMIC,
    "KINEMATIC": pymunk.Body.KINEMATIC,
}

SHAPE_KINDS = ("CIRCLE", "BOX", "POLY")

DEFAULT_DENSITY = 1.0  # 动态刚体的默认密度（质量与转动惯量由几何算出）


def resolve_body_type(body_type: Any) -> int:
    """接受 ``"DYNAMIC"`` 这类字符串，也接受 pymunk 常量。"""
    if isinstance(body_type, str):
        key = body_type.upper()
        if key not in BODY_TYPES:
            raise ValueError(
                f"未知的刚体类型 {body_type!r}：请用 STATIC / DYNAMIC / KINEMATIC "
                f"（或 pymunk.Body 的对应常量）"
            )
        return BODY_TYPES[key]
    return int(body_type)


class Body:
    """一个刚体 + 一个形状。"""

    def __init__(
        self,
        body_type: Any = "DYNAMIC",
        shape: str = "CIRCLE",
        size: Any = None,
        sensor: bool = False,
        world: Any = None,
        _register: bool = True,
    ) -> None:
        from ..context import resolve_world  # 延迟导入，避免 context <-> scene <-> physics 成环

        self.world = resolve_world(world)
        self.kind = str(shape).upper()
        if self.kind not in SHAPE_KINDS:
            raise ValueError(f"未知的形状 {shape!r}：请用 {' / '.join(SHAPE_KINDS)}")
        self._sensor = bool(sensor)
        self._type = resolve_body_type(body_type)
        self.parent: Any = None
        self.offset = vec(0, 0)  # 瓦片组里的相对偏移；单体刚体恒为 0

        if self._type == pymunk.Body.DYNAMIC:
            # 动态刚体必须有质量与转动惯量（pymunk 会校验），因此不传 body_type 而先建默认动态体
            self.body = pymunk.Body(DEFAULT_DENSITY, 1.0)
        else:
            self.body = pymunk.Body(body_type=self._type)
        self.shape = self._make_shape(self.kind, size, self._sensor)
        if self._type == pymunk.Body.DYNAMIC:
            self.body.mass = DEFAULT_DENSITY * self.shape.area
            self.body.moment = DEFAULT_DENSITY * max(float(getattr(self.shape, "moment", 1.0)), 1e-6)

        self.world.space.add(self.body, self.shape)
        if _register:
            self.world.rigids.add(self)

    # ------------------------------------------------------------------ 形状
    def _make_shape(self, kind: str, size: Any, sensor: bool) -> Any:
        shape = self._create_shape(kind, size)
        shape.sensor = bool(sensor)
        return shape

    def _create_shape(self, kind: str, size: Any) -> Any:
        if kind == "CIRCLE":
            radius = int(size if size is not None else 1)
            if radius <= 0:
                raise ValueError(f"圆形半径必须是正整数，收到 {size!r}")
            return pymunk.Circle(self.body, radius)
        if kind == "BOX":
            if not isinstance(size, (tuple, list)) or len(size) != 2:
                raise ValueError(f"矩形需要 (宽, 高)，收到 {size!r}")
            return pymunk.Poly.create_box(self.body, (float(size[0]), float(size[1])))
        if not isinstance(size, (list, tuple)) or len(size) < 3:
            raise ValueError(f"多边形需要至少三个顶点，收到 {size!r}")
        return pymunk.Poly(self.body, [(float(p[0]), float(p[1])) for p in size])

    # ------------------------------------------------------------------ 属性
    @property
    def sensor(self) -> bool:
        return bool(self.shape.sensor)

    @sensor.setter
    def sensor(self, value: bool) -> None:
        self.shape.sensor = bool(value)

    @property
    def velocity(self) -> Any:
        return self.body.velocity

    @velocity.setter
    def velocity(self, value: Any) -> None:
        self.body.velocity = to_cp(value)

    @property
    def angular_velocity(self) -> float:
        return float(self.body.angular_velocity)

    @angular_velocity.setter
    def angular_velocity(self, value: float) -> None:
        self.body.angular_velocity = float(value)

    @property
    def mass(self) -> float:
        return float(self.body.mass)

    @mass.setter
    def mass(self, value: float) -> None:
        self.body.mass = float(value)

    @property
    def elasticity(self) -> float:
        return float(self.shape.elasticity)

    @elasticity.setter
    def elasticity(self, value: float) -> None:
        self.shape.elasticity = float(value)

    @property
    def friction(self) -> float:
        return float(self.shape.friction)

    @friction.setter
    def friction(self, value: float) -> None:
        self.shape.friction = float(value)

    @property
    def body_type(self) -> int:
        return int(self.body.body_type)

    # ------------------------------------------------------------------ 位置 / 角度
    def set_pos(self, pos: Any) -> None:
        """写位置；**没变就直接返回**（不触发宽相重排）。"""
        target = to_cp(pos)
        body = self.shape.body
        assert body is not None
        if body.position[0] == target[0] and body.position[1] == target[1]:
            return
        body.position = target
        self.world.space.reindex_shapes_for_body(body)

    def set_rot(self, degrees: float) -> None:
        """写角度（度）；**没变就直接返回**。"""
        angle = math.radians(float(degrees))
        body = self.shape.body
        assert body is not None
        if body.angle == angle:
            return
        body.angle = angle
        self.world.space.reindex_shapes_for_body(body)

    def set_velocity(self, value: Any) -> None:
        self.velocity = value

    # ------------------------------------------------------------------ 生命周期
    def set_parent(self, parent: Any) -> None:
        """挂到宿主（实体）上，并立刻把刚体摆到宿主的位置。"""
        self.parent = parent
        self.set_pos(getattr(parent, "pos", vec(0, 0)))

    def sync(self) -> None:
        """物理 -> 显示：只改宿主的显示缓存（spec 01 §4 不变量）。"""
        parent = self.parent
        if parent is None:
            return
        body = self.shape.body
        assert body is not None
        sync_pos = getattr(parent, "sync_pos", None)
        if sync_pos is not None:
            sync_pos(body.position)
        sync_rot = getattr(parent, "sync_rot", None)
        if sync_rot is not None:
            sync_rot(math.degrees(body.angle))

    def kill(self) -> None:
        """从空间里移除自己。"""
        try:
            self.world.space.remove(self.shape, self.body)
        except (AssertionError, KeyError):
            pass
        self.world.rigids.remove(self)
        self.parent = None

    # ------------------------------------------------------------------ 查询
    def point_query(self, point: Any) -> bool:
        """点是否落在这个刚体上（spec 03 §5）。"""
        return point_in_shape(self.shape, point)

    def collide(self, other: Any) -> bool:
        """与另一个刚体是否接触（几何判定）。"""
        return shapes_overlap(self.shape, other.shape)

    def __repr__(self) -> str:  # pragma: no cover - 仅调试用
        body = self.shape.body
        pos = tuple(round(v, 2) for v in (body.position if body else (0, 0)))
        return f"<Body {self.kind} at {pos}>"
