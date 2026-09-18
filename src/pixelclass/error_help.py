"""中英双语报错（spec 07 §1）。

规则：**中文在前、英文在后**，保留原始异常类型；不吞掉英文原文（便于搜索报错）。
完整的异常钩子与规则库在报错里程碑补齐，这里先提供拼接函数与最常用的两个错误。
"""


def bilingual(zh: str, en: str) -> str:
    """把中英两段文本拼成一条错误消息。"""
    return f"{zh}\n{en}"


def not_initialised(action: str = "创建对象") -> RuntimeError:
    """还没有 ``setup()`` 就使用需要窗口/空间的功能。"""
    return RuntimeError(
        bilingual(
            f"{action}失败：还没有初始化窗口。请先调用 setup(800, 600)（数字是窗口宽、高）。",
            "No window/space yet: call setup(width, height) before creating objects.",
        )
    )
