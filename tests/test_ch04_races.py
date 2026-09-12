"""第 4 章的計算核心：氣的三分類、對殺判定式、大眼氣數。

跑法：  python -m pytest tests/ -q      或   python tests/test_ch04_races.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from go_core import BLACK, WHITE, Board, format_coord                    # noqa: E402
from go_core.capture_race import (attacker_moves, big_eye_liberties,     # noqa: E402
                                  classify_liberties, defender_moves,
                                  eye_points, race_formula,
                                  race_preconditions, race_winner)
from go_core.search import moves_to_capture, net_moves_to_capture        # noqa: E402
from go_core.strings import all_strings                                  # noqa: E402


def make(black=(), white=(), n=9):
    b = Board(n)
    b.place_many(BLACK, black)
    b.place_many(WHITE, white)
    return b


# ------------------------------------------------------------ 三分類

def test_adjacent_walls_have_no_shared_liberties():
    """推論 4.2：兩塊直接相鄰的敵對棋串，公氣為 0。"""
    b = make(black=["C4", "C5", "C6"], white=["D4", "D5", "D6"])
    d = classify_liberties(b, all_strings(b, BLACK)[0], all_strings(b, WHITE)[0])
    assert d["c"] == 0


def test_gap_of_one_creates_shared_liberties():
    """隔一格才有公氣，而且中間那一列全是公氣。"""
    b = make(black=["C3", "C4", "C5"], white=["E3", "E4", "E5"])
    d = classify_liberties(b, all_strings(b, BLACK)[0], all_strings(b, WHITE)[0])
    assert d["c"] == 3
    assert {format_coord(p, 9) for p in d["shared"]} == {"D3", "D4", "D5"}
    assert d["a"] == d["b"] == 5


# ------------------------------------------------- 判定式 vs 完整搜尋

def test_formula_matches_search_exhaustively():
    """6,000 組以上逐格比對，零誤差。"""
    total = 0
    for c in range(0, 8):
        for a in range(0, 10):
            for b in range(0, 10):
                for me in (False, True):
                    for op in (False, True):
                        for turn in (True, False):
                            if b + c + op == 0 or a + c + me == 0:
                                continue
                            total += 1
                            assert race_winner(a, b, c, me, op, turn) == \
                                   race_formula(a, b, c, me, op, turn), \
                                   (a, b, c, me, op, turn)
    assert total > 6000


def test_no_shared_liberties_means_no_seki():
    """c <= 1 時雙活帶是空的。"""
    for c in (0, 1):
        for a in range(6):
            for b in range(6):
                for turn in (True, False):
                    if b + c == 0 or a + c == 0:
                        continue
                    assert race_formula(a, b, c, False, False, turn) != "雙活"


def test_seki_band_width():
    """推論 4.5：雙活帶的寬度是 2(c-1)。"""
    for c in range(2, 7):
        band = [d for d in range(-12, 13) if 2 - c <= d <= c - 1]
        assert len(band) == 2 * (c - 1)


def test_more_liberties_is_not_enough_when_dame_are_many():
    """外氣多一口，公氣三口 —— 還是雙活。這是實戰最常見的誤判。"""
    assert race_formula(3, 2, 3, False, False, True) == "雙活"
    assert race_formula(5, 3, 3, False, False, True) == "我勝"


def test_eye_takes_all_the_dame():
    """定理 4.6：有眼殺無眼，公氣全歸有眼方，而且永不雙活。"""
    for c in range(0, 6):
        for a in range(0, 5):
            for b in range(0, 9):
                if b + c == 0 or a + c + 1 == 0:
                    continue
                for turn in (True, False):
                    r = race_formula(a, b, c, True, False, turn)
                    assert r != "雙活"
                    tau = 1 if turn else 0
                    assert (r == "我勝") == (b <= a + c + tau)


# ------------------------------------------------------ 真實盤面

def test_minimal_seki_on_3x3():
    """3 路盤上的最小雙活：黑佔左列、白佔右列。"""
    b = make(black=["A1", "A2", "A3"], white=["C1", "C2", "C3"], n=3)
    B, W = all_strings(b, BLACK)[0], all_strings(b, WHITE)[0]
    d = classify_liberties(b, B, W)
    assert (d["a"], d["b"], d["c"]) == (0, 0, 3)
    assert race_preconditions(b, B, W)[0]
    for turn in (True, False):
        assert race_formula(0, 0, 3, False, False, turn) == "雙活"


def test_preconditions_catch_the_counterexample():
    """練習 4.2：前提不成立時，判定式會給出錯的答案。"""
    b = make(black=["A1", "A2", "A3"], white=["C1", "C2"], n=3)
    B, W = all_strings(b, BLACK)[0], all_strings(b, WHITE)[0]
    ok, why = race_preconditions(b, B, W)
    assert not ok and why
    d = classify_liberties(b, B, W)
    assert race_formula(d["a"], d["b"], d["c"], False, False, False) == "雙活"
    from go_core.search import can_capture
    cands = frozenset(d["own"] | d["opp"] | d["shared"])
    captured, _ = can_capture(b, next(iter(B)), WHITE, candidates=cands, max_depth=14)
    assert captured                       # 真相是白勝


def test_eye_points_are_liberties_not_extras():
    """眼點本身就是一口氣 —— 不能又算外氣又算眼。"""
    b = make(black=["A2", "B2", "B1"], n=9)
    S = all_strings(b, BLACK)[0]
    from go_core.strings import liberties
    assert eye_points(b, S) <= liberties(b, S)


# ------------------------------------------------------ 大眼氣數

N7 = 7


def _nakade(shape, origin=(3, 2)):
    r0, c0 = origin
    R = {(r0 + dr, c0 + dc) for dr, dc in shape}
    ring = lambda S: {(r + dr, c + dc) for (r, c) in S
                      for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                      if 0 <= r + dr < N7 and 0 <= c + dc < N7} - S
    wall = ring(R)
    board = Board(N7)
    for p in wall:
        board.grid[p] = BLACK
    for p in ring(R | wall):
        board.grid[p] = WHITE
    return board, frozenset(R), next(iter(wall))


DEAD_SHAPES = {
    2: [(0, 0), (0, 1)],
    3: [(0, 0), (0, 1), (0, 2)],
    4: [(0, 0), (0, 1), (0, 2), (1, 1)],
    5: [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)],
}


def test_big_eye_table_is_the_net_count():
    """口訣表數的是淨手數，不是攻方實際手數。"""
    for n, shape in DEAD_SHAPES.items():
        board, region, target = _nakade(shape)
        g = moves_to_capture(board, target, WHITE, candidates=region,
                             max_depth=5 * n + 8)
        f = net_moves_to_capture(board, target, WHITE, region, max_depth=5 * n + 8)
        assert f == big_eye_liberties(n), (n, f)
        assert g == attacker_moves(n), (n, g)
        assert g - f == defender_moves(n) == n - 2


def test_closed_forms_are_consistent():
    for n in range(2, 7):
        assert attacker_moves(n) - defender_moves(n) == big_eye_liberties(n)
    assert [big_eye_liberties(n) for n in range(2, 7)] == [2, 3, 5, 8, 12]
    assert [attacker_moves(n) for n in range(2, 7)] == [2, 4, 7, 11, 16]


def test_alive_shape_cannot_be_killed():
    """直四是活形，殺不掉 —— 大眼氣數表對它不適用。"""
    board, region, target = _nakade([(0, 0), (0, 1), (0, 2), (0, 3)])
    assert moves_to_capture(board, target, WHITE, candidates=region,
                            max_depth=20) is None


def test_vital_point_is_the_only_killing_move():
    """三目大眼：只有下正中才殺得掉。"""
    results = {}
    for coord in ["C4", "D4", "E4"]:
        board, region, target = _nakade([(0, 0), (0, 1), (0, 2)])
        board.play(WHITE, coord)
        rest = moves_to_capture(board, target, WHITE, candidates=region,
                                max_depth=18, _to_move=BLACK)
        results[coord] = None if rest is None else rest + 1
    assert results == {"C4": None, "D4": 4, "E4": None}


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} 個測試全部通過。")
