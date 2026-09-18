"""示例测试：三个例子都要能在无显示器环境下跑完固定帧数（并且真的动起来）。"""

import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(ROOT, "examples")
FRAMES = "60"


def _run(name):
    env = os.environ.copy()
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    env["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    env["PIXELCLASS_EXAMPLE_FRAMES"] = FRAMES
    return subprocess.run(
        [sys.executable, os.path.join(EXAMPLES, name)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("name", ["quickstart.py", "physics_basics.py", "tiledmap_basics.py"])
def test_example_runs_headless(name):
    result = _run(name)
    assert result.returncode == 0, f"{name} 退出码 {result.returncode}\n{result.stderr[-800:]}"
    assert f"跑了 {FRAMES} 帧" in result.stdout, result.stdout[-400:]


def test_examples_are_listed_in_readme():
    readme = open(os.path.join(EXAMPLES, "README.md"), encoding="utf-8").read()
    for name in ("quickstart.py", "physics_basics.py", "tiledmap_basics.py"):
        assert name in readme
