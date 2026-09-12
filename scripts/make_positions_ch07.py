#!/usr/bin/env python
"""產生第 7 章用到的所有 positions/*.sgf。

第 7 章的主角是一個【真實的收官盤面】：上面有好幾個互不干擾的局部，
每個局部有自己的溫度。整章要做的事就是把它們排序，然後收完。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from go_core.sgf import save_sgf   # noqa: E402

OUT = ROOT / "positions"
OUT.mkdir(exist_ok=True)
N = 9
C = "ABCDEFGHJ"


def bottom_left(n):
    """貼著左下角的走廊，長 n，開口朝右。"""
    black = [f"{C[i]}2" for i in range(n)]
    white = [f"{C[n]}1", f"{C[n]}2"]
    region = [f"{C[i]}1" for i in range(n)]
    return black, white, region


def top_left(n):
    """貼著左上角的走廊，長 n，開口朝右。"""
    black = [f"{C[i]}8" for i in range(n)]
    white = [f"{C[n]}9", f"{C[n]}8"]
    region = [f"{C[i]}9" for i in range(n)]
    return black, white, region


def bottom_right(n):
    """貼著右下角、沿右邊界往上的走廊，長 n，開口朝上。"""
    black = [f"H{r}" for r in range(1, n + 1)]
    white = [f"J{n + 1}", f"H{n + 1}"]
    region = [f"J{r}" for r in range(1, n + 1)]
    return black, white, region


bl2 = bottom_left(2)
tl3 = top_left(3)
br2 = bottom_right(2)
bl4 = bottom_left(4)

# 收官盤面：三個互不干擾的局部，長度 2、3、2
END_B = bl2[0] + tl3[0] + br2[0]
END_W = bl2[1] + tl3[1] + br2[1]
END_R = bl2[2] + tl3[2] + br2[2]

POSITIONS = {
    # --- §5 主盤面：三個局部的收官 -------------------------------------
    "ch07_endgame": dict(
        AB=END_B, AW=END_W,
        comment="§5 要收的盤面。三個互不干擾的局部：左下長 2、左上長 3、右下長 2。"
                "先算出每個局部的溫度，排序，然後照順序收 —— 這就是整章的內容。",
    ),

    # --- §4.2 溫度的兩個極端 --------------------------------------------
    "ch07_hot": dict(
        AB=bl4[0], AW=bl4[1],
        comment="長度 4 的走廊：溫度 7/8，快到 1 了。走廊越長越燙 ——"
                "因為黑封口能得的目數越多，而白擠進來的損失也越大。",
    ),
    "ch07_cold": dict(
        AB=["A4", "B4", "C4", "C3", "C2", "C1"],
        comment="已經定型的黑地，6 目。溫度 0 —— 雙方在這裡下都是虧，所以沒有人想動。"
                "溫度 0 的局部就是「收完了」的精確意思。",
    ),

    # --- §6 練習 ---------------------------------------------------------
    "ch07_ex1": dict(
        AB=bottom_left(3)[0] + top_left(2)[0],
        AW=bottom_left(3)[1] + top_left(2)[1],
        comment="練習 7.1：兩個局部，左下長 3、左上長 2。"
                "各自的溫度是多少？黑先的話第一手該下哪裡？",
    ),
    "ch07_ex2": dict(
        AB=bottom_left(2)[0] + top_left(2)[0] + bottom_right(3)[0],
        AW=bottom_left(2)[1] + top_left(2)[1] + bottom_right(3)[1],
        comment="練習 7.2：三個局部，兩個長 2、一個長 3。"
                "黑先，把整個收官順序寫出來，並算出最終的總分。",
    ),
}


def main():
    for name, spec in POSITIONS.items():
        save_sgf(str(OUT / f"{name}.sgf"), None, n=N,
                 AB=spec.get("AB", ()), AW=spec.get("AW", ()), AE=spec.get("AE", ()),
                 LB=spec.get("LB"), MA=spec.get("MA", ()),
                 moves=spec.get("moves", ()), comment=spec.get("comment"))
    print(f"寫出 {len(POSITIONS)} 個盤面")
    print("收官盤面的三個區域：")
    for nm, r in [("左下(2)", bl2[2]), ("左上(3)", tl3[2]), ("右下(2)", br2[2])]:
        print(f"   {nm}: {r}")
    print("練習 7.2 的三個區域：",
          bottom_left(2)[2], top_left(2)[2], bottom_right(3)[2])


if __name__ == "__main__":
    main()
