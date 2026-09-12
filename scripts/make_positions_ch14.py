#!/usr/bin/env python
"""產生第 14 章用到的 positions/*.sgf。

9 路盤那一局不是人擺的 —— 它由 go_core.anatomy.book_player 下出來，
而那個程式**完全照本書的層級順序**走：能提就提、被叫吃就逃、
有要害就佔、其餘看場。沒有搜尋。

說明文字裡的每一個數字，這支腳本都會先驗證過再寫出去。
"""

import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.setrecursionlimit(200000)
sys.path.insert(0, str(ROOT))

from go_core.anatomy import (layer1_candidates, layer2_candidates,     # noqa: E402
                             layer3_candidates, layer4_candidates,
                             play_book_game)
from go_core.board import BLACK, EMPTY, WHITE, Board, format_coord    # noqa: E402
from go_core.minimax import move_values                               # noqa: E402
from go_core.score import chinese_score, dame                         # noqa: E402
from go_core.sgf import save_sgf                                      # noqa: E402

OUT = ROOT / "positions"
OUT.mkdir(exist_ok=True)

# ---- 四層一起指錯的那個局面 ----
MISS = Board(3)
MISS.place_many(BLACK, ["A3", "C3"])
MISS.place(WHITE, "B3")
_vals = dict(move_values(MISS, WHITE, komi=0.0, max_ply=15))
_best = min(_vals.values())
_winners = {p for p, v in _vals.items() if v == _best and p is not None}
_union = set()
for _fn in (layer1_candidates, layer2_candidates, layer3_candidates,
            layer4_candidates):
    _union |= _fn(MISS, WHITE)[0]
_best_nom = min(_vals[p] for p in _union if p in _vals)
_loss = -(_best - _best_nom)

assert _winners == {MISS._pt("B2")}, _winners
assert not (_union & _winners), "這個局面就是要四層全部落空"
assert _loss == 5, _loss
assert sorted(format_coord(p, 3) for p in _union) == ["A2", "B1", "C2"]

# ---- 9 路盤：照書下的一局 ----
MOVES, REASONS, GAME = play_book_game(9, max_moves=90, rng=random.Random(14))
BY_LAYER = Counter(r for r in REASONS if r is not None)
FINAL_C = chinese_score(GAME.board)
assert len(dame(GAME.board)) == 0, "應該已經填完單官"

BLACK_FINAL = [format_coord(p, 9) for p in GAME.board.points()
               if GAME.board.grid[p] == BLACK]
WHITE_FINAL = [format_coord(p, 9) for p in GAME.board.points()
               if GAME.board.grid[p] == WHITE]

# 第 20 手的中盤局面
MID = Board(9)
_ko = None
for _c, _m in MOVES[:20]:
    if _m:
        MID.play(_c, _m)
MID_B = [format_coord(p, 9) for p in MID.points() if MID.grid[p] == BLACK]
MID_W = [format_coord(p, 9) for p in MID.points() if MID.grid[p] == WHITE]


POSITIONS = {
    # --- §4.5 四層一起指錯 -----------------------------------------------
    "ch14_miss": dict(n=3, AB=["A3", "C3"], AW=["B3"],
        LB={"B2": "a", "A2": "b", "C2": "c"},
        comment=f"輪到白。四層的判準全部指向 b 與 c（提掉一顆黑子），"
                f"而正解是 a（天元）—— 提子那兩手各虧 {int(_loss)} 目。"
                "連通性與場都說「提子」，死活與溫度一句話都沒有。"
                "這是本書 9% 的破口裡最典型的一種。",
    ),

    # --- §4.6 照書下的一局 9 路棋 ----------------------------------------
    "ch14_book_mid": dict(n=9, AB=MID_B, AW=MID_W,
        comment="照書下的一局，第 20 手之後。這局棋沒有搜尋 —— "
                "每一手都只是照【能提就提、被叫吃就逃、有要害就佔、"
                "其餘看場】這個順序挑出來的。",
    ),
    "ch14_book_final": dict(n=9, AB=BLACK_FINAL, AW=WHITE_FINAL,
        comment=f"同一局的終局（共 {len(MOVES)} 手，單官已填完）。"
                f"數子結果 C = {FINAL_C:+.0f}。"
                f"各層決定了幾手：場 {BY_LAYER.get(4,0)}、"
                f"死活 {BY_LAYER.get(2,0)}、溫度 {BY_LAYER.get(3,0)}、"
                f"連通性 {BY_LAYER.get(1,0)}。**場下了絕大多數的手** —— "
                "因為多數時候別的層根本沒話說。",
    ),

    # --- §6 練習 -----------------------------------------------------------
    "ch14_ex1": dict(n=3, AB=["A3", "C3"], AW=["B3"],
        comment="練習 14.1：輪到白。四層各會提名哪些點？正解是什麼？"
                "為什麼「提子」在這裡是錯的？",
    ),
    "ch14_ex2": dict(n=9, AB=MID_B, AW=MID_W,
        comment="練習 14.2：用覆盤清單的第 4 條檢查這個局面 —— "
                "雙方哪些棋塊【不是】Benson 活？把它們的賭注加總。",
    ),
}


def main():
    for name, spec in POSITIONS.items():
        save_sgf(str(OUT / f"{name}.sgf"), None, n=spec.get("n", 9),
                 AB=spec.get("AB", ()), AW=spec.get("AW", ()), AE=spec.get("AE", ()),
                 LB=spec.get("LB"), MA=spec.get("MA", ()),
                 moves=spec.get("moves", ()), comment=spec.get("comment"))
    print(f"寫出 {len(POSITIONS)} 個盤面")
    print(f"  四層落空的局面：正解 B2，四層提名 "
          f"{sorted(format_coord(p, 3) for p in _union)}，虧 {int(_loss)} 目")
    print(f"  9 路照書對局：{len(MOVES)} 手、C = {FINAL_C:+.0f}、"
          f"各層 {dict(BY_LAYER)}")


if __name__ == "__main__":
    main()
