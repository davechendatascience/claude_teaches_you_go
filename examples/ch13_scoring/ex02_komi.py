#!/usr/bin/env python
"""第 13 章配套範例 2：3 路盤的兩個公平貼目。

對應章節：第 13 章 §4.3、§5.3。

第 10 章的結論是「貼目就是 V(空盤)」，而那一章算的是**數子**規則：3 路盤 9。
有了定理 13.2，同一個棋盤也可以用**數目**規則解，因為

    J = C - (b - w)

而 (b - w) 只要沿路加減就好（黑落子 +1、白落子 -1，虛手不算）。
狀態只多帶一個整數，不必記提子數。

結果：**數子的公平貼目 9，數目的公平貼目 5。**
而兩套規則走出兩個完全不同的終局 —— 規則改變的不是分數，是「什麼時候該停手」。

跑法（在專案根目錄）：
    python examples/ch13_scoring/ex02_komi.py
"""

import sys
from pathlib import Path

sys.setrecursionlimit(200000)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, WHITE, Board, format_coord, opposite      # noqa: E402
from go_core.minimax import Solver, legal_moves                      # noqa: E402
from go_core.score import ScoredGame, solve_japanese                 # noqa: E402

MAX_PLY = 15


def converge():
    print("=" * 66)
    print("1. 兩套規則各自的公平貼目")
    print("=" * 66)
    print(f"  {'手數上限':>9}{'數子 C':>9}{'數目 J':>9}{'差':>6}{'節點':>10}")
    print("  " + "-" * 44)
    for ply in [11, 13, 15, 17]:
        s = Solver(komi=0.0, max_ply=ply)
        c, _ = s.search(Board(3), BLACK)
        j, _, nodes = solve_japanese(Board(3), BLACK, komi=0.0, max_ply=ply)
        print(f"  {ply:>9}{c:>9.0f}{j:>9.0f}{c - j:>6.0f}{nodes:>10}")

    s = Solver(komi=0.0, max_ply=MAX_PLY)
    c, cmv = s.search(Board(3), BLACK)
    j, jmv, _ = solve_japanese(Board(3), BLACK, komi=0.0, max_ply=MAX_PLY)
    assert c == 9 and j == 5
    print(f"\n  數子的公平貼目 = {c:.0f}，數目的公平貼目 = {j:.0f}")
    print(f"  兩套規則的最佳第一手都是 "
          f"{format_coord(cmv, 3)} / {format_coord(jmv, 3)}（天元）")

    # 各自貼掉之後都歸零 —— 那就是「公平」的定義
    assert Solver(komi=c, max_ply=MAX_PLY).search(Board(3), BLACK)[0] == 0
    assert solve_japanese(Board(3), BLACK, komi=j, max_ply=MAX_PLY)[0] == 0
    print("  各自貼掉之後 V(空盤) 都是 0 —— 那就是「公平」的定義（第 10 章）。")


def play_out(rule):
    """把某一套規則的最優對局走完，回傳 ScoredGame 與著手序列。"""
    g = ScoredGame(3)
    colour, ko, passes, ply, pv = BLACK, None, 0, 0, []
    s = Solver(komi=0.0, max_ply=MAX_PLY)
    while ply < MAX_PLY and passes < 2:
        if rule == "chinese":
            _, mv = s.search(g.board, colour, passes=passes, ko=ko, ply=ply)
        else:
            _, mv, _ = solve_japanese(g.board, colour, komi=0.0,
                                      max_ply=MAX_PLY - ply)
        if mv is None:
            pv.append((colour, None))
            g.pass_move()
            passes += 1
            ko = None
        else:
            for p, child, nk in legal_moves(g.board, colour, ko):
                if p == mv:
                    g.play(colour, format_coord(p, 3))
                    ko = nk
                    break
            pv.append((colour, mv))
            passes = 0
        colour = opposite(colour)
        ply += 1
    return g, pv


def two_endings():
    print("\n" + "=" * 66)
    print("2. 同一個棋盤，兩套規則走出兩個終局")
    print("=" * 66)
    for rule, name in [("chinese", "數子"), ("japanese", "數目")]:
        g, pv = play_out(rule)
        r = g.report()
        print(f"\n  --- {name}規則的最優對局（{len(pv)} 手）---")
        print("  " + " ".join(
            f"{'黑' if c == BLACK else '白'}"
            f"{format_coord(p, 3) if p else '虛手'}" for c, p in pv))
        print("  " + str(g.board).replace("\n", "\n  "))
        print(f"    手數 (黑,白) = {r['moves']}   盤上子數 = {r['stones']}")
        print(f"    地 = {r['territory']}   提子 = {r['prisoners']}")
        print(f"    C = {r['chinese']:+.0f}   J = {r['japanese']:+.0f}   "
              f"C-J = {r['gap']:+.0f}   b-w = {r['move_diff']:+d}")
        assert r["gap"] == r["move_diff"]
        assert r["chinese"] == 9
        if rule == "japanese":
            assert r["moves"] == (6, 2) and r["japanese"] == 5

    print("\n  白的行為完全不同：")
    print("    數子規則下白一路下到底 —— 填了不用付錢。")
    print("    數目規則下白下兩手就虛手 —— 每多一顆就是多送一個提子。")
    print("\n  規則改變的不是分數，是【什麼時候該停手】。")


def main():
    converge()
    two_endings()


if __name__ == "__main__":
    main()
