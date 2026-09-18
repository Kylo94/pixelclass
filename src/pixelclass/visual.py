"""视觉组件：绘制策略、变换缓存与动画（spec 04）。

组织结构（与旧实现不同）：**四种绘制来源各自是一个"策略对象"**，
``Sprite`` 只负责"选策略 + 变换缓存 + 把图交给窗口画"。

变换缓存规则（spec 04 §1.3）：旋转 / 缩放 / 翻转 / 着色都是"重活"，
只有在对应标记为真时才重算，算完把标记复位——只改位置时绝不重算图像。
"""

import os
from typing import Any, Dict, List, Optional

import pygame

from .error_help import bilingual

DEFAULT_FRAME_TIME = 1 / 12  # 帧序列默认每帧停留时间（秒）


def _load_image(source: Any) -> pygame.Surface:
    """路径 / Surface → Surface（路径不存在时给中英双语提示）。"""
    if isinstance(source, str):
        if not os.path.isfile(source):
            raise FileNotFoundError(
                bilingual(
                    f"找不到图片文件：{os.path.abspath(source)}（检查路径与当前目录）",
                    f"Image file not found: {os.path.abspath(source)}",
                )
            )
        return pygame.image.load(source).convert_alpha()
    if hasattr(source, "get_rect") and hasattr(source, "get_size"):
        return source
    raise TypeError(
        bilingual(
            f"不认识的贴图来源：{type(source).__name__}",
            f"Unsupported image source: {type(source).__name__}",
        )
    )


# ---------------------------------------------------------------------- 策略
class EasySpriteStrategy:
    """单图：永远画同一张。"""

    def __init__(self, image: Any, sheet: Any = None) -> None:
        self.image = _load_image(image)
        self.frame = 0
        self.frame_count = 1

    def advance(self, dt: float) -> None:
        return

    def set_frame(self, index: int) -> None:
        self.frame = 0


class ListSpriteStrategy:
    """帧序列：按 ``frame`` 索引取图，``dt`` 控制每帧停留时间。"""

    def __init__(self, images: Any, sheet: Any = None) -> None:
        if isinstance(images, dict):  # 容错：误把状态字典交给帧序列
            images = next(iter(images.values()))
        self.frames: List[pygame.Surface] = [_load_image(item) for item in images]
        if not self.frames:
            raise ValueError(bilingual("帧列表是空的", "The frame list is empty"))
        self.frame = 0
        self.dt = DEFAULT_FRAME_TIME
        self._timer = 0.0
        self.frame_count = len(self.frames)

    @property
    def image(self) -> pygame.Surface:
        return self.frames[self.frame % len(self.frames)]

    def advance(self, dt: float) -> None:
        if len(self.frames) <= 1:
            return
        self._timer += max(0.0, float(dt))
        while self._timer >= self.dt:
            self._timer -= self.dt
            self.frame = (self.frame + 1) % len(self.frames)

    def set_frame(self, index: int) -> None:
        self.frame = int(index) % len(self.frames)


class AnimatorStrategy:
    """状态机：``{状态名: [帧…]}``，可设下一状态与首末回调。"""

    def __init__(self, states: Dict[str, Any], sheet: Any = None) -> None:
        if not states:
            raise ValueError(bilingual("状态字典是空的", "The state dictionary is empty"))
        self.states: Dict[str, ListSpriteStrategy] = {
            name: ListSpriteStrategy(frames) for name, frames in states.items()
        }
        self._state = next(iter(self.states))
        self._pending: Optional[str] = None
        self._next_state: Optional[str] = None
        self._condition: Any = None
        self._start_func: Any = None
        self._end_func: Any = None

    # ---------------------------------------------------------------- 状态
    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, name: str) -> None:
        if name not in self.states:
            raise ValueError(
                bilingual(
                    f"没有这个动画状态：{name!r}。可用状态：{sorted(self.states)}",
                    f"Unknown animation state {name!r}; available: {sorted(self.states)}",
                )
            )
        self._pending = name  # 下一帧生效（避免在遍历中改状态）

    @property
    def current(self) -> ListSpriteStrategy:
        return self.states[self._state]

    @property
    def image(self) -> pygame.Surface:
        return self.current.image

    @property
    def frame(self) -> int:
        return self.current.frame

    @frame.setter
    def frame(self, index: int) -> None:
        self.current.set_frame(index)

    @property
    def frame_count(self) -> int:
        return self.current.frame_count

    @property
    def dt(self) -> float:
        return self.current.dt

    @dt.setter
    def dt(self, value: float) -> None:
        for strategy in self.states.values():
            strategy.dt = float(value)

    def set_next_state(self, name: str, condition: Any = None) -> None:
        self._next_state = name
        self._condition = condition

    def set_start_func(self, func: Any) -> None:
        self._start_func = func

    def set_end_func(self, func: Any) -> None:
        self._end_func = func

    def advance(self, dt: float) -> None:
        if self._pending is not None and self._pending != self._state:
            self._switch(self._pending)
        self._pending = None

        before = self.current.frame
        self.current.advance(dt)
        looped = self.current.frame < before  # 回环说明播完一轮

        if self._next_state is None:
            return
        ready = self._condition(self) if callable(self._condition) else looped
        if ready and self._next_state != self._state:
            self._switch(self._next_state)

    def _switch(self, name: str) -> None:
        if name not in self.states:
            raise ValueError(
                bilingual(
                    f"要切换到的动画状态不存在：{name!r}。可用状态：{sorted(self.states)}",
                    f"Cannot switch to unknown state {name!r}; available: {sorted(self.states)}",
                )
            )
        if callable(self._end_func):
            self._end_func(self)
        self._state = name
        self.current.frame = 0
        if callable(self._start_func):
            self._start_func(self)


class TiledMapStrategy:
    """整图：把瓦片地图一次性烘焙成一张大图。"""

    def __init__(self, tiledmap: Any, sheet: Any = None) -> None:
        surface = pygame.Surface((int(tiledmap.width), int(tiledmap.height)), pygame.SRCALPHA)
        tiledmap.render(surface)
        self.image = surface
        self.frame = 0
        self.frame_count = 1

    def advance(self, dt: float) -> None:
        return

    def set_frame(self, index: int) -> None:
        self.frame = 0


class SpriteSheet:
    """图集：把一张大图按网格切成若干帧。"""

    def __init__(self, image: Any, frame_width: int, frame_height: int) -> None:
        self.surface = _load_image(image)
        self.frame_width = int(frame_width)
        self.frame_height = int(frame_height)

    def frames(self) -> List[pygame.Surface]:
        columns = self.surface.get_width() // self.frame_width
        rows = self.surface.get_height() // self.frame_height
        images = []
        for row in range(rows):
            for column in range(columns):
                rect = pygame.Rect(
                    column * self.frame_width, row * self.frame_height, self.frame_width, self.frame_height
                )
                images.append(self.surface.subsurface(rect).copy())
        return images

    def __repr__(self) -> str:  # pragma: no cover - 仅调试用
        return f"<SpriteSheet {self.surface.get_size()} 每帧 {self.frame_width}×{self.frame_height}>"


# ---------------------------------------------------------------------- 视觉组件
class Sprite:
    """一张（或一组）贴图 + 绘制状态 + 变换缓存。"""

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
        self.scaled = False
        self.rotated = False
        self.fliped = False
        self.modified = False
        self.strategy = self._make_strategy(source)
        self.rect = self._base_image().get_rect()
        self._display: Optional[pygame.Surface] = None
        self._mask: Optional[Any] = None
        self.world.visuals.add(self)

    # ---------------------------------------------------------------- 建立
    def _make_strategy(self, source: Any) -> Any:
        if source is None:
            raise ValueError(bilingual("贴图来源不能为空", "The image source cannot be None"))
        if isinstance(source, SpriteSheet):
            return ListSpriteStrategy(source.frames())
        if isinstance(source, dict):
            return AnimatorStrategy(source)
        if isinstance(source, (list, tuple)):
            return ListSpriteStrategy(source)
        if hasattr(source, "render"):  # 瓦片地图（整图策略）
            return TiledMapStrategy(source)
        return EasySpriteStrategy(source)

    def _base_image(self) -> pygame.Surface:
        return self.strategy.image

    # ---------------------------------------------------------------- 动画
    @property
    def sprite_strategy(self) -> Any:
        """兼容名（旧讲义里用它读动画策略）。"""
        return self.strategy

    @property
    def frame(self) -> int:
        return int(getattr(self.strategy, "frame", 0))

    @frame.setter
    def frame(self, index: int) -> None:
        setter = getattr(self.strategy, "set_frame", None)
        if setter is not None:
            setter(index)

    @property
    def state(self) -> str:
        return str(getattr(self.strategy, "state", ""))

    @state.setter
    def state(self, name: str) -> None:
        setattr(self.strategy, "state", name)

    @property
    def dt(self) -> float:
        return float(getattr(self.strategy, "dt", DEFAULT_FRAME_TIME))

    @dt.setter
    def dt(self, value: float) -> None:
        setattr(self.strategy, "dt", float(value))

    def set_next_state(self, name: str, condition: Any = None) -> None:
        setter = getattr(self.strategy, "set_next_state", None)
        if setter is None:
            raise TypeError(bilingual("这个贴图不是状态机，无法设置下一状态", "Not a state-machine sprite"))
        setter(name, condition)

    def set_start_func(self, func: Any) -> None:
        setter = getattr(self.strategy, "set_start_func", None)
        if setter is not None:
            setter(func)

    def set_end_func(self, func: Any) -> None:
        setter = getattr(self.strategy, "set_end_func", None)
        if setter is not None:
            setter(func)

    # ---------------------------------------------------------------- 尺寸与状态
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

    # ---------------------------------------------------------------- 每帧
    def _parent_pos(self) -> Any:
        if self.parent is None:
            return (0, 0)
        return getattr(self.parent, "pos", (0, 0))

    def _parent_rot(self) -> float:
        return float(getattr(self.parent, "rot", 0.0)) if self.parent is not None else 0.0

    def _parent_scl(self) -> Any:
        return getattr(self.parent, "scl", (1, 1)) if self.parent is not None else (1, 1)

    def advance(self, dt: float) -> None:
        self.strategy.advance(dt)

    def _has_pending_transform(self) -> bool:
        scale = self._parent_scl()
        return bool(
            self.scaled
            or self.rotated
            or self.fliped
            or self.modified
            or (float(scale[0]), float(scale[1])) != (1.0, 1.0)
        )

    def _transform(self) -> pygame.Surface:
        """按需重算变换后的图像（只在标记为真时重算）。"""
        if self._display is not None and not self._has_pending_transform():
            return self._display

        image = self._base_image()
        if self.fliped and (self.is_flip_h or self.is_flip_v):
            image = pygame.transform.flip(image, self.is_flip_h, self.is_flip_v)
        scale = self._parent_scl()
        if self.scaled or (float(scale[0]), float(scale[1])) != (1.0, 1.0):
            width = max(1, int(image.get_width() * float(scale[0])))
            height = max(1, int(image.get_height() * float(scale[1])))
            image = pygame.transform.scale(image, (width, height))
        if self.rotated:
            image = pygame.transform.rotate(image, self._parent_rot())
        if self.modified and (self.red, self.green, self.blue, self.alpha) != (255, 255, 255, 255):
            tinted = image.copy()
            tinted.fill((self.red, self.green, self.blue, self.alpha), special_flags=pygame.BLEND_RGBA_MULT)
            image = tinted

        self._display = image
        self._mask = None
        self.scaled = self.rotated = self.fliped = self.modified = False
        return image

    def update(self) -> None:
        """每帧：推进动画，再同步显示矩形（只改位置时**不重算图像**）。"""
        self.advance(self.world.clock.dt)
        image = self._transform()
        self.rect = image.get_rect()
        pos = self._parent_pos()
        self.rect.center = (int(pos[0]), int(pos[1]))

    def set_base_image(self, image: pygame.Surface) -> None:
        """替换基础图（单图策略），并让变换缓存失效。"""
        self.strategy = EasySpriteStrategy(image)
        self._display = None
        self._mask = None
        self.update()

    def display_image(self) -> pygame.Surface:
        """当前该画的图（含变换）。"""
        return self._transform()

    def draw(self, surface: pygame.Surface, camera: Any) -> None:
        """由窗口调用：按相机偏移把图贴上去。"""
        if not self.visible:
            return
        image = self.display_image()
        zoom = float(getattr(camera, "zoom", 1.0) or 1.0)
        if abs(zoom - 1.0) > 1e-6:
            size = (max(1, int(image.get_width() * zoom)), max(1, int(image.get_height() * zoom)))
            transform = (
                pygame.transform.smoothscale
                if getattr(camera, "smooth_zoom", False)
                else pygame.transform.scale
            )
            image = transform(image, size)
        rect = image.get_rect()
        center = camera.to_screen(self._parent_pos())
        rect.center = (int(center[0]), int(center[1]))
        surface.blit(image, rect)

    def world_rect(self) -> pygame.Rect:
        """按宿主**当前**位置算出的显示矩形。

        与每帧缓存的 ``rect`` 的区别：移动对象之后立刻做点查询/碰撞也能拿到正确结果，
        不必等下一帧（学生会这样写：goto 之后马上判断碰到了没）。
        """
        rect = self.display_image().get_rect()
        pos = self._parent_pos()
        rect.center = (int(pos[0]), int(pos[1]))
        return rect

    def mask(self) -> Any:
        """像素掩码（碰撞判定用）：取自**当前显示图**，变换后自动失效重建。"""
        if self._mask is None:
            self._mask = pygame.mask.from_surface(self.display_image())
        return self._mask

    def kill(self) -> None:
        self.world.visuals.remove(self)
        self.parent = None

    def __repr__(self) -> str:  # pragma: no cover - 仅调试用
        return f"<Sprite {self.width}×{self.height} at {self.rect.center}>"
