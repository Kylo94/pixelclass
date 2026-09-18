"""窗口与绘制（spec 01 §3.3）。

M1 只负责：创建窗口、每帧清屏、画调试线段、翻页、保存画面。
实体的绘制在视觉里程碑接入（spec 04）。
"""

import os
from typing import Any, Tuple

import pygame

BACKGROUND = (0, 0, 0)


class Window:
    """一个窗口（整个进程只有一个；多场景共用它，各自有自己的相机偏移）。"""

    def __init__(self, size: Tuple[int, int] = (800, 600), caption: str = "pixelclass") -> None:
        self.size = (int(size[0]), int(size[1]))
        self.surface = pygame.display.set_mode(self.size)
        pygame.display.set_caption(caption)

    def set_size(self, size: Tuple[int, int]) -> None:
        size = (int(size[0]), int(size[1]))
        if size != self.size:
            self.size = size
            self.surface = pygame.display.set_mode(self.size)

    def set_title(self, text: str) -> None:
        pygame.display.set_caption(str(text))

    def draw(self, scene: Any) -> None:
        """清屏 -> 画线段 -> （视觉里程碑接入实体绘制）-> 翻页。"""
        self.surface.fill(BACKGROUND)
        camera = scene.camera
        for line in list(scene.lines):
            start = camera.to_screen(line[0])
            end = camera.to_screen(line[1])
            pygame.draw.line(self.surface, line[2], start, end, line[3])
        scene.lines.clear()
        pygame.display.flip()

    def save(self, path: str) -> str:
        directory = os.path.dirname(os.path.abspath(path))
        if directory and not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)
        pygame.image.save(self.surface, path)
        return path
