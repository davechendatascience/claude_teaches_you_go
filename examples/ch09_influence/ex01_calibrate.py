#!/usr/bin/env python
"""第 9 章配套範例 1：影響力場到底準不準？（跑完約需二到四分鐘）

對應章節：第 9 章 §4.2、§4.3。

坊間的勢力理論書會畫出漂亮的等高線圖，然後說「所以黑優」。
這支腳本做的是那些書從來不做的事：**把它量出來**。

作法：
  1. 從空盤隨機下 16 手，得到一個 9 路中盤盤面。
  2. 從那裡隨機把棋下完 N 次，每一點取多數決 —— 這是「實際歸屬」。
  3. 拿場的預測去比。場說「不知道」的點不算錯，另外記成覆蓋率。

結論（書上 §4.2 的表就是這麼來的）：
  * Zobrist 全盤開口只有 77% 準，但基準線只有 68%（猜最近的子）。
  * Bouzy 看起來準得多（94%），但它只在 18% 的點上開口。
  * **在相同覆蓋率下，兩者一樣準。** Bouzy 那一整套機器沒有買到任何東西。

跑法（在專案根目錄）：
    python examples/ch09_influence/ex01_calibrate.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np                                                   # noqa: E402

from go_core import BLACK, EMPTY, WHITE, Board, opposite             # noqa: E402
from go_core.influence import (bouzy_field, field_ownership,          # noqa: E402
                               final_ownership, playout, zobrist_field)

N = 9
POSITIONS = 30
OPENING = 16
TRIALS = 21
SEED = 90909


def make_position(rng):
    """隨機下 OPENING 手，得到一個中盤盤面。"""
    b = Board(N)
    colour = BLACK
    for _ in range(OPENING):
        cands = [p for p in b.points() if b.grid[p] == EMPTY]
        rng.shuffle(cands)
        for p in cands:
            t = b.copy()
            try:
                t.play(colour, p)
            except ValueError:
                continue
            b = t
            break
        colour = opposite(colour)
    return b


def ground_truth(board, rng):
    """隨機下完 TRIALS 次，每一點取多數決當作「實際歸屬」。"""
    votes = np.zeros((N, N, 3))
    for _ in range(TRIALS):
        own = final_ownership(playout(board, BLACK, rng))
        for r in range(N):
            for c in range(N):
                votes[r, c, own[r, c]] += 1
    return votes.argmax(axis=2)


def score(pred, truth, empties):
    """回傳 (答對, 答錯, 沒開口)。"""
    hit = miss = skip = 0
    for p in empties:
        if pred[p] == 0 or truth[p] == 0:
            skip += 1
        elif pred[p] == truth[p]:
            hit += 1
        else:
            miss += 1
    return hit, miss, skip


def evaluate(fields, boards, truths, empties):
    H = M = S = 0
    for f, t, e in zip(fields, truths, empties):
        h, m, s = score(f, t, e)
        H += h
        M += m
        S += s
    total = H + M
    return (H / total if total else float("nan"),
            total / (total + S) if total + S else 0.0)


def main():
    rng = random.Random(SEED)
    print(f"產生 {POSITIONS} 個 9 路中盤盤面（隨機 {OPENING} 手），"
          f"每個隨機下完 {TRIALS} 次取多數決 ...")
    boards = [make_position(rng) for _ in range(POSITIONS)]
    truths = [ground_truth(b, rng) for b in boards]
    empties = [[p for p in b.points() if b.grid[p] == EMPTY] for b in boards]

    # ---------- 基準線 ----------
    print("\n" + "=" * 62)
    print("基準線：不用場也能猜")
    print("=" * 62)
    H = M = 0
    for b, t, e in zip(boards, truths, empties):
        for p in e:
            if t[p] == 0:
                continue
            if t[p] == BLACK:
                H += 1
            else:
                M += 1
    print(f"  全部猜黑        準確率 {H / (H + M):>6.1%}   覆蓋率 100.0%")

    H = M = S = 0
    for b, t, e in zip(boards, truths, empties):
        stones = [(p, int(b.grid[p])) for p in b.points() if b.grid[p] != EMPTY]
        for p in e:
            if t[p] == 0:
                S += 1
                continue
            near = min(stones,
                       key=lambda sc: abs(sc[0][0] - p[0]) + abs(sc[0][1] - p[1]))
            if near[1] == t[p]:
                H += 1
            else:
                M += 1
    print(f"  猜最近的那顆子  準確率 {H / (H + M):>6.1%}   覆蓋率 "
          f"{(H + M) / (H + M + S):>5.1%}")

    # ---------- Zobrist：lambda ----------
    print("\n" + "=" * 62)
    print("Zobrist：lambda 掃描（theta = 0，全盤都開口）")
    print("=" * 62)
    print(f"  {'lambda':>8}{'準確率':>10}{'覆蓋率':>10}")
    best = None
    for lam in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        fields = [field_ownership(zobrist_field(b, lam)) for b in boards]
        acc, cov = evaluate(fields, boards, truths, empties)
        print(f"  {lam:>8.1f}{acc:>10.1%}{cov:>10.1%}")
        if best is None or acc > best[1]:
            best = (lam, acc)
    lam_best = best[0]
    print(f"  最佳 lambda = {lam_best}")

    # ---------- Zobrist：theta ----------
    print("\n" + "=" * 62)
    print(f"Zobrist lambda={lam_best}：提高門檻，用覆蓋率換準確率")
    print("=" * 62)
    print(f"  {'theta':>8}{'準確率':>10}{'覆蓋率':>10}")
    curve = []
    for th in [0.0, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
        fields = [field_ownership(zobrist_field(b, lam_best), th) for b in boards]
        acc, cov = evaluate(fields, boards, truths, empties)
        if np.isnan(acc):
            continue
        curve.append((th, acc, cov))
        print(f"  {th:>8.2f}{acc:>10.1%}{cov:>10.1%}")

    # ---------- Bouzy，以及公平的比較 ----------
    print("\n" + "=" * 62)
    print("Bouzy vs Zobrist —— 在【相同覆蓋率】下比")
    print("=" * 62)
    for k, off in [(3, False), (3, True), (4, True)]:
        fields = [field_ownership(bouzy_field(b, k, off)) for b in boards]
        acc, cov = evaluate(fields, boards, truths, empties)
        near = min(curve, key=lambda x: abs(x[2] - cov))
        print(f"  Bouzy k={k} 盤外算敵={str(off):<5} "
              f"覆蓋 {cov:>5.1%} 準確 {acc:>6.1%}")
        print(f"      對照 Zobrist theta={near[0]:<5} "
              f"覆蓋 {near[2]:>5.1%} 準確 {near[1]:>6.1%}")

    print("\n  結論：Bouzy 那一整套膨脹／侵蝕，相對於「一行指數衰減 + 一個門檻」，")
    print("        沒有買到任何東西。唯一真正的旋鈕是門檻 —— 也就是你願意在")
    print("        多少地方說「不知道」。")


if __name__ == "__main__":
    main()
