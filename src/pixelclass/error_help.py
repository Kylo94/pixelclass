"""中英双语报错与全局异常钩子（spec 07 §1–§2）。

规则匹配**刻意克制**：只在异常类型 + 特征串都能对上时才给中文解释，匹配不到就什么都不加、
直接走 python 默认行为——硬凑解释比不解释更误导人（旧实现踩过：把任何 ``NoneType`` 的
``AttributeError`` 都判成"忘了 setup()"）。
"""

import os
import sys
from typing import Any, Optional

ENV_VAR = "PIXELCLASS_ERROR_HELP"  # 用本项目自己的前缀，不复用其它项目

_enabled = True
_installed = False
_previous_hook: Any = None

HEADER = "【pixelclass 中文提示】"


def bilingual(zh: str, en: str) -> str:
    """把中英两段文本拼成一条错误消息（中文在前、英文在后）。"""
    return f"{zh}\n{en}"


def not_initialised(action: str = "创建对象") -> RuntimeError:
    """还没有 ``setup()`` 就使用需要窗口/空间的功能。"""
    return RuntimeError(
        bilingual(
            f"{action}失败：还没有初始化窗口。请先调用 setup(800, 600)（数字是窗口宽、高）。",
            "No window/space yet: call setup(width, height) before creating objects.",
        )
    )


# ---------------------------------------------------------------------- 规则
#: (异常类型, 消息特征, 中文解释)。特征串要"够特别"，宁可匹配不到也不要误报。
RULES = [
    (
        RuntimeError,
        "还没有初始化窗口",
        "窗口与物理空间是 setup() 建的：在创建任何对象之前先调用 setup(宽, 高)。",
    ),
    (
        RuntimeError,
        "video system not initialized",
        "画面系统还没启动：先调用 setup(宽, 高)；如果中途调用过 done()，需要重新 setup()。",
    ),
    (
        FileNotFoundError,
        "找不到图片文件",
        "图片路径不对：确认文件存在，并且程序的工作目录就是素材所在目录。",
    ),
    (
        FileNotFoundError,
        "找不到地图文件",
        "地图路径不对：确认 .tmx 文件存在，它引用的图集文件也在同一目录。",
    ),
    (
        AttributeError,
        "has no attribute 'image'",
        "这个对象没有贴图：创建时传入图片，例如 Character('hero.png', size=(32, 32))。",
    ),
    (
        ValueError,
        "动画状态",
        "动画状态名写错了：用 sprite.state 读当前状态，可用状态在创建时的字典键里。",
    ),
    (
        TypeError,
        "约束需要带刚体的对象",
        "约束的对象要有刚体：创建时给 size，例如 Character(size=(32, 32))。",
    ),
    (
        TypeError,
        "size 参数看不懂",
        "size 可以给：整数（半径）、(宽, 高)、点集 [[x, y], …]，或地图对象列表。",
    ),
]


def explain_exception(exc: BaseException) -> str:
    """给异常找一条中文解释；没有合适规则时返回空字符串（不硬凑）。"""
    message = str(exc)
    for kind, needle, explanation in RULES:
        if isinstance(exc, kind) and needle in message:
            return explanation
    return ""


def explain(text: str) -> Optional[str]:
    """按错误文本给中文解释（供教学演示/自测用）。"""
    for _kind, needle, explanation in RULES:
        if needle in text:
            return explanation
    return None


# ---------------------------------------------------------------------- 开关
def is_error_help_enabled() -> bool:
    """当前是否启用中文提示（环境变量 ``PIXELCLASS_ERROR_HELP=0`` 可整体关闭）。"""
    if os.environ.get(ENV_VAR, "1") == "0":
        return False
    return _enabled


def set_error_help(enabled: bool = True) -> bool:
    global _enabled
    _enabled = bool(enabled)
    return _enabled


# ---------------------------------------------------------------------- 钩子
def _hook(exc_type: Any, exc: BaseException, traceback: Any) -> None:
    if is_error_help_enabled():
        explanation = explain_exception(exc)
        if explanation:
            print(f"\n{HEADER}{explanation}\n", file=sys.stderr)
    sys.__excepthook__(exc_type, exc, traceback)


def install_error_help() -> None:
    """安装全局异常钩子：未捕获异常先给中文提示，再打印原始信息。"""
    global _installed, _previous_hook
    if not _installed:
        _previous_hook = sys.excepthook
        sys.excepthook = _hook
        _installed = True


def uninstall_error_help() -> None:
    """还原默认钩子（保留原有非默认钩子）。"""
    global _installed
    if _installed:
        sys.excepthook = _previous_hook if _previous_hook is not None else sys.__excepthook__
        _installed = False


def is_error_help_installed() -> bool:
    return _installed


__all__ = [
    "bilingual",
    "not_initialised",
    "explain_exception",
    "explain",
    "install_error_help",
    "uninstall_error_help",
    "set_error_help",
    "is_error_help_enabled",
    "is_error_help_installed",
    "RULES",
    "ENV_VAR",
]
