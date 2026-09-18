# pixelclass

给中小学课堂用的 2D 游戏引擎：写十行代码就能让角色动起来，报错给中文提示，物理手感正确。

- 基于 **pygame**（窗口 / 输入 / 绘制）+ **pymunk**（物理）+ **pytmx**（瓦片地图）
- 面向课堂规模：几十个中小精灵、200 个以内的对象
- **每个关键行为都有对拍测试**（`acceptance/`）：改动不会悄悄改变手感
- 规格先行：实现按 `docs/spec/` 推进，看得见的文档、查得到的行为

## 快速开始

```bash
pip install pixelclass
```

```python
import pixelclass as pc

pc.setup(640, 480)          # 建窗口
pc.set_gravity(0, -1200)    # 没设重力的话角色不会往下掉

hero = pc.Character("hero.png", size=(32, 32))   # 有贴图 + 有刚体
hero.goto(-200, 0)
floor = pc.Wall(size=(600, 20))                  # 不动的地面
floor.goto(0, -150)
hero.velocity = (150, 0)

while True:
    pc.update()             # 一帧：物理 + 绘制
```

坐标原点在**窗口中心**、**y 轴向上**——学生说"往右上飞"就是 x 变大、y 变大。

## 核心概念

| 概念 | 说明 |
|---|---|
| **场景** | `Scene`：一套独立的世界（物理空间 + 对象 + 相机 + 时钟）。多个场景互不干扰。 |
| **实体** | `Entity`：由三个**可选**组件组成——视觉（贴图）/ 单体刚体 / 瓦片刚体组。 |
| **预设** | `Character`（会掉、会被推）、`Wall`（不动）、`Sensor`（穿透触发器）、`Mouse`（跟随鼠标）。 |
| **固定步长** | 物理固定 1/60 秒，与帧率无关；高速物体会自动**切成子步**，防止穿墙。 |
| **三条写入路径** | `pos = …`（瞬移，清零速度）、`shift_by()`（位移，不动速度）、`sync_pos()`（物理回写，只改显示）。 |

**"半个对象"也是合法的**：只给图片不给 `size` → 没有物理；只给 `size` 不给图片 → 没有显示。
这时相关接口会给**一次**中英双语提示并返回中性值（`velocity` → `None`、`width` → `0`…），
不会抛看不懂的 `AttributeError`。

## 常用接口速查

```python
# 场景与主循环
pc.setup(宽, 高)   pc.update()   pc.done()   pc.title("标题")   pc.save_screen("shot.png")

# 创建与摆放
hero = pc.Character("hero.png", size=(32, 32))     # (宽, 高) → 矩形刚体；size=16 → 半径 16 的圆
hero.goto(100, 50)      # 放到坐标（清零速度）
hero.forward(10)        # 沿朝向走 10 像素（不清速度）
hero.slide_to((0, 0), 5)

# 物理
hero.velocity = (200, 0)      hero.mass = 2      hero.elasticity = 0.6
hero.apply_force(100, 200)    hero.angular_velocity = 90
pc.connect(a, b)              # 销钉；pc.Spring(a, b, rest_length=80, stiffness=200, damping=10) 弹簧
pc.set_gravity(0, -1200)

# 视觉与动画
hero.color = (255, 100, 100, 255)     hero.hide() / hero.show()      hero.layer = 5
hero2 = pc.Character(["a.png", "b.png"])          # 帧序列
hero3 = pc.Character({"idle": [...], "walk": [...]})   # 状态机：hero3.state = "walk"（下一帧生效）

# 碰撞
hero.collide((x, y))          # 点是否落在对象上（刚体 > 瓦片组 > 贴图 mask）
hero.collide(other)           # 两个对象是否接触
hero.separate(other)          # 把重叠推开

# 地图 / 相机 / 文本
m = pc.TiledMap("level.tmx");  m.render(surface) 或 pc.bgpic("level.tmx")
spawn = m.create_objects(name="spawn", body_type="DYNAMIC")
scene.camera.follow(hero);  scene.camera.deadzone(40, 40);  scene.camera.shake(6, 0.3)
pc.TextBox(20, "得分：0").goto(-280, 200);  pc.DialogBox(hero).say("你好！")

# 输入
pc.key_pressed(pc.K_SPACE)     pc.key_just_pressed(pc.K_LEFT)     pc.key_pressed()  # 任意键
pc.get_mouse_pos()             pc.get_mouse_clicked()              hero.get_mouse_upon()
hero.get_mouse_just_clicked()  hero.get_mouse_just_released()      # 只在该帧为真：点一下/松开

# 教学辅助
pc.debug(True)      # 画出刚体轮廓：碰撞体到底在哪一目了然
pc.tracer(True)     # 每秒打印一次 FPS
pc.speed(1)         # 慢动作：每帧位移的步长
```

## 验收与开发

```bash
python scripts/check.py            # 格式 / 静态检查 / 类型 / 单元测试 / 行为验收
python scripts/check.py --matrix   # 额外跑 pymunk 6.11.1 与最新版
python acceptance/run.py           # 只跑行为验收（27 项观测对拍基线）
python scripts/release.py --dry-run
```

`acceptance/` 里的 27 项观测是本项目的"手感合同"：位移/速度语义、碰撞三条路径、
约束、防穿透子步、相机、对象层坐标、整帧像素哈希、生命周期。任何改动都要能对上；
有意改动时用 `--freeze` 重新冻结（它会**拒绝**悄悄覆盖既有期望值）。

## 目录

```
src/pixelclass/      实现（scene / entity / visual / physics / worldmap / ui / audio / fonts / error_help）
docs/spec/           规格：实现的唯一依据（先读 README 索引）
acceptance/          行为验收：观测清单、夹具、运行脚本、基线
tests/               单元测试（122 项）
examples/            可直接运行的例子
scripts/             check.py（门禁）、release.py（发布）
```

## 许可证

MIT，见 `LICENSE`。
