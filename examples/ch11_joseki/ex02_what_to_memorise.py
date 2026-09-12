#!/usr/bin/env python
"""第 11 章配套範例 2：該記什麼？（跑完約需四到六分鐘）

對應章節：第 11 章 §4.4、§4.5、§5.3。

「定石要活用」是一句正確的廢話。這支腳本把它換成數字。

設定：3 路盤，4 手之內能到的全部 1,742 個局面，每個都用第 10 章的求解器
算出【所有】最佳著。然後：

  1. 七條便宜的規則各下一手，量命中率與平均失分。
  2. 一本【完美擬合】的定石辭典 —— 記憶者只看得到一個窗，
     而辭典直接用同一批資料擬合（對背譜最寬容的設定）。

兩個結果都不太舒服：

  * 贏的是「下離中央最近的合法點」這條一行的規則（90.2%），
    打敗第 9 章整套影響力場（83.4%）和跑一百次模擬的 MCTS（77.1%）。
  * 那條規則抵得上一本 97 條的定石辭典（90.4%）。

跑法（在專案根目錄）：
    python examples/ch11_joseki/ex02_what_to_memorise.py
"""

import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.setrecursionlimit(100000)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, Board                                     # noqa: E402
from go_core.minimax import legal_moves                              # noqa: E402
from go_core.tewari import (_board_from_key, policy_centre,           # noqa: E402
                            policy_greedy_score, policy_influence,
                            policy_liberties, policy_mcts,
                            reachable_states, score_policy, solve_all)

N, DEPTH = 3, 4


def policy_random(seed=0):
    rng = random.Random(seed)

    def fn(board, to_move, ko=None):
        opts = [p for p, _, _ in legal_moves(board, to_move, ko)]
        return rng.choice(opts) if opts else None
    return fn


WINDOWS = [
    ("下面一列 (3 點)", [(2, 0), (2, 1), (2, 2)]),
    ("左下角 (4 點)", [(1, 0), (1, 1), (2, 0), (2, 1)]),
    ("下面兩列 (6 點)", [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)]),
    ("漏掉一個角 (8 點)", [(r, c) for r in range(3) for c in range(3)
                          if (r, c) != (0, 2)]),
    ("整個棋盤 (9 點)", [(r, c) for r in range(3) for c in range(3)]),
]


def dictionary_hit_rate(table, win):
    """一本用同一批資料擬合的辭典，命中率是多少？回傳 (條目數, 命中率)。"""
    winset = set(win)
    groups = defaultdict(list)
    for key, (best, _vals) in table.items():
        board, colour, _ko = _board_from_key(key, N)
        gk = (tuple(int(board.grid[p]) for p in win), colour)
        groups[gk].append(best)
    hits = total = 0
    for members in groups.values():
        counter = Counter()
        for best in members:
            inside = [p for p in best if p in winset]
            if inside:
                for p in inside:
                    counter[p] += 1
            else:
                counter[None] += 1
        memorised = counter.most_common(1)[0][0]
        for best in members:
            total += 1
            inside = {p for p in best if p in winset}
            hits += (not inside) if memorised is None else (memorised in best)
    return len(groups), hits / total


def main():
    print(f"列出 {DEPTH} 手之內可達的局面 ...")
    states = reachable_states(N, DEPTH)
    print(f"  {len(states)} 個")

    t = time.time()
    table, solver = solve_all(states, n=N)
    print(f"  用求解器算出每個局面的【所有】最佳著："
          f"{len(table)} 個非終局局面（{time.time() - t:.0f}s）")

    # ------------------------------------------------ 七條規則
    print("\n" + "=" * 68)
    print("七條便宜的規則，對照精確的 V")
    print("=" * 68)
    print(f"  {'規則':<16}{'選中最佳著':>12}{'平均失分':>11}{'最大失分':>10}")
    scores = {}
    for name, pol in [("隨機亂下", policy_random(1)),
                      ("立刻數子最好", policy_greedy_score),
                      ("MCTS 30 次", policy_mcts(30, 3)),
                      ("自己氣最多", policy_liberties),
                      ("MCTS 100 次", policy_mcts(100, 3)),
                      ("影響力最大", policy_influence),
                      ("靠中央", policy_centre)]:
        t = time.time()
        r = score_policy(table, pol, n=N)
        scores[name] = r
        print(f"  {name:<16}{r['hit_rate']:>12.1%}{r['mean_loss']:>11.2f}"
              f"{r['max_loss']:>10.0f}   ({time.time() - t:.0f}s)")

    assert scores["靠中央"]["hit_rate"] > scores["影響力最大"]["hit_rate"]
    assert scores["靠中央"]["hit_rate"] > scores["MCTS 100 次"]["hit_rate"]
    assert scores["隨機亂下"]["hit_rate"] < 0.5
    print("\n  贏的是最笨的那一條 ——「下離中央最近的合法點」。")
    print("  它打敗了第 9 章整套影響力場，也打敗了跑一百次模擬的 MCTS。")

    counts = [len(best) for best, _ in table.values()]
    print(f"\n  平均每個局面有 {sum(counts) / len(counts):.1f} 個最佳著"
          f"（最少 {min(counts)}、最多 {max(counts)}）")
    print("  「唯一正解」通常不唯一 —— 所以「撞對」比想像中容易。")

    # ------------------------------------------------ 定石辭典
    print("\n" + "=" * 68)
    print("一本【完美擬合】的定石辭典，命中率有多高？")
    print("=" * 68)
    print(f"  {'記憶者看得到':<22}{'要記幾條':>10}{'命中率':>10}{'每多一條買到':>14}")
    prev, rates = None, []
    for name, win in WINDOWS:
        size, rate = dictionary_hit_rate(table, win)
        gain = "—" if prev is None else \
            f"{(rate - prev[1]) / (size - prev[0]) * 1e4:.1f}"
        print(f"  {name:<22}{size:>10}{rate:>10.1%}{gain:>14}")
        rates.append((size, rate))
        prev = (size, rate)

    sizes = [s for s, _ in rates]
    hits = [h for _, h in rates]
    assert sizes == sorted(sizes) and hits == sorted(hits)
    assert hits[-1] == 1.0
    marginal = [(hits[i + 1] - hits[i]) / (sizes[i + 1] - sizes[i])
                for i in range(len(rates) - 1)]
    assert marginal == sorted(marginal, reverse=True), marginal

    print("\n  最右欄（每多記一條買到幾個萬分點的命中率）一路遞減。")
    print("  條目數指數成長，命中率卻有 100% 的天花板 —— 邊際報酬必然遞減。")

    rule = scores["靠中央"]["hit_rate"]
    # (「靠中央」對照 4 點辭典)

    print(f"\n  而「靠中央」這【一句話】：{rule:.1%}")
    print(f"     「左下角 4 點」那本【97 條】的辭典：{rates[1][1]:.1%}")
    assert abs(rule - rates[1][1]) < 0.02
    print("  兩者實質相同。一句話 vs 九十七個形狀。")
    print("\n  而且那 97 條是在考題上訓練出來的最佳值 —— 實戰上只會更差。")


if __name__ == "__main__":
    main()
