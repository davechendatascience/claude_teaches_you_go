"""第 3 章的計算核心：眼的判定與 Benson 無條件活。

跑法：  python -m pytest tests/ -q      或   python tests/test_ch03_life.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from go_core import BLACK, WHITE, Board, format_coord, find_string   # noqa: E402
from go_core.benson import benson_alive, enclosed_regions, is_vital  # noqa: E402
from go_core.eyes import is_eye_like, is_true_eye, is_false_eye, eye_report  # noqa: E402


def make(black=(), white=(), n=9):
    b = Board(n)
    b.place_many(BLACK, black)
    b.place_many(WHITE, white)
    return b


def alive(board, colour=BLACK):
    return {frozenset(format_coord(p, board.n) for p in ch)
            for ch in benson_alive(board, colour)}


# ---------------------------------------------------------------- 眼的判定

def test_eye_like():
    b = make(black=["A2", "B2", "C2", "B1"])
    assert is_eye_like(b, "A1") == BLACK
    assert is_eye_like(b, "C1") is None          # C1 的鄰點 D1 是空的


def test_true_eye_in_centre_needs_three_diagonals():
    """中央：對方最多佔 1 個對角。d_opp + 0 <= 1。"""
    nbrs = ["E6", "E4", "D5", "F5"]
    # 對方佔 1 個對角 -> 仍是真眼
    b = make(black=nbrs + ["D6", "F6", "D4"], white=["F4"])
    assert is_true_eye(b, "E5", BLACK)
    # 對方佔 2 個對角 -> 假眼
    b = make(black=nbrs + ["D6", "F6"], white=["D4", "F4"])
    assert is_false_eye(b, "E5", BLACK)


def test_true_eye_on_edge_allows_no_enemy_diagonal():
    """邊上：指示函數是 1，所以對方一個對角都不能佔。d_opp + 1 <= 1。"""
    # A5 在左邊緣，鄰點 A4, A6, B5
    b = make(black=["A4", "A6", "B5", "B4", "B6"])
    assert is_true_eye(b, "A5", BLACK)
    b = make(black=["A4", "A6", "B5", "B4"], white=["B6"])
    assert is_false_eye(b, "A5", BLACK)


def test_corner_eye():
    """角上：只有 1 個對角，而且不能被對方佔。"""
    b = make(black=["A2", "B1", "B2"])
    assert is_true_eye(b, "A1", BLACK)
    b = make(black=["A2", "B1"], white=["B2"])
    assert is_false_eye(b, "A1", BLACK)


def test_eye_report_matches_inequality():
    b = make(black=["E6", "E4", "D5", "F5", "D6", "F6"], white=["D4", "F4"])
    r = eye_report(b, "E5")
    assert r["眼位"] and r["對方"] == 2 and r["在邊緣"] is False
    assert r["真眼"] is False


# ------------------------------------------------------- Benson 無條件活

def test_two_one_point_eyes_are_pass_alive():
    b = make(black=["A2", "B2", "C2", "D2", "B1", "D1"])
    assert len(alive(b)) == 1
    regions = enclosed_regions(b, BLACK)
    small = [r for r in regions if len(r) == 1]
    assert len(small) == 2                      # A1 與 C1


def test_one_eye_is_not_pass_alive():
    b = make(black=["A2", "B2", "C2", "B1"])
    assert alive(b) == set()


def test_straight_four_is_alive_but_not_pass_alive():
    """直四是【活】，但不是【虛手也活】—— 它需要應手。

    這是第 3 章 §4.6 最重要的一個區別：Benson 活是活的**充分**條件，不是必要條件。
    """
    b = make(black=["A2", "B2", "C2", "D2", "E1"])
    regions = enclosed_regions(b, BLACK)
    four = [r for r in regions if len(r) == 4]
    assert len(four) == 1                       # 眼位是一個 4 點的區域
    assert is_vital(b, four[0], find_string(b, "A2"))   # 而且它是 vital 的
    assert alive(b) == set()                    # 但只有一個，所以不是 Benson 活


def test_false_eye_group_is_not_pass_alive():
    """假眼的根源：那個眼點周圍是【四個不同的棋串】，不是一塊棋。"""
    b = make(black=["A2", "C2", "B1", "B3"], white=["A1", "C3"])
    assert is_false_eye(b, "B2", BLACK)
    assert alive(b) == set()


def test_two_two_point_eyes_are_pass_alive():
    """眼不必是一個點。兩個【立二】的眼位一樣是 Benson 活。"""
    b = make(black=["A2", "B2", "C2", "D2", "E2", "F2", "C1", "F1"])
    got = alive(b)
    assert len(got) == 1, got                   # {A1,B1} 與 {D1,E1} 兩個 vital 區域


def test_square_four_eyespace_is_not_vital():
    """方四死 —— Benson 的 vital 條件自動抓到了它。

    2x2 眼位的四個點，每一個的鄰點都還在眼位裡面（角點根本不貼牆），
    所以這個區域【不是】vital 的：對手可以走進去而不立刻被提。
    「方四死」這句口訣，就是 vital 這個條件的白話版。
    """
    b = make(black=["A3", "B3", "C1", "C2"])
    regions = enclosed_regions(b, BLACK)
    square = [r for r in regions if len(r) == 4]
    assert len(square) == 1
    assert not is_vital(b, square[0], find_string(b, "A3"))
    assert alive(b) == set()


def test_benson_is_monotone_fixed_point():
    """迭代一定收斂，而且結果只會變小不會變大。"""
    b = make(black=["A2", "B2", "C2", "D2", "B1", "D1"])
    _, log = benson_alive(b, BLACK, trace=True)
    chains = [row["chains"] for row in log]
    assert chains == sorted(chains, reverse=True)
    assert log[-1]["chains"] == log[-2]["chains"] if len(log) > 1 else True


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} 個測試全部通過。")
