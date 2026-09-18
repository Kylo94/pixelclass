"""M3 测试：实体、三个组件槽位、四个预设、缺失组件提示、碰撞三路径（spec 02 / 03 §5）。"""

import os
import warnings

import pytest

import pixelclass as pc
from pixelclass.context import resolve_world
from pixelclass.physics import BODY_TYPES

FIXTURE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "acceptance", "fixtures", "tiles.png"
)


@pytest.fixture(autouse=True)
def _fresh_scene():
    pc.setup(320, 240)
    yield


# ------------------------------------------------------------------ 预设与形状
def test_presets_are_entities_with_expected_body_types():
    character = pc.Character(size=(16, 16))
    wall = pc.Wall(size=(16, 16))
    sensor = pc.Sensor(size=(16, 16))
    assert isinstance(character, pc.Entity) and isinstance(wall, pc.Entity)
    assert character.rigid.body_type == BODY_TYPES["DYNAMIC"]
    assert wall.rigid.body_type == BODY_TYPES["STATIC"]
    assert sensor.rigid.body_type == BODY_TYPES["KINEMATIC"]
    assert sensor.rigid.sensor is True and character.rigid.sensor is False


def test_aliases_point_to_same_class():
    assert pc.GameObject is pc.Entity and pc.NewGameObject is pc.Entity
    assert pc.World is pc.Scene


def test_size_decides_shape():
    circle = pc.Character(size=12)
    box = pc.Character(size=(20, 10))
    poly = pc.Character(size=[[0, 0], [10, 0], [0, 10]])
    assert circle.rigid.kind == "CIRCLE" and circle.rigid.shape.radius == 12
    assert box.rigid.kind == "BOX"
    assert poly.rigid.kind == "POLY"

    class Tile:
        x, y = 0, 0
        points = [(-4, -4), (4, -4), (4, 4), (-4, 4)]

    holder = pc.Wall(size=[Tile(), Tile()])
    assert holder.rigid is None and holder.tiles is not None and len(holder.tiles) == 2


def test_bad_size_raises_readable_error():
    with pytest.raises(TypeError):
        pc.Character(size="大")


def test_component_aliases():
    hero = pc.Character(FIXTURE, size=(16, 16))
    assert hero.visual is hero.sprite
    assert hero.rigid is hero.body
    assert hero.tiles is hero.tiledmap_bodies


# ------------------------------------------------------------------ 位置 / 速度语义
def test_pos_paths_and_speed_semantics():
    hero = pc.Character(size=(16, 16))
    hero.goto(100, 50)
    assert tuple(hero.pos) == (100.0, 50.0)

    hero.velocity = (99, 99)
    hero.pos = (0, 0)
    assert tuple(hero.pos) == (0.0, 0.0)
    assert tuple(hero.velocity) == (0.0, 0.0), "写 pos 视为瞬移，应清零速度"

    hero.velocity = (7, 3)
    hero.forward(5)
    assert tuple(hero.pos) == (5.0, 0.0), "forward 沿朝向走 5 像素"
    assert tuple(hero.velocity) == (7.0, 3.0), "forward 不清速度"
    hero.backward(5)
    assert tuple(hero.pos) == (0.0, 0.0)

    hero.velocity = (5, 5)
    hero.slide_to((40, 0), 2)
    assert tuple(hero.pos) == (2.0, 0.0), "slide_to 只走一步"
    assert tuple(hero.velocity) == (5.0, 5.0)


def test_x_y_setters_and_sync_pos():
    hero = pc.Character(size=(16, 16))
    hero.velocity = (9, 9)
    hero.x = 20
    assert hero.x == 20 and tuple(hero.velocity) == (0.0, 0.0)
    hero.velocity = (9, 9)
    hero.y = -30
    assert hero.y == -30 and tuple(hero.velocity) == (0.0, 0.0)

    hero.sync_pos((111, 222))  # 物理回写：只改显示缓存
    assert tuple(hero.pos) == (111.0, 222.0)


def test_rotation_direction_and_angle():
    hero = pc.Character(size=(16, 16))
    hero.rot = 30
    assert hero.rot == 30 and abs(hero.rigid.body.angle - 0.5236) < 1e-3

    hero.set_angle(0)
    assert abs(hero.angle) < 1e-6
    hero.dir = (1, 0)
    assert abs(hero.angle - 90.0) < 1e-6

    hero.goto(0, 0)
    hero.face_to(10, 0)
    assert abs(hero.dir[0] - 1.0) < 1e-6


def test_sync_rot_writes_cache_only():
    hero = pc.Character(size=(16, 16))
    hero.rot = 30
    hero.sync_rot(0)
    assert hero.rot == 0
    assert abs(hero.rigid.body.angle - 0.5236) < 1e-3, "物理回写不得反向写回刚体"


def test_scale_scales_visual_and_body():
    hero = pc.Character(FIXTURE, size=(32, 32))
    hero.scale(2)
    assert tuple(hero.scl) == (2.0, 2.0)
    assert hero.visual.scaled is True
    from pixelclass.physics.geometry import bounds_size

    width, height = bounds_size(hero.rigid.shape)
    assert abs(width - 64) < 1e-3 and abs(height - 64) < 1e-3


# ------------------------------------------------------------------ 缺失组件的中性行为
def test_missing_visual_gives_one_warning_and_neutral_values():
    hero = pc.Character(size=(16, 16))  # 只有刚体，没有贴图
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        hero.color = (10, 20, 30, 200)  # 不抛异常，只是被忽略
        assert hero.red is None
        assert hero.color is None
        assert hero.visible is False
        assert hero.width == 0 and hero.height == 0
        hero.flipx(True)
        hero.layer = 3
    assert len(caught) == 1, f"同一对象只应提示一次，实际 {len(caught)} 次"
    assert issubclass(caught[0].category, RuntimeWarning)
    assert "贴图" in str(caught[0].message)


def test_missing_body_gives_one_warning_and_neutral_values():
    hero = pc.Character(FIXTURE)  # 只有贴图，没有刚体
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        hero.velocity = (1, 2)
        assert hero.velocity is None
        assert hero.mass is None
        hero.apply_force(1, 2)
    assert len(caught) == 1
    assert "刚体" in str(caught[0].message)


def test_visual_works_when_present():
    hero = pc.Character(FIXTURE, size=(16, 16))
    assert hero.width == 64 and hero.height == 16
    hero.color = (10, 20, 30, 200)
    assert tuple(hero.color) == (10, 20, 30, 200)
    hero.hide()
    assert hero.visible is False
    hero.show()
    assert hero.visible is True
    hero.layer = 5
    assert hero.layer == 5
    hero.move_to_front()
    assert hero.layer == 5, "本来就在最前时保持不变"

    other = pc.Character(FIXTURE)
    other.layer = 9
    hero.move_to_front()
    assert hero.layer == 10, "应当排到最前"
    hero.move_to_back()
    assert hero.layer == 8, "应当排到最后"


# ------------------------------------------------------------------ 碰撞
def test_collide_point_and_object_via_rigid():
    hero = pc.Character(size=(20, 20))
    wall = pc.Wall(size=(40, 40))
    assert hero.collide((0.0, 0.0)) is True
    assert hero.collide((500.0, 500.0)) is False
    assert hero.collide(wall) is True
    wall.goto(300, 0)
    assert hero.collide(wall) is False


def test_collide_point_via_sprite_mask_when_no_body():
    hero = pc.Character(FIXTURE)  # 只有贴图
    hero.goto(0, 0)
    assert hero.collide((0.0, 0.0)) is True, "贴图内部应当命中"
    assert hero.collide((200.0, 0.0)) is False


def test_separate_coincident_objects_stay_put():
    hero = pc.Character(size=(20, 20))
    wall = pc.Wall(size=(40, 40))
    hero.goto(0, 0)
    wall.goto(0, 0)
    hero.separate(wall)
    assert tuple(hero.pos) == (0.0, 0.0), "完全重合时方向不定，按规格保持不动"


def test_separate_pushes_dynamic_object_apart():
    hero = pc.Character(size=(20, 20))
    wall = pc.Wall(size=(20, 20))
    hero.goto(0, 0)
    wall.goto(6, 0)
    hero.separate(wall)
    assert hero.pos[0] < 0, "重叠时动态对象应沿中心连线被推开"


# ------------------------------------------------------------------ 生命周期
def test_kill_clears_slots_and_calls_hook():
    calls = []

    class Custom(pc.Entity):
        def _on_kill(self):
            calls.append("hook")

    hero = Custom(FIXTURE, size=(16, 16))
    hero.kill()
    assert calls == ["hook"]
    assert hero.alive is False
    assert hero.visual is None and hero.rigid is None and hero.tiles is None
    assert hero not in list(resolve_world().entities)
    hero.kill()  # 重复销毁必须安全
    assert hero.alive is False


def test_update_hook_and_internal_update():
    log = []

    class Custom(pc.Entity):
        def update(self):
            log.append("public")

        def _on_kill(self):
            pass

    hero = Custom(FIXTURE)
    hero._update()
    hero.update()
    assert log == ["public"]
    assert hero._just_released is False


def test_mouse_follows_mouse_position():
    mouse = pc.Mouse()
    mouse._update()
    assert tuple(mouse.pos) == pc.get_mouse_pos(mouse.world), "Mouse 每帧跟随鼠标"


def test_set_world_moves_entity_between_scenes():
    first = pc.Scene()
    second = pc.Scene()
    pc.setup(320, 240, world=first)
    pc.setup(320, 240, world=second)
    hero = pc.Character(size=(16, 16), world=first)
    assert hero in list(first.entities)
    hero.set_world(second)
    assert hero.world is second
    assert hero in list(second.entities) and hero not in list(first.entities)
