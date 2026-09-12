#!/usr/bin/env python
"""把 positions/*.sgf 畫成書上的 ASCII 棋圖。

用法：
    python scripts/sgf_to_ascii.py positions/ch02_bent_three.sgf
    python scripts/sgf_to_ascii.py --all positions/ch02_*.sgf

正文中不准手打棋圖（docs/03_writing_brief.md §4.1）。所有棋圖都從這裡出來，
再由 scripts/check_diagrams.py 回頭驗證章節檔案裡的圖沒有被手動改壞。
"""

import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from go_core.render import render_ascii   # noqa: E402
from go_core.sgf import load_sgf          # noqa: E402


def render_file(path):
    board, numbers, labels, marks, comment = load_sgf(str(path))
    return render_ascii(board, numbers=numbers, labels=labels, marks=marks), comment


def main(argv):
    args = [a for a in argv if not a.startswith("-")]
    paths = []
    for a in args:
        paths.extend(sorted(glob.glob(a)))
    if not paths:
        print(__doc__)
        return 1
    for p in paths:
        art, comment = render_file(p)
        print(f"<!-- diagram: {Path(p).stem} -->")
        print("```text")
        print(art)
        print("```")
        if comment:
            print(f"*{comment}*")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
