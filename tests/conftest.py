"""pytest 公共配置：无显示器环境下用 dummy 驱动（headless）。"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT, "src")
# 发布流程会用 PIXELCLASS_TEST_INSTALLED=1 跑测试，此时要测"装好的包"而不是 src/
if os.environ.get("PIXELCLASS_TEST_INSTALLED") != "1" and _SRC not in sys.path:
    sys.path.insert(0, _SRC)
