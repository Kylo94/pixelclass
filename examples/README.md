# 例子

三个可以直接跑的小例子（都要先 `pip install -e .` 或在仓库根目录运行）：

| 文件 | 内容 |
|---|---|
| `quickstart.py` | 最小可运行：角色落到地面、向右走、屏幕上有一行字 |
| `physics_basics.py` | 弹性球、箱子、弹簧、高速子弹防穿透，并打开刚体轮廓调试绘制 |
| `tiledmap_basics.py` | 铺 TMX 背景、从对象层取出实体、用整图当碰撞体 |

```bash
python examples/quickstart.py
PIXELCLASS_EXAMPLE_FRAMES=120 python examples/physics_basics.py   # 只跑 120 帧（无显示器也能跑）
```

`PIXELCLASS_EXAMPLE_FRAMES` 用来限制帧数：CI 与自动化测试都靠它（否则 `while True` 不会退出）。
地图素材与验收夹具共用（`acceptance/fixtures/`），这样示例里出现的就是测试验证过的那套坐标。
