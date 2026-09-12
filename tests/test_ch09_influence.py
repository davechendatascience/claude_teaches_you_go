"""第 9 章的計算核心：影響力場，以及它可以被證明的兩個極限。

這一章是全書唯一標 🟡 的一層 —— 模型本身沒有定理。所以這裡的測試分成兩類：

  * **模型的性質**（可加性、衰減、對稱）—— 這些是程式碼正確性的測試。
  * **模型的極限**（命題 9.4、定理 9.5）—— 這兩個【是】定理，逐一驗證。

跑法：  python -m pytest tests/ -q      或   python tests/test_ch09_influence.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np                                                   # noqa: E402

from go_core import BLACK, EMPTY, WHITE, Board                       # noqa: E402
from go_core.influence import (bouzy_field, dilate, discontinuity_witness,  # noqa: E402
                               distance_map, erode, field_ownership,
                               final_ownership, marginal_moyo, moyo,
                               moyo_area, playout, render_field,
                               zobrist_field)

COLS = "ABCDEFGHJKLMNOPQRST"


# ------------------------------------------------------- 距離與場的定義

def test_distance_map_is_manhattan():
    D = distance_map(5)
    assert D.shape == (25, 25)
    assert D[0, 0] == 0
    assert D[0, 1] == 1                      # (0,0) 到 (0,1)
    assert D[0, 24] == 8                     # (0,0) 到 (4,4)
    assert (D == D.T).all()                  # 對稱


def test_zobrist_matches_the_definition():
    """I(v) = sum_s sigma(s) lam^d(s,v)，逐點對定義核對。"""
    b = Board(9)
    b.place_many(BLACK, ["D4", "D5"])
    b.place(WHITE, "F6")
    lam = 0.5
    f = zobrist_field(b, lam)
    stones = [(b._pt("D4"), 1), (b._pt("D5"), 1), (b._pt("F6"), -1)]
    for p in b.points():
        want = sum(sig * lam ** (abs(s[0] - p[0]) + abs(s[1] - p[1]))
                   for s, sig in stones)
        assert abs(float(f[p]) - want) < 1e-12, p


def test_exercise_9_1_exact_values():
    """練習 9.1 的三個分數：1/8、5/16、-13/256。"""
    b = Board(9)
    b.place_many(BLACK, ["D4", "D5"])
    b.place(WHITE, "F6")
    f = zobrist_field(b, 0.5)
    want = {"C7": 1 / 8, "E3": 5 / 16, "H8": -13 / 256}
    for coord in want:
        assert abs(float(f[b._pt(coord)]) - want[coord]) < 1e-12, coord
    order = sorted(want, key=lambda k: -want[k])
    assert order == ["E3", "C7", "H8"]


def test_field_is_additive():
    """可加性：多下一顆子就是多加一項。這是這個模型唯一真正的優點。"""
    b1 = Board(9)
    b1.place(BLACK, "C3")
    b2 = Board(9)
    b2.place(WHITE, "G7")
    both = Board(9)
    both.place(BLACK, "C3")
    both.place(WHITE, "G7")
    assert np.allclose(zobrist_field(both, 0.7),
                       zobrist_field(b1, 0.7) + zobrist_field(b2, 0.7))


def test_field_ignores_shape():
    """場看不見形狀：只要位置一樣，連著或分開都一樣。"""
    a = Board(9)
    a.place_many(BLACK, ["D4", "D5"])
    assert np.allclose(zobrist_field(a, 0.7), zobrist_field(a.copy(), 0.7))
    # 兩顆子換成隔開的位置，場當然不同 —— 但同一組位置永遠給同一個場
    c = Board(9)
    c.place_many(BLACK, ["D5", "D4"])        # 順序顛倒
    assert np.allclose(zobrist_field(a, 0.7), zobrist_field(c, 0.7))


def test_zobrist_rejects_bad_lambda():
    b = Board(9)
    b.place(BLACK, "D4")
    for bad in [0.0, 1.0, -0.5, 1.5]:
        try:
            zobrist_field(b, bad)
        except ValueError:
            continue
        raise AssertionError(f"lam={bad} 應該被拒絕")


def test_empty_board_has_zero_field():
    assert not zobrist_field(Board(9), 0.6).any()
    assert not bouzy_field(Board(9), 3).any()


# ------------------------------------------------------- 膨脹／侵蝕

def test_dilate_erode_are_symmetric_in_the_centre():
    """中央的一顆子，膨脹侵蝕之後必須保持八重對稱。"""
    f = np.zeros((9, 9))
    f[4, 4] = 1.0
    for _ in range(4):
        f = dilate(f)
    for _ in range(12):
        f = erode(f)
    assert np.allclose(f, f.T)               # 轉置對稱
    assert np.allclose(f, f[::-1, :])        # 上下對稱
    assert np.allclose(f, f[:, ::-1])        # 左右對稱


def test_dilate_is_blocked_by_the_opponent():
    """膨脹遇到反號的鄰居就停 —— 這是 Bouzy 和 Zobrist 最大的差別。"""
    f = np.zeros((5, 5))
    f[2, 1] = 1.0
    f[2, 3] = -1.0
    g = dilate(f)
    assert g[2, 2] == 0.0                    # 夾在中間，一正一負相消


def test_bouzy_is_local_zobrist_is_not():
    """同一道牆：Bouzy 只承認附近幾條線，Zobrist 滲到全盤。"""
    b = Board(13)
    b.place_many(BLACK, [f"D{r}" for r in range(4, 11)])
    z = zobrist_field(b, 0.8)
    bz = bouzy_field(b, 4)
    far = b._pt("N7")                        # 離牆九路
    assert z[far] > 0.5                      # Zobrist 說那裡偏黑
    assert bz[far] == 0.0                    # Bouzy 沉默


def test_offboard_convention_changes_the_answer():
    """盤外算不算敵，是一個有後果的選擇（erode 的 docstring 說過）。"""
    b = Board(9)
    b.place(BLACK, "C3")
    keep = bouzy_field(b, 4, count_offboard=False)
    strict = bouzy_field(b, 4, count_offboard=True)
    assert (keep != 0).sum() > (strict != 0).sum()


# ------------------------------------------------------- 模樣與門檻

def test_moyo_shrinks_as_theta_grows():
    """門檻越高，模樣越小 —— 單調性。"""
    b = Board(13)
    b.place_many(BLACK, [f"D{r}" for r in range(4, 11)])
    f = zobrist_field(b, 0.8)
    areas = [moyo_area(b, f, t, BLACK) for t in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]]
    assert all(x >= y for x, y in zip(areas, areas[1:])), areas
    assert areas[0] > areas[-1]


def test_exercise_9_2_moyo_interval():
    """練習 9.2：|M(2.0)| = 52、|M(1.0)| = 93。區間寬度才是資訊。"""
    b = Board(13)
    b.place_many(BLACK, [f"D{r}" for r in range(4, 11)] + ["G10"])
    b.place_many(WHITE, ["K4", "K10"])
    f = zobrist_field(b, 0.8)
    assert moyo_area(b, f, 2.0, BLACK) == 52
    assert moyo_area(b, f, 1.0, BLACK) == 93


def test_moyo_only_counts_empty_points():
    b = Board(9)
    b.place_many(BLACK, ["D4", "D5"])
    f = zobrist_field(b, 0.8)
    region = moyo(f, 0.0, BLACK)
    assert b._pt("D4") in region                          # 棋子本身在勢力圈裡
    assert b._pt("D4") not in [p for p in region
                               if b.grid[p] == EMPTY]     # 但不算進面積
    assert moyo_area(b, f, 0.0, BLACK) == sum(
        1 for p in region if b.grid[p] == EMPTY)


def test_field_ownership_is_three_valued():
    b = Board(9)
    b.place(BLACK, "C3")
    b.place(WHITE, "G7")
    own = field_ownership(zobrist_field(b, 0.8), 0.0)
    assert set(np.unique(own)) <= {EMPTY, BLACK, WHITE}
    assert own[b._pt("C3")] == BLACK
    assert own[b._pt("G7")] == WHITE
    assert own[b._pt("E5")] == EMPTY          # 天元在零線上，場說「不知道」


# ------------------------------------------------------- 厚勢不圍空

def test_thickness_does_not_enclose_territory():
    """§4.4：牆背後多下一手幾乎沒有價值，牆前方差二十幾倍。"""
    b = Board(13)
    b.place_many(BLACK, [f"D{r}" for r in range(4, 11)])
    wall_col = b._pt("D7")[1]
    behind, front = [], []
    for p in b.points():
        if b.grid[p] != EMPTY:
            continue
        v = marginal_moyo(b, BLACK, p, theta=1.0, lam=0.8)
        if p[1] < wall_col:
            behind.append(v)
        elif p[1] > wall_col + 2:
            front.append(v)
    assert max(behind) <= 3                    # 牆背後最多多 3 點
    assert np.mean(front) > 10 * np.mean(behind)


# ------------------------------------------------------- 命題 9.4

def test_proposition_9_4_centre_preference():
    """場永遠偏好中央：42 組 (n, lambda)，最大值在天元且往中央單調遞增。"""
    combos = 0
    for n in [5, 7, 9, 11, 13, 19]:
        D = distance_map(n)
        for lam in [0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]:
            t = (lam ** D).sum(axis=1).reshape(n, n)
            c = n // 2
            combos += 1
            assert np.isclose(t.max(), t[c, c]), (n, lam)
            for r in range(n):
                row = t[r]
                assert all(row[i] <= row[i + 1] + 1e-12 for i in range(c)), (n, lam, r)
                assert all(row[i] >= row[i + 1] - 1e-12
                           for i in range(c, n - 1)), (n, lam, r)
    assert combos == 42


def test_centre_is_2_6_times_the_corner_on_19():
    T = (0.8 ** distance_map(19)).sum(axis=1).reshape(19, 19)
    assert abs(T[9, 9] - 62.83) < 0.01
    assert abs(T[0, 0] - 24.28) < 0.01
    assert abs(T[9, 9] / T[0, 0] - 2.59) < 0.01


def test_field_prefers_higher_lines_monotonically():
    """三線到天元，模樣面積單調遞增 —— 場說「越高越好」。"""
    areas = []
    for line in range(3, 8):
        b = Board(13)
        b.place_many(BLACK, [f"{COLS[line - 1]}{r}" for r in range(4, 11)])
        areas.append(moyo_area(b, zobrist_field(b, 0.8), 1.0, BLACK))
    assert areas == [101, 114, 125, 134, 138]
    assert all(x <= y for x, y in zip(areas, areas[1:]))


def test_normalising_shrinks_but_does_not_reverse_the_bias():
    """練習 9.4：想得到的修法有效果，但沒有翻轉。"""
    for n in [9, 13, 19]:
        W = 0.8 ** distance_map(n)
        tot = W.sum(axis=1)
        score = (W @ (1.0 / tot)).reshape(n, n)
        t = tot.reshape(n, n)
        c = n // 2
        before, after = t[c, c] / t[0, 0], score[c, c] / score[0, 0]
        assert after < before, n              # 縮小了
        assert after > 1.0, n                 # 但中央還是贏
        assert not np.isclose(score.max(), score[0, 0]), n


# ------------------------------------------------------- 定理 9.5

def test_theorem_9_5_discontinuity():
    """場只變 lambda^15，死活完全翻轉。"""
    w = discontinuity_witness(lam=0.6)
    assert w["distance"] == 15
    assert w["ladder_length"] == 35
    assert abs(w["field_change"] - 0.6 ** 15) < 1e-15
    assert w["captured_before"] is True
    assert w["captured_after"] is False


def test_theorem_9_5_holds_for_every_lambda():
    """lambda 越小場的變化越小，死活的翻轉一模一樣。"""
    changes = []
    for lam in [0.9, 0.7, 0.5, 0.3]:
        w = discontinuity_witness(lam=lam)
        assert abs(w["field_change"] - lam ** 15) < 1e-15, lam
        assert w["captured_before"] and not w["captured_after"], lam
        changes.append(w["field_change"])
    assert all(x > y for x, y in zip(changes, changes[1:]))   # 遞減
    assert changes[-1] < changes[0] / 1e6


def test_no_threshold_can_separate_both_positions():
    """能判對兩個盤面的門檻區間，寬度恰好是 lambda^15 —— 而且會趨近 0。"""
    for lam in [0.8, 0.6, 0.4]:
        w = discontinuity_witness(lam=lam)
        lo = -w["field_after"]        # 要判「活」需要 theta >= 這個
        hi = -w["field_before"]       # 要判「死」需要 theta < 這個
        assert lo < hi
        assert abs((hi - lo) - lam ** 15) < 1e-15


# ------------------------------------------------------- 隨機下完（量測工具）

def test_playout_terminates_and_fills_the_board():
    rng = random.Random(11)
    b = Board(9)
    done = playout(b, BLACK, rng)
    empties = sum(1 for p in done.points() if done.grid[p] == EMPTY)
    assert empties < 81 * 0.5           # 隨機下完之後大部分點有子


def test_playout_does_not_fill_its_own_eyes():
    """如果會填自己的眼，量測就沒有意義了（第 3 章的工具在這裡把關）。"""
    rng = random.Random(5)
    b = Board(9)
    # 黑在角上做兩個眼
    b.place_many(BLACK, ["A3", "B3", "C3", "C2", "C1"])
    done = playout(b, WHITE, rng, max_moves=200)
    # 那塊黑棋不該在隨機對局裡自己死掉
    assert done.grid[done._pt("A3")] == BLACK
    assert done.grid[done._pt("C1")] == BLACK


def test_final_ownership_assigns_enclosed_regions():
    b = Board(5)
    # 黑把左下角完全圍起來
    b.place_many(BLACK, ["A3", "B3", "C3", "C2", "C1"])
    own = final_ownership(b)
    for coord in ["A1", "A2", "B1", "B2"]:
        assert own[b._pt(coord)] == BLACK, coord
    # 剩下那一大片只碰到黑，所以【也是黑的】—— 日本規則就是這樣數
    assert own[b._pt("E5")] == BLACK

    # 放一顆白子進去，那一片就變成雙方都碰得到的無主地
    b.place(WHITE, "E5")
    own2 = final_ownership(b)
    assert own2[b._pt("E5")] == WHITE          # 有子的點屬於那顆子
    assert own2[b._pt("D4")] == EMPTY          # 兩邊都碰到 -> 無主
    for coord in ["A1", "A2", "B1", "B2"]:     # 黑的角還是黑的
        assert own2[b._pt(coord)] == BLACK, coord


def test_render_field_units():
    b = Board(9)
    b.place(BLACK, "C3")
    b.place(WHITE, "G7")
    f = zobrist_field(b, 0.8)
    text = render_field(f, b, unit=0.1)
    lines = text.splitlines()
    assert len(lines) == 9
    assert all(len(ln.split(" ")) == 9 for ln in lines)
    assert "X" in text and "O" in text
    # 天元在零線上 -> 印成 '.'
    assert lines[4].split(" ")[4] == "."


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
