"""界面文本与对话框（spec 07 §4）。

两者都是**实体**：可以 `goto()`、`color`、`visible`、`kill()`，
由场景的绘制集合按图层统一绘制（每帧更新不会闪烁）。
"""

from typing import Any, Optional, Tuple

import pygame

from ..entity import Entity
from ..fonts import load_font

DEFAULT_SIZE = 18
DEFAULT_COLOR = (255, 255, 255)
DEFAULT_BACKGROUND = (0, 0, 0, 160)
MARGIN = 8


class TextBox(Entity):
    """屏幕文字：`write(文字)` 更新内容。"""

    def __init__(
        self,
        size: int = DEFAULT_SIZE,
        text: str = "",
        color: Tuple[int, int, int] = DEFAULT_COLOR,
        background: Optional[Tuple[int, int, int, int]] = DEFAULT_BACKGROUND,
        font: Optional[str] = None,
        world: Any = None,
    ) -> None:
        Entity.__init__(self, None, None, body_type="KINEMATIC", sensor=False, world=world)
        self.font_size = int(size)
        self.font_path = font
        self.text_color = tuple(color)
        self.background = background
        self.text = ""
        self._font: Any = None
        self.write(text)

    # ------------------------------------------------------------------ 内容
    def _get_font(self) -> Any:
        if self._font is None:
            self._font = load_font(self.font_size, self.font_path)
        return self._font

    def set_font(self, path: Optional[str], size: Optional[int] = None) -> None:
        """换字体（例如指定一个中文字体文件）。"""
        self.font_path = path
        if size is not None:
            self.font_size = int(size)
        self._font = None
        self.write(self.text)

    def write(self, text: Any) -> None:
        """更新显示的文字（立即重画，下一帧就是新内容）。"""
        self.text = "" if text is None else str(text)
        self._rebuild()

    #: 兼容名（旧讲义里用 `textbox.write()`；这里也允许 `textbox.text = ...` 后手动刷新）
    def refresh(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        font = self._get_font()
        lines = self.text.split("\n") or [""]
        rendered = [font.render(line, True, self.text_color) for line in lines]
        width = max((item.get_width() for item in rendered), default=1) + MARGIN * 2
        height = sum(item.get_height() for item in rendered) + MARGIN * 2
        surface = pygame.Surface((max(1, width), max(1, height)), pygame.SRCALPHA)
        if self.background is not None:
            surface.fill(tuple(self.background))
        offset = MARGIN
        for item in rendered:
            surface.blit(item, (MARGIN, offset))
            offset += item.get_height()
        if self.visual is None:
            from ..visual import Sprite

            self.visual = Sprite(surface, self.world)
            self.visual.set_parent(self)
        else:
            self.visual.set_base_image(surface)

    def _update(self) -> None:
        super()._update()
        if self._dirty:
            self._dirty = False
            self._rebuild()

    #: 直接改 `text` 属性后置真即可在下一帧重画
    _dirty = False


class DialogBox(TextBox):
    """跟随某个对象的对话框：按目标所在象限选择朝向，`say()` 显示、自动淡出。"""

    def __init__(
        self,
        target: Any = None,
        size: int = DEFAULT_SIZE,
        color: Tuple[int, int, int] = DEFAULT_COLOR,
        background: Optional[Tuple[int, int, int, int]] = DEFAULT_BACKGROUND,
        font: Optional[str] = None,
        world: Any = None,
    ) -> None:
        TextBox.__init__(self, size=size, color=color, background=background, font=font, world=world)
        self.target = target
        self.duration = 2.0
        self._left = 0.0
        self.visible = False

    # ------------------------------------------------------------------ 显示
    def say(self, text: Any, duration: Optional[float] = None) -> None:
        """显示一句话；`duration` 秒后自动隐藏。"""
        self.write(text)
        if duration is not None:
            self.duration = float(duration)
        self._left = self.duration
        self.visible = True
        self._follow()

    def hide(self) -> None:
        self.visible = False
        self._left = 0.0

    def _follow(self) -> None:
        """按目标的屏幕象限决定对话框贴在它的哪一侧。"""
        target = self.target
        if target is None:
            return
        camera = self.world.camera
        screen_x, screen_y = camera.to_screen(getattr(target, "pos", (0, 0)))
        half_w, half_h = camera.size[0] / 2, camera.size[1] / 2
        above = screen_y >= half_h
        right = screen_x <= half_w
        offset_x = (self.width / 2 + 12) * (1 if right else -1)
        offset_y = (self.height / 2 + 12) * (1 if above else -1)
        pos = getattr(target, "pos", (0, 0))
        self.goto(pos[0] + offset_x, pos[1] + offset_y)

    def _update(self) -> None:
        TextBox._update(self)
        target = self.target
        if target is not None and not getattr(target, "alive", True):
            self.hide()  # 目标被销毁：安静地消失，不报错
            return
        if not self.visible:
            return
        self._follow()
        self._left = max(0.0, self._left - self.world.clock.dt)
        if self._left <= 0.0:
            self.hide()

    def _on_kill(self) -> None:
        self.target = None


__all__ = ["TextBox", "DialogBox"]
