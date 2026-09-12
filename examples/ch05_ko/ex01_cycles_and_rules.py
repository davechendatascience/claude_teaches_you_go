#!/usr/bin/env python
"""第 5 章配套範例 1：劫是環，三種規則是三種剪法。

對應章節：第 5 章 §4.1、§4.2、§4.3。

這支腳本用【在真實盤面上找環】的方式，把三種劫規則的差別算出來：

    規則              單劫      三劫循環
    無規則            2-環      2-環        <- 遊戲不會結束
    基本劫規          無環      6-環        <- 擋得住短的，擋不住長的
    positional        無環      無環
    situational       無環      無環

中間那一列（基本劫規 / 三劫 = 6-環）就是 superko 存在的全部理由。

跑法（在專案根目錄）：
    python examples/ch05_ko/ex01_cycles_and_rules.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, WHITE, Board, format_coord                # noqa: E402
from go_core.ko import (GameState, IllegalMove, find_cycle,           # noqa: E402
                        max_game_length)

C = "ABCDEFGHJ"
RULES = ["none", "basic", "positional", "situational"]


def ko_stones(col, row, taker=BLACK):
    """排一個標準單劫。回傳 (黑子, 白子, 待提子, 提點)。

    taker 是【現在可以提子的一方】。三個劫要構成循環，方向必須交替 ——
    否則其中一方根本無子可提，環就接不起來。
    """
    c = C.index(col)
    P = lambda dc, dr: f"{C[c + dc]}{row + dr}"
    three = [P(1, 2), P(0, 1), P(1, 0)]            # 可以提子的一方
    four = [P(2, 2), P(1, 1), P(3, 1), P(2, 0)]    # 被提的一方，P(1,1) 是待提子
    return (three, four, P(1, 1), P(2, 1)) if taker == BLACK \
        else (four, three, P(1, 1), P(2, 1))


def build(spots, n=9):
    b, pts = Board(n), []
    for col, row, taker in spots:
        blk, wht, victim, kopt = ko_stones(col, row, taker)
        b.place_many(BLACK, blk)
        b.place_many(WHITE, wht)
        pts += [victim, kopt]
    return b, pts


SINGLE = build([("C", 4, BLACK)])
DOUBLE = build([("A", 1, BLACK), ("F", 1, WHITE)])
TRIPLE = build([("A", 1, BLACK), ("F", 1, WHITE), ("A", 6, BLACK)])
SAME_WAY = build([("A", 1, BLACK), ("F", 1, BLACK), ("A", 6, BLACK)])


def part1_table():
    print("=" * 72)
    print("1. 四種盤面 x 四種規則：找得到環嗎？")
    print("=" * 72)
    cases = [("單劫", SINGLE), ("雙劫（方向交替）", DOUBLE),
             ("三劫（方向交替）", TRIPLE), ("三劫（方向相同）", SAME_WAY)]
    print(f"{'規則':<14}" + "".join(f"{name:>18}" for name, _ in cases))
    print("-" * 72)
    table = {}
    for rule in RULES:
        row = []
        for _, (board, pts) in cases:
            st = GameState(board, rule=rule, to_move=BLACK)
            cycle = find_cycle(st, pts, max_len=10)
            row.append(len(cycle) if cycle else 0)
        table[rule] = row
        print(f"{rule:<14}" + "".join(
            f"{(str(k) + '-環' if k else '無環'):>18}" for k in row))

    print()
    print("  第三欄第二列 —— 基本劫規擋不住三劫循環的 6-環 —— 就是 superko 的理由。")
    print("  最後一欄：三個劫【方向相同】時反而沒有環，因為有一方無子可提。")
    print("  循環需要交替，這一點常被忽略。")

    assert table["none"][0] == 2
    assert table["basic"][0] == 0 and table["basic"][2] == 6
    assert table["positional"] == [0, 0, 0, 0]
    assert table["situational"] == [0, 0, 0, 0]
    assert table["basic"][3] == 0          # 同向三劫沒有環


def part2_the_cycle():
    print()
    print("=" * 72)
    print("2. 那條 6-環長什麼樣")
    print("=" * 72)
    board, pts = TRIPLE
    print(board)
    st = GameState(board, rule="basic", to_move=BLACK)
    cycle = find_cycle(st, pts, max_len=10)
    print("\n  基本劫規之下的合法循環：")
    for i, (colour, p) in enumerate(cycle, 1):
        print(f"    第 {i} 手  {'黑' if colour == BLACK else '白'} {format_coord(p, 9)}")
    print("  六手之後，盤面與手番【完全復原】—— 而每一手都沒有違反基本劫規，")
    print("  因為基本劫規只回頭看一手，看不到六手之前。")
    assert len(cycle) == 6

    print()
    print("  同一條路徑，換成 situational superko：")
    st = GameState(board, rule="situational", to_move=BLACK)
    played = 0
    for colour, p in cycle:
        try:
            st.play(colour, p)
            played += 1
        except IllegalMove:
            print(f"    第 {played + 1} 手 {format_coord(p, 9)} 被規則擋住")
            break
    print(f"  只走得了 {played} 手。有人必須讓步 —— 於是勝負才有可能產生。")
    assert played == 5


def part3_termination():
    print()
    print("=" * 72)
    print("3. 終止性：為什麼這條規則非有不可")
    print("=" * 72)
    print("  沒有劫規則 -> 狀態圖有環 -> 存在無限長的棋局 -> 這盤棋沒有結果。")
    print("  有 positional superko -> 每個盤面至多出現一次 -> 手數 <= 3^(n*n)。")
    print()
    print(f"{'盤面':>6}{'交叉點':>8}{'手數上界 3^(n*n)':>24}")
    for n in (3, 5, 9, 13, 19):
        print(f"{n:>4} 路{n*n:>8}{max_game_length(n):>24.6g}")
    print()
    print("  這些數字荒謬地大（19 路盤是 10^172，比可觀測宇宙的原子還多），")
    print("  但【有限】和【無限】在數學上是天差地別：")
    print("    有限 -> 有結果 -> 有勝負 -> 「最佳下法」有定義（第 10 章 Zermelo 定理）")
    print("    無限 -> 有些棋局沒有結果 -> 談「最佳」沒有意義")
    assert max_game_length(3) == 3 ** 9
    assert max_game_length(19) == 3 ** 361


def part4_single_ko_all_rules_agree():
    print()
    print("=" * 72)
    print("4. 三種規則在【單劫】上的行為完全一致")
    print("=" * 72)
    print("  常見的誤解：以為「打劫要隔一手」是一條獨立的規則。")
    print("  它不是 —— 它是「不准重複盤面」的推論。\n")
    for rule in ["basic", "positional", "situational"]:
        board, _ = build([("C", 4, BLACK)])
        st = GameState(board, rule=rule, to_move=BLACK)
        st.play(BLACK, "E5")                       # 黑提劫
        try:
            st.copy().play(WHITE, "D5")
            immediate = "可以"
        except IllegalMove:
            immediate = "不行"
        st.play(WHITE, "A1")                       # 白下別處（劫材）
        st.play(BLACK, "A9")                       # 黑應
        try:
            st.play(WHITE, "D5")
            later = "可以"
        except IllegalMove:
            later = "不行"
        print(f"  {rule:<14} 立刻回提：{immediate}    下完別處再回提：{later}")
        assert immediate == "不行" and later == "可以"
    print("\n  三者一致。差別只出現在需要回頭看更遠歷史的三劫循環。")


if __name__ == "__main__":
    part1_table()
    part2_the_cycle()
    part3_termination()
    part4_single_ko_all_rules_agree()
    print("\n全部斷言通過。")
