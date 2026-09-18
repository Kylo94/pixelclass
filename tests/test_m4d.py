"""M4d 测试：中英双语报错、中文字体、音频安全无操作、相机手感（spec 06 / 07）。"""

import os
import sys

import pytest

import pixelclass as pc
from pixelclass import error_help, fonts
from pixelclass.clock import Clock


@pytest.fixture(autouse=True)
def _fresh_scene():
    scene = pc.setup(320, 240)
    scene.clock = Clock(ticker=lambda: 17)
    yield scene


# ------------------------------------------------------------------ 报错助手
def test_explanation_rules_match_expected_cases():
    assert "setup" in pc.explain_exception(RuntimeError("载入地图失败：还没有初始化窗口"))
    assert "路径" in pc.explain_exception(FileNotFoundError("找不到图片文件：x.png"))
    assert "size" in pc.explain_exception(TypeError("size 参数看不懂：'大'"))
    assert "动画状态" in pc.explain_exception(ValueError("没有这个动画状态：'fly'"))


def test_explanation_never_guesses_wildly():
    """规则要克制：泛泛的 NoneType 报错不能硬说成"忘了 setup()"。"""
    generic = AttributeError("'NoneType' object has no attribute 'anything'")
    assert pc.explain_exception(generic) == ""
    assert pc.explain_exception(KeyError("whatever")) == ""


def test_toggle_and_env_var(monkeypatch):
    pc.set_error_help(False)
    assert pc.is_error_help_enabled() is False
    pc.set_error_help(True)
    assert pc.is_error_help_enabled() is True
    monkeypatch.setenv(error_help.ENV_VAR, "0")
    assert pc.is_error_help_enabled() is False
    monkeypatch.delenv(error_help.ENV_VAR)


def test_hook_prints_chinese_hint_then_original(capsys):
    pc.uninstall_error_help()
    before = sys.excepthook
    try:
        pc.install_error_help()
        assert sys.excepthook is not sys.__excepthook__
        error_help._hook(RuntimeError, RuntimeError("还没有初始化窗口"), None)
        captured = capsys.readouterr()
        assert error_help.HEADER in captured.err
        assert "RuntimeError" in captured.err, "原始报错信息不能被吞掉"
    finally:
        pc.uninstall_error_help()
        assert sys.excepthook is before, "卸载应当还原安装前的钩子"
        pc.install_error_help()  # 恢复本包的默认状态


def test_hook_installed_by_default():
    pc.install_error_help()
    assert error_help.is_error_help_installed()


# ------------------------------------------------------------------ 中文字体
def test_find_font_returns_existing_path_or_none():
    found = pc.find_font()
    assert found is None or os.path.isfile(found)


def test_load_font_uses_default_when_nothing_found(monkeypatch):
    fonts.reset_cache()
    monkeypatch.setattr(fonts, "find_font", lambda: None)
    font = pc.load_font(20)
    assert font is not None
    assert font.get_height() > 0


def test_load_font_with_explicit_missing_path_raises():
    with pytest.raises(FileNotFoundError):
        pc.load_font(20, path="/nope/not-a-font.ttf")


# ------------------------------------------------------------------ 音频（无设备安全）
def test_audio_functions_are_safe_without_device():
    assert pc.audio_available() in (True, False)
    assert pc.music_load("nope") in (True, False)
    assert pc.music_play() in (True, False)
    assert pc.music_stop() in (True, False)
    assert pc.music_pause() in (True, False)
    assert pc.music_unpause() in (True, False)
    assert pc.music_rewind() in (True, False)
    assert pc.music_fadeout() in (True, False), "不传参数时必须能用默认时长"
    assert pc.music_get_busy() in (True, False)
    assert isinstance(pc.music_get_pos(), float)
    assert isinstance(pc.music_get_endevent(), int)


def test_set_volume_clamps_and_survives_without_device():
    assert pc.set_volume(0.5) == pytest.approx(0.5)
    assert pc.set_volume(5) == pytest.approx(1.0)
    assert pc.set_volume(-1) == pytest.approx(0.0)
    pc.set_volume(1.0)


def test_resolve_music_probes_extensions(tmp_path, monkeypatch):
    from pixelclass import audio

    monkeypatch.chdir(tmp_path)
    assert audio.resolve_music("song") is None
    (tmp_path / "song.mp3").write_bytes(b"not really audio")
    assert audio.resolve_music("song") == os.path.join(".", "song.mp3") or audio.resolve_music(
        "song"
    ).endswith("song.mp3")


def test_entity_sound_helpers_do_not_crash(_fresh_scene):
    hero = pc.Character(size=(16, 16))
    assert hero.play_snd("nope") is None
    assert hero.set_volume(0.3) == pytest.approx(0.3)
    hero.kill()  # 销毁时停止音效也不应报错


# ------------------------------------------------------------------ 相机
def test_camera_follow_and_snap(_fresh_scene):
    hero = pc.Character(size=(16, 16))
    hero.goto(100, 50)
    _fresh_scene.camera.follow(hero)
    pc.update()
    assert (_fresh_scene.camera.x, _fresh_scene.camera.y) == (100.0, 50.0)
    _fresh_scene.camera.follow(None)
    hero.goto(0, 0)
    pc.update()
    assert _fresh_scene.camera.x == 100.0, "解除跟随后相机不动"


def test_camera_deadzone_ignores_small_moves(_fresh_scene):
    camera = _fresh_scene.camera
    hero = pc.Character(size=(16, 16))
    hero.goto(0, 0)
    camera.deadzone(40, 40)
    camera.follow(hero)
    pc.update()
    hero.goto(20, 20)  # 仍在死区内
    pc.update()
    assert (camera.x, camera.y) == (0.0, 0.0)
    hero.goto(100, 0)  # 超出死区
    pc.update()
    assert camera.x == pytest.approx(60.0), "超出死区后应当把目标拉回死区边缘"


def test_camera_shake_then_stops(_fresh_scene):
    camera = _fresh_scene.camera
    assert tuple(camera._shake_offset) == (0.0, 0.0)
    camera.shake(5.0, 0.1)
    camera.advance(0.05)
    assert camera._shake_offset.length() > 0, "抖动期间应当有偏移"
    camera.advance(0.2)
    assert tuple(camera._shake_offset) == (0.0, 0.0), "超过时长后应当归零"
    camera.shake()
    camera.stop_shake()
    assert tuple(camera._shake_offset) == (0.0, 0.0)


def test_camera_zoom_to_converges_and_affects_screen(_fresh_scene):
    camera = _fresh_scene.camera
    camera.zoom_to(2.0, speed=10.0)
    for _ in range(30):
        camera.advance(1 / 60)
    assert camera.zoom == pytest.approx(2.0)

    camera.pos = (0, 0)
    assert camera.to_screen((10, 0)) == (320 / 2 + 20, 240 / 2), "缩放应当作用在屏幕偏移上"


def test_camera_smooth_zoom_flag_is_used_when_set(_fresh_scene):
    camera = _fresh_scene.camera
    camera.smooth_zoom = True
    camera.zoom_to(1.5, speed=10.0)
    for _ in range(30):
        camera.advance(1 / 60)
    assert camera.zoom == pytest.approx(1.5)
