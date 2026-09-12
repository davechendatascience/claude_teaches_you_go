#!/usr/bin/env python
"""第 7 章配套範例 2：「大的先下」到底有多好？

對應章節：第 7 章 §4.6。

三個實驗，回答三個不同的問題：

  實驗一  在【圍棋實際會出現的局部】上，貪婪法是最優的嗎？
  實驗二  在【任意的小賽局】上呢？而且「局部裡挑哪一手」的判準重不重要？
  實驗三  不是最優的時候，差多少？有沒有上界？

跑法（在專案根目錄）：
    python examples/ch07_temperature/ex02_greedy.py
"""

import random
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core.cgt import Game, number, switch                        # noqa: E402
from go_core.endgame import corridor, region_value                   # noqa: E402
from go_core.temperature import (is_settled, play_greedy,            # noqa: E402
                                 play_optimal, temperature)


def gap(games, first, by="thermograph"):
    """貪婪法比最優解少賺多少（對先手方而言）。"""
    g = play_greedy(games, first, by=by)[0]
    o = play_optimal(games, first)
    return (o - g) if first == "black" else (g - o)


def part1_real_go_locals():
    print("=" * 70)
    print("1. 圍棋實際會出現的局部：走廊與開關")
    print("=" * 70)
    corridors = [region_value(*corridor(n)).canonical() for n in range(1, 5)]
    switches = [switch(a, b) for a, b in [(1, 0), (2, 0), (3, 1), (4, 0), (2, -2)]]
    pool = corridors + switches
    print(f"  題庫：{len(corridors)} 種走廊 + {len(switches)} 種開關")
    print(f"  走廊的溫度：{[str(temperature(g)) for g in corridors]}")

    random.seed(11)
    n = bad = 0
    worst = Fraction(0)
    for _ in range(300):
        games = [random.choice(pool) for _ in range(random.randint(2, 4))]
        for first in ("black", "white"):
            n += 1
            d = gap(games, first)
            if d > 0:
                bad += 1
                worst = max(worst, d)
    print(f"\n  {n} 組隨機組合：貪婪法非最優 {bad} 組，最大落差 {worst}")
    assert bad == 0
    print("  **在圍棋實際會出現的局部上，貪婪法就是最優解。**")


def rnd_game(depth, rng):
    if depth == 0 or rng.random() < 0.35:
        return number(rng.randint(-4, 4))
    return Game([rnd_game(depth - 1, rng) for _ in range(rng.randint(1, 2))],
                [rnd_game(depth - 1, rng) for _ in range(rng.randint(1, 2))])


def part2_arbitrary_games():
    print()
    print("=" * 70)
    print("2. 任意的小賽局：判準會不會影響結果？")
    print("=" * 70)
    print("  「局部裡挑哪一手」有兩種判準：")
    print("    by='mean'         挑均值最好的選項")
    print("    by='thermograph'  挑熱圖指定的那一手")
    print()
    results = {}
    for by in ("mean", "thermograph"):
        rng = random.Random(23)
        n = bad = 0
        worst = Fraction(0)
        for _ in range(1500):
            games = [rnd_game(rng.randint(1, 3), rng).canonical()
                     for _ in range(rng.randint(2, 3))]
            if all(is_settled(g) for g in games):
                continue
            for first in ("black", "white"):
                n += 1
                try:
                    d = gap(games, first, by=by)
                except RecursionError:
                    continue
                if d > 0:
                    bad += 1
                    worst = max(worst, d)
        results[by] = (n, bad, worst)
        print(f"  by={by:<12} {n} 組，非最優 {bad} 組（{100*bad/n:.1f}%），最大落差 {worst}")

    assert results["mean"][1] >= results["thermograph"][1]
    print()
    print("  兩件事同時成立：")
    print("    * 貪婪法【不是】永遠最優（在任意賽局上）。")
    print("    * 用均值挑更糟 —— 判準真的有差。")


def part3_error_bound():
    print()
    print("=" * 70)
    print("3. 落差有沒有上界？")
    print("=" * 70)
    rng = random.Random(23)
    n = bad = violations = 0
    worst_ratio = Fraction(0)
    example = None
    for _ in range(1500):
        games = [rnd_game(rng.randint(1, 3), rng).canonical()
                 for _ in range(rng.randint(2, 3))]
        if all(is_settled(g) for g in games):
            continue
        tmax = max(temperature(g) for g in games)
        for first in ("black", "white"):
            n += 1
            try:
                d = gap(games, first)
            except RecursionError:
                continue
            if d <= 0:
                continue
            bad += 1
            if d > tmax:
                violations += 1
            if tmax > 0 and d / tmax > worst_ratio:
                worst_ratio = d / tmax
                example = (d, tmax, [repr(g) for g in games], first)

    print(f"  {n} 組：非最優 {bad} 組，其中【落差 > t_max】的有 {violations} 組")
    print(f"  落差 / t_max 的最大值 = {worst_ratio}")
    assert violations == 0
    assert worst_ratio == 1
    print()
    print("  上界成立，而且是【緊的】—— 有落差剛好等於 t_max 的例子。")
    if example:
        d, tmax, gs, first = example
        print(f"\n  一個緊的例子（{'黑' if first == 'black' else '白'}先，落差 {d}，t_max {tmax}）：")
        for g in gs:
            print(f"    {g}")


def part4_why_it_fails():
    print()
    print("=" * 70)
    print("4. 貪婪法失效的原因：它看不到先手")
    print("=" * 70)
    inner = switch(1, -4)
    tricky = Game([number(2)], [inner])
    games = [switch(1, -1), tricky, switch(4, 2)]

    print("  三個局部：")
    for g in games:
        print(f"    {g!r:<20} 溫度 {temperature(g)}")
    tmax = max(temperature(g) for g in games)
    print(f"\n  三個溫度都是 {tmax} —— 貪婪法【分不出來】該先下哪個。")
    print(f"\n  但看中間那個：白下完之後剩下 {inner!r}，溫度 {temperature(inner)}")
    print(f"  {temperature(inner)} > 全局溫度 {tmax}，所以依定理 7.8，那是白的【先手】。")
    print("  貪婪法只問「現在哪裡最燙」，不問「下完之後哪裡會變燙」。")

    g = play_greedy(games, "black")[0]
    o = play_optimal(games, "black")
    print(f"\n  黑先：貪婪 {g}   最優 {o}   落差 {o - g}   t_max {tmax}")
    assert o - g == tmax == 1
    print()
    print("  這就是「先手官子先收」這條經驗法則的來源：")
    print("  一個溫度看起來不高、但下完會留下大後續的地方，實際上是先手，要提前收。")


if __name__ == "__main__":
    part1_real_go_locals()
    part2_arbitrary_games()
    part3_error_bound()
    part4_why_it_fails()
    print("\n全部斷言通過。")
