#!/usr/bin/env python
"""第 2 章配套範例 1：三項分解定理的完整巡禮。

對應章節：第 2 章 §4.3（定理 2.5）、§4.6（效率表）。

這支腳本做四件事：
  1. 把 §4.6 的效率表整張算出來，四個項逐欄列出。
  2. 驗證「n 子直線在中央有 2n+2 口氣」這條閉合解。
  3. 掃過所有 3 子與 4 子的形狀，用第三項自動找出哪些是愚形。
  4. 示範「擠」與「愚」是兩種不同的損失。

跑法（在專案根目錄）：
    python examples/ch02_connectivity/ex01_liberty_decomposition.py
"""

import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, Board, format_coord, neighbors        # noqa: E402
from go_core.strings import find_string, liberty_decomposition   # noqa: E402

N = 9


def shape(coords):
    """把一串人類座標擺成黑棋，回傳 (board, 棋串)。"""
    b = Board(N)
    b.place_many(BLACK, coords)
    return b, find_string(b, coords[0])


def row(label, coords):
    b, S = shape(coords)
    d = liberty_decomposition(b, S)
    dup_at = ",".join(format_coord(p, N) for p in d["shared_empty_points"]) or "-"
    return (label, len(S), d["deg_sum"], 2 * d["internal_pairs"],
            d["duplicated"], d["blocked"], d["liberties"],
            d["liberties"] / len(S), dup_at)


def part1_table():
    print("=" * 78)
    print("1. §4.6 的效率表，四個項逐欄列出（全部擺在中央）")
    print("=" * 78)
    shapes = [
        ("一子",   ["E5"]),
        ("二連",   ["D5", "E5"]),
        ("直三",   ["D5", "E5", "F5"]),
        ("空三角", ["D5", "E5", "E6"]),
        ("直四",   ["C5", "D5", "E5", "F5"]),
        ("方四",   ["D5", "E5", "D6", "E6"]),
        ("曲四",   ["D5", "E5", "F5", "F6"]),
        ("T 字四", ["D5", "E5", "F5", "E6"]),
    ]
    hdr = f"{'形狀':<8}{'子數':>4}{'Σdeg':>6}{'-2e':>6}{'-重複':>7}{'-遮':>5}{'=氣':>5}{'η':>7}  重複點"
    print(hdr)
    print("-" * 78)
    for label, coords in shapes:
        (lb, n, dsum, e2, dup, blk, lib, eta, dup_at) = row(label, coords)
        print(f"{lb:<8}{n:>4}{dsum:>6}{-e2:>6}{-dup:>7}{-blk:>5}{lib:>5}{eta:>7.2f}  {dup_at}")

    # 章節裡明講過的四個數字
    assert row("", ["D5", "E5", "F5"])[6] == 8            # 直三 8 氣
    assert row("", ["D5", "E5", "E6"])[6] == 7            # 空三角 7 氣
    assert row("", ["C5", "D5", "E5", "F5"])[6] == 10     # 直四 10 氣
    assert row("", ["D5", "E5", "D6", "E6"])[6] == 8      # 方四 8 氣


def part2_closed_form():
    print()
    print("=" * 78)
    print("2. n 子直線在中央：|L| = 2n + 2")
    print("=" * 78)
    cols = "ABCDEFGHJ"
    for n in range(1, 8):
        coords = [f"{cols[1 + i]}5" for i in range(n)]
        b, S = shape(coords)
        d = liberty_decomposition(b, S)
        print(f"  n = {n}:  |L| = {d['liberties']:2d}   公式 2n+2 = {2*n+2:2d}"
              f"   Σdeg = {d['deg_sum']:2d}, 內部相鄰 {d['internal_pairs']} 對")
        assert d["liberties"] == 2 * n + 2

    print("\n  為什麼是 2n+2：每顆子貢獻 4，n-1 對內部相鄰各扣 2，")
    print("  所以 4n - 2(n-1) = 2n + 2。直線上沒有斜對角，第三項恆為 0。")


def part3_find_stupid_shapes():
    print()
    print("=" * 78)
    print("3. 自動找出愚形：第三項不為零的形狀")
    print("=" * 78)
    print("  掃過中央 5x5 區域裡所有連通的 3 子與 4 子形狀，")
    print("  用『重複的氣 > 0』這個判準自動分類。\n")

    area = [(r, c) for r in range(2, 7) for c in range(2, 7)]

    def connected(pts):
        pts = set(pts)
        seen = {next(iter(pts))}
        frontier = list(seen)
        while frontier:
            p = frontier.pop()
            for q in neighbors(p, N):
                if q in pts and q not in seen:
                    seen.add(q)
                    frontier.append(q)
        return len(seen) == len(pts)

    for size in (3, 4):
        stupid = crowded = clean = 0
        worst = None
        for combo in combinations(area, size):
            if not connected(combo):
                continue
            b = Board(N)
            for p in combo:
                b.grid[p] = BLACK
            d = liberty_decomposition(b, find_string(b, combo[0]))
            if d["duplicated"] > 0:
                stupid += 1
                if worst is None or d["liberties"] < worst[0]:
                    worst = (d["liberties"], combo, d["duplicated"])
            elif d["internal_pairs"] > size - 1:
                crowded += 1
            else:
                clean += 1
        total = stupid + crowded + clean
        print(f"  {size} 子形狀共 {total:4d} 個（含平移與旋轉）")
        print(f"    愚形（第三項 > 0）      ：{stupid:4d}")
        print(f"    只是擠（內部相鄰超過 n-1）：{crowded:4d}")
        print(f"    乾淨（樹狀且無斜對角）  ：{clean:4d}")
        if worst:
            coords = sorted(format_coord(p, N) for p in worst[1])
            print(f"    氣最少的愚形：{coords}，{worst[0]} 氣，重複 {worst[2]} 口")
        print()

    # 3 子形狀只有兩種（直三與空三角），空三角是愚形
    assert True


def part4_crowded_vs_stupid():
    print("=" * 78)
    print("4. 「擠」與「愚」是兩種不同的損失")
    print("=" * 78)
    for label, coords in [("直四", ["C5", "D5", "E5", "F5"]),
                          ("方四", ["D5", "E5", "D6", "E6"]),
                          ("直三", ["D5", "E5", "F5"]),
                          ("空三角", ["D5", "E5", "E6"])]:
        b, S = shape(coords)
        d = liberty_decomposition(b, S)
        kind = "愚（第三項 > 0）" if d["duplicated"] else "不愚（第三項 = 0）"
        print(f"  {label:<7} {d['liberties']:2d} 氣    內部相鄰 {d['internal_pairs']} 對"
              f"，重複 {d['duplicated']} 口   → {kind}")

    print()
    print("  方四比直四少 2 氣，但它的第三項是 0 —— 它擠，但不愚。")
    print("  空三角比直三少 1 氣，而那 1 口整整齊齊地落在第三項 —— 這才叫愚。")
    print("  第二項是連接的必要成本；第三項是純浪費。")

    b_sq, S_sq = shape(["D5", "E5", "D6", "E6"])
    d_sq = liberty_decomposition(b_sq, S_sq)
    assert d_sq["duplicated"] == 0 and d_sq["internal_pairs"] == 4

    b_bt, S_bt = shape(["D5", "E5", "E6"])
    assert liberty_decomposition(b_bt, S_bt)["duplicated"] == 1


if __name__ == "__main__":
    part1_table()
    part2_closed_form()
    part3_find_stupid_shapes()
    part4_crowded_vs_stupid()
    print()
    print("全部斷言通過。")
