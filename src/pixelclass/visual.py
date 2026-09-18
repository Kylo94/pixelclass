"""视觉组件（spec 04，M3 先做"够用"的部分）。

本阶段提供：从路径 / Surface / 帧列表 / 状态字典建立贴图、着色与透明度、可见性、
翻转、图层、**用于碰撞判定的 mask**，以及"只改位置不重算图像"的变换缓存标记。
整套绘制与动画策略（帧序列推进、状态机）在视觉里程碑补齐。
"""

import os
from typing import Any, Dict, List, Optional

import pygame


class Sprite:
    """一张（或一组）贴图 + 绘制状态。"""

    def __init__(self, source: Any, world: Any = None) -> None:
        from .context import resolve_world  # 延迟导入，避免导入环

        self.world = resolve_world(world)
        self.parent: Any = None
        self.layer = 0
        self.visible = True
        self.red = 255
        self.green = 255
        self.blue = 255
        self.alpha = 255
        self.is_flip_h = False
        self.is_flip_v = False
        # 重绘标记（spec 04 §1.3）：只有为真时才重算变换后的图像
        self.scaled = False
        self.rotated = False
        self.fliped = False
        self.modified = False

        self.frames: List[Any] = []
        self.states: Dict[str, Any] = {}
        self.image = self._load_source(source)
        self.rect = self.image.get_rect()
        self._mask: Optional[Any] = None
        self.world.visuals.add(self)

    # ------------------------------------------------------------------ 建立
    def _load_source(self, source: Any) -> Any:
        if source is None:
            raise ValueError("贴图来源不能为空：请给图片路径、Surface、帧列表或状态字典")
        if isinstance(source, dict):
            self.states = {name: list(frames) for name, frames in source.items()}
            first = next(iter(self.states.values()))
            self.frames = list(first)
            return self._load_source(self.frames[0])
        if isinstance(source, (list, tuple)):
            self.frames = list(source)
            return self._load_source(self.frames[0])
        if isinstance(source, str):
            path = source
            if not os.path.isfile(path):
                raise FileNotFoundError(
                    f"找不到图片文件：{os.path.abspath(path)}"
                    "\nImage file not found: check the path (and whether you are in the right folder)."
                )
            return pygame.image.load(path).convert_alpha()
        if hasattr(source, "get_rect"):  # pygame.Surface
            return source.convert_alpha()
        if hasattr(source, "render"):  # 瓦片地图（整图策略）
            surface = pygame.Surface((int(getattr(source, "width", 1)), int(getattr(source, "height", 1))))
            source.render(surface)
            return surface
        raise TypeError(f"不认识的贴图来源：{type(source).__name__}")

    # ------------------------------------------------------------------ 尺寸与状态
    @property
    def width(self) -> int:
        return int(self.rect.width)

    @property
    def height(self) -> int:
        return int(self.rect.height)

    @property
    def color(self) -> Any:
        return (self.red, self.green, self.blue, self.alpha)

    @color.setter
    def color(self, value: Any) -> None:
        self.red, self.green, self.blue, self.alpha = (
            int(value[0]),
            int(value[1]),
            int(value[2]),
            int(value[3]),
        )
        self.modified = True

    def set_parent(self, parent: Any) -> None:
        self.parent = parent
        self.update()

    # ------------------------------------------------------------------ 位置与变换
    def _parent_pos(self) -> Any:
        if self.parent is None:
            return (0, 0)
        return getattr(self.parent, "pos", (0, 0))

    def update(self) -> None:
        """同步位置与变换缓存（只改位置时**不重算图像**）。"""
        pos = self._parent_pos()
        self.rect.center = (int(pos[0]), int(pos[1]))
        self.mask()  # 位置变了，mask 的缓存要跟着更新

    def mask(self) -> Any:
        """像素掩码（碰撞判定用），按需生成并缓存。"""
        if self._mask is None:
            self._mask = pygame.mask.from_surface(self.image)
        return self._mask

    def kill(self) -> None:
        self.world.visuals.remove(self)
        self.parent = None

    def __repr__(self) -> str:  # pragma: no cover - 仅调试用
        return f"<Sprite {self.width}×{self.height} at {self.rect.center}>"
