#!/usr/bin/env python
"""第 11 章配套範例 1：手割的兩層，以及它的三個失效條件。

對應章節：第 11 章 §4.1、§4.2、§5.1、§5.2。

手割在傳統教材裡看起來像魔法。它的理論內容其實有兩層：

  第一層（定理 11.1）  無提子 ==> 盤面只取決於「哪個點放了什麼顏色」的集合。
                       因為加法可交換。

  第二層（定理 11.2）  Σ黑失分 − Σ白失分 = V(s0) − V(sn)。
                       右邊只認頭尾，所以左邊與順序無關。望遠鏡消去，一行。

第二層才是手割真正在用的東西：**它不是重排棋子，是重新分攤失分。**

三個失效條件都在這裡示範：提子、劫、以及雙方手數改變。

跑法（在專案根目錄）：
    python examples/ch11_joseki/ex01_tewari.py
"""

import itertools
import sys
from collections import Counter
from pathlib import Path

sys.setrecursionlimit(100000)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, WHITE, Board, format_coord, opposite     # noqa: E402
from go_core.minimax import Solver                                  # noqa: E402
from go_core.tewari import (is_capture_free, play_sequence,          # noqa: E402
                            stone_set, tewari_equal)

SOLVER = Solver(komi=0.0, max_ply=15)
BLACK_STONES = ["B2", "A1"]
WHITE_STONES = ["B3", "C2"]


def walk(seq):
    """走一遍序列，回傳 (每一手的 (顏色, 點, 失分), 終局盤面)。"""
    b, steps = Board(3), []
    for colour, coord in seq:
        before = SOLVER.search(b, colour)[0]
        t = b.copy()
        taken = t.play(colour, coord)
        assert not taken, "手割的前提是無提子"
        after = SOLVER.search(t, opposite(colour))[0]
        loss = (before - after) if colour == BLACK else (after - before)
        steps.append((colour, coord, loss))
        b = t
    return steps, b


def layer_one():
    print("=" * 70)
    print("第一層（定理 11.1）：無提子時，盤面只認集合")
    print("=" * 70)
    A = [(BLACK, "B2"), (WHITE, "B3"), (BLACK, "A1"), (WHITE, "C2")]
    B = [(BLACK, "A1"), (WHITE, "C2"), (BLACK, "B2"), (WHITE, "B3")]
    r = tewari_equal(A, B, n=3)
    print(f"  兩種順序到達同一個盤面嗎：{r['same']}")
    print(f"  兩個序列都無提子嗎：{is_capture_free(A, 3) and is_capture_free(B, 3)}")
    assert r["same"] and not r["captures_a"] and not r["captures_b"]
    print("\n  加法可交換 —— 這就是全部的理論內容。")


def failure_capture():
    print("\n" + "=" * 70)
    print("失效一：有提子的時候，順序會改變盤面")
    print("=" * 70)
    C = [(BLACK, "A1"), (BLACK, "B1"), (WHITE, "A2"), (WHITE, "B2"),
         (WHITE, "C1")]
    D = [(WHITE, "A2"), (WHITE, "B2"), (WHITE, "C1"), (BLACK, "A1"),
         (BLACK, "B1")]
    for name, seq in [("甲（黑先放，白再包）", C), ("乙（白先包，黑再放）", D)]:
        b, caps = play_sequence(seq, n=3, allow_illegal=True)
        print(f"\n  順序 {name}：")
        print("    " + str(b).replace("\n", "\n    "))
        took = [(i, co, sorted(format_coord(p, 3) for p in t))
                for i, _, co, t in caps if t]
        bad = [(i, co) for i, _, co, t in caps if t is None]
        print(f"    提子：{took}    不合法的手：{bad}")

    r = tewari_equal(C, D, n=3)
    print(f"\n  兩個盤面相同嗎：{r['same']}")
    print(f"  只有順序乙有的子：{r['only_b']}")
    assert not r["same"]
    assert r["captures_a"] and r["illegal_b"]
    print("\n  加法可交換，減法不可交換。有提子就有減法。")


def failure_ko():
    print("\n" + "=" * 70)
    print("失效二：有劫的時候，同一個盤面不是同一個局面")
    print("=" * 70)
    b = Board(3)
    b.place_many(BLACK, ["A3", "C3", "B2", "C1"])
    b.place_many(WHITE, ["A2", "A1"])
    print(b)
    v_free, mv = SOLVER.search(b, WHITE, ko=None)
    v_ko, _ = SOLVER.search(b, WHITE, ko=b._pt("B3"))
    print(f"  輪到白走")
    print(f"    沒有劫：   V = {v_free:+.0f}   白的最佳著 = "
          f"{format_coord(mv, 3) if mv else '虛手'}")
    print(f"    B3 是劫點：V = {v_ko:+.0f}")
    print(f"    差 {abs(v_ko - v_free):.0f} 目 —— 整個棋盤")
    assert v_free == -9 and v_ko == 9
    print("\n  棋子集合完全一樣、輪走的人一樣，V 差 18 目。")
    print("  「盤面」不足以決定局面 —— 你還得知道剛剛發生了什麼。")


def failure_ko_census(depth=7):
    """這不是一個罕見的邊角情況 —— 把 3 路盤掃一遍數給你看。（約 40 秒）"""
    from collections import defaultdict

    from go_core.tewari import reachable_states, solve_all

    print("\n" + "=" * 70)
    print("失效二有多常見？把 3 路盤 7 手之內的局面全掃一遍")
    print("=" * 70)
    states = reachable_states(3, depth)
    table, _ = solve_all(states, n=3)

    def value(key):
        vals = table[key][1].values()
        return max(vals) if key[1] == BLACK else min(vals)

    groups = defaultdict(set)
    for key in table:
        groups[(key[0], key[1])].add(key)        # 同盤面、同輪次
    multi = {g: ks for g, ks in groups.items() if len({k[2] for k in ks}) > 1}
    diff = {g: ks for g, ks in multi.items() if len({value(k) for k in ks}) > 1}

    gaps = sorted(abs(max(value(k) for k in ks) - min(value(k) for k in ks))
                  for ks in diff.values())
    print(f"  可解的局面（有合法手）：{len(table)}")
    print(f"  同盤面、同輪次，但劫狀態不同：{len(multi)} 組")
    print(f"  其中 V 真的不一樣：          {len(diff)} 組"
          f"（{len(diff) / len(multi):.0%}）")
    print(f"  V 的差距：最小 {min(gaps):.0f} 目、最大 {max(gaps):.0f} 目")
    from collections import Counter
    for g, c in sorted(Counter(gaps).items()):
        print(f"    差 {g:>2.0f} 目：{c} 組")
    assert len(multi) == 196 and len(diff) == 72
    assert max(gaps) == 18
    print("\n  三分之一以上的情況下，「同一個盤面」的 V 真的不同。")
    print("  手割假設盤面決定一切 —— 這 72 組就是那個假設的反例。")


def failure_move_count():
    print("\n" + "=" * 70)
    print("失效三：雙方手數必須各自不變")
    print("=" * 70)
    A = [(BLACK, "B2"), (WHITE, "A1"), (BLACK, "C3")]
    B = [(BLACK, "C3"), (WHITE, "A1"), (BLACK, "B2")]
    r = tewari_equal(A, B, n=3)
    print(f"  合法的重排（黑兩手、白一手不變）：盤面相同嗎 {r['same']}")
    assert r["same"]
    assert Counter(c for c, _ in A) == Counter(c for c, _ in B)
    print(f"  兩個序列的顏色計數：{dict(Counter(c for c, _ in A))}")
    print("\n  傳統教材說「把這兩手拿掉」—— 必須是【雙方各一手】同時拿掉，")
    print("  否則輪次對不上，比較的就不是同一件事。")


def layer_two():
    print("\n" + "=" * 70)
    print("第二層（定理 11.2）：失分的【差】與順序無關")
    print("=" * 70)
    print(f"  {'順序':<24}{'每一手的失分':<26}{'黑':>5}{'白':>5}{'黑-白':>7}")
    print("  " + "-" * 65)
    diffs, finals = set(), set()
    for bo in itertools.permutations(BLACK_STONES):
        for wo in itertools.permutations(WHITE_STONES):
            seq = [(BLACK, bo[0]), (WHITE, wo[0]),
                   (BLACK, bo[1]), (WHITE, wo[1])]
            steps, final = walk(seq)
            lb = sum(l for c, _, l in steps if c == BLACK)
            lw = sum(l for c, _, l in steps if c == WHITE)
            diffs.add(lb - lw)
            finals.add(final.grid.tobytes())
            order = " ".join(f"{'黑' if c == BLACK else '白'}{p}" for c, p in seq)
            detail = " ".join(f"{p}{l:+.0f}" for _, p, l in steps)
            print(f"  {order:<24}{detail:<26}{lb:>5.0f}{lw:>5.0f}{lb - lw:>+7.0f}")

    assert len(finals) == 1, "四種順序必須到達同一個盤面"
    assert diffs == {10.0}, diffs
    print(f"\n  終局盤面：{len(finals)} 種")
    print(f"  四種順序的（黑失分 − 白失分）：{sorted(diffs)[0]:+.0f}，完全相同")

    # 望遠鏡：差 = V(頭) − V(尾)
    v0 = SOLVER.search(Board(3), BLACK)[0]
    fin = Board(3)
    fin.place_many(BLACK, BLACK_STONES)
    fin.place_many(WHITE, WHITE_STONES)
    v4 = SOLVER.search(fin, BLACK)[0]
    print(f"\n  V(空盤) − V(終局) = {v0:+.0f} − ({v4:+.0f}) = {v0 - v4:+.0f}")
    assert v0 - v4 == 10.0
    print("  望遠鏡級數在棋盤上收斂成兩個數字。")

    print("\n  但注意：守恆的只有【差】。")
    print("    順序甲：黑 11、白 1    順序乙：黑 19、白 9")
    print("    黑的總失分從 11 變成 19 —— 手割不能回答「黑虧了幾目」，")
    print("    只能回答「這個交換對誰有利」。")

    print("\n  而順序乙有一手掉 18 目 —— 一看就知道不能下。")
    print("  順序甲最大的一手只掉 11 目，看起來像正常的交換。")
    print("  兩本帳的總數一樣，只有一本告訴你該改什麼。這就是手割。")


def main():
    layer_one()
    failure_capture()
    failure_ko()
    failure_ko_census()
    failure_move_count()
    layer_two()


if __name__ == "__main__":
    main()
