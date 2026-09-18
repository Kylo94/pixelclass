"""窗口与绘制（spec 01 §3.3）。

M1 只负责：创建窗口、每帧清屏、画调试线段、翻页、保存画面。
实体的绘制在视觉里程碑接入（spec 04）。
"""

import math
import os
from typing import Any, List, Tuple

import pymunk

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
        """清屏 -> 按图层画所有可见贴图 -> 画线段 -> 翻页（spec 04 §3）。"""
        self.surface.fill(BACKGROUND)
        camera = scene.camera
        for visual in sorted(list(scene.visuals), key=lambda item: getattr(item, "layer", 0)):
            if not getattr(visual, "visible", True):
                continue
            visual.draw(self.surface, camera)
        for line in list(scene.lines):
            start = camera.to_screen(line[0])
            end = camera.to_screen(line[1])
            pygame.draw.line(self.surface, line[2], start, end, line[3])
        scene.lines.clear()
        if getattr(scene, "debug", False):
            self._draw_debug(scene)
        pygame.display.flip()

    def _draw_debug(self, scene: Any) -> None:
        """`debug(True)` 时把刚体轮廓画出来（课堂演示"碰撞体到底在哪"）。"""
        bodies = list(scene.rigids)
        for group in list(scene.tiles):
            bodies.extend(list(group))
        camera = scene.camera
        for body in bodies:
            shape = getattr(body, "shape", None)
            if shape is None or shape.body is None:
                continue
            if isinstance(shape, pymunk.Circle):
                center = camera.to_screen(shape.body.position)
                pygame.draw.circle(
                    self.surface,
                    (0, 255, 0),
                    (int(center[0]), int(center[1])),
                    max(1, int(shape.radius * camera.zoom)),
                    1,
                )
                continue
            angle = shape.body.angle
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            origin = shape.body.position
            points: List[Tuple[float, float]] = [
                camera.to_screen(
                    (
                        origin[0] + vertex[0] * cos_a - vertex[1] * sin_a,
                        origin[1] + vertex[0] * sin_a + vertex[1] * cos_a,
                    )
                )
                for vertex in shape.get_vertices()
            ]
            if len(points) >= 3:
                pygame.draw.polygon(self.surface, (0, 255, 0), points, 1)

    def save(self, path: str) -> str:
        directory = os.path.dirname(os.path.abspath(path))
        if directory and not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)
        pygame.image.save(self.surface, path)
        return path
