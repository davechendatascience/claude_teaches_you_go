"""第 13 章的計算核心：三種計分、等價定理、終局、兩套規則的貼目。

跑法：  python -m pytest tests/ -q      或   python tests/test_ch13_scoring.py
"""

import random
import statistics
import sys
from pathlib import Path

sys.setrecursionlimit(200000)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from go_core import BLACK, EMPTY, WHITE, Board, format_coord, opposite  # noqa: E402
from go_core.minimax import Solver, area_score                       # noqa: E402
from go_core.score import (ScoredGame, chinese_score, dame,           # noqa: E402
                           empty_regions, equivalence_gap, is_finished,
                           japanese_score, random_finished_game,
                           solve_japanese, stones, territory,
                           tromp_taylor_score)

MAX_PLY = 15


def wall_board(n=7):
    """黑牆在 C 列、白牆在 E 列，中間 D 列是單官。"""
    b = Board(n)
    for r in range(1, n + 1):
        b.place(BLACK, f"C{r}")
        b.place(WHITE, f"E{r}")
    return b


# ------------------------------------------------- 基本計分

def test_territory_only_counts_single_colour_regions():
    b = wall_board()
    tb, tw = territory(b)
    assert (tb, tw) == (14, 14)
    assert len(dame(b)) == 7            # D 列碰得到兩色


def test_dame_touches_both_colours():
    b = wall_board()
    for p in dame(b):
        region_colours = None
        for region, colours in empty_regions(b):
            if p in region:
                region_colours = colours
        assert region_colours == frozenset({BLACK, WHITE})


def test_chinese_is_stones_plus_territory():
    b = wall_board()
    sb, sw = stones(b)
    tb, tw = territory(b)
    assert chinese_score(b) == (sb + tb) - (sw + tw)
    assert (sb, sw) == (7, 7)


def test_japanese_is_territory_plus_prisoners():
    b = wall_board()
    assert japanese_score(b) == 0
    assert japanese_score(b, prisoners_black=5) == 5
    assert japanese_score(b, prisoners_white=3) == -3


def test_tromp_taylor_equals_chinese_on_finished_boards():
    rng = random.Random(7)
    for _ in range(20):
        g = random_finished_game(9, rng)
        assert tromp_taylor_score(g.board) == chinese_score(g.board)


def test_komi_shifts_both_the_same_way():
    b = wall_board()
    assert chinese_score(b, komi=6.5) == chinese_score(b) - 6.5
    assert japanese_score(b, komi=6.5) == japanese_score(b) - 6.5


# ------------------------------------------------- 定義 13.1（終局）

def test_is_finished_iff_no_dame():
    b = wall_board()
    done, left = is_finished(b)
    assert not done and left == 7

    colour = BLACK
    while True:
        d = sorted(dame(b))
        if not d:
            break
        b.play(colour, format_coord(d[0], 7))
        colour = opposite(colour)
    done, left = is_finished(b)
    assert done and left == 0


# ------------------------------------------------- 定理 13.2

def test_equivalence_on_the_wall_board():
    g = ScoredGame(7)
    for r in range(1, 8):
        g.board.place(BLACK, f"C{r}")
        g.board.place(WHITE, f"E{r}")
    # 擺盤面不算手數，所以此時 b = w = 0 而 C = J = 0
    assert g.check_equivalence()[4]

    colour = BLACK
    while True:
        d = sorted(dame(g.board))
        if not d:
            break
        g.play(colour, format_coord(d[0], 7))
        colour = opposite(colour)

    r = g.report()
    assert r["moves"] == (4, 3)          # 七個單官，黑先填
    assert r["chinese"] == 1
    assert r["japanese"] == 0
    assert r["gap"] == r["move_diff"] == 1


def test_equivalence_on_300_random_games():
    """定理 13.2：C - J = b - w，零例外。"""
    rng = random.Random(1313)
    bad = 0
    for _ in range(300):
        g = random_finished_game(9, rng)
        _, _, gap, md, ok = g.check_equivalence()
        bad += not ok
    assert bad == 0


def test_equal_move_counts_means_identical_scores():
    """b = w 時兩套規則完全相同。"""
    rng = random.Random(99)
    seen = 0
    for _ in range(300):
        g = random_finished_game(9, rng)
        c, j, gap, md, ok = g.check_equivalence()
        assert ok
        if md == 0:
            assert c == j
            seen += 1
    assert seen > 0, "300 局裡應該有一些是手數相等的"


def test_move_difference_median_is_one():
    """b - w 的中位數是 1 —— 貼目那一目差的來源。"""
    rng = random.Random(1313)
    diffs = []
    for _ in range(300):
        g = random_finished_game(9, rng)
        diffs.append(g.check_equivalence()[3])
    assert statistics.median(diffs) == 1
    assert 0.5 < statistics.mean(diffs) < 1.5
    assert min(diffs) < 0 < max(diffs)   # 但分佈遠比 {0,1} 寬


def test_random_games_finish_with_no_dame():
    rng = random.Random(5)
    for _ in range(30):
        g = random_finished_game(9, rng)
        assert is_finished(g.board)[0]


def test_equivalence_gap_reports_correctly():
    b = Board(3)
    b.place_many(BLACK, ["A1", "A2", "A3", "B2", "C1", "C3"])
    c, j, gap, md, ok = equivalence_gap(b, 6, 2, prisoners_black=2)
    assert c == 9 and j == 5
    assert gap == md == 4 and ok


# ------------------------------------------------- 命題 13.3

def test_dame_belongs_to_nobody_in_both_systems():
    """單官在兩套規則下都不算目。"""
    b = wall_board()
    tb, tw = territory(b)
    total_empty = sum(1 for p in b.points() if b.grid[p] == EMPTY)
    assert tb + tw + len(dame(b)) == total_empty
    # 填掉一個單官，兩邊的「地」都不變
    b2 = b.copy()
    b2.play(BLACK, format_coord(sorted(dame(b))[0], 7))
    assert territory(b2) == (tb, tw)


# ------------------------------------------------- §4.3 貼目

def test_chinese_fair_komi_on_3x3_is_nine():
    for ply in [13, 15, 17]:
        s = Solver(komi=0.0, max_ply=ply)
        assert s.search(Board(3), BLACK)[0] == 9, ply


def test_japanese_fair_komi_on_3x3_is_five():
    for ply in [13, 15, 17]:
        v, _, _ = solve_japanese(Board(3), BLACK, komi=0.0, max_ply=ply)
        assert v == 5, ply


def test_fair_komi_makes_the_empty_board_zero():
    assert Solver(komi=9, max_ply=MAX_PLY).search(Board(3), BLACK)[0] == 0
    assert solve_japanese(Board(3), BLACK, komi=5, max_ply=MAX_PLY)[0] == 0


def test_both_rules_pick_tengen_first():
    _, cmv = Solver(komi=0.0, max_ply=MAX_PLY).search(Board(3), BLACK)
    _, jmv, _ = solve_japanese(Board(3), BLACK, komi=0.0, max_ply=MAX_PLY)
    assert format_coord(cmv, 3) == format_coord(jmv, 3) == "B2"


def test_japanese_optimal_white_stops_playing():
    """數目規則下白只下兩手就虛手 —— 多放一顆就是多送一個提子。"""
    from go_core.minimax import legal_moves

    g = ScoredGame(3)
    colour, ko, passes, ply = BLACK, None, 0, 0
    while ply < MAX_PLY and passes < 2:
        _, mv, _ = solve_japanese(g.board, colour, komi=0.0,
                                  max_ply=MAX_PLY - ply)
        if mv is None:
            g.pass_move()
            passes += 1
            ko = None
        else:
            for p, child, nk in legal_moves(g.board, colour, ko):
                if p == mv:
                    g.play(colour, format_coord(p, 3))
                    ko = nk
                    break
            passes = 0
        colour = opposite(colour)
        ply += 1
    r = g.report()
    assert r["moves"] == (6, 2)
    assert r["chinese"] == 9 and r["japanese"] == 5
    assert r["gap"] == r["move_diff"] == 4


def test_chinese_optimal_white_plays_on():
    """數子規則下白一路下到底 —— 填了不用付錢。"""
    from go_core.minimax import legal_moves

    s = Solver(komi=0.0, max_ply=MAX_PLY)
    g = ScoredGame(3)
    colour, ko, passes, ply = BLACK, None, 0, 0
    while ply < MAX_PLY and passes < 2:
        _, mv = s.search(g.board, colour, passes=passes, ko=ko, ply=ply)
        if mv is None:
            g.pass_move()
            passes += 1
            ko = None
        else:
            for p, child, nk in legal_moves(g.board, colour, ko):
                if p == mv:
                    g.play(colour, format_coord(p, 3))
                    ko = nk
                    break
            passes = 0
        colour = opposite(colour)
        ply += 1
    r = g.report()
    assert r["moves"][1] > 2             # 白下得比數目規則下多
    assert r["chinese"] == 9
    assert r["gap"] == r["move_diff"]


# ------------------------------------------------- §4.5 雙活的眼

def test_seki_eyes_only_shift_the_japanese_side():
    b = wall_board()
    plain = japanese_score(b)
    assert japanese_score(b, seki_eyes=3) == plain - 3
    assert chinese_score(b) == 0          # 中國規則不受影響


def test_seki_eye_worked_example():
    """§4.5 的算術例子：地 40:38、手數相等、雙活裡黑 2 眼白 1 眼。"""
    c = 40 - 38
    j = 40 - 38                            # b = w，所以兩者相同
    j_prime = (40 - 2) - (38 - 1)
    assert c == j == 2
    assert j_prime == 1
    assert c - j_prime == 1                # 差額 = 眼數的黑減白


# ------------------------------------------------- §4.6 死子

def dead_stone_board():
    g = ScoredGame(7)
    for c in ["B1", "B2", "B3", "B4", "B5", "B6", "B7",
              "C7", "D7", "E7", "F7", "G7"]:
        g.board.place(BLACK, c)
    for c in ["A3", "A4"]:
        g.board.place(WHITE, c)
    return g


def test_chinese_settles_dead_stones_by_playing():
    g = dead_stone_board()
    placed_b, placed_w = 12, 2
    for mv in ["A5", "A2", "A1", "A6", "A7"]:
        if g.board.grid[g.board._pt(mv)] == EMPTY:
            g.play(BLACK, mv)
    r = g.report()
    assert r["chinese"] == 49              # 整個 49 點的棋盤
    b_total = placed_b + r["moves"][0]
    w_total = placed_w + r["moves"][1]
    j_agreed = japanese_score(g.board, prisoners_black=2)
    assert j_agreed == 34
    assert r["chinese"] - j_agreed == b_total - w_total == 15


def test_benson_only_gives_a_sufficient_condition():
    """Benson 判不出「死」—— 它只保證「活」。"""
    from go_core.benson import benson_alive

    g = dead_stone_board()
    # 黑那一大塊沒有被 Benson 認證，但沒有人會說它死了
    assert len(benson_alive(g.board, BLACK, trace=False)) == 0
    assert len(benson_alive(g.board, WHITE, trace=False)) == 0


# ------------------------------------------------- 練習

def test_exercise_13_1_parity():
    """單官奇數 -> 差一目；偶數 -> 完全相同。"""
    for first in (BLACK, WHITE):
        g = ScoredGame(7)
        for r in range(1, 8):
            g.board.place(BLACK, f"C{r}")
            g.board.place(WHITE, f"E{r}")
        colour = first
        while True:
            d = sorted(dame(g.board))
            if not d:
                break
            g.play(colour, format_coord(d[0], 7))
            colour = opposite(colour)
        r = g.report()
        assert abs(r["gap"]) == 1          # 七個單官是奇數
        assert r["gap"] == r["move_diff"]


def test_exercise_13_2():
    b = Board(3)
    b.place_many(BLACK, ["A1", "A2", "A3", "B2", "C1", "C3"])
    assert stones(b) == (6, 0)
    assert territory(b) == (3, 0)
    assert chinese_score(b) == 9
    assert chinese_score(b) - (6 - 2) == 5
    assert japanese_score(b, prisoners_black=2) == 5


def test_exercise_13_3_ideal_bound():
    """無提子、不虛手、嚴格交替 -> b - w in {0, 1}。"""
    for n_moves in range(0, 20):
        b = (n_moves + 1) // 2
        w = n_moves // 2
        assert b - w in (0, 1)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
