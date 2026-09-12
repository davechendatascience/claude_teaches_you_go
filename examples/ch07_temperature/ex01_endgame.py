#!/usr/bin/env python
"""第 7 章配套範例 1：把一個收官盤面拆開、算溫度、排序、收完。

對應章節：第 7 章 §4.2、§4.3、§5.1。

這支腳本走完收官的完整流程：

    盤面 -> 切成局部 -> 各算 (溫度, 均值) -> 依溫度排序 -> 收 -> 驗證

而且每一步都和完全搜尋的最優解比對。

跑法（在專案根目錄）：
    python examples/ch07_temperature/ex01_endgame.py
"""

import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, WHITE, Board                              # noqa: E402
from go_core.endgame import corridor, region_value                    # noqa: E402
from go_core.temperature import (analyse, mean, play_greedy,          # noqa: E402
                                 play_optimal, temperature, thermograph)

BOARD_BLACK = ["A2", "B2", "A8", "B8", "C8", "H1", "H2"]
BOARD_WHITE = ["C1", "C2", "D9", "D8", "J3", "H3"]
REGIONS = {"左下(長2)": ["A1", "B1"],
           "左上(長3)": ["A9", "B9", "C9"],
           "右下(長2)": ["J1", "J2"]}


def build():
    b = Board(9)
    b.place_many(BLACK, BOARD_BLACK)
    b.place_many(WHITE, BOARD_WHITE)
    return b


def part1_split():
    print("=" * 70)
    print("1. 切成局部，各算兩個數")
    print("=" * 70)
    b = build()
    print(b)
    games = []
    print(f"\n{'局部':<12}{'賽局值':<26}{'溫度':>8}{'均值':>8}")
    print("-" * 56)
    for name, region in REGIONS.items():
        g = region_value(b, region).canonical()
        games.append(g)
        t, m = analyse(g)
        print(f"{name:<12}{repr(g):<26}{str(t):>8}{str(m):>8}")
    return games


def part2_judge_and_order(games):
    print()
    print("=" * 70)
    print("2. 兩個數，兩種用途")
    print("=" * 70)
    total = sum(mean(g) for g in games)
    print(f"  形勢判斷（均值總和）：黑 +{total}")
    assert total == Fraction(9, 4)
    print()
    print("  收官順序（依溫度遞減）：")
    order = sorted(range(len(games)), key=lambda i: -temperature(games[i]))
    names = list(REGIONS)
    for rank, i in enumerate(order, 1):
        print(f"    第 {rank} 順位  {names[i]:<12} 溫度 {temperature(games[i])}")
    print()
    print("  注意左下與右下溫度相同（都是 1/2）—— 它們是【見合】（第 6 章 §4.6）。")
    print("  你收一個我收一個，總帳不變。真正要爭的只有左上那一個。")
    return total


def part3_play_it_out(games, total):
    print()
    print("=" * 70)
    print("3. 收完，並與完全搜尋比對")
    print("=" * 70)
    names = list(REGIONS)
    for first in ("black", "white"):
        greedy, log = play_greedy(games, first)
        best = play_optimal(games, first)
        who = "黑" if first == "black" else "白"
        print(f"\n  --- {who}先 ---")
        for step, (colour, i, t) in enumerate(log, 1):
            c = "黑" if colour == "black" else "白"
            print(f"    第 {step} 手  {c} 下 {names[i]:<12} 當時溫度 {t}")
        print(f"    貪婪法 {greedy}   完全搜尋 {best}   "
              f"{'一致' if greedy == best else '不一致'}")
        assert greedy == best

    tmax = max(temperature(g) for g in games)
    bfirst = play_optimal(games, "black")
    wfirst = play_optimal(games, "white")
    print()
    print(f"  黑先 {bfirst} > 均值 {total} > 白先 {wfirst}")
    print(f"  黑先 - 均值 = {bfirst - total} = t_max = {tmax}")
    assert bfirst == 3 and wfirst == 2
    assert bfirst - total == tmax
    print("  「先手多賺一個最高溫度」—— 在見合成對的盤面上，這個等式剛好成立。")


def part4_thermograph():
    print()
    print("=" * 70)
    print("4. 熱圖的轉折點 = 後續手段的溫度")
    print("=" * 70)
    c2 = region_value(*corridor(2)).canonical()
    c3 = region_value(*corridor(3)).canonical()
    print(f"  C(2) = {c2!r}   溫度 {temperature(c2)}")
    print(f"  C(3) = {c3!r}   溫度 {temperature(c3)}")
    print()
    print(f"  C(3) 的熱圖：")
    print(f"    {'稅率 t':>8}{'左牆':>8}{'右牆':>8}   註")
    prev_r = None
    for t, left, right in thermograph(c3, [Fraction(k, 8) for k in range(9)]):
        note = ""
        if prev_r is not None and right != prev_r and prev_r == 1:
            note = f"  <- 轉折！t = {t} 附近，而 t(C(2)) = {temperature(c2)}"
        if left == right:
            note = "  <- 兩牆相碰 = 溫度"
        print(f"    {str(t):>8}{str(left):>8}{str(right):>8}{note}")
        prev_r = right

    print()
    print("  右牆在 t < 1/2 時是【平的】—— 因為白擠進去之後還想再擠一次，")
    print("  付的稅被後續的收益抵銷了。過了 t(C(2)) = 1/2，後續不划算，牆才開始上升。")
    print()
    print("  【熱圖的轉折點，就是後續手段的溫度。】")
    print("  而「這一手是不是先手」，讀的正是這個轉折點（§4.5 定理 7.8）。")
    assert temperature(c2) == Fraction(1, 2)
    assert temperature(c3) == Fraction(3, 4)


if __name__ == "__main__":
    gs = part1_split()
    tot = part2_judge_and_order(gs)
    part3_play_it_out(gs, tot)
    part4_thermograph()
    print("\n全部斷言通過。")
