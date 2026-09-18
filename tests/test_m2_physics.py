"""M2 测试：刚体形状与属性、宽相重排规则、点查询与碰撞、瓦片刚体组（spec 03）。"""

import pymunk
import pytest

import pixelclass as pc
from pixelclass.physics import Body, TiledMapBodies
from pixelclass.vec import vec


class _Host:
    """最小宿主：验证"物理 -> 显示"只写显示缓存。"""

    def __init__(self, pos=(0, 0)):
        self._pos = vec(pos)
        self._rot = 0.0
        self.sync_calls = 0

    @property
    def pos(self):
        return self._pos

    def sync_pos(self, value):
        self._pos = vec(value)
        self.sync_calls += 1

    def sync_rot(self, value):
        self._rot = float(value)


class _Tile:
    """最小瓦片对象：只有顶点与坐标（模拟 TMX 对象层的解析结果）。"""

    def __init__(self, x, y, half=8):
        self.x = x
        self.y = y
        self.points = [(-half, -half), (-half, half), (half, -half), (half, half)]


@pytest.fixture(autouse=True)
def _fresh_scene():
    pc.setup(320, 240)
    yield


# ------------------------------------------------------------------ 形状与属性
def test_shape_kinds_and_body_types():
    circle = Body("DYNAMIC", "CIRCLE", size=10)
    assert circle.shape.radius == 10
    assert circle.body.mass > 0 and circle.body.moment > 0, "动态刚体必须有质量与转动惯量"

    box = Body("STATIC", "BOX", size=(20, 30))
    assert abs(box.shape.area - 600) < 1e-6

    poly = Body("KINEMATIC", "POLY", size=[[0, 0], [10, 0], [0, 10]])
    assert len(poly.shape.get_vertices()) == 3
    assert abs(poly.shape.area - 50) < 1e-6

    assert Body(pymunk.Body.DYNAMIC, "CIRCLE", size=5).body_type == pymunk.Body.DYNAMIC


def test_bad_shape_or_type_raises_readable_error():
    with pytest.raises(ValueError):
        Body("DYNAMIC", "TRIANGLE", size=(1, 2))
    with pytest.raises(ValueError):
        Body("NOPE", "CIRCLE", size=5)
    with pytest.raises(ValueError):
        Body("DYNAMIC", "CIRCLE", size=0)
    with pytest.raises(ValueError):
        Body("DYNAMIC", "POLY", size=[[0, 0], [1, 1]])


def test_property_proxies():
    body = Body("DYNAMIC", "BOX", size=(10, 10))
    body.velocity = (3, 4)
    assert tuple(body.body.velocity) == (3.0, 4.0)
    body.angular_velocity = 2.5
    assert body.angular_velocity == 2.5
    body.friction = 0.7
    body.elasticity = 0.3
    assert body.shape.friction == 0.7 and body.shape.elasticity == 0.3
    assert body.sensor is False
    body.sensor = True
    assert body.shape.sensor is True


# ------------------------------------------------------------------ "没变就不重排"
def test_set_pos_and_rot_skip_reindex_when_unchanged():
    scene = pc.global_var
    body = Body("STATIC", "BOX", size=(10, 10))
    calls = []
    original = scene.space.reindex_shapes_for_body
    scene.space.reindex_shapes_for_body = lambda b: calls.append(b)
    try:
        body.set_pos((0, 0))  # 与初始位置相同
        assert calls == [], "位置没变不应触发宽相重排"
        body.set_pos((5, 0))
        assert len(calls) == 1
        body.set_pos((5, 0))
        assert len(calls) == 1, "重复写同一位置也不应重排"
        body.set_rot(0)
        assert len(calls) == 1, "角度没变不应重排"
        body.set_rot(90)
        assert len(calls) == 2
    finally:
        scene.space.reindex_shapes_for_body = original


# ------------------------------------------------------------------ 查询与碰撞
def test_point_query_hit_and_miss():
    box = Body("STATIC", "BOX", size=(20, 20))
    box.set_pos((0, 0))
    assert box.point_query((0, 0)) is True
    assert box.point_query((9.9, 0)) is True
    assert box.point_query((100, 100)) is False

    circle = Body("STATIC", "CIRCLE", size=10)
    circle.set_pos((0, 0))
    assert circle.point_query((5, 0)) is True
    assert circle.point_query((15, 0)) is False


def test_collision_covers_four_geometry_combos():
    circle = Body("STATIC", "CIRCLE", size=10)
    circle.set_pos((0, 0))
    other_circle = Body("STATIC", "CIRCLE", size=10)
    other_circle.set_pos((15, 0))
    assert circle.collide(other_circle) is True  # 圆-圆
    other_circle.set_pos((100, 0))
    assert circle.collide(other_circle) is False

    box = Body("STATIC", "BOX", size=(10, 10))
    box.set_pos((0, 0))
    assert circle.collide(box) is True  # 圆-盒

    box2 = Body("STATIC", "BOX", size=(10, 10))
    box2.set_pos((0, 0))
    assert box.collide(box2) is True  # 盒-盒

    poly = Body("STATIC", "POLY", size=[[-10, -10], [10, -10], [0, 10]])
    poly.set_pos((0, 0))
    assert box.collide(poly) is True  # 多边形参与
    poly.set_pos((200, 200))
    assert box.collide(poly) is False


# ------------------------------------------------------------------ 显示同步
def test_sync_writes_display_cache_only():
    host = _Host((10, 20))
    body = Body("DYNAMIC", "BOX", size=(10, 10))
    body.set_parent(host)
    assert tuple(body.body.position) == (10.0, 20.0), "挂到宿主时应当摆到宿主位置"

    body.body.position = (30, 40)
    body.sync()
    assert host.sync_calls == 1
    assert tuple(host._pos) == (30.0, 40.0)
    assert tuple(body.body.position) == (30.0, 40.0), "同步不得反向写回刚体"


def test_scene_sync_display_covers_rigids():
    host = _Host((0, 0))
    body = Body("DYNAMIC", "BOX", size=(10, 10))
    body.set_parent(host)
    body.body.position = (7, 8)
    pc.global_var.sync_display()
    assert tuple(host._pos) == (7.0, 8.0)


def test_kill_removes_from_space_and_scene():
    scene = pc.global_var
    body = Body("DYNAMIC", "BOX", size=(10, 10))
    assert len(scene.rigids) == 1
    assert body.body in scene.space.bodies
    body.kill()
    assert len(scene.rigids) == 0
    assert body.body not in scene.space.bodies


# ------------------------------------------------------------------ 重力与类型
def test_static_ignores_gravity_dynamic_falls():
    pc.set_gravity(0, -1200)
    static = Body("STATIC", "BOX", size=(20, 10))
    static.set_pos((0, 0))
    dynamic = Body("DYNAMIC", "BOX", size=(20, 10))
    dynamic.set_pos((0, 50))
    for _ in range(30):
        pc.update()
    assert tuple(static.body.position) == (0.0, 0.0), "静态刚体不受重力影响"
    assert dynamic.body.position.y < 50, "动态刚体应当下落"


# ------------------------------------------------------------------ 瓦片刚体组
def test_tiles_are_placed_by_their_own_offsets():
    tiles = [_Tile(i * 32, j * 32) for i in range(3) for j in range(3)]
    holder = _Host((100, 0))
    group = TiledMapBodies("STATIC", tiles, world=pc.global_var)
    group.set_parent(holder)

    assert len(group) == 9
    for tile in tiles:
        expected = (100 + tile.x, tile.y)
        assert group.point_query(expected) is True, expected
    assert group.point_query((-200, -200)) is False


def test_tile_group_moves_as_a_whole():
    tiles = [_Tile(0, 0), _Tile(32, 0)]
    group = TiledMapBodies("STATIC", tiles, world=pc.global_var)
    group.set_pos((10, 20))
    assert group.point_query((10, 20)) is True
    assert group.point_query((42, 20)) is True  # 第二块按偏移摆好
    group.set_pos((0, 0))
    assert group.point_query((10, 20)) is False
    assert group.point_query((32, 0)) is True


def test_tile_group_sync_writes_group_position():
    host = _Host((5, 5))
    group = TiledMapBodies("STATIC", [_Tile(0, 0)], world=pc.global_var)
    group.set_parent(host)
    host._pos = vec(0, 0)
    group.set_pos((11, 22))
    group.sync()
    assert tuple(host._pos) == (11.0, 22.0)


def test_tile_neighbour_joints_far_fewer_than_pairwise():
    tiles = [_Tile(i * 32, j * 32) for i in range(5) for j in range(5)]
    group = TiledMapBodies("DYNAMIC", tiles, world=pc.global_var)
    pairwise = 25 * 24 // 2
    assert 0 < len(group.joints) <= 40, len(group.joints)
    assert len(group.joints) < pairwise / 4, "只连相邻，不两两连接"


def test_isolated_tile_is_not_connected():
    group = TiledMapBodies("DYNAMIC", [_Tile(0, 0), _Tile(500, 500)], world=pc.global_var)
    assert group.joints == [], "孤立瓦片不该被连进来"


def test_tile_kill_clears_everything():
    scene = pc.global_var
    group = TiledMapBodies("STATIC", [_Tile(0, 0), _Tile(32, 0)], world=scene)
    assert len(scene.tiles) == 1
    group.kill()
    assert len(group) == 0
    assert len(scene.tiles) == 0
    assert len(scene.space.shapes) == 0
