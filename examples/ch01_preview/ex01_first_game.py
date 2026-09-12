#!/usr/bin/env python
"""第 1 章配套範例：你的第一局棋，從第一手數到終局。

對應章節：第 1 章 §4.2、§4.3、§4.5、§5.1、§5.2、§5.3。

這支腳本做四件事：

  1. 把 §5 那一局 7 路棋【逐手播放】，每 9 手印一張圖（本書的圖示約定）；
  2. 終局時同時用【三種】規則各數一次：數子、數目、Tromp-Taylor；
  3. 驗證恆等式 C - J = b - w；
  4. 跑五個不同的亂數種子，看那條恆等式有沒有例外。

這一局棋不是人下的。它由 go_core/anatomy.py 的 book_player 下出來，
而那個程式完全照本書的五層順序走，沒有搜尋：
能提就提 -> 被叫吃就逃 -> 佔要害 -> 其餘看場。

跑法（在專案根目錄）：
    python examples/ch01_preview/ex01_first_game.py
"""

import random
import sys
from pathlib import Path

sys.setrecursionlimit(200000)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core.anatomy import play_book_game                          # noqa: E402
from go_core.board import BLACK, WHITE, Board, format_coord         # noqa: E402
from go_core.render import render_ascii                             # noqa: E402
from go_core.score import (chinese_score, dame, japanese_score,     # noqa: E402
                           stones, territory, tromp_taylor_score)

N = 7
SEED = 2


def bar(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def replay(real):
    """每 9 手印一張圖 —— 這正是第 1 章 §4.5 說的「一張圖最多 9 手」。"""
    bar("1. 逐手播放：每 9 手一張圖")
    board = Board(N)
    numbers = {}
    for i, (colour, coord) in enumerate(real, 1):
        board.play(colour, coord)
        numbers[board._pt(coord)] = (i - 1) % 9 + 1
        if i % 9 == 0 or i == len(real):
            lo = ((i - 1) // 9) * 9 + 1
            print(f"\n  第 {lo}–{i} 手")
            print(render_ascii(board, numbers=numbers))
            numbers = {}
    return board


def score_three_ways(game, real):
    bar("2. 終局：三種規則各數一次")
    b = game.board
    r = game.report()
    b_moves = sum(1 for c, _m in real if c == BLACK)
    w_moves = len(real) - b_moves

    sb, sw = stones(b)
    tb, tw = territory(b)
    pb, pw = r["prisoners"]

    print(f"  盤上   黑 {sb} 子、白 {sw} 子")
    print(f"  地     黑 {tb} 點、白 {tw} 點")
    print(f"  單官   {len(dame(b))} 點")
    print(f"  提子   黑提 {pb} 顆、白提 {pw} 顆")
    print(f"  手數   黑 {b_moves} 手、白 {w_moves} 手")
    print(f"\n  守恆檢查：{sb} + {sw} + {tb} + {tw} + {len(dame(b))} = "
          f"{sb + sw + tb + tw + len(dame(b))}（棋盤共 {N * N} 點）")
    assert sb + sw + tb + tw + len(dame(b)) == N * N

    C = chinese_score(b)
    J = japanese_score(b, prisoners_black=pb, prisoners_white=pw)
    T = tromp_taylor_score(b)
    print(f"\n  數子  C = 子 + 地       = ({sb} + {tb}) - ({sw} + {tw}) = {C:+.0f}")
    print(f"  數目  J = 地 + 提子     = ({tb} + {pb}) - ({tw} + {pw}) = {J:+.0f}")
    print(f"  T-T   Tromp-Taylor      = {T:+.0f}")
    assert C == J == 19.0
    assert T == C          # 沒有死子、沒有單官時，T-T 和數子一致

    print(f"\n  C - J = {C - J:+.0f}   b - w = {b_moves - w_moves:+d}")
    assert C - J == b_moves - w_moves == 0
    print("  兩套完全不同的數法，同一個答案 —— 因為這一局兩人手數相同。")
    print("  第 13 章定理 13.2：C - J = b - w。")


def try_to_break_it():
    bar("3. 試圖推翻它：五個種子，手數不同的也要成立")
    print(f"  {'種子':>4}{'黑手數':>8}{'白手數':>8}{'C':>7}{'J':>7}"
          f"{'C-J':>7}{'b-w':>7}")
    print("  " + "-" * 48)
    for seed in range(1, 6):
        moves, _r, game = play_book_game(N, max_moves=70,
                                         rng=random.Random(seed))
        real = [(c, m) for c, m in moves if m is not None]
        b_n = sum(1 for c, _m in real if c == BLACK)
        w_n = len(real) - b_n
        rep = game.report()
        C, J = rep["chinese"], rep["japanese"]
        mark = "" if b_n == w_n else "   <- 手數不同"
        print(f"  {seed:>4}{b_n:>8}{w_n:>8}{C:>7.0f}{J:>7.0f}"
              f"{C - J:>7.0f}{b_n - w_n:>7d}{mark}")
        assert C - J == b_n - w_n
    print("\n  五局零例外。這不是證明 —— 但如果出現一個例外，那條定理就完了。")
    print("  本書每一條公式旁邊都有一段這樣的程式，它的工作是【試圖推翻】。")


def main():
    moves, _reasons, game = play_book_game(N, max_moves=70,
                                           rng=random.Random(SEED))
    real = [(c, m) for c, m in moves if m is not None]
    print(f"  一局 {N} 路棋，共 {len(real)} 手（最後兩手是虛手，不畫）。")
    replay(real)
    score_three_ways(game, real)
    try_to_break_it()
    print()
    print("=" * 70)
    print("  規則只有三條半，而它們決定的東西是：什麼是合法的。")
    print("  哪一手比較好，規則一句話也沒說 —— 那是後面十三章的事。")
    print("=" * 70)


if __name__ == "__main__":
    main()
