"""M5a 测试：输入事件、文本与对话框、资源缓存、场景级工具（spec 06 / 07）。"""

import os
import warnings

import pygame
import pytest

import pixelclass as pc
from pixelclass import input as input_state
from pixelclass.clock import Clock

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "acceptance", "fixtures")
TILES = os.path.join(FIXTURES, "tiles.png")


@pytest.fixture(autouse=True)
def _fresh_scene():
    scene = pc.setup(320, 240)
    scene.clock = Clock(ticker=lambda: 17)
    state = input_state.get_input_state()
    state["keys_held"].clear()
    state["keys_just_pressed"].clear()
    state["keys_just_released"].clear()
    state["text_buffer"] = ""
    state["text_done"] = False
    state["mouse_held"] = False
    state["mouse_just_pressed"] = False
    state["mouse_just_released"] = False
    state["quit"] = False  # 关窗标记也要复位，否则会污染后面的测试
    pygame.event.clear()
    yield scene


# ------------------------------------------------------------------ 鼠标 / 键盘
def test_mouse_button_state_across_frames():
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)))
    input_state.process_events()
    assert pc.get_mouse_clicked() is True
    assert pc.get_mouse_just_clicked() is True

    input_state.process_events()  # 没有新事件：只按住的标记保留
    assert pc.get_mouse_clicked() is True
    assert pc.get_mouse_just_clicked() is False, "刚按下只应在一帧内为真"

    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(0, 0)))
    input_state.process_events()
    assert pc.get_mouse_clicked() is False
    assert pc.get_mouse_just_released() is True


def test_keyboard_state_and_any_key():
    assert pc.key_pressed() is False
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="a"))
    input_state.process_events()
    assert pc.key_pressed(pygame.K_a) is True
    assert pc.key_pressed() is True, "不传键表示任意键按住"
    assert pc.key_just_pressed(pygame.K_a) is True

    input_state.process_events()
    assert pc.key_pressed(pygame.K_a) is True
    assert pc.key_just_pressed(pygame.K_a) is False

    pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_a))
    input_state.process_events()
    assert pc.key_pressed(pygame.K_a) is False
    assert pc.key_just_released(pygame.K_a) is True


def test_text_input_flow():
    assert pc.key_input() == ""
    for char in "abc":
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode=char))
    input_state.process_events()
    assert pc.key_input() == "abc"
    assert pc.text_input_done() is False

    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, unicode=""))
    input_state.process_events()
    assert pc.key_input() == "ab", "退格应当删掉一个字符"

    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r"))
    input_state.process_events()
    assert pc.text_input_done() is True
    pc.text_input_reset()
    assert pc.key_input() == "" and pc.text_input_done() is False


def test_text_input_respects_max_length():
    pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text="abcdefghij"))
    input_state.process_events()
    assert pc.key_input(max_length=4) == "abcd"


def test_quit_flag():
    assert pc.should_quit() is False
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    input_state.process_events()
    assert pc.should_quit() is True
    input_state.reset_quit()
    assert pc.should_quit() is False


def test_window_close_ends_the_loop(_fresh_scene):
    """点了窗口关闭按钮之后，`while True: update()` 必须能自己结束。"""
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    pc.update()  # 这一帧照常走完（学生还能看到最后一帧）
    assert pc.should_quit() is True

    with pytest.raises(SystemExit):
        pc.update()  # 下一次 update(): 收尾 + 结束
    assert pygame.display.get_surface() is None, "退出时应当把窗口关掉"

    pc.setup(320, 240)  # 给后面的测试一个干净窗口


def test_window_close_can_be_intercepted(_fresh_scene):
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    pc.update()
    assert pc.should_quit() is True
    input_state.reset_quit()  # 自己处理退出：拦下来
    pc.update()
    assert pc.should_quit() is False, "拦下之后程序继续跑"


def test_entity_mouse_interaction(_fresh_scene):
    hero = pc.Character(TILES)
    mouse_pos = pc.get_mouse_pos()  # dummy 驱动下是窗口中心对应的数学坐标
    hero.goto(mouse_pos[0], mouse_pos[1])
    assert hero.get_mouse_upon() is True
    assert hero.get_mouse_clicked() is False, "没按下时为假"

    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)))
    input_state.process_events()
    assert hero.get_mouse_clicked() is True

    hero.hide()
    assert hero.get_mouse_upon() is False, "隐藏后不参与命中判定"


def test_entity_mouse_just_clicked_and_released(_fresh_scene):
    hero = pc.Character(TILES)
    elsewhere = pc.Character(TILES)
    mouse_pos = pc.get_mouse_pos()
    hero.goto(mouse_pos[0], mouse_pos[1])
    elsewhere.goto(mouse_pos[0] + 500, mouse_pos[1] + 500)

    assert hero.get_mouse_just_clicked() is False, "没按下时为假"

    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)))
    input_state.process_events()
    assert hero.get_mouse_just_clicked() is True, "对象上按下的那一帧为真"
    assert elsewhere.get_mouse_just_clicked() is False, "只对鼠标下的对象为真"

    input_state.process_events()  # 只是按住，不再算"刚按下"
    assert hero.get_mouse_clicked() is True
    assert hero.get_mouse_just_clicked() is False, "刚按下只应在一帧内为真"
    assert hero.get_mouse_just_released() is False

    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(0, 0)))
    input_state.process_events()
    assert hero.get_mouse_just_released() is True, "对象上松开的那一帧为真"
    assert elsewhere.get_mouse_just_released() is False

    input_state.process_events()
    assert hero.get_mouse_just_released() is False, "刚松开只应在一帧内为真"


# ------------------------------------------------------------------ 文本与对话框
def test_textbox_print_resizes_and_is_killable(_fresh_scene):
    box = pc.TextBox(16, "hi")
    narrow = box.width
    box.print("hi there, this is longer")
    assert box.width > narrow
    assert box.visual is not None
    box.kill()
    assert box.alive is False


def test_textbox_write_is_still_an_alias(_fresh_scene):
    box = pc.TextBox(16, "hi")
    box.write("换了内容")
    assert box.text == "换了内容"
    assert box.print("再换一次") is None
    assert box.text == "再换一次"


def test_textbox_multiline(_fresh_scene):
    box = pc.TextBox(14, "第一行\n第二行")
    assert box.height > 20


def test_dialogbox_say_follows_target_and_hides(_fresh_scene):
    hero = pc.Character(TILES, size=(16, 16))
    hero.goto(0, 0)
    dialog = pc.DialogBox(hero, 16)
    assert dialog.visible is False
    dialog.say("你好", duration=0.05)
    assert dialog.visible is True
    assert tuple(dialog.pos) != tuple(hero.pos), "对话框应当贴在目标旁边"

    for _ in range(6):
        pc.update()
    assert dialog.visible is False, "超过时长应当自动隐藏"


def test_dialogbox_survives_target_kill(_fresh_scene):
    hero = pc.Character(TILES, size=(16, 16))
    dialog = pc.DialogBox(hero, 16)
    dialog.say("再见", duration=10.0)
    hero.kill()
    pc.update()  # 目标没了也不该报错
    assert dialog.visible is False
    dialog.hide()


# ------------------------------------------------------------------ 资源
def test_image_cache_reuses_the_same_surface(_fresh_scene):
    first = pc.load_image(TILES)
    second = pc.load_image(TILES)
    assert first is second
    from pixelclass.resources import manager

    stats = manager().stats()
    assert stats["hits"] >= 1 and stats["misses"] >= 1


def test_preload_returns_all_and_reports_missing():
    images = pc.preload([TILES, TILES])
    assert len(images) == 2
    with pytest.raises(FileNotFoundError) as error:
        pc.preload([TILES, os.path.join(FIXTURES, "missing.png")])
    assert "missing.png" in str(error.value)


def test_load_image_before_setup_gives_readable_error():
    from pixelclass.resources import manager

    manager().clear()  # 已缓存的图片不需要窗口，这里要测的是"真的去解码"的路径
    pygame.display.quit()
    try:
        with pytest.raises(RuntimeError) as error:
            pc.load_image(TILES)
        assert "setup" in str(error.value)
    finally:
        pc.setup(320, 240)


# ------------------------------------------------------------------ 工具
def test_debug_and_tracer_switches(_fresh_scene):
    assert pc.debug(True, world=_fresh_scene) is True
    assert _fresh_scene.debug is True
    assert pc.tracer(True, world=_fresh_scene) is True
    pc.update()  # 开着调试绘制与帧率跟踪也要能正常跑一帧
    pc.debug(False, world=_fresh_scene)
    pc.tracer(False, world=_fresh_scene)
    assert _fresh_scene.debug is False


def test_random_pos_stays_inside_the_view(_fresh_scene):
    _fresh_scene.camera.pos = (0, 0)
    for _ in range(20):
        pos = pc.random_pos(margin=10)
        assert abs(pos[0]) <= _fresh_scene.camera.size[0] / 2
        assert abs(pos[1]) <= _fresh_scene.camera.size[1] / 2


def test_set_depth_returns_path_without_changing_cwd():
    before = os.getcwd()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        path = pc.set_depth(1)
    assert os.path.isdir(path)
    assert os.getcwd() == before, "不得改变进程工作目录"
    assert any(issubclass(item.category, DeprecationWarning) for item in caught)
