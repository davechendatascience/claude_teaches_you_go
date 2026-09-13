#!/usr/bin/env python
"""產生第 9 章用到的 figures/*.txt（影響力場圖）。

和 positions/*.sgf 同一個規矩：書上不准手打任何一張圖。
場圖由這支腳本算出來寫成檔案，check_figures.py 再逐位元組比對。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from go_core.board import BLACK, WHITE, Board                       # noqa: E402
from go_core.influence import (bouzy_field, marginal_map,            # noqa: E402
                               render_field, zobrist_field)

OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)

COLS = "ABCDEFGHJKLMNOPQRST"
LAM = 0.8


def wall_board(line, n=13, lo=4, hi=10):
    b = Board(n)
    b.place_many(BLACK, [f"{COLS[line - 1]}{r}" for r in range(lo, hi + 1)])
    return b


def two_lamps():
    b = Board(9)
    b.place(BLACK, "C3")
    b.place(WHITE, "G7")
    return render_field(zobrist_field(b, LAM), b, unit=0.1)


def wall4_zobrist():
    b = wall_board(4)
    return render_field(zobrist_field(b, LAM), b, unit=1.0)


def wall4_bouzy():
    b = wall_board(4)
    return render_field(bouzy_field(b, 4), b, unit=1.0)


def wall4_stats():
    """牆的【背後】與【前方】，每手平均多圍幾點模樣。

    牆在 D 列。背後 = A–C 三列；前方 = F 列以後（D、E 是牆本身與它
    緊貼的一路，兩邊都不算）。這兩個數字正文會引用，所以在這裡算。
    """
    b = wall_board(4)
    mm = marginal_map(b, BLACK, theta=1.0, lam=LAM)
    cols = "ABCDEFGHJKLMN"
    back, front = [], []
    for (r, c), v in mm.items():
        if b.grid[r, c] != 0:
            continue
        name = cols[c]
        if name in "ABC":
            back.append(v)
        elif name not in "DE":
            front.append(v)
    return (sum(back) / len(back), max(back),
            sum(front) / len(front), max(front))


def wall4_marginal():
    """每一個空點：在那裡多下一手，模樣（I > 1）大幾點。"""
    b = wall_board(4)
    mm = marginal_map(b, BLACK, theta=1.0, lam=LAM)
    n = b.n
    rows = []
    for r in range(n):
        cells = []
        for c in range(n):
            if b.grid[r, c] != 0:
                cells.append("X" if b.grid[r, c] == BLACK else "O")
            else:
                v = mm[(r, c)]
                cells.append("." if v <= 0 else
                             str(min(9, (v + 4) // 5)))
        rows.append(" ".join(cells))
    bm, bx, fm, fx = wall4_stats()
    rows.append("")
    rows.append(f"  牆的背後（A-C 列）：每手平均 +{bm:.2f} 點（最大 {bx}）")
    rows.append(f"  牆的前方（F 列以後）：每手平均 +{fm:.2f} 點（最大 {fx}）")
    rows.append(f"  差 {fm / bm:.0f} 倍。")
    return "\n".join(rows)


def three_walls():
    """三線、四線、五線的牆，各自的場（同一個刻度，可以直接比）。"""
    parts = []
    for line in (3, 4, 5):
        b = wall_board(line)
        parts.append(f"第 {line} 線")
        parts.append(render_field(zobrist_field(b, LAM), b, unit=1.0))
        parts.append("")
    return "\n".join(parts).rstrip("\n")


FIGURES = {
    "ch09_field_lamps": two_lamps,
    "ch09_field_wall4": wall4_zobrist,
    "ch09_field_wall4_bouzy": wall4_bouzy,
    "ch09_field_marginal": wall4_marginal,
}


def main():
    for name, fn in FIGURES.items():
        text = fn().rstrip("\n") + "\n"
        (OUT / f"{name}.txt").write_text(text, encoding="utf-8", newline="\n")
    print(f"寫出 {len(FIGURES)} 張場圖")


if __name__ == "__main__":
    main()
