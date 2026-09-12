#!/usr/bin/env python
"""產生第 13 章用到的 figures/*.txt。（跑完約需一分鐘）

三張表：
  * ch13_equivalence  定理 13.2 在隨機對局上的驗證
  * ch13_komi         3 路盤的公平貼目：數子 9、數目 5
  * ch13_moves        手數差 b-w 的分佈 —— 貼目那一目差的來源
"""

import random
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.setrecursionlimit(200000)
sys.path.insert(0, str(ROOT))

from go_core.board import BLACK, Board                               # noqa: E402
from go_core.minimax import Solver                                   # noqa: E402
from go_core.score import (dame, random_finished_game,                # noqa: E402
                           solve_japanese)

OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)

GAMES = 300
SEED = 1313


def _sample():
    rng = random.Random(SEED)
    rows = []
    for _ in range(GAMES):
        g = random_finished_game(9, rng)
        c, j, gap, md, ok = g.check_equivalence()
        rows.append((c, j, gap, md, ok, g.moves[BLACK], g.moves[2],
                     g.prisoners[BLACK], g.prisoners[2],
                     len(dame(g.board))))
    return rows


ROWS = _sample()


def equivalence_table():
    out = [f"  {'黑手數 b':>9}{'白手數 w':>9}{'黑提子':>8}{'白提子':>8}"
           f"{'C(數子)':>9}{'J(數目)':>9}{'C-J':>6}{'b-w':>6}",
           "  " + "-" * 64]
    for r in ROWS[:10]:
        c, j, gap, md, ok, b, w, pb, pw, d = r
        out.append(f"  {b:>9}{w:>9}{pb:>8}{pw:>8}{c:>9.0f}{j:>9.0f}"
                   f"{gap:>6.0f}{md:>6}")
    bad = sum(1 for r in ROWS if not r[4])
    out.append("")
    out.append(f"  以上是前 10 局。全部 {len(ROWS)} 局裡，"
               f"C - J != b - w 的有 {bad} 局。")
    out.append(f"  終局時還留著單官的有 {sum(1 for r in ROWS if r[9] > 0)} 局。")
    return "\n".join(out)


def komi_table():
    out = [f"  {'手數上限':>9}{'數子 C':>9}{'數目 J':>9}{'差':>6}", "  " + "-" * 34]
    for ply in [11, 13, 15, 17]:
        s = Solver(komi=0.0, max_ply=ply)
        c, _ = s.search(Board(3), BLACK)
        j, _, _ = solve_japanese(Board(3), BLACK, komi=0.0, max_ply=ply)
        out.append(f"  {ply:>9}{c:>9.0f}{j:>9.0f}{c - j:>6.0f}")
    out.append("")
    out.append("  3 路盤的公平貼目：數子 9、數目 5。")
    out.append("")
    out.append("  兩邊的 C 都是 9（黑本來就拿得走整個棋盤），差別全在手數：")
    out.append("  數目規則下的最優對局是黑 6 手、白 2 手，b - w = 4，")
    out.append("  於是 J = C - (b - w) = 9 - 4 = 5。貼目的差就是手數的差。")
    out.append("")
    out.append("  白為什麼只下兩手就虛手？因為在數目規則下，")
    out.append("  往必死的地方多放一顆子，就是白送對方一個提子。")
    return "\n".join(out)


def moves_table():
    diffs = [r[3] for r in ROWS]
    counter = Counter(diffs)
    out = [f"  {GAMES} 局隨機 9 路對局（單官都填完）裡，手數差 b - w 的分佈：", "",
           f"  {'b - w':>7}{'局數':>7}{'':>3}"]
    for d in sorted(counter):
        bar = "#" * max(1, round(counter[d] / max(counter.values()) * 40))
        out.append(f"  {d:>7}{counter[d]:>7}   {bar}")
    out.append("")
    out.append(f"  平均 {statistics.mean(diffs):.2f}、中位數 "
               f"{statistics.median(diffs):.0f}、範圍 {min(diffs)} 到 {max(diffs)}")
    out.append("")
    out.append("  中位數是 1 —— 黑先，所以在勢均力敵的對局裡黑通常多下一手。")
    out.append("  這就是中國貼目比日本貼目多【一目】的來源。")
    return "\n".join(out)


FIGURES = {
    "ch13_equivalence": equivalence_table,
    "ch13_komi": komi_table,
    "ch13_moves": moves_table,
}


def main():
    for name, fn in FIGURES.items():
        (OUT / f"{name}.txt").write_text(fn().rstrip("\n") + "\n",
                                         encoding="utf-8", newline="\n")
        print(f"  寫出 {name}.txt")


if __name__ == "__main__":
    main()
