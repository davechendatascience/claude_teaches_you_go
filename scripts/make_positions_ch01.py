#!/usr/bin/env python
"""產生第 1 章用到的 positions/*.sgf。

第 1 章是預覽，所以它的棋圖有兩種：**規則示範**（手擺的，但每一句說明
都在這支腳本裡驗證過）與**一整局 7 路棋**（不是人擺的 —— 它由
go_core.anatomy.book_player 下出來，那個程式完全照本書的層級順序走）。

那一局的重點是：黑白各下了 27 手（b = w），所以數子與數目**恰好相等**，
兩套規則都是黑勝 19。這正是第 13 章定理 13.2（C - J = b - w）的特例，
而第 1 章要讓讀者在還沒學任何公式之前，先親眼看到它。
"""

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.setrecursionlimit(200000)
sys.path.insert(0, str(ROOT))

from go_core.anatomy import play_book_game                          # noqa: E402
from go_core.board import BLACK, WHITE, Board, format_coord         # noqa: E402
from go_core.score import (chinese_score, dame, japanese_score,     # noqa: E402
                           stones, territory)
from go_core.sgf import save_sgf                                    # noqa: E402
from go_core.strings import find_string, liberties                  # noqa: E402

OUT = ROOT / "positions"
OUT.mkdir(exist_ok=True)

N = 7

# ---------------------------------------------------------------- 規則示範

# 一顆子的氣
_b = Board(N)
_b.place(BLACK, "D4")
_LIB = sorted(format_coord(p, N) for p in liberties(_b, find_string(_b, _b._pt("D4"))))
assert _LIB == ["C4", "D3", "D5", "E4"], _LIB

# 角上一顆子只有兩口氣
_c = Board(N)
_c.place(BLACK, "A1")
assert len(liberties(_c, find_string(_c, _c._pt("A1")))) == 2

# 叫吃：白 D4 只剩一口氣
_atari = Board(N)
_atari.place(WHITE, "D4")
_atari.place_many(BLACK, ["C4", "E4", "D5"])
_ATARI_LIB = sorted(format_coord(p, N)
                    for p in liberties(_atari, find_string(_atari, _atari._pt("D4"))))
assert _ATARI_LIB == ["D3"], _ATARI_LIB

# 提子：黑下 D3，白 D4 被提走
_cap = Board(N)
_cap.place(WHITE, "D4")
_cap.place_many(BLACK, ["C4", "E4", "D5"])
_taken = _cap.play(BLACK, "D3")
assert sorted(format_coord(p, N) for p in _taken) == ["D4"]
_CAP_BLACK = sorted(format_coord(p, N) for p in _cap.points()
                    if _cap.grid[p] == BLACK)
assert _CAP_BLACK == ["C4", "D3", "D5", "E4"]

# 圍地：黑在左下角圍出 6 個交叉點
_terr = Board(N)
_terr.place_many(BLACK, ["A4", "B4", "C4", "C3", "C2", "C1"])
_terr.place_many(WHITE, ["E7", "E6", "E5", "F5", "G5"])
_TB, _TW = territory(_terr)
assert (_TB, _TW) == (6, 4), (_TB, _TW)
assert len(dame(_terr)) == 28

# 練習 1.1：白兩子只剩一口氣，黑下 a 提兩子
_ex1 = Board(N)
_ex1.place_many(WHITE, ["D4", "D5"])
_ex1.place_many(BLACK, ["C4", "C5", "E4", "E5", "D6"])
assert len(liberties(_ex1, find_string(_ex1, _ex1._pt("D4")))) == 1
assert len(_ex1.play(BLACK, "D3")) == 2

# 練習 1.2：黑 8 點、白 4 點，其餘 25 點兩色都走得到（不算地）
_ex2 = Board(N)
_ex2.place_many(BLACK, ["A5", "B5", "C5", "C4", "C3", "C2", "C1"])
_ex2.place_many(WHITE, ["E1", "E2", "E3", "F3", "G3"])
assert territory(_ex2) == (8, 4)
assert len(dame(_ex2)) == 25

# ---------------------------------------------------------------- 一整局棋

MOVES, _REASONS, GAME = play_book_game(N, max_moves=70, rng=random.Random(2))
REAL = [(c, m) for c, m in MOVES if m is not None]
B_MOVES = sum(1 for c, _m in REAL if c == BLACK)
W_MOVES = len(REAL) - B_MOVES

REPORT = GAME.report()
C = REPORT["chinese"]
J = REPORT["japanese"]
PRIS_B, PRIS_W = REPORT["prisoners"]

assert len(REAL) == 54
assert B_MOVES == W_MOVES == 27          # 手數相同 -> 兩套規則必然一致
assert REPORT["dame"] == 0
assert C == J == 19.0
assert REPORT["gap"] == 0.0
assert (PRIS_B, PRIS_W) == (14, 1)
assert stones(GAME.board) == (26, 13)
assert territory(GAME.board) == (8, 2)

OPENING = REAL[:9]

MID = Board(N)
for _c2, _m2 in REAL[:27]:
    MID.play(_c2, _m2)
MID_B = [format_coord(p, N) for p in MID.points() if MID.grid[p] == BLACK]
MID_W = [format_coord(p, N) for p in MID.points() if MID.grid[p] == WHITE]

FIN = GAME.board
FIN_B = [format_coord(p, N) for p in FIN.points() if FIN.grid[p] == BLACK]
FIN_W = [format_coord(p, N) for p in FIN.points() if FIN.grid[p] == WHITE]


POSITIONS = {
    # --- §4.1 棋盤 ------------------------------------------------------
    "ch01_board": dict(
        comment="一個空的 7 路棋盤。橫向是 A 到 G（圍棋慣例【跳過 I】），"
                "縱向由下往上 1 到 7。標成 + 的是【星】，只是方便定位的記號，"
                "沒有任何規則上的意義。棋子下在【線的交叉點】上，不是下在格子裡。",
    ),

    # --- §4.2 氣、叫吃、提子 --------------------------------------------
    "ch01_liberty": dict(AB=["D4"], LB={"C4": "a", "D5": "b", "E4": "c", "D3": "d"},
        comment="黑子 D4 的【氣】就是 a、b、c、d 這四個【緊鄰的空交叉點】。"
                "斜的不算。角上的子只有兩口氣，邊上的子三口 —— "
                "這個「位置決定氣數」的小事，第 2 章會長成金角銀邊的證明。",
    ),
    "ch01_atari": dict(AW=["D4"], AB=["C4", "E4", "D5"], LB={"D3": "a"},
        comment="白 D4 的四口氣被黑佔掉了三口，只剩 a 一口。這個狀態叫【叫吃】。"
                "注意這裡沒有任何「威脅」的概念 —— 只有一個數字：氣 = 1。",
    ),
    "ch01_capture": dict(AB=["C4", "D3", "D5", "E4"],
        comment="和上一張比對：黑下在 a（D3）之後，白 D4 的氣變成 0，"
                "於是【立刻從棋盤上拿走】—— D4 現在是空的（那個 + 是星位記號）。"
                "提子不是一種選擇，是規則的自動結果：氣歸零的棋子不能留在盤上。",
    ),

    # --- §4.3 圍地 ------------------------------------------------------
    "ch01_territory": dict(AB=["A4", "B4", "C4", "C3", "C2", "C1"],
        AW=["E7", "E6", "E5", "F5", "G5"],
        comment="黑用 6 顆子把左下角的 6 個交叉點圍了起來（A1、A2、A3、B1、B2、B3）。"
                "【地】的定義只有一句話：一個空點如果只走得到黑子、走不到白子，"
                "它就是黑的地。注意黑借用了棋盤的兩條邊當免費的牆 —— "
                "同樣 6 個點如果圍在盤中央，要花的子多得多。",
    ),

    # --- §4.5 棋圖怎麼讀 ------------------------------------------------
    "ch01_read": dict(AB=["B5"], AW=["F3"], LB={"C3": "a", "F5": "b"},
        moves=[(BLACK, "D4"), (WHITE, "D5"), (BLACK, "E4"), (WHITE, "C4")],
        comment="這張圖示範本書的全部圖示約定：X 是黑子、O 是白子、. 是空點、"
                "+ 是星位；數字 1234 是【著手順序】（黑先，所以奇數是黑）；"
                "小寫字母 a、b 是正文要指涉的參考點。一張圖最多放 9 手，"
                "超過就分圖 —— 因為第 10 手開始，讀者就數不清了。",
    ),

    # --- §5 一整局 7 路棋 -----------------------------------------------
    "ch01_game_open": dict(moves=OPENING,
        comment="這一局的前 9 手。黑 1 佔天元（7 路盤最大的一點），"
                "白 2 立刻貼上來。看不懂沒關係 —— 第 1 章不要求你懂棋，"
                "只要求你能把棋圖和座標對上。",
    ),
    "ch01_game_mid": dict(AB=MID_B, AW=MID_W,
        comment="第 27 手之後。黑（X）在上方連成一大片，白（O）在下方兩路。"
                "此時盤上還沒有定案 —— 中間那條交界線是後面一半棋的戰場。",
    ),
    "ch01_game_final": dict(AB=FIN_B, AW=FIN_W,
        comment=f"終局（共 {len(REAL)} 手，雙方各 {B_MOVES} 手，最後兩手是虛手）。"
                f"棋盤上黑 {stones(FIN)[0]} 子、白 {stones(FIN)[1]} 子，"
                f"黑地 {territory(FIN)[0]} 點、白地 {territory(FIN)[1]} 點，"
                f"沒有單官。數子 C = {C:+.0f}、數目 J = {J:+.0f} —— "
                "兩套規則給出同一個答案，而 §5.2 會說明為什麼這不是巧合。",
    ),

    # --- §6 練習 ---------------------------------------------------------
    "ch01_ex1": dict(AW=["D4", "D5"], AB=["C4", "C5", "E4", "E5", "D6"],
        LB={"D3": "a"},
        comment="練習 1.1：白兩子 D4、D5 還剩幾口氣？黑下在 a 會發生什麼事？",
    ),
    "ch01_ex2": dict(AB=["A5", "B5", "C5", "C4", "C3", "C2", "C1"],
        AW=["E1", "E2", "E3", "F3", "G3"],
        comment="練習 1.2：黑與白各圍出了幾個交叉點的地？中間那一大片"
                "既走得到黑也走得到白的空點，又該算誰的？"
                "（提示：地的定義是「只走得到一色」。）",
    ),
}


def main():
    for name, spec in POSITIONS.items():
        save_sgf(str(OUT / f"{name}.sgf"), None, n=spec.get("n", N),
                 AB=spec.get("AB", ()), AW=spec.get("AW", ()),
                 AE=spec.get("AE", ()), LB=spec.get("LB"),
                 MA=spec.get("MA", ()), moves=spec.get("moves", ()),
                 comment=spec.get("comment"))
    print(f"寫出 {len(POSITIONS)} 個盤面")
    print(f"  7 路對局：{len(REAL)} 手（黑 {B_MOVES}、白 {W_MOVES}）")
    print(f"  C = {C:+.0f}、J = {J:+.0f}、提子（黑提／白提）= {PRIS_B} / {PRIS_W}")
    print(f"  子 {stones(FIN)}、地 {territory(FIN)}、單官 {len(dame(FIN))}")


if __name__ == "__main__":
    main()
