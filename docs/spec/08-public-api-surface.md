# 08 公共接口面（清单与兼容规则）

> 实现依据。本文件定"哪些名字必须存在、参数形状如何"，实现从规格产出。

## 1. 兼容规则

1. `from pixelclass import *` 之后，下表的名字全部可直接使用。
2. 需要场景的接口保留 `world=` 这个**参数名**（已有讲义里写的就是它），类型是本项目的场景对象。
3. 未特别说明时，参数与返回值语义见对应章节的规格。
4. **不复用旧项目与其品牌**：包名、模块名、环境变量前缀都用 `pixelclass` / `PIXELCLASS_`。

## 2. 必须提供的名字（按章节分组）

### 2.1 场景与主循环（spec 01）

`Scene`（正式名）· `World`（别名，讲义兼容）· `setup` · `update` · `done` · `title` · `save_screen`
· `Screen` · `global_var`（当前场景）· `init` · `cwd` · `Group`

### 2.2 实体（spec 02）

`Entity`（正式名）· `GameObject` / `NewGameObject`（**别名**）· `Character` · `Sensor` · `Wall` · `Mouse`

### 2.3 视觉与动画（spec 04）

`Sprite` · `SpriteSheet` · `EasySpriteStrategy` · `ListSpriteStrategy` · `AnimatorStrategy` · `TiledMapStrategy`

- 实体上的播放控制（spec 04 §2.4）：`play_anim` · `pause_anim` · `stop_anim` · `is_anim_playing`

### 2.4 物理与约束（spec 03）

`Body` · `BodiesGroup` · `TiledMapBodies` · `TiledMapBodiesGroup` · `connect` · `Connect` · `Spring`

### 2.5 地图与背景（spec 05）

`TiledMap` · `bgpic`

### 2.6 相机（spec 06）

`Camera`

### 2.7 文本与对话框（spec 07）

`TextBox` · `DialogBox`

### 2.8 输入（spec 06）

`get_mouse_pos` · `get_mouse_rel` · `get_mouse_clicked` · `get_mouse_just_clicked`
· `get_mouse_just_released` · `set_mouse_visible`
· `key_pressed` · `key_just_pressed` · `key_just_released` · `key_input`

### 2.9 音频（spec 06）

`bgmusic` · `set_volume` · `audio_available`
· `music_load` · `music_play` · `music_queue` · `music_stop` · `music_pause` · `music_unpause`
· `music_rewind` · `music_fadeout` · `music_set_pos` · `music_get_pos`
· `music_set_volume` · `music_get_volume` · `music_get_busy`
· `music_set_endevent` · `music_get_endevent`

### 2.10 资源（spec 06）

`load_image` · `preload` · `ResourceManager`

### 2.11 报错助手（spec 07）

`install_error_help` · `uninstall_error_help` · `set_error_help` · `is_error_help_enabled` · `explain_exception`

### 2.12 工具（spec 01 / 07）

`draw_line` · `random_pos` · `sign` · `tracer` · `speed` · `debug` · `set_gravity`
· `Cartesian2pygame` · `pygame2Cartesian` · `to_cp` · `vec` · `set_depth` · `__version__`

### 2.13 pygame 常量

`from pygame.locals import *` 的事件 / 按键常量照旧导出（`K_SPACE`、`QUIT`、鼠标常量等），
这样学生不写 `pygame.` 前缀也能用。**不导出** pygame 模块对象本身。

## 3. 与旧项目的**有意差异**（写清楚，避免被当成缺漏）

| 差异 | 说明 |
|---|---|
| 不导出 `Object` | 旧项目里它曾是"内部载体"，语义混乱；新项目根类叫 `Entity`，不再提供 `Object` 这个名字 |
| 新增 `Scene` | 正式概念名；`World` 保留为别名，讲义可继续用 |
| 音频/图形常量之外的模块对象 | 一律不导出（`pygame` / `pymunk` / `pytmx` 模块本身） |
| 环境变量前缀 | `PIXELCLASS_ERROR_HELP`（旧项目用自己的前缀，本项目一律换掉） |
| 品牌名 | 代码、文档、示例中不出现旧项目/公司名称 |

## 4. 验收点

- 上表每个名字都在 `pixelclass.__all__` 里且可访问（写测试逐个断言）。
- `from pixelclass import *` 后 `Character` / `K_SPACE` / `setup` 都可用。
- `__all__` 里**不含**模块对象（`pygame` / `pymunk` / `pytmx` / `os` / `sys`）。
- `Scene is not None and World is Scene`。
- **品牌扫描**：源码、`README.md`、`docs/spec/*`、`acceptance/*` 中不出现旧项目名与公司名。
  白名单只有两处**过程记录**：`CONTRIBUTING.md` 与 `docs/spec/00-overview.md` 的净室说明段落
  ——它们记录"规格先行、未复制实现"，是净室过程的证据，**有意保留**。
  扫描脚本按白名单断言，其余文件必须零命中。
