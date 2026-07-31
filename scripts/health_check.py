#!/usr/bin/env python3
"""系统健康检查：死代码 + 测试 + 覆盖率 + 类型检查 四合一
用法: python3 scripts/health_check.py [--full]
"""
import os
import subprocess
import sys
import json
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

PYTHON = "/usr/bin/python3"
FULL = "--full" in sys.argv


def run(name: str, cmd: list, timeout: int = 300) -> dict:
    print(f"\n{'='*50}\n▶ {name}\n{'='*50}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
        return {
            "name": name,
            "ok": r.returncode == 0,
            "exit": r.returncode,
            "stdout_tail": r.stdout[-1500:] if r.stdout else "",
            "stderr_tail": r.stderr[-1000:] if r.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"name": name, "ok": False, "exit": -1, "stdout_tail": "TIMEOUT", "stderr_tail": ""}
    except Exception as e:
        return {"name": name, "ok": False, "exit": -2, "stdout_tail": str(e), "stderr_tail": ""}


def main():
    results = []
    report = []
    problems = []

    # 1. 死代码扫描
    r = run("死代码扫描 dead_code_check", [PYTHON, "scripts/dead_code_check.py"], timeout=60)
    results.append(r)
    # 死代码扫描有输出=有潜在断链，但脚本本身exit 0。输出非空即提示
    if r["stdout_tail"].strip():
        problems.append(f"死代码扫描发现潜在断链 {len(r['stdout_tail'].splitlines())} 行")

    # 2. 回归测试
    r = run("回归测试 pytest", [PYTHON, "-m", "pytest", "tests/", "-q", "--no-header"], timeout=300)
    results.append(r)
    if not r["ok"]:
        problems.append(f"pytest 失败 (exit {r['exit']})")

    # 3. 覆盖率
    cov_cmd = [PYTHON, "-m", "coverage", "run", "--source=backend/app", "-m", "pytest", "tests/", "-q", "--no-header"]
    r = run("覆盖率采集 coverage run", cov_cmd, timeout=300)
    if r["ok"]:
        r2 = subprocess.run(
            [PYTHON, "-m", "coverage", "report", "--fail-under=40", "--skip-covered"],
            capture_output=True, text=True, cwd=ROOT, timeout=60,
        )
        results.append({"name": "覆盖率报告", "ok": r2.returncode == 0, "exit": r2.returncode,
                        "stdout_tail": r2.stdout[-1500:], "stderr_tail": r2.stderr[-500:]})
        total_line = [l for l in r2.stdout.splitlines() if "TOTAL" in l]
        if total_line:
            problems.append(f"覆盖率: {total_line[0].strip()}")
        if r2.returncode != 0:
            problems.append("覆盖率低于阈值 40%")
    else:
        results.append({"name": "覆盖率采集", "ok": False, "exit": r["exit"], "stdout_tail": "", "stderr_tail": ""})
        problems.append("coverage 采集失败")

    # 4. mypy 类型检查（仅 --full 或首次）
    if FULL:
        r = run("mypy 类型检查", [PYTHON, "-m", "mypy", "backend/app", "--ignore-missing-imports", "--no-error-summary"], timeout=300)
        results.append(r)
        if not r["ok"]:
            problems.append(f"mypy 发现类型问题 (exit {r['exit']})")
    else:
        print("\n(跳过 mypy，--full 时执行)")

    # 汇总
    print("\n" + "=" * 50)
    print("健康检查汇总")
    print("=" * 50)
    for res in results:
        status = "✅" if res["ok"] else "❌"
        print(f"  {status} {res['name']} (exit {res.get('exit')})")

    if problems:
        print("\n⚠️ 发现问题：")
        for p in problems:
            print(f"  - {p}")
        print("\n详细输出见上方日志")
        sys.exit(1)
    else:
        print("\n✅ 全部健康，无问题")
        sys.exit(0)


if __name__ == "__main__":
    main()
