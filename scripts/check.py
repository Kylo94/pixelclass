"""一条命令跑完所有检查：格式 / 静态检查 / 类型 / 单元测试 / 行为验收。

python scripts/check.py            # 快速：本机环境
python scripts/check.py --matrix   # 额外跑 pymunk 6.11.1 与最新版的依赖矩阵
python scripts/check.py --list     # 只列出会跑哪些步骤
"""

import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
PYTHON = sys.executable


def _env(**extra):
    env = os.environ.copy()
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    env.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    env.update(extra)
    return env


def _run(label, command, env=None):
    print(f"\n$ {' '.join(command)}")
    result = subprocess.run(command, cwd=ROOT, env=env or _env())
    return label, result.returncode == 0


def steps(include_matrix: bool):
    """返回 [(步骤名, 命令, 环境)]。"""
    plan = [
        ("格式（black --check）", [PYTHON, "-m", "black", "--check", "."], None),
        ("静态检查（flake8）", [PYTHON, "-m", "flake8", "src", "tests", "acceptance", "scripts"], None),
        ("类型检查（mypy）", [PYTHON, "-m", "mypy", "src"], None),
        ("单元测试（pytest）", [PYTHON, "-m", "pytest", "-q"], None),
        ("行为验收（acceptance/run.py）", [PYTHON, os.path.join("acceptance", "run.py")], None),
    ]
    if include_matrix:
        for pymunk in ("pymunk==6.11.1", "pymunk"):
            plan.append(
                (
                    f"依赖矩阵（{pymunk}）",
                    [
                        "uv",
                        "run",
                        "--no-project",
                        "--quiet",
                        f"--python={PYTHON}",
                        "--with=pygame>=2.5.0",
                        f"--with={pymunk}",
                        "--with=pytmx>=3.32",
                        "--with=pytest",
                        "python",
                        "-m",
                        "pytest",
                        "-q",
                    ],
                    None,
                )
            )
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description="pixelclass 全量检查")
    parser.add_argument("--matrix", action="store_true", help="额外跑 pymunk 新旧两个版本")
    parser.add_argument("--list", action="store_true", help="只列出步骤")
    args = parser.parse_args(argv)

    plan = steps(args.matrix)
    if args.list:
        for name, _command, _env in plan:
            print(f"  - {name}")
        return 0

    failures = []
    for name, command, env in plan:
        label, ok = _run(name, command, env)
        if not ok:
            failures.append(label)

    print("\n" + "=" * 72)
    if failures:
        print("失败项：")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
