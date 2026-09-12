#!/usr/bin/env python
"""第 8 章配套範例 1：形的普查 —— 把「好形」變成一張可以排序的表。

對應章節：第 8 章 §4.1、§4.2、§5.2。

這支腳本做三件事：

1. 窮舉 2 到 6 顆子的所有連通形狀（去掉旋轉／翻轉的重複），
   用第 2 章的三項分解逐項算，依效率排序。
2. 把兩種低效率分開：**擠**（第二項，連接的必要成本）
   與**愚**（第三項，純浪費）。表裡會出現「氣一樣多但來源不同」的成對形狀。
3. 驗證命題 8.2 與推論 8.3：邊際氣公式，以及「任何一手最多多兩口氣」。

跑法（在專案根目錄）：
    python examples/ch08_shape/ex01_shape_census.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, EMPTY, Board, find_string, neighbors     # noqa: E402
from go_core.shape import (canonical_shape, enumerate_shapes,        # noqa: E402
                           marginal_decomposition, shape_on_board,
                           shape_report)

N = 13
ORIGIN = (4, 4)          # 擺在正中央，避開邊界，讓 b(S) = 0


def census(size):
    """所有大小為 size 的形狀，去對稱之後的報告表。"""
    seen = {}
    for shape in enumerate_shapes(size, span=size):
        key = canonical_shape(shape)
        if key in seen:
            continue
        board, S = shape_on_board(shape, n=N, origin=ORIGIN)
        r = shape_report(board, S)
        assert r["blocked"] == 0, "擺在中央應該不會被邊界遮到"
        seen[key] = r
    return seen


def source_of_loss(r, size):
    """這個形狀的氣少在哪裡？"""
    tags = []
    if r["internal_pairs"] > size - 1:          # 超過樹狀連接的最低成本
        tags.append("擠")
    if r["duplicated"] > 0:
        tags.append("愚")
    return "+".join(tags) if tags else "—"


def main():
    print("=" * 74)
    print("形的普查：Sdeg - 2e(S) - 重複 = 氣          （第 2 章定理 2.5）")
    print("=" * 74)

    for size in range(2, 7):
        table = census(size)
        rows = sorted(table.items(), key=lambda kv: -kv[1]["liberties"])
        best = rows[0][1]["liberties"]
        worst = rows[-1][1]["liberties"]
        print(f"\n--- {size} 子：共 {len(rows)} 種形狀，氣從 {best} 到 {worst} ---")
        print(f"  {'Sdeg':>5}{'-2e':>6}{'-重複':>7}{'= 氣':>6}{'eta':>7}   低效率來源")
        shown = rows if len(rows) <= 8 else rows[:4] + rows[-4:]
        if len(rows) > 8:
            print("  （只印最好的四個與最差的四個）")
        for _, r in shown:
            print(f"  {r['deg_sum']:>5}{-2 * r['internal_pairs']:>6}"
                  f"{-r['duplicated']:>7}{r['liberties']:>6}"
                  f"{r['efficiency']:>7.2f}   {source_of_loss(r, size)}")

        # 氣一樣多、來源不同的成對形狀
        by_libs = {}
        for _, r in rows:
            by_libs.setdefault(r["liberties"], []).append(r)
        for libs, group in sorted(by_libs.items()):
            kinds = {source_of_loss(r, size) for r in group}
            if "擠" in kinds and "愚" in kinds:
                print(f"  ** {libs} 氣這一格裡，【擠】和【愚】兩種形狀都有 —— "
                      f"同一個數字，兩種病。")
                break

    # ---- 命題 8.2 與推論 8.3 ----
    print("\n" + "=" * 74)
    print("命題 8.2：dL = deg(p) - k - 1 - delta+     推論 8.3：dL <= 2")
    print("=" * 74)

    checked = tight = 0
    best_delta = -99
    by_deg = {2: -99, 3: -99, 4: -99}
    for size in range(1, 7):
        for shape in enumerate_shapes(size, span=size):
            for origin in [ORIGIN, (0, 0), (0, 1), (1, 0), (0, 4)]:   # 中央、角、貼角、邊
                board, S = shape_on_board(shape, n=N, origin=origin)
                for p in board.points():
                    if board.grid[p] != EMPTY:
                        continue
                    if not any(q in S for q in neighbors(p, N)):
                        continue
                    m = marginal_decomposition(board, S, p)
                    assert m["delta"] == m["predicted"], (sorted(S), p, m)
                    assert m["new_duplicated"] >= 0, m
                    assert m["delta"] <= m["deg"] - m["contacts"] - 1, m
                    checked += 1
                    tight += (m["new_duplicated"] == 0)
                    best_delta = max(best_delta, m["delta"])
                    by_deg[m["deg"]] = max(by_deg[m["deg"]], m["delta"])

    print(f"  檢查 {checked} 手：命題 8.2 全中，delta+ 從未為負")
    print(f"  實際出現的最大 dL = {best_delta}")
    print(f"  上界達到（delta+ = 0）的比例 = {tight / checked:.0%}")
    print(f"  分位置的最大 dL：角 {by_deg[2]}、邊 {by_deg[3]}、中央 {by_deg[4]}")
    assert best_delta == 2
    assert by_deg[4] == 2 and by_deg[3] == 1 and by_deg[2] == 0
    print("\n  角上的棋長不出氣來（上限 0）—— 這是 deg(p) 小的另一面。")


if __name__ == "__main__":
    main()
