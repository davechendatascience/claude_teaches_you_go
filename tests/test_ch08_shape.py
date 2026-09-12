"""第 8 章的計算核心：形的效率、邊際氣、三個手筋、征子與陰影。

跑法：  python -m pytest tests/ -q      或   python tests/test_ch08_shape.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from go_core import (BLACK, EMPTY, WHITE, Board, find_string,        # noqa: E402
                     format_coord, liberties, neighbors)
from go_core.ladder import ladder_capture, ladder_shadow             # noqa: E402
from go_core.shape import (canonical_shape, connection_points,       # noqa: E402
                           double_atari_points, efficiency,
                           enumerate_shapes, marginal_decomposition,
                           shape_on_board, shape_report,
                           snapback_points)


def build(stones, n=11, colour=BLACK, others=(), other_colour=WHITE):
    b = Board(n)
    b.place_many(colour, stones)
    if others:
        b.place_many(other_colour, others)
    return b, find_string(b, stones[0])


# ------------------------------------------------------- §4.2 四種四子形

FOUR = {
    "直四": ([(0, 0), (0, 1), (0, 2), (0, 3)], 10, 3, 0),
    "曲四": ([(0, 0), (0, 1), (0, 2), (1, 0)], 9, 3, 1),
    "丁四": ([(0, 0), (0, 1), (0, 2), (1, 1)], 8, 3, 2),
    "方四": ([(0, 0), (0, 1), (1, 0), (1, 1)], 8, 4, 0),
}


def test_four_shapes_decomposition():
    """§4.2 的表：氣、內部相鄰、重複，三個數字都要對。"""
    for name, (shape, libs, pairs, dup) in FOUR.items():
        board, S = shape_on_board(shape, n=11, origin=(4, 4))
        r = shape_report(board, S)
        assert r["deg_sum"] == 16, name
        assert r["liberties"] == libs, (name, r)
        assert r["internal_pairs"] == pairs, (name, r)
        assert r["duplicated"] == dup, (name, r)
        assert r["blocked"] == 0, name


def test_squeeze_versus_stupid():
    """丁四與方四都是 8 氣，但一個【愚】、一個【擠】。"""
    tee = FOUR["丁四"][0]
    sq = FOUR["方四"][0]
    bt, St = shape_on_board(tee, n=11, origin=(4, 4))
    bs, Ss = shape_on_board(sq, n=11, origin=(4, 4))
    rt, rs = shape_report(bt, St), shape_report(bs, Ss)

    assert rt["liberties"] == rs["liberties"] == 8      # 同樣的總數
    assert rt["stupid"] and not rs["stupid"]            # 但只有丁四是愚形
    assert rt["duplicated"] == 2 and rs["duplicated"] == 0
    # 方四的損失全在第二項：內部相鄰超過樹狀連接的最低成本 |S| - 1
    assert rs["internal_pairs"] == 4 > 4 - 1
    assert rt["internal_pairs"] == 3 == 4 - 1


def test_efficiency_ranking():
    """直四是四子裡效率最高的，而效率最高的形狀永遠是一顆孤子。"""
    ranked = []
    for name in FOUR:
        board, S = shape_on_board(FOUR[name][0], n=11, origin=(4, 4))
        ranked.append((efficiency(board, S), name))
    ranked.sort(reverse=True)
    assert ranked[0][1] == "直四"

    lone, Sl = shape_on_board([(0, 0)], n=11, origin=(4, 4))
    assert efficiency(lone, Sl) == 4.0 > ranked[0][0]


# ------------------------------------------------------- §4.1 命題 8.2

def _random_shape(n, size, rng):
    b = Board(n)
    start = (rng.randrange(n), rng.randrange(n))
    b.grid[start] = BLACK
    pts = [start]
    while len(pts) < size:
        cand = [q for q in neighbors(rng.choice(pts), n) if b.grid[q] == EMPTY]
        if not cand:
            continue
        q = rng.choice(cand)
        b.grid[q] = BLACK
        pts.append(q)
    return b, find_string(b, start)


def test_marginal_formula_exhaustive():
    """命題 8.2：dL = deg(p) - k - 1 - delta+，對所有 <= 5 子的形狀窮舉。"""
    checked = 0
    for size in range(1, 6):
        for shape in enumerate_shapes(size, span=size):
            for origin in [(4, 4), (0, 0), (0, 1), (0, 4)]:
                board, S = shape_on_board(shape, n=11, origin=origin)
                for p in board.points():
                    if board.grid[p] != EMPTY:
                        continue
                    if not any(q in S for q in neighbors(p, 11)):
                        continue
                    m = marginal_decomposition(board, S, p)
                    assert m["delta"] == m["predicted"], (sorted(S), p, m)
                    checked += 1
    assert checked > 2500, checked


def test_delta_plus_never_negative():
    """delta+ >= 0：多一顆子只會讓更多空點被重複貼到。"""
    rng = random.Random(4242)
    for _ in range(200):
        n = rng.choice([9, 11, 13])
        board, S = _random_shape(n, rng.randint(1, 8), rng)
        for p in board.points():
            if board.grid[p] != EMPTY or not any(q in S for q in neighbors(p, n)):
                continue
            m = marginal_decomposition(board, S, p)
            assert m["new_duplicated"] >= 0, (sorted(S), p, m)


def test_two_liberty_ceiling():
    """推論 8.3：任何一手最多多兩口氣；邊上 1、角上 0。"""
    rng = random.Random(99)
    by_deg = {2: -99, 3: -99, 4: -99}
    for _ in range(300):
        board, S = _random_shape(13, rng.randint(1, 8), rng)
        for p in board.points():
            if board.grid[p] != EMPTY or not any(q in S for q in neighbors(p, 13)):
                continue
            m = marginal_decomposition(board, S, p)
            assert m["delta"] <= m["deg"] - m["contacts"] - 1, m
            by_deg[m["deg"]] = max(by_deg[m["deg"]], m["delta"])
    assert by_deg[4] == 2, by_deg          # 上界是緊的
    assert by_deg[3] == 1, by_deg
    assert by_deg[2] == 0, by_deg


def test_straight_three_marginal_table():
    """直三上的三手棋：長 +2、端點的肩 +1、中間的肩 0。差別只在 delta+。"""
    board, S = build(["E5", "F5", "G5"])
    assert len(liberties(board, S)) == 8
    expect = {"H5": (1, 0, 2), "D5": (1, 0, 2), "E6": (1, 1, 1), "F6": (1, 2, 0)}
    for mv in expect:
        k, dplus, dl = expect[mv]
        m = marginal_decomposition(board, S, mv)
        got = (m["contacts"], m["new_duplicated"], m["delta"])
        assert got == (k, dplus, dl), (mv, m)


def test_tiger_is_not_more_liberties_than_solid_connection():
    """草稿裡的錯誤宣稱：「虎比實接多兩口氣」。實際上三種下法完全一樣。"""
    def union_libs(board, coords):
        seen, total = set(), set()
        for c in coords:
            pt = board._pt(c)
            if pt in seen:
                continue
            T = find_string(board, pt)
            seen |= T
            total |= liberties(board, T)
        return total

    jump = Board(11)
    jump.place_many(BLACK, ["E5", "G5"])
    base = len(union_libs(jump, ["E5", "G5"]))
    assert base == 7

    outcomes = {}
    for mv in ["F5", "F4", "F6"]:
        t = jump.copy()
        t.place(BLACK, mv)
        outcomes[mv] = (len(union_libs(t, ["E5", "G5", mv])),
                        find_string(t, "E5") == find_string(t, "G5"))

    assert outcomes["F5"][0] == outcomes["F4"][0] == outcomes["F6"][0] == 8
    # 差別不在氣，在連接是不是真的
    assert outcomes["F5"][1] is True
    assert outcomes["F4"][1] is False and outcomes["F6"][1] is False


# ------------------------------------------------------- §4.3 三個手筋

def test_double_atari_needs_a_shared_liberty():
    """命題 8.5：雙打點就是兩塊各兩口氣的棋所【共用】的那一口。"""
    b, _ = build(["B3", "D3"], n=9, others=["A3", "B4", "E3", "D4"])
    lb = liberties(b, find_string(b, "B3"))
    ld = liberties(b, find_string(b, "D3"))
    assert len(lb) == len(ld) == 2
    shared = lb & ld
    assert len(shared) == 1

    pts = double_atari_points(b, WHITE)
    assert [p for p, _ in pts] == sorted(shared)
    assert pts[0][1] == 2


def test_double_atari_survives_a_change_of_shape():
    """同樣的條件、不一樣的圖形（練習 8.2）—— 查條件查得出來，認圖認不出來。"""
    b, _ = build(["C3", "E3"], n=9, others=["B3", "C4", "F3", "E4"])
    pts = double_atari_points(b, WHITE)
    assert [(format_coord(p, 9), k) for p, k in pts] == [("D3", 2)]


def test_no_double_atari_without_a_shared_liberty():
    """兩塊棋各兩口氣，但不共用 —— 就沒有雙打。"""
    b = Board(9)
    b.place_many(BLACK, ["B2", "G8"])
    b.place_many(WHITE, ["A2", "B3", "G7", "F8"])
    assert double_atari_points(b, WHITE) == []


def test_snapback_two_adjacent_liberties():
    """命題 8.6：倒撲要「兩口氣而且相鄰」。送一得三，逐手驗。"""
    b, S = build(["A2", "B2"], n=9, others=["A3", "B3", "C2", "C1"])
    libs = liberties(b, S)
    assert len(libs) == 2
    p, q = sorted(libs)
    assert q in neighbors(p, 9)            # 兩口氣相鄰

    found = snapback_points(b, WHITE)
    assert [(format_coord(x, 9), sac, got) for x, sac, got in found] == [("A1", 1, 3)]

    t = b.copy()
    t.play(WHITE, "A1")
    assert len(liberties(t, find_string(t, "A1"))) == 1     # 白送一子
    taken = t.play(BLACK, "B1")
    assert len(taken) == 1                                   # 黑提一子
    assert len(liberties(t, find_string(t, "B2"))) == 1      # 黑自己填掉一口氣
    assert len(t.play(WHITE, "A1")) == 3                     # 白提三子


def test_snapback_fails_when_liberties_are_not_adjacent():
    """兩口氣不相鄰時，送吃的那顆子有自己的氣，倒撲不成立。"""
    b = Board(9)
    b.place_many(BLACK, ["D5"])
    b.place_many(WHITE, ["C5", "E5"])
    libs = liberties(b, find_string(b, "D5"))
    assert len(libs) == 2
    p, q = sorted(libs)
    assert q not in neighbors(p, 9)        # D4 與 D6 不相鄰
    assert snapback_points(b, WHITE) == []


def test_connection_points_pigeonhole():
    """命題 8.8：兩個接點，一手只接得了一個 —— 兩眼定理的攻守互換。"""
    b = Board(9)
    b.place_many(BLACK, ["A1", "A2", "C1", "C2"])
    b.place_many(WHITE, ["A3", "B3", "C3", "D1", "D2"])
    S = find_string(b, "A1")
    cp = connection_points(b, S)
    assert sorted(format_coord(p, 9) for p, _ in cp) == ["B1", "B2"]
    assert len(cp) == 2

    # 接了一個，兩塊就變成一塊
    t = b.copy()
    t.play(BLACK, "B1")
    assert find_string(t, "A1") == find_string(t, "C1")


# ------------------------------------------------------- §4.4 征子

LADDER_TARGET = "D10"
LADDER_WHITE = ["D11", "C10", "E11"]


def ladder_board(extra=None, n=13):
    b = Board(n)
    b.place(BLACK, LADDER_TARGET)
    b.place_many(WHITE, LADDER_WHITE)
    if extra:
        b.place(BLACK, extra)
    return b


def test_ladder_runs_to_the_corner():
    ok, path = ladder_capture(ladder_board(), LADDER_TARGET, WHITE, max_depth=200)
    assert ok
    assert len(path) == 35
    pts = [p for _, p in path]
    assert pts[0] == ladder_board()._pt("D9")
    last = pts[-1]
    assert last[0] >= 10 and last[1] >= 10       # 一路斜到右下角


def test_ladder_needs_the_third_white_stone():
    """只有兩顆白子時黑長出去就有三口氣 —— 那不是征子。"""
    b = Board(13)
    b.place(BLACK, LADDER_TARGET)
    b.place_many(WHITE, ["D11", "C10"])
    ok, _ = ladder_capture(b, LADDER_TARGET, WHITE, max_depth=200)
    assert not ok


def test_ladder_direction_matters():
    """命題 8.9：往一邊叫吃黑得三口氣，往另一邊只有兩口。"""
    for first, expect in [("E10", 3), ("D9", 2)]:
        t = ladder_board()
        t.play(WHITE, first)
        reply = "D9" if first == "E10" else "E10"
        t.play(BLACK, reply)
        assert len(liberties(t, find_string(t, LADDER_TARGET))) == expect


def test_ladder_shadow_is_exactly_the_set_that_breaks_it():
    """陰影的定義就是它的驗證：在陰影裡放子 <=> 征子失敗。"""
    base = ladder_board()
    shadow = ladder_shadow(base, LADDER_TARGET, WHITE, max_depth=200)
    assert len(shadow) == 48

    rng = random.Random(2026)
    empties = [p for p in base.points() if base.grid[p] == EMPTY]
    for p in rng.sample(empties, 40):
        coord = format_coord(p, 13)
        ok, _ = ladder_capture(ladder_board(coord), LADDER_TARGET, WHITE,
                               max_depth=200)
        assert (p in shadow) == (not ok), coord


def test_ladder_breaker_can_be_far_away():
    """引徵可以離戰場很遠：N4 距離 D10 十五路，照樣破得掉。"""
    base = ladder_board()
    _, path = ladder_capture(base, LADDER_TARGET, WHITE, max_depth=200)
    shadow = ladder_shadow(base, LADDER_TARGET, WHITE, max_depth=200)
    on_path = {p for _, p in path}
    off = sorted(shadow - on_path)
    assert len(off) == 16               # 真正的「引徵」點

    origin = base._pt(LADDER_TARGET)

    def dist(q):
        return abs(q[0] - origin[0]) + abs(q[1] - origin[1])

    breaker = max(off, key=dist)
    assert format_coord(breaker, 13) == "N4"
    assert dist(breaker) == 15
    ok, _ = ladder_capture(ladder_board("N4"), LADDER_TARGET, WHITE, max_depth=200)
    assert not ok


def test_exercise_8_3():
    base = ladder_board()
    shadow = ladder_shadow(base, LADDER_TARGET, WHITE, max_depth=200)
    _, path = ladder_capture(base, LADDER_TARGET, WHITE, max_depth=200)
    on_path = {p for _, p in path}
    expect = {"G7": (True, True), "K7": (True, False), "M11": (False, False)}
    for coord in expect:
        in_shadow, on_the_path = expect[coord]
        pt = base._pt(coord)
        assert (pt in shadow) is in_shadow, coord
        assert (pt in on_path) is on_the_path, coord
        ok, _ = ladder_capture(ladder_board(coord), LADDER_TARGET, WHITE,
                               max_depth=200)
        assert (not ok) is in_shadow, coord


# ------------------------------------------------------- 形狀列舉

def test_shape_enumeration_counts():
    """去對稱之後的多連方塊數（polyomino）：1, 1, 2, 5, 12, 35。"""
    expect = {1: 1, 2: 1, 3: 2, 4: 5, 5: 12, 6: 35}
    for size in expect:
        shapes = {canonical_shape(s) for s in enumerate_shapes(size, span=size)}
        assert len(shapes) == expect[size], (size, len(shapes))


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
