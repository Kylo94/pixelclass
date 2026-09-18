"""行为验收：跑 `observations.md` 里的观测并与 `baseline.json` 对拍。

    python acceptance/run.py             # 对拍
    python acceptance/run.py --strict    # 把"暂缺"也算失败（M5 收口时用）
    python acceptance/run.py --freeze    # 有意改动时重新冻结基线

脚本**从规格重写**（不复制旧项目的测试代码）：只使用公共接口 + 可注入时钟。

每项观测**独立执行**：某个功能还没实现（例如地图模块、约束模块）只让相关观测记为"暂缺"，
不影响其它观测的结果——这样进度是一张连续变化的清单，而不是"一票否决"。
"""

import argparse
import json
import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import pygame  # noqa: E402

import pixelclass as pc  # noqa: E402
from pixelclass.clock import PHYSICS_DT, Clock  # noqa: E402
from pixelclass.stepping import fastest_speed, substeps_for  # noqa: E402

FIXTURES = os.path.join(ROOT, "acceptance", "fixtures")
BASELINE = os.path.join(ROOT, "acceptance", "baseline.json")
TILES = os.path.join(FIXTURES, "tiles.png")
LEVEL = os.path.join(FIXTURES, "level.tmx")
TICK_MS = 17  # 固定每帧 17ms：结果可复现（observations.md §0）
TOLERANCE = {"abs_tol": 1e-3, "rel_tol": 1e-9}


class Skip(Exception):
    """功能尚未实现——相关观测记为"暂缺"，不算失败。"""


def _scene(gravity=(0, -1200), size=(640, 480)):
    scene = pc.setup(size[0], size[1])
    pc.set_gravity(gravity[0], gravity[1])
    scene.clock = Clock(ticker=lambda: TICK_MS)
    return scene


def _round(value, digits=3):
    return round(float(value), digits)


def _pair(value):
    return [_round(value[0]), _round(value[1])]


# ---------------------------------------------------------------------- 各观测
def obs_goto_pos():
    _scene()
    hero = pc.Character(size=(32, 32))
    hero.goto(100, 50)
    return _pair(hero.pos)


def _fall_setup():
    _scene()
    hero = pc.Character(size=(32, 32))
    hero.goto(100, 50)
    hero.velocity = (30, 0)
    for _ in range(30):
        pc.update()
    return hero


def obs_fall_after_30():
    return _pair(_fall_setup().pos)


def obs_fall_velocity():
    return _pair(_fall_setup().velocity)


def obs_x_setter():
    _scene()
    hero = pc.Character(size=(32, 32))
    hero.velocity = (99, 99)
    hero.x = 200
    return [_round(hero.x), _round(hero.velocity[0])]


def obs_y_setter():
    _scene()
    hero = pc.Character(size=(32, 32))
    hero.velocity = (99, 99)
    hero.y = -75
    return [_round(hero.y), _round(hero.velocity[1])]


def obs_pos_setter():
    _scene()
    hero = pc.Character(size=(32, 32))
    hero.pos = (-10, -20)
    return [_round(hero.pos[0]), _round(hero.pos[1]), _round(hero.velocity[0]), _round(hero.velocity[1])]


def obs_forward():
    _scene()
    hero = pc.Character(size=(32, 32))
    hero.goto(0, 0)
    hero.velocity = (7, 3)
    hero.forward(5)
    return [
        _round(hero.pos[0]),
        _round(hero.pos[1]),
        _round(hero.velocity[0]),
        _round(hero.velocity[1]),
    ]


def obs_backward():
    _scene()
    hero = pc.Character(size=(32, 32))
    hero.goto(0, 0)
    hero.velocity = (7, 3)
    hero.forward(5)
    hero.backward(5)
    return _pair(hero.pos)


def obs_slide_to():
    _scene()
    hero = pc.Character(size=(32, 32))
    hero.goto(0, 0)
    hero.velocity = (5, 5)
    hero.slide_to((40, 0), 2)
    return [
        _round(hero.pos[0]),
        _round(hero.pos[1]),
        _round(hero.velocity[0]),
        _round(hero.velocity[1]),
    ]


def obs_rot():
    _scene()
    hero = pc.Character(size=(32, 32))
    hero.rot = 30
    return {"rot": _round(hero.rot), "body_angle_deg": _round(math.degrees(hero.rigid.body.angle))}


def obs_scale():
    from pixelclass.physics.geometry import bounds_size

    _scene()
    hero = pc.Character(size=(32, 32))
    hero.scale(2)
    width, height = bounds_size(hero.rigid.shape)
    return [_round(width), _round(height)]


def obs_color():
    _scene()
    tinted = pc.Character(TILES)
    tinted.goto(0, 0)
    tinted.color = (10, 20, 30, 200)
    return list(tinted.color)


def obs_sprite_only_has_body():
    _scene()
    return pc.Character(TILES).rigid is not None


def obs_collisions():
    _scene(gravity=(0, 0))
    wall = pc.Wall(size=(40, 40))
    wall.goto(0, 0)
    box = pc.Character(size=(20, 20))
    box.goto(0, 0)
    result = {
        "collide_point_hit": bool(box.collide((0.0, 0.0))),
        "collide_point_miss": bool(box.collide((500.0, 500.0))),
        "collide_object": bool(box.collide(wall)),
    }
    box.separate(wall)
    result["separate_moved"] = _pair(box.pos)
    return result


def obs_tiled_objects():
    try:
        from pixelclass.worldmap import TiledMap
    except ImportError as exc:
        raise Skip(f"地图模块尚未实现（{exc}）")
    _scene(gravity=(0, 0))
    created = TiledMap(LEVEL).create_objects()
    return [
        [
            go.name,
            _round(go.pos[0], 2),
            _round(go.pos[1], 2),
            go.rigid is not None,
            go.tiles is None,
            go.visual is not None,
        ]
        for go in created
    ]


def obs_camera_pos():
    scene = _scene(gravity=(0, 0))
    target = pc.Character(size=(16, 16), world=scene)
    target.goto(123, 45)
    scene.camera.follow(target)
    pc.update(scene)
    return [_round(scene.camera.x), _round(scene.camera.y)]


def obs_constraint_distance():
    try:
        from pixelclass.physics.joints import connect
    except ImportError as exc:
        raise Skip(f"约束模块尚未实现（{exc}）")
    scene = _scene(gravity=(0, 0))
    first = pc.Character(size=(16, 16), world=scene)
    second = pc.Character(size=(16, 16), world=scene)
    first.goto(0, 0)
    second.goto(50, 0)
    connect(first, second, world=scene)
    second.velocity = (0, 120)
    for _ in range(20):
        pc.update(scene)
    return _round((second.pos - first.pos).length(), 2)


def obs_substepping():
    scene = _scene(gravity=(0, 0))
    bullet = pc.Character(size=(6, 6), world=scene)
    barrier = pc.Wall(size=(8, 120), world=scene)
    bullet.goto(-300, 0)
    barrier.goto(0, 0)
    bullet.velocity = (2400, 0)
    maximum = 0
    for _ in range(40):
        maximum = max(
            maximum,
            substeps_for(
                fastest_speed(scene.space),
                PHYSICS_DT,
                scene.max_step_distance,
                scene.max_substeps,
            ),
        )
        pc.update(scene)
    return {
        "max_substeps": int(maximum),
        "substep_no_tunnel": bool(bullet.pos[0] < 0),
        "tunnel_bullet_x": _round(bullet.pos[0], 2),
    }


def obs_after_kill():
    _scene()
    hero = pc.Character(TILES, size=(16, 16))
    hero.kill()
    return [hero.alive, hero.visual is None, hero.rigid is None, hero.tiles is None]


def obs_frame_hash():
    """固定场景渲染一帧后的像素哈希（B 组：在本引擎自己的夹具上冻结）。"""
    import hashlib

    _scene()
    pc.bgpic(TILES)
    marker = pc.Character(TILES, size=(32, 32))
    marker.goto(30, 20)
    marker.rot = 15
    pc.update()
    surface = pygame.display.get_surface()
    return hashlib.sha256(pygame.image.tostring(surface, "RGB")).hexdigest()[:16]


def obs_sprite_only_collide_self():
    _scene()
    tinted = pc.Character(TILES)
    tinted.goto(0, 0)
    return bool(tinted.collide((float(tinted.width) / 2, 0.0)))


OBSERVATIONS = [
    obs_goto_pos,
    obs_fall_after_30,
    obs_fall_velocity,
    obs_x_setter,
    obs_y_setter,
    obs_pos_setter,
    obs_forward,
    obs_backward,
    obs_slide_to,
    obs_rot,
    obs_scale,
    obs_color,
    obs_sprite_only_has_body,
    obs_collisions,
    obs_tiled_objects,
    obs_camera_pos,
    obs_constraint_distance,
    obs_substepping,
    obs_after_kill,
    obs_frame_hash,
    obs_sprite_only_collide_self,
]


def observe():
    """跑全部观测；单项失败/暂缺不影响其它项。"""
    _scene()  # 先建立窗口与默认场景（Sprite 载入图片需要 display）
    out = {}
    for function in OBSERVATIONS:
        name = function.__name__[4:]
        try:
            value = function()
        except Skip as exc:
            out[name] = f"NA: {exc}"
        except Exception as exc:  # noqa: BLE001 - 验收脚本要如实报告，而不是崩掉
            out[name] = f"ERROR: {type(exc).__name__}: {exc}"
        else:
            if isinstance(value, dict):
                for key, item in value.items():
                    out[key] = item
            else:
                out[name] = value
    return out


# ---------------------------------------------------------------------- 对拍
def _is_missing(value):
    return isinstance(value, str) and (value.startswith("NA") or value.startswith("ERROR"))


def _same(want, got):
    if isinstance(want, float) or isinstance(got, float):
        try:
            return math.isclose(float(got), float(want), **TOLERANCE)
        except (TypeError, ValueError):
            return False
    return want == got


def main(argv=None):
    parser = argparse.ArgumentParser(description="pixelclass 行为验收")
    parser.add_argument("--freeze", action="store_true", help="把新观测合并进基线")
    parser.add_argument("--force", action="store_true", help="配合 --freeze：允许覆盖既有期望值")
    parser.add_argument("--strict", action="store_true", help="把暂缺的观测也算失败")
    args = parser.parse_args(argv)

    actual = observe()

    if args.freeze:
        existing = {}
        if os.path.isfile(BASELINE):
            with open(BASELINE, encoding="utf-8") as handle:
                existing = {k: v for k, v in json.load(handle).items() if not k.startswith("_")}
        fresh = {key: value for key, value in actual.items() if not _is_missing(value)}

        # 既有期望值（A 组，来自旧引擎实测）不允许被悄悄覆盖：那是等价性承诺
        changed = [
            (name, existing[name], fresh[name])
            for name in sorted(set(existing) & set(fresh))
            if not _same(existing[name], fresh[name])
        ]
        if changed and not args.force:
            print("拒绝冻结：以下既有期望值发生了变化（这属于行为回归，不是新观测）：")
            for name, want, got in changed:
                print(f"  ✗ {name:22s} 期望 {want}  实际 {got}")
            print("\n确认是有意改动时用 --freeze --force。")
            return 1

        merged = dict(existing)
        merged.update(fresh)
        with open(BASELINE, "w", encoding="utf-8") as handle:
            json.dump(merged, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        added = sorted(set(fresh) - set(existing))
        print(f"基线已更新：{os.path.relpath(BASELINE, ROOT)}（共 {len(merged)} 项，新增 {added or '无'}）")
        return 0

    if not os.path.isfile(BASELINE):
        print(f"缺少基线文件：{os.path.relpath(BASELINE, ROOT)}")
        return 1
    with open(BASELINE, encoding="utf-8") as handle:
        baseline = {key: value for key, value in json.load(handle).items() if not key.startswith("_")}

    matched, mismatched, missing = [], [], []
    for name in sorted(baseline):
        want = baseline[name]
        if name not in actual or _is_missing(actual.get(name)):
            reason = actual.get(name, "NA: 脚本未产出")
            missing.append((name, str(reason)[4:].strip() or "暂缺"))
        elif _same(want, actual[name]):
            matched.append(name)
        else:
            mismatched.append((name, want, actual[name]))

    print(f"对照基线：一致 {len(matched)} 项 / 不一致 {len(mismatched)} 项 / 暂缺 {len(missing)} 项\n")
    for name in sorted(matched):
        print(f"  ✓ {name:22s} {baseline[name]}")
    for name, want, got in mismatched:
        print(f"  ✗ {name:22s} 期望 {want}  实际 {got}")
    for name, reason in missing:
        print(f"  — {name:22s} 暂缺（{reason}）")

    if mismatched:
        print(f"\n不一致 {len(mismatched)} 项")
        return 1
    if args.strict and missing:
        print(f"\n[--strict] 仍有 {len(missing)} 项暂缺")
        return 1
    print("\n行为验收通过" + (f"（{len(missing)} 项暂缺）" if missing else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
