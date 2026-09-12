#!/usr/bin/env python
"""產生第 13 章用到的 positions/*.sgf。

3 路盤的兩張終局圖不是擺出來的 —— 一張是用【數子】解出來的最優對局終點
（第 10 章），另一張是用【數目】解出來的（本章 go_core/score.py）。
同一個棋盤、同一個「黑拿走全部」的結果，兩套規則走出兩個不同的終局。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.setrecursionlimit(200000)
sys.path.insert(0, str(ROOT))

from go_core.board import BLACK, EMPTY, WHITE, Board, format_coord, opposite  # noqa: E402
from go_core.minimax import Solver, legal_moves                     # noqa: E402
from go_core.score import (ScoredGame, chinese_score, dame,          # noqa: E402
                           japanese_score, solve_japanese, territory)
from go_core.sgf import save_sgf                                     # noqa: E402

OUT = ROOT / "positions"
OUT.mkdir(exist_ok=True)

MAX_PLY = 15


def chinese_optimal():
    """用數子解出來的最優對局（第 10 章那一局）。"""
    s = Solver(komi=0.0, max_ply=MAX_PLY)
    g = ScoredGame(3)
    colour, ko, passes, ply = BLACK, None, 0, 0
    while ply < MAX_PLY and passes < 2:
        _, mv = s.search(g.board, colour, passes=passes, ko=ko, ply=ply)
        if mv is None:
            g.pass_move()
            passes += 1
            ko = None
        else:
            for p, child, nk in legal_moves(g.board, colour, ko):
                if p == mv:
                    g.play(colour, format_coord(p, 3))
                    ko = nk
                    break
            passes = 0
        colour = opposite(colour)
        ply += 1
    return g


def japanese_optimal():
    """用數目解出來的最優對局。"""
    g = ScoredGame(3)
    colour, ko, passes, ply = BLACK, None, 0, 0
    while ply < MAX_PLY and passes < 2:
        _, mv, _ = solve_japanese(g.board, colour, komi=0.0,
                                  max_ply=MAX_PLY - ply)
        if mv is None:
            g.pass_move()
            passes += 1
            ko = None
        else:
            for p, child, nk in legal_moves(g.board, colour, ko):
                if p == mv:
                    g.play(colour, format_coord(p, 3))
                    ko = nk
                    break
            passes = 0
        colour = opposite(colour)
        ply += 1
    return g


CN = chinese_optimal()
JP = japanese_optimal()
CNR, JPR = CN.report(), JP.report()

# ---- 說明文字裡的數字，先驗證 ----
assert CNR["chinese"] == 9 and JPR["chinese"] == 9
assert JPR["japanese"] == 5
assert CNR["gap"] == CNR["move_diff"] and JPR["gap"] == JPR["move_diff"]
assert JPR["move_diff"] == 4


def stones_of(g, colour):
    return [format_coord(p, 3) for p in g.board.points()
            if g.board.grid[p] == colour]


# 一個「只剩單官」的 7 路盤面：黑牆在 C 列、白牆在 E 列，中間的 D 列是單官
UNFIN_B = [f"C{r}" for r in range(1, 8)]
UNFIN_W = [f"E{r}" for r in range(1, 8)]
_u = Board(7)
_u.place_many(BLACK, UNFIN_B)
_u.place_many(WHITE, UNFIN_W)
N_DAME = len(dame(_u))
_TB, _TW = territory(_u)
assert N_DAME == 7, N_DAME
assert (_TB, _TW) == (14, 14), (_TB, _TW)

# 把單官填完之後的樣子（黑先填，交替）
_filled = ScoredGame(7)
for c in UNFIN_B:
    _filled.board.place(BLACK, c)
for c in UNFIN_W:
    _filled.board.place(WHITE, c)
_col = BLACK
while True:
    left = sorted(dame(_filled.board))
    if not left:
        break
    _filled.play(_col, format_coord(left[0], 7))
    _col = opposite(_col)
FILLED_B = [format_coord(p, 7) for p in _filled.board.points()
            if _filled.board.grid[p] == BLACK]
FILLED_W = [format_coord(p, 7) for p in _filled.board.points()
            if _filled.board.grid[p] == WHITE]
_FR = _filled.report()
assert _FR["dame"] == 0


POSITIONS = {
    # --- §4.2 同一個棋盤，兩套規則走出兩個終局 ---------------------------
    "ch13_cn_final": dict(n=3,
        AB=stones_of(CN, BLACK), AW=stones_of(CN, WHITE),
        comment=f"【數子】解出來的終局。黑白各下了 {CNR['moves'][0]}、"
                f"{CNR['moves'][1]} 手，盤上黑 {CNR['stones'][0]} 子、"
                f"白 {CNR['stones'][1]} 子。C = {CNR['chinese']:.0f}。"
                "白一路下到底 —— 因為數子規則下，往自己必死的地方填子不用付錢。",
    ),
    "ch13_jp_final": dict(n=3,
        AB=stones_of(JP, BLACK), AW=stones_of(JP, WHITE),
        comment=f"【數目】解出來的終局。同一個棋盤，白只下了 "
                f"{JPR['moves'][1]} 手就一直虛手 —— 因為每多下一顆，"
                f"就是白送黑一個提子。C = {JPR['chinese']:.0f}、"
                f"J = {JPR['japanese']:.0f}，差 {JPR['gap']:.0f} = 手數差。",
    ),

    # --- §4.1 終局的定義：還有單官就還沒完 --------------------------------
    "ch13_dame": dict(n=7, AB=UNFIN_B, AW=UNFIN_W,
        comment=f"雙方的地都定了：黑 {_TB} 目、白 {_TW} 目。"
                f"但中間 D 列那 {N_DAME} 個點碰得到兩種顏色 —— 那是【單官】。"
                "單官的溫度是 0：填它不賺目。但在數目規則下填它要付一目，"
                "在數子規則下不用。兩套規則就在這裡分家。",
    ),
    "ch13_filled": dict(n=7, AB=FILLED_B, AW=FILLED_W,
        comment=f"單官填完了（黑先填，交替）。黑多填了 "
                f"{_FR['move_diff']} 手，於是 C - J = {_FR['gap']:.0f} —— "
                "正好是手數差（定理 13.2）。",
    ),

    # --- §4.6 死子：中國規則不必判，日本規則必須判 ---------------------
    "ch13_dead_stones": dict(n=7,
        AB=["B1", "B2", "B3", "B4", "B5", "B6", "B7",
            "C7", "D7", "E7", "F7", "G7"],
        AW=["A3", "A4"],
        LB={"A2": "a", "A5": "b"},
        comment="白 A3、A4 這兩顆做不出兩個眼 —— 大家都同意它們死了。"
                "但【同意】不是算術。中國規則不必判：黑下 a 或 b 提掉就是了。"
                "日本規則必須判，所以它需要一套確認手續。",
    ),

    # --- §6 練習 -----------------------------------------------------------
    "ch13_ex1": dict(n=7, AB=UNFIN_B, AW=UNFIN_W,
        comment="練習 13.1：數出黑白各有多少地、多少單官。"
                "然後回答：把單官全部填完之後，兩套規則的差會是多少？",
    ),
    "ch13_ex2": dict(n=3,
        AB=stones_of(JP, BLACK), AW=stones_of(JP, WHITE),
        comment="練習 13.2：這是數目規則的終局。黑下了 6 手、白下了 2 手。"
                "用定理 13.2 算出 C 與 J，並解釋白為什麼不再下了。",
    ),
}


def main():
    for name, spec in POSITIONS.items():
        save_sgf(str(OUT / f"{name}.sgf"), None, n=spec.get("n", 9),
                 AB=spec.get("AB", ()), AW=spec.get("AW", ()), AE=spec.get("AE", ()),
                 LB=spec.get("LB"), MA=spec.get("MA", ()),
                 moves=spec.get("moves", ()), comment=spec.get("comment"))
    print(f"寫出 {len(POSITIONS)} 個盤面")
    print(f"  數子最優：{len(CN.moves)} 色、手數 {CNR['moves']}、"
          f"C = {CNR['chinese']:.0f}、J = {CNR['japanese']:.0f}")
    print(f"  數目最優：手數 {JPR['moves']}、"
          f"C = {JPR['chinese']:.0f}、J = {JPR['japanese']:.0f}")
    print(f"  只剩單官的 7 路盤面：地 {_TB}:{_TW}、單官 {N_DAME} 個")
    print(f"  填完之後：手數差 {_FR['move_diff']}、C = {_FR['chinese']:.0f}、"
          f"J = {_FR['japanese']:.0f}、C-J = {_FR['gap']:.0f}")


if __name__ == "__main__":
    main()
