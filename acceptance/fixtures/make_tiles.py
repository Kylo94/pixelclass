"""生成验收夹具用的图集（自绘色块，不使用任何第三方素材）。

用法：python acceptance/fixtures/make_tiles.py
输出：acceptance/fixtures/tiles.png —— 4 个 16×16 色块横向排列（共 64×16）。

第 1 块（gid=1）完全不透明；第 2 块带一个透明角（用于验证"贴图 mask 判定"确实按 alpha 走）；
第 3、4 块为实色，其中 gid=4 被验收地图的图块对象引用。
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

TILE = 16
COLORS = [(220, 60, 60), (60, 180, 90), (70, 120, 220), (240, 200, 70)]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tiles.png")


def build():
    pygame.init()
    pygame.display.set_mode((64, 16))
    sheet = pygame.Surface((TILE * len(COLORS), TILE), pygame.SRCALPHA)
    for index, color in enumerate(COLORS):
        tile = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        tile.fill(color)
        if index == 1:  # 第 2 块挖掉右下角 6×6：mask 判定应当认为那里"没碰着"
            pygame.draw.rect(tile, (0, 0, 0, 0), pygame.Rect(TILE - 6, TILE - 6, 6, 6))
        sheet.blit(tile, (index * TILE, 0))
    pygame.image.save(sheet, OUT)
    pygame.quit()
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"已生成 {path}（{os.path.getsize(path)} 字节）")
