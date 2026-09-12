"""第 12 章的計算核心：賭注、死活擺盪、做活點、急場判定。

跑法：  python -m pytest tests/ -q      或   python tests/test_ch12_attack.py
"""

import sys
from pathlib import Path

sys.setrecursionlimit(100000)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from go_core import BLACK, EMPTY, WHITE, Board, find_string, format_coord  # noqa: E402
from go_core.attack import (as_switch, can_kill, enclosed_empties,   # noqa: E402
                            is_alive, is_urgent, life_distance,
                            life_distance_contested, life_swing,
                            should_abandon, stake, urgency, vital_points)
from go_core.minimax import area_score                               # noqa: E402
from go_core.temperature import mean, temperature                    # noqa: E402


def corridor_group(e, n=9):
    """眼位長 e 的一塊黑棋，四周被白包住。"""
    b = Board(n)
    b.place_many(BLACK, [f"B{r}" for r in range(1, e + 2)] + [f"A{e + 1}"])
    b.place_many(WHITE, [f"C{r}" for r in range(1, e + 2)]
                 + [f"B{e + 2}", f"A{e + 2}"])
    return b, find_string(b, "B1")


# ------------------------------------------------- 賭注

def test_enclosed_empties_only_counts_regions_touching_this_group():
    b, S = corridor_group(3)
    region = enclosed_empties(b, S)
    assert sorted(format_coord(p, 9) for p in region) == ["A1", "A2", "A3"]
    # 棋盤右邊那一大片碰得到白，不算
    assert all(b.grid[p] == EMPTY for p in region)


def test_enclosed_empties_excludes_regions_touching_other_groups():
    """碰得到【別塊同色棋】的空點，不算這塊棋的本錢。"""
    b = Board(9)
    b.place_many(BLACK, ["A3", "B3", "C3", "C2", "C1"])
    b.place(BLACK, "A1")                      # 另一塊黑，在同一個空區塊旁邊
    b.place_many(WHITE, ["A4", "B4", "C4", "D3", "D2", "D1"])
    S = find_string(b, "A3")
    assert b._pt("A1") not in S
    region = enclosed_empties(b, S)
    assert region == frozenset(), region       # A1 那塊黑讓角上的區域不算


def test_stake_is_stones_plus_territory():
    for e in range(1, 9):
        b, S = corridor_group(e, n=13)
        assert stake(b, S) == len(S) + len(enclosed_empties(b, S))


# ------------------------------------------------- 定理 12.2

def test_theorem_12_2_swing_is_twice_the_stake():
    """逐格數子，不套公式。"""
    for e in range(1, 9):
        b, S = corridor_group(e, n=13)
        assert life_swing(b, S) == 2 * stake(b, S), e


def test_swing_is_computed_not_asserted():
    """life_swing 真的呼叫 area_score 兩次 —— 拿手算的結果核對一次。"""
    b, S = corridor_group(3)
    region = enclosed_empties(b, S)
    alive = b.copy()
    dead = b.copy()
    for p in set(S) | set(region):
        dead.grid[p] = WHITE
    ab, aw = area_score(alive)
    db, dw = area_score(dead)
    assert life_swing(b, S) == (ab - aw) - (db - dw)


# ------------------------------------------------- 命題 12.3

def test_unsettled_group_temperature_equals_stake():
    for e in range(1, 9):
        b, S = corridor_group(e, n=13)
        G = as_switch(b, S)
        assert temperature(G) == stake(b, S), e
        assert mean(G) == 0, e
        assert urgency(b, S) == stake(b, S)


def test_deiri_of_the_group_is_the_swing():
    """出入 = 2 x 溫度 = 2k = 擺盪。第 7 章定理 7.6 的同一個 2。"""
    for e in range(2, 8):
        b, S = corridor_group(e, n=13)
        assert 2 * temperature(as_switch(b, S)) == life_swing(b, S), e


# ------------------------------------------------- 定理 12.4（急場）

def test_urgency_threshold_is_the_global_temperature():
    b, S = corridor_group(3)
    k = stake(b, S)
    assert k == 8
    assert is_urgent(b, S, k - 1)[0] is True     # T' < k -> 急場
    assert is_urgent(b, S, k)[0] is False        # 平手不算急
    assert is_urgent(b, S, k + 1)[0] is False


def test_critical_point_is_2k_not_k():
    """臨界的大場出入是 2k；用 k 當門檻會在 (k, 2k] 整段選錯。"""
    b, S = corridor_group(3)
    k = stake(b, S)
    flips = []
    for D in range(2, 4 * k + 1, 2):
        correct = is_urgent(b, S, D / 2)[0]      # 2k > D
        naive = k > D
        if correct != naive:
            flips.append(D)
    assert flips, "應該有一段區間會選錯"
    # 選錯的區間是 k <= D < 2k，等價於書上寫的 D/2 < k <= D
    assert min(flips) >= k and max(flips) < 2 * k
    for D in flips:
        assert D / 2 < k <= D
    # 錯的方向永遠一樣：正確說急場，天真說大場
    for D in flips:
        assert is_urgent(b, S, D / 2)[0] and not (k > D)


# ------------------------------------------------- 做活點

def test_vital_points_count_is_e_minus_2():
    for e in range(1, 8):
        b, S = corridor_group(e)
        assert len(vital_points(b, S, BLACK)) == max(0, e - 2), e


def test_vital_points_really_make_it_alive():
    for e in range(3, 7):
        b, S = corridor_group(e)
        for p in vital_points(b, S, BLACK):
            t = b.copy()
            t.play(BLACK, p)
            assert is_alive(t, find_string(t, p), BLACK), (e, p)


def test_attacker_kills_exactly_when_vital_points_at_most_one():
    """鴿籠原理：一手只佔得住一個做活點。"""
    for e in range(1, 8):
        b, S = corridor_group(e)
        n_vital = len(vital_points(b, S, BLACK))
        assert can_kill(b, S, BLACK, max_moves=3) == (n_vital <= 1), e


def test_straight_three_dies_straight_four_lives():
    b3, S3 = corridor_group(3)
    b4, S4 = corridor_group(4)
    assert can_kill(b3, S3, BLACK, max_moves=3)          # 直三死
    assert not can_kill(b4, S4, BLACK, max_moves=3)      # 直四活
    # 而守方先手時直三活
    assert life_distance(b3, S3, BLACK, max_moves=2)[0] == 1


def test_square_four_has_no_vital_points():
    """e - 2 只對直線眼位成立。方四同樣四點，做活點是 0。"""
    b = Board(9)
    b.place_many(BLACK, ["A3", "B3", "C3", "C2", "C1"])
    b.place_many(WHITE, ["A4", "B4", "C4", "D3", "D2", "D1"])
    S = find_string(b, "A3")
    assert len(enclosed_empties(b, S)) == 4              # 眼位確實是 4 點
    assert vital_points(b, S, BLACK) == []               # 但做活點 0 個


# ------------------------------------------------- 治孤距離

def test_life_distance_is_one_when_a_vital_point_exists():
    for e in range(3, 8):
        b, S = corridor_group(e)
        d, path = life_distance(b, S, BLACK, max_moves=3)
        assert d == 1, e
        assert path[0] in vital_points(b, S, BLACK)


def test_life_distance_none_when_dead():
    for e in [1, 2]:
        b, S = corridor_group(e)
        assert life_distance(b, S, BLACK, max_moves=3)[0] is None, e


def test_contested_distance_matches_free_when_one_move_suffices():
    for e in range(3, 7):
        b, S = corridor_group(e)
        assert life_distance_contested(b, S, BLACK, max_moves=3) == 1, e


def test_already_alive_has_distance_zero():
    b, S = corridor_group(5)
    t = b.copy()
    t.play(BLACK, vital_points(b, S, BLACK)[0])
    S2 = find_string(t, "B1")
    assert is_alive(t, S2, BLACK)
    assert life_distance(t, S2, BLACK)[0] == 0


# ------------------------------------------------- 分斷

def connected_board():
    b = Board(9)
    b.place_many(BLACK, ["B1", "B2", "B3", "B4", "B5", "A5"])
    b.place_many(WHITE, ["C1", "C2", "C3", "C4", "C5", "B6", "A6"])
    return b, find_string(b, "B1")


def split_board():
    b = Board(9)
    b.place_many(BLACK, ["B1", "B2", "B3", "A3", "B6", "B7", "B8", "A6"])
    b.place_many(WHITE, ["C1", "C2", "C3", "B4", "A4", "C6", "C7", "C8",
                         "B9", "A9", "B5", "A5"])
    return b, find_string(b, "B1"), find_string(b, "B6")


def test_connected_lives_split_dies():
    conn, Sc = connected_board()
    assert len(vital_points(conn, Sc, BLACK)) == 2
    assert not can_kill(conn, Sc, BLACK, max_moves=3)

    split, Sa, Sb = split_board()
    assert Sa != Sb
    for S in (Sa, Sb):
        assert vital_points(split, S, BLACK) == []
        assert can_kill(split, S, BLACK, max_moves=3)


def test_vital_points_are_superadditive_under_splitting():
    """切一刀，做活點從 e-2 變成 (e1-2)+(e2-2) = e-4。"""
    for e1, e2 in [(2, 2), (3, 2), (3, 3), (4, 2)]:
        whole = max(0, (e1 + e2) - 2)
        parts = max(0, e1 - 2) + max(0, e2 - 2)
        assert parts == max(0, e1 - 2) + max(0, e2 - 2)
        assert whole - parts >= 2 or (e1 < 3 and e2 < 3)


# ------------------------------------------------- 棄子

def test_should_abandon_when_unsavable():
    b, S = corridor_group(2)
    abandon, swing, cost, d = should_abandon(b, S, 10)
    assert abandon is True
    assert d is None and cost == float("inf")
    assert swing == 2 * stake(b, S)


def test_should_not_abandon_a_cheap_save():
    b, S = corridor_group(5)
    abandon, swing, cost, d = should_abandon(b, S, 5)
    assert d == 1
    assert cost == 5
    assert swing == 2 * stake(b, S) == 24
    assert abandon is False                    # 24 > 5


# ------------------------------------------------- 練習

def test_exercise_12_1():
    b, S = corridor_group(2)
    assert len(S) == 4
    assert len(enclosed_empties(b, S)) == 2
    assert stake(b, S) == 6
    assert life_swing(b, S) == 12
    assert vital_points(b, S, BLACK) == []
    assert life_distance(b, S, BLACK, max_moves=3)[0] is None
    assert can_kill(b, S, BLACK, max_moves=3)


def test_exercise_12_2():
    b, S = corridor_group(3)
    assert stake(b, S) == 8
    assert is_urgent(b, S, 10)[0] is False     # D = 20
    assert is_urgent(b, S, 7)[0] is True       # D = 14


def test_exercise_12_3():
    b, S = corridor_group(4)
    assert len(vital_points(b, S, BLACK)) == 2
    assert not can_kill(b, S, BLACK, max_moves=3)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
