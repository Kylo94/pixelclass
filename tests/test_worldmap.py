"""地图模块测试：载入、坐标换算只做一次、对象层 → 实体、渲染（spec 05）。"""

import os

import pygame
import pytest

import pixelclass as pc

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "acceptance", "fixtures")
LEVEL = os.path.join(FIXTURES, "level.tmx")
TILES = os.path.join(FIXTURES, "tiles.png")

EXPECTED = [
    ("spawn", -120.0, -56.0, False),
    ("ground_body", 0.0, -104.0, False),
    ("platform_a", -64.0, -8.0, False),
    ("platform_b", 64.0, 8.0, False),
    ("coin_a", -72.0, 24.0, True),
    ("coin_b", 56.0, 40.0, True),
]


@pytest.fixture(autouse=True)
def _fresh_scene():
    pc.setup(320, 240)
    yield


def test_loading_before_setup_gives_readable_error():
    pygame.display.quit()
    try:
        with pytest.raises(RuntimeError) as error:
            pc.TiledMap(LEVEL)
        assert "setup" in str(error.value)
    finally:
        pc.setup(320, 240)


def test_missing_file_raises_readable_error():
    with pytest.raises(FileNotFoundError) as error:
        pc.TiledMap(os.path.join(FIXTURES, "nope.tmx"))
    assert "nope.tmx" in str(error.value)


def test_map_size_and_objects_are_idempotent():
    tiled = pc.TiledMap(LEVEL)
    assert (tiled.width, tiled.height) == (320, 192)
    first = [(item.name, round(item.x, 2), round(item.y, 2)) for item in tiled.objects]
    second = [(item.name, round(item.x, 2), round(item.y, 2)) for item in tiled.objects]
    assert first == second, "反复读取对象坐标不得再次叠加偏移"
    assert first == [(name, x, y) for name, x, y, _ in EXPECTED]


def test_get_objects_filtering():
    tiled = pc.TiledMap(LEVEL)
    assert len(tiled.get_objects()) == 6
    assert [item.name for item in tiled.get_objects("spawn")] == ["spawn"]
    assert tiled.get_objects("nope") == []


def test_create_objects_makes_one_entity_per_object():
    tiled = pc.TiledMap(LEVEL)
    created = tiled.create_objects()
    assert len(created) == 6
    for entity, (name, x, y, has_visual) in zip(created, EXPECTED):
        assert entity.name == name
        assert (round(entity.pos[0], 2), round(entity.pos[1], 2)) == (x, y)
        assert entity.rigid is not None, f"{name} 应有刚体"
        assert entity.tiles is None, f"{name} 不应是瓦片刚体组"
        assert (entity.visual is not None) is has_visual
        assert entity.properties == {} and entity.tmx_object is not None


def test_create_objects_can_filter_by_name_and_take_body_type():
    tiled = pc.TiledMap(LEVEL)
    created = tiled.create_objects(name="coin_a", body_type="KINEMATIC")
    assert len(created) == 1 and created[0].name == "coin_a"
    assert created[0].rigid.body_type == pc.physics.BODY_TYPES["KINEMATIC"]


def test_create_objects_accepts_images_mapping():
    tiled = pc.TiledMap(LEVEL)
    surface = pygame.image.load(TILES)
    created = tiled.create_objects(name="spawn", images={"spawn": surface})
    assert created[0].visual is not None, "给了 images 映射就应当有贴图"


def test_each_object_geometry_hits_its_own_center():
    tiled = pc.TiledMap(LEVEL)
    for entity in tiled.create_objects():
        assert entity.collide((entity.pos[0], entity.pos[1])) is True, entity.name
        assert entity.collide((entity.pos[0] + 500, entity.pos[1])) is False, entity.name


def test_tile_objects_get_a_tile_image():
    tiled = pc.TiledMap(LEVEL)
    coin = tiled.get_objects("coin_a")[0]
    image = tiled.tile_image(coin.gid)
    assert image is not None and image.get_size() == (16, 16)


def test_render_draws_tiles():
    tiled = pc.TiledMap(LEVEL)
    surface = pygame.Surface((tiled.width, tiled.height))
    surface.fill((0, 0, 0))
    tiled.render(surface)
    drawn = sum(
        1
        for y in range(0, tiled.height, 4)
        for x in range(0, tiled.width, 4)
        if surface.get_at((x, y))[:3] != (0, 0, 0)
    )
    assert drawn > 0, "地面层应当画出边框图块"


def test_map_can_be_used_as_a_sprite_source():
    tiled = pc.TiledMap(LEVEL)
    holder = pc.Character(tiled)
    assert holder.visual is not None
    assert (holder.width, holder.height) == (tiled.width, tiled.height)
