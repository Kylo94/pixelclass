"""瓦片刚体组（spec 03 §4）：用一整张瓦片地图当碰撞体。

每块瓦片各自是一个形状，但共享一个"组位置"：组移动时每块瓦片按**自己的相对偏移**
重新摆放。因此整张地图会作为一个整体移动，而不是散落的碎片。
"""

from typing import Any, Iterable, List, Optional, Tuple

import pymunk

from ..error_help import bilingual
from ..vec import vec
from .body import Body, BODY_TYPES, resolve_body_type
from .geometry import bounds_center, bounds_size, shapes_overlap

DYNAMIC_MAP_WARNING = bilingual(
    "不建议把整张网格地图设成动态刚体：瓦片之间会按邻居关系连成一片；" "需要完全刚性请用 STATIC。",
    "A whole tile map as a DYNAMIC body is not recommended: tiles get linked to "
    "their neighbours. Use STATIC for a rigid map.",
)


class TiledMapBodies:
    """一组瓦片刚体（顺序即创建顺序）。"""

    def __init__(
        self,
        body_type: Any = "STATIC",
        objs: Optional[Iterable[Any]] = None,
        sensor: bool = False,
        world: Any = None,
    ) -> None:
        from ..context import resolve_world  # 延迟导入，避免 context <-> scene <-> physics 成环

        self.world = resolve_world(world)
        self.parent: Any = None
        self.pos = vec(0, 0)
        self.bodies: List[Body] = []
        self.joints: List[Any] = []
        self._type = resolve_body_type(body_type)

        for obj in objs or []:
            points = list(getattr(obj, "points", []) or [])
            if len(points) < 3:
                continue  # 解析不出来的对象跳过，不打断整张地图
            tile = Body(
                body_type,
                "POLY",
                size=points,
                sensor=sensor,
                world=self.world,
                _register=False,
            )
            tile.offset = vec(float(getattr(obj, "x", 0.0)), float(getattr(obj, "y", 0.0)))
            self.bodies.append(tile)

        self.world.tiles.add(self)
        self.set_pos(self.pos)  # 建好立刻归位（不等第一次 goto）

        if self._type == BODY_TYPES["DYNAMIC"]:
            print(DYNAMIC_MAP_WARNING)
            self.connect_neighbors()

    # ------------------------------------------------------------------ 容器接口
    def __len__(self) -> int:
        return len(self.bodies)

    def __iter__(self):
        return iter(list(self.bodies))

    def __getitem__(self, index: int) -> Body:
        return self.bodies[index]

    # ------------------------------------------------------------------ 位置 / 角度
    def set_pos(self, pos: Any) -> None:
        """设置组位置：每块瓦片按 ``pos + 自己的偏移`` 摆放。"""
        self.pos = vec(pos)
        for tile in self.bodies:
            tile.set_pos(self.pos + tile.offset)

    def set_rot(self, degrees: float) -> None:
        """设置整组角度（每块瓦片同步）。"""
        for tile in self.bodies:
            tile.set_rot(degrees)

    def set_scale(self, scalex: float, scaley: Optional[float] = None) -> None:
        """缩放每块瓦片的几何（整张地图一起缩放）。"""
        scaley = scalex if scaley is None else scaley
        for tile in self.bodies:
            vertices = tile.shape.get_vertices()
            tile.shape.unsafe_set_vertices([(float(v[0]) * scalex, float(v[1]) * scaley) for v in vertices])
            self.world.space.reindex_shapes_for_body(tile.body)

    def set_parent(self, parent: Any) -> None:
        self.parent = parent
        self.set_pos(getattr(parent, "pos", self.pos))

    def sync(self) -> None:
        """物理 -> 显示：只把组位置写给宿主的显示缓存。"""
        if self.parent is None:
            return
        sync_pos = getattr(self.parent, "sync_pos", None)
        if sync_pos is not None:
            sync_pos(self.pos)

    # ------------------------------------------------------------------ 生命周期
    def kill(self) -> None:
        for joint in list(self.joints):
            try:
                self.world.space.remove(joint)
            except (AssertionError, KeyError):
                pass
        self.joints.clear()
        for tile in list(self.bodies):
            tile.kill()
        self.bodies.clear()
        self.world.tiles.remove(self)
        self.parent = None

    # ------------------------------------------------------------------ 查询
    def point_query(self, point: Any) -> bool:
        """点是否落在组内任意一块瓦片上。"""
        return any(tile.point_query(point) for tile in self.bodies)

    def collide(self, other: Any) -> bool:
        """与另一个刚体 / 瓦片组是否接触。"""
        if isinstance(other, TiledMapBodies):
            for mine in self.bodies:
                for theirs in other.bodies:
                    if shapes_overlap(mine.shape, theirs.shape):
                        return True
            return False
        for mine in self.bodies:
            if shapes_overlap(mine.shape, other.shape):
                return True
        return False

    # ------------------------------------------------------------------ 邻居连接
    def _pitch(self) -> Tuple[float, float]:
        """推断网格间距：取相邻中心点最小间距（推断不出来时退化为瓦片自身尺寸）。"""
        centers = [bounds_center(tile.shape) for tile in self.bodies]
        sizes = [bounds_size(tile.shape) for tile in self.bodies]
        xs = sorted({round(c[0], 4) for c in centers})
        ys = sorted({round(c[1], 4) for c in centers})
        dxs = [b - a for a, b in zip(xs, xs[1:]) if b - a > 1e-6]
        dys = [b - a for a, b in zip(ys, ys[1:]) if b - a > 1e-6]
        width = min((s[0] for s in sizes), default=1.0) or 1.0
        height = min((s[1] for s in sizes), default=1.0) or 1.0
        return (min(dxs) if dxs else width, min(dys) if dys else height)

    def connect_neighbors(self) -> List[Any]:
        """把**上下左右相邻**的瓦片用销钉连起来，使整张地图成为一体。

        按网格间距把瓦片归到格子里，只连相邻格子：25 块瓦片的网格只有约 40 个关节，
        远小于两两连接；隔着很远的孤立瓦片不会被连进来。
        """
        pitch_x, pitch_y = self._pitch()
        cells = {}
        for tile in self.bodies:
            center = bounds_center(tile.shape)
            cells[(round(center[0] / pitch_x), round(center[1] / pitch_y))] = tile
        for (gx, gy), tile in cells.items():
            for step in ((1, 0), (0, 1)):
                neighbor = cells.get((gx + step[0], gy + step[1]))
                if neighbor is None:
                    continue
                joint = pymunk.PinJoint(tile.body, neighbor.body)
                self.world.space.add(joint)
                self.joints.append(joint)
        return self.joints
