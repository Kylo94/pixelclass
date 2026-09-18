"""TMX 瓦片地图（spec 05）。

* 载入时**一次性**把 Tiled 的坐标（左上原点、y 向下）换算成引擎坐标（屏幕中心原点、y 向上）；
  之后多次读取对象坐标不会再叠加偏移（反复叠加是旧实现踩过的坑）。
* 对象层 → 实体：每个对象一个实体（不是把整层合成一个大刚体）。
* 整张地图当碰撞体是另一条路径（``Entity(size=[对象…])`` → 瓦片刚体组）。
"""

import os
from typing import Any, Dict, List, Optional, Tuple

import pygame
from pytmx.util_pygame import load_pygame  # type: ignore[import-untyped]  # pytmx 不带类型标注

from ..context import resolve_world
from ..error_help import bilingual, not_initialised

#: 多边形对象的顶点少于这个数就当矩形处理
MIN_POLYGON_POINTS = 3


class MapObject:
    """对象层里的一个对象（坐标已换算成引擎坐标）。"""

    __slots__ = ("name", "x", "y", "width", "height", "points", "properties", "gid", "tmx_object")

    def __init__(
        self,
        name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        points: Optional[List[Tuple[float, float]]],
        properties: Dict[str, Any],
        gid: Optional[int],
        tmx_object: Any,
    ) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.points = points
        self.properties = properties
        self.gid = gid
        self.tmx_object = tmx_object

    def __repr__(self) -> str:  # pragma: no cover - 仅调试用
        return f"<MapObject {self.name!r} at ({self.x:.1f}, {self.y:.1f})>"


class TiledMap:
    """一张 TMX 地图。"""

    def __init__(self, tilemap: str) -> None:
        if not isinstance(tilemap, str) or not os.path.isfile(tilemap):
            raise FileNotFoundError(
                bilingual(
                    f"找不到地图文件：{os.path.abspath(str(tilemap))}",
                    "Map file not found: check the path and the current working directory.",
                )
            )
        if not pygame.display.get_init():
            # 图块需要 pygame 的显示表面；与「需要窗口的接口要先 setup()」一致，给可读提示
            raise not_initialised("载入地图")
        self._tmx = load_pygame(tilemap, pixelalpha=True)
        self.width = int(self._tmx.width * self._tmx.tilewidth)
        self.height = int(self._tmx.height * self._tmx.tileheight)
        self.tile_width = int(self._tmx.tilewidth)
        self.tile_height = int(self._tmx.tileheight)
        self._objects = [self._convert(obj) for obj in list(self._tmx.objects)]

    # ------------------------------------------------------------------ 坐标换算
    def to_engine(self, x: float, y: float, width: float = 0.0, height: float = 0.0) -> Tuple[float, float]:
        """Tiled 坐标 → 引擎坐标：按对象**中心**对齐到地图中心（只做一次）。"""
        return (
            float(x) + width / 2 - self.width / 2,
            self.height / 2 - (float(y) + height / 2),
        )

    def _convert(self, obj: Any) -> MapObject:
        width = float(getattr(obj, "width", 0) or 0)
        height = float(getattr(obj, "height", 0) or 0)
        points = getattr(obj, "points", None)
        if points:
            # 多边形：顶点相对对象原点、y 向下；换算成"以多边形中心为原点"的引擎坐标
            xs = [float(p[0]) for p in points]
            ys = [float(p[1]) for p in points]
            local = [(x - min(xs), max(ys) - y) for x, y in zip(xs, ys)]
            span_x = max(xs) - min(xs)
            span_y = max(ys) - min(ys)
            center_x, center_y = self.to_engine(obj.x + min(xs), obj.y + min(ys), span_x, span_y)
            local = [(x - span_x / 2, y - span_y / 2) for x, y in local]
            return MapObject(
                str(getattr(obj, "name", "") or ""),
                center_x,
                center_y,
                span_x,
                span_y,
                local,
                dict(getattr(obj, "properties", {}) or {}),
                getattr(obj, "gid", None),
                obj,
            )
        center_x, center_y = self.to_engine(obj.x, obj.y, width, height)
        return MapObject(
            str(getattr(obj, "name", "") or ""),
            center_x,
            center_y,
            width,
            height,
            None,
            dict(getattr(obj, "properties", {}) or {}),
            getattr(obj, "gid", None),
            obj,
        )

    # ------------------------------------------------------------------ 查询
    @property
    def objects(self) -> List[MapObject]:
        """对象层里的对象（**幂等**：多次读取坐标不变）。"""
        return list(self._objects)

    def get_objects(self, name: Optional[str] = None) -> List[MapObject]:
        """按名字过滤；不传名字返回全部；名字不存在时返回空列表（不报错）。"""
        if name is None:
            return self.objects
        return [item for item in self._objects if item.name == name]

    def tile_image(self, gid: Optional[int]) -> Any:
        """按 gid 取图块图像（取不到返回 None）。"""
        if gid is None:
            return None
        try:
            return self._tmx.get_tile_image_by_gid(gid)
        except Exception:  # noqa: BLE001 - 图集缺图块时不该中断整张地图
            return None

    # ------------------------------------------------------------------ 渲染
    def render(self, surface: pygame.Surface) -> pygame.Surface:
        """把地图的全部图块图层画到给定表面（地图中心对齐表面中心）。"""
        offset_x = (surface.get_width() - self.width) / 2
        offset_y = (surface.get_height() - self.height) / 2
        for layer in self._tmx.layers:
            tiles = getattr(layer, "tiles", None)
            if tiles is None:
                continue  # 对象层没有图块
            for x, y, image in tiles():
                if image is None:
                    continue
                surface.blit(
                    image,
                    (
                        offset_x + x * self.tile_width,
                        offset_y + y * self.tile_height,
                    ),
                )
        return surface

    # ------------------------------------------------------------------ 对象层 → 实体
    def create_objects(
        self,
        name: Optional[str] = None,
        body_type: Any = "STATIC",
        sensor: bool = False,
        images: Optional[Dict[str, Any]] = None,
        world: Any = None,
    ) -> List[Any]:
        """把对象层的对象实例化成**游戏对象**（每个对象一个）。"""
        from ..entity import Entity  # 延迟导入：entity 依赖 runtime，模块级会成环

        scene = resolve_world(world)
        images = images or {}
        created = []
        for item in self.get_objects(name):
            size: Any = item.points if item.points else (item.width, item.height)
            source = images.get(item.name)
            if source is None and item.gid is not None:
                source = self.tile_image(item.gid)
            entity = Entity(source, size=size, body_type=body_type, sensor=sensor, world=scene)
            entity.name = item.name
            entity.properties = dict(item.properties)
            entity.tmx_object = item.tmx_object
            entity.goto(item.x, item.y)
            created.append(entity)
        return created

    def __repr__(self) -> str:  # pragma: no cover - 仅调试用
        return f"<TiledMap {self.width}×{self.height} 对象 {len(self._objects)} 个>"
