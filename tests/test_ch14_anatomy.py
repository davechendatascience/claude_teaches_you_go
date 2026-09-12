"""第 14 章的計算核心：五層的判準、解釋一手棋、成績單、衝突、帳單。

這一章沒有新的定理 —— 它是前十三章的整合，所以測的是「整合有沒有走樣」：
每一層是否真的照它宣稱的定義在提名、沉默是否真的表示「不適用」、
以及書上印出來的那幾個數字（100%、80.2%、9.0%、零敗）是否還對得上。

跑法：  python -m pytest tests/ -q      或   python tests/test_ch14_anatomy.py
"""

import random
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.setrecursionlimit(200000)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest                                                        # noqa: E402

from go_core import BLACK, EMPTY, WHITE, Board, format_coord          # noqa: E402
from go_core.anatomy import (LAYER_NAMES, book_player, coverage,      # noqa: E402
                             explain_game, explain_move,
                             layer1_candidates, layer2_candidates,
                             layer3_candidates, layer4_candidates,
                             layer5_candidates, play_book_game,
                             render_table)
from go_core.attack import is_alive, vital_points                     # noqa: E402
from go_core.eyes import is_eye_like                                  # noqa: E402
from go_core.influence import zobrist_field                           # noqa: E402
from go_core.minimax import legal_moves, move_values                  # noqa: E402
from go_core.score import dame                                        # noqa: E402

from go_core.strings import all_strings, find_string, liberties       # noqa: E402
from go_core.tewari import _board_from_key, reachable_states, solve_all  # noqa: E402

N, MAX_PLY = 3, 15
LAYERS = {1: layer1_candidates, 2: layer2_candidates,
          3: layer3_candidates, 4: layer4_candidates}


# ------------------------------------------------- 全書最貴的一個 fixture

@pytest.fixture(scope="module")
def solved():
    """3 路盤上所有可達局面的答案 + 四層在每個局面的提名。（約 25 秒）"""
    table, _ = solve_all(reachable_states(N, 4), n=N)
    nom, legal_n, best_n = {}, {}, {}
    for key in table:
        b, c, ko = _board_from_key(key, N)
        legal_n[key] = len(legal_moves(b, c, ko))
        best_n[key] = len(table[key][0])
        for k, fn in LAYERS.items():
            nom.setdefault(k, {})[key] = fn(b, c, ko)[0]
    return table, nom, legal_n, best_n


# ------------------------------------------------- 每一層的判準本身

def test_layer1_nominates_max_marginal_liberties():
    """第 1 層宣稱的定義：讓自己【多出】最多氣的點。

    空盤上沒有自己人可以接，所以邊際氣就是落子後那顆子的氣數 ——
    盤心 4 口、邊上 3 口、角上 2 口（第 2 章）。
    """
    b = Board(5)
    s, best = layer1_candidates(b, BLACK)
    assert best == 4
    for p, child, _ in legal_moves(b, BLACK, None):
        libs = len(liberties(child, find_string(child, p)))
        assert (p in s) == (libs == 4)


def test_layer1_marginal_not_absolute():
    """接上一塊已有 4 口氣的棋，邊際氣可能是負的 —— 這正是第 8 章的重點。"""
    b = Board(5)
    b.place(BLACK, "C3")
    _s, best = layer1_candidates(b, BLACK)
    # 落在盤心空地（不接觸 C3）最多也只多 4 口；接在 C3 旁邊反而只多 2 口
    assert best == 4
    child = b.copy()
    child.play(BLACK, "C4")                    # 接上 C3
    delta = len(liberties(child, find_string(child, child._pt("C4")))) - 4
    assert delta == 2 < best


def test_layer1_always_speaks_when_a_move_is_legal():
    """第 1 層永遠開口 —— 每個合法點都有一個氣數，取極大一定取得到。"""
    rng = random.Random(140)
    for _ in range(30):
        b = Board(4)
        for _ in range(rng.randrange(0, 6)):
            pts = [p for p in b.points() if b.grid[p] == EMPTY]
            if not pts:
                break
            try:
                b.play(rng.choice([BLACK, WHITE]), format_coord(rng.choice(pts), 4))
            except ValueError:
                pass
        for colour in (BLACK, WHITE):
            if legal_moves(b, colour, None):
                assert layer1_candidates(b, colour)[0]


def test_layer2_is_silent_when_nothing_is_unsettled():
    """空盤上沒有未定的棋 -> 死活層沒有做活點可以提名。"""
    assert layer2_candidates(Board(5), BLACK)[0] == set()


def test_layer2_only_nominates_vital_points():
    """不變式：第 2 層提名的每個點，都必須是某塊棋的做活點，而且合法。"""
    rng = random.Random(1402)
    spoke = 0

    # 一個一定會讓它開口的局面：白的眼位還沒做完（第 12 章）
    fixed = Board(5)
    fixed.place_many(WHITE, ["A2", "B2", "C2", "D2", "D1"])
    cands, _ = layer2_candidates(fixed, BLACK)
    assert sorted(format_coord(q, 5) for q in cands) == ["B1", "E2"]

    for _ in range(60):
        b = Board(5)
        for _ in range(rng.randrange(2, 10)):
            pts = [q for q in b.points() if b.grid[q] == EMPTY]
            if not pts:
                break
            try:
                b.play(rng.choice([BLACK, WHITE]),
                       format_coord(rng.choice(pts), 5))
            except ValueError:
                pass
        for colour in (BLACK, WHITE):
            cands, _ = layer2_candidates(b, colour)
            if not cands:
                continue
            spoke += 1
            vp = set()
            for c in (BLACK, WHITE):
                for S in all_strings(b, c):
                    vp |= set(vital_points(b, S, c))
            legal = {q for q, _, _ in legal_moves(b, colour, None)}
            assert cands <= vp & legal
    del spoke  # 隨機抽樣不保證抽得到，上面那個固定局面才是保證


def test_layer4_nominates_max_field_sum():
    """第 4 層宣稱的定義：讓自己影響力總和最大的點（第 9 章）。"""
    b = Board(5)
    s, best = layer4_candidates(b, BLACK)
    scores = {}
    for p, child, _ in legal_moves(b, BLACK, None):
        scores[p] = float(zobrist_field(child, 0.8).sum())
    top = max(scores.values())
    assert all(abs(scores[p] - top) < 1e-9 for p in s)
    assert abs(best - top) < 1e-9


def test_layer4_prefers_the_centre_on_an_empty_board():
    """空盤上場一定指天元（第 9 章命題 9.4）。"""
    for n in (3, 5, 7):
        s, _ = layer4_candidates(Board(n), BLACK)
        mid = (n + 1) // 2
        assert s == {Board(n)._pt(f"{chr(ord('A') + mid - 1)}{mid}")}


def test_layer5_is_exactly_the_optimal_moves():
    """第 5 層就是答案本身 —— 它不是判準，是裁判。"""
    b = Board(3)
    b.place_many(BLACK, ["A3", "C3"])
    b.place(WHITE, "B3")
    s, _ = layer5_candidates(b, WHITE, max_ply=MAX_PLY)
    vals = dict(move_values(b, WHITE, komi=0.0, max_ply=MAX_PLY))
    best = min(vals.values())
    assert s == {p for p, v in vals.items() if v == best and p is not None}


# ------------------------------------------------- explain_move / explain_game

def test_explain_move_reports_every_layer():
    b = Board(3)
    rep = explain_move(b, BLACK, b._pt("B2"), with_v=True, max_ply=MAX_PLY)
    assert set(rep) == set(LAYER_NAMES)
    for k, (hit, n_nom, n_legal, _note) in rep.items():
        assert isinstance(hit, bool)
        assert 0 <= n_nom <= n_legal
    assert rep[4][0] is True                    # 空盤天元一定是場的提名


def test_explain_move_hit_means_the_layer_nominated_it():
    b = Board(3)
    b.place_many(BLACK, ["A3", "C3"])
    b.place(WHITE, "B3")
    rep = explain_move(b, WHITE, b._pt("B2"), max_ply=MAX_PLY)
    for k, fn in LAYERS.items():
        assert rep[k][0] == (b._pt("B2") in fn(b, WHITE)[0])


def test_explain_game_handles_passes():
    moves = [(BLACK, "B2"), (WHITE, None), (BLACK, None)]
    rows = explain_game(moves, n=3, with_v=False, max_ply=MAX_PLY)
    assert len(rows) == 3
    assert rows[1]["pass"] is True and rows[1]["coord"] == "虛手"
    assert rows[0]["pass"] is False and rows[0]["coord"] == "B2"
    render_table(rows, n=3)                     # 不應該爆炸


def test_coverage_ignores_passes():
    """虛手沒有層可以解釋，所以它不進分母。"""
    rows = explain_game([(BLACK, "B2"), (WHITE, None), (BLACK, None)],
                        n=3, with_v=False, max_ply=MAX_PLY)
    assert coverage(rows)["total"] == 1


def test_coverage_counts_unexplained_moves():
    moves = [(BLACK, "B2"), (WHITE, "A1")]
    rows = explain_game(moves, n=3, with_v=False, max_ply=MAX_PLY)
    cov = coverage(rows)
    assert cov["total"] == 2
    assert 0 <= cov["unexplained"] <= 2
    for k in LAYERS:
        assert 0.0 <= cov["hit_rate"][k] <= 1.0
        assert 0.0 <= cov["selectivity"][k] <= 1.0


# ------------------------------------------------- 書上印出來的那幾個數字

def test_scorecard_matches_the_book(solved):
    """§4.3 那張成績單。"""
    table, nom, _legal, _best = solved
    assert len(table) == 1742

    spoke, hit = {}, {}
    for k in LAYERS:
        keys = [key for key in table if nom[k][key]]
        spoke[k] = len(keys)
        hit[k] = sum(bool(nom[k][key] & table[key][0]) for key in keys) / len(keys)

    assert spoke[1] == spoke[4] == 1742          # 連通性與場永遠開口
    assert spoke[2] == spoke[3] == 364           # 死活與溫度只在 21%
    assert hit[2] == hit[3] == 1.0               # 開口就沒錯過
    assert round(hit[1], 3) == 0.685
    assert round(hit[4], 3) == 0.865


def test_the_100_percent_is_inflated(solved):
    """§4.3 / 練習 14.2：死活層開口的局面，亂猜也有 80%。

    這是本章寫作時修正自己的地方 —— 這條測試就是那個修正的守門員。
    """
    table, nom, legal_n, best_n = solved
    keys = [k for k in table if nom[2][k]]
    baseline = statistics.mean(best_n[k] / legal_n[k] for k in keys)
    assert 0.79 < baseline < 0.81, baseline
    assert 5.0 < statistics.mean(legal_n[k] for k in keys) < 5.8
    assert 4.0 < statistics.mean(best_n[k] for k in keys) < 4.6

    # 在同一批局面裡，場也有 97.8% —— 死活的優勢只有 8 個局面
    h2 = sum(bool(nom[2][k] & table[k][0]) for k in keys)
    h4 = sum(bool(nom[4][k] & table[k][0]) for k in keys)
    assert h2 == len(keys)
    assert h2 - h4 == 8


def test_life_and_death_never_loses_a_conflict(solved):
    """§4.4：這才是優先序真正的證據。"""
    table, nom, _legal, _best = solved
    losses = Counter()
    diffs = Counter()
    for a, b in [(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)]:
        for key, (best, _v) in table.items():
            sa, sb = nom[a][key], nom[b][key]
            if not sa or not sb or sa == sb:
                continue
            diffs[(a, b)] += 1
            ha, hb = bool(sa & best), bool(sb & best)
            if hb and not ha:
                losses[a] += 1
            elif ha and not hb:
                losses[b] += 1

    assert losses[2] == losses[3] == 0            # 死活／溫度：零敗
    assert diffs[(2, 4)] == diffs[(3, 4)] == 224
    assert diffs[(1, 2)] == diffs[(1, 3)] == 328
    assert losses[1] > 0 and losses[4] > 0        # 另外兩層都輸過


def test_life_and_death_advantage_is_small(solved):
    """零敗，但樣本只有 8 —— 效果量也要進測試，不然只會記得那個 0。"""
    table, nom, _legal, _best = solved
    wins = 0
    for key, (best, _v) in table.items():
        sa, sb = nom[2][key], nom[4][key]
        if not sa or not sb or sa == sb:
            continue
        if (sa & best) and not (sb & best):
            wins += 1
    assert wins == 8


def test_the_bill_is_nine_percent(solved):
    """§4.5：四層一起落空的局面。"""
    table, nom, _legal, _best = solved
    misses = []
    for key, (best, _v) in table.items():
        u = set()
        for k in LAYERS:
            u |= nom[k][key]
        if not (u & best):
            misses.append(key)
    assert round(len(misses) / len(table), 3) == 0.090


def test_the_flagship_miss():
    """§4.5 那個局面：四層全部落空，而且全部說「去提子」。"""
    b = Board(3)
    b.place_many(BLACK, ["A3", "C3"])
    b.place(WHITE, "B3")
    vals = dict(move_values(b, WHITE, komi=0.0, max_ply=MAX_PLY))
    best = min(vals.values())
    winners = {p for p, v in vals.items() if v == best and p is not None}
    assert winners == {b._pt("B2")}

    union = set()
    for fn in LAYERS.values():
        union |= fn(b, WHITE)[0]
    assert not (union & winners)
    assert sorted(format_coord(p, 3) for p in union) == ["A2", "B1", "C2"]
    loss = -(best - min(vals[p] for p in union if p in vals))
    assert loss == 5


# ------------------------------------------------- 照書下棋的那個程式

def test_book_player_never_fills_its_own_eye():
    b = Board(5)
    b.place_many(BLACK, ["A2", "B2", "B1"])       # A1 是黑的眼
    mv, _layer = book_player(b, BLACK, rng=random.Random(0))
    assert mv != b._pt("A1")


def test_book_player_captures_when_it_can():
    b = Board(5)
    b.place(WHITE, "A1")
    b.place(BLACK, "A2")                          # 白 A1 只剩 B1 一口氣
    mv, layer = book_player(b, BLACK, rng=random.Random(0))
    assert format_coord(mv, 5) == "B1"
    assert layer == 2                             # 提子算死活層


def test_book_player_escapes_atari():
    b = Board(5)
    b.place(BLACK, "C3")
    b.place_many(WHITE, ["B3", "C2", "C4"])       # 黑 C3 只剩 D3
    mv, layer = book_player(b, BLACK, rng=random.Random(0))
    assert format_coord(mv, 5) == "D3"
    assert layer == 1                             # 逃 = 連通性


def test_book_player_takes_the_centre_on_an_empty_board():
    mv, layer = book_player(Board(9), BLACK, rng=random.Random(0))
    assert format_coord(mv, 9) == "E5"
    assert layer == 4


def test_book_game_is_reproducible_and_finishes():
    moves, reasons, game = play_book_game(9, max_moves=90,
                                          rng=random.Random(14))
    assert len(moves) == 94
    assert len(dame(game.board)) == 0
    by = Counter(r for r in reasons if r)
    assert by[4] == 64 and by[2] == 15 and by[3] == 6 and by[1] == 5
    assert sum(1 for r in reasons if r == 0) == 4      # 收單官

    again, _r2, _g2 = play_book_game(9, max_moves=90, rng=random.Random(14))
    assert again == moves                              # 同一顆種子，同一局


def test_every_book_move_has_a_layer():
    """book_player 的重點不是強，是【每一手都有一層負責】。"""
    _moves, reasons, _game = play_book_game(7, max_moves=60,
                                            rng=random.Random(7))
    assert all(r in (0, 1, 2, 3, 4) for r in reasons if r is not None)
    assert None not in reasons[:20]                    # 開局不會虛手


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
