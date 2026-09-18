"""资源缓存（spec 06 §4）：同一路径只解码一次。

用普通字典 + 显式清理，而不是弱引用兜底：pygame 的 Surface 在很多平台上不支持
弱引用，与其"有时能回收、有时不能"，不如给出确定的 `clear()` 让老师自己控制。
"""

import os
from typing import Any, Dict, Iterable, List, Optional

import pygame

from .error_help import bilingual, not_initialised


class ResourceManager:
    """图片加载与缓存（按路径缓存，命中即复用）。"""

    def __init__(self) -> None:
        self._images: Dict[str, pygame.Surface] = {}
        self.hits = 0
        self.misses = 0

    # ------------------------------------------------------------------ 图片
    def load_image(self, path: Any) -> pygame.Surface:
        key = str(path)
        if key in self._images:
            self.hits += 1
            return self._images[key]
        if not os.path.isfile(key):
            raise FileNotFoundError(
                bilingual(
                    f"找不到图片文件：{os.path.abspath(key)}（检查路径与当前目录）",
                    f"Image file not found: {os.path.abspath(key)}",
                )
            )
        if pygame.display.get_surface() is None:
            raise not_initialised("载入图片")
        try:
            image = pygame.image.load(key).convert_alpha()
        except pygame.error as error:
            message = str(error)
            if "display" in message or "video" in message:
                # pygame 的 display 状态在 quit() 之后不一定如实反映，这里按真实失败原因归类
                raise not_initialised("载入图片") from error
            raise ValueError(
                bilingual(f"这个文件不是能用的图片：{key}（{error}）", f"Not a usable image: {key} ({error})")
            ) from error
        self._images[key] = image
        self.misses += 1
        return image

    def preload(self, paths: Iterable[Any]) -> List[pygame.Surface]:
        """批量载入；任何一个文件缺失都会给出可读错误。"""
        return [self.load_image(path) for path in paths]

    # ------------------------------------------------------------------ 维护
    def has(self, path: Any) -> bool:
        return str(path) in self._images

    def clear(self, path: Optional[Any] = None) -> None:
        """清空缓存（或只清某一个路径）。"""
        if path is None:
            self._images.clear()
        else:
            self._images.pop(str(path), None)

    def stats(self) -> Dict[str, int]:
        return {"cached": len(self._images), "hits": self.hits, "misses": self.misses}


#: 进程内共享的默认缓存（两个场景共用同一张图不会重复解码）
_default = ResourceManager()


def manager(world: Any = None) -> ResourceManager:
    """取场景级缓存（场景自建一个，默认场景共用进程缓存）。"""
    from .context import resolve_world

    scene = resolve_world(world)
    cache = getattr(scene, "resources", None)
    if cache is None:
        cache = ResourceManager()
        scene.resources = cache
    return cache


def load_image(path: Any, world: Any = None) -> pygame.Surface:
    """载入图片（带缓存）。"""
    return manager(world).load_image(path)


def preload(paths: Iterable[Any], world: Any = None) -> List[pygame.Surface]:
    """批量预载（缺文件会报中英双语错误）。"""
    return manager(world).preload(paths)


__all__ = ["ResourceManager", "load_image", "preload", "manager"]
