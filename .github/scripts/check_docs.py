#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文档检查：Markdown 相对链接校验 + 行数统计。

用法：
    python3 .github/scripts/check_docs.py links   # 只查相对链接，有断链则退出码 1
    python3 .github/scripts/check_docs.py stats   # 只输出行数统计
    python3 .github/scripts/check_docs.py all     # 两者都做

设计取舍：
- 文件清单来自 `git ls-files`，因此天然排除被 .gitignore 忽略的内容（如 2 GB 的 dl/）；
- 只校验**仓库内相对链接**，外链仅列出不访问 —— 外链检查依赖第三方站点，
  会在网络抖动时把 CI 变成"随机失败"，不适合当门槛；
- 围栏代码块内的示例链接不参与校验（否则文档里的示例会被误判）。
"""

import os
import re
import subprocess
import sys
import urllib.parse

# 行内链接与图片： [text](target) / ![alt](target)，允许 <target> 与 "title"
LINK_RE = re.compile(r'!?\[[^\]]*\]\(\s*<?([^)>\s]+)>?(?:\s+"[^"]*")?\s*\)')
FENCE_RE = re.compile(r'^\s*(```|~~~)')

SUMMARY_PATH = os.environ.get("GITHUB_STEP_SUMMARY")


def tracked_markdown():
    """仓库中纳入版本管理的 Markdown 文件（相对仓库根，POSIX 风格）。"""
    raw = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.md"],
        capture_output=True,
        check=True,
    ).stdout
    return sorted(p for p in raw.decode("utf-8").split("\0") if p)


def strip_code_fences(lines):
    """围栏代码块内容置空，但保留行号，便于报错定位。"""
    out, in_fence = [], False
    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else line)
    return out


def iter_links(path):
    """产出 (行号, 链接目标)。"""
    with open(path, encoding="utf-8") as fh:
        lines = strip_code_fences(fh.read().splitlines())
    for lineno, line in enumerate(lines, 1):
        for match in LINK_RE.finditer(line):
            yield lineno, match.group(1)


def check_links(files):
    broken, external, internal = [], set(), 0
    for path in files:
        base = os.path.dirname(path)
        for lineno, target in iter_links(path):
            if target.startswith(("#", "mailto:")):
                continue
            if target.startswith(("http://", "https://", "//")):
                external.add(target)
                continue
            internal += 1
            rel = urllib.parse.unquote(target.split("#")[0])
            if not rel:
                continue
            if not os.path.exists(os.path.normpath(os.path.join(base, rel))):
                broken.append((path, lineno, target))
    return broken, external, internal


def line_stats(files):
    rows = []
    for path in files:
        with open(path, encoding="utf-8") as fh:
            lines = sum(1 for _ in fh)
        rows.append((lines, os.path.getsize(path), path))
    rows.sort(reverse=True)
    return rows


def emit(lines):
    text = "\n".join(lines)
    print(text)
    if SUMMARY_PATH:
        with open(SUMMARY_PATH, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")


def do_links(files):
    broken, external, internal = check_links(files)
    out = ["## Markdown 链接检查", ""]
    out.append("| 项 | 数值 |")
    out.append("|---|---:|")
    out.append(f"| 检查的 Markdown 文件 | {len(files)} |")
    out.append(f"| 仓库内相对链接 | {internal} |")
    out.append(f"| 外部链接（仅统计，不访问） | {len(external)} |")
    out.append(f"| **断链** | **{len(broken)}** |")
    if broken:
        out += ["", "| 位置 | 断链目标 |", "|---|---|"]
        out += [f"| `{p}:{n}` | `{t}` |" for p, n, t in broken]
        out += ["", "> 相对链接必须指向仓库中真实存在的文件（大小写敏感）。"]
    emit(out)
    return 1 if broken else 0


def do_stats(files):
    rows = line_stats(files)
    total_lines = sum(r[0] for r in rows)
    total_bytes = sum(r[1] for r in rows)
    out = ["## 文档行数统计", ""]
    out.append("| 文件 | 行数 | 大小 |")
    out.append("|---|---:|---:|")
    for lines, size, path in rows:
        out.append(f"| `{path}` | {lines} | {size / 1024:.1f} KB |")
    out.append(f"| **合计（{len(rows)} 份）** | **{total_lines}** | **{total_bytes / 1024:.1f} KB** |")
    emit(out)
    return 0


def main(argv):
    mode = argv[1] if len(argv) > 1 else "all"
    if mode not in ("links", "stats", "all"):
        print(f"未知模式：{mode}（可选 links / stats / all）", file=sys.stderr)
        return 2

    files = tracked_markdown()
    if not files:
        print("未找到纳入版本管理的 Markdown 文件。", file=sys.stderr)
        return 2

    code = 0
    if mode in ("links", "all"):
        code = do_links(files)
    if mode in ("stats", "all"):
        code = max(code, do_stats(files))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
