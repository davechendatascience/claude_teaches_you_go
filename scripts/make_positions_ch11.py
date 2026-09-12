#!/usr/bin/env python
"""產生第 11 章用到的 positions/*.sgf。

手割的兩張圖用的是【同樣四顆子、不同順序】—— 所以它們必須用 moves（會編號），
不能用 AB/AW。編號本身就是這一章的重點。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from go_core.sgf import save_sgf                                   # noqa: E402

OUT = ROOT / "positions"
OUT.mkdir(exist_ok=True)

# 四顆子：黑 B2（天元）、黑 A1（角）；白 B3、白 C2
ORDER_GOOD = [("B", "B2"), ("W", "B3"), ("B", "A1"), ("W", "C2")]
ORDER_BAD = [("B", "A1"), ("W", "B3"), ("B", "B2"), ("W", "C2")]

POSITIONS = {
    # --- §4.2 手割：同樣四顆子，兩種順序 ---------------------------------
    "ch11_tewari_good": dict(n=3, moves=ORDER_GOOD,
        comment="順序甲：黑先佔天元，之後才下角。四顆子的位置和下一張圖【完全一樣】，"
                "只有編號不同。每一手的失分：0、0、11、1。",
    ),
    "ch11_tewari_bad": dict(n=3, moves=ORDER_BAD,
        comment="順序乙：黑第一手就下角。同樣的四顆子，但失分變成 18、8、1、1 —— "
                "第一手掉 18 目，一看就知道不能下。而總帳（黑失分減白失分）"
                "和順序甲一模一樣，都是 +10。",
    ),

    # --- §4.1 提子時順序有影響 --------------------------------------------
    "ch11_capture_a": dict(n=3,
        moves=[("B", "A1"), ("B", "B1"), ("W", "A2"), ("W", "B2"), ("W", "C1")],
        comment="順序甲：黑先放 A1、B1，白再包。白第 5 手提掉黑兩子，角上變空。",
    ),
    "ch11_capture_b": dict(n=3, AW=["A2", "B2", "C1"], AB=["A1"],
        LB={"B1": "x"},
        comment="順序乙：白先擺好三顆，黑再放。這時黑 A1 是合法的（有 B1 這口氣），"
                "但 x 點不合法（自殺）。同樣五手，兩個【不同】的盤面 —— "
                "有提子的時候，手割不能用。",
    ),

    # --- §4.1 劫讓「同一個盤面」變成兩個局面 --------------------------------
    "ch11_ko_same": dict(n=3, AB=["A3", "C3", "B2", "C1"], AW=["A2", "A1"],
        LB={"B3": "a"},
        comment="輪到白走。這個盤面的 V 是 -9 還是 +9，取決於【a 是不是劫點】。"
                "同一個盤面、同一方走，差 18 目（整個棋盤）—— "
                "盤面一樣，局面不一樣。",
    ),

    # --- §6 練習 -----------------------------------------------------------
    "ch11_ex1": dict(n=3, moves=[("B", "B2"), ("W", "A1"), ("B", "C3")],
        comment="練習 11.1：三手棋。把它重排成【白先下 A1】的順序，"
                "並回答：重排之後合法嗎？如果不合法，說明手割為什麼在這裡失效。",
    ),
    "ch11_ex2": dict(n=3, AB=["B2", "B1"], AW=["B3", "A2"],
        LB={"C2": "a", "A1": "b", "C1": "c"},
        comment="練習 11.2：輪到黑走。a、b、c 哪些是最佳著？"
                "先用「靠中央」這條規則猜，再用求解器核對。",
    ),
    "ch11_ex3": dict(n=3, AB=["A3", "C3", "B2", "C1"], AW=["A2", "A1"],
        LB={"B3": "a"},
        comment="練習 11.3：輪到白走。白下 a 提掉黑一子。"
                "如果 a 是劫點（白剛剛才被提），白不能下 —— "
                "算出兩種情況的 V，並解釋差距為什麼是整個棋盤。",
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
