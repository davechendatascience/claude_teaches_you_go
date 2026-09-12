#!/usr/bin/env python
"""第 9 章配套範例 2：影響力場的兩個極限。

對應章節：第 9 章 §4.5（命題 9.4）、§4.6（定理 9.5）。

第 4 層是全書唯一標 🟡 的一層 —— 它沒有定理。這支腳本示範的是這一層
**唯二的兩個定理**，而它們講的都是這一層算不出什麼。

1. 命題 9.4：場永遠偏好中央。
   對任何盤面大小、任何 lambda 都成立（本檔逐點窮舉驗證）。
   後果：場說不出第 2 章證明過的「金角銀邊」。

2. 定理 9.5：場算不出死活。
   用第 8 章的征子當見證：15 路外的一顆子讓場只變 lambda^15，
   卻讓一塊棋從死變活。

跑法（在專案根目錄）：
    python examples/ch09_influence/ex02_limits.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np                                                   # noqa: E402

from go_core import BLACK, WHITE, Board                              # noqa: E402
from go_core.influence import (discontinuity_witness, distance_map,   # noqa: E402
                               moyo_area, zobrist_field)

SIZES = [5, 7, 9, 11, 13, 19]
LAMBDAS = [0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
COLS = "ABCDEFGHJKLMNOPQRST"


def stone_total(n, lam):
    """T(s) = 一顆放在 s 的子，對全盤的場總和。"""
    return (lam ** distance_map(n)).sum(axis=1).reshape(n, n)


def check_centre_preference():
    """命題 9.4：最大值在天元，且沿每一行往中央單調遞增。"""
    violations = combos = 0
    for n in SIZES:
        for lam in LAMBDAS:
            t = stone_total(n, lam)
            c = n // 2
            combos += 1
            if not np.isclose(t.max(), t[c, c]):
                violations += 1
                print(f"    反例：n={n} lam={lam} 最大值不在天元")
            for r in range(n):
                row = t[r]
                if any(row[i] > row[i + 1] + 1e-12 for i in range(c)):
                    violations += 1
                if any(row[i] < row[i + 1] - 1e-12 for i in range(c, n - 1)):
                    violations += 1
    return combos, violations


def main():
    # ---------------------------------------------- 命題 9.4
    print("=" * 66)
    print("命題 9.4：場永遠偏好中央")
    print("=" * 66)
    combos, violations = check_centre_preference()
    print(f"  {combos} 組 (盤面大小, lambda)，逐點檢查最大值位置與單調性")
    print(f"  反例：{violations} 個")
    assert violations == 0

    T = stone_total(19, 0.8)
    print("\n  19 路盤、lambda=0.8，一顆子的場總和：")
    for name, pt in [("天元", (9, 9)), ("星（四線）", (3, 3)), ("三三", (2, 2)),
                     ("邊（一線中點）", (0, 9)), ("角（一一）", (0, 0))]:
        print(f"    {name:<16}{T[pt]:>8.2f}")
    print(f"    天元 / 角 = {T[9, 9] / T[0, 0]:.2f} 倍")
    assert T[9, 9] == T.max()

    print("\n  對照第 2 章定理 2.11：角 : 邊 : 中 = 1 : sqrt(2) : 2（圍地的成本）")
    print("  場說中央值 2.6 個角落；定理 2.11 說中央要花兩倍的成本。")
    print("  兩者【方向相反】—— 因為場量的是「附近有幾個點」，")
    print("  而定理 2.11 量的是「你不必自己蓋的那段牆」。")

    # 三線 vs 四線 vs 五線：場的分數單調遞增到天元
    print("\n  七子牆放在不同線上（13 路），場給的分數：")
    print(f"    {'線':>4}{'確定地 I>2':>12}{'模樣 I>1':>11}{'影響 I>0.3':>12}")
    moyos = []
    for line in range(3, 8):
        b = Board(13)
        b.place_many(BLACK, [f"{COLS[line - 1]}{r}" for r in range(4, 11)])
        f = zobrist_field(b, 0.8)
        a2, a1, a03 = (moyo_area(b, f, 2.0), moyo_area(b, f, 1.0),
                       moyo_area(b, f, 0.3))
        moyos.append(a1)
        print(f"    {line:>4}{a2:>12}{a1:>11}{a03:>12}")
    assert all(x <= y for x, y in zip(moyos, moyos[1:]))
    print(f"    模樣面積一路遞增到天元（{moyos[0]} -> {moyos[-1]}，"
          f"+{100 * (moyos[-1] / moyos[0] - 1):.0f}%）")

    # 正規化能不能救？
    print("\n  用「附近有幾個點」正規化，能修掉中央偏好嗎？")
    print(f"    {'盤面':>6}{'原本 中/角':>13}{'正規化後 中/角':>17}")
    for n in [9, 13, 19]:
        W = 0.8 ** distance_map(n)
        tot = W.sum(axis=1)
        score = (W @ (1.0 / tot)).reshape(n, n)
        t = tot.reshape(n, n)
        c = n // 2
        before, after = t[c, c] / t[0, 0], score[c, c] / score[0, 0]
        print(f"    {n:>6}{before:>13.2f}{after:>17.2f}")
        assert after < before      # 縮小了
        assert after > 1.0         # 但沒有翻轉
    print("    縮小了，但中央還是贏。金角銀邊講的是周長，不是鄰居數。")

    # ---------------------------------------------- 定理 9.5
    print("\n" + "=" * 66)
    print("定理 9.5：場算不出死活")
    print("=" * 66)
    w = discontinuity_witness(lam=0.6)
    print(f"  見證：第 8 章的征子（13 路，白征子成立，{w['ladder_length']} 手）")
    print(f"  引徵點 N4 距離目標 D10  {w['distance']} 路")
    print(f"  I(D10) 放子前            {w['field_before']:+.8f}")
    print(f"  I(D10) 放子後            {w['field_after']:+.8f}")
    print(f"  場的變化                 {w['field_change']:.8f}")
    print(f"  理論值 lambda^{w['distance']}          {w['bound']:.8f}")
    print(f"  黑 D10 被提掉（放子前）   {w['captured_before']}")
    print(f"  黑 D10 被提掉（放子後）   {w['captured_after']}")
    assert w["distance"] == 15
    assert abs(w["field_change"] - w["bound"]) < 1e-15
    assert w["captured_before"] and not w["captured_after"]

    print("\n  換不同的 lambda：場的變化可以任意小，死活的翻轉一模一樣")
    print(f"    {'lambda':>8}{'場的變化':>16}{'死活':>16}")
    changes = []
    for lam in [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]:
        ww = discontinuity_witness(lam=lam)
        changes.append(ww["field_change"])
        assert ww["captured_before"] and not ww["captured_after"]
        assert abs(ww["field_change"] - lam ** 15) < 1e-15
        print(f"    {lam:>8}{ww['field_change']:>16.3e}{'死 -> 活':>14}")
    assert changes[-1] < changes[0] / 1000

    print("\n  沒有任何固定的門檻能同時判對這兩個盤面 —— 而且區間寬度")
    print("  隨征子加長以 lambda^d 趨近 0。這就是定理 9.5。")
    print("\n  場對遠處的擾動是連續的；死活不是。")


if __name__ == "__main__":
    main()
