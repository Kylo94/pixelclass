"""约束（关节）：把两个物体连起来（spec 03 §6）。

* ``Connect`` / ``connect(a, b)``：**销钉**，保持两物体创建时的距离（刚性杆）；
* ``Spring``：**弹簧-阻尼**，距离被拉回自然长度（默认 = 创建时距离）。

两者都接受**实体**或**裸刚体**，并自动把关节加进对象所属场景的物理空间。
"""

from typing import Any, Optional, Tuple

import pymunk

from ..context import resolve_world
from ..error_help import bilingual
from .body import Body

DEFAULT_STIFFNESS = 100.0
DEFAULT_DAMPING = 10.0


def _body_and_world(obj: Any) -> Tuple[Any, Any]:
    """取出对象里的 pymunk 刚体与它所属的场景。

    用类型判断而不是"有没有某个属性"来猜测（``Body`` 与实体都有 ``body`` 之类的名字）。
    """
    from ..entity import Entity  # 延迟导入：entity 依赖 runtime，模块级导入会成环

    if isinstance(obj, Entity):
        if obj.rigid is None:
            raise TypeError(
                bilingual(
                    f"约束需要带刚体的对象，收到的是没有刚体的 {type(obj).__name__}。"
                    "请在创建时给出尺寸，例如 Character(size=(32, 32))。",
                    f"Constraints need objects with a physics body; {type(obj).__name__} has none. "
                    "Pass a size when creating it, e.g. Character(size=(32, 32)).",
                )
            )
        return obj.rigid.body, obj.world
    if isinstance(obj, Body):
        return obj.body, obj.world
    raise TypeError(
        bilingual(
            f"约束只接受游戏对象或物理层刚体，收到的是 {type(obj).__name__}。",
            f"Constraints accept game objects or physics bodies; got {type(obj).__name__}.",
        )
    )


def _scene_of(world: Any, world_a: Any, world_b: Any) -> Any:
    """关节加到哪个场景：显式 world > a 的场景 > b 的场景 > 当前场景。"""
    return resolve_world(world if world is not None else (world_a or world_b))


class Connect(pymunk.PinJoint):
    """销钉关节：把两个物体连成一根刚性杆（长度 = 创建时的距离）。"""

    def __init__(self, a: Any, b: Any, world: Any = None) -> None:
        body_a, world_a = _body_and_world(a)
        body_b, world_b = _body_and_world(b)
        super().__init__(body_a, body_b)
        _scene_of(world, world_a, world_b).space.add(self)


class Spring(pymunk.DampedSpring):
    """弹簧-阻尼关节：把距离拉回 ``rest_length``（默认 = 创建时的距离）。"""

    def __init__(
        self,
        a: Any,
        b: Any,
        rest_length: Optional[float] = None,
        stiffness: float = DEFAULT_STIFFNESS,
        damping: float = DEFAULT_DAMPING,
        world: Any = None,
    ) -> None:
        body_a, world_a = _body_and_world(a)
        body_b, world_b = _body_and_world(b)
        if rest_length is None:
            rest_length = float((body_b.position - body_a.position).length)
        super().__init__(body_a, body_b, (0, 0), (0, 0), float(rest_length), stiffness, damping)
        _scene_of(world, world_a, world_b).space.add(self)


def connect(a: Any, b: Any, world: Any = None) -> Connect:
    """课堂常用入口：把两个对象连成刚性杆。"""
    return Connect(a, b, world=world)


__all__ = ["Connect", "Spring", "connect"]
