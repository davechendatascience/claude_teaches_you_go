#!/usr/bin/env python
"""第 3 章配套範例 1：Benson 迭代的逐輪追蹤。

對應章節：第 3 章 §4.6、§5.1。

這支腳本把 §5 的手算整個攤開來跑，一輪印一次盤面狀態，讓「連鎖倒塌」
這件事看得見。重點不是最後的答案，是**中間那幾輪**。

跑法（在專案根目錄）：
    python examples/ch03_life_and_death/ex01_benson_trace.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, Board, format_coord, neighbors          # noqa: E402
from go_core.benson import enclosed_regions, is_vital              # noqa: E402
from go_core.eyes import eye_report                                # noqa: E402
from go_core.strings import all_strings, find_string               # noqa: E402

N = 9
name = lambda S: "".join(sorted(format_coord(p, N) for p in S))


def verbose_benson(board, colour):
    """和 go_core.benson.benson_alive 一樣的演算法，但每一輪都印出來。"""
    X = set(all_strings(board, colour))
    R = {r for r in enclosed_regions(board, colour) if len(r) <= 8}

    print(f"  起始：{len(X)} 個棋串、{len(R)} 個（小）區域")
    for ch in sorted(X, key=name):
        vit = [name(r) for r in R if is_vital(board, r, ch)]
        print(f"      {name(ch):16s} vital 區域 {len(vit)} 個 {vit}")

    rnd = 0
    while True:
        rnd += 1
        before = (frozenset(X), frozenset(R))

        # 步驟 1：區域的鄰接棋串都必須還活著
        dropped_r = set()
        for r in R:
            nbr = {find_string(board, q)
                   for p in r for q in neighbors(p, board.n)
                   if board.grid[q] == colour}
            if any(ch not in X for ch in nbr):
                dropped_r.add(r)
        R -= dropped_r

        # 步驟 2：棋串至少要有兩個 vital 區域
        dropped_x = {ch for ch in X
                     if sum(1 for r in R if is_vital(board, r, ch)) < 2}
        X -= dropped_x

        print(f"\n  第 {rnd} 輪")
        print(f"      步驟 1 刪掉區域：{[name(r) for r in sorted(dropped_r, key=name)] or '無'}")
        print(f"      步驟 2 刪掉棋串：{[name(c) for c in sorted(dropped_x, key=name)] or '無'}")
        print(f"      剩下 {len(X)} 個棋串、{len(R)} 個區域")

        if (frozenset(X), frozenset(R)) == before:
            print(f"      -> 沒有變化，停止。")
            break
    return X


def part1_worked():
    print("=" * 74)
    print("1. §5 的盤面：四個點全部通過真眼判定式，一半的棋卻是死的")
    print("=" * 74)
    b = Board(N)
    b.place_many(BLACK, ["A2", "B2", "C2", "D2", "B1", "D1",
                         "A8", "B8", "B9", "C8", "D9", "E9"])
    print(b)
    print("\n  真眼判定式：")
    for label, pt in [("a", "A1"), ("b", "C1"), ("c", "A9"), ("d", "C9")]:
        r = eye_report(b, pt)
        print(f"      {label} = {pt}: {r['判定式']} -> {'真眼' if r['真眼'] else '假眼'}")
        assert r["真眼"]

    print("\n  Benson 迭代：")
    X = verbose_benson(b, BLACK)
    print(f"\n  結論：無條件活的是 {[name(s) for s in X]}")
    assert len(X) == 1 and name(next(iter(X))) == "A2B1B2C2D1D2"
    print("  上面那兩塊，四個真眼裡佔了兩個，一樣死。差別只在 D8 那一個空點。")


def part2_cascade_and_fix():
    print()
    print("=" * 74)
    print("2. 連鎖倒塌，以及四顆子如何同時救活兩塊棋")
    print("=" * 74)

    for title, stones in [
        ("倒塌前", ["A2", "B1", "B2", "C2", "D1", "E1"]),
        ("補強後", ["A2", "B1", "B2", "C2", "D1", "E1", "E2", "F2", "G1", "G2"]),
    ]:
        b = Board(N)
        b.place_many(BLACK, stones)
        print(f"\n--- {title}（{len(stones)} 顆子）---")
        X = verbose_benson(b, BLACK)
        print(f"  無條件活：{[name(s) for s in sorted(X, key=name)] or '無'}")

    b1, b2 = Board(N), Board(N)
    b1.place_many(BLACK, ["A2", "B1", "B2", "C2", "D1", "E1"])
    b2.place_many(BLACK, ["A2", "B1", "B2", "C2", "D1", "E1", "E2", "F2", "G1", "G2"])
    from go_core.benson import benson_alive
    assert len(benson_alive(b1, BLACK)) == 0
    assert len(benson_alive(b2, BLACK)) == 2

    print("\n  請注意方向：那四顆子下在【右邊】，救活的卻是【兩塊】。")
    print("  左邊一顆子都沒加，卻從死變活 —— 因為它的第二個眼終於站得住了。")


if __name__ == "__main__":
    part1_worked()
    part2_cascade_and_fix()
    print("\n全部斷言通過。")
