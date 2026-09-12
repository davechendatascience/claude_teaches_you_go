"""第 7 章的計算核心：溫度、均值、熱圖、貪婪收官。

跑法：  python -m pytest tests/ -q      或   python tests/test_ch07_temperature.py
"""

import random
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from go_core import BLACK, WHITE, Board                              # noqa: E402
from go_core.cgt import STAR, ZERO, Game, number, switch              # noqa: E402
from go_core.endgame import corridor, region_value                    # noqa: E402
from go_core.temperature import (analyse, deiri, is_settled, mean,     # noqa: E402
                                 miai, play_greedy, play_optimal,
                                 temperature, thermograph)


# ------------------------------------------------------------ 開關

def test_switch_closed_form():
    """命題 7.3：t = (a-b)/2、m = (a+b)/2。"""
    for a, b in [(4, 0), (1, 0), (3, -1), (6, 0), (4, -2), (10, 9)]:
        t, m = analyse(switch(a, b))
        assert t == Fraction(a - b, 2), (a, b, t)
        assert m == Fraction(a + b, 2), (a, b, m)


def test_numbers_have_zero_temperature():
    for v in [0, 3, -5, Fraction(1, 2)]:
        assert temperature(number(v)) == 0
        assert mean(number(v)) == Fraction(v)


def test_star_has_zero_temperature_but_is_not_a_number():
    assert temperature(STAR) == 0
    assert mean(STAR) == 0
    assert not is_settled(STAR)          # * 不是數
    assert is_settled(ZERO)


# ------------------------------------------------------------ 走廊

def test_corridor_closed_forms():
    """t(C(n)) = 1 - 2^-(n-1)、m(C(n)) = n - 2 + 2^-(n-1)。"""
    for n in range(1, 6):
        g = region_value(*corridor(n)).canonical()
        t, m = analyse(g)
        assert t == 1 - Fraction(1, 2 ** (n - 1)), (n, t)
        assert m == n - 2 + Fraction(1, 2 ** (n - 1)), (n, m)


def test_corridor_temperature_approaches_one_from_below():
    ts = [temperature(region_value(*corridor(n)).canonical()) for n in range(1, 7)]
    assert all(t < 1 for t in ts)
    assert ts == sorted(ts)              # 遞增
    assert ts[-1] == Fraction(31, 32)       # C(6)：1 - 2^-5


# ------------------------------------------------------------ 熱圖

def test_thermograph_walls_meet_at_temperature():
    g = switch(4, 0)
    t, m = analyse(g)
    pts = dict((x, (l, r)) for x, l, r in
               thermograph(g, [Fraction(k, 2) for k in range(0, 9)]))
    for x, (l, r) in pts.items():
        if x < t:
            assert l > r, (x, l, r)      # 還沒相碰
            assert l == 4 - x and r == 0 + x
        else:
            assert l == r == m, (x, l, r)


def test_thermograph_kink_is_the_followup_temperature():
    """C(3) 的右牆在 t(C(2)) 轉折 —— 轉折點就是後續手段的溫度。"""
    c2 = region_value(*corridor(2)).canonical()
    c3 = region_value(*corridor(3)).canonical()
    t2 = temperature(c2)
    walls = dict((x, r) for x, l, r in
                 thermograph(c3, [Fraction(k, 8) for k in range(9)]))
    for x in [Fraction(k, 8) for k in range(0, 5)]:      # t <= 1/2
        assert walls[x] == 1, (x, walls[x])              # 平的
    assert walls[Fraction(5, 8)] > 1                     # 過了 t2 開始上升
    assert t2 == Fraction(1, 2)


# ------------------------------------------------------ 出入 vs 見合

def test_deiri_is_twice_miai():
    games = [switch(6, 0), switch(4, -2), switch(1, 0),
             region_value(*corridor(3)).canonical()]
    for g in games:
        assert deiri(g) == 2 * miai(g)
        assert miai(g) == temperature(g)


def test_same_deiri_can_differ_in_mean():
    p, q = switch(6, 0), switch(4, -2)
    assert deiri(p) == deiri(q) == 6
    assert temperature(p) == temperature(q) == 3
    assert mean(p) == 3 and mean(q) == 1       # 溫度相同，均值不同


# ------------------------------------------------------------ 收官

def _endgame_board():
    b = Board(9)
    b.place_many(BLACK, ["A2", "B2", "A8", "B8", "C8", "H1", "H2"])
    b.place_many(WHITE, ["C1", "C2", "D9", "D8", "J3", "H3"])
    return b


def test_worked_endgame():
    """§5.1 的盤面：均值 9/4、黑先 3、白先 2。"""
    b = _endgame_board()
    games = [region_value(b, r).canonical()
             for r in (["A1", "B1"], ["A9", "B9", "C9"], ["J1", "J2"])]
    assert [str(temperature(g)) for g in games] == ["1/2", "3/4", "1/2"]
    assert sum(mean(g) for g in games) == Fraction(9, 4)
    assert play_optimal(games, "black") == 3
    assert play_optimal(games, "white") == 2
    for first in ("black", "white"):
        assert play_greedy(games, first)[0] == play_optimal(games, first)


def test_greedy_is_optimal_on_real_go_locals():
    """實驗一：走廊與開關組成的盤面，貪婪法就是最優解。"""
    pool = [region_value(*corridor(n)).canonical() for n in range(1, 5)]
    pool += [switch(a, b) for a, b in [(1, 0), (2, 0), (3, 1), (4, 0), (2, -2)]]
    rng = random.Random(11)
    for _ in range(60):
        games = [rng.choice(pool) for _ in range(rng.randint(2, 4))]
        for first in ("black", "white"):
            assert play_greedy(games, first)[0] == play_optimal(games, first)


def _rnd_game(depth, rng):
    if depth == 0 or rng.random() < 0.35:
        return number(rng.randint(-4, 4))
    return Game([_rnd_game(depth - 1, rng) for _ in range(rng.randint(1, 2))],
                [_rnd_game(depth - 1, rng) for _ in range(rng.randint(1, 2))])


def test_greedy_error_is_bounded_by_tmax():
    """實驗三：落差 <= t_max。

    上界【是緊的】這件事由 test_the_tight_counterexample 用一個確定的例子驗，
    這裡只驗上界本身 —— 隨機取樣要跑到上千組才碰得到緊的例子，太慢。
    """
    rng = random.Random(23)
    saw_any_gap = False
    for _ in range(400):
        games = [_rnd_game(rng.randint(1, 3), rng).canonical()
                 for _ in range(rng.randint(2, 3))]
        if all(is_settled(g) for g in games):
            continue
        tmax = max(temperature(g) for g in games)
        for first in ("black", "white"):
            g = play_greedy(games, first)[0]
            o = play_optimal(games, first)
            d = (o - g) if first == "black" else (g - o)
            assert d <= tmax, (d, tmax)
            if d > 0:
                saw_any_gap = True
    assert saw_any_gap, "應該找得到貪婪法不是最優的例子"


def test_the_tight_counterexample():
    """§4.6 那個落差剛好 = t_max 的例子。"""
    inner = switch(1, -4)
    tricky = Game([number(2)], [inner])
    games = [switch(1, -1), tricky, switch(4, 2)]
    assert all(temperature(g) == 1 for g in games)
    assert temperature(inner) == Fraction(5, 2)     # 後續比全局溫度還燙 -> 先手
    g = play_greedy(games, "black")[0]
    o = play_optimal(games, "black")
    assert o - g == 1 == max(temperature(x) for x in games)


def test_option_criterion_matters():
    """在局部裡挑哪一手，用均值挑會比用熱圖挑差。"""
    rng = random.Random(23)
    bad = {"mean": 0, "thermograph": 0}
    for _ in range(300):
        games = [_rnd_game(rng.randint(1, 3), rng).canonical()
                 for _ in range(rng.randint(2, 3))]
        if all(is_settled(g) for g in games):
            continue
        for first in ("black", "white"):
            o = play_optimal(games, first)
            for by in ("mean", "thermograph"):
                g = play_greedy(games, first, by=by)[0]
                d = (o - g) if first == "black" else (g - o)
                if d > 0:
                    bad[by] += 1
    assert bad["mean"] >= bad["thermograph"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} 個測試全部通過。")
