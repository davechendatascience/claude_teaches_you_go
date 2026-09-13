#!/usr/bin/env python
"""產生第 9 章用到的 positions/*.sgf。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from go_core.sgf import save_sgf                               # noqa: E402

OUT = ROOT / "positions"
OUT.mkdir(exist_ok=True)

COLS = "ABCDEFGHJKLMNOPQRST"


def wall(line, lo=4, hi=10):
    """第 line 線上、從 lo 到 hi 的一道直牆。"""
    return [f"{COLS[line - 1]}{r}" for r in range(lo, hi + 1)]


POSITIONS = {
    # --- §1 兩盞燈 -----------------------------------------------------
    "ch09_two_lamps": dict(n=9, AB=["C3"], AW=["G7"],
        LB={"E5": "a", "D4": "b"},
        comment="兩盞燈。黑 C3 與白 G7 各照亮自己周圍。"
                "a 是正中間、b 靠黑近一點 —— 這兩點的「亮度」差多少？"
                "整章就是在把這個問題變成一個算式。",
    ),

    # --- §4.1、§4.4 四線的牆 --------------------------------------------
    "ch09_wall4": dict(n=13, AB=wall(4),
        LB={"B7": "a", "K7": "b"},
        comment="黑在第四線築了一道七子的牆。a 在牆的【背後】，b 在牆的【前方】。"
                "兩點看起來都在黑的勢力範圍裡 —— 但多下一手的價值差二十二倍。",
    ),

    # --- §4.5 三線 vs 四線 vs 五線 ---------------------------------------
    "ch09_wall3": dict(n=13, AB=wall(3),
        comment="同樣七顆子，改放第三線。影響力場給它的分數最低 —— 在場的眼裡，第三線是三條線裡最差的一條。",
    ),
    "ch09_wall5": dict(n=13, AB=wall(5),
        comment="同樣七顆子放第五線。影響力場給它的分數最高 —— 而且會一路給到天元為止（命題 9.4）。場永遠偏好中央，所以它說不出「金角銀邊」。",
    ),
    # --- §6 練習 --------------------------------------------------------
    "ch09_ex1": dict(n=9, AB=["D4", "D5"], AW=["F6"],
        LB={"C7": "a", "E3": "b", "H8": "c"},
        comment="練習 9.1：用 lambda = 0.5 手算 a、b、c 三點的影響力，"
                "並排出大小順序。座標距離用格子數（Manhattan）。",
    ),
    "ch09_ex2": dict(n=13, AB=wall(4) + ["G10"], AW=["K4", "K10"],
        comment="練習 9.2：用 I > 1 和 I > 2 兩個門檻各算一次黑的模樣面積。"
                "兩個數字差很多 —— 哪一個才是「黑的地」？",
    ),
    "ch09_ex3": dict(n=13, AB=["D10"], AW=["D11", "C10", "E11"],
        LB={"N4": "a"},
        comment="練習 9.3：這是第 8 章的征子。在 a 放一顆黑子，"
                "影響力場在 D10 這一點的值會變多少？黑 D10 的死活會變多少？",
    ),
}


def main():
    for name, spec in POSITIONS.items():
        save_sgf(str(OUT / f"{name}.sgf"), None, n=spec.get("n", 9),
                 AB=spec.get("AB", ()), AW=spec.get("AW", ()), AE=spec.get("AE", ()),
                 LB=spec.get("LB"), MA=spec.get("MA", ()),
                 moves=spec.get("moves", ()), comment=spec.get("comment"))
    print(f"寫出 {len(POSITIONS)} 個盤面")


if __name__ == "__main__":
    main()
