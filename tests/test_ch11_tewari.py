"""第 11 章的計算核心：手割的兩層定理、它的失效條件、以及規則的評分。

跑法：  python -m pytest tests/ -q      或   python tests/test_ch11_tewari.py
"""

import itertools
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.setrecursionlimit(100000)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from go_core import BLACK, EMPTY, WHITE, Board, format_coord, opposite  # noqa: E402
from go_core.cgt import ZERO                                         # noqa: E402
from go_core.endgame import corridor, region_value                   # noqa: E402
from go_core.minimax import Solver, legal_moves, move_values         # noqa: E402
from go_core.tewari import (_board_from_key, is_capture_free,         # noqa: E402
                            play_sequence, policy_centre,
                            policy_greedy_score, policy_influence,
                            policy_liberties, reachable_states,
                            score_policy, solve_all, stone_set,
                            tewari_equal)

MAX_PLY = 15
BLACK_STONES = ["B2", "A1"]
WHITE_STONES = ["B3", "C2"]


# ------------------------------------------------- 定理 11.1（盤面版）

def test_capture_free_reordering_gives_the_same_board():
    A = [(BLACK, "B2"), (WHITE, "B3"), (BLACK, "A1"), (WHITE, "C2")]
    B = [(BLACK, "A1"), (WHITE, "C2"), (BLACK, "B2"), (WHITE, "B3")]
    r = tewari_equal(A, B, n=3)
    assert r["same"]
    assert not r["captures_a"] and not r["captures_b"]
    assert is_capture_free(A, 3) and is_capture_free(B, 3)


def test_all_orderings_of_four_stones_agree():
    """四顆子的所有合法順序，終局盤面只有一種。"""
    boards = set()
    for bo in itertools.permutations(BLACK_STONES):
        for wo in itertools.permutations(WHITE_STONES):
            seq = [(BLACK, bo[0]), (WHITE, wo[0]),
                   (BLACK, bo[1]), (WHITE, wo[1])]
            b, caps = play_sequence(seq, n=3)
            assert not caps, seq
            boards.add(b.grid.tobytes())
    assert len(boards) == 1


def test_stone_set_is_the_right_invariant():
    b, _ = play_sequence([(BLACK, "B2"), (WHITE, "B3")], n=3)
    s = stone_set(b)
    assert (b._pt("B2"), BLACK) in s
    assert (b._pt("B3"), WHITE) in s
    assert len(s) == 2


# ------------------------------------------------- 失效一：提子

def test_captures_break_commutativity():
    C = [(BLACK, "A1"), (BLACK, "B1"), (WHITE, "A2"), (WHITE, "B2"),
         (WHITE, "C1")]
    D = [(WHITE, "A2"), (WHITE, "B2"), (WHITE, "C1"), (BLACK, "A1"),
         (BLACK, "B1")]
    r = tewari_equal(C, D, n=3)
    assert not r["same"]
    assert r["captures_a"]            # 順序 C 有提子
    assert r["illegal_b"]             # 順序 D 有一手不合法
    assert r["only_b"] == [("A1", BLACK)]
    assert r["only_a"] == []


def test_capture_order_a_empties_the_corner():
    C = [(BLACK, "A1"), (BLACK, "B1"), (WHITE, "A2"), (WHITE, "B2"),
         (WHITE, "C1")]
    b, caps = play_sequence(C, n=3)
    assert b.grid[b._pt("A1")] == EMPTY
    assert b.grid[b._pt("B1")] == EMPTY
    assert len(caps) == 1 and len(caps[0][3]) == 2


# ------------------------------------------------- 失效二：劫

def ko_board():
    b = Board(3)
    b.place_many(BLACK, ["A3", "C3", "B2", "C1"])
    b.place_many(WHITE, ["A2", "A1"])
    return b


def test_ko_makes_the_same_board_two_different_positions():
    b = ko_board()
    solver = Solver(komi=0.0, max_ply=MAX_PLY)
    v_free, _ = solver.search(b, WHITE, ko=None)
    v_ko, _ = solver.search(b, WHITE, ko=b._pt("B3"))
    assert v_free == -9
    assert v_ko == 9
    assert abs(v_ko - v_free) == 18            # 整個棋盤


def test_ko_clashes_are_common_not_exotic():
    """3 路盤 6 手之內：同盤面同輪次、劫狀態不同而 V 不同的，是常態不是特例。"""
    states = reachable_states(3, 6)
    groups = defaultdict(set)
    for grid, colour, ko in states:
        groups[(grid, colour)].add(ko)
    candidates = {k: v for k, v in groups.items() if len(v) > 1}
    assert candidates, "6 手之內應該就有劫"

    solver = Solver(komi=0.0, max_ply=MAX_PLY)
    clashes = 0
    for (grid, colour), kos in candidates.items():
        vals = set()
        for ko in kos:
            b, _, _ = _board_from_key((grid, colour, ko), 3)
            vals.add(solver.search(b, colour, ko=ko)[0])
        clashes += len(vals) > 1
    assert clashes > 0
    assert clashes / len(candidates) > 0.1     # 佔比不低


def test_ko_first_appears_at_depth_five():
    assert all(k[2] is None for k in reachable_states(3, 4))
    assert any(k[2] is not None for k in reachable_states(3, 5))


# ------------------------------------------------- 定理 11.2（值版）

def _walk(seq, solver):
    b, steps = Board(3), []
    for colour, coord in seq:
        before = solver.search(b, colour)[0]
        t = b.copy()
        assert not t.play(colour, coord)
        after = solver.search(t, opposite(colour))[0]
        loss = (before - after) if colour == BLACK else (after - before)
        steps.append((colour, coord, loss))
        b = t
    return steps, b


def test_loss_difference_is_path_independent():
    """定理 11.2：黑失分 - 白失分，與順序無關。"""
    solver = Solver(komi=0.0, max_ply=MAX_PLY)
    diffs, finals, totals = set(), set(), set()
    for bo in itertools.permutations(BLACK_STONES):
        for wo in itertools.permutations(WHITE_STONES):
            seq = [(BLACK, bo[0]), (WHITE, wo[0]),
                   (BLACK, bo[1]), (WHITE, wo[1])]
            steps, final = _walk(seq, solver)
            lb = sum(l for c, _, l in steps if c == BLACK)
            lw = sum(l for c, _, l in steps if c == WHITE)
            diffs.add(lb - lw)
            totals.add((lb, lw))
            finals.add(final.grid.tobytes())
    assert len(finals) == 1
    assert diffs == {10.0}                     # 差守恆
    assert len(totals) > 1                     # 但各自的總量【不】守恆


def test_telescoping_matches_head_minus_tail():
    solver = Solver(komi=0.0, max_ply=MAX_PLY)
    v0 = solver.search(Board(3), BLACK)[0]
    fin = Board(3)
    fin.place_many(BLACK, BLACK_STONES)
    fin.place_many(WHITE, WHITE_STONES)
    v4 = solver.search(fin, BLACK)[0]
    assert v0 == 9 and v4 == -1
    assert v0 - v4 == 10.0


def test_reordering_exposes_the_big_loss():
    """重排讓 18 目的失分現形；原順序最大只有 11。"""
    solver = Solver(komi=0.0, max_ply=MAX_PLY)
    good = [(BLACK, "B2"), (WHITE, "B3"), (BLACK, "A1"), (WHITE, "C2")]
    bad = [(BLACK, "A1"), (WHITE, "B3"), (BLACK, "B2"), (WHITE, "C2")]
    sg, _ = _walk(good, solver)
    sb, _ = _walk(bad, solver)
    assert max(l for _, _, l in sg) == 11
    assert max(l for _, _, l in sb) == 18
    # 但總帳一樣
    diff = lambda st: (sum(l for c, _, l in st if c == BLACK)
                       - sum(l for c, _, l in st if c == WHITE))
    assert diff(sg) == diff(sb) == 10.0


def test_move_counts_must_match_for_a_valid_reordering():
    A = [(BLACK, "B2"), (WHITE, "A1"), (BLACK, "C3")]
    B = [(BLACK, "C3"), (WHITE, "A1"), (BLACK, "B2")]
    assert Counter(c for c, _ in A) == Counter(c for c, _ in B)
    assert tewari_equal(A, B, n=3)["same"]


# ------------------------------------------------- 兩分 = 局部值 0

def test_two_halves_means_local_value_zero():
    """「兩分」= G + (-G) = 0 = 見合（第 6 章定義 6.9）。"""
    for n in [1, 2, 3]:
        b, region = corridor(n)
        G = region_value(b, region)
        assert (G + (-G)).canonical() == ZERO, n


# ------------------------------------------------- §4.4 規則評分

def test_centre_rule_beats_the_influence_field():
    """3 路盤上，一行的規則打敗第 9 章整套場。"""
    states = reachable_states(3, 3)            # 小一點，測試才跑得快
    table, _ = solve_all(states, n=3)
    centre = score_policy(table, policy_centre, n=3)
    field = score_policy(table, policy_influence, n=3)
    libs = score_policy(table, policy_liberties, n=3)
    greedy = score_policy(table, policy_greedy_score, n=3)
    assert centre["hit_rate"] > field["hit_rate"]
    assert field["hit_rate"] > libs["hit_rate"]
    assert libs["hit_rate"] > greedy["hit_rate"]
    assert centre["mean_loss"] < field["mean_loss"]


def test_random_policy_is_the_floor():
    states = reachable_states(3, 3)
    table, _ = solve_all(states, n=3)
    rng = random.Random(1)

    def pol(board, to_move, ko=None):
        opts = [p for p, _, _ in legal_moves(board, to_move, ko)]
        return rng.choice(opts) if opts else None

    r = score_policy(table, pol, n=3)
    assert r["hit_rate"] < 0.6
    assert r["mean_loss"] > 3


def test_best_move_is_usually_not_unique():
    states = reachable_states(3, 3)
    table, _ = solve_all(states, n=3)
    counts = [len(best) for best, _ in table.values()]
    assert max(counts) > 1
    assert sum(counts) / len(counts) > 1.5     # 平均超過一個


# ------------------------------------------------- §4.5 定石辭典

def _dictionary(table, win):
    winset = set(win)
    groups = defaultdict(list)
    for key, (best, _v) in table.items():
        board, colour, _ko = _board_from_key(key, 3)
        groups[(tuple(int(board.grid[p]) for p in win), colour)].append(best)
    hits = total = 0
    for members in groups.values():
        counter = Counter()
        for best in members:
            inside = [p for p in best if p in winset]
            if inside:
                for p in inside:
                    counter[p] += 1
            else:
                counter[None] += 1
        memorised = counter.most_common(1)[0][0]
        for best in members:
            total += 1
            inside = {p for p in best if p in winset}
            hits += (not inside) if memorised is None else (memorised in best)
    return len(groups), hits / total


def test_dictionary_only_reaches_100_percent_with_the_whole_board():
    states = reachable_states(3, 3)
    table, _ = solve_all(states, n=3)
    windows = [
        [(2, 0), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (2, 0), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)],
        [(r, c) for r in range(3) for c in range(3)],
    ]
    rates = [_dictionary(table, w) for w in windows]
    sizes = [s for s, _ in rates]
    hits = [h for _, h in rates]
    assert sizes == sorted(sizes)
    assert hits == sorted(hits)
    assert hits[-1] == 1.0                     # 只有看全盤才 100%
    assert hits[0] < 0.9                       # 只看一列遠遠不夠


def test_dictionary_has_diminishing_returns():
    states = reachable_states(3, 3)
    table, _ = solve_all(states, n=3)
    windows = [
        [(2, 0), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (2, 0), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)],
        [(r, c) for r in range(3) for c in range(3)],
    ]
    rates = [_dictionary(table, w) for w in windows]
    marginal = [(rates[i + 1][1] - rates[i][1]) / (rates[i + 1][0] - rates[i][0])
                for i in range(len(rates) - 1)]
    assert marginal == sorted(marginal, reverse=True), marginal


# ------------------------------------------------- 練習

def test_exercise_11_2():
    b = Board(3)
    b.place_many(BLACK, ["B2", "B1"])
    b.place_many(WHITE, ["B3", "A2"])
    vals = dict(move_values(b, BLACK, komi=0.0, max_ply=MAX_PLY))
    best = max(vals.values())
    winners = {p for p, v in vals.items() if v == best}
    assert best == 9
    assert winners == {b._pt("C2"), b._pt("A1")}
    assert policy_centre(b, BLACK) in winners
    # A1 是角，「靠中央」給它最差的評價，它卻和 C2 一樣好
    dist = lambda p: abs(p[0] - 1) + abs(p[1] - 1)
    assert dist(b._pt("A1")) > dist(b._pt("C2"))


def test_exercise_11_3():
    b = ko_board()
    solver = Solver(komi=0.0, max_ply=MAX_PLY)
    assert solver.search(b, WHITE, ko=None)[0] == -9
    assert solver.search(b, WHITE, ko=b._pt("B3"))[0] == 9


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
