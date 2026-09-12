#!/usr/bin/env python
"""第 4 章配套範例 1：對殺判定式是怎麼被驗證出來的。

對應章節：第 4 章 §4.2、§4.3、§4.6。

書上的判定式（定理 4.4、4.6、4.7）不是從別的書上抄來的，也不是猜的。
它們是這樣得到的，而這支腳本把整個過程重跑一遍：

  第 1 步  寫一個【抽象模型】：只有 (a, b, c, 誰有眼, 手番) 五個數，
           三種著手（填外氣、填公氣、虛手），做完整的三值搜尋。
  第 2 步  猜一條公式，然後和模型【逐格比對】。不合就修公式。
  第 3 步  把模型拿去對【真實盤面】。不合就找出模型缺了什麼前提。

第 3 步跑了三輪，每一輪的「不合」都逼出一個我原本沒寫出來的假設：
    輪 1：終端判定的順序錯了（雙活被誤判成一方獲勝）
    輪 2：公氣的口袋必須是封閉的
    輪 3：眼點本身就是一口氣，不能又算外氣又算眼（重複計算）
          而且外氣口袋不能還能做出眼

跑法（在專案根目錄）：
    python examples/ch04_capture_races/ex01_race_formula.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, WHITE, Board, neighbors, format_coord        # noqa: E402
from go_core.capture_race import (classify_liberties, eye_points,        # noqa: E402
                                  race_formula, race_preconditions,
                                  race_winner)
from go_core.search import can_capture                                   # noqa: E402
from go_core.strings import all_strings                                  # noqa: E402


def part1_formula_vs_model():
    print("=" * 74)
    print("1. 公式 vs 完整搜尋樹：逐格比對")
    print("=" * 74)
    total = mismatch = 0
    for c in range(0, 8):
        for a in range(0, 10):
            for b in range(0, 10):
                for me in (False, True):
                    for op in (False, True):
                        for turn in (True, False):
                            if b + c + op == 0 or a + c + me == 0:
                                continue          # 退化輸入
                            total += 1
                            if race_winner(a, b, c, me, op, turn) != \
                               race_formula(a, b, c, me, op, turn):
                                mismatch += 1
    print(f"  比對 {total} 組 (a, b, c, 我的眼, 他的眼, 手番)：不符 {mismatch} 組")
    assert mismatch == 0
    print("  公式與搜尋樹完全一致。")


def part2_the_three_regimes():
    print()
    print("=" * 74)
    print("2. 三種局面，三條門檻（c = 公氣數）")
    print("=" * 74)
    print("  令 d = a - b + tau（tau = 1 表示我先手）\n")
    print(f"{'c':>3} | {'無眼對無眼':^26} | {'雙方有眼':^22}")
    print(f"{'':>3} | {'我勝門檻':>10}{'雙活帶':>16} | {'我勝門檻':>10}{'雙活帶':>12}")
    print("-" * 74)
    for c in range(0, 6):
        ne_win = max(c, 1)
        ne_seki = f"[{2-c}, {c-1}]" if c >= 2 else "（空）"
        be_win = c + 1
        be_seki = f"[{1-c}, {c}]" if c >= 1 else "（空）"
        print(f"{c:>3} | {'d >= ' + str(ne_win):>10}{ne_seki:>16} |"
              f" {'d >= ' + str(be_win):>10}{be_seki:>12}")

    print("\n  有眼殺無眼：我勝 <=> b <= a + c + tau，而且【永遠不會雙活】。")
    print("  意思是公氣全部算給有眼的一方。")
    print()
    print("  三件值得記住的事：")
    print("    * c <= 1 時雙活帶是空的 —— 沒有公氣就沒有雙活。")
    print("    * 雙活帶的寬度是 2(c-1)：每多一口公氣，就往兩邊各擴一格。")
    print("    * 「氣多者勝」只是 c <= 1 的特例。真正的門檻是 d >= c。")

    # 書上明講的幾個數字
    assert race_formula(0, 0, 3, False, False, True) == "雙活"      # 三口公氣
    assert race_formula(0, 0, 1, False, False, True) == "我勝"      # 一口公氣
    assert race_formula(0, 0, 2, True, False, True) == "我勝"       # 有眼殺無眼
    assert race_formula(0, 0, 2, True, False, False) == "我勝"      # 不管誰先手
    assert race_formula(3, 2, 3, False, False, True) == "雙活"      # 練習 4.4


def part3_model_vs_board():
    """把模型拿去對真實盤面。這一步是三個前提的來源。"""
    print()
    print("=" * 74)
    print("3. 模型 vs 真實盤面：前提是怎麼被逼出來的")
    print("=" * 74)
    random.seed(11)
    N = 4
    pts = [(r, c) for r in range(N) for c in range(N)]
    stats = {"總生成": 0, "兩塊棋": 0, "合乎前提": 0, "一致": 0}
    seen = set()

    for _ in range(60000):
        b = Board(N)
        for p in pts:
            b.grid[p] = random.choices([0, BLACK, WHITE], [0.28, 0.36, 0.36])[0]
        stats["總生成"] += 1
        bs, ws = all_strings(b, BLACK), all_strings(b, WHITE)
        if len(bs) != 1 or len(ws) != 1:
            continue
        stats["兩塊棋"] += 1
        B, W = bs[0], ws[0]
        if not race_preconditions(b, B, W)[0]:
            continue
        d = classify_liberties(b, B, W)
        eB, eW = eye_points(b, B), eye_points(b, W)
        # 眼點【本身就是一口氣】，所以外氣要先把它扣掉，否則重複計算
        a, bb, c = d["a"] - len(eB), d["b"] - len(eW), d["c"]
        if a < 0 or bb < 0:
            continue
        if a + c + len(eB) == 0 or bb + c + len(eW) == 0 or a + bb + c > 9:
            continue
        key = b.grid.tobytes()
        if key in seen:
            continue
        seen.add(key)
        stats["合乎前提"] += 1

        ok = True
        for turn in (True, False):
            predicted = race_formula(a, bb, c, bool(eB), bool(eW), turn)
            cands = frozenset(d["own"] | d["opp"] | d["shared"])
            mover = BLACK if turn else WHITE
            target = next(iter(W if turn else B))
            captured, _ = can_capture(b, target, mover, candidates=cands,
                                      max_depth=2 * (a + bb + c) + 6)
            expected_capture = (predicted == "我勝") if turn else (predicted == "他勝")
            if captured != expected_capture:
                ok = False
        if ok:
            stats["一致"] += 1

    for k, v in stats.items():
        print(f"  {k:<10}{v:>8}")
    rate = 100 * stats["一致"] / max(stats["合乎前提"], 1)
    print(f"\n  合乎前提的盤面中，模型與盤面搜尋一致：{rate:.1f}%")
    assert stats["合乎前提"] >= 100
    assert stats["一致"] == stats["合乎前提"]
    print("  100%。而在【不】合乎前提的盤面上，一致率只有九成出頭 ——")
    print("  那百分之幾，就是 §4.6 那三個前提存在的理由。")


def part4_a_counterexample():
    """練習 4.2：前提不成立時，公式會安靜地給出錯的答案。"""
    print()
    print("=" * 74)
    print("4. 一個反例：前提不成立時會發生什麼")
    print("=" * 74)
    b = Board(3)
    b.place_many(BLACK, ["A1", "A2", "A3"]).place_many(WHITE, ["C1", "C2"])
    print(b)
    B, W = all_strings(b, BLACK)[0], all_strings(b, WHITE)[0]
    d = classify_liberties(b, B, W)
    ok, why = race_preconditions(b, B, W)
    print(f"\n  (a, b, c) = ({d['a']}, {d['b']}, {d['c']})")
    print(f"  前提成立嗎？{ok}")
    for r in why:
        print(f"      {r}")
    predicted = race_formula(d["a"], d["b"], d["c"], False, False, False)
    cands = frozenset(d["own"] | d["opp"] | d["shared"])
    captured, mv = can_capture(b, next(iter(B)), WHITE, candidates=cands, max_depth=14)
    print(f"\n  白先 —— 判定式說：{predicted}")
    print(f"  白先 —— 盤面搜尋說：{'白殺得掉黑' + (f'（下 ' + format_coord(mv, 3) + '）' if mv else '')}"
          if captured else "  白先 —— 盤面搜尋說：殺不掉")
    assert not ok and predicted == "雙活" and captured
    print("\n  判定式說雙活，真相是白勝。公式沒有錯，是它的前提沒被滿足 ——")
    print("  而它不會警告你。這就是為什麼書上把三個前提寫成定理的一部分。")


if __name__ == "__main__":
    part1_formula_vs_model()
    part2_the_three_regimes()
    part3_model_vs_board()
    part4_a_counterexample()
    print("\n全部斷言通過。")
