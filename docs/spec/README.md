# 规格索引

实现前先读本页，再按顺序读对应章节。**实现只依据本目录与 `../acceptance/`。**

| 文件 | 内容 |
|---|---|
| [00-overview.md](00-overview.md) | 目标、非目标、术语、兼容性决策、新架构、里程碑 |
| [01-coordinates-scene-loop.md](01-coordinates-scene-loop.md) | 坐标系、场景生命周期、固定步长与自适应子步、位置/角度写入三路径 |
| [02-object-model.md](02-object-model.md) | 实体与三个组件槽位、四个预设类、构造与形状判定、缺失组件的行为、生命周期 |
| [03-physics-and-collision.md](03-physics-and-collision.md) | 刚体类型与形状、宽相重排规则、瓦片刚体组、碰撞三路径、约束 |
| [04-visuals-and-animation.md](04-visuals-and-animation.md) | 四种绘制来源、绘制状态与重绘标记、帧序列与状态机、图层顺序 |
| [05-worldmap.md](05-worldmap.md) | TMX 载入与渲染、坐标换算、对象层 → 实体、整图刚体 |
| [06-camera-input-audio-resources.md](06-camera-input-audio-resources.md) | 相机、鼠标/键盘、实体级交互、音频（无声卡安全）、资源缓存 |
| [07-errors-fonts-text-tools.md](07-errors-fonts-text-tools.md) | 中英双语报错、异常钩子、中文字体、文本与对话框、场景级工具 |
| [08-public-api-surface.md](08-public-api-surface.md) | 必须提供的公共名字清单、兼容规则、与旧实现的有意差异 |

验收规格（**不是**实现依据的一部分，是它的判据）：`../acceptance/observations.md`。

## 写作约定

- 规格只描述**行为与接口**（"应当如何"），不规定内部数据结构与算法；
- 每条规格尽量给出**可验证的验收点**（能写成断言的那种）；
- 实现中发现规格不足 → 先补规格，再写代码；确实需要回头查证旧实现的行为，
  登记到仓库根的 `SPEC-QUESTIONS.md`（只记"问题 → 行为结论"，不贴代码）。
