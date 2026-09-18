"""音频（spec 06 §3）。

铁律：**没有可用设备、或没有载入音乐时，所有接口安全无操作**——
绝不因为放不出声音而让游戏崩掉。
"""

import os
from typing import Any, Optional

import pygame

MUSIC_EXTENSIONS = (".ogg", ".mp3", ".wav")  # 文件名不写扩展名时按此顺序探测

_master_volume = 1.0


def audio_available() -> bool:
    """当前是否有可用的音频设备。"""
    return pygame.mixer.get_init() is not None


def _ready() -> bool:
    """确保混音器可用；不可用就返回 False（调用方静默返回）。"""
    if pygame.mixer.get_init() is not None:
        return True
    try:
        pygame.mixer.init()
    except (pygame.error, TypeError):
        return False
    return pygame.mixer.get_init() is not None


def resolve_music(name: Any) -> Optional[str]:
    """把音乐名解析成真实文件路径（可省略扩展名）；找不到返回 ``None``。"""
    if name is None:
        return None
    text = str(name)
    if os.path.isfile(text):
        return text
    for extension in MUSIC_EXTENSIONS:
        candidate = text + extension
        if os.path.isfile(candidate):
            return candidate
    return None


# ---------------------------------------------------------------------- 背景音乐
def music_load(name: Any) -> bool:
    if not _ready():
        return False
    path = resolve_music(name)
    if path is None:
        print(f"[pixelclass] 找不到音乐文件：{name}（Music file not found）")
        return False
    try:
        pygame.mixer.music.load(path)
    except pygame.error as error:  # 格式不支持等
        print(f"[pixelclass] 音乐载入失败：{error}")
        return False
    return True


def music_play(loops: int = -1, start: float = 0.0) -> bool:
    """开始播放；没有载入音乐时返回 False（不抛异常）。"""
    if not _ready():
        return False
    try:
        pygame.mixer.music.set_volume(_master_volume)
        pygame.mixer.music.play(loops=loops, start=start)
    except pygame.error:
        return False
    return True


def bgmusic(name: Any) -> bool:
    """课堂常用入口：载入并循环播放。"""
    return music_load(name) and music_play()


def music_queue(name: Any) -> bool:
    if not _ready():
        return False
    path = resolve_music(name)
    if path is None:
        return False
    try:
        pygame.mixer.music.queue(path)
    except pygame.error:
        return False
    return True


def music_stop() -> bool:
    if not _ready():
        return False
    try:
        pygame.mixer.music.stop()
    except pygame.error:
        return False
    return True


def music_pause() -> bool:
    if not _ready():
        return False
    try:
        pygame.mixer.music.pause()
    except pygame.error:
        return False
    return True


def music_unpause() -> bool:
    if not _ready():
        return False
    try:
        pygame.mixer.music.unpause()
    except pygame.error:
        return False
    return True


def music_rewind() -> bool:
    if not _ready():
        return False
    try:
        pygame.mixer.music.rewind()
    except pygame.error:
        return False
    return True


def music_fadeout(ms: int = 1000) -> bool:
    """淡出（不传参数时用默认 1000 毫秒，不得因缺参报错）。"""
    if not _ready():
        return False
    try:
        pygame.mixer.music.fadeout(int(ms))
    except pygame.error:
        return False
    return True


def music_set_pos(seconds: float) -> bool:
    if not _ready():
        return False
    try:
        pygame.mixer.music.set_pos(float(seconds))
    except pygame.error:
        return False
    return True


def music_get_pos() -> float:
    if not _ready():
        return 0.0
    try:
        return float(pygame.mixer.music.get_pos())
    except pygame.error:
        return 0.0


def music_set_volume(value: float) -> float:
    if not _ready():
        return 0.0
    volume = max(0.0, min(1.0, float(value)))
    try:
        pygame.mixer.music.set_volume(volume)
    except pygame.error:
        return 0.0
    return volume


def music_get_volume() -> float:
    if not _ready():
        return 0.0
    try:
        return float(pygame.mixer.music.get_volume())
    except pygame.error:
        return 0.0


def music_get_busy() -> bool:
    if not _ready():
        return False
    try:
        return bool(pygame.mixer.music.get_busy())
    except pygame.error:
        return False


def music_set_endevent(event_type: Optional[int] = None) -> bool:
    if not _ready():
        return False
    try:
        pygame.mixer.music.set_endevent(event_type if event_type is not None else 0)
    except pygame.error:
        return False
    return True


def music_get_endevent() -> int:
    if not _ready():
        return 0
    try:
        return int(pygame.mixer.music.get_endevent())
    except pygame.error:
        return 0


def set_volume(value: float) -> float:
    """主音量（0~1）：同时作用于背景音乐与之后播放的音效。"""
    global _master_volume
    _master_volume = max(0.0, min(1.0, float(value)))
    if _ready():
        try:
            pygame.mixer.music.set_volume(_master_volume)
        except pygame.error:
            pass
    return _master_volume


def get_volume() -> float:
    return _master_volume


def load_sound(path: Any) -> Optional[Any]:
    """载入音效（无设备或文件缺失时返回 None，不抛异常）。"""
    if not _ready():
        return None
    resolved = resolve_music(path)
    if resolved is None:
        return None
    try:
        sound = pygame.mixer.Sound(resolved)
        sound.set_volume(_master_volume)
    except pygame.error:
        return None
    return sound


__all__ = [
    "audio_available",
    "resolve_music",
    "load_sound",
    "bgmusic",
    "set_volume",
    "get_volume",
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
]
