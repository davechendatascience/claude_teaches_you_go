#!/usr/bin/env python
"""第 13 章配套範例 1：數子與數目差在哪裡。

對應章節：第 13 章 §4.1、§4.2、§4.4、§4.6、§5.2。

中國規則數子（子 + 地），日本規則數目（地 + 提子）。兩套完全不同的數法，
結果「幾乎總是一樣」—— 而這支腳本把「幾乎」變成一個式子：

    C - J = b - w          （定理 13.2）

其中 b、w 是黑白各自下過幾顆子（含後來被提掉的）。

跑法（在專案根目錄）：
    python examples/ch13_scoring/ex01_equivalence.py
"""

import random
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.setrecursionlimit(100000)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, WHITE, Board, format_coord, opposite       # noqa: E402
from go_core.benson import benson_alive                               # noqa: E402
from go_core.score import (ScoredGame, chinese_score, dame,            # noqa: E402
                           japanese_score, random_finished_game,
                           stones, territory)

GAMES = 300
SEED = 1313


def dame_demo():
    print("=" * 70)
    print("1. 單官：兩套規則分家的地方")
    print("=" * 70)
    g = ScoredGame(7)
    for r in range(1, 8):
        g.board.place(BLACK, f"C{r}")
        g.board.place(WHITE, f"E{r}")
    print(g.board)
    tb, tw = territory(g.board)
    d = dame(g.board)
    print(f"  黑地 {tb}、白地 {tw}、單官 {len(d)} 個："
          f"{sorted(format_coord(p, 7) for p in d)}")
    print(f"  C = {chinese_score(g.board):+.0f}   "
          f"J = {japanese_score(g.board):+.0f}   （都是和局）")
    assert (tb, tw) == (14, 14) and len(d) == 7
    assert chinese_score(g.board) == japanese_score(g.board) == 0

    colour = BLACK
    while True:
        left = sorted(dame(g.board))
        if not left:
            break
        g.play(colour, format_coord(left[0], 7))
        colour = opposite(colour)

    r = g.report()
    print(f"\n  黑先填、交替填完之後：黑填 {r['moves'][0]} 個、"
          f"白填 {r['moves'][1]} 個")
    print(f"    C = {r['chinese']:+.0f}   J = {r['japanese']:+.0f}   "
          f"C-J = {r['gap']:+.0f}   b-w = {r['move_diff']:+d}")
    assert r["moves"] == (4, 3)
    assert r["chinese"] == 1 and r["japanese"] == 0
    assert r["gap"] == r["move_diff"] == 1
    print("\n  填單官在【數目】下不改分數，在【數子】下改了 1 目。")
    print("  七是奇數，黑先填 -> 黑多填一個 -> 差一目。")
    print("  19 路盤的貼目差一目，機制就是這個。")


def theorem():
    print("\n" + "=" * 70)
    print("2. 定理 13.2：C - J = b - w")
    print("=" * 70)
    rng = random.Random(SEED)
    rows, bad = [], 0
    for _ in range(GAMES):
        g = random_finished_game(9, rng)
        c, j, gap, md, ok = g.check_equivalence()
        bad += not ok
        rows.append((g.moves[BLACK], g.moves[WHITE],
                     g.prisoners[BLACK], g.prisoners[WHITE],
                     c, j, gap, md, len(dame(g.board))))

    print(f"  {'黑手數':>7}{'白手數':>7}{'黑提子':>7}{'白提子':>7}"
          f"{'C':>7}{'J':>7}{'C-J':>6}{'b-w':>6}")
    print("  " + "-" * 54)
    for r in rows[:10]:
        print(f"  {r[0]:>7}{r[1]:>7}{r[2]:>7}{r[3]:>7}"
              f"{r[4]:>7.0f}{r[5]:>7.0f}{r[6]:>6.0f}{r[7]:>6}")
    print(f"\n  {GAMES} 局裡 C - J != b - w 的有 {bad} 局")
    print(f"  終局時還留著單官的有 {sum(1 for r in rows if r[8] > 0)} 局")
    assert bad == 0

    diffs = sorted(r[7] for r in rows)
    counter = Counter(diffs)
    print(f"\n  b - w 的分佈：")
    for d in sorted(counter):
        bar = "#" * max(1, round(counter[d] / max(counter.values()) * 36))
        print(f"    {d:>3}  {counter[d]:>3}  {bar}")
    print(f"\n  平均 {statistics.mean(diffs):.2f}、"
          f"中位數 {statistics.median(diffs):.0f}、"
          f"範圍 {min(diffs)} 到 {max(diffs)}")
    assert statistics.median(diffs) == 1
    print("  中位數 1 —— 黑先，所以黑通常多下一手。那就是貼目的一目差。")

    ideal = sum(1 for d in diffs if d in (0, 1))
    print(f"\n  落在理想化的 {{0, 1}} 裡的：{ideal}/{GAMES} = {ideal/GAMES:.0%}")
    print("  理想化（不虛手、不提子、嚴格交替）給出 {0, 1}；")
    print("  實戰的寬度來自虛手、提子與劫。好模型給你中位數，")
    print("  分佈的寬度告訴你它漏了什麼。")


def dead_stones():
    print("\n" + "=" * 70)
    print("3. 死子：中國規則不必判，日本規則必須判")
    print("=" * 70)
    g = ScoredGame(7)
    for c in ["B1", "B2", "B3", "B4", "B5", "B6", "B7",
              "C7", "D7", "E7", "F7", "G7"]:
        g.board.place(BLACK, c)
    for c in ["A3", "A4"]:
        g.board.place(WHITE, c)
    placed_b, placed_w = 12, 2                    # 擺盤面用掉的「手數」
    print(g.board)
    print("  白 A3、A4 做不出兩個眼 —— 大家都同意它們死了。")
    print("  但 Benson 只給【充分條件】，它不會告訴你誰死了：")
    print(f"    Benson 判黑無條件活的棋串：{len(benson_alive(g.board, BLACK, trace=False))} 塊")
    print(f"    Benson 判白無條件活的棋串：{len(benson_alive(g.board, WHITE, trace=False))} 塊")

    print("\n  中國規則：不必判，下下去提掉就是了。")
    for mv in ["A5", "A2", "A1", "A6", "A7"]:
        if g.board.grid[g.board._pt(mv)] == 0:
            taken = g.play(BLACK, mv)
            if taken:
                print(f"    黑 {mv} 提掉 "
                      f"{sorted(format_coord(p, 7) for p in taken)}")
    r = g.report()
    b_total = placed_b + r["moves"][0]
    w_total = placed_w + r["moves"][1]
    print(f"    下完：C = {r['chinese']:+.0f}（整個 49 點的棋盤）")
    print(f"    黑總共放了 {b_total} 顆、白 {w_total} 顆")

    j_agreed = japanese_score(g.board, prisoners_black=2)
    print(f"\n  日本規則：同意那兩顆是死的，直接拿掉。")
    print(f"    J = 地 {territory(g.board)[0]} + 提子 2 = {j_agreed:+.0f}")
    print(f"\n  C - J = {r['chinese'] - j_agreed:+.0f}   "
          f"b - w = {b_total - w_total:+d}   定理 13.2 依然成立")
    assert r["chinese"] == 49
    assert j_agreed == 34
    assert r["chinese"] - j_agreed == b_total - w_total == 15
    print("\n  兩條路殊途同歸 —— 但只有一條需要人開口。")
    print("  數子把死活交給棋盤，數目把它交給棋手。")


def main():
    dame_demo()
    theorem()
    dead_stones()


if __name__ == "__main__":
    main()
