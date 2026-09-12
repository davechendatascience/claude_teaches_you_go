#!/usr/bin/env python
"""驗證章節檔案裡的每一張棋圖，都與它的 SGF 原始檔一致。

章節裡的棋圖必須長這樣：

    <!-- diagram: ch02_bent_three -->
    ```text
    ...（由 sgf_to_ascii 產生的內容）...
    ```
    *說明行*

這支腳本會重新產生每一張圖，逐字元比對。圍棋書最常見的錯誤是棋圖少一顆子
或標號錯位，而讀者會為此困惑半小時，卻以為是自己笨。這條檢查讓那種錯誤
不可能發生。

用法：
    python scripts/check_diagrams.py                # 檢查全部章節
    python scripts/check_diagrams.py chapters/ch02_connectivity.md
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from go_core.render import render_ascii   # noqa: E402
from go_core.sgf import load_sgf          # noqa: E402

BLOCK = re.compile(
    r"<!--\s*diagram:\s*([A-Za-z0-9_]+)\s*-->\s*\n```text\n(.*?)\n```\n(\*.*?\*)?",
    re.S,
)


def check_file(path):
    text = Path(path).read_text(encoding="utf-8")
    problems = []
    found = 0
    for m in BLOCK.finditer(text):
        found += 1
        name, body, caption = m.group(1), m.group(2), m.group(3)
        sgf = ROOT / "positions" / f"{name}.sgf"
        if not sgf.exists():
            problems.append(f"  [{name}] 找不到 {sgf.relative_to(ROOT)}")
            continue
        board, numbers, labels, marks, _ = load_sgf(str(sgf))
        want = render_ascii(board, numbers=numbers, labels=labels, marks=marks)
        if body.rstrip() != want.rstrip():
            problems.append(f"  [{name}] 棋圖與 SGF 不一致")
        if not caption:
            problems.append(f"  [{name}] 缺少底下的「請看什麼」說明行（寫作規範 §4.3）")

    # 手打棋圖偵測：出現座標列但沒有 diagram 標記的 text 區塊
    for m in re.finditer(r"```text\n(.*?)\n```", text, re.S):
        body = m.group(1)
        if re.search(r"^\s+A B C D", body, re.M):
            before = text[: m.start()].rstrip().splitlines()
            if not before or not before[-1].startswith("<!-- diagram:"):
                problems.append("  有一張棋圖沒有 <!-- diagram: ... --> 標記（疑似手打）")
    return found, problems


def main(argv):
    targets = [Path(a) for a in argv] or sorted((ROOT / "chapters").glob("*.md"))
    bad = 0
    for t in targets:
        if not t.exists():
            print(f"[skip] {t} 不存在")
            continue
        found, problems = check_file(t)
        if problems:
            bad += 1
            print(f"[FAIL] {t.name}（{found} 張圖）")
            for p in problems:
                print(p)
        else:
            print(f"[ ok ] {t.name}（{found} 張圖）")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
