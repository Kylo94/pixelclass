"""当前场景（供不传 ``world`` 的接口使用）。

单独放一个模块是为了避免循环导入：场景不导入物理/实体层，而物理/实体层只依赖这里。
"""

from typing import Any

from .scene import Scene

#: 当前场景。``setup()`` 会重新初始化**这个对象**（不重新绑定名字），
#: 因此学生代码里长期持有的 ``global_var`` 引用不会失效。
global_var = Scene()


def resolve_world(world: Any = None) -> Scene:
    """``None`` 表示"当前场景"（spec 01 §2.2）。"""
    return global_var if world is None else world
