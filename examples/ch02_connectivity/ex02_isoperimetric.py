#!/usr/bin/env python
"""第 2 章配套範例 2：金角銀邊草肚皮，用窮舉驗證等周定理。

對應章節：第 2 章 §4.5（定理 2.10、定理 2.11）、§4.5.1。

  1. 掃過所有 a x b 長方形，比對整數最佳解與 AM-GM 給的連續下界（定理 2.10）。
  2. 放寬到所有連通形狀 —— 會發現【長方形不是最省的】。面積 5 的十字形只要
     8 顆子，而唯一的長方形 1x5 要 12 顆。原因是定理 2.5 的第三項對空地
     一樣成立，只是符號的好壞相反。這就是 §4.5.1。
  3. 對角、邊、中央各自窮舉，確認就算絕對值全變了，比值仍然是 1 : √2 : 2
     —— 定理 2.11 的反射論證預測的正是這件事。

跑法（在專案根目錄）：
    python examples/ch02_connectivity/ex02_isoperimetric.py
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import Board, neighbors   # noqa: E402

N = 13          # 用 13 路盤，才放得下比較大的中央區域


def boundary(region, n=N):
    """|∂R| = |N(R) \\ R|：圍住 region 需要幾顆子。"""
    R = set(region)
    return len({q for p in R for q in neighbors(p, n) if q not in R})


def rect(r0, c0, h, w):
    """左上角在 (r0, c0)、高 h 寬 w 的長方形，用內部座標。"""
    return [(r0 + i, c0 + j) for i in range(h) for j in range(w)]


def part1_rectangles():
    print("=" * 76)
    print("1. 長方形：整數最佳解 vs AM-GM 給的連續下界")
    print("=" * 76)
    print(f"{'面積':>4} | {'角':>12} | {'邊':>12} | {'中央':>12}")
    print(f"{'':>4} | {'實際 公式':>12} | {'實際 公式':>12} | {'實際 公式':>12}")
    print("-" * 76)

    for A in [4, 6, 8, 9, 12, 16, 20, 24, 25, 36]:
        best = {}
        for h in range(1, N - 2):
            if A % h:
                continue
            w = A // h
            if w > N - 2:
                continue
            # 角：貼左上兩邊
            best["角"] = min(best.get("角", 99), boundary(rect(0, 0, h, w)))
            # 邊：貼上邊，左右都留空
            if 1 + w <= N - 1:
                best["邊"] = min(best.get("邊", 99), boundary(rect(0, 1, h, w)))
            # 中央：四面懸空
            if 1 + h <= N - 1 and 1 + w <= N - 1:
                best["中"] = min(best.get("中", 99), boundary(rect(1, 1, h, w)))

        f_corner = 2 * math.sqrt(A)
        f_edge = 2 * math.sqrt(2 * A)
        f_centre = 4 * math.sqrt(A)
        print(f"{A:>4} | {best['角']:>5} {f_corner:>6.2f} |"
              f" {best['邊']:>5} {f_edge:>6.2f} |"
              f" {best['中']:>5} {f_centre:>6.2f}")

        # 連續下界不可能被整數解突破
        assert best["角"] >= f_corner - 1e-9
        assert best["邊"] >= f_edge - 1e-9
        assert best["中"] >= f_centre - 1e-9

    print()
    print("  公式永遠是下界，整數解永遠 >= 它。當最佳的 a、b 剛好是整數時（例如 A 為完全")
    print("  平方數的角落與中央），兩者完全相等 —— 這就是 A = 16 時 8 和 16 的來源。")

    # 章節裡明講的三個數字
    assert boundary(rect(0, 0, 4, 4)) == 8         # 角 16 目要 8 子
    assert boundary(rect(0, 1, 4, 4)) == 12        # 邊 16 目要 12 子
    assert boundary(rect(1, 1, 4, 4)) == 16        # 中央 16 目要 16 子


def connected_regions(cells, size):
    """列舉 cells 這個範圍內、大小為 size 的所有連通區域（去重）。"""
    cells = set(cells)
    seen = set()
    frontier = {frozenset([c]) for c in cells}
    for _ in range(size - 1):
        nxt = set()
        for R in frontier:
            for p in R:
                for q in neighbors(p, N):
                    if q in cells and q not in R:
                        nxt.add(R | {q})
        frontier = nxt
    seen |= frontier
    return seen


def part2_shapes():
    """§4.5.1：長方形不是最省的形狀。"""
    print()
    print("=" * 76)
    print("2. 不限長方形：窮舉所有連通區域（§4.5.1）")
    print("=" * 76)
    print("  定理 2.10 只在長方形之間比較。放寬到所有形狀，結果會變成怎樣？\n")

    cells = [(r, c) for r in range(3, 10) for c in range(3, 10)]
    print(f"{'面積':>4} | {'所有形狀':>8} | {'最好的長方形':>12} | {'差':>3} | 最省的形狀")
    print("-" * 76)
    beat = 0
    for A in range(1, 8):
        regions = connected_regions(cells, A)
        best = min(boundary(R) for R in regions)
        best_R = min(regions, key=boundary)
        rect_best = min(
            (boundary(rect(5, 5, h, A // h)) for h in range(1, A + 1) if A % h == 0),
            default=99,
        )
        if best < rect_best:
            beat += 1
        r0 = min(p[0] for p in best_R)
        c0 = min(p[1] for p in best_R)
        norm = sorted((p[0] - r0, p[1] - c0) for p in best_R)
        print(f"{A:>4} | {best:>8} | {rect_best:>12} | {rect_best-best:>3} | {norm}")

    print()
    print(f"  在面積 1 到 7 之間，有 {beat} 個面積是「非長方形比任何長方形都省」。")
    print("  最極端的是面積 5：十字形只要 8 顆子，而唯一的長方形 1x5 要 12 顆。")
    print()
    print("  為什麼？因為定理 2.5 的三項分解對空地一樣成立：")
    print("      |∂R| = Σdeg(r) - 2·e(R) - 重複的邊界點")
    print("  十字形有四個凸角，每個凸角外面的點都被兩格同時貼著，第三項是 4：")
    print("      5*4 - 2*4 - 4 = 8")
    print("  同一個「重複」，長在你的棋子上是愚形（少一口氣），")
    print("  長在你要圍的空地邊界上卻是節省（少一顆子）。符號相反。")

    # §4.5.1 明講的兩個數字
    cross = [(5, 6), (6, 5), (6, 6), (6, 7), (7, 6)]
    assert boundary(cross) == 8
    assert boundary(rect(5, 5, 1, 5)) == 12


def part2b_ratio():
    """定理 2.11：比值 1 : √2 : 2 不依賴形狀。"""
    print()
    print("=" * 76)
    print("2b. 定理 2.11：常數會變，比值不會")
    print("=" * 76)
    print("  對角、邊、中央三種位置，各自窮舉所有形狀求最小邊界，然後看比值。\n")

    corner = [(r, c) for r in range(0, 7) for c in range(0, 7)]
    edge = [(r, c) for r in range(0, 7) for c in range(4, 11)]
    centre = [(r, c) for r in range(4, 11) for c in range(4, 11)]

    def best_at(cells, A, anchor):
        rs = [R for R in connected_regions(cells, A) if anchor in R]
        return min(boundary(R) for R in rs)

    print(f"{'A':>3} | {'角':>4} {'邊':>4} {'中':>4} | {'中÷角':>6} {'邊÷角':>6} | 理論 2.00 / 1.41")
    print("-" * 76)
    ratios = []
    for A in range(4, 10):
        c = best_at(corner, A, (0, 0))
        e = best_at(edge, A, (0, 7))
        m = best_at(centre, A, (7, 7))
        ratios.append(m / c)
        print(f"{A:>3} | {c:>4} {e:>4} {m:>4} | {m/c:>6.2f} {e/c:>6.2f} |")

    avg = sum(ratios) / len(ratios)
    print(f"\n  中÷角 的平均：{avg:.2f}（理論值 2）")
    print("  絕對值全面低於定理 2.10 的長方形公式，但比值穩穩地停在 2 附近 ——")
    print("  這正是反射論證預測的：常數 k 在相除時被約掉了。")
    assert 1.9 <= avg <= 2.3


def part3_inverse():
    print()
    print("=" * 76)
    print("3. 反過來看：給定 L 顆棋子，最多能圍幾目？")
    print("=" * 76)
    print(f"{'棋子數 L':>8} | {'角 (L/2)²':>10} | {'邊 L²/8':>9} | {'中 (L/4)²':>10} | 角是中的幾倍")
    print("-" * 76)
    for L in [4, 8, 12, 16, 20]:
        a_corner = (L / 2) ** 2
        a_edge = L ** 2 / 8
        a_centre = (L / 4) ** 2
        print(f"{L:>8} | {a_corner:>10.1f} | {a_edge:>9.1f} | {a_centre:>10.1f} |"
              f" {a_corner / a_centre:>6.0f} 倍")
        assert abs(a_corner / a_centre - 4.0) < 1e-9

    print()
    print("  比值永遠是 4，不是 2。因為 2 是【邊界長度】的比，而面積與邊界是平方關係：")
    print("  邊界省一半，面積就變四倍。")
    print()
    print("  實戰翻譯：開局在中央下的一手，若【只】用來圍地，價值大約是同一手下在")
    print("  空角的四分之一。中央的價值不在地，在影響力 —— 那是第 9 章的事。")


if __name__ == "__main__":
    Board(N)          # 確認 N 路盤是支援的大小
    part1_rectangles()
    part2_shapes()
    part2b_ratio()
    part3_inverse()
    print()
    print("全部斷言通過。")
