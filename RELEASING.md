# 发布说明

## 日常检查

```bash
python scripts/check.py            # 格式 / 静态检查 / 类型 / 单元测试 / 行为验收
python scripts/check.py --matrix   # 额外跑 pymunk 6.11.1 与最新版
```

## 发版

1. 改 `src/pixelclass/_version.py` 的版本号；
2. 在 `CHANGELOG.md` 顶部写 `## [未发布]` 段落；
3. 运行：

```bash
python scripts/release.py --dry-run   # 演练：自检 + 门禁 + 构建 + 产物校验 + 安装测试，不上传
python scripts/release.py -y          # 正式发布
```

脚本会：环境自检（版本是否占用、CHANGELOG 条目、令牌权限）→ 门禁 → 构建 →
`twine check` + 全新环境安装测试 → 上传 → 发布后核验（索引可见 + 从索引安装）。
**任何一步失败都停在上传之前。**

## 令牌

令牌放在仓库根的 `.pypi-token`（已被 `.gitignore` 排除），**只从文件读入环境变量、不打印**；
权限建议 `chmod 600`。演练真实上传流程用 `--repository testpypi`（对应 `.pypi-token-test`）。

## 分支与提交

- `main` 始终可发布：`python scripts/check.py` 全绿才提交；
- 大改动走分支：`git switch -c feature/xxx`，做完跑绿再合回；
- 提交信息用中文描述即可，前缀 `feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:`。
