#!/usr/bin/env python3
"""AST 静态分析：找出 backend/app 和 scripts 下定义了但从未被调用的函数/类/方法。

排除项：
- 以 _ 开头的私有函数/方法
- __init__、main、create_app
- FastAPI 路由装饰器（@router.get/post/...、@app.get/...）注册的函数
- pytest 测试类（Test*）和方法（test_*）
- dataclass 字段（类级注解赋值，非 FunctionDef/ClassDef，天然不在此列）
"""
import ast
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIRS = ["backend/app", "scripts"]

ROUTE_DECORATORS = {
    "get", "post", "put", "patch", "delete",
    "options", "head", "websocket", "route", "api_route",
}
EXCLUDE_NAMES = {"main", "create_app"}


def _is_route_decorated(node: ast.AST) -> bool:
    for dec in node.decorator_list:
        func = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(func, ast.Attribute):
            if func.attr in ROUTE_DECORATORS:
                return True
        elif isinstance(func, ast.Name):
            if func.id in ROUTE_DECORATORS:
                return True
    return False


class _ReferenceCollector(ast.NodeVisitor):
    """收集代码中所有被引用到的名字（Name / Attribute / import 别名）。"""

    def __init__(self):
        self.referenced: set[str] = set()

    def visit_Name(self, node):
        self.referenced.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        self.referenced.add(node.attr)
        self.generic_visit(node)

    def _alias(self, node):
        if node.asname:
            self.referenced.add(node.asname)
        else:
            self.referenced.add(node.name.split(".")[-1])
        self.generic_visit(node)

    def visit_Import(self, node):
        for a in node.names:
            self._alias(a)

    def visit_ImportFrom(self, node):
        for a in node.names:
            self._alias(a)


def _is_skipped_def(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if node.name.startswith("_"):
        return True
    if node.name.startswith("visit_"):
        # ast.NodeVisitor 通过 'visit_' + 节点名 动态分发调用，静态无法识别
        return True
    if node.name in EXCLUDE_NAMES:
        return True
    if node.name.startswith("test_"):
        return True
    if _is_route_decorated(node):
        return True
    return False


def _collect_defs(tree: ast.Module, filepath: str, defs: list):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _is_skipped_def(node):
                defs.append((filepath, node.lineno, "function", node.name))
        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("Test"):
                continue
            defs.append((filepath, node.lineno, "class", node.name))
            for item in node.body:
                is_def = isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                if is_def and not _is_skipped_def(item):
                    defs.append((filepath, item.lineno, "method", f"{node.name}.{item.name}"))


def main() -> int:
    all_refs: set[str] = set()
    defs: list[tuple[str, int, str, str]] = []

    for scan_dir in SCAN_DIRS:
        base = os.path.join(PROJECT_ROOT, scan_dir)
        for root, _, files in os.walk(base):
            for fn in sorted(files):
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(root, fn)
                try:
                    with open(path, encoding="utf-8") as f:
                        source = f.read()
                    tree = ast.parse(source, filename=path)
                except (SyntaxError, OSError) as e:
                    print(f"[warn] {os.path.relpath(path, PROJECT_ROOT)}: {e}")
                    continue
                collector = _ReferenceCollector()
                collector.visit(tree)
                all_refs |= collector.referenced
                _collect_defs(tree, path, defs)

    dead_by_file: dict[str, list] = {}
    for path, lineno, kind, qual in defs:
        if qual.split(".")[-1] in all_refs:
            continue
        dead_by_file.setdefault(path, []).append((lineno, kind, qual))

    total = 0
    for path in sorted(dead_by_file):
        print(os.path.relpath(path, PROJECT_ROOT))
        for lineno, kind, qual in sorted(dead_by_file[path]):
            print(f"  :{lineno:<6} [{kind:<8}] {qual}")
            total += 1
        print()

    print(f"共发现 {total} 个疑似未使用定义")
    return 0


if __name__ == "__main__":
    sys.exit(main())
