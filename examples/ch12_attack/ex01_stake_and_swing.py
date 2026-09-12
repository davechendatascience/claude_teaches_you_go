#!/usr/bin/env python
"""第 12 章配套範例 1：賭注、擺盪，以及那個差一倍的單位錯誤。

對應章節：第 12 章 §4.1、§4.2、§4.3、§5.2。

一塊未定的棋同時記在兩個帳本上：死活（第 2 層，離散）與溫度（第 3 層，連續）。
這支腳本把兩者接起來：

  賭注   k = s + t           （子數 + 它圍住的空點）
  擺盪   2k                  （定理 12.2 —— 死活是雙向的）
  溫度   t({+k | -k}) = k    （命題 12.3 —— 於是可以和大場比大小）

然後示範「大場不如急場」修正的是什麼：一個差一倍的單位錯誤。

跑法（在專案根目錄）：
    python examples/ch12_attack/ex01_stake_and_swing.py
"""

import sys
from pathlib import Path

sys.setrecursionlimit(100000)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, WHITE, Board, find_string, format_coord   # noqa: E402
from go_core.attack import (as_switch, enclosed_empties, is_urgent,   # noqa: E402
                            life_swing, stake)
from go_core.temperature import mean, temperature                     # noqa: E402


def corridor_group(e, n=13):
    """眼位長 e 的一塊黑棋，四周被白包住。"""
    b = Board(n)
    b.place_many(BLACK, [f"B{r}" for r in range(1, e + 2)] + [f"A{e + 1}"])
    b.place_many(WHITE, [f"C{r}" for r in range(1, e + 2)]
                 + [f"B{e + 2}", f"A{e + 2}"])
    return b, find_string(b, "B1")


def one_group():
    print("=" * 70)
    print("1. 一塊未定的棋：數子、數目、算賭注")
    print("=" * 70)
    b, S = corridor_group(3, n=9)
    print(b)
    region = enclosed_empties(b, S)
    print(f"  子數 s = {len(S)}："
          f"{sorted(format_coord(p, 9) for p in S)}")
    print(f"  圍住的空點 t = {len(region)}："
          f"{sorted(format_coord(p, 9) for p in region)}")
    print(f"  賭注 k = s + t = {stake(b, S)}")
    print(f"  死活的擺盪（逐格數子，不套公式）= {life_swing(b, S)}")
    assert (len(S), len(region)) == (5, 3)
    assert stake(b, S) == 8 and life_swing(b, S) == 16
    print("\n  直覺會說「這塊棋值 8 目」。那是它【活著】的價值。")
    print("  它死掉你差多少？16 —— 因為那 8 點會變成對方的。")


def theorem_and_temperature():
    print("\n" + "=" * 70)
    print("2. 定理 12.2 與命題 12.3：八種大小逐一驗證")
    print("=" * 70)
    print(f"  {'眼位':>5}{'子數 s':>8}{'目數 t':>8}{'賭注 k':>9}"
          f"{'實際擺盪':>10}{'2k':>6}{'溫度':>7}{'均值':>7}")
    print("  " + "-" * 62)
    for e in range(1, 9):
        b, S = corridor_group(e)
        s_, t_ = len(S), len(enclosed_empties(b, S))
        k, sw = stake(b, S), life_swing(b, S)
        G = as_switch(b, S)
        print(f"  {e:>5}{s_:>8}{t_:>8}{k:>9}{sw:>10}{2 * k:>6}"
              f"{str(temperature(G)):>7}{str(mean(G)):>7}")
        assert sw == 2 * k                    # 定理 12.2
        assert temperature(G) == k            # 命題 12.3
        assert mean(G) == 0
    print("\n  擺盪永遠是 2k；溫度永遠是 k；均值永遠是 0。")
    print("  【均值為零的局部可以燙得要命】—— 這正是「急場」。")


def units_error():
    print("\n" + "=" * 70)
    print("3. 「大場不如急場」修正的是一個差一倍的單位錯誤")
    print("=" * 70)
    b, S = corridor_group(3, n=9)
    k = stake(b, S)
    print(f"  這塊棋：賭注 k = {k}，正確的價碼 2k = {2 * k}")
    print(f"\n  {'大場出入 D':>12}{'T = D/2':>10}{'2k vs D':>12}"
          f"{'正確決定':>10}{'只數一倍':>10}{'弄錯了嗎':>10}")
    flips = 0
    for D in [24, 20, 18, 16, 14, 12, 8]:
        urgent, _, _ = is_urgent(b, S, D / 2)
        correct = "補棋" if urgent else "佔大場"
        naive = "補棋" if k > D else "佔大場"
        flip = correct != naive
        flips += flip
        cmp = f"{2*k} {'>' if 2*k > D else '<' if 2*k < D else '='} {D}"
        print(f"  {D:>12}{D/2:>10}{cmp:>12}{correct:>10}{naive:>10}"
              f"{('是' if flip else ''):>10}")
    assert flips > 0
    print(f"\n  臨界點在 D = 2k = {2 * k}。用 k = {k} 當門檻，"
          f"會在 D 介於 {k} 和 {2 * k} 之間時全部選錯，")
    print("  而且錯的方向永遠一樣：低估急場。")

    print("\n  順帶一提：D 會隨棋局進行變小（第 7 章的溫度遞減），而 k 不變。")
    print("  所以【同一塊棋會從「不急」變成「急」】—— 不是心理作用。")


def main():
    one_group()
    theorem_and_temperature()
    units_error()


if __name__ == "__main__":
    main()
