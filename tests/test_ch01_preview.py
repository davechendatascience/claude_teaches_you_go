"""第 1 章的規則示範與那一局 7 路棋。

第 1 章沒有自己的計算模組（它用的全是後面章節的東西），所以這裡測的是
**書上印出來的每一個數字**：三條半規則的示範盤面、以及 §5 那一局的
子數、地、提子、手數與兩種計分。

那一局的關鍵性質是 b = w = 27，所以 C = J 是【必然】而不是巧合
（第 13 章定理 13.2）。如果 book_player 或計分改動讓這一局變了，
第 1 章的正文就會對不上 —— 這個檔案的工作就是讓那件事立刻爆掉。

跑法：  python -m pytest tests/ -q      或   python tests/test_ch01_preview.py
"""

import random
import sys
from pathlib import Path

sys.setrecursionlimit(200000)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest                                                        # noqa: E402

from go_core import BLACK, WHITE, Board, format_coord                # noqa: E402
from go_core.anatomy import play_book_game                           # noqa: E402
from go_core.score import (chinese_score, dame, japanese_score,      # noqa: E402
                           stones, territory, tromp_taylor_score)
from go_core.strings import find_string, liberties                   # noqa: E402

N, SEED = 7, 2


@pytest.fixture(scope="module")
def game():
    moves, _reasons, g = play_book_game(N, max_moves=70,
                                        rng=random.Random(SEED))
    real = [(c, m) for c, m in moves if m is not None]
    return real, g


# ------------------------------------------------- §4.1 棋盤

def test_degree_is_two_three_or_four():
    """角 2、邊 3、其餘 4 —— 整本書的地基（§4.1）。"""
    b = Board(N)
    for coord, want in [("A1", 2), ("A7", 2), ("G1", 2), ("G7", 2),
                        ("A4", 3), ("D1", 3), ("G4", 3), ("D7", 3),
                        ("D4", 4), ("B2", 4), ("F6", 4)]:
        t = Board(N)
        t.place(BLACK, coord)
        assert len(liberties(t, find_string(t, t._pt(coord)))) == want, coord
    assert b.n * b.n == 49


# ------------------------------------------------- §4.2 氣與提子

def test_a_string_shares_its_liberties():
    """兩顆連在一起的子算【一塊】的氣，不是各算各的（練習 1.1）。"""
    b = Board(N)
    b.place_many(WHITE, ["D4", "D5"])
    b.place_many(BLACK, ["C4", "C5", "E4", "E5", "D6"])
    S = find_string(b, b._pt("D4"))
    assert len(S) == 2
    assert sorted(format_coord(p, N) for p in liberties(b, S)) == ["D3"]


def test_capture_is_automatic():
    """氣歸零就拿走 —— 不是玩家的選擇（§4.2）。"""
    b = Board(N)
    b.place(WHITE, "D4")
    b.place_many(BLACK, ["C4", "E4", "D5"])
    taken = b.play(BLACK, "D3")
    assert sorted(format_coord(p, N) for p in taken) == ["D4"]
    assert b.grid[b._pt("D4")] == 0


def test_capture_takes_the_whole_string():
    b = Board(N)
    b.place_many(WHITE, ["D4", "D5"])
    b.place_many(BLACK, ["C4", "C5", "E4", "E5", "D6"])
    assert len(b.play(BLACK, "D3")) == 2


# ------------------------------------------------- §4.3 地

def test_territory_needs_both_colours_on_the_board():
    """§4.3 的示範盤面：黑 6 點、白 4 點、其餘 28 點誰的也不是。"""
    b = Board(N)
    b.place_many(BLACK, ["A4", "B4", "C4", "C3", "C2", "C1"])
    b.place_many(WHITE, ["E7", "E6", "E5", "F5", "G5"])
    tb, tw = territory(b)
    assert (tb, tw) == (6, 4)
    assert len(dame(b)) == 28
    assert tb + tw + len(dame(b)) + 6 + 5 == N * N


def test_exercise_1_2():
    b = Board(N)
    b.place_many(BLACK, ["A5", "B5", "C5", "C4", "C3", "C2", "C1"])
    b.place_many(WHITE, ["E1", "E2", "E3", "F3", "G3"])
    assert territory(b) == (8, 4)
    assert len(dame(b)) == 25
    assert 8 + 4 + 25 + 7 + 5 == N * N


# ------------------------------------------------- §5 那一局棋

def test_the_first_game_is_reproducible(game):
    real, _g = game
    again, _r2, _g2 = play_book_game(N, max_moves=70, rng=random.Random(SEED))
    assert [(c, m) for c, m in again if m is not None] == real


def test_the_first_game_numbers_match_the_chapter(game):
    real, g = game
    b_moves = sum(1 for c, _m in real if c == BLACK)
    w_moves = len(real) - b_moves
    r = g.report()

    assert len(real) == 54
    assert b_moves == w_moves == 27
    assert stones(g.board) == (26, 13)
    assert territory(g.board) == (8, 2)
    assert r["prisoners"] == (14, 1)
    assert len(dame(g.board)) == 0
    assert 26 + 13 + 8 + 2 == N * N            # 守恆


def test_both_rules_agree_because_the_move_counts_agree(game):
    real, g = game
    b_moves = sum(1 for c, _m in real if c == BLACK)
    w_moves = len(real) - b_moves
    pb, pw = g.report()["prisoners"]

    C = chinese_score(g.board)
    J = japanese_score(g.board, prisoners_black=pb, prisoners_white=pw)
    assert C == J == 19.0
    assert C - J == b_moves - w_moves == 0
    assert tromp_taylor_score(g.board) == C     # 無死子、無單官時三者一致


def test_the_identity_survives_unequal_move_counts():
    """C - J = b - w 在手數不同的局面也要成立（練習 1.4）。"""
    unequal = 0
    for seed in range(1, 6):
        moves, _r, g = play_book_game(N, max_moves=70, rng=random.Random(seed))
        real = [(c, m) for c, m in moves if m is not None]
        b_n = sum(1 for c, _m in real if c == BLACK)
        w_n = len(real) - b_n
        rep = g.report()
        assert rep["chinese"] - rep["japanese"] == b_n - w_n
        unequal += b_n != w_n
    assert unequal >= 1, "五個種子全是等手數，這條測試沒測到重點"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
