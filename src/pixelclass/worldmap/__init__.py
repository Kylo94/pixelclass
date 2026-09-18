"""地图模块：TMX 解析、图层渲染、对象层 → 实体（spec 05）。"""

from .tiled import MapObject, TiledMap

__all__ = ["TiledMap", "MapObject"]
