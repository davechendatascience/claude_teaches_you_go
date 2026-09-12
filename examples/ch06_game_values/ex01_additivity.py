#!/usr/bin/env python
"""第 6 章配套範例 1：可加性，以及走廊那一族值。

對應章節：第 6 章 §4.2、§4.5、§4.7。

本章最重要的一句話是「局部可以相加」。這支腳本用兩種【完全不同】的方式
算同一個盤面，看它們合不合：

    方法 A  分別算兩個局部的值，然後用 CGT 的加法規則相加
    方法 B  把兩個局部的所有點當成一整塊，窮舉所有下法

如果定理 6.4 是對的，兩者必須相等。

跑法（在專案根目錄）：
    python examples/ch06_game_values/ex01_additivity.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, WHITE, Board                       # noqa: E402
from go_core.cgt import STAR, ZERO, Game, number              # noqa: E402
from go_core.endgame import corridor, region_value            # noqa: E402


def part1_corridors():
    print("=" * 70)
    print("1. 走廊：由真實盤面窮舉出來的一族值")
    print("=" * 70)
    values = {}
    for n in range(1, 6):
        board, region = corridor(n)
        raw = region_value(board, region)
        g = raw.canonical()
        values[n] = g
        print(f"  長度 {n}: {g!r}")
        assert raw == g, "化簡不應該改變值"

    print()
    print("  遞迴一眼就看得出來：C(1) = *，C(n) = {n-1 | C(n-1)}")
    assert values[1] == STAR
    for n in range(2, 6):
        assert values[n] == Game([number(n - 1)], [values[n - 1]]), n
    print("  五個長度全部符合。")
    print()
    print("  翻譯回棋：黑封口得 n-1 目（封口那一手佔掉一格）；")
    print("            白擠進來，剩下的就是短一格的同一種走廊。")
    return values


def part2_additivity(values):
    print()
    print("=" * 70)
    print("2. 可加性：分開算再相加  vs  擺在一起整盤算")
    print("=" * 70)

    cases = [
        ("兩條長度 2 的走廊",
         ["A2", "B2", "A8", "B8"], ["C1", "C2", "C9", "C8"],
         ["A1", "B1", "A9", "B9"], values[2], values[2]),
        ("長度 3 + 長度 1",
         ["A2", "B2", "C2", "A8"], ["D1", "D2", "B9", "B8"],
         ["A1", "B1", "C1", "A9"], values[3], values[1]),
        ("長度 2 + 長度 2（上下對調）",
         ["A2", "B2", "A8", "B8"], ["C1", "C2", "C9", "C8"],
         ["A9", "B9", "A1", "B1"], values[2], values[2]),
    ]
    for label, blk, wht, region, g1, g2 in cases:
        b = Board(9)
        b.place_many(BLACK, blk)
        b.place_many(WHITE, wht)
        together = region_value(b, region).canonical()
        apart = (g1 + g2).canonical()
        ok = apart == together
        print(f"\n  --- {label} ---")
        print(f"    分開算再相加 : {apart!r}")
        print(f"    整盤一起算   : {together!r}")
        print(f"    相等嗎       : {ok}")
        assert ok

    print()
    print("  三組都相等。定理 6.4（可加性）在真實盤面上成立。")
    print("  注意第三組：只是把兩個局部的順序對調，值不變 —— 這就是交換律。")


def part3_star():
    print()
    print("=" * 70)
    print("3. 星：不值目，但值一個手番")
    print("=" * 70)
    print(f"  *      = {STAR!r}   勝負類別 {STAR.outcome()}")
    print(f"  0      = {ZERO!r}   勝負類別 {ZERO.outcome()}")
    print(f"  * == 0 ? {STAR == ZERO}      * > 0 ? {STAR > ZERO}      * < 0 ? {STAR < ZERO}")
    print("  三個都是 False —— * 和 0 的關係是【混】（fuzzy）。")
    assert STAR != ZERO and not (STAR > ZERO) and not (STAR < ZERO)

    print()
    print("  單官的奇偶：")
    total = ZERO
    for k in range(1, 7):
        total = (total + STAR).canonical()
        parity = "奇數 -> 先手有利" if k % 2 else "偶數 -> 後手有利"
        print(f"    {k} 個單官：值 = {total!r:3s}  {total.outcome():5s}  {parity}")
        assert (total == ZERO) == (k % 2 == 0)

    print()
    print("  兩個單官的和是 0（見合）。這是「見合則緩」最單純的形式。")


def part4_simplicity_rule():
    print()
    print("=" * 70)
    print("4. 簡單性規則：半目與四分之一目是怎麼冒出來的")
    print("=" * 70)
    from fractions import Fraction
    cases = [(0, 2), (0, 1), (0, Fraction(1, 2)), (Fraction(1, 2), 1),
             (-1, 1), (1, 3), (Fraction(1, 4), Fraction(1, 2))]
    print(f"{'左選項':>8}{'右選項':>10}{'值':>10}   為什麼")
    print("-" * 60)
    for a, b in cases:
        g = Game([number(a)], [number(b)])
        v = g.as_number()
        why = ("中間有整數" if v.denominator == 1
               else f"中間沒有整數，也沒有分母 {v.denominator // 2} 的數")
        print(f"{str(a):>8}{str(b):>10}{str(v):>10}   {why}")
    print()
    print("  搜尋順序是 1, 1/2, 1/4, 1/8, ... —— 一路二分。")
    print("  所以圍棋會有半目、四分之一目，永遠不會有三分之一目。")

    assert Game([number(0)], [number(1)]).as_number() == Fraction(1, 2)
    assert Game([number(0)], [number(Fraction(1, 2))]).as_number() == Fraction(1, 4)
    assert Game([number(0)], [number(2)]).as_number() == 1


if __name__ == "__main__":
    vals = part1_corridors()
    part2_additivity(vals)
    part3_star()
    part4_simplicity_rule()
    print("\n全部斷言通過。")
