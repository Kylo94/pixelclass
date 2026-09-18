# 06 相机 / 输入 / 音频 / 资源

> 实现依据。

## 1. 相机

- **每个场景一个相机**，不是全局单例：`Camera(尺寸=None, world=None)` 可显式创建；
  `scene.camera` 读该场景的相机。
- 尺寸默认取窗口大小；创建后可用 `Camera((宽, 高))` 改变可视区域（例如让背景图铺满）。

| 接口 | 语义 |
|---|---|
| `follow(对象)` | 每帧把相机对准目标；传 `None` 解除跟随 |
| `deadzone(宽, 高)` | 死区：目标在死区内时相机不动（避免呼吸式抖动） |
| `shake(强度=8, 时长=0.3)` | 抖动一段时间后自动停 |
| `stop_shake()` | 立即停止抖动 |
| `zoom_to(倍数, 速度=2)` | 平滑缩放到目标倍数 |
| `smooth_zoom` | 缩放时使用平滑重采样（观感更好，成本更高） |

- 相机位置只影响**绘制偏移**，不改变任何对象坐标。
- 相机效果按真实经过时间推进（测试时可注入假时钟）。
- 多场景：推进/绘制一个场景不改变另一个场景的相机。

## 2. 输入

### 2.1 鼠标

| 接口 | 语义 |
|---|---|
| `get_mouse_pos(world=None)` | 鼠标位置的**数学坐标** |
| `get_mouse_rel()` | 自上一帧起的相对位移 |
| `get_mouse_clicked()` | 左键是否**按住** |
| `get_mouse_just_clicked()` | 本帧是否**刚按下** |
| `get_mouse_just_released()` | 本帧是否**刚松开** |
| `set_mouse_visible(布尔)` | 是否显示系统光标 |

- "刚按下/刚松开"只在事件发生的那一帧为真，下一帧自动复位。

### 2.2 键盘

| 接口 | 语义 |
|---|---|
| `key_pressed(键=None)` | 按住；不传键 = 任意键按住 |
| `key_just_pressed(键)` / `key_just_released(键)` | 仅本帧为真 |
| `key_input(提示文字="", 最大长度=20, world=None)` | 简易文本输入：每帧返回当前已输入文字；回车后 `text_input_done()` 变真，取完结果用 `text_input_reset()` 清空 |

- 键名使用 pygame 的键常量；`from … import *` 后可直接写 `K_SPACE`。

### 2.3 实体级交互

- `obj.get_mouse_upon()`：鼠标**悬停在对象上**时为真；
- `obj.get_mouse_clicked()`：鼠标**在对象上**按下（按住期间持续为真）；
- `obj.get_mouse_just_clicked()`：鼠标**刚在对象上按下**（仅该帧为真，适合"点一下"）；
- `obj.get_mouse_just_released()`：鼠标**刚在对象上松开**（仅该帧为真）；
- 判定要求对象 `visible`；命中判定走碰撞/贴图 mask（见 `03` §5）。

## 3. 音频

### 3.1 背景音乐

```
bgmusic(音乐名)                       # 载入并循环播放（最常用）
music_load / music_play / music_queue / music_stop / music_pause / music_unpause
music_rewind / music_fadeout(毫秒=1000) / music_set_pos / music_get_pos
music_set_volume / music_get_volume / music_get_busy
music_set_endevent / music_get_endevent
set_volume(0~1)                       # 主音量
audio_available()                     # 是否有可用音频设备
```

- 音频文件名可以不写扩展名（按 `.ogg` → `.mp3` → `.wav` 顺序探测）。
- **没有音频设备时（无声卡、CI、无显示器环境）所有音频接口必须安全无操作**，不得抛异常。
- `music_fadeout()` 不传参数时使用默认时长（1000 ms），不得因缺参报错。

### 3.2 实体音效

- `obj.play_snd(文件[, 循环=False])`；`obj.set_volume(0~1)` 控制该对象的音效音量。

## 4. 资源缓存

| 接口 | 语义 |
|---|---|
| `load_image(路径, world=None)` | 载入图片（带缓存） |
| `preload([路径…], world=None)` | 批量预载，返回数量或列表；缺文件要给出可读错误 |
| `ResourceManager` | 场景级缓存：同一路径只解码一次。用**普通字典 + 显式 `clear()`**：pygame 的 Surface 在不少平台不支持弱引用，与其"有时能回收"不如给确定的清理手段；`stats()` 可看命中次数 |

- 图片与字体都缓存；同一路径第二次载入应当**命中缓存**（不重复解码）。
- **实体贴图（`Character(...)` 给路径 / 路径列表 / 状态字典）也必须走这个缓存**：
  它内部就是"每造一个对象载一次图"，不过缓存的话，课堂里"每帧造子弹"的写法会把
  磁盘解码全烧掉，并让 libpng 把 stderr 刷满。
- 素材里带错误 ICC 配置（`iCCP: known incorrect sRGB profile`）时，解码前在**内存里**
  过滤掉 PNG 的 `iCCP` 块再交给 pygame：不改磁盘文件，也不再刷屏。
- 载入失败 → 中英双语可读错误，指出路径与可能原因（拼错 / 不在工作目录 / 不是图片）。

## 5. 验收点

- 相机：跟随目标后相机位置等于目标位置；死区内的微小移动不改变相机；`shake` 一段时间后自动归位；
  多场景相机互不影响。
- 输入：鼠标坐标是数学坐标；"刚按下"只在一帧内为真；`key_pressed()` 不传参 = 任意键。
- 音频：在无音频设备环境下，`bgmusic` / `music_*` / `obj.play_snd` 全部不报错；
  `music_fadeout()` 无参可调用。
- 资源：同一图片载入两次命中缓存；缺文件时错误信息包含路径。
