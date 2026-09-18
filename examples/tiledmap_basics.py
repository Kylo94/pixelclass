"""瓦片地图例子：铺背景 + 从对象层取出实体 + 用整图当碰撞体。

    python examples/tiledmap_basics.py
    PIXELCLASS_EXAMPLE_FRAMES=120 python examples/tiledmap_basics.py

地图与图集用的是仓库自带的验收夹具（`acceptance/fixtures/`），示例与测试共用同一套素材。
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import pixelclass as pc  # noqa: E402

FRAMES = int(os.environ.get("PIXELCLASS_EXAMPLE_FRAMES", "0"))
LEVEL = os.path.join(ROOT, "acceptance", "fixtures", "level.tmx")


def main():
    pc.setup(640, 480)
    pc.title("tiledmap basics")
    pc.set_gravity(0, -1000)

    # 1) 整张地图当背景（相机尺寸会自动设成地图大小）
    pc.bgpic(LEVEL)

    # 2) 对象层 → 实体：地形做成静态、金币做成触发器
    tiled = pc.TiledMap(LEVEL)
    terrain = tiled.create_objects(name="ground_body", body_type="STATIC")
    platforms = tiled.create_objects(name="platform_a", body_type="STATIC")
    coins = tiled.create_objects(name="coin_a", body_type="KINEMATIC", sensor=True)

    # 3) 一个会掉下来的角色，看看它落在哪
    hero = pc.Character(size=(16, 16))
    hero.goto(-120, 60)

    hud = pc.TextBox(16, "从对象层生成：" + ", ".join(item.name for item in tiled.objects))
    hud.goto(-300, 220)

    hits = 0
    frame = 0
    while True:
        pc.update()
        if coins and hero.collide(coins[0]):
            hits += 1
        frame += 1
        if FRAMES and frame >= FRAMES:
            break

    pc.done()
    return frame, len(terrain), len(platforms), len(coins), hits


if __name__ == "__main__":
    frames, terrain, platforms, coins, hits = main()
    if FRAMES:
        print(
            f"跑了 {frames} 帧；地形 {terrain} 个、平台 {platforms} 个、金币 {coins} 个；碰到金币 {hits} 次"
        )
