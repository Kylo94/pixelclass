"""一键发布：环境自检 -> 门禁 -> 构建 -> 校验 -> 安装测试 -> 上传 -> 核验。

    python scripts/release.py --dry-run          # 演练：不上传
    python scripts/release.py -y                 # 完整发布（不再逐步确认）
    python scripts/release.py --repository testpypi -y
    python scripts/release.py --verify-only      # 只补跑发布后核验

设计原则：**任何一步失败都停在上传之前**；令牌只从文件读入环境变量，绝不打印。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = "pixelclass"
VERSION_FILE = os.path.join(ROOT, "src", PACKAGE, "_version.py")
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")
DIST = os.path.join(ROOT, "dist")
REPOS = {
    "pypi": {
        "url": "https://upload.pypi.org/legacy/",
        "json": "https://pypi.org/pypi/{name}/{version}/json",
        "token_file": ".pypi-token",
    },
    "testpypi": {
        "url": "https://test.pypi.org/legacy/",
        "json": "https://test.pypi.org/pypi/{name}/{version}/json",
        "token_file": ".pypi-token-test",
    },
}


class Abort(Exception):
    """检查失败：带可执行的修复建议。"""

    def __init__(self, step: str, message: str, hint: str = "") -> None:
        super().__init__(f"[{step}] {message}" + (f"\n        提示：{hint}" if hint else ""))


def ok(message: str) -> None:
    print(f"  ✓ {message}")


def warn(message: str) -> None:
    print(f"  ! {message}")


def run(command, env=None, capture=False, cwd=None):
    return subprocess.run(
        command,
        cwd=cwd or ROOT,
        env=env or os.environ.copy(),
        capture_output=capture,
        text=True,
    )


# ---------------------------------------------------------------------- 自检用的小工具
def read_version(path: str = VERSION_FILE) -> str:
    """从 _version.py 里读出版本号（不导入包）。"""
    import re

    with open(path, encoding="utf-8") as handle:
        match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', handle.read(), re.M)
    if not match:
        raise Abort("环境自检", f"无法从 {os.path.relpath(path, ROOT)} 解析 __version__")
    return match.group(1)


def changelog_heading(version: str, path: str = CHANGELOG):
    """返回 CHANGELOG 里该版本的标题行；没有则返回 None。"""
    import re

    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        match = re.search(rf"^##\s*\[?{re.escape(version)}\]?.*$", handle.read(), re.M)
    return match.group(0).strip() if match else None


def unreleased_heading(path: str = CHANGELOG):
    """返回 CHANGELOG 里"未发布"那条标题；没有则返回 None。"""
    import re

    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        match = re.search(r"^##\s*\[?(?:未发布|待发布|unreleased|tbd)\]?\s*$", handle.read(), re.I | re.M)
    return match.group(0).strip() if match else None


def replace_first_heading(old: str, new: str, path: str = CHANGELOG) -> None:
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text.replace(old, new, 1))


def discover_tests(tests_dir: str = None):
    """返回测试文件名（pytest 约定：test_*.py）。"""
    directory = tests_dir or os.path.join(ROOT, "tests")
    if not os.path.isdir(directory):
        return []
    return sorted(name for name in os.listdir(directory) if name.startswith("test_") and name.endswith(".py"))


def remote_has_version(version: str, repo: str = "pypi"):
    url = REPOS[repo]["json"].format(name=PACKAGE, version=version)
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            json.load(response)
    except urllib.error.HTTPError as error:
        return False if error.code == 404 else None
    except Exception:  # noqa: BLE001 - 网络问题不该让发布流程误判
        return None
    return True


# ---------------------------------------------------------------------- 步骤
def confirm(question: str, assume_yes: bool) -> bool:
    if assume_yes:
        print(f"  ? {question} -> 自动确认（-y）")
        return True
    try:
        answer = input(f"  ? {question} [y/N] ").strip().lower()
    except EOFError:  # 非交互环境（CI、管道）里不要卡住
        print(f"  ? {question} -> 无法交互，视为否（可用 -y 自动确认）")
        return False
    return answer in ("y", "yes")


def step_preflight(args):
    print("=" * 72 + "\n第 1/7 步：环境自检\n" + "=" * 72)
    version = read_version()
    print(f"  版本：{version}")

    if os.path.isdir(os.path.join(ROOT, ".git")):
        dirty = run(["git", "status", "--porcelain"], capture=True).stdout.strip()
        if dirty:
            warn("工作区有未提交改动（发布产物仍会按当前文件构建）")

    exists = remote_has_version(version, args.repository)
    if exists is True:
        raise Abort(
            "环境自检",
            f"{version} 在 {args.repository} 上已经存在（同版本不可覆盖）",
            "先改 src/pixelclass/_version.py 并在 CHANGELOG 写新条目",
        )
    if exists is False:
        ok(f"{version} 尚未被占用")

    heading = changelog_heading(version)
    if heading is None:
        pending = unreleased_heading()
        today = time.strftime("%Y-%m-%d")
        if pending:
            fixed = f"## [{version}] - {today}"
            if args.dry_run:
                ok(f"演练：正式发布会把「{pending}」定版为「{fixed}」")
            elif confirm(f"CHANGELOG 里是「{pending}」，定版为「{fixed}」？", args.yes):
                replace_first_heading(pending, fixed)
                ok(f"CHANGELOG 已定版：{fixed}")
            else:
                raise Abort("环境自检", "CHANGELOG 没有该版本条目")
        else:
            raise Abort("环境自检", "CHANGELOG 既没有该版本条目、也没有「未发布」条目")

    if args.dry_run:
        ok("演练模式：不会上传")
    return version


def step_gate(args):
    print("=" * 72 + "\n第 2/7 步：门禁（格式 / 静态检查 / 类型 / 测试 / 行为验收）\n" + "=" * 72)
    command = [sys.executable, os.path.join("scripts", "check.py")]
    if args.matrix:
        command.append("--matrix")
    if run(command).returncode != 0:
        raise Abort("门禁", "scripts/check.py 未通过", "先修好再发布")
    ok("门禁全部通过")


def step_build(args):
    print("=" * 72 + "\n第 3/7 步：构建 sdist + wheel\n" + "=" * 72)
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    if run([sys.executable, "-m", "build"]).returncode != 0:
        raise Abort("构建", "python -m build 失败", "确认已安装 dev 依赖（pip install -e '.[dev]'）")
    files = sorted(os.path.join(DIST, name) for name in os.listdir(DIST))
    for path in files:
        print(f"    {os.path.basename(path)}  {os.path.getsize(path) / 1024:.0f} KB")
    ok("构建完成")
    return files


def step_check_artifacts(args, files):
    print("=" * 72 + "\n第 4/7 步：产物校验 + 安装测试\n" + "=" * 72)
    if run([sys.executable, "-m", "twine", "check", *files]).returncode != 0:
        raise Abort("产物校验", "twine check 未通过", "检查 README 的渲染与元数据")

    if args.skip_install_test:
        warn("按参数跳过安装测试")
        return

    temp = tempfile.mkdtemp(prefix="pixelclass-release-")
    venv = os.path.join(temp, "venv")
    try:
        if run(["uv", "venv", venv]).returncode != 0:
            raise Abort("安装测试", "uv venv 失败")
        python = os.path.join(venv, "bin", "python")
        wheel = next((path for path in files if path.endswith(".whl")), files[0])
        if run(["uv", "pip", "install", "--python", python, wheel, "pytest"]).returncode != 0:
            raise Abort("安装测试", "在全新环境里安装产物失败")
        env = os.environ.copy()
        env["SDL_VIDEODRIVER"] = "dummy"
        env["SDL_AUDIODRIVER"] = "dummy"
        env["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
        env["PIXELCLASS_TEST_INSTALLED"] = "1"  # 让测试用已安装的包，而不是 src/
        env.pop("PYTHONPATH", None)

        # 先断言"导入到的是装好的包"：0.1.0 就是被 pythonpath 设置蒙过去的——
        # pytest 用了本地 src/，安装测试假通过，带着缺子包的轮子发了出去
        probe = run([python, "-c", f"import {PACKAGE}; print({PACKAGE}.__file__)"], env=env, capture=True)
        location = (probe.stdout or "").strip().splitlines()[-1] if probe.stdout else ""
        if probe.returncode != 0 or not location:
            raise Abort("安装测试", f"装好的包导入失败：{(probe.stderr or '').strip()[-200:]}")
        if os.path.abspath(location).startswith(os.path.abspath(ROOT)):
            raise Abort(
                "安装测试",
                f"测试用的是本地源码而不是装好的包：{location}",
                "检查 pyproject 的 pythonpath 设置与 PYTHONPATH",
            )
        ok(f"导入路径确认是安装产物：{location}")

        # -o pythonpath= 覆盖 pyproject 里的 pythonpath 设置，确保测试导入的是安装产物
        if run([python, "-m", "pytest", "-q", "-o", "pythonpath="], env=env).returncode != 0:
            raise Abort("安装测试", "装了产物之后测试没通过", "本地能过、装了不过通常是打包漏文件")
        ok("全新环境安装产物后测试通过")
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def step_upload(args, files):
    print("=" * 72 + "\n第 5/7 步：上传\n" + "=" * 72)
    if args.dry_run:
        warn("演练模式：跳过上传")
        return
    token_path = os.path.join(ROOT, REPOS[args.repository]["token_file"])
    if not os.path.isfile(token_path):
        raise Abort("上传", f"找不到令牌文件 {os.path.relpath(token_path, ROOT)}")
    mode = os.stat(token_path).st_mode & 0o777
    if mode & 0o077:
        warn(f"令牌文件权限较宽（{oct(mode)}），建议 chmod 600")

    env = os.environ.copy()
    with open(token_path, encoding="utf-8") as handle:
        env["UV_PUBLISH_TOKEN"] = handle.read().strip()  # 只进环境变量，不打印
    print(f"  即将上传到 {args.repository}：{', '.join(os.path.basename(p) for p in files)}")
    if not confirm("确认上传？上传后版本不可覆盖", args.yes):
        raise Abort("上传", "用户取消")
    result = run(["uv", "publish", "--publish-url", REPOS[args.repository]["url"], *files], env=env)
    if result.returncode != 0:
        raise Abort("上传", "uv publish 失败", "检查令牌权限（首次上传需要整个项目的权限）")
    ok("已上传")


def step_verify(args, version):
    print("=" * 72 + "\n第 6/7 步：发布后核验\n" + "=" * 72)
    if args.dry_run:
        warn("演练模式：跳过核验")
        return
    deadline = time.time() + 180
    while time.time() < deadline:
        if remote_has_version(version, args.repository) is True:
            ok(f"{args.repository} 上已经能看到 {version}")
            break
        time.sleep(5)
    else:
        raise Abort("核验", "等待超时：索引还没刷新", "稍后可用 --verify-only 重新核验")

    package = f"{PACKAGE}=={version}"
    probe = f"import {PACKAGE}; print({PACKAGE}.__version__); print({PACKAGE}.__file__)"
    neutral = tempfile.mkdtemp(prefix="pixelclass-verify-")
    try:
        # 必须在**干净环境里**核验：仓库里的核验会被本地可编辑安装顶替，变成"自己验自己"
        # （0.1.0 就是这么骗过我的）。只加 --no-project 不够——当前激活的 venv 里就有本地
        # 可编辑安装，所以这里建一个全新的空 venv，用索引上的包把它装满。
        venv = os.path.join(neutral, "venv")
        if run(["uv", "venv", venv], cwd=neutral).returncode != 0:
            raise Abort("核验", "uv venv 失败")
        python = os.path.join(venv, "bin", "python")
        env = {
            **os.environ,
            "SDL_VIDEODRIVER": "dummy",
            "SDL_AUDIODRIVER": "dummy",
            "PYGAME_HIDE_SUPPORT_PROMPT": "1",
        }
        env.pop("PYTHONPATH", None)
        env.pop("VIRTUAL_ENV", None)
        for attempt in range(1, 7):
            # --refresh 绕开本机索引缓存，确保拿到的是刚传上去的产物
            installed = run(
                ["uv", "pip", "install", "--python", python, "--refresh", package],
                env=env,
                capture=True,
                cwd=neutral,
            )
            result = (
                run([python, "-c", probe], env=env, capture=True, cwd=neutral)
                if installed.returncode == 0
                else installed
            )
            lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
            if result.returncode == 0 and lines:
                installed_version, location = lines[0], lines[-1]
                if installed_version != version:
                    raise Abort("核验", f"索引上装到的是 {installed_version}，期望 {version}")
                if os.path.abspath(location).startswith(os.path.abspath(ROOT)):
                    raise Abort("核验", f"装到的其实是本地源码：{location}", "核验要在项目目录之外进行")
                ok(f"从索引安装成功（{installed_version}）：{location}")
                return
            warn(f"第 {attempt} 次核验还没成功，等索引刷新…")
            time.sleep(10)
        raise Abort("核验", f"从索引装不上 {version}", "稍后用 --verify-only 重试")
    finally:
        shutil.rmtree(neutral, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="pixelclass 一键发布")
    parser.add_argument("--dry-run", action="store_true", help="只做自检/门禁/构建/校验，不上传")
    parser.add_argument("--verify-only", action="store_true", help="只补跑发布后核验")
    parser.add_argument("-y", "--yes", action="store_true", help="所有确认自动通过")
    parser.add_argument("--matrix", action="store_true", help="门禁额外跑 pymunk 依赖矩阵")
    parser.add_argument("--skip-install-test", action="store_true", help="跳过全新环境安装测试（不推荐）")
    parser.add_argument("--repository", choices=sorted(REPOS), default="pypi")
    args = parser.parse_args(argv)

    if args.verify_only:
        step_verify(args, read_version())
        return 0

    try:
        version = step_preflight(args)
        step_gate(args)
        files = step_build(args)
        step_check_artifacts(args, files)
        step_upload(args, files)
        step_verify(args, version)
    except Abort as error:
        print(f"\n✗ 发布中止：{error}\n")
        return 1

    print("\n" + "=" * 72)
    if args.dry_run:
        print(f"✓ 演练完成（未上传）：{PACKAGE} {version}")
    else:
        print(f"✓ 发布完成：{PACKAGE} {version}（{args.repository}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
