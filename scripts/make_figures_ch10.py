#!/usr/bin/env python
"""產生第 10 章用到的 figures/*.txt。

兩張圖：
  * ch10_deltav      3 路盤每一手的失分（由完全解算出）
  * ch10_sigmoid     勝率曲線 p = sigma(V/tau)，看得見凹與凸的分界
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from go_core.board import BLACK, Board                                # noqa: E402
from go_core.minimax import move_values, win_rate                     # noqa: E402

OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)

MAX_PLY = 15
TAU = 6.0


def deltav_map():
    """3 路盤：每一點下第一手的【失分】。"""
    vals = dict(move_values(Board(3), BLACK, komi=0.0, max_ply=MAX_PLY))
    best = max(v for v in vals.values())
    rows = []
    for r in range(3):
        cells = []
        for c in range(3):
            d = best - vals[(r, c)]
            cells.append(f"{-d:+3.0f}" if d else "  0")
        rows.append(" ".join(cells))
    rows.append("")
    rows.append(f"pass {-(best - vals[None]):+3.0f}")
    return "\n".join(rows)


def sigmoid_plot(width=61, height=17, lo=-24.0, hi=24.0):
    """勝率曲線的 ASCII 圖。橫軸是目數 V，縱軸是勝率。"""
    grid = [[" "] * width for _ in range(height)]
    for col in range(width):
        v = lo + (hi - lo) * col / (width - 1)
        p = float(win_rate(v, TAU))
        row = int(round((1.0 - p) * (height - 1)))
        grid[row][col] = "*"
    mid_col = int(round((0 - lo) / (hi - lo) * (width - 1)))
    for row in range(height):
        if grid[row][mid_col] == " ":
            grid[row][mid_col] = "|"
    mid_row = (height - 1) // 2
    for col in range(width):
        if grid[mid_row][col] == " ":
            grid[mid_row][col] = "-"

    lines = []
    for row in range(height):
        p = 1.0 - row / (height - 1)
        label = f"{p:4.2f} "
        lines.append(label + "".join(grid[row]))
    axis = " " * 5 + "".join(
        "^" if col in (0, mid_col, width - 1) else " " for col in range(width))
    lines.append(axis)
    lines.append(f"     {lo:<+5.0f}{'V (目)':^{width - 12}}{hi:>+5.0f}")
    lines.append("")
    lines.append("     V < 0 這半邊是凸的 -> 該提高變異數（勝負手）")
    lines.append("     V > 0 這半邊是凹的 -> 該降低變異數（緩手、收官）")
    return "\n".join(lines)


FIGURES = {
    "ch10_deltav": deltav_map,
    "ch10_sigmoid": sigmoid_plot,
}


def main():
    for name, fn in FIGURES.items():
        (OUT / f"{name}.txt").write_text(fn().rstrip("\n") + "\n",
                                         encoding="utf-8", newline="\n")
    print(f"寫出 {len(FIGURES)} 張圖表")


if __name__ == "__main__":
    main()
