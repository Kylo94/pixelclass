"""pixelclass：给中小学课堂用的 2D 游戏引擎。

实现进度见 `docs/spec/README.md`（里程碑在 spec 00 §7）。
当前处于 **M1**：场景、可注入时钟、固定步长与自适应子步、主循环。
实体 / 视觉 / 物理组件在 M2–M4 接入，公共名字逐步补齐到 spec 08 的清单。
"""

import types

from pygame import locals as _pygame_locals
from pygame.locals import *  # noqa: F401,F403  —— 事件与按键常量（学生不写前缀也能用）

from ._version import __version__
from .audio import (
    audio_available,
    set_volume,
    bgmusic,
    music_fadeout,
    music_get_busy,
    music_get_endevent,
    music_get_pos,
    music_get_volume,
    music_load,
    music_pause,
    music_play,
    music_queue,
    music_rewind,
    music_set_endevent,
    music_set_pos,
    music_set_volume,
    music_stop,
    music_unpause,
)
from .camera import Camera
from .context import global_var
from .error_help import (
    explain_exception,
    install_error_help,
    is_error_help_enabled,
    set_error_help,
    uninstall_error_help,
)
from .fonts import find_font, load_font
from .entity import Character, Entity, Mouse, Sensor, Wall
from .physics import Body, BodiesGroup, TiledMapBodies, TiledMapBodiesGroup
from .physics.joints import Connect, Spring, connect
from .resources import ResourceManager, load_image, preload
from .runtime import (
    bgpic,
    debug,
    cwd,
    done,
    draw_line,
    init,
    save_screen,
    set_gravity,
    setup,
    random_pos,
    set_depth,
    speed,
    title,
    tracer,
    update,
)
from .input import (
    get_mouse_clicked,
    get_mouse_just_clicked,
    get_mouse_just_released,
    get_mouse_pos,
    get_mouse_rel,
    key_input,
    key_just_pressed,
    key_just_released,
    key_pressed,
    set_mouse_visible,
    should_quit,
    text_input_done,
    text_input_reset,
)
from .scene import Group, Scene
from .vec import Cartesian2pygame, pygame2Cartesian, sign, to_cp, vec
from .visual import (
    AnimatorStrategy,
    EasySpriteStrategy,
    ListSpriteStrategy,
    Sprite,
    SpriteSheet,
    TiledMapStrategy,
)
from .ui import DialogBox, TextBox
from .worldmap import TiledMap
from .window import Window

# 讲义兼容别名（spec 08 §2.1）
World = Scene
Screen = Window
GameObject = Entity
NewGameObject = Entity  # 兼容名：老讲义里出现过的基类名

_FRAMEWORK_NAMES = [
    # 场景与主循环（spec 01）
    "Scene",
    "World",
    "setup",
    "update",
    "done",
    "title",
    "save_screen",
    "global_var",
    "init",
    "cwd",
    "Group",
    # 实体与预设（spec 02）
    "Entity",
    "GameObject",
    "NewGameObject",
    "Character",
    "Wall",
    "Sensor",
    "Mouse",
    # 视觉与输入（spec 04）
    "Sprite",
    "SpriteSheet",
    "EasySpriteStrategy",
    "ListSpriteStrategy",
    "AnimatorStrategy",
    "TiledMapStrategy",
    "bgpic",
    # 地图（spec 05）
    "TiledMap",
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
    "should_quit",
    # 文本与对话框（spec 07 §4）
    "TextBox",
    "DialogBox",
    # 资源（spec 06 §4）
    "load_image",
    "preload",
    "ResourceManager",
    # 窗口与相机
    "Window",
    "Screen",
    "Camera",
    # 物理（spec 03）
    "Body",
    "BodiesGroup",
    "TiledMapBodies",
    "TiledMapBodiesGroup",
    # 约束（spec 03 §6）
    "connect",
    "Connect",
    "Spring",
    # 音频（spec 06 §3）
    "bgmusic",
    "set_volume",
    "audio_available",
    "music_load",
    "music_play",
    "music_queue",
    "music_stop",
    "music_pause",
    "music_unpause",
    "music_rewind",
    "music_fadeout",
    "music_set_pos",
    "music_get_pos",
    "music_set_volume",
    "music_get_volume",
    "music_get_busy",
    "music_set_endevent",
    "music_get_endevent",
    # 报错与字体（spec 07）
    "install_error_help",
    "uninstall_error_help",
    "set_error_help",
    "is_error_help_enabled",
    "explain_exception",
    "find_font",
    "load_font",
    # 工具（spec 01 / 07）
    "draw_line",
    "set_gravity",
    "debug",
    "tracer",
    "random_pos",
    "set_depth",
    "speed",
    "sign",
    "Cartesian2pygame",
    "pygame2Cartesian",
    "to_cp",
    "vec",
    "__version__",
]

_PYGAME_CONSTANTS = [
    _name
    for _name in dir(_pygame_locals)
    if not _name.startswith("_") and not isinstance(getattr(_pygame_locals, _name), types.ModuleType)
]

__all__ = [*_FRAMEWORK_NAMES, *_PYGAME_CONSTANTS]

# 默认安装中文报错钩子（可用 set_error_help(False) 或 PIXELCLASS_ERROR_HELP=0 关闭）
if is_error_help_enabled():
    install_error_help()
