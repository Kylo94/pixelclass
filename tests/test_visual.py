"""视觉与动画测试：变换缓存、图层绘制、帧序列、状态机、图集（spec 04）。"""

import os
import warnings

import pygame
import pytest

import pixelclass as pc
from pixelclass.clock import Clock
from pixelclass.visual import AnimatorStrategy, ListSpriteStrategy, SpriteSheet, TiledMapStrategy

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "acceptance", "fixtures")
TILES = os.path.join(FIXTURES, "tiles.png")
LEVEL = os.path.join(FIXTURES, "level.tmx")


@pytest.fixture(autouse=True)
def _fresh_scene():
    scene = pc.setup(320, 240)
    scene.clock = Clock(ticker=lambda: 17)
    yield scene


def _surface(color=(255, 0, 0), size=(16, 16)):
    surface = pygame.Surface(size, pygame.SRCALPHA)
    surface.fill(color)
    return surface


# ------------------------------------------------------------------ 变换缓存
def test_moving_does_not_recompute_transformed_image(monkeypatch, _fresh_scene):
    calls = []
    original = pygame.transform.rotate

    def counting_rotate(image, angle):
        calls.append(angle)
        return original(image, angle)

    monkeypatch.setattr(pygame.transform, "rotate", counting_rotate)
    hero = pc.Character(_surface(), size=(16, 16))
    pc.update()
    assert calls == [], "只改位置不应重算图像"

    hero.rot = 30
    pc.update()
    assert len(calls) == 1, "旋转后应当重算一次"
    pc.update()
    assert len(calls) == 1, "标记复位后不应再重算"


def test_scale_flip_and_color_update_display_image(_fresh_scene):
    hero = pc.Character(_surface(), size=(16, 16))
    hero.scale(2)
    pc.update()
    assert (hero.width, hero.height) == (32, 32)

    hero.flipx(True)
    pc.update()
    assert hero.visual.fliped is False, "重算后标记应当复位"

    hero.color = (128, 128, 128, 255)
    pc.update()
    assert hero.visual.modified is False


def test_scaled_sprite_is_not_rescaled_every_frame(monkeypatch, _fresh_scene):
    """被缩放的贴图不能每帧都重算图像（缩放是重活，spec 04 §1.3）。"""
    calls = []
    original = pygame.transform.scale

    def counting_scale(image, size):
        calls.append(size)
        return original(image, size)

    monkeypatch.setattr(pygame.transform, "scale", counting_scale)
    hero = pc.Character(_surface())
    hero.scale(0.5)
    pc.update()
    assert len(calls) == 1, "缩放后应当重算一次"
    for _ in range(5):
        pc.update()
    assert len(calls) == 1, "缩放没变就不该再重算（以前是每帧都重算）"

    hero.scale(0.25)
    pc.update()
    assert len(calls) == 2, "缩放真的变了才重算"


def test_animation_frame_change_is_visible(_fresh_scene):
    """换帧后**画面**必须跟着换：只涨 frame 索引不算数。"""
    frames = [_surface((255, 0, 0)), _surface((0, 0, 255))]
    hero = pc.Character(frames)
    hero.goto(0, 0)
    hero.dt = 0.01
    colors = []
    for _ in range(4):
        pc.update()
        image = hero.visual.display_image()
        colors.append(tuple(image.get_at((image.get_width() // 2, image.get_height() // 2)))[:3])
    assert len(set(colors)) > 1, f"动画在画面上冻住了：{colors}"
    assert colors[0] != colors[-1]


def test_manual_frame_write_stops_the_auto_advance(_fresh_scene):
    """课堂写法：每帧写一次 `frame` 切换两张图（卡片"可买 / 置灰"）——不能被自动播放打断。

    真实案例：植物大战僵尸的卡槽卡片每帧写 `self.frame = sun_point < self.coin`，
    而两张图的序列同时在自动播放，于是卡片每隔约 4~5 帧闪一次灰图。
    """

    class Card(pc.Character):
        manual = True

        def update(self):
            if self.manual:
                self.frame = 0  # 等同于 demo 里的 change_card()

    card = Card([_surface((255, 0, 0)), _surface((0, 0, 255))])
    card.dt = 0.01
    pixels = set()
    for _ in range(12):
        pc.update()
        image = card.visual.display_image()
        pixels.add(tuple(image.get_at((8, 8)))[:3])
    assert pixels == {(255, 0, 0)}, f"卡片在频闪：{pixels}"
    assert card.frame == 0
    assert card.visual.playing is False, "手动写 frame 等于接管播放"

    # 不再每帧写 frame 之后，play_anim() 能恢复自动播放
    card.manual = False
    card.play_anim()
    seen = set()
    for _ in range(6):
        pc.update()
        image = card.visual.display_image()
        seen.add(tuple(image.get_at((8, 8)))[:3])
    assert len(seen) > 1, "play_anim() 之后应当继续自动播放"


def test_manual_frame_seek_then_play_resumes_from_there(_fresh_scene):
    hero = pc.Character([_surface((255, 0, 0)), _surface((0, 0, 255)), _surface((0, 255, 0))])
    hero.dt = 0.01
    hero.frame = 2
    assert hero.frame == 2 and hero.visual.playing is False
    pc.update()
    assert hero.frame == 2, "手动指定的帧不会被自动播放顶掉"

    hero.play_anim()
    seen = set()
    for _ in range(6):
        pc.update()
        seen.add(hero.frame)
    assert len(seen) > 1, "play_anim() 后从第 2 帧继续播"


def test_alpha_survives_recompute_on_scaled_sprite(_fresh_scene):
    """虚影（缩放 + 半透明）不能画着画着变回不透明。

    真实案例：植物大战僵尸示例里 `shadow.alpha = 128` + `shadow.scale(0.8)`，
    前一版只在 modified 那一次贴透明度，而缩放贴图每帧都会重算，
    于是第二帧起虚影就是完全不透明的。
    """
    hero = pc.Character(_surface((255, 0, 0)))
    hero.scale(0.8)
    hero.alpha = 128
    for _ in range(5):
        pc.update()
        image = hero.visual.display_image()
        biggest = max(
            image.get_at((x, y)).a for x in range(image.get_width()) for y in range(image.get_height())
        )
        assert biggest <= 130, f"透明度丢了：最大 alpha = {biggest}"


def test_color_accepts_three_or_four_elements(_fresh_scene):
    hero = pc.Character(_surface())
    hero.color = (10, 20, 30)
    assert hero.color == (10, 20, 30, 255), "三元素只改颜色，保留透明度"

    hero.alpha = 200
    hero.color = (1, 2, 3)
    assert hero.color == (1, 2, 3, 200), "三元素不该把透明度重置"

    hero.color = (4, 5, 6, 7)
    assert hero.color == (4, 5, 6, 7)

    with pytest.raises(ValueError):
        hero.color = (1, 2)


# ------------------------------------------------------------------ 绘制与图层
def test_draw_paints_visible_sprites_with_layer_order(_fresh_scene):
    low = pc.Character(_surface((255, 0, 0)), size=(32, 32))
    high = pc.Character(_surface((0, 0, 255)), size=(32, 32))
    low.goto(0, 0)
    high.goto(0, 0)
    low.layer = 0
    high.layer = 1
    pc.update()
    surface = pygame.display.get_surface()
    pixel = surface.get_at((160, 120))[:3]
    assert pixel == (0, 0, 255), f"图层大的应当画在上面，实际 {pixel}"

    high.move_to_back()
    pc.update()
    pixel = pygame.display.get_surface().get_at((160, 120))[:3]
    assert pixel == (255, 0, 0), f"换到后面后应当被覆盖，实际 {pixel}"


def test_hidden_sprite_is_not_drawn(_fresh_scene):
    hero = pc.Character(_surface((255, 0, 0)), size=(32, 32))
    hero.goto(0, 0)
    hero.hide()
    pc.update()
    assert pygame.display.get_surface().get_at((160, 120))[:3] == (0, 0, 0)


def test_bgpic_sets_camera_size_and_returns_object(_fresh_scene):
    background = pc.bgpic(TILES)
    assert background.visual is not None
    assert _fresh_scene.camera.size == (background.width, background.height)
    background.kill()
    assert background.alive is False


def test_save_screen_writes_a_file(tmp_path, _fresh_scene):
    hero = pc.Character(_surface((255, 0, 0)), size=(16, 16))
    hero.goto(0, 0)
    pc.update()
    path = os.path.join(str(tmp_path), "shot.png")
    pc.save_screen(path)
    assert os.path.isfile(path) and os.path.getsize(path) > 0


# ------------------------------------------------------------------ 帧序列
def test_frame_list_animation_loops(_fresh_scene):
    frames = [_surface((255, 0, 0)), _surface((0, 255, 0))]
    hero = pc.Character(frames)
    hero.dt = 0.1
    hero.goto(0, 0)
    assert hero.frame == 0

    for _ in range(6):  # 6 × 17ms ≈ 0.1s
        pc.update()
    assert hero.frame == 1

    for _ in range(6):
        pc.update()
    assert hero.frame == 0, "播完应当回到第一帧"


def test_single_image_never_advances(_fresh_scene):
    hero = pc.Character(_surface())
    assert hero.frame == 0
    for _ in range(10):
        pc.update()
    assert hero.frame == 0
    assert hero.visual.strategy.frame_count == 1


# ------------------------------------------------------------------ 播放控制
def test_pause_play_and_stop(_fresh_scene):
    frames = [_surface((255, 0, 0)), _surface((0, 255, 0))]
    hero = pc.Character(frames)
    hero.dt = 0.05
    hero.goto(0, 0)
    assert hero.is_anim_playing() is True, "新对象默认就在播放"

    for _ in range(4):  # 4 × 17ms ≈ 0.068s > 0.05s：推进一帧
        pc.update()
    assert hero.frame == 1

    hero.pause_anim()
    assert hero.is_anim_playing() is False
    for _ in range(10):
        pc.update()
    assert hero.frame == 1, "暂停后帧不再推进"

    hero.play_anim()
    assert hero.is_anim_playing() is True
    for _ in range(4):
        pc.update()
    assert hero.frame == 0, "play 应当从当前帧继续（上一帧是 1），而不是跳帧"


def test_stop_anim_rewinds_to_first_frame(_fresh_scene):
    frames = [_surface((255, 0, 0)), _surface((0, 255, 0)), _surface((0, 0, 255))]
    hero = pc.Character(frames)
    hero.dt = 0.01
    hero.goto(0, 0)
    for _ in range(5):
        pc.update()
    assert hero.frame != 0

    hero.stop_anim()
    assert hero.frame == 0
    assert hero.is_anim_playing() is False
    for _ in range(5):
        pc.update()
    assert hero.frame == 0, "stop 之后应当保持暂停"


def test_playback_controls_do_not_touch_position_or_drawing(_fresh_scene):
    hero = pc.Character(_surface())
    hero.goto(10, 20)
    hero.pause_anim()
    hero.goto(30, 40)
    pc.update()
    assert tuple(hero.pos) == (30, 40), "暂停只冻结帧推进"
    assert hero.visible is True


def test_playback_controls_on_single_image_and_state_machine(_fresh_scene):
    flat = pc.Character(_surface())
    assert flat.is_anim_playing() is True
    flat.pause_anim()
    flat.stop_anim()
    assert flat.frame == 0 and flat.is_anim_playing() is False, "单图对象上不报错"
    flat.play_anim()
    assert flat.is_anim_playing() is True

    machine = pc.Character({"idle": [_surface((255, 0, 0))], "walk": [_surface((0, 255, 0))]})
    machine.pause_anim()
    machine.state = "walk"
    for _ in range(3):
        pc.update()
    assert machine.state == "idle", "暂停时状态切换也冻结"
    machine.play_anim()
    pc.update()
    assert machine.state == "walk", "恢复播放后，暂停期间赋的状态才生效"
    machine.stop_anim()
    assert machine.frame == 0 and machine.is_anim_playing() is False


def test_set_dt_on_frame_list(_fresh_scene):
    frames = [_surface((255, 0, 0)), _surface((0, 255, 0))]
    hero = pc.Character(frames)
    hero.goto(0, 0)
    hero.set_dt(0.5)
    assert hero.dt == pytest.approx(0.5)

    for _ in range(20):  # 20 × 17ms ≈ 0.34s < 0.5s：还不到换帧
        pc.update()
    assert hero.frame == 0

    hero.set_dt(0.01)
    for _ in range(3):
        pc.update()
    assert hero.frame != 0, "改小 dt 后立刻生效"


def test_set_dt_per_state_on_state_machine(_fresh_scene):
    machine = pc.Character({"idle": [_surface(), _surface()], "walk": [_surface(), _surface()]})
    machine.goto(0, 0)
    default = machine.dt

    machine.set_dt("walk", 0.5)
    assert machine.dt == pytest.approx(default), "当前是 idle，不受影响"
    assert machine.visual.strategy.states["walk"].dt == pytest.approx(0.5)

    machine.state = "walk"
    pc.update()  # 切换状态
    assert machine.dt == pytest.approx(0.5)
    for _ in range(10):
        pc.update()
    assert machine.frame == 0, "walk 变慢了，还没换帧"

    machine.set_dt(0.02)  # 只给一个数值 = 所有状态
    assert machine.visual.strategy.states["idle"].dt == pytest.approx(0.02)
    assert machine.visual.strategy.states["walk"].dt == pytest.approx(0.02)

    machine.stop_anim()  # 回到第 0 帧、清零帧计时，便于观察新 dt
    machine.play_anim()
    for _ in range(4):
        pc.update()
    assert machine.frame != 0, "改小 dt 后立刻变快"


def test_set_dt_rejects_bad_state_and_bad_values(_fresh_scene):
    machine = pc.Character({"idle": [_surface()], "walk": [_surface()]})
    with pytest.raises(ValueError) as error:
        machine.set_dt("run", 0.1)
    assert "idle" in str(error.value), "错误里要列出可用状态"

    frames = [_surface(), _surface()]
    plain = pc.Character(frames)
    with pytest.raises(TypeError):
        plain.set_dt("walk", 0.1)  # 帧序列不需要动画名字

    for bad in (0, -0.5, "快一点", None):
        with pytest.raises((TypeError, ValueError)):
            plain.set_dt(bad)
    with pytest.raises((TypeError, ValueError)):
        plain.dt = 0


def test_missing_visual_set_dt_is_neutral():
    hero = pc.Character(size=(16, 16))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        hero.set_dt(0.1)
    assert len(caught) == 1, "同一对象只提示一次"


def test_missing_visual_playback_controls_are_neutral():
    hero = pc.Character(size=(16, 16))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        hero.play_anim()
        hero.pause_anim()
        hero.stop_anim()
        assert hero.is_anim_playing() is False
    assert len(caught) == 1, "同一对象只提示一次"


# ------------------------------------------------------------------ 状态机
def test_state_machine_switches_on_next_frame(_fresh_scene):
    hero = pc.Character({"idle": [_surface((255, 0, 0))], "walk": [_surface((0, 255, 0))]})
    hero.goto(0, 0)
    assert hero.state == "idle"
    hero.state = "walk"
    assert hero.state == "idle", "写状态应当下一帧生效"

    pc.update()
    assert hero.state == "walk"
    assert hero.visual.strategy.frame == 0


def test_state_machine_rejects_unknown_state(_fresh_scene):
    hero = pc.Character({"idle": [_surface()]})
    with pytest.raises(ValueError) as error:
        hero.state = "fly"
    assert "fly" in str(error.value)


def test_state_machine_next_state_and_callbacks(_fresh_scene):
    started, ended = [], []
    hero = pc.Character(
        {"idle": [_surface((255, 0, 0)), _surface((200, 0, 0))], "walk": [_surface((0, 255, 0))]}
    )
    hero.dt = 0.01
    hero.set_next_state("walk")
    hero.set_start_func(lambda strategy: started.append(strategy.state))
    hero.set_end_func(lambda strategy: ended.append(strategy.state))
    for _ in range(10):
        pc.update()
    assert hero.state == "walk"
    assert started == ["walk"] and ended == ["idle"], (started, ended)


def test_set_next_state_on_plain_sprite_raises(_fresh_scene):
    hero = pc.Character(_surface())
    with pytest.raises(TypeError):
        hero.set_next_state("walk")


# ------------------------------------------------------------------ 策略与图集
def test_sprite_sheet_slices_frames(_fresh_scene):
    sheet = SpriteSheet(TILES, 16, 16)
    frames = sheet.frames()
    assert len(frames) == 4, "图集是 4 个 16×16 的色块"
    assert all(frame.get_size() == (16, 16) for frame in frames)
    hero = pc.Character(sheet)
    assert isinstance(hero.visual.strategy, ListSpriteStrategy)
    assert hero.visual.strategy.frame_count == 4


def test_tiledmap_strategy_bakes_the_map(_fresh_scene):
    tiled = pc.TiledMap(LEVEL)
    hero = pc.Character(tiled)
    assert isinstance(hero.visual.strategy, TiledMapStrategy)
    assert (hero.width, hero.height) == (tiled.width, tiled.height)


def test_state_dict_strategy_type(_fresh_scene):
    hero = pc.Character({"a": [_surface()], "b": [_surface()]})
    assert isinstance(hero.visual.strategy, AnimatorStrategy)


def test_missing_visual_animation_proxies_are_neutral():
    hero = pc.Character(size=(16, 16))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert hero.frame == 0 and hero.state == "" and hero.dt == 0.0
        hero.frame = 3
        hero.state = "walk"
    assert len(caught) == 1, "同一对象只提示一次"
