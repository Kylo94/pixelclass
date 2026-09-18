# pixelclass

给中小学课堂用的 2D 游戏引擎：写十行代码就能让角色动起来，报错给中文提示，物理手感正确。

- 基于 **pygame**（窗口 / 输入 / 绘制）+ **pymunk**（物理）+ **pytmx**（瓦片地图）
- 面向课堂规模：几十个中小精灵、200 个以内的对象
- 每个关键行为都有自动化对拍测试（`acceptance/`），改动不会悄悄改变手感

## 状态

早期开发中（骨架阶段）。规格先行：实现按 `docs/spec/` 推进，行为以 `acceptance/` 为准。

## 安装

尚未发布到 PyPI。本地开发：

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```

## 开发

```bash
pytest -q                 # 全部测试
python acceptance/run.py  # 行为基线对拍（实现到位后可用）
black . && flake8 . && mypy src
```

## 许可证

MIT，见 `LICENSE`。
