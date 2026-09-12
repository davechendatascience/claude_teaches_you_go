#!/usr/bin/env python
"""產生第 12 章用到的 figures/*.txt。

三張表，全部算出來：
  * ch12_swing      定理 12.1：死活的擺盪 = 2 x 賭注
  * ch12_eyespace   眼位普查：做活點個數與「攻方先手殺不殺得掉」
  * ch12_units      「大場不如急場」修正的那個【差一倍】的單位錯誤
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.setrecursionlimit(100000)
sys.path.insert(0, str(ROOT))

from go_core.attack import (as_switch, can_kill, enclosed_empties,   # noqa: E402
                            life_distance, life_swing, stake,
                            vital_points)
from go_core.board import BLACK, WHITE, Board, format_coord         # noqa: E402
from go_core.strings import find_string                             # noqa: E402
from go_core.temperature import mean, temperature                   # noqa: E402

OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)

N = 13


def corridor_group(e):
    b = Board(N)
    b.place_many(BLACK, [f"B{r}" for r in range(1, e + 2)] + [f"A{e + 1}"])
    b.place_many(WHITE, [f"C{r}" for r in range(1, e + 2)]
                 + [f"B{e + 2}", f"A{e + 2}"])
    return b, find_string(b, "B1")


def swing_table():
    rows = [f"  {'眼位':>5}{'子數 s':>8}{'目數 t':>8}{'賭注 s+t':>10}"
            f"{'實際擺盪':>10}{'2(s+t)':>9}{'溫度 t(G)':>11}",
            "  " + "-" * 62]
    for e in range(1, 9):
        b, S = corridor_group(e)
        s_, t_ = len(S), len(enclosed_empties(b, S))
        k, sw = stake(b, S), life_swing(b, S)
        temp = temperature(as_switch(b, S))
        assert sw == 2 * k and temp == k and mean(as_switch(b, S)) == 0
        rows.append(f"  {e:>5}{s_:>8}{t_:>8}{k:>10}{sw:>10}{2 * k:>9}{str(temp):>11}")
    rows.append("")
    rows.append("  擺盪永遠是賭注的兩倍；未定塊的溫度永遠等於賭注、均值為 0。")
    return "\n".join(rows)


def eyespace_table():
    rows = [f"  {'眼位 e':>7}{'做活點數':>10}{'= e - 2 ?':>11}"
            f"{'守方先手':>10}{'攻方先手':>10}",
            "  " + "-" * 50]
    for e in range(1, 8):
        b, S = corridor_group(e)
        vp = vital_points(b, S, BLACK)
        expect = max(0, e - 2)
        d, _ = life_distance(b, S, BLACK, max_moves=2)
        killed = can_kill(b, S, BLACK, max_moves=3)
        rows.append(f"  {e:>7}{len(vp):>10}{str(len(vp) == expect):>11}"
                    f"{('活' if d else '死'):>10}{('死' if killed else '活'):>10}")
    rows.append("")
    rows.append("  做活點恰好 e - 2 個。攻方一手只佔得住一個，所以")
    rows.append("  e >= 4（做活點 >= 2）時攻方先手也殺不掉 —— 直三死、直四活。")
    return "\n".join(rows)


def units_table(D=20):
    rows = [f"  大場出入 D = {D} 目（也就是全局溫度 T' = {D // 2}）", "",
            f"  {'賭注 k':>8}{'正確的價碼 2k':>15}{'正確決定':>10}"
            f"{'只數一倍':>10}{'弄錯了嗎':>10}",
            "  " + "-" * 55]
    wrong = 0
    for k in range(4, 24, 2):
        correct = "急場" if 2 * k > D else "大場"
        naive = "急場" if k > D else "大場"
        flip = correct != naive
        wrong += flip
        rows.append(f"  {k:>8}{2 * k:>15}{correct:>10}{naive:>10}"
                    f"{('是' if flip else ''):>10}")
    rows.append("")
    rows.append(f"  只要賭注落在 {D // 2} < k <= {D} 這一段，用一倍算就會選錯 ——")
    rows.append(f"  這一段有 {wrong} 格，而它正是實戰上最常出現的區間。")
    return "\n".join(rows)


FIGURES = {
    "ch12_swing": swing_table,
    "ch12_eyespace": eyespace_table,
    "ch12_units": units_table,
}


def main():
    for name, fn in FIGURES.items():
        (OUT / f"{name}.txt").write_text(fn().rstrip("\n") + "\n",
                                         encoding="utf-8", newline="\n")
        print(f"  寫出 {name}.txt")


if __name__ == "__main__":
    main()
