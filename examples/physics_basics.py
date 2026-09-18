"""物理例子：碰撞、弹性、约束、防高速穿透，并打开调试绘制看刚体轮廓。

python examples/physics_basics.py
PIXELCLASS_EXAMPLE_FRAMES=180 python examples/physics_basics.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import pixelclass as pc  # noqa: E402

FRAMES = int(os.environ.get("PIXELCLASS_EXAMPLE_FRAMES", "0"))


def main():
    pc.setup(800, 480)
    pc.title("physics basics")
    pc.set_gravity(0, -900)
    pc.debug(True)  # 画出刚体轮廓：碰撞体到底在哪一目了然

    ground = pc.Wall(size=(760, 20))
    ground.goto(0, -200)

    # 会弹的球
    ball = pc.Character(size=18)
    ball.goto(-260, 120)
    ball.elasticity = 0.8
    ball.velocity = (160, 0)

    # 结实一点的箱子
    crate = pc.Character(size=(36, 36))
    crate.goto(-40, 160)
    crate.elasticity = 0.1
    crate.friction = 0.9

    # 用弹簧把箱子吊起来
    anchor = pc.Wall(size=(10, 10))
    anchor.goto(-40, 200)
    pc.Spring(anchor, crate, rest_length=40, stiffness=200, damping=12)

    # 高速子弹：不开子步就会穿墙
    bullet = pc.Character(size=(6, 6))
    bullet.goto(300, 0)
    bullet.velocity = (-2400, 0)

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
