#!/usr/bin/env python
"""產生第 6 章用到的所有 positions/*.sgf。

第 6 章的盤面都很小，因為它要示範的是【值】，不是複雜的死活。
每一個盤面都會在章節裡被程式算出一個組合賽局值。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from go_core.sgf import save_sgf   # noqa: E402

OUT = ROOT / "positions"
OUT.mkdir(exist_ok=True)
N = 9


def corridor_stones(col0, row, n):
    """一條長 n 的走廊：上面一排黑牆，右端一顆白子當開口。

    回傳 (黑子, 白子, 走廊的點)。走廊在 row，開口朝右。
    """
    C = "ABCDEFGHJ"
    c = C.index(col0)
    black = [f"{C[c + i]}{row + 1}" for i in range(n)]
    white = [f"{C[c + n]}{row}", f"{C[c + n]}{row + 1}"]
    region = [f"{C[c + i]}{row}" for i in range(n)]
    return black, white, region


def top_corridor_stones(n):
    """貼著【上邊】的走廊，左端靠左邊界。這樣兩端都被盤邊封死，不會漏氣。

    第二個局部一定要這樣擺 —— 如果隨便放在盤面中間，那個「局部」其實
    通往一大片空地，根本不是一個封閉的局部，算出來的值也就沒有意義。
    """
    C = "ABCDEFGHJ"
    black = [f"{C[i]}8" for i in range(n)]
    white = [f"{C[n]}9", f"{C[n]}8"]
    region = [f"{C[i]}9" for i in range(n)]
    return black, white, region


b1, w1, r1 = corridor_stones("A", 1, 1)
b2, w2, r2 = corridor_stones("A", 1, 2)
b3, w3, r3 = corridor_stones("A", 1, 3)
b4, w4, r4 = corridor_stones("A", 1, 4)

# 第二條走廊，擺在上方，用來示範「兩個局部相加」
b1b, w1b, r1b = top_corridor_stones(1)
b2b, w2b, r2b = top_corridor_stones(2)

POSITIONS = {
    # --- §4.3 最小的例子：單官 --------------------------------------
    "ch06_dame": dict(
        AB=b1, AW=w1,
        LB={r1[0]: "a"},
        comment="全盤最小的局部：一個單官 a。黑下 a 不賺不賠，白下 a 也是。"
                "但【誰先下】這件事本身有意義 —— 這個局部的值是「星」，寫成 *。",
    ),
    "ch06_two_dame": dict(
        AB=b1 + b1b, AW=w1 + w1b,
        LB={r1[0]: "a", r1b[0]: "b"},
        comment="兩個單官 a 與 b。這是【見合】最單純的樣子："
                "你下 a 我就下 b，你下 b 我就下 a。整體的值是 0。"
                "用 CGT 寫就是 * + * = 0 —— 兩個一樣的星互相抵銷。",
    ),

    # --- §4.4 走廊 ------------------------------------------------------
    "ch06_corridor2": dict(
        AB=b2, AW=w2,
        LB={r2[0]: "a", r2[1]: "b"},
        comment="長度 2 的走廊。黑下 b 封口，得 1 目；白下 b 擠進來，"
                "剩下的 a 變成單官。所以這個局部的值是 {1 | *}。",
    ),
    "ch06_corridor3": dict(
        AB=b3, AW=w3,
        LB={r3[0]: "a", r3[1]: "b", r3[2]: "c"},
        comment="長度 3 的走廊。黑下 c 封口得 2 目；白下 c 擠進來，"
                "剩下的就是上一張圖那條長度 2 的走廊。值是 {2 | {1 | *}}。",
    ),
    "ch06_corridor4": dict(
        AB=b4, AW=w4,
        comment="長度 4。同樣的遞迴再套一層：{3 | {2 | {1 | *}}}。"
                "走廊每長一格，就在外面包一層。",
    ),

    # --- §4.2 分離和 ----------------------------------------------------
    "ch06_sum": dict(
        AB=b2 + b2b, AW=w2 + w2b,
        comment="兩條長度 2 的走廊，隔得很遠、互不干擾。"
                "整體的值就是兩個局部的值【相加】 —— 這就是第 6 章的全部槓桿。",
    ),

    # --- §4.5 已定型的地 ------------------------------------------------
    "ch06_settled": dict(
        AB=["A4", "B4", "C4", "C3", "C2", "C1"],
        comment="已經定型的黑地：A1–B3 共 6 目，四周全是黑子。"
                "雙方在這裡下都只是自填 —— 黑下損自己一目，白下是送死。"
                "這種【下了會虧】的局部，它的值就是一個【數】：6。",
    ),

    # --- §6 練習 ---------------------------------------------------------
    "ch06_ex1": dict(
        AB=["A3", "B3", "C3", "C2", "C1"],
        AW=["D1", "D2", "D3"],
        comment="練習 6.1：這個局部已經定型了嗎？它的值是多少？"
                "先自己數，再想想「雙方在這裡下會怎樣」。",
    ),
    "ch06_ex2": dict(
        AB=b3 + b1b, AW=w3 + w1b,
        LB={r1b[0]: "d"},
        comment="練習 6.2：一條長度 3 的走廊，加上一個單官 d。"
                "整體的值是多少？誰先下比較好？",
    ),
}


def main():
    for name, spec in POSITIONS.items():
        save_sgf(str(OUT / f"{name}.sgf"), None, n=N,
                 AB=spec.get("AB", ()), AW=spec.get("AW", ()), AE=spec.get("AE", ()),
                 LB=spec.get("LB"), MA=spec.get("MA", ()),
                 moves=spec.get("moves", ()), comment=spec.get("comment"))
    print(f"寫出 {len(POSITIONS)} 個盤面")
    for nm, r in [("走廊1", r1), ("走廊2", r2), ("走廊3", r3), ("走廊4", r4),
                  ("上方單官", r1b), ("右方走廊2", r2b)]:
        print(f"  {nm}: {r}")


if __name__ == "__main__":
    main()
