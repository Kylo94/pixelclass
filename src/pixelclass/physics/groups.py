"""刚体集合容器（spec 08 §2.4）。

场景用它们分别持有"单体刚体"与"瓦片组"：每帧同步显示状态时遍历这两个集合。
"""

from ..scene import Group


class BodiesGroup(Group):
    """单体刚体集合（``scene.rigids``）。"""


class TiledMapBodiesGroup(Group):
    """瓦片刚体组集合（``scene.tiles``）。"""
