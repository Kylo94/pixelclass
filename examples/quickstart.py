"""最小可运行例子：一个角色落到地面并向右走。

python examples/quickstart.py
PIXELCLASS_EXAMPLE_FRAMES=120 python examples/quickstart.py   # 只跑 120 帧（CI / 无显示器）
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import pixelclass as pc  # noqa: E402

FRAMES = int(os.environ.get("PIXELCLASS_EXAMPLE_FRAMES", "0"))


def main():
    pc.setup(640, 480)
    pc.title("quickstart")
    pc.set_gravity(0, -1200)  # 不设重力的话角色不会往下掉

    floor = pc.Wall(size=(600, 20))
    floor.goto(0, -180)

    hero = pc.Character(size=(32, 32))
    hero.goto(-250, 150)
    hero.velocity = (150, 0)

    hud = pc.TextBox(18, "按 Ctrl+C 结束")
    hud.goto(-290, 210)

    frame = 0
    while True:
        pc.update()
        frame += 1
        if FRAMES and frame >= FRAMES:
            break

    pc.done()
    return frame


if __name__ == "__main__":
    frames = main()
    if FRAMES:
        print(f"跑了 {frames} 帧")
