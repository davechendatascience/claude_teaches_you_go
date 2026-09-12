"""第 10 章的計算核心：值函數、完全解、MCTS、勝率。

跑法：  python -m pytest tests/ -q      或   python tests/test_ch10_value.py
"""

import random
import sys
from collections import deque
from pathlib import Path

sys.setrecursionlimit(100000)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np                                                   # noqa: E402

from go_core import BLACK, EMPTY, WHITE, Board, format_coord, opposite  # noqa: E402
from go_core.ladder import ladder_capture                            # noqa: E402
from go_core.mcts import rollout, search                             # noqa: E402
from go_core.minimax import (Solver, area_score, expected_win_rate,   # noqa: E402
                             final_value, legal_moves, move_values,
                             solve, variance_preference, win_rate)

MAX_PLY = 15


# ------------------------------------------------------------ 記分

def test_area_score_counts_stones_and_enclosed_space():
    b = Board(5)
    b.place_many(BLACK, ["A3", "B3", "C3", "C2", "C1"])
    bl, wh = area_score(b)
    # 5 顆子 + 圍住的 A1,A2,B1,B2 = 9；其餘只碰到黑，所以也算黑的
    assert bl == 25 and wh == 0


def test_area_score_neutral_region():
    b = Board(5)
    b.place_many(BLACK, ["A3", "B3", "C3", "C2", "C1"])
    b.place(WHITE, "E5")
    bl, wh = area_score(b)
    assert bl == 9                     # 左下角那 4 點 + 5 顆黑子
    assert wh == 1                     # 白只有那顆子
    assert bl + wh < 25                # 中間那一大片是單官，不算給任何人


def test_final_value_subtracts_komi():
    b = Board(3)
    b.place_many(BLACK, ["A1", "B1", "C1", "A2", "B2", "C2", "A3", "B3", "C3"])
    assert final_value(b, komi=0.0) == 9
    assert final_value(b, komi=7.5) == 1.5


# ------------------------------------------------------------ 著手

def test_legal_moves_excludes_suicide():
    b = Board(3)
    b.place_many(WHITE, ["A2", "B1"])
    pts = [format_coord(p, 3) for p, _, _ in legal_moves(b, BLACK)]
    assert "A1" not in pts             # 黑下 A1 是自殺


def test_legal_moves_marks_the_ko_point():
    """提掉單子、自己也是單子一口氣 -> 產生劫點。"""
    b = Board(5)
    b.place_many(BLACK, ["B3", "A2", "B1"])
    b.place_many(WHITE, ["C3", "D2", "C1", "B2"])
    kos = {format_coord(p, 5): nk for p, _, nk in legal_moves(b, BLACK)}
    assert kos.get("C2") is not None
    assert format_coord(kos["C2"], 5) == "B2"


# ------------------------------------- §4.1 2 路盤：V 不存在

def test_2x2_never_converges_period_six():
    """只有基本劫規時，2 路盤的 V 以週期 6 震盪。"""
    vals = []
    for ply in range(4, 27, 2):
        s = Solver(komi=0.0, max_ply=ply)
        v, _ = s.search(Board(2), BLACK)
        vals.append(int(v))
    assert vals == [-1, 0, 0] * 4


def test_2x2_shortest_pure_move_cycle_is_six():
    """震盪的週期 = 狀態圖裡最短純落子環的長度 = 6（第 5 章規則 5.4）。"""
    n = 2
    sig = lambda b, c, ko: (b.grid.tobytes(), c, ko)
    start = (Board(n), BLACK, None)
    edges, nodes = {}, {sig(*start)}
    Q = deque([start])
    while Q:
        b, c, ko = Q.popleft()
        k = sig(b, c, ko)
        edges[k] = []
        for p, child, nk in legal_moves(b, c, ko):
            s2 = sig(child, opposite(c), nk)
            edges[k].append((p, s2))
            if s2 not in nodes:
                nodes.add(s2)
                Q.append((child, opposite(c), nk))
        s2 = sig(b, opposite(c), None)
        edges[k].append((None, s2))
        if s2 not in nodes:
            nodes.add(s2)
            Q.append((b, opposite(c), None))

    shortest = None
    for src in nodes:
        dist = {src: 0}
        Q2 = deque([src])
        while Q2:
            u = Q2.popleft()
            for mv, v in edges.get(u, []):
                if mv is None:
                    continue
                if v == src:
                    d = dist[u] + 1
                    if shortest is None or d < shortest:
                        shortest = d
                    continue
                if v not in dist:
                    dist[v] = dist[u] + 1
                    Q2.append(v)
        if shortest == 6:
            break
    assert shortest == 6


# ------------------------------------- §4.2 3 路盤：完全解

def test_3x3_value_is_nine():
    for ply in [13, 15, 19]:
        s = Solver(komi=0.0, max_ply=ply)
        v, mv = s.search(Board(3), BLACK)
        assert v == 9, ply
        assert format_coord(mv, 3) == "B2", ply       # 天元


def test_3x3_converges_after_ply_13():
    vals = []
    for ply in [9, 11, 13, 15, 19]:
        s = Solver(komi=0.0, max_ply=ply)
        v, _ = s.search(Board(3), BLACK)
        vals.append(int(v))
    assert vals == [6, 6, 9, 9, 9]


def test_3x3_delta_v_by_symmetry_class():
    """天元 0、邊 -5、角 -18，而且【角 = 虛手】。"""
    vals = dict(move_values(Board(3), BLACK, komi=0.0, max_ply=MAX_PLY))
    best = max(vals.values())
    assert best == 9
    assert best - vals[(1, 1)] == 0
    for p in [(0, 1), (1, 0), (1, 2), (2, 1)]:
        assert best - vals[p] == 5, p
    for p in [(0, 0), (0, 2), (2, 0), (2, 2)]:
        assert best - vals[p] == 18, p
    assert best - vals[None] == 18


def test_fair_komi_is_the_value_of_the_empty_board():
    v, _ = solve(Board(3), BLACK, komi=0.0, max_ply=MAX_PLY)
    v_fair, _ = solve(Board(3), BLACK, komi=v, max_ply=MAX_PLY)
    assert v == 9
    assert v_fair == 0                     # 貼掉 V(空盤) 之後正好持平


def test_3x3_optimal_game_takes_the_whole_board():
    s = Solver(komi=0.0, max_ply=MAX_PLY)
    b, colour, ko, passes, ply, moves = Board(3), BLACK, None, 0, 0, 0
    while ply < MAX_PLY and passes < 2:
        _, mv = s.search(b, colour, passes=passes, ko=ko, ply=ply)
        if mv is None:
            passes += 1
            ko = None
        else:
            for p, child, nk in legal_moves(b, colour, ko):
                if p == mv:
                    b, ko = child, nk
                    break
            passes = 0
        colour = opposite(colour)
        ply += 1
        moves += 1
    assert area_score(b) == (9, 0)
    assert moves == 15


# ------------------------------------- §4.3 搜尋的代價

def test_alpha_beta_gives_the_same_answer_much_cheaper():
    counts = {}
    for ab in [False, True]:
        s = Solver(komi=0.0, max_ply=15, use_alphabeta=ab)
        v, _ = s.search(Board(3), BLACK)
        assert v == 9
        counts[ab] = s.nodes
    assert counts[True] == 9591
    assert counts[False] == 556948
    assert counts[False] / counts[True] > 50


def test_transposition_table_is_sound_with_flags():
    """置換表存的是界限時必須標旗標，否則答案會安靜地變錯。"""
    a = Solver(komi=0.0, max_ply=13, use_memo=True, use_alphabeta=True)
    b = Solver(komi=0.0, max_ply=13, use_memo=False, use_alphabeta=True)
    va, _ = a.search(Board(3), BLACK)
    vb, _ = b.search(Board(3), BLACK)
    assert va == vb == 9
    assert a.nodes < b.nodes


# ------------------------------------- §4.4 MCTS

def test_mcts_finds_tengen_quickly():
    for sims in [50, 200, 800]:
        _, stats = search(Board(3), BLACK, simulations=sims, c=1.4,
                          rng=random.Random(7))
        assert format_coord(stats[0][0], 3) == "B2", sims


def test_mcts_ranking_matches_the_exact_solution():
    exact = dict(move_values(Board(3), BLACK, komi=0.0, max_ply=MAX_PLY))
    _, stats = search(Board(3), BLACK, simulations=1600, c=1.4,
                      rng=random.Random(7))
    order = [p for p, _, _ in stats if p is not None]
    assert exact[order[0]] == max(exact.values())      # 第一名正確
    # 天元 > 邊 > 角，訪問次數也照這個順序
    visits = {p: n for p, n, _ in stats if p is not None}
    assert visits[(1, 1)] > max(visits[p] for p in visits if p != (1, 1))


def test_mcts_value_estimate_is_badly_off():
    """排序先收斂，估值後收斂 —— 這就是價值網路存在的理由。"""
    root, _ = search(Board(3), BLACK, simulations=1600, c=1.4,
                     rng=random.Random(7))
    est = root.w / root.n
    true_scaled = 9 / 9.0
    assert 0 < est < true_scaled / 2                   # 差超過兩倍


def test_rollout_terminates_and_scores():
    rng = random.Random(3)
    v = rollout(Board(5), BLACK, None, 0, rng)
    assert -25 <= v <= 25


# ------------------------------------- §4.5 勝率與 Jensen

def test_win_rate_is_a_sigmoid():
    assert win_rate(0, 6) == 0.5
    assert win_rate(100, 6) > 0.99
    assert win_rate(-100, 6) < 0.01
    for v in [-10, -1, 0, 1, 10]:
        assert abs(float(win_rate(v, 6)) + float(win_rate(-v, 6)) - 1.0) < 1e-12


def test_one_point_is_worth_less_when_far_ahead():
    slope = lambda v: float(win_rate(v, 6)) * (1 - float(win_rate(v, 6))) / 6
    assert slope(0) > slope(5) > slope(10) > slope(20)
    assert slope(0) / slope(20) > 7


def test_jensen_steady_when_ahead_wild_when_behind():
    for mu in [5, 10, 20, 30]:
        _, _, diff = variance_preference(mu, 10, tau=6)
        assert diff > 0, mu                    # 凹 -> 求穩
    for mu in [-5, -10, -20, -30]:
        _, _, diff = variance_preference(mu, 10, tau=6)
        assert diff < 0, mu                    # 凸 -> 求亂
    _, _, diff = variance_preference(0, 10, tau=6)
    assert abs(diff) < 1e-12                   # 分界點


def test_direction_is_independent_of_tau():
    """練習 10.2：凹凸性只由 V 的正負決定，和 tau 無關。

    唯一的例外是浮點數飽和：tau 很小時 sigma(V/tau) 會被捨入成剛好 1.0
    （例如 tau=0.25, V=15 -> sigma(60)），三個值全都是 1.0，差自然是 0。
    那不是定理不成立，是 float64 沒有位數了 —— 所以這裡把飽和的情況
    單獨認出來，並確認它【真的】是飽和而不是方向反了。
    """
    saturated = 0
    for tau in [0.25, 0.5, 1, 2, 6, 12, 50, 200]:
        for mu in [-15, -3, 3, 15]:
            steady, wild, diff = variance_preference(mu, 2.0, tau=tau)
            if steady in (0.0, 1.0) and wild in (0.0, 1.0):
                assert diff == 0.0, (tau, mu)      # 飽和：三個值都貼到邊界
                saturated += 1
                continue
            assert (diff > 0) == (mu > 0), (tau, mu, diff)
    assert saturated > 0                            # 確實有飽和的例子
    assert saturated < 8                            # 但大部分沒有


def test_sigmoid_second_derivative_sign():
    x = np.linspace(-8, 8, 401)
    s = 1 / (1 + np.exp(-x))
    second = s * (1 - s) * (1 - 2 * s)
    assert (second[x < -0.05] > 0).all()
    assert (second[x > 0.05] < 0).all()


def test_giving_up_one_point_buys_win_rate():
    steady = expected_win_rate([19], tau=6)
    wild = expected_win_rate([10, 30], tau=6)
    assert steady > wild
    assert abs((steady - wild) - 0.0423) < 0.001


# ------------------------------------- §4.6 深度懸崖

def ladder_board(extra=None):
    b = Board(13)
    b.place(BLACK, "D10")
    b.place_many(WHITE, ["D11", "C10", "E11"])
    if extra:
        b.place(BLACK, extra)
    return b


def test_depth_cliff_at_34():
    for d in [5, 10, 20, 30, 33]:
        ok, _ = ladder_capture(ladder_board(), "D10", WHITE, max_depth=d)
        assert not ok, d                      # 讀不夠深 -> 答錯
    for d in [34, 40, 60]:
        ok, _ = ladder_capture(ladder_board(), "D10", WHITE, max_depth=d)
        assert ok, d                          # 讀夠了 -> 答對


def test_shallow_search_cannot_tell_the_two_positions_apart():
    """深度 33 以下的搜尋，和第 9 章那個被證明無能的場一樣瞎。"""
    for d in [5, 10, 20, 30, 33]:
        plain, _ = ladder_capture(ladder_board(), "D10", WHITE, max_depth=d)
        broken, _ = ladder_capture(ladder_board("N4"), "D10", WHITE, max_depth=d)
        assert plain == broken, d             # 分不出來
    for d in [34, 40]:
        plain, _ = ladder_capture(ladder_board(), "D10", WHITE, max_depth=d)
        broken, _ = ladder_capture(ladder_board("N4"), "D10", WHITE, max_depth=d)
        assert plain and not broken, d        # 分得出來，而且兩邊都對


# ------------------------------------- 練習

def test_exercise_10_1():
    b = Board(3)
    b.place(BLACK, "B2")
    b.place(WHITE, "B3")
    d = dict(move_values(b, BLACK, komi=0.0, max_ply=MAX_PLY))
    assert d[b._pt("A2")] == 9
    assert d[b._pt("C2")] == 9
    assert d[b._pt("B1")] == 9               # 三個正解
    assert d[b._pt("A3")] == -1              # 角落虧 10
    assert d[None] == -3


def test_exercise_10_3():
    b = Board(3)
    b.place_many(BLACK, ["B2", "A2"])
    b.place_many(WHITE, ["B3", "C2"])
    d = dict(move_values(b, BLACK, komi=0.0, max_ply=MAX_PLY))
    assert max(d.values()) == 9
    assert d[b._pt("A3")] == 9 and d[b._pt("B1")] == 9
    assert d[b._pt("A1")] == -1
    assert d[b._pt("C1")] == -3
    # 兩個角的值不同 ——「角」本身不是有意義的分類
    assert d[b._pt("A1")] != d[b._pt("C1")]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
