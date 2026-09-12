#!/usr/bin/env python
"""第 8 章配套範例 2：征子 —— 一條斜線，與它算出來的陰影。

對應章節：第 8 章 §4.4、§5.1、§6（練習 8.3）。

傳統教材說「征子引徵要下在征子的路線上」，然後畫一條手繪的斜線。
這支腳本不畫那條線 —— 它把線算出來：

    對盤上每一個空點，放一顆守方的子，重跑一次征子，看結果會不會翻轉。

翻轉的那些點所成的集合就是陰影。而陰影裡**不在征子路徑上**的那些點，
才是真正意義的「引徵」—— 一顆離戰場十幾路遠的子，決定近處一塊棋的死活。

跑法（在專案根目錄）：
    python examples/ch08_shape/ex02_ladder.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, WHITE, Board, format_coord               # noqa: E402
from go_core.ladder import (describe_path, ladder_capture,           # noqa: E402
                            ladder_shadow)
from go_core.render import render_ascii                              # noqa: E402

N = 13
TARGET = "D10"
WHITE_STONES = ["D11", "C10", "E11"]


def setup(extra_black=None):
    b = Board(N)
    b.place(BLACK, TARGET)
    b.place_many(WHITE, WHITE_STONES)
    if extra_black:
        b.place(BLACK, extra_black)
    return b


def main():
    base = setup()

    # ---- 1. 兩個方向，只有一邊征得到 ----
    print("=" * 70)
    print("1. 白該從哪一邊叫吃？（命題 8.9：長出去那一點，其他三鄰恰好一顆白子）")
    print("=" * 70)
    for first in ["E10", "D9"]:
        t = base.copy()
        t.play(WHITE, first)
        # 黑往另一邊長
        reply = "D9" if first == "E10" else "E10"
        t.play(BLACK, reply)
        from go_core.strings import find_string, liberties
        libs = liberties(t, find_string(t, TARGET))
        ok, path = ladder_capture(base, TARGET, WHITE, max_depth=200)
        print(f"  白先叫吃 {first}，黑長 {reply} -> 黑 {len(libs)} 氣"
              f"   {'征子繼續' if len(libs) == 2 else '跑掉了'}")
    ok, path = ladder_capture(base, TARGET, WHITE, max_depth=200)
    print(f"\n  整體：白征子成立 = {ok}，共 {len(path)} 手")
    print(f"  前八手：{describe_path(path[:8], N)} ...")
    assert ok and len(path) == 35

    # ---- 2. 陰影 ----
    print("\n" + "=" * 70)
    print("2. 征子陰影：每一個空點都放一顆黑子試一次")
    print("=" * 70)
    shadow = ladder_shadow(base, TARGET, WHITE, max_depth=200)
    on_path = {p for _, p in path}
    off_path = sorted(shadow - on_path)
    print(f"  陰影共 {len(shadow)} 點，其中 {len(shadow & on_path)} 點在征子路徑上，"
          f"{len(off_path)} 點不在")
    print("  不在路徑上的那些點，才是真正的「引徵」：")
    print("   ", " ".join(format_coord(p, N) for p in off_path))

    labels = {p: ("x" if p in on_path else "o") for p in shadow}
    print()
    print(render_ascii(base, labels=labels))

    # ---- 3. 最遠的引徵點 ----
    print("=" * 70)
    print("3. 引徵能有多遠？")
    print("=" * 70)
    origin = base._pt(TARGET)
    dist = lambda q: abs(q[0] - origin[0]) + abs(q[1] - origin[1])
    breaker = max(off_path, key=dist)
    name = format_coord(breaker, N)
    print(f"  離 {TARGET} 最遠而且不在路徑上的陰影點：{name}，"
          f"距離 {dist(breaker)} 路")
    broke, _ = ladder_capture(setup(name), TARGET, WHITE, max_depth=200)
    print(f"  在 {name} 放一顆黑子之後，白還征得到嗎 = {broke}")
    assert not broke

    # ---- 4. 練習 8.3 的三個點 ----
    print("\n" + "=" * 70)
    print("4. 練習 8.3：a=G7、b=K7、c=M11")
    print("=" * 70)
    for label, coord in [("a", "G7"), ("b", "K7"), ("c", "M11")]:
        pt = base._pt(coord)
        in_shadow = pt in shadow
        still, _ = ladder_capture(setup(coord), TARGET, WHITE, max_depth=200)
        kind = ("在征子路徑上" if pt in on_path else "不在路徑上（真正的引徵）") \
            if in_shadow else "不在陰影裡"
        print(f"  {label} = {coord:<4} 在陰影裡 = {str(in_shadow):<5} "
              f"破得掉征子 = {str(not still):<5} {kind}")
        assert in_shadow == (not still)

    print("\n  陰影不是一條線，是【路徑加上它外緣的一格】。")


if __name__ == "__main__":
    main()
