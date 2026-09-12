#!/usr/bin/env python
"""第 5 章配套範例 2：劫爭的判定式，以及可加性為什麼會壞掉。

對應章節：第 5 章 §4.4、§4.5、§4.6。

三件事：
  1. 有效劫材的門檻 t >= K —— 一個劫材差一目，可能就從「關鍵資源」變成「什麼都不是」。
  2. 判定式 m - h + tau >= 1，和完整模擬逐格比對。
  3. 可加性失效：同一個劫，在不同的盤面上值不同的東西。

跑法（在專案根目錄）：
    python examples/ch05_ko/ex02_ko_fight.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core.ko import ko_fight, ko_fight_rule   # noqa: E402


def part1_the_threshold():
    print("=" * 72)
    print("1. 有效劫材的門檻：t >= K")
    print("=" * 72)
    K = 10
    print(f"  劫的價值 K = {K}。我有一個值 15 的劫材，第二個劫材的價值變化如下：\n")
    print(f"{'第二個劫材':>10}{'算不算有效':>12}{'m':>4}{'結果':>10}")
    print("-" * 40)
    for t in [14, 12, 11, 10, 9, 8, 5]:
        mine = [15, t]
        valid = t >= K
        m = sum(1 for x in mine if x >= K)
        r = ko_fight_rule(mine, [20], K, i_hold_the_ko=False)
        print(f"{t:>10}{('是' if valid else '否'):>12}{m:>4}{r:>10}")

    print()
    print("  10 和 9 之間有一道懸崖。值 9 的棋不是「小一點的劫材」，")
    print("  它根本不是劫材 —— 對手會直接不理，消掉劫賺 10，讓你只賺 9。")
    assert ko_fight_rule([15, 10], [20], 10, False) == "打贏劫"
    assert ko_fight_rule([15, 9], [20], 10, False) == "打輸劫"


def part2_formula_vs_simulation():
    print()
    print("=" * 72)
    print("2. 判定式 vs 完整模擬")
    print("=" * 72)
    random.seed(3)
    total = bad = 0
    for _ in range(40000):
        K = random.randint(1, 20)
        mine = [random.randint(1, 30) for _ in range(random.randint(0, 6))]
        his = [random.randint(1, 30) for _ in range(random.randint(0, 6))]
        for hold in (True, False):
            total += 1
            if ko_fight(K, mine, his, hold)[0] != ko_fight_rule(mine, his, K, hold):
                bad += 1
    print(f"  {total} 組 (K, 我的劫材, 他的劫材, 手番)：不符 {bad} 組")
    assert bad == 0
    print("  判定式 m - h + tau >= 1 與完整模擬完全一致。")
    print()
    print("  順帶一提：這條式子和第 4 章的對殺判定式 d = a - b + tau 同一個形狀。")
    print("  它們是同一種結構 —— 交替消耗資源的競賽，加一個手番項。")


def part3_a_worked_fight():
    print()
    print("=" * 72)
    print("3. 一場劫爭，逐回合")
    print("=" * 72)
    for label, mine, his, K, hold in [
        ("我的劫材較多", [15, 12], [20], 10, False),
        ("第二個劫材縮水成 8", [15, 8], [20], 10, False),
        ("天下劫（K 大到沒人有劫材）", [30, 25], [28, 27], 100, True),
    ]:
        print(f"\n--- {label} ---")
        winner, log = ko_fight(K, mine, his, hold)
        for line in log:
            print(f"    {line}")
        print(f"    => {winner}")

    assert ko_fight(10, [15, 12], [20], False)[0] == "打贏劫"
    assert ko_fight(10, [15, 8], [20], False)[0] == "打輸劫"
    assert ko_fight(100, [30, 25], [28, 27], True)[0] == "打贏劫"
    assert ko_fight(100, [30, 25], [28, 27], False)[0] == "打輸劫"


def part4_additivity_fails():
    print()
    print("=" * 72)
    print("4. 可加性失效：同一個劫，在不同盤面上值不同的東西")
    print("=" * 72)
    K = 10
    print(f"  一個 K = {K} 的劫，黑握著它（tau = 1）。\n")
    scenarios = [
        ("全盤沒有任何劫材", [], []),
        ("右下角給白一個值 12 的局部", [], [12]),
        ("右下角那個局部只值 9", [], [9]),
        ("黑也在左上角有一個值 11 的局部", [11], [12]),
    ]
    print(f"{'盤面其他地方':<28}{'m':>3}{'h':>3}{'結果':>10}")
    print("-" * 46)
    for label, mine, his in scenarios:
        m = sum(1 for t in mine if t >= K)
        h = sum(1 for t in his if t >= K)
        r = ko_fight_rule(mine, his, K, i_hold_the_ko=True)
        print(f"{label:<28}{m:>3}{h:>3}{r:>10}")

    assert ko_fight_rule([], [], K, True) == "打贏劫"
    assert ko_fight_rule([], [12], K, True) == "打輸劫"
    assert ko_fight_rule([], [9], K, True) == "打贏劫"     # 9 < K，不算劫材
    assert ko_fight_rule([11], [12], K, True) == "打贏劫"

    print()
    print("  第二列：右下角多了一個局部，左上角這個劫的勝負就翻了。")
    print("  而右下角那個局部【本身值幾目完全沒變】。")
    print()
    print("  這就是可加性失效：")
    print("      V(左上 + 右下)  !=  V(左上) + V(右下)")
    print()
    print("  第三列同樣重要：值 9 的局部【不會】造成影響，因為 9 < K。")
    print("  所以影響不是連續的，是一道門檻 —— 這讓形勢判斷特別難做。")
    print()
    print("  對比：沒有劫的時候，兩個互不相鄰的角落完全獨立，")
    print("  各自的目數可以直接相加。那是第 6、7 章整套工具的地基。")


if __name__ == "__main__":
    part1_the_threshold()
    part2_formula_vs_simulation()
    part3_a_worked_fight()
    part4_additivity_fails()
    print("\n全部斷言通過。")
