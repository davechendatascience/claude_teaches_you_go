#!/usr/bin/env python
"""第 14 章配套範例 1：把一局棋逐手拆到五層裡。

對應章節：第 14 章 §4.1、§4.2、§4.5、§4.6、§5.1、§5.2。

這支腳本做四件事：

  1. 解一局 3 路盤的【最優對局】，逐手標出哪幾層解釋得了它；
  2. 把那個「四層一起指錯」的局面攤開來看（本章 §4.5 的帳單）；
  3. 用 book_player 下一局 9 路棋 —— 完全照本書的層級順序，沒有搜尋；
  4. 對那局 9 路棋做「覆盤清單第 4 條」：哪些棋塊不是 Benson 活。

跑法（在專案根目錄）：
    python examples/ch14_anatomy/ex01_dissect.py
"""

import random
import sys
from collections import Counter
from pathlib import Path

sys.setrecursionlimit(200000)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, WHITE, Board, format_coord, opposite      # noqa: E402
from go_core.anatomy import (LAYER_NAMES, coverage, explain_game,     # noqa: E402
                             layer1_candidates, layer2_candidates,
                             layer3_candidates, layer4_candidates,
                             play_book_game, render_table)
from go_core.attack import stake                                      # noqa: E402
from go_core.benson import benson_alive                               # noqa: E402
from go_core.minimax import Solver, legal_moves, move_values          # noqa: E402
from go_core.score import chinese_score, dame                         # noqa: E402
from go_core.strings import all_strings                               # noqa: E402

MAX_PLY = 15
LAYERS = {1: layer1_candidates, 2: layer2_candidates,
          3: layer3_candidates, 4: layer4_candidates}


def bar(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# --------------------------------------------------------------- 1

def optimal_game(n=3):
    """把 3 路盤的最優對局一手一手走出來。"""
    s = Solver(komi=0.0, max_ply=MAX_PLY)
    b, colour, ko, passes, ply, moves = Board(n), BLACK, None, 0, 0, []
    while ply < MAX_PLY and passes < 2:
        _, m = s.search(b, colour, passes=passes, ko=ko, ply=ply)
        if m is None:
            moves.append((colour, None))
            passes += 1
            ko = None
        else:
            moves.append((colour, format_coord(m, n)))
            for p, child, nk in legal_moves(b, colour, ko):
                if p == m:
                    b, ko = child, nk
                    break
            passes = 0
        colour = opposite(colour)
        ply += 1
    return moves


def dissect_optimal():
    bar("1. 一局最優的 3 路棋，逐手解剖")
    moves = optimal_game()
    rows = explain_game(moves, n=3, with_v=True, max_ply=MAX_PLY)
    print(render_table(rows, n=3, with_v=True))

    cov = coverage(rows)
    print(f"\n  {'層':<8}{'命中率':>9}{'選擇性':>9}")
    for k in sorted(cov["hit_rate"]):
        print(f"  {LAYER_NAMES[k]:<8}{cov['hit_rate'][k]:>9.0%}"
              f"{cov['selectivity'][k]:>9.0%}")
    print(f"\n  一層都解釋不了的手：{cov['unexplained']} / {cov['total']}")

    # 第 5 層是裁判，所以在【最優對局】上它必然全中。
    assert cov["hit_rate"][5] == 1.0
    print("  第 5 層整欄都是 O —— 這是定義，不是成績（它就是答案本身）。")


# --------------------------------------------------------------- 2

def the_miss():
    bar("2. 帳單：四層一起指錯的那個局面")
    b = Board(3)
    b.place_many(BLACK, ["A3", "C3"])
    b.place(WHITE, "B3")
    print(b)
    print("  輪到白下。")

    vals = dict(move_values(b, WHITE, komi=0.0, max_ply=MAX_PLY))
    best_v = min(vals.values())                    # 白要最小化 V
    winners = {p for p, v in vals.items() if v == best_v and p is not None}
    print(f"\n  正解：{sorted(format_coord(p, 3) for p in winners)}"
          f"（V = {best_v:+.0f}）")

    union = set()
    for k in sorted(LAYERS):
        s, _ = LAYERS[k](b, WHITE)
        names = sorted(format_coord(p, 3) for p in s) or ["（沉默）"]
        mark = "命中" if s & winners else ("落空" if s else "----")
        print(f"    第 {k} 層 {LAYER_NAMES[k]:<4} 提名 {str(names):<26} {mark}")
        union |= s

    assert not (union & winners), "這個局面就是要四層全部落空"
    loss = -(best_v - min(vals[p] for p in union if p in vals))
    print(f"\n  四層【全部】落空，而且提名的那幾手各虧 {loss:.0f} 目。")
    print("  它們錯在同一件事：都說「去提子」，而正解是不提。")
    print("  提子是最看得見的收穫，也是最容易被高估的收穫。")
    assert loss == 5


# --------------------------------------------------------------- 3

def book_game():
    bar("3. 照本書下的一局 9 路棋（沒有搜尋）")
    moves, reasons, game = play_book_game(9, max_moves=90,
                                          rng=random.Random(14))
    by_layer = Counter(r for r in reasons if r is not None)
    print(game.board)
    print(f"  共 {len(moves)} 手，單官已填完（剩 {len(dame(game.board))} 個）。")
    print(f"  數子結果 C = {chinese_score(game.board):+.0f}")
    total = sum(n for k, n in by_layer.items() if k)
    print("\n  哪一層決定了這一手：")
    for k in sorted(by_layer, key=lambda k: -by_layer[k]):
        if not k:
            continue
        n = by_layer[k]
        print(f"    第 {k} 層 {LAYER_NAMES[k]:<4} {n:>3} 手  {n / total:>6.1%}")
    print(f"    （另有 {by_layer[0]} 手是收單官，不屬於任何一層）")

    assert len(dame(game.board)) == 0
    assert by_layer[4] > total / 2
    print("\n  場下了一半以上的手 —— 不是因為它最好，")
    print("  是因為多數時候別的層根本沒話說（3 路盤上量到的是 21%）。")
    print("\n  ** 這局棋沒有裁判。9 路盤算不出 V，所以不能說它下得好不好。**")
    return game


# --------------------------------------------------------------- 4

def checklist_item_4(game):
    bar("4. 覆盤清單第 4 條：哪些棋塊【不是】Benson 活？")
    b = game.board
    for colour, name in ((BLACK, "黑"), (WHITE, "白")):
        alive = benson_alive(b, colour, trace=False)
        alive_pts = set().union(*alive) if alive else set()
        groups = list(all_strings(b, colour))
        risky = [g for g in groups if not (g & alive_pts)]
        total = sum(stake(b, g) for g in risky)
        print(f"  {name}：{len(groups)} 塊，其中 {len(alive)} 塊 Benson 活、"
              f"{len(risky)} 塊沒有")
        print(f"      沒活淨的那些棋子共 {sum(len(g) for g in risky)} 顆，"
              f"賭注加總 = {total}")
    print("\n  賭注 k = s + t（第 12 章命題 12.3），生死擺盪 = 2k。")
    print("  這就是清單第 4 條要你算的東西 —— 它不是感覺，是一個整數。")
    print("\n  注意「沒有 Benson 活」不等於「死」。Benson 只是【充分條件】")
    print("  （第 3 章定理 3.5）：它要求兩個眼位是完全封閉的小區域，")
    print("  而終局盤上很多明顯活棋並不滿足那個嚴格條件。")
    print("  所以這一條清單問的是「哪些地方我還沒有【證明】安全」，")
    print("  不是「哪些地方我一定會死」。")


def main():
    dissect_optimal()
    the_miss()
    g = book_game()
    checklist_item_4(g)
    print()
    print("=" * 70)
    print("  五層不是五個技巧，是五個【判準】。")
    print("  它們會沉默、會衝突、也會一起錯 —— 而那三件事都可以量。")
    print("=" * 70)


if __name__ == "__main__":
    main()
