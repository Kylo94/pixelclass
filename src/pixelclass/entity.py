"""实体与课堂预设（spec 02）。

组合而非深继承：一个实体持有三个**可选**组件槽位——

    visual（显示） / rigid（单体刚体） / tiles（瓦片刚体组）

槽位为 ``None`` 是**合法状态**（"半个对象"）。此时对应的接口给一次性中英双语提示并返回
中性值，**绝不抛 AttributeError**（spec 02 §3）——这是初学者最容易卡住的地方。
"""

import math
import warnings
from typing import Any, List, Optional

import pygame

from .context import resolve_world
from .error_help import bilingual
from .input import get_mouse_pos
from .runtime import update
from .physics.body import BODY_TYPES, Body
from .physics.tiles import TiledMapBodies
from .vec import vec
from .visual import Sprite

EPS = 1e-9


def _rigid_property(name: str):
    def getter(self):
        if self._no_body(name):
            return None
        return None if self.rigid is None else getattr(self.rigid, name)

    def setter(self, value):
        if self._no_body(name):
            return
        if self.rigid is not None:
            setattr(self.rigid, name, value)

    return property(getter, setter)


class Entity:
    """游戏对象基类（历史讲义里的 ``GameObject`` / ``NewGameObject`` 都指向它）。"""

    def __init__(
        self,
        imgs: Any = None,
        size: Any = None,
        body_type: Any = "KINEMATIC",
        sensor: bool = False,
        world: Any = None,
    ) -> None:
        self.world = resolve_world(world)
        self.name = ""
        self.properties: dict = {}
        self.tmx_object: Any = None
        self.alive = True

        # 显示缓存（坐标/旋转/缩放）与朝向
        self._pos = vec(0, 0)
        self._rot = 0.0
        self._scl = vec(1, 1)
        self._direction = vec(1, 0)

        # 三个组件槽位
        self.visual: Optional[Sprite] = None
        self.rigid: Optional[Body] = None
        self.tiles: Optional[TiledMapBodies] = None

        # 缺组件时只提示一次
        self._no_body_warned = False
        self._no_visual_warned = False

        self.sounds: List[Any] = []
        self.volume = 1.0
        self._just_released = False

        if imgs is not None:
            self.visual = Sprite(imgs, self.world)
            self.visual.set_parent(self)
        if size is not None:
            self._build_physics(size, body_type, sensor)

        self.world.entities.add(self)

    # ------------------------------------------------------------------ 建立刚体
    def _build_physics(self, size: Any, body_type: Any, sensor: bool) -> None:
        if isinstance(size, bool):
            raise TypeError(bilingual(f"size 不能是布尔值：{size!r}", f"size cannot be a bool: {size!r}"))

        if isinstance(size, int):
            self.rigid = Body(body_type, "CIRCLE", size=size, sensor=sensor, world=self.world)
        elif (
            isinstance(size, (tuple, list))
            and len(size) == 2
            and all(isinstance(v, (int, float)) for v in size)
        ):
            self.rigid = Body(body_type, "BOX", size=size, sensor=sensor, world=self.world)
        elif isinstance(size, list) and size and isinstance(size[0], (list, tuple)):
            self.rigid = Body(body_type, "POLY", size=size, sensor=sensor, world=self.world)
        elif isinstance(size, list):
            self.tiles = TiledMapBodies(body_type, size, sensor=sensor, world=self.world)
        else:
            raise TypeError(
                bilingual(
                    f"size 参数看不懂：{size!r}。可以给整数（半径）、(宽, 高)、"
                    "点集 [[x, y], …]，或地图对象列表。",
                    f"Unsupported size: {size!r}. Use an int (radius), (width, height), "
                    "a list of points, or a list of map objects.",
                )
            )

        if self.rigid is not None:
            self.rigid.set_parent(self)
        if self.tiles is not None:
            self.tiles.set_parent(self)

    # ------------------------------------------------------------------ 组件访问
    @property
    def sprite(self) -> Optional[Sprite]:
        """显示组件（``visual`` 的兼容别名）。"""
        return self.visual

    @property
    def body(self) -> Optional[Body]:
        """单体刚体（``rigid`` 的兼容别名）。"""
        return self.rigid

    @property
    def tiledmap_bodies(self) -> Optional[TiledMapBodies]:
        """瓦片刚体组（``tiles`` 的兼容别名）。"""
        return self.tiles

    # ------------------------------------------------------------------ 缺失组件提示
    def _no_body(self, action: str) -> bool:
        """没有刚体：提示一次并返回 True（调用方给中性值）。"""
        if self.rigid is not None or self.tiles is not None:
            return False
        if not self._no_body_warned:
            self._no_body_warned = True
            warnings.warn(
                bilingual(
                    f"{action} 没有生效：这个对象没有刚体。创建时给 size 才会有物理"
                    f"（例如 Character(图片, size=(32, 32))）。",
                    f"{action} had no effect: this object has no physics body. "
                    f"Pass size when creating it, e.g. Character(image, size=(32, 32)).",
                ),
                RuntimeWarning,
                stacklevel=3,
            )
        return True

    def _no_visual(self, action: str) -> bool:
        """没有贴图：提示一次并返回 True。"""
        if self.visual is not None:
            return False
        if not self._no_visual_warned:
            self._no_visual_warned = True
            warnings.warn(
                bilingual(
                    f"{action} 没有生效：这个对象没有贴图。创建时传入图片才会有显示层"
                    f"（例如 Character('hero.png', size=(32, 32))）。",
                    f"{action} had no effect: this object has no sprite/image. "
                    f"Pass an image when creating it, e.g. Character('hero.png', size=(32, 32)).",
                ),
                RuntimeWarning,
                stacklevel=3,
            )
        return True

    # ------------------------------------------------------------------ 位置 / 角度
    @property
    def pos(self) -> Any:
        return self._pos

    @pos.setter
    def pos(self, value: Any) -> None:
        self._write_pos(value)
        self._stop()  # 瞬移：清零速度（spec 01 §5）

    def _write_pos(self, value: Any) -> None:
        self._pos = vec(value)
        if self.rigid is not None:
            self.rigid.set_pos(self._pos)
        if self.tiles is not None:
            self.tiles.set_pos(self._pos)

    def _stop(self) -> None:
        if self.rigid is not None:
            self.rigid.velocity = (0, 0)

    def sync_pos(self, value: Any) -> None:
        """物理层回写：只改显示缓存（spec 01 §5）。"""
        self._pos = vec(value)

    @property
    def x(self) -> float:
        return float(self._pos[0])

    @x.setter
    def x(self, value: float) -> None:
        self.pos = vec(float(value), self._pos[1])

    @property
    def y(self) -> float:
        return float(self._pos[1])

    @y.setter
    def y(self, value: float) -> None:
        self.pos = vec(self._pos[0], float(value))

    def shift_by(self, delta: Any) -> None:
        """增量位移：同步刚体但**不清速度**（重力继续生效）。"""
        self._write_pos(self._pos + vec(delta))

    def goto(self, x: Any, *y: Any) -> None:
        """放到指定坐标（等价于写 ``pos``），并清零速度。支持 ``goto(x, y)`` 与 ``goto((x, y))``。"""
        self.pos = vec(x, y[0]) if y else vec(x)

    @property
    def rot(self) -> float:
        return float(self._rot)

    @rot.setter
    def rot(self, value: float) -> None:
        self._write_rot(value)
        if self.rigid is not None:
            self.rigid.set_rot(value)
        if self.tiles is not None:
            self.tiles.set_rot(value)

    def _write_rot(self, value: float) -> None:
        value = float(value)
        if value == self._rot:
            return  # 角度没变：不标记重绘（物理每帧回写时尤其重要，见 spec 04 §1.3）
        self._rot = value
        if self.visual is not None:
            self.visual.rotated = True

    def sync_rot(self, value: float) -> None:
        """物理层回写角度：只改显示缓存。"""
        self._write_rot(value)

    @property
    def angle(self) -> float:
        """朝向角度（度，float，由 ``dir`` 算出）——与 ``rot``（贴图/刚体旋转角）是两回事。"""
        return math.degrees(math.atan2(self._direction[0], self._direction[1]))

    @property
    def dir(self) -> Any:
        return self._direction

    @dir.setter
    def dir(self, value: Any) -> None:
        self._direction = vec(value)

    def set_angle(self, degrees: float) -> None:
        """设置朝向（同时更新 ``dir``）。"""
        radians = math.radians(float(degrees))
        self._direction = vec(math.sin(radians), math.cos(radians))

    def face_to(self, x: Any, *y: Any) -> None:
        """转向某个坐标（或方向向量）。"""
        target = vec(x, y[0]) if y else vec(x)
        delta = target - self._pos
        if delta.length() < EPS:
            return
        self._direction = delta.normalize()
        self.rot = -delta.angle_to(vec(1, 0))

    def forward(self, distance: float) -> None:
        """沿朝向走 ``distance`` 像素（不清速度）。"""
        self._walk(self._direction, distance)

    def backward(self, distance: float) -> None:
        """沿朝向反方向走 ``distance`` 像素（不清速度）。"""
        self._walk(-self._direction, distance)

    def _walk(self, direction: Any, distance: float) -> None:
        remaining = float(distance)
        step_limit = max(float(getattr(self.world, "speed_limit", 1) or 1), EPS)
        sign_of = 1.0 if remaining >= 0 else -1.0
        while abs(remaining) > EPS:
            chunk = min(step_limit, abs(remaining))
            self.shift_by(direction * chunk * sign_of)
            remaining -= chunk * sign_of
            if getattr(self.world, "auto_update", False):
                update(self.world)  # 教学演示模式：边移动边推进画面

    def slide_to(self, target: Any, step: float = 1.0) -> None:
        """朝目标滑行；距离小于步长时直接落点。"""
        goal = vec(target)
        delta = goal - self._pos
        if delta.length() < step:
            self.pos = goal
        else:
            self.shift_by(delta.normalize() * step)

    @property
    def scl(self) -> Any:
        return self._scl

    @scl.setter
    def scl(self, value: Any) -> None:
        if isinstance(value, (tuple, list)):
            self._scl = vec(value)
        else:
            self._scl = vec(float(value))

    def scale(self, scalex: float, scaley: Optional[float] = None) -> None:
        """缩放贴图与刚体（圆形只能等比）。"""
        if self.visual is not None:
            self.visual.scaled = True
        self._scl = vec(scalex) if scaley is None else vec(scalex, scaley)
        if scaley is None:
            self.body_scale(scalex, scalex)
        else:
            self.body_scale(scalex, scaley)

    def body_scale(self, scalex: float, scaley: Optional[float] = None) -> None:
        """只缩放刚体几何（圆形忽略不同方向的拉伸）。"""
        if self.rigid is None:
            if self.tiles is not None:
                self.tiles.set_scale(scalex, scaley)
            return
        scaley = scalex if scaley is None else scaley
        if getattr(self.rigid, "kind", "") == "CIRCLE":
            self.rigid.shape.unsafe_set_radius(int(self.rigid.shape.radius * scalex))
        else:
            vertices = self.rigid.shape.get_vertices()
            points = [(v[0] * scalex, v[1] * scaley) for v in vertices]
            self.rigid.shape.unsafe_set_vertices(points)
        self.world.space.reindex_shapes_for_body(self.rigid.body)

    # ------------------------------------------------------------------ 显示层代理
    @property
    def visible(self) -> bool:
        if self._no_visual("visible"):
            return False
        assert self.visual is not None
        return bool(self.visual.visible)

    @visible.setter
    def visible(self, value: Any) -> None:
        if self._no_visual("visible"):
            return
        assert self.visual is not None
        self.visual.visible = bool(value)

    def show(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def _color_channel(self, name: str) -> Optional[int]:
        if self._no_visual(name):
            return None
        assert self.visual is not None
        return int(getattr(self.visual, name))

    def _set_color_channel(self, name: str, value: int) -> None:
        if self._no_visual(name):
            return
        assert self.visual is not None
        setattr(self.visual, name, int(value))
        self.visual.modified = True

    @property
    def red(self) -> Optional[int]:
        return self._color_channel("red")

    @red.setter
    def red(self, value: int) -> None:
        self._set_color_channel("red", value)

    @property
    def green(self) -> Optional[int]:
        return self._color_channel("green")

    @green.setter
    def green(self, value: int) -> None:
        self._set_color_channel("green", value)

    @property
    def blue(self) -> Optional[int]:
        return self._color_channel("blue")

    @blue.setter
    def blue(self, value: int) -> None:
        self._set_color_channel("blue", value)

    @property
    def alpha(self) -> Optional[int]:
        return self._color_channel("alpha")

    @alpha.setter
    def alpha(self, value: int) -> None:
        self._set_color_channel("alpha", value)

    @property
    def color(self) -> Any:
        if self._no_visual("color"):
            return None
        assert self.visual is not None
        return self.visual.color

    @color.setter
    def color(self, value: Any) -> None:
        if self._no_visual("color"):
            return
        assert self.visual is not None
        self.visual.color = value

    @property
    def width(self) -> int:
        if self._no_visual("width"):
            return 0
        assert self.visual is not None
        return int(self.visual.width)

    @property
    def height(self) -> int:
        if self._no_visual("height"):
            return 0
        assert self.visual is not None
        return int(self.visual.height)

    @property
    def frame(self) -> int:
        if self._no_visual("frame"):
            return 0
        assert self.visual is not None
        return int(self.visual.frame)

    @frame.setter
    def frame(self, index: int) -> None:
        if self._no_visual("frame"):
            return
        assert self.visual is not None
        self.visual.frame = index

    @property
    def state(self) -> str:
        if self._no_visual("state"):
            return ""
        assert self.visual is not None
        return str(self.visual.state)

    @state.setter
    def state(self, name: str) -> None:
        if self._no_visual("state"):
            return
        assert self.visual is not None
        self.visual.state = name  # 写状态下一帧生效（spec 04 §2.2）

    @property
    def dt(self) -> float:
        if self._no_visual("dt"):
            return 0.0
        assert self.visual is not None
        return float(self.visual.dt)

    @dt.setter
    def dt(self, value: float) -> None:
        if self._no_visual("dt"):
            return
        assert self.visual is not None
        self.visual.dt = value

    def set_next_state(self, name: str, condition: Any = None) -> None:
        if self._no_visual("set_next_state"):
            return
        assert self.visual is not None
        self.visual.set_next_state(name, condition)

    def set_start_func(self, func: Any) -> None:
        if self._no_visual("set_start_func"):
            return
        assert self.visual is not None
        self.visual.set_start_func(func)

    def set_end_func(self, func: Any) -> None:
        if self._no_visual("set_end_func"):
            return
        assert self.visual is not None
        self.visual.set_end_func(func)

    def flipx(self, value: bool = True) -> None:
        if self._no_visual("flipx"):
            return
        assert self.visual is not None
        self.visual.fliped = True
        self.visual.is_flip_h = bool(value)

    def flipy(self, value: bool = True) -> None:
        if self._no_visual("flipy"):
            return
        assert self.visual is not None
        self.visual.fliped = True
        self.visual.is_flip_v = bool(value)

    @property
    def layer(self) -> Optional[int]:
        if self._no_visual("layer"):
            return None
        assert self.visual is not None
        return int(self.visual.layer)

    @layer.setter
    def layer(self, value: int) -> None:
        if self._no_visual("layer"):
            return
        assert self.visual is not None
        self.visual.layer = int(value)

    def move_to_front(self) -> None:
        """排到最前（本来就在最前时保持不变）。"""
        if self._no_visual("move_to_front"):
            return
        assert self.visual is not None
        others = [item.layer for item in self.world.visuals if item is not self.visual]
        if not others or self.visual.layer > max(others):
            return
        self.visual.layer = max(others) + 1

    def move_to_back(self) -> None:
        """排到最后（本来就在最后时保持不变）。"""
        if self._no_visual("move_to_back"):
            return
        assert self.visual is not None
        others = [item.layer for item in self.world.visuals if item is not self.visual]
        if not others or self.visual.layer < min(others):
            return
        self.visual.layer = min(others) - 1

    # ------------------------------------------------------------------ 物理层代理
    @property
    def velocity(self) -> Any:
        if self._no_body("velocity"):
            return None
        if self.rigid is not None:
            return self.rigid.velocity
        return None

    @velocity.setter
    def velocity(self, value: Any) -> None:
        if self._no_body("velocity"):
            return
        if self.rigid is not None:
            self.rigid.velocity = value

    @property
    def angular_velocity(self) -> Optional[float]:
        if self._no_body("angular_velocity"):
            return None
        return None if self.rigid is None else self.rigid.angular_velocity

    @angular_velocity.setter
    def angular_velocity(self, value: float) -> None:
        if self._no_body("angular_velocity"):
            return
        if self.rigid is not None:
            self.rigid.angular_velocity = value

    mass = _rigid_property("mass")
    elasticity = _rigid_property("elasticity")
    friction = _rigid_property("friction")

    def apply_force(self, x: Any, *y: Any) -> None:
        """施加冲量（局部点）。"""
        if self._no_body("apply_force"):
            return
        if self.rigid is None:
            return
        point = (float(x), float(y[0])) if y else (float(x[0]), float(x[1]))
        self.rigid.body.apply_impulse_at_local_point(point)

    # ------------------------------------------------------------------ 鼠标交互
    def get_mouse_upon(self) -> bool:
        """鼠标是否悬停在这个对象上（要求对象可见；无贴图对象按刚体判定）。"""
        from .input import get_mouse_pos

        if self.visual is not None and not self.visual.visible:
            return False
        if not self.alive:
            return False
        return bool(self.collide(get_mouse_pos(self.world)))

    def get_mouse_clicked(self) -> bool:
        """鼠标是否**在这个对象上**按下（按住期间一直为真）。"""
        from .input import get_mouse_clicked

        return bool(get_mouse_clicked()) and self.get_mouse_upon()

    # ------------------------------------------------------------------ 音效
    def play_snd(self, path: Any, loop: bool = False) -> Any:
        """播放一个音效（无音频设备时安全无操作）。"""
        from .audio import load_sound

        sound = load_sound(path)
        if sound is None:
            return None
        sound.set_volume(float(self.volume))
        sound.play(loops=-1 if loop else 0)
        self.sounds.append(sound)
        return sound

    def set_volume(self, value: float) -> float:
        """设置该对象音效的音量（0~1）。"""
        self.volume = max(0.0, min(1.0, float(value)))
        for sound in list(self.sounds):
            try:
                sound.set_volume(self.volume)
            except (AttributeError, pygame.error):  # 设备已失效
                pass
        return self.volume

    # ------------------------------------------------------------------ 碰撞
    def collide(self, other: Any) -> bool:
        """点查询（传坐标）或对象碰撞（传另一个实体）。"""
        if isinstance(other, (tuple, list)) or isinstance(other, pygame.math.Vector2):
            return self._collide_point(other)
        return self._collide_entity(other)

    def _collide_point(self, point: Any) -> bool:
        if self.rigid is not None:
            return self.rigid.point_query(point)
        if self.tiles is not None:
            return self.tiles.point_query(point)
        return self._point_in_mask(point)

    def _point_in_mask(self, point: Any) -> bool:
        if self.visual is None or not self.visual.visible:
            return False
        rect = self.visual.world_rect()
        local_x = int(round(float(point[0]) - rect.left))
        local_y = int(round(rect.bottom - float(point[1])))
        if not (0 <= local_x < rect.width and 0 <= local_y < rect.height):
            return False
        return bool(self.visual.mask().get_at((local_x, local_y)))

    def _collide_entity(self, other: Any) -> bool:
        if not getattr(other, "alive", True):
            return False
        if self.rigid is not None and getattr(other, "rigid", None) is not None:
            return self.rigid.collide(other.rigid)
        if self.tiles is not None and getattr(other, "rigid", None) is not None:
            return self.tiles.collide(other.rigid)
        if self.rigid is not None and getattr(other, "tiles", None) is not None:
            return other.tiles.collide(self.rigid)
        if self.tiles is not None and getattr(other, "tiles", None) is not None:
            return self.tiles.collide(other.tiles)
        return self._mask_overlap(other)

    def _mask_overlap(self, other: Any) -> bool:
        if self.visual is None or other.visual is None:
            return False
        if not self.visual.visible or not other.visual.visible:
            return False
        mine = self.visual.world_rect()
        theirs = other.visual.world_rect()
        offset = (theirs.left - mine.left, mine.bottom - theirs.bottom)
        return self.visual.mask().overlap(other.visual.mask(), offset) is not None

    def separate(self, other: Any) -> None:
        """把两个重叠的对象沿"中心连线"方向推开（完全重合时不动，保证确定性）。"""
        if not self._collide_entity(other):
            return
        delta = vec(getattr(other, "pos", (0, 0))) - self._pos
        if delta.length() < EPS:
            return
        direction = delta.normalize()
        depth = self._overlap_depth(other, direction)
        if depth <= 0:
            return
        if self._movable():
            self.shift_by(-direction * depth)
        elif getattr(other, "_movable", lambda: False)():
            other.shift_by(direction * depth)

    def _movable(self) -> bool:
        return self.rigid is not None and self.rigid.body_type == BODY_TYPES["DYNAMIC"]

    def _overlap_depth(self, other: Any, direction: Any) -> float:
        mine = self._bounds_radius(direction)
        theirs = other._bounds_radius(direction)
        distance = abs((vec(other.pos) - self._pos).dot(direction))
        return mine + theirs - distance

    def _bounds_radius(self, direction: Any) -> float:
        if self.visual is not None:
            half_w, half_h = self.visual.width / 2, self.visual.height / 2
        elif self.rigid is not None:
            from .physics.geometry import bounds_size

            width, height = bounds_size(self.rigid.shape)
            half_w, half_h = width / 2, height / 2
        else:
            half_w = half_h = 0.0
        return abs(float(direction[0])) * half_w + abs(float(direction[1])) * half_h

    # ------------------------------------------------------------------ 生命周期
    def _update(self) -> None:
        """内部每帧调用（**不要覆盖**）：只做框架自己的状态维护。

        贴图的每帧推进由场景的绘制集合统一负责（``scene.visuals``），
        实体这里**不再**重复调用，否则动画会按两倍速度播放。
        """
        self._just_released = False

    def update(self) -> None:
        """留给使用者覆盖的每帧钩子（默认什么都不做）。"""

    def kill(self) -> None:
        """销毁：组件销毁、槽位清空、标记不再存活，最后回调 :meth:`_on_kill`。"""
        for sound in list(self.sounds):
            try:
                sound.stop()
            except (AttributeError, pygame.error):  # 设备已失效
                pass
        self.sounds.clear()
        if self.visual is not None:
            self.visual.kill()
        if self.rigid is not None:
            self.rigid.kill()
        if self.tiles is not None:
            self.tiles.kill()
        self.visual = None
        self.rigid = None
        self.tiles = None
        self.alive = False
        self.world.entities.remove(self)
        self._on_kill()

    def _on_kill(self) -> None:
        """销毁后的清理钩子（子类覆盖它，而不是覆盖 ``kill()``）。"""

    # ------------------------------------------------------------------ 场景
    def set_world(self, world: Any) -> None:
        """把对象搬到另一个场景（教学演示多场景时用）。"""
        self.world.entities.remove(self)
        self.world = resolve_world(world)
        self.world.entities.add(self)

    def __repr__(self) -> str:  # pragma: no cover - 仅调试用
        return f"<{type(self).__name__} at ({self._pos[0]:.0f}, {self._pos[1]:.0f})>"


class Character(Entity):
    """会受重力、会被推、会挡住别人的角色。"""

    def __init__(self, imgs: Any = None, size: Any = None, world: Any = None) -> None:
        Entity.__init__(self, imgs, size, body_type="DYNAMIC", sensor=False, world=world)


class Wall(Entity):
    """不动的墙 / 地面。"""

    def __init__(self, imgs: Any = None, size: Any = None, world: Any = None) -> None:
        Entity.__init__(self, imgs, size, body_type="STATIC", sensor=False, world=world)


class Sensor(Entity):
    """穿透型触发器：自己不动也不被推，但能检测到"谁进来了"。"""

    def __init__(self, imgs: Any = None, size: Any = None, world: Any = None) -> None:
        Entity.__init__(self, imgs, size, body_type="KINEMATIC", sensor=True, world=world)


class Mouse(Entity):
    """每帧跟随鼠标位置。"""

    def __init__(self, imgs: Any = None, world: Any = None) -> None:
        Entity.__init__(self, imgs, None, body_type="KINEMATIC", sensor=False, world=world)

    def _update(self) -> None:
        Entity._update(self)
        self.goto(get_mouse_pos(self.world))


# 历史讲义里的基类名（spec 02 §8）
GameObject = Entity
NewGameObject = Entity

__all__ = ["Entity", "GameObject", "NewGameObject", "Character", "Wall", "Sensor", "Mouse"]
