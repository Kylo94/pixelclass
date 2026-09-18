"""场景（Scene）：一套独立的世界（spec 01 §2）。

组合而非继承：场景拥有物理空间、对象集合、绘制集合、相机与时钟，
并且**不是全局单例**——课堂上可以同时存在多个互不干扰的场景。
"""

from typing import Any, Callable, Iterator, List, Optional

import pymunk

from .camera import Camera
from .clock import Clock
from .stepping import DEFAULT_MAX_STEP_DISTANCE, DEFAULT_MAX_SUBSTEPS
from .vec import to_cp, vec


class Group:
    """有序的对象集合（比 set 稳定、比 list 好删）。

    ``update()`` 逐一遍历：先调内部 ``_update()``，对象仍存活时再调可覆写的 ``update()``。
    """

    def __init__(self, update_hook: Optional[Callable[[Any], None]] = None) -> None:
        self._items: List[Any] = []
        self._update_hook = update_hook

    # ------------------------------------------------------------ 容器接口
    def add(self, item: Any) -> None:
        if item not in self._items:
            self._items.append(item)

    def remove(self, item: Any) -> None:
        if item in self._items:
            self._items.remove(item)

    def clear(self) -> None:
        self._items.clear()

    def __iter__(self) -> Iterator[Any]:
        return iter(list(self._items))

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, item: Any) -> bool:
        return item in self._items

    def __getitem__(self, index: int) -> Any:
        return self._items[index]

    # ------------------------------------------------------------ 更新
    def update(self) -> None:
        for item in list(self._items):
            if not getattr(item, "alive", True):
                self._items.remove(item)
                continue
            if self._update_hook is not None:
                self._update_hook(item)
            internal = getattr(item, "_update", None)
            if internal is not None:
                internal()
            if getattr(item, "alive", True):
                public = getattr(item, "update", None)
                if public is not None:
                    public()


class Scene:
    """一套独立的世界：物理空间 + 对象集合 + 相机 + 时钟。"""

    def __init__(self, name: str = "") -> None:
        self.name = name
        self.space = pymunk.Space()
        self.gravity = vec(0, 0)  # spec 01 §2.1：默认无重力
        self.space.gravity = to_cp(self.gravity)

        self.entities = Group()
        self.visuals = Group()

        # 物理层集合：刚体 / 瓦片组（延迟导入避免循环：scenario 不依赖物理模块）
        from .physics.groups import BodiesGroup, TiledMapBodiesGroup

        self.rigids = BodiesGroup()
        self.tiles = TiledMapBodiesGroup()

        self.camera = Camera(world=self)
        self.clock = Clock()

        # 自适应子步参数（spec 01 §3.2）：0 表示关闭子步
        self.max_step_distance = DEFAULT_MAX_STEP_DISTANCE
        self.max_substeps = DEFAULT_MAX_SUBSTEPS

        self.lines: List[Any] = []  # draw_line() 画的线，下一帧清除
        self.debug = False
        self.is_updated = False  # 本帧是否已被推进过（教学/调试用）
        self.speed_limit = 1  # forward()/backward() 每次循环最多走多少像素（spec 07 §5 的 speed()）
        self.auto_update = False  # 教学演示：位移过程中自动推进画面（默认关闭，行为可复现）
        self.tracer = False  # 帧率跟踪开关（spec 07 §5 的 tracer()）
        self.resources: Any = None  # 资源缓存（首次 load_image() 时建立）

    # ------------------------------------------------------------ 物理
    def set_gravity(self, x: float, y: float) -> None:
        self.gravity = vec(x, y)
        self.space.gravity = to_cp(self.gravity)

    # ------------------------------------------------------------ 同步与生命周期
    def sync_display(self) -> None:
        """物理 -> 显示：只改显示缓存，不反向写回刚体（spec 01 §4）。"""
        for body in list(self.rigids):
            body.sync()
        for group in list(self.tiles):
            group.sync()

    def reset(self, size: tuple) -> None:
        """重新初始化该场景（换一套空间与集合，保留相机对象本身）。"""
        self.space = pymunk.Space()
        self.space.gravity = to_cp(self.gravity)
        self.entities.clear()
        self.visuals.clear()
        self.rigids.clear()
        self.tiles.clear()
        self.lines.clear()
        self.camera.reset(size)
        self.clock = Clock()

    def clear(self) -> None:
        """清空场景内容（保留重力与子步设置）。"""
        self.space = pymunk.Space()
        self.space.gravity = to_cp(self.gravity)
        self.entities.clear()
        self.visuals.clear()
        self.lines.clear()
