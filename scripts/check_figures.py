#!/usr/bin/env python
"""檢查章節裡的「非棋圖」圖表（影響力場、熱圖、表格）是否和產生器一致。

和 check_diagrams.py 同一套規矩，只是來源不同：

    棋圖   <!-- diagram: NAME -->   來源 positions/NAME.sgf
    圖表   <!-- figure:  NAME -->   來源 figures/NAME.txt

figures/*.txt 由 scripts/make_figures_chNN.py 產生。書上不准手打任何一張圖，
這個檔案負責讓那條規矩對第 9 章之後的新圖種也成立。

跑法：
    python scripts/check_figures.py chapters/ch09_influence.md
    python scripts/check_figures.py chapters/*.md
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"

BLOCK = re.compile(
    r"<!-- figure: (?P<name>[\w]+) -->\n```text\n(?P<body>.*?)\n```\n(?P<cap>\*.*?\*)?",
    re.S,
)


def check_file(path):
    text = Path(path).read_text(encoding="utf-8")
    problems = []
    found = 0

    for m in BLOCK.finditer(text):
        found += 1
        name = m.group("name")
        src = FIGURES / f"{name}.txt"
        if not src.exists():
            problems.append(f"  [{name}] 找不到 figures/{name}.txt")
            continue
        want = src.read_text(encoding="utf-8").rstrip("\n")
        if m.group("body").rstrip() != want.rstrip():
            problems.append(f"  [{name}] 圖表與 figures/{name}.txt 不一致")
        if not m.group("cap"):
            problems.append(f"  [{name}] 缺少底下的「請看什麼」說明行")

    # 沒有標記卻長得像場圖的區塊
    for m in re.finditer(r"```text\n(.*?)\n```", text, re.S):
        body = m.group(1)
        looks_like_field = (
            len(body.splitlines()) >= 5
            and sum(1 for ln in body.splitlines()
                    if re.fullmatch(r"[0-9a-zXO. ]+", ln)) >= 5
            and not re.search(r"^\s+A B C D", body, re.M)
        )
        if looks_like_field:
            before = text[: m.start()].rstrip().splitlines()
            tag = before[-1] if before else ""
            if not tag.startswith("<!-- figure:") and not tag.startswith("<!-- diagram:"):
                problems.append("  有一張場圖沒有 <!-- figure: ... --> 標記（疑似手打）")
    return found, problems


def main(argv):
    if not argv:
        argv = [str(p) for p in sorted((ROOT / "chapters").glob("*.md"))]
    bad = 0
    for path in argv:
        found, problems = check_file(path)
        name = Path(path).name
        if problems:
            bad = 1
            print(f"[FAIL] {name}（{found} 張圖表）")
            for p in problems:
                print(p)
        else:
            print(f"[ ok ] {name}（{found} 張圖表）")
    return bad


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
