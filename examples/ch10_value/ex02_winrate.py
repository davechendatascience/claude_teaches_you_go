#!/usr/bin/env python
"""第 10 章配套範例 2：MCTS、勝率，以及深度懸崖。

對應章節：第 10 章 §4.4、§4.5、§4.6。

三件事：

1. **MCTS 排序先收斂，估值後收斂。** 在 3 路盤上，50 次模擬就選對天元，
   1600 次之後值卻還是 +0.34（真值 +1.0）。這就是價值網路存在的理由。

2. **AI 的緩手是 Jensen 不等式。** p = sigma(V/tau) 在 V > 0 是凹的，
   所以同樣的期望目數，變異數小的勝率高。穩穩收 19 目勝過期望 20 目但會抖。

3. **深度懸崖。** 第 8 章那個征子：深度 33 答錯、深度 34 答對，中間沒有過渡。
   而深度 33 以下的搜尋，對「有引徵」和「沒引徵」給出【一模一樣】的答案 ——
   和第 9 章那個被證明無能的影響力場一樣瞎。

跑法（在專案根目錄）：
    python examples/ch10_value/ex02_winrate.py
"""

import random
import sys
from pathlib import Path

sys.setrecursionlimit(100000)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np                                                   # noqa: E402

from go_core import BLACK, WHITE, Board, format_coord                # noqa: E402
from go_core.ladder import ladder_capture                            # noqa: E402
from go_core.mcts import describe, search                            # noqa: E402
from go_core.minimax import (expected_win_rate, move_values,          # noqa: E402
                             variance_preference, win_rate)

TAU = 6.0


def mcts_section():
    print("=" * 66)
    print("1. MCTS：排序先收斂，估值後收斂")
    print("=" * 66)
    exact = dict(move_values(Board(3), BLACK, komi=0.0, max_ply=15))
    best_exact = max(exact.values())
    print(f"  精確解：V = {best_exact:+.0f}，最佳第一手 = 天元 B2")

    print(f"\n  {'模擬次數':>8}{'選出來的手':>12}{'對嗎':>6}{'根節點的值':>12}")
    for sims in [50, 100, 200, 400, 800, 1600]:
        root, stats = search(Board(3), BLACK, simulations=sims, c=1.4,
                             rng=random.Random(7))
        top = stats[0][0]
        name = format_coord(top, 3) if top else "虛手"
        ok = "O" if name == "B2" else "X"
        print(f"  {sims:>8}{name:>12}{ok:>6}{root.w / root.n:>+12.3f}")
        assert name == "B2", sims

    root, stats = search(Board(3), BLACK, simulations=1600, c=1.4,
                         rng=random.Random(7))
    print("\n  1600 次模擬之後的訪問分佈：")
    print(describe(stats, 3))

    # 排序對不對？（和精確解比）
    order = [p for p, _, _ in stats if p is not None]
    exact_rank = sorted(order, key=lambda p: -exact[p])
    print(f"\n  MCTS 的排序：  {[format_coord(p, 3) for p in order[:5]]}")
    print(f"  精確解的排序：{[format_coord(p, 3) for p in exact_rank[:5]]}")
    assert order[0] == exact_rank[0]                    # 第一名一致
    assert exact[order[0]] == best_exact

    est = root.w / root.n
    true_scaled = best_exact / 9.0
    print(f"\n  但值呢：MCTS 估 {est:+.3f}，真值 {true_scaled:+.3f} —— "
          f"差 {true_scaled / est:.1f} 倍")
    assert est < true_scaled / 2
    print("  排序早就對了，值還差得遠。這就是價值網路要解決的問題。")


def jensen_section():
    print("\n" + "=" * 66)
    print("2. 勝率：AI 為什麼下緩手")
    print("=" * 66)
    print(f"  一目棋值多少勝率（tau = {TAU:.0f}）：")
    print(f"    {'V':>5}{'勝率':>10}{'一目 = 幾勝率':>16}")
    slopes = {}
    for v in [0, 2, 5, 10, 20, 40]:
        p = float(win_rate(v, TAU))
        slope = p * (1 - p) / TAU
        slopes[v] = slope
        print(f"    {v:>+5}{p:>10.4f}{slope:>16.5f}")
    print(f"  -> 領先 20 目時，一目只值盤面接近時的 "
          f"1/{slopes[0] / slopes[20]:.1f}")
    assert slopes[0] / slopes[20] > 7

    print(f"\n  同樣的期望目數，穩 vs 亂（tau = {TAU:.0f}, spread = 10）：")
    print(f"    {'期望目數':>8}{'穩':>10}{'亂':>10}{'差':>10}   該怎麼下")
    for mu in [-20, -10, -5, 0, 5, 10, 20]:
        steady, wild, diff = variance_preference(mu, 10, tau=TAU)
        verdict = ("求穩" if diff > 1e-9
                   else "求亂（勝負手）" if diff < -1e-9 else "一樣")
        print(f"    {mu:>+8}{steady:>10.4f}{wild:>10.4f}{diff:>+10.4f}   {verdict}")
        if mu > 0:
            assert diff > 0
        elif mu < 0:
            assert diff < 0
        else:
            assert abs(diff) < 1e-12

    steady = expected_win_rate([19], tau=TAU)
    wild = expected_win_rate([10, 30], tau=TAU)
    print(f"\n  穩穩收 +19 目：          勝率 {steady:.4f}")
    print(f"  期望 +20 目但可能 10/30：勝率 {wild:.4f}")
    print(f"  -> 少賺一目，多賺 {steady - wild:+.4f} 勝率")
    assert steady > wild and abs((steady - wild) - 0.0423) < 0.001
    print("  AI 送你那一目不是失誤，是買保險。")

    # 凹凸性與 tau 無關
    for tau in [0.5, 1, 2, 6, 12, 50]:
        for mu in [-15, -3, 3, 15]:
            _, _, diff = variance_preference(mu, 2.0, tau=tau)
            assert (diff > 0) == (mu > 0), (tau, mu)
    print("\n  六種 tau x 四種局面：方向永遠只由 V 的正負決定。")
    print("  tau 只決定幅度，不決定方向。")


def depth_section():
    print("\n" + "=" * 66)
    print("3. 深度懸崖：搜尋和場的真正差別")
    print("=" * 66)

    def board(extra=None):
        b = Board(13)
        b.place(BLACK, "D10")
        b.place_many(WHITE, ["D11", "C10", "E11"])
        if extra:
            b.place(BLACK, extra)
        return b

    print(f"  {'深度':>5}{'沒有引徵':>12}{'有引徵':>12}{'分得出來嗎':>14}")
    rows = []
    for d in [5, 10, 20, 30, 33, 34, 40, 60]:
        plain, _ = ladder_capture(board(), "D10", WHITE, max_depth=d)
        broken, _ = ladder_capture(board("N4"), "D10", WHITE, max_depth=d)
        rows.append((d, plain, broken))
        print(f"  {d:>5}{('征子成立' if plain else '跑掉了'):>12}"
              f"{('征子成立' if broken else '跑掉了'):>12}"
              f"{('分不出來' if plain == broken else '分得出來'):>14}")

    for d, plain, broken in rows:
        if d <= 33:
            assert plain == broken, d          # 分不出來（而且沒引徵那欄是錯的）
            assert not plain
        else:
            assert plain and not broken        # 分得出來，兩欄都對

    print("\n  正解：沒有引徵 -> 征子成立；有引徵 -> 跑掉了。")
    print("  深度 33 以下，兩欄的答案一模一樣 —— 搜尋分不出這兩個盤面。")
    print("  第 9 章的定理 9.5 說：任何影響力場【永遠】分不出這兩個盤面。")
    print("\n  => 第 4 層和第 5 層不是兩種東西，是同一條深度軸上的兩個位置。")


def main():
    mcts_section()
    jensen_section()
    depth_section()


if __name__ == "__main__":
    main()
