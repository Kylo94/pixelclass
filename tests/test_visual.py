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
