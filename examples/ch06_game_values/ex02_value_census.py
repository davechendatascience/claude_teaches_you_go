#!/usr/bin/env python
"""第 6 章配套範例 2：圍棋局部的值到底長什麼樣？

對應章節：第 6 章 §4.5。

寫這一章的大綱時，我寫下了這句話：

    「半目與四分之一目的局部真的存在，會給實際盤面。」

然後我請程式去找。在【單一局部】裡找不到。

**然後校對這本書的時候，我把搜尋範圍拉大，又找到了一個。**
它出現在「若干個互不相連的局部的【和】」裡，不在單一局部裡。

所以這支腳本示範的是同一句話的兩面：
  * 單一連通局部 40,000 個 -> 真分數 0 個
  * 不相連的空點合成一區（＝和）7,075 個 -> 真分數 1 個（一個 1/2）

而這兩次修正都是程式推翻作者，不是作者想通 ——
**第二次還推翻了第一次下得太強的結論。**

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


def components(pts, n):
    """把一組點切成連通分量。"""
    from go_core.board import neighbors

    pts, out = set(pts), []
    while pts:
        seed = pts.pop()
        comp, stack = {seed}, [seed]
        while stack:
            q = stack.pop()
            for r in neighbors(q, n):
                if r in pts:
                    pts.discard(r)
                    comp.add(r)
                    stack.append(r)
        out.append(comp)
    return out


def _random_board(rng):
    n = rng.choice([4, 5])
    b = Board(n)
    pts = [(r, c) for r in range(n) for c in range(n)]
    for q in pts:
        b.grid[q] = rng.choices([EMPTY, BLACK, WHITE], [0.30, 0.36, 0.34])[0]
    return n, b, pts


def _classify(board, region):
    g = region_value(board, frozenset(region), max_depth=8).canonical()
    num = g.as_number(3, 6)
    if num is None:
        return "不是數", g, None
    return ("整數" if num.denominator == 1 else "真分數"), g, num


def part1_single_locals(target=40000, seed=6):
    """單一【連通】局部：其餘空點填實，讓這一塊真的孤立。"""
    print("=" * 70)
    print("1. 單一連通局部：真分數一個都沒有")
    print("=" * 70)
    rng = random.Random(seed)
    kinds, sizes, found = Counter(), Counter(), {}
    while sum(kinds.values()) < target:
        n, b, pts = _random_board(rng)
        comps = [c for c in components([q for q in pts if b.grid[q] == EMPTY], n)
                 if 1 <= len(c) <= 4]
        if not comps:
            continue
        region = rng.choice(comps)
        for q in pts:
            if b.grid[q] == EMPTY and q not in region:
                b.grid[q] = rng.choice([BLACK, WHITE])
        kind, g, num = _classify(b, region)
        kinds[kind] += 1
        sizes[len(region)] += 1
        if kind == "真分數":
            found.setdefault(num, str(b))

    total = sum(kinds.values())
    print(f"  取樣 {total} 個【單一連通】局部：\n")
    for k in ["整數", "不是數", "真分數"]:
        print(f"    {k:<6}{kinds[k]:>7}  ({100 * kinds[k] / total:5.1f}%)")
    print()
    print("  區域大小分布：",
          "、".join(f"{k} 點 {v}" for k, v in sorted(sizes.items())))
    assert kinds["真分數"] == 0, f"找到真分數：{found}"
    print()
    print("  真分數：0 個。")
    return kinds


def part1b_sums(target=7075, seed=17):
    """把盤上【所有】空點合成一區 —— 那不是一個局部，是若干局部的和。"""
    print()
    print("=" * 70)
    print("2. 若干局部的【和】：真分數出現了")
    print("=" * 70)
    rng = random.Random(seed)
    kinds, found = Counter(), {}
    tried = 0
    while sum(kinds.values()) < target and tried < 200000:
        tried += 1
        n, b, pts = _random_board(rng)
        empties = [q for q in pts if b.grid[q] == EMPTY]
        if not 1 <= len(empties) <= 4:
            continue
        try:
            kind, g, num = _classify(b, empties)
        except Exception:
            continue
        kinds[kind] += 1
        if kind == "真分數":
            found.setdefault(num, (str(b), len(components(empties, n))))

    total = sum(kinds.values())
    print(f"  取樣 {total} 個區域（多數是好幾塊不相連的空點）：\n")
    for k in ["整數", "不是數", "真分數"]:
        print(f"    {k:<6}{kinds[k]:>7}")
    print()
    assert kinds["真分數"] >= 1, "這一段的重點就是要找到它"
    for num, (board_str, n_comp) in found.items():
        print(f"  找到了：值 = {num}，而那個區域分成 {n_comp} 塊互不相連的地方")
        print(board_str)
    print("  真分數不是不會出現，是它出現在【和】裡 —— 加法是製造中間值的機器。")
    return kinds


def part1c_the_exact_one():
    """把那個 1/2 的盤面直接擺出來，不靠亂數。"""
    print()
    print("=" * 70)
    print("3. 那個 1/2，直接擺給你看")
    print("=" * 70)
    b = Board(5)
    b.place_many(BLACK, ["C5", "D5", "A4", "D4", "E4", "A3",
                         "B2", "C2", "D2", "E2", "B1"])
    b.place_many(WHITE, ["A5", "B5", "B4", "C4", "B3", "C3", "D3", "E3",
                         "A1", "C1"])
    print(b)
    empties = ["E5", "A2", "D1", "E1"]
    comps = components([b._pt(q) for q in empties], 5)
    g = region_value(b, empties, max_depth=8).canonical()
    print(f"  空點 {empties} 分成 {len(comps)} 塊互不相連的地方")
    print(f"  合起來的值 = {g!r}  =  {g.as_number(3, 6)}")
    assert len(comps) == 3
    assert g.as_number(3, 6) == Fraction(1, 2)
    print()
    print("  這就是全書唯一一個真分數，而它是一個【和】。")


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
    part1_single_locals()
    part1b_sums()
    part1c_the_exact_one()
    part2_why()
    part3_where_half_actually_lives()
    print("\n全部斷言通過。")
    print()
    print("本書大綱原本寫「半目的局部真的存在」—— 第一次搜尋說沒有。")
    print("校對時把範圍拉大，第二次搜尋說：在【和】裡有。")
    print("兩次修正都是程式推翻作者，而第二次推翻的是第一次的結論。")
