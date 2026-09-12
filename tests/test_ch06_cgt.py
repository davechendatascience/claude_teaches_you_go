"""第 6 章的計算核心：組合賽局值、可加性、標準形。

跑法：  python -m pytest tests/ -q      或   python tests/test_ch06_cgt.py
"""

import random
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from go_core import BLACK, EMPTY, WHITE, Board                     # noqa: E402
from go_core.cgt import (DOWN, STAR, UP, ZERO, Game, number,        # noqa: E402
                         simplest_between, switch)
from go_core.endgame import corridor, region_value, territory       # noqa: E402


# ---------------------------------------------------------------- 數

def test_numbers_round_trip():
    for v in [0, 1, 2, -1, -3, Fraction(1, 2), Fraction(1, 4),
              Fraction(3, 4), Fraction(-5, 8)]:
        assert number(v).as_number() == Fraction(v), v


def test_number_arithmetic():
    assert (number(Fraction(1, 2)) + number(Fraction(1, 2))).as_number() == 1
    assert (number(Fraction(1, 4)) + number(Fraction(1, 4))).as_number() == Fraction(1, 2)
    assert (number(3) + number(-3)).as_number() == 0
    assert (number(2) - number(Fraction(1, 2))).as_number() == Fraction(3, 2)


def test_non_dyadic_is_rejected():
    try:
        number(Fraction(1, 3))
    except ValueError:
        return
    raise AssertionError("1/3 不應該被接受")


# ------------------------------------------------------- 簡單性規則

def test_simplicity_rule():
    assert Game([number(0)], [number(2)]).as_number() == 1
    assert Game([number(0)], [number(1)]).as_number() == Fraction(1, 2)
    assert Game([number(0)], [number(Fraction(1, 2))]).as_number() == Fraction(1, 4)
    assert Game([number(Fraction(1, 2))], [number(1)]).as_number() == Fraction(3, 4)
    assert Game([number(-1)], [number(1)]).as_number() == 0


def test_simplest_between_prefers_integers():
    assert simplest_between(Fraction(-3), Fraction(5)) == 0
    assert simplest_between(Fraction(1), Fraction(4)) == 2
    assert simplest_between(Fraction(0), Fraction(1)) == Fraction(1, 2)


# ------------------------------------------------------------ 星、上下

def test_star_is_fuzzy_with_zero():
    assert STAR != ZERO
    assert not (STAR > ZERO) and not (STAR < ZERO)
    assert STAR.outcome() == "先手勝"
    assert ZERO.outcome() == "後手勝"


def test_star_plus_star_is_zero():
    assert STAR + STAR == ZERO
    total = ZERO
    for k in range(1, 8):
        total = total + STAR
        assert (total == ZERO) == (k % 2 == 0), k


def test_up_is_positive_but_infinitesimal():
    assert UP > ZERO
    for k in range(1, 8):
        assert UP < number(Fraction(1, 2 ** k))
    assert UP + DOWN == ZERO
    assert UP.as_number(3, 4) is None          # ↑ 不是數


def test_switch_is_hot():
    for a, b in [(1, 0), (3, -1), (Fraction(1, 2), Fraction(-1, 2))]:
        g = switch(a, b)
        assert g.as_number(3, 6) is None
        assert g.outcome() == "先手勝"


# ------------------------------------------------------------ 標準形

def test_canonical_preserves_value():
    games = [number(Fraction(1, 2)), STAR, UP, switch(1, 0),
             Game([number(0), number(-1)], [number(1)]),
             Game([STAR], [STAR])]
    for g in games:
        assert g.canonical() == g


def test_canonical_simplifies():
    assert Game([number(0), number(-1)], [number(1)]).canonical() == number(Fraction(1, 2))
    assert Game([STAR], [STAR]).canonical() == ZERO


# ------------------------------------------------------------ 盤面

def test_settled_territory_is_an_integer():
    b = Board(9)
    b.place_many(BLACK, ["A4", "B4", "C4", "C3", "C2", "C1"])
    region = ["A1", "A2", "A3", "B1", "B2", "B3"]
    _, _, settled = territory(b, [b.pt(p) for p in region])
    assert settled
    assert region_value(b, region).as_number() == 6


def test_corridor_recursion():
    """C(1) = *，C(n) = {n-1 | C(n-1)} —— 由真實盤面窮舉出來。"""
    vals = {}
    for n in range(1, 6):
        vals[n] = region_value(*corridor(n)).canonical()
    assert vals[1] == STAR
    for n in range(2, 6):
        assert vals[n] == Game([number(n - 1)], [vals[n - 1]]), n


def test_additivity_on_a_real_board():
    """定理 6.4：分開算再相加 == 擺在一起整盤算。"""
    c2 = region_value(*corridor(2)).canonical()
    b = Board(9)
    b.place_many(BLACK, ["A2", "B2", "A8", "B8"])
    b.place_many(WHITE, ["C1", "C2", "C9", "C8"])
    together = region_value(b, ["A1", "B1", "A9", "B9"]).canonical()
    assert (c2 + c2) == together


def test_two_dame_is_miai():
    b = Board(9)
    b.place_many(BLACK, ["A2", "A8"])
    b.place_many(WHITE, ["B1", "B2", "B9", "B8"])
    assert region_value(b, ["A1", "A9"]).canonical() == ZERO


def test_commutativity_on_a_real_board():
    b = Board(9)
    b.place_many(BLACK, ["A2", "B2", "A8", "B8"])
    b.place_many(WHITE, ["C1", "C2", "C9", "C8"])
    one = region_value(b, ["A1", "B1", "A9", "B9"]).canonical()
    two = region_value(b, ["A9", "B9", "A1", "B1"]).canonical()
    assert one == two


def test_no_proper_fractions_in_sampled_positions():
    """§4.5 的普查：真分數 0 個。

    這是一個【搜尋結果】，不是定理 —— 測試也照這個範圍寫。
    """
    random.seed(17)
    kinds = Counter()
    for _ in range(500):
        n = random.choice([4, 5])
        b = Board(n)
        pts = [(r, c) for r in range(n) for c in range(n)]
        for p in pts:
            b.grid[p] = random.choices([EMPTY, BLACK, WHITE], [0.30, 0.36, 0.34])[0]
        empties = [p for p in pts if b.grid[p] == EMPTY]
        if not 1 <= len(empties) <= 4:
            continue
        try:
            g = region_value(b, frozenset(empties), max_depth=8).canonical()
        except Exception:
            continue
        num = g.as_number(3, 6)
        kinds["不是數" if num is None
              else ("整數" if num.denominator == 1 else "真分數")] += 1
    assert sum(kinds.values()) > 50
    assert kinds["整數"] > 0 and kinds["不是數"] > 0
    assert kinds["真分數"] == 0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} 個測試全部通過。")
