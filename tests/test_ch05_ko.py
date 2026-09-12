"""第 5 章的計算核心：狀態圖裡的環、三種劫規則、劫爭判定式。

跑法：  python -m pytest tests/ -q      或   python tests/test_ch05_ko.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from go_core import BLACK, WHITE, Board, format_coord                 # noqa: E402
from go_core.ko import (GameState, IllegalMove, find_cycle,           # noqa: E402
                        ko_fight, ko_fight_rule, max_game_length)

C = "ABCDEFGHJ"


def ko_stones(col, row, taker=BLACK):
    c = C.index(col)
    P = lambda dc, dr: f"{C[c + dc]}{row + dr}"
    three = [P(1, 2), P(0, 1), P(1, 0)]
    four = [P(2, 2), P(1, 1), P(3, 1), P(2, 0)]
    return (three, four, P(1, 1), P(2, 1)) if taker == BLACK \
        else (four, three, P(1, 1), P(2, 1))


def build(spots, n=9):
    b, pts = Board(n), []
    for col, row, taker in spots:
        blk, wht, victim, kopt = ko_stones(col, row, taker)
        b.place_many(BLACK, blk)
        b.place_many(WHITE, wht)
        pts += [victim, kopt]
    return b, pts


SINGLE = [("C", 4, BLACK)]
TRIPLE = [("A", 1, BLACK), ("F", 1, WHITE), ("A", 6, BLACK)]
TRIPLE_SAME = [("A", 1, BLACK), ("F", 1, BLACK), ("A", 6, BLACK)]


def cycle_len(spots, rule):
    b, pts = build(spots)
    c = find_cycle(GameState(b, rule=rule, to_move=BLACK), pts, max_len=10)
    return len(c) if c else 0


# ------------------------------------------------------------ 環

def test_single_ko_is_a_two_cycle_without_any_rule():
    assert cycle_len(SINGLE, "none") == 2


def test_basic_ko_rule_stops_the_single_ko():
    assert cycle_len(SINGLE, "basic") == 0


def test_basic_ko_rule_does_not_stop_the_triple_ko():
    """本章的核心事實：基本劫規擋得住 2-環，擋不住 6-環。"""
    assert cycle_len(TRIPLE, "basic") == 6


def test_superko_stops_everything():
    for rule in ("positional", "situational"):
        assert cycle_len(SINGLE, rule) == 0
        assert cycle_len(TRIPLE, rule) == 0


def test_three_kos_facing_the_same_way_have_no_cycle():
    """循環需要方向【交替】，否則有一方無子可提。"""
    assert cycle_len(TRIPLE_SAME, "basic") == 0
    assert cycle_len(TRIPLE_SAME, "none") == 2      # 單一個劫仍然有 2-環


def test_superko_blocks_the_sixth_move():
    b, pts = build(TRIPLE)
    cycle = find_cycle(GameState(b, rule="basic", to_move=BLACK), pts, max_len=10)
    st = GameState(b, rule="situational", to_move=BLACK)
    played = 0
    for colour, p in cycle:
        try:
            st.play(colour, p)
            played += 1
        except IllegalMove:
            break
    assert played == 5


# ------------------------------------------------- 單劫在三種規則下一致

def test_all_rules_agree_on_a_single_ko():
    for rule in ("basic", "positional", "situational"):
        b, _ = build(SINGLE)
        st = GameState(b, rule=rule, to_move=BLACK)
        st.play(BLACK, "E5")
        try:
            st.copy().play(WHITE, "D5")
            immediate_ok = True
        except IllegalMove:
            immediate_ok = False
        assert not immediate_ok, rule            # 立刻回提：不行
        st.play(WHITE, "A1")
        st.play(BLACK, "A9")
        st.play(WHITE, "D5")                     # 下完別處再回提：可以


# ------------------------------------------------------------ 終止性

def test_termination_bound():
    assert max_game_length(3) == 3 ** 9
    assert max_game_length(19) == 3 ** 361
    assert max_game_length(9) > 10 ** 38


# ------------------------------------------------------------ 劫爭

def test_threat_threshold():
    """t >= K 是一道懸崖，不是斜坡。"""
    assert ko_fight_rule([15, 10], [20], 10, False) == "打贏劫"
    assert ko_fight_rule([15, 9], [20], 10, False) == "打輸劫"


def test_formula_matches_simulation():
    random.seed(3)
    for _ in range(20000):
        K = random.randint(1, 20)
        mine = [random.randint(1, 30) for _ in range(random.randint(0, 6))]
        his = [random.randint(1, 30) for _ in range(random.randint(0, 6))]
        for hold in (True, False):
            assert ko_fight(K, mine, his, hold)[0] == ko_fight_rule(mine, his, K, hold)


def test_holding_the_ko_is_worth_one_threat():
    """劫在我手上時平手也算我贏；在他手上時我得多一個。"""
    for m in range(4):
        for h in range(4):
            mine, his = [100] * m, [100] * h
            assert (ko_fight_rule(mine, his, 10, True) == "打贏劫") == (m >= h)
            assert (ko_fight_rule(mine, his, 10, False) == "打贏劫") == (m > h)


def test_all_dominating_ko():
    """天下劫：K 大到沒有任何一手夠格 -> 劫在誰手上誰贏。"""
    assert ko_fight_rule([30, 25], [28, 27], 100, True) == "打贏劫"
    assert ko_fight_rule([30, 25], [28, 27], 100, False) == "打輸劫"


def test_additivity_fails():
    """§4.6：別處多一個局部，這裡的劫就翻盤 —— 而那個局部本身沒變。"""
    K = 10
    assert ko_fight_rule([], [], K, True) == "打贏劫"
    assert ko_fight_rule([], [12], K, True) == "打輸劫"     # 別處多一個 >= K 的局部
    assert ko_fight_rule([], [9], K, True) == "打贏劫"      # 9 < K，沒有影響


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} 個測試全部通過。")
