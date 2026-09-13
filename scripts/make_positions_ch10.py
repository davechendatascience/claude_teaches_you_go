#!/usr/bin/env python
"""產生第 10 章用到的 positions/*.sgf。

3 路盤的那幾張圖不是擺出來的 —— 它們是 go_core/minimax.py 把 3 路圍棋
【完全解開】之後印出來的。最優對局的每一手都由搜尋決定。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from go_core.board import BLACK, WHITE, Board, format_coord, opposite  # noqa: E402
from go_core.minimax import Solver, area_score, legal_moves            # noqa: E402
from go_core.sgf import save_sgf                                       # noqa: E402

OUT = ROOT / "positions"
OUT.mkdir(exist_ok=True)

MAX_PLY = 15


def principal_variation(n=3, max_ply=MAX_PLY):
    """把最優對局走完，回傳 (著手序列, 終局盤面)。"""
    s = Solver(komi=0.0, max_ply=max_ply)
    b, colour, ko, passes, ply = Board(n), BLACK, None, 0, 0
    pv = []
    while ply < max_ply and passes < 2:
        _, mv = s.search(b, colour, passes=passes, ko=ko, ply=ply)
        if mv is None:
            pv.append((colour, None))
            passes += 1
            ko = None
        else:
            for p, child, nk in legal_moves(b, colour, ko):
                if p == mv:
                    b, ko = child, nk
                    break
            pv.append((colour, mv))
            passes = 0
        colour = opposite(colour)
        ply += 1
    return pv, b


PV, FINAL = principal_variation()
BLACK_FINAL = [format_coord(p, 3) for p in FINAL.points()
               if FINAL.grid[p] == BLACK]
WHITE_FINAL = [format_coord(p, 3) for p in FINAL.points()
               if FINAL.grid[p] == WHITE]
NB, NW = area_score(FINAL)

POSITIONS = {
    # --- §4.2 三種第一手 ------------------------------------------------
    "ch10_3x3_moves": dict(n=3,
        LB={"B2": "a", "B3": "b", "A3": "c"},
        comment="3 路盤的空盤。三種第一手：a 天元、b 邊、c 角。"
                "這是全書唯一一個「每一手值幾目」有【確切答案】的盤面 —— "
                "因為 3 路圍棋可以被完全解開。",
    ),

    # --- §4.2 解出來的終局 ------------------------------------------------
    "ch10_3x3_final": dict(n=3, AB=BLACK_FINAL, AW=WHITE_FINAL,
        comment=f"雙方都下最好的棋，3 路盤的結局：黑佔 {NB} 點"
                f"（盤上 {len(BLACK_FINAL)} 顆子，加上 {NB - len(BLACK_FINAL)} 個目）、"
                f"白 {NW} 點。黑拿走整個棋盤 —— 這不是估計，"
                f"是 {len(PV)} 手的完全搜尋算出來的。",
    ),

    # --- §4.1 2 路盤的環 ---------------------------------------------------
    "ch10_2x2_cycle": dict(n=2, AB=["B2"], AW=["A2"],
        comment="2 路盤上的一個盤面。從這裡出發，只用【落子】就能在 6 手之後"
                "回到同一個狀態 —— 基本劫規擋不住這個 6-環（第 5 章規則 5.4）。"
                "於是 2 路圍棋在基本劫規下【沒有值】。",
    ),

    # --- §6 練習 -----------------------------------------------------------
    "ch10_ex1": dict(n=3, AB=["B2"], AW=["B3"],
        LB={"A2": "a", "C2": "b", "A3": "c"},
        comment="練習 10.1：黑天元、白扳，輪到黑走。a、b、c 三點哪一個最好？"
                "先猜，再用 go_core.minimax 算 —— 這一題有唯一正確答案。",
    ),
    "ch10_ex2": dict(n=3, AB=["B2", "A2"], AW=["B3", "C2"],
        comment="練習 10.3：最優對局的第 5 手。黑該下哪裡？"
                "順便回答：這個盤面的 V 是多少？",
    ),
    "ch10_ex3": dict(n=13, AB=["D10"], AW=["D11", "C10", "E11"],
        LB={"N4": "a"},
        comment="練習 10.4：第 8 章的征子，第 9 章證明過任何影響力場都算不出它。"
                "搜尋算得出來 —— 但要讀多深？在 a 放一顆黑子之後又要讀多深？",
    ),
}


def main():
    for name, spec in POSITIONS.items():
        save_sgf(str(OUT / f"{name}.sgf"), None, n=spec.get("n", 9),
                 AB=spec.get("AB", ()), AW=spec.get("AW", ()), AE=spec.get("AE", ()),
                 LB=spec.get("LB"), MA=spec.get("MA", ()),
                 moves=spec.get("moves", ()), comment=spec.get("comment"))
    print(f"寫出 {len(POSITIONS)} 個盤面")
    print(f"  3 路最優對局 {len(PV)} 手，終局 黑 {NB} : 白 {NW}")


if __name__ == "__main__":
    main()
