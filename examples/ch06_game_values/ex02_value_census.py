#!/usr/bin/env python
"""第 6 章配套範例 2：圍棋局部的值到底長什麼樣？

對應章節：第 6 章 §4.5。

寫這一章的大綱時，我寫下了這句話：

    「半目與四分之一目的局部真的存在，會給實際盤面。」

然後我請程式去找。找不到。

這支腳本重跑那次普查。它的結論修正了本書自己的大綱 ——
半目不在【值】裡，在【均值】裡（第 7 章）。

跑法（在專案根目錄）：
    python examples/ch06_game_values/ex02_value_census.py
"""

import random
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, EMPTY, WHITE, Board                 # noqa: E402
from go_core.cgt import Game, STAR, number                     # noqa: E402
from go_core.endgame import corridor, region_value             # noqa: E402


def part1_census(samples=2500, seed=17):
    print("=" * 70)
    print("1. 普查：隨機小局部的值屬於哪一類")
    print("=" * 70)
    random.seed(seed)
    kinds = Counter()
    shapes = Counter()
    fractions_found = {}
    for _ in range(samples):
        n = random.choice([4, 5])
        b = Board(n)
        pts = [(r, c) for r in range(n) for c in range(n)]
        for p in pts:
            b.grid[p] = random.choices([EMPTY, BLACK, WHITE], [0.30, 0.36, 0.34])[0]
        empties = [p for p in pts if b.grid[p] == EMPTY]
        if not 1 <= len(empties) <= 4:
            continue
        try:
            g = region_value(b, frozenset(empties), max_depth=8).canonical()
        except Exception:
            continue
        num = g.as_number(3, 6)
        if num is None:
            kinds["不是數"] += 1
            shapes[repr(g)[:20]] += 1
        elif num.denominator == 1:
            kinds["整數"] += 1
        else:
            kinds["真分數"] += 1
            fractions_found.setdefault(num, str(b))

    total = sum(kinds.values())
    print(f"  取樣 {total} 個局部：\n")
    for k in ["整數", "不是數", "真分數"]:
        pct = 100 * kinds[k] / max(total, 1)
        print(f"    {k:<6}{kinds[k]:>6}  ({pct:5.1f}%)")
    print()
    print("  最常見的幾種「不是數」的值：")
    for shape, cnt in shapes.most_common(6):
        print(f"    {shape:<24}{cnt:>5}")

    assert total > 200
    assert kinds["真分數"] == 0, f"找到真分數：{fractions_found}"
    print()
    print("  真分數：0 個。")
    return total


def part2_why():
    print()
    print("=" * 70)
    print("2. 為什麼？")
    print("=" * 70)
    print("  依簡單性規則（定理 6.8），要得到 1/2 需要 {0 | 1}：")
    print("  黑的最佳選項是 0、白的最佳選項是 1，而且【黑的比較小】。")
    print()
    print("  翻譯回棋：黑動一手虧、白動一手也虧，而且虧的量剛好把值卡在半目。")
    print("  在日本規則的記分法下，這種配置很難出現 ——")
    print("  一個局部只要有人動了會賺，它就變成「熱」的（不是數）；")
    print("  而如果雙方動了都虧，通常整個局部早就定型了，值是整數。")
    print()
    print("  抽象地說，1/2 當然存在：")
    half = Game([number(0)], [number(1)])
    print(f"    {{0|1}} = {half.as_number()}")
    assert half.as_number() == Fraction(1, 2)
    print("  問題不是「這個值存不存在」，而是「圍棋局部會不會產生它」。")
    print("  前者是數學，後者是經驗 —— 兩者的證據標準不一樣。")


def part3_where_half_actually_lives():
    print()
    print("=" * 70)
    print("3. 那半目在哪裡？在【均值】裡")
    print("=" * 70)
    board, region = corridor(2)
    c2 = region_value(board, region).canonical()
    half = number(Fraction(1, 2))
    print(f"  長度 2 的走廊：{c2!r}")
    print(f"    它 > 1/2 嗎？{c2 > half}")
    print(f"    它 < 1/2 嗎？{c2 < half}")
    print(f"    它 = 1/2 嗎？{c2 == half}")
    assert not (c2 > half) and not (c2 < half) and not (c2 == half)
    print("    三個都是 False —— 它和 1/2 的關係是【混】。")
    print()
    print("  但如果雙方在這裡輪流下到底，平均的結果是半目：")
    print("    黑先：黑封口，得 1 目。")
    print("    白先：白擠進來，剩一個單官，約 0 目。")
    print("    平均 = (1 + 0) / 2 = 1/2。")
    print()
    print("  那個「平均」就是第 7 章的【均值】m(G)。")
    print("  而 (1 - 0) / 2 = 1/2 是【溫度】t(G) —— 現在下一手能賺多少。")
    print()
    print("  一個賽局，兩個數：均值管形勢判斷，溫度管收官順序。")


if __name__ == "__main__":
    part1_census()
    part2_why()
    part3_where_half_actually_lives()
    print("\n全部斷言通過。")
    print()
    print("本書大綱原本寫「半目的局部真的存在」。修正它的是程式，不是作者。")
