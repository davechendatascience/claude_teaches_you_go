#!/usr/bin/env python
"""產生第 4 章用到的所有 positions/*.sgf。

第 4 章的對殺盤面不是手工設計的，是【搜出來的】：
在 4 路盤上隨機生成盤面，篩選出符合抽象模型三個前提（見 go_core/capture_race.py
的 race_preconditions）的那些，再挑出剛好涵蓋各種結果的六個。
這樣可以保證書上每一張對殺圖都是模型適用的乾淨案例。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from go_core.board import BLACK, WHITE, Board, neighbors, format_coord   # noqa: E402
from go_core.sgf import save_sgf                                          # noqa: E402

OUT = ROOT / "positions"
OUT.mkdir(exist_ok=True)


def nakade(shape, n=7, origin=(3, 2)):
    """幫一個眼位空間砌黑牆，外面再包一層白，做出「只剩一個大眼」的死棋。"""
    r0, c0 = origin
    R = {(r0 + dr, c0 + dc) for dr, dc in shape}
    ring = lambda S: {(r + dr, c + dc) for (r, c) in S
                      for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                      if 0 <= r + dr < n and 0 <= c + dc < n} - S
    wall = ring(R)
    outer = ring(R | wall)
    return (sorted(format_coord(p, n) for p in wall),
            sorted(format_coord(p, n) for p in outer),
            sorted(format_coord(p, n) for p in R))


w3, o3, r3 = nakade([(0, 0), (0, 1), (0, 2)])
w5, o5, r5 = nakade([(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)])

POSITIONS = {
    # --- §4.1 把氣分成三類（9 路，示範用，不需符合模型前提）-------------
    "ch04_classify": dict(n=9,
        AB=["C3", "C4", "C5"],
        AW=["E3", "E4", "E5"],
        LB={"D3": "c", "D4": "c", "D5": "c", "B4": "a", "F4": "b"},
        comment="黑白之間隔著一列。標 c 的三點【同時貼著兩邊】—— 那是公氣。"
                "標 a 的只貼黑、標 b 的只貼白。注意：兩道牆如果直接貼在一起，"
                "反而一口公氣都沒有 —— 公氣需要中間剛好隔一格。",
    ),

    # --- §4.2 最小的雙活（3 路盤）--------------------------------------
    "ch04_seki_min": dict(n=3,
        AB=["A1", "A2", "A3"],
        AW=["C1", "C2", "C3"],
        comment="最小的雙活：3 路盤，黑佔左列、白佔右列，中間三點全是公氣。"
                "雙方的外氣都是 0。誰先填公氣，誰就先把自己填死 —— 所以誰都不動。",
    ),

    # --- §4.2 無眼對無眼：一口公氣，誰先誰贏 -----------------------------
    "ch04_one_dame": dict(n=4,
        AB=["A1", "B1", "B3", "C1", "C3", "D1", "D2", "D3", "D4"],
        AW=["A2", "A3", "A4", "B2", "B4", "C4"],
        LB={"C2": "a"},
        comment="a 是全盤唯一的空點，也是雙方唯一的氣（外氣都是 0，公氣 1）。"
                "誰先下 a，誰就提掉對方 —— 因為提子發生在自殺判定之前。",
    ),

    # --- §4.2 三口公氣：雙活 --------------------------------------------
    "ch04_seki3": dict(n=4,
        AB=["C2", "C3", "C4"],
        AW=["A1", "A2", "A3", "A4", "B1", "C1", "D1", "D2", "D3", "D4"],
        LB={"B2": "a", "B3": "b", "B4": "c"},
        comment="黑三子被白完全包住，雙方的外氣都是 0，公氣有三口（a、b、c）。"
                "白先填任何一口，黑就跟著填，最後白會先沒氣。所以白不能動 —— 雙活。",
    ),

    # --- §4.3 有眼殺無眼 -------------------------------------------------
    "ch04_eye_wins": dict(n=4,
        AB=["A1", "A3", "A4", "B1", "B2", "B3", "C1", "C3"],
        AW=["C4", "D1", "D2", "D3", "D4"],
        LB={"A2": "e", "B4": "a", "C2": "b"},
        comment="黑有一個眼 e，白沒有。雙方的外氣都是 0，公氣是 a 與 b 兩口。"
                "黑贏 —— 而且不管誰先手。兩口公氣全部算在有眼的一方頭上。",
    ),
    "ch04_eye_loses": dict(n=4,
        AB=["A1", "A2", "A3", "A4", "B2", "B4", "C4", "D4"],
        AW=["B1", "B3", "C1", "C2", "C3", "D2"],
        LB={"D1": "e", "D3": "a"},
        comment="這次換白有眼 e。同樣的道理，唯一那口公氣 a 算給白，白勝。"
                "把這張圖和上一張並排看：眼在誰那邊，公氣就在誰那邊。",
    ),
    "ch04_both_eyes_seki": dict(n=4,
        AB=["A1", "A3", "A4", "B1", "B2", "B3", "B4", "C4"],
        AW=["C1", "C2", "D2", "D3", "D4"],
        LB={"A2": "e", "D1": "f", "C3": "a"},
        comment="雙方各有一個眼（e 與 f），還剩一口公氣 a。"
                "誰填 a 誰就先把自己填到只剩一個眼，然後被對方提。所以雙活。"
                "「雙方有眼也會雙活」—— 而且這是最常見的一種雙活。",
    ),
    "ch04_both_eyes_race": dict(n=4,
        AB=["B4", "C1", "C2", "C3", "C4", "D1", "D2", "D4"],
        AW=["A2", "A3", "A4", "B1", "B2", "B3"],
        LB={"A1": "e", "D3": "f"},
        comment="同樣雙方各一個眼，但這次【沒有公氣】。沒有公氣就沒有「誰先動誰吃虧」，"
                "於是回到單純的比快 —— 誰先手誰贏。公氣是雙活的必要條件。",
    ),

    # --- §4.4 大眼 -------------------------------------------------------
    "ch04_nakade3": dict(n=7, AB=w3, AW=o3,
        LB={r3[0]: "a", r3[1]: "b", r3[2]: "c"},
        comment="黑被白完全包圍，只剩 a、b、c 三點的大眼。"
                "白要下幾手才提得掉？先猜一個數，§4.4 會給兩個答案 —— 而且兩個都對。",
    ),
    "ch04_nakade5": dict(n=7, AB=w5, AW=o5,
        LB={r5[i]: ch for i, ch in enumerate("abcde")},
        comment="五點的大眼（花五）。口訣說「五目八氣」。"
                "八是哪來的？白實際上要下的手數並不是 8。",
    ),

    # --- §6 練習 ---------------------------------------------------------
    "ch04_ex1": dict(n=9,
        AB=["F3", "F4", "F5"],
        AW=["H3", "H4", "H5"],
        comment="練習 4.1：寫出這個盤面的 (a, b, c)。"
                "注意哪些點是公氣、哪些不是 —— 不要把「靠得近」當成「公用」。",
    ),
    "ch04_ex2": dict(n=3,
        AB=["A1", "A2", "A3"],
        AW=["C1", "C2"],
        LB={"C3": "a"},
        comment="練習 4.2：把最小雙活改一下 —— 白少一子，多出 a 這個點。"
                "先分類 (a, b, c) 並套判定式，然後【檢查三個前提】。"
                "最後用搜尋核對。三個答案會不會一致？",
    ),
    "ch04_ex3": dict(n=7, AB=w3, AW=o3,
        LB={r3[1]: "a"},
        comment="練習 4.3：同樣的三目大眼。白第一手應該下 a（正中），還是下旁邊？"
                "兩種都算一遍，比較白總共要花幾手。",
    ),
}


def main():
    for name, spec in POSITIONS.items():
        n = spec.get("n", 9)
        save_sgf(str(OUT / f"{name}.sgf"), None, n=n,
                 AB=spec.get("AB", ()), AW=spec.get("AW", ()), AE=spec.get("AE", ()),
                 LB=spec.get("LB"), MA=spec.get("MA", ()),
                 moves=spec.get("moves", ()), comment=spec.get("comment"))
    print(f"寫出 {len(POSITIONS)} 個盤面")


if __name__ == "__main__":
    main()
