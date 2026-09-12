#!/usr/bin/env python
"""產生第 5 章用到的所有 positions/*.sgf。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from go_core.board import BLACK, WHITE, Board, format_coord   # noqa: E402
from go_core.sgf import save_sgf                              # noqa: E402

OUT = ROOT / "positions"
OUT.mkdir(exist_ok=True)
N = 9
C = "ABCDEFGHJ"


def ko_stones(col, row, taker=BLACK):
    """在 (col,row) 左下角處排一個標準單劫。

    taker 是【現在可以提子的一方】。回傳 (taker 的子, 對方的子, 待提子, 提點)。
    """
    c = C.index(col)
    P = lambda dc, dr: f"{C[c + dc]}{row + dr}"
    three = [P(1, 2), P(0, 1), P(1, 0)]        # 可以提子的一方
    four = [P(2, 2), P(1, 1), P(3, 1), P(2, 0)]  # 被提的一方，P(1,1) 是待提子
    if taker == BLACK:
        return three, four, P(1, 1), P(2, 1)   # (黑子, 白子, 待提子, 提點)
    return four, three, P(1, 1), P(2, 1)


# 單劫（黑可提）
b1, w1, victim1, kopt1 = ko_stones("C", 4, BLACK)

# 三劫循環：三個劫，方向必須【交替】，否則有一方無子可提
tri_b, tri_w, tri_pts = [], [], []
for col, row, taker in [("A", 1, BLACK), ("F", 1, WHITE), ("A", 6, BLACK)]:
    blk, wht, victim, kopt = ko_stones(col, row, taker)
    tri_b += blk
    tri_w += wht
    tri_pts += [victim, kopt]

POSITIONS = {
    # --- §4.1 一個劫長什麼樣 ------------------------------------------
    "ch05_ko_shape": dict(
        AB=b1, AW=w1,
        LB={kopt1: "a"},
        comment="標準的單劫。白 D5 那一子只剩 a 這一口氣 —— 黑下 a 就提得掉它。"
                "而黑提完之後，黑那一顆子也只剩一口氣（原本白子的位置）。"
                "「你提我一子、我提你一子」，這就是劫。",
    ),
    "ch05_ko_taken": dict(
        AB=b1, AW=[s for s in w1 if s != victim1],
        LB={victim1: "b"},
        comment="黑提之後。現在輪到白，而 b 這一點白下下去就能把黑那顆子提回來 —— "
                "盤面會【一模一樣】地回到上一張圖。如果允許，兩人可以這樣提到天荒地老。",
    ),

    # --- §4.3 三劫循環 -------------------------------------------------
    "ch05_triple_ko": dict(
        AB=tri_b, AW=tri_w,
        comment="三個劫，方向交替（左下與左上黑可提，右下白可提）。"
                "只有基本劫規的話，這個盤面存在一條長度 6 的循環 —— "
                "六手之後盤面與手番完全復原。基本劫規擋不住它。",
    ),

    # --- §5 手算 --------------------------------------------------------
    "ch05_worked": dict(
        AB=b1 + ["G7", "H7", "J7", "G8", "G9"],
        AW=w1 + ["G6", "H6", "J6", "H8", "J8"],
        LB={kopt1: "a", "H9": "t"},
        comment="§5 要手算的盤面。左下是一個劫（提點 a），右上是黑的一個劫材："
                "黑下 t 就叫吃白 H8、J8 兩子。這一手值不值得當劫材，"
                "要看劫本身值多少 —— 這正是本章要算的東西。",
    ),

    # --- §6 練習 ---------------------------------------------------------
    "ch05_ex1": dict(
        AB=b1, AW=w1,
        LB={kopt1: "a", victim1: "b"},
        comment="練習 5.1：黑下 a 提子之後，白【不能】下 b。"
                "但白可以下別的地方。請說出：白下完別處、黑應了之後，白能不能下 b？"
                "三種規則（基本劫規、positional、situational）的答案一樣嗎？",
    ),
    "ch05_ex2": dict(
        AB=tri_b, AW=tri_w,
        comment="練習 5.2：這個三劫盤面，在 situational superko 之下，"
                "黑提了左下的劫以後，白最多能連續提幾次劫才會被規則擋住？",
    ),
}


def main():
    for name, spec in POSITIONS.items():
        save_sgf(str(OUT / f"{name}.sgf"), None, n=N,
                 AB=spec.get("AB", ()), AW=spec.get("AW", ()), AE=spec.get("AE", ()),
                 LB=spec.get("LB"), MA=spec.get("MA", ()),
                 moves=spec.get("moves", ()), comment=spec.get("comment"))
    print(f"寫出 {len(POSITIONS)} 個盤面")
    print(f"單劫：待提子 {victim1}、提點 {kopt1}")
    print(f"三劫的六個關鍵點：{tri_pts}")


if __name__ == "__main__":
    main()
