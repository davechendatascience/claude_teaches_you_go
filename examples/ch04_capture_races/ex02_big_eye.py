#!/usr/bin/env python
"""第 4 章配套範例 2：大眼氣數表，用完整搜尋重新算一遍。

對應章節：第 4 章 §4.4。

「三目三氣、四目五氣、五目八氣、六目十二氣。」

這串數字每一本圍棋書都會列，但沒有一本說它在數什麼。你自己排一個三目大眼、
數白要下幾手，會數到 4，不是 3 —— 然後以為自己排錯了。

你沒有排錯。那張表數的是【淨手數】：

    淨手數 = 攻方實際下的手數 - 守方在眼內被迫陪下的手數

這支腳本把三個數字都算出來，並驗證三條閉合解：

    攻方實際手數   g(n) = 1 + n(n-1)/2
    守方陪下手數        = n - 2
    淨手數（口訣表） f(n) = 2 + (n-1)(n-2)/2 = g(n) - (n-2)

跑法（在專案根目錄）：
    python examples/ch04_capture_races/ex02_big_eye.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, WHITE, Board, format_coord                    # noqa: E402
from go_core.capture_race import (attacker_moves, big_eye_liberties,     # noqa: E402
                                  defender_moves)
from go_core.search import moves_to_capture, net_moves_to_capture        # noqa: E402
from go_core.strings import liberties, find_string                       # noqa: E402

N = 7


def nakade(shape, origin=(3, 2)):
    """幫一個眼位空間砌黑牆，外面再包一層白 —— 做出「只剩一個大眼」的死棋。"""
    r0, c0 = origin
    R = {(r0 + dr, c0 + dc) for dr, dc in shape}
    ring = lambda S: {(r + dr, c + dc) for (r, c) in S
                      for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                      if 0 <= r + dr < N and 0 <= c + dc < N} - S
    wall = ring(R)
    board = Board(N)
    for p in wall:
        board.grid[p] = BLACK
    for p in ring(R | wall):
        board.grid[p] = WHITE
    return board, frozenset(R), next(iter(wall))


SHAPES = [
    ("直二",   [(0, 0), (0, 1)],                                   True),
    ("直三",   [(0, 0), (0, 1), (0, 2)],                           True),
    ("曲三",   [(0, 0), (0, 1), (1, 1)],                           True),
    ("丁四",   [(0, 0), (0, 1), (0, 2), (1, 1)],                   True),
    ("方四",   [(0, 0), (0, 1), (1, 0), (1, 1)],                   True),
    ("直四",   [(0, 0), (0, 1), (0, 2), (0, 3)],                   False),   # 活形
    ("花五",   [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)],           True),
    ("刀把五", [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2)],           True),
    ("花六",   [(0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 1)],   True),
]


def part1_table():
    print("=" * 76)
    print("1. 三個數字：攻方實際手數、守方陪下、淨手數")
    print("=" * 76)
    print(f"{'形狀':<8}{'n':>3}{'攻方手數 g':>11}{'守方陪下':>9}{'淨手數 f':>10}"
          f"{'公式 f(n)':>10}{'':>3}秒")
    print("-" * 76)
    for label, shape, dead in SHAPES:
        board, region, target = nakade(shape)
        n = len(shape)
        t0 = time.time()
        g = moves_to_capture(board, target, WHITE, candidates=region,
                             max_depth=5 * n + 8)
        f = net_moves_to_capture(board, target, WHITE, region,
                                 max_depth=5 * n + 8)
        dt = time.time() - t0
        fml = big_eye_liberties(n) if dead else "—"
        gs = "殺不掉" if g is None else str(g)
        fs = "殺不掉" if f is None else str(f)
        ds = "—" if (g is None or f is None) else str(g - f)
        print(f"{label:<8}{n:>3}{gs:>11}{ds:>9}{fs:>10}{str(fml):>10}{dt:>6.1f}")

        if dead:
            assert f == big_eye_liberties(n), (label, f, big_eye_liberties(n))
            assert g == attacker_moves(n), (label, g, attacker_moves(n))
            assert g - f == defender_moves(n)
        else:
            assert g is None and f is None      # 活形殺不掉

    print()
    print("  同樣的點數，死形的三個數字完全一樣（丁四 = 方四，花五 = 刀把五）——")
    print("  大眼氣數只看【點數】，不看形狀。形狀只決定它是不是死形。")


def part2_closed_forms():
    print()
    print("=" * 76)
    print("2. 三條閉合解")
    print("=" * 76)
    print(f"{'n':>3}{'g(n) = 1 + n(n-1)/2':>22}{'守方 = n - 2':>14}"
          f"{'f(n) = 2 + (n-1)(n-2)/2':>26}")
    print("-" * 76)
    for n in range(2, 7):
        g, dfd, f = attacker_moves(n), defender_moves(n), big_eye_liberties(n)
        print(f"{n:>3}{g:>22}{dfd:>14}{f:>26}")
        assert g - dfd == f
    print("\n  恆等式：g(n) - (n-2) = 1 + n(n-1)/2 - n + 2")
    print("                      = 2 + (n^2 - 3n + 2)/2")
    print("                      = 2 + (n-1)(n-2)/2  =  f(n)   ✓")
    print()
    print("  差分：g 的差分是 2,3,4,5（每次多一）；f 的差分是 2,3,4（也是每次多一）。")
    print("  兩者相差 n-2，正好就是守方每次多陪一手。")


def part3_the_vital_point():
    print()
    print("=" * 76)
    print("3. 要點：為什麼第一手一定要下在正中")
    print("=" * 76)
    board, region, target = nakade([(0, 0), (0, 1), (0, 2)])
    print(board)
    print()
    for p in sorted(region):
        b2, R2, t2 = nakade([(0, 0), (0, 1), (0, 2)])
        b2.play(WHITE, p)
        rest = moves_to_capture(b2, t2, WHITE, candidates=R2,
                                max_depth=18, _to_move=BLACK)
        total = None if rest is None else rest + 1
        verdict = f"白總共 {total} 手" if total else "殺不掉 —— 黑做出兩個眼"
        print(f"  白第一手 {format_coord(p, N)}: {verdict}")

    def total_after(coord):
        b2, R2, t2 = nakade([(0, 0), (0, 1), (0, 2)])
        b2.play(WHITE, coord)
        rest = moves_to_capture(b2, t2, WHITE, candidates=R2,
                                max_depth=18, _to_move=BLACK)
        return None if rest is None else rest + 1

    assert total_after("D4") == 4
    assert total_after("C4") is None and total_after("E4") is None

    print()
    print("  下正中是唯一能殺的一手，其他兩點【直接失敗】，不是慢一步。")
    print("  原因：下在旁邊那顆子只有一口氣，馬上被提；提完之後剩下的兩點")
    print("  互不相連，就是兩個真眼。")
    print()
    print("  這和第 3 章練習 3.4 是同一件事的兩面：")
    print("    防守方想【切開】眼位做出兩個眼；")
    print("    進攻方想【佔住那個切點】讓它切不開。")
    print("  「敵之要點即我之要點」講的就是這個共用的切點。")


def part4_why_the_defender_plays_inside():
    print()
    print("=" * 76)
    print("4. 守方為什麼要在自己眼裡下棋？")
    print("=" * 76)
    print("  直覺上，在自己的眼位裡落子是自填，是壞棋。但搜尋顯示守方【必須】這麼做。")
    print()
    board, region, target = nakade([(0, 0), (0, 1), (0, 2)])
    with_defence = net_moves_to_capture(board, target, WHITE, region, max_depth=20)
    plain = moves_to_capture(board, target, WHITE, candidates=region, max_depth=20)
    print(f"  三目大眼：攻方實際 {plain} 手，淨值 {with_defence}，守方陪了 {plain - with_defence} 手。")
    print()
    print("  守方那一手在做什麼？【提子】。")
    print("  白填到剩最後一口時，黑下那一點會提掉白已經填進去的兩顆子，")
    print("  逼白從頭再填一次。黑花一手，換白多花兩手 —— 淨賺一手。")
    print()
    print("  在對殺的帳上，守方每在眼裡下一手，就是他【沒有】拿去填對方外氣的一手。")
    print("  所以那些手要從攻方的成本裡扣掉 —— 這就是淨手數的全部意義。")
    assert plain - with_defence == defender_moves(3) == 1


if __name__ == "__main__":
    part1_table()
    part2_closed_forms()
    part3_the_vital_point()
    part4_why_the_defender_plays_inside()
    print("\n全部斷言通過。")
