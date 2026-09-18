# 02 对象模型（实体 / 视觉 / 刚体）

> 实现依据。只描述**行为与接口**，不规定内部数据结构。

## 1. 分层：组合，不是深继承

课堂上讲"一个游戏对象 = 一张图 + 一个刚体"，代码里就要能指出来：

```
Entity（实体）
├── visual   显示组件（一张图 / 帧序列 / 状态机 / 瓦片地图）—— 可为空
├── rigid    刚体组件（圆 / 矩形 / 多边形）—— 可为空
└── tiles    瓦片刚体组件（一组按格子摆放的刚体）—— 可为空
```

- `rigid` 与 `tiles` **互斥**：一个实体要么是单个刚体，要么是一组瓦片刚体。
- 组件为 `None` 表示"这一层不存在"，这是**合法状态**，不是错误（见 §3）。
- 实体自身只管：身份、变换缓存、组件槽位、生命周期、所属场景。
- 槽位的**正式名**是 `visual` / `rigid` / `tiles`；同时提供讲义里用过的兼容别名
  `sprite` / `body` / `tiledmap_bodies`（同一个对象，两种叫法）。

### 1.1 预设类（课堂直接用）

| 类 | 刚体类型 | 说明 |
|---|---|---|
| `Character` | 动态（DYNAMIC） | 会受重力、会碰撞、会被推动 |
| `Wall` | 静态（STATIC） | 永远不动，撞上去会被挡住 |
| `Sensor` | 运动学（KINEMATIC）+ 触发（sensor） | 自己不动也不被推，但能检测到"谁进来了" |
| `Mouse` | 运动学 | 每帧跟随鼠标位置 |

四者构造签名一致（见 §2），都直接是 `Entity` 的子类。

## 2. 构造签名与形状判定

```
Entity(图片=None, size=None, body_type=KINEMATIC, sensor=False, world=None)
Character(图片=None, size=None, world=None)          # body_type 固定 DYNAMIC
Wall(图片=None, size=None, world=None)               # 固定 STATIC
Sensor(图片=None, size=None, world=None)             # 固定 KINEMATIC + sensor=True
Mouse(图片=None, world=None)                         # 跟随鼠标
```

`size` 决定刚体形状：

| `size` 类型 | 形状 | 说明 |
|---|---|---|
| `int` | 圆 | 值是半径；负数或 0 视为非法并给出可读错误 |
| `(w, h)` 二元组（元组或两元素列表） | 矩形 | 宽高 |
| `[[x, y], …]`（点列表） | 多边形 | 顶点坐标，自动求凸包（或直接使用 pymunk 的多边形约束） |
| `[obj, obj, …]`（扁平对象列表） | 瓦片刚体组 | 每个 `obj` 至少要有 `points`，可选 `x` / `y` 作为相对偏移 |

- `图片` 支持：`None`、路径字符串、`pygame.Surface`、路径列表（帧动画）、
  `{"状态名": [帧…]}` 字典（状态机）、瓦片地图对象。
- 构造顺序：先建立组件，再把实体登记进场景（登记后每帧才会被更新/绘制）。

## 3. 组件缺失时的行为（重要，旧版最容易踩的坑）

"半个对象"必须**明确可用**，而不是抛 `AttributeError`：

| 情况 | 显示层接口 | 物理层接口 |
|---|---|---|
| 只有图片（`size=None`） | 正常 | **一次性**中英双语提示 + 返回中性值（`velocity` → `None`、赋值被忽略） |
| 只有 `size`（`图片=None`） | **一次性**中英双语提示 + 中性值（`visible` → `False`、`width`/`height` → `0`、颜色/图层 → `None`、赋值被忽略） | 正常 |
| 两者都有 | 正常 | 正常 |

- 提示文案要能教会人：说清"为什么没生效"和"怎么改"（例：创建时传 `size=(32, 32)` 才有刚体）。
- **每个实体对每类缺失只提示一次**，避免游戏循环里每帧刷屏。
- 提示类型是 `RuntimeWarning`，可用 `warnings` 过滤。

## 4. 变换接口

| 接口 | 语义 | 权限 |
|---|---|---|
| `pos` / `x` / `y` | 位置（读）；写 = **瞬移：同步刚体 + 清零速度** | 读写 |
| `goto(x, y)` / `goto((x, y))` | 放到指定坐标（等价于写 `pos`），并清零速度 | 方法 |
| `shift_by((dx, dy))` | 增量位移：同步刚体、**不动速度** | 方法 |
| `rot` | 旋转角（度）；写 = 缓存 + 标记重绘 + 同步刚体 | 读写 |
| `angle` | **朝向角**（度，float，由 `dir` 算出）；只读 | 只读 |
| `set_angle(度)` | 设置朝向（同时更新 `dir`） | 方法 |
| `dir` | 朝向向量（默认 `(1, 0)`） | 读写 |
| `scl` / `scale(sx, sy=None)` | 缩放：贴图与刚体一起缩放；圆形只能等比 | 读写 / 方法 |
| `face_to(x, y)` | 转向某个坐标（或某个方向向量） | 方法 |
| `forward(d)` / `backward(d)` | 沿朝向走 `d` 像素（内部走 `shift_by`，**不清速度**） | 方法 |
| `slide_to(目标, 步长)` | 朝目标滑行；距离小于步长时直接落点 | 方法 |
| `distance(目标)` | 到目标（另一个对象或某个坐标）的**直线距离**（像素） | 方法 |

- `distance()` 的目标可以给：另一个对象（用它的 `pos`）、坐标 `(x, y)` / `vec(x, y)`，
  或分开写 `distance(x, y)`。返回两个**中心点**的距离，永远非负；自己到自己为 0。
- 它只算数、**不移动、不转向、不清速度**（要移动用 `slide_to`，要转向用 `face_to`）；
  目标读不出来时抛可读的中英双语错误，而不是 `TypeError`/`AttributeError`。

## 5. 显示层代理接口

| 接口 | 说明 |
|---|---|
| `red` / `green` / `blue` / `alpha` / `color` | 着色与透明度；写颜色会标记"需要重绘"。`color` 可写 `(r, g, b)` 或 `(r, g, b, a)` |
| `visible` / `show()` / `hide()` | 是否参与绘制 |
| `width` / `height` | 贴图尺寸（只读） |
| `flipx(布尔)` / `flipy(布尔)` | 水平 / 垂直翻转 |
| `layer` / `move_to_front()` / `move_to_back()` | 绘制层级 |

## 6. 物理层代理接口

| 接口 | 说明 |
|---|---|
| `velocity` | 线速度（`vec`）；无刚体时提示 + `None` |
| `angular_velocity` | 角速度 |
| `mass` / `elasticity` / `friction` | 质量 / 弹性 / 摩擦 |
| `apply_force(x, y)` | 施加冲量（内部按 pymunk 的局部点冲量施加） |
| `body_scale(sx, sy)` | 只缩放刚体几何 |

## 7. 生命周期

- `alive`：布尔；`kill()` 之后为 `False`。
- `kill()` 的行为：销毁显示组件与物理组件 → 清空槽位 → `alive = False` → 回调 `_on_kill()`。
- `_on_kill()`：**给子类的清理钩子**（默认什么都不做）。子类要清理自己的东西时覆盖它，
  **不要覆盖 `kill()`**（覆盖 `kill()` 容易忘记调用父类实现，导致组件没销毁而且不报错）。
- 重复 `kill()` 必须安全（不报错）。
- 帧钩子：`_update()` 内部每帧调用一次；`update()` 是**留给使用者覆盖**的空实现。

## 8. 兼容别名（照顾已有讲义）

| 本引擎名字 | 同时提供的别名 | 说明 |
|---|---|---|
| `Entity` | `GameObject`、`NewGameObject` | 历史讲义里出现过的基类名 |
| `angle` | `get_angle`（属性） | 旧讲义可能写作 `obj.get_angle`，返回同样的 float |

> 别名只是名字，实现只有一份；新代码请用左列的名字。

## 9. 不变量

1. `kill()` 之后：`alive is False`、三个组件槽位均为 `None`，再 `kill()` 不报错。
2. `pos` 与刚体位置一致——除非显式只写缓存（`sync_pos`）或只写刚体（不存在这种接口）。
3. 无组件的接口调用**永不**抛 `AttributeError`（见 §3）。
4. `angle` 与 `rot` 是两个不同的量：`angle` 由 `dir` 算出（朝向），`rot` 是贴图/刚体的旋转角。

## 10. 验收点

- 继承关系：`Character` / `Wall` / `Sensor` / `Mouse` 都是 `Entity` 的实例。
- 别名等价：`GameObject is Entity`、`NewGameObject is Entity`。
- `pos=` 清零速度、`shift_by()` 不清、`sync_pos()` 不动刚体（三条路径 × 有/无刚体）。
- 无图/无刚体两种"半个对象"的四个接口各给一次性提示 + 中性值，且**只提示一次**。
- `kill()` 后槽位清空、`alive=False`、`_on_kill()` 被调用一次。
