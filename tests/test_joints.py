"""约束测试：销钉与弹簧、参数接受实体或裸刚体、关节进入正确的空间（spec 03 §6）。"""

import pytest

import pixelclass as pc
from pixelclass.physics import Body
from pixelclass.physics.joints import Connect, Spring, connect

FIXTURE = "acceptance/fixtures/tiles.png"


@pytest.fixture(autouse=True)
def _fresh_scene():
    scene = pc.setup(320, 240)
    pc.set_gravity(0, 0)
    return scene


def _pair(scene=None):
    first = pc.Character(size=(16, 16), world=scene)
    second = pc.Character(size=(16, 16), world=scene)
    first.goto(0, 0)
    second.goto(50, 0)
    return first, second


def test_connect_adds_pin_joint_to_scene_space():
    first, second = _pair()
    joint = connect(first, second)
    assert isinstance(joint, Connect)
    assert joint in pc.global_var.space.constraints


def test_connect_keeps_the_distance():
    first, second = _pair()
    connect(first, second)
    second.velocity = (0, 120)
    for _ in range(20):
        pc.update()
    assert (second.pos - first.pos).length() == pytest.approx(50.0, abs=0.5)


def test_connect_accepts_raw_bodies():
    scene = pc.global_var
    first = Body("DYNAMIC", "BOX", size=(16, 16), sensor=False, world=scene)
    second = Body("DYNAMIC", "BOX", size=(16, 16), sensor=False, world=scene)
    first.set_pos((0, 0))
    second.set_pos((40, 0))
    joint = connect(first, second, world=scene)
    assert joint in scene.space.constraints


def test_connect_rejects_entity_without_body():
    sprite_only = pc.Character(FIXTURE)
    other = pc.Character(size=(16, 16))
    with pytest.raises(TypeError) as error:
        connect(sprite_only, other)
    message = str(error.value)
    assert "刚体" in message and "size" in message


def test_connect_rejects_wrong_type():
    with pytest.raises(TypeError):
        connect(object(), pc.Character(size=(16, 16)))


def test_spring_default_rest_length_is_current_distance():
    first, second = _pair()
    spring = Spring(first, second)
    assert spring.rest_length == pytest.approx(50.0)


def test_spring_pulls_back_to_rest_length():
    scene = pc.global_var
    first, second = _pair()
    spring = Spring(first, second, rest_length=50.0)
    # 把第二个物体拉远，弹簧应当把它拉回来
    second.pos = (140, 0)
    for _ in range(60):
        pc.update()
    distance = (second.pos - first.pos).length()
    assert distance < 140.0, distance
    assert spring in scene.space.constraints


def test_joint_uses_explicit_world_when_given():
    other_scene = pc.Scene()
    pc.setup(320, 240, world=other_scene)
    first = pc.Character(size=(16, 16), world=other_scene)
    second = pc.Character(size=(16, 16), world=other_scene)
    joint = connect(first, second, world=other_scene)
    assert joint in other_scene.space.constraints
    assert joint not in pc.global_var.space.constraints
