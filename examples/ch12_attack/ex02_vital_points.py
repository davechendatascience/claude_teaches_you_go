#!/usr/bin/env python
"""第 12 章配套範例 2：做活點 —— 把死活題推導出來，而不是背下來。

對應章節：第 12 章 §4.4、§4.6、§5.3。

三件事：

1. 一條長 e 的直線眼位，做活點恰好 **e - 2** 個（窮舉驗證）。
   而攻方一手只佔得住一個 —— 鴿籠原理，本書第五次。
   於是「直三死、直四活」被推導出來，不必背。

2. 但 e - 2 只對【直線】眼位成立。方四同樣四個點，做活點是 **0** ——
   因為做活點量的是「切得開幾種」，不是「有多大」。

3. 分斷為什麼那麼兇：做活點對眼位是超可加的。
   切一刀，做活點從 e - 2 變成 (e1 - 2) + (e2 - 2) = e - 4。

跑法（在專案根目錄）：
    python examples/ch12_attack/ex02_vital_points.py
"""

import sys
from pathlib import Path

sys.setrecursionlimit(100000)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, WHITE, Board, find_string, format_coord   # noqa: E402
from go_core.attack import (can_kill, life_distance, stake,           # noqa: E402
                            vital_points)


def corridor_group(e, n=9):
    b = Board(n)
    b.place_many(BLACK, [f"B{r}" for r in range(1, e + 2)] + [f"A{e + 1}"])
    b.place_many(WHITE, [f"C{r}" for r in range(1, e + 2)]
                 + [f"B{e + 2}", f"A{e + 2}"])
    return b, find_string(b, "B1")


def census():
    print("=" * 70)
    print("1. 直線眼位：做活點恰好 e - 2 個")
    print("=" * 70)
    print(f"  {'眼位 e':>7}{'做活點':>24}{'個數':>6}{'e-2':>5}"
          f"{'守方先手':>10}{'攻方先手':>10}")
    print("  " + "-" * 64)
    for e in range(1, 8):
        b, S = corridor_group(e)
        vp = vital_points(b, S, BLACK)
        names = sorted(format_coord(p, 9) for p in vp)
        d, _ = life_distance(b, S, BLACK, max_moves=2)
        killed = can_kill(b, S, BLACK, max_moves=3)
        print(f"  {e:>7}{str(names):>24}{len(vp):>6}{max(0, e - 2):>5}"
              f"{('活' if d else '死'):>10}{('死' if killed else '活'):>10}")
        assert len(vp) == max(0, e - 2), e

    print("\n  鴿籠原理：攻方一手只佔得住一個做活點。")
    for e in range(1, 8):
        b, S = corridor_group(e)
        n_vital = len(vital_points(b, S, BLACK))
        assert can_kill(b, S, BLACK, max_moves=3) == (n_vital <= 1), e
    print("  「攻方先手殺得掉」<=>「做活點 <= 1」<=> e <= 3，七種大小無一例外。")
    print("\n  直三死、直四活 = 一個減法（e - 2）加一次鴿籠原理。")


def square_four():
    print("\n" + "=" * 70)
    print("2. 方四：同樣四點，做活點是 0")
    print("=" * 70)
    sq = Board(9)
    sq.place_many(BLACK, ["A3", "B3", "C3", "C2", "C1"])
    sq.place_many(WHITE, ["A4", "B4", "C4", "D3", "D2", "D1"])
    Ssq = find_string(sq, "A3")
    print(sq)
    vsq = vital_points(sq, Ssq, BLACK)
    print(f"  方四（2x2 眼位）：做活點 {len(vsq)} 個 -> {vsq}")
    assert len(vsq) == 0

    st, Sst = corridor_group(4)
    vst = vital_points(st, Sst, BLACK)
    print(f"  直四（1x4 眼位）：做活點 {len(vst)} 個 -> "
          f"{sorted(format_coord(p, 9) for p in vst)}")
    assert len(vst) == 2

    print("\n  眼位一樣大，做活點 0 vs 2，死活相反。")
    print("  做活點量的是【切得開幾種】—— 而方四的四個點圍成一個環，")
    print("  環沒有割點，所以怎麼下都切不開。")
    print("  （第 8 章 §4.2 說方四「擠」的那個環，就是同一個環。）")


def splitting():
    print("\n" + "=" * 70)
    print("3. 分斷：做活點是超可加的，切一刀少兩個")
    print("=" * 70)
    conn = Board(9)
    conn.place_many(BLACK, ["B1", "B2", "B3", "B4", "B5", "A5"])
    conn.place_many(WHITE, ["C1", "C2", "C3", "C4", "C5", "B6", "A6"])
    Sc = find_string(conn, "B1")
    print("  連在一起（眼位 4）：")
    print("  " + str(conn).replace("\n", "\n  "))
    print(f"    做活點 {len(vital_points(conn, Sc, BLACK))} 個，"
          f"賭注 {stake(conn, Sc)}，白先手殺得掉 = "
          f"{can_kill(conn, Sc, BLACK, max_moves=3)}")
    assert len(vital_points(conn, Sc, BLACK)) == 2
    assert not can_kill(conn, Sc, BLACK, max_moves=3)

    split = Board(9)
    split.place_many(BLACK, ["B1", "B2", "B3", "A3", "B6", "B7", "B8", "A6"])
    split.place_many(WHITE, ["C1", "C2", "C3", "B4", "A4", "C6", "C7", "C8",
                             "B9", "A9", "B5", "A5"])
    print("\n  被切成兩塊（眼位 2 + 2）：")
    print("  " + str(split).replace("\n", "\n  "))
    for seed, name in [("B1", "下塊"), ("B6", "上塊")]:
        Ss = find_string(split, seed)
        vp = vital_points(split, Ss, BLACK)
        killed = can_kill(split, Ss, BLACK, max_moves=3)
        print(f"    {name}：做活點 {len(vp)} 個，賭注 {stake(split, Ss)}，"
              f"白先手殺得掉 = {killed}")
        assert vp == [] and killed

    print("\n  同樣的空間，連著殺不掉，斷開【兩塊都死】。")
    print("  (e1 - 2) + (e2 - 2) = e - 4 —— 切一刀，做活點直接少兩個。")
    print("  一塊棋要活需要兩個眼；兩塊棋要活需要四個。")


def main():
    census()
    square_four()
    splitting()


if __name__ == "__main__":
    main()
