"""输入（spec 06 §2）：鼠标、键盘、简易文本输入。

坐标一律返回**数学坐标**。"刚按下 / 刚松开"只在事件发生的那一帧为真：
每帧开头由 :func:`process_events` 复位这些标记，再由事件队列重新置位。
"""

from typing import Any, Dict, Optional, Tuple

import pygame

from .context import resolve_world
from .vec import pygame2Cartesian

LEFT = 1  # pygame 的左键编号（学生直接写 1 也行）

_state: Dict[str, Any] = {
    "mouse_held": False,
    "mouse_just_pressed": False,
    "mouse_just_released": False,
    "keys_held": set(),
    "keys_just_pressed": set(),
    "keys_just_released": set(),
    "text_buffer": "",
    "text_done": False,
    "quit": False,
}


def _scene_size(world: Any = None) -> Tuple[int, int]:
    scene = resolve_world(world)
    size = getattr(scene.camera, "size", None)
    return (int(size[0]), int(size[1])) if size else (800, 600)


# ---------------------------------------------------------------------- 每帧事件
def process_events(world: Any = None) -> Dict[str, Any]:
    """每帧开头调用：复位"刚发生"标记，然后从事件队列里更新状态。"""
    _state["mouse_just_pressed"] = False
    _state["mouse_just_released"] = False
    _state["keys_just_pressed"] = set()
    _state["keys_just_released"] = set()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            _state["quit"] = True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == LEFT:
            _state["mouse_held"] = True
            _state["mouse_just_pressed"] = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == LEFT:
            _state["mouse_held"] = False
            _state["mouse_just_released"] = True
        elif event.type == pygame.KEYDOWN:
            _state["keys_held"].add(event.key)
            _state["keys_just_pressed"].add(event.key)
            if event.key == pygame.K_RETURN:
                _state["text_done"] = True
            elif event.key == pygame.K_BACKSPACE:
                _state["text_buffer"] = _state["text_buffer"][:-1]
            elif getattr(event, "unicode", "") and event.unicode.isprintable():
                _state["text_buffer"] += event.unicode
        elif event.type == pygame.KEYUP:
            _state["keys_held"].discard(event.key)
            _state["keys_just_released"].add(event.key)
        elif event.type == pygame.TEXTINPUT:
            _state["text_buffer"] += event.text
    return _state


def should_quit() -> bool:
    """用户是否点了窗口关闭按钮。"""
    return bool(_state["quit"])


def reset_quit() -> None:
    _state["quit"] = False


# ---------------------------------------------------------------------- 鼠标
def get_mouse_pos(world: Any = None) -> Tuple[float, float]:
    """鼠标位置的数学坐标。"""
    return pygame2Cartesian(pygame.mouse.get_pos(), _scene_size(world))


def get_mouse_rel() -> Tuple[float, float]:
    """自上一帧起的鼠标相对位移（y 取反以符合数学坐标习惯）。"""
    dx, dy = pygame.mouse.get_rel()
    return (float(dx), -float(dy))


def get_mouse_clicked() -> bool:
    """左键是否**按住**。"""
    return bool(_state["mouse_held"])


def get_mouse_just_clicked() -> bool:
    """本帧是否**刚按下**。"""
    return bool(_state["mouse_just_pressed"])


def get_mouse_just_released() -> bool:
    """本帧是否**刚松开**。"""
    return bool(_state["mouse_just_released"])


def set_mouse_visible(visible: bool = True) -> None:
    pygame.mouse.set_visible(bool(visible))


# ---------------------------------------------------------------------- 键盘
def key_pressed(key: Optional[int] = None) -> bool:
    """按键是否按住；不传键表示"任意键按住"。"""
    if key is None:
        return bool(_state["keys_held"])
    return key in _state["keys_held"]


def key_just_pressed(key: int) -> bool:
    return key in _state["keys_just_pressed"]


def key_just_released(key: int) -> bool:
    return key in _state["keys_just_released"]


# ---------------------------------------------------------------------- 文本输入
def key_input(prompt: str = "", max_length: int = 20, world: Any = None) -> str:
    """简易文本输入：返回当前已输入的文字（回车表示结束）。

    用法：每帧调用，把返回值画出来；`text_input_done()` 变真说明学生按了回车，
    取完结果后用 `text_input_reset()` 清空。
    """
    text = str(_state["text_buffer"])
    if len(text) > int(max_length):
        text = text[: int(max_length)]
        _state["text_buffer"] = text
    return text


def text_input_done() -> bool:
    """这一轮输入是否已按回车结束。"""
    return bool(_state["text_done"])


def text_input_reset() -> None:
    """清空输入内容与结束标记（开始新一轮输入）。"""
    _state["text_buffer"] = ""
    _state["text_done"] = False


def get_input_state() -> Dict[str, Any]:
    """当前输入状态（测试与调试用）。"""
    return _state


__all__ = [
    "process_events",
    "should_quit",
    "reset_quit",
    "get_mouse_pos",
    "get_mouse_rel",
    "get_mouse_clicked",
    "get_mouse_just_clicked",
    "get_mouse_just_released",
    "set_mouse_visible",
    "key_pressed",
    "key_just_pressed",
    "key_just_released",
    "key_input",
    "text_input_done",
    "text_input_reset",
    "get_input_state",
]
