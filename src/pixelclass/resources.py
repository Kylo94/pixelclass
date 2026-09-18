"""资源缓存（spec 06 §4）：同一路径只解码一次。

用普通字典 + 显式清理，而不是弱引用兜底：pygame 的 Surface 在很多平台上不支持
弱引用，与其"有时能回收、有时不能"，不如给出确定的 `clear()` 让老师自己控制。
"""

import io
import os
from typing import Any, Dict, Iterable, List, Optional

import pygame

from .error_help import bilingual, not_initialised

#: PNG 文件头（判断"要不要做块过滤"用）
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def strip_iccp(data: bytes) -> Optional[bytes]:
    """去掉 PNG 里的 ``iCCP`` 块；不是 PNG 或本来没有 iCCP 时返回 ``None``。

    为什么要动文件内容：不少素材（含课堂用的这套）带的是"known incorrect sRGB profile"
    这种有问题的 ICC 配置，libpng 每解码一次就往 stderr 打印一条
    ``libpng warning: iCCP: known incorrect sRGB profile``——加载几十张图就刷屏，
    把学生真正要看的信息冲掉。iCCP 只是颜色配置文件，去掉它不影响画面。
    这里只在内存里过滤，**不改动磁盘上的原始素材**。
    """
    if not data.startswith(PNG_SIGNATURE):
        return None
    out = bytearray(PNG_SIGNATURE)
    index = len(PNG_SIGNATURE)
    removed = False
    while index + 8 <= len(data):
        length = int.from_bytes(data[index : index + 4], "big")
        chunk_type = data[index + 4 : index + 8]
        end = index + 12 + length
        if end > len(data):  # 结构不对：原样交回给 pygame 报错
            return None
        if chunk_type == b"iCCP":
            removed = True
        else:
            out += data[index:end]
        index = end
        if chunk_type == b"IEND":
            break
    return bytes(out) if removed else None


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
        source: Any = key
        try:
            with open(key, "rb") as handle:
                raw = handle.read()
        except OSError:
            raw = b""
        clean = strip_iccp(raw) if raw else None
        if clean is not None:
            source = io.BytesIO(clean)
        try:
            image = pygame.image.load(source).convert_alpha()
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
