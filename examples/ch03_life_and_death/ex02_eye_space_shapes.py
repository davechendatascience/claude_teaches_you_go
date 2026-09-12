#!/usr/bin/env python
"""第 3 章配套範例 2：用程式重新推導那張死活口訣表。

對應章節：第 3 章 §4.4、§4.6。

「直三死、直四活、曲四活、方四死、丁四死」—— 這是每一本圍棋書都會列、
卻沒有一本會證明的一張表。這支腳本把它算出來。

做法：給定一個眼位空間的形狀，自動幫它砌一圈實心的圍牆（wall = N(R) \\ R），
然後問三個層次的問題：

    Q1  現在就是 Benson 活嗎？                       （虛手也活）
    Q2  防守方先下一手，能變成 Benson 活嗎？          （先手做活）
    Q3  進攻方先下一手，防守方再下一手，還能嗎？      （被點之後還活不活）

Q3 的答案，就是那張口訣表。

【誠實聲明】Q3 只往下看【兩手】（進攻一手、防守一手）。這對 3、4、5 點的眼位
空間剛好夠用，跑出來的答案和口訣表逐條吻合。但六點以上就不夠了 ——
板六需要往下看四手以上，而這支腳本會把它誤判成死。那不是 Benson 錯了，
是這個 2 手模型的深度不夠。完整的死活搜尋要等第 4 章的 AND-OR 樹。

跑法（在專案根目錄）：
    python examples/ch03_life_and_death/ex02_eye_space_shapes.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, WHITE, Board, neighbors, format_coord   # noqa: E402
from go_core.benson import benson_alive, enclosed_regions, is_vital  # noqa: E402
from go_core.strings import all_strings                            # noqa: E402

N = 9


def build(shape, origin=(0, 0)):
    """把一個形狀擺在角上，並自動砌一圈實心圍牆。

    shape 用相對座標 (dr, dc) 給，(0,0) 是最靠角的那一點。
    回傳 (board, 眼位空間的絕對座標集合)。
    """
    r0, c0 = origin
    region = {(r0 + dr, c0 + dc) for dr, dc in shape}
    # 圍牆要【實心】：只取上下左右的鄰點，四個角會漏掉，牆會裂成好幾塊。
    # 所以取 Chebyshev 距離 1（含對角）以內的所有點。
    wall = {(r + dr, c + dc)
            for (r, c) in region
            for dr in (-1, 0, 1) for dc in (-1, 0, 1)
            if (r + dr, c + dc) not in region
            and 0 <= r + dr < N and 0 <= c + dc < N}
    b = Board(N)
    for p in wall:
        b.grid[p] = BLACK
    return b, region


def n_vital(board, region_pts):
    """這塊棋目前有幾個 vital 區域（取最多的那個棋串）。"""
    regions = [r for r in enclosed_regions(board, BLACK) if len(r) <= 8]
    best = 0
    for ch in all_strings(board, BLACK):
        best = max(best, sum(1 for r in regions if is_vital(board, r, ch)))
    return best


def pass_alive(board):
    return len(benson_alive(board, BLACK)) > 0


def q2_defender_first(board, region):
    """防守方先下一手，能不能達到 Benson 活？回傳成功的著點。"""
    ok = []
    for p in region:
        if board.grid[p] != 0:
            continue
        t = board.copy()
        t.grid[p] = BLACK
        if pass_alive(t):
            ok.append(format_coord(p, N))
    return sorted(ok)


def q3_attacker_first(board, region):
    """進攻方先下一手，防守方再下一手 —— 防守方守得住嗎？

    回傳 (守得住嗎, 進攻方的最佳點)。守不住表示這個形狀被點就死。
    """
    worst = None
    attacker_has_a_move = False
    for a in region:
        if board.grid[a] != 0:
            continue
        after = board.copy()
        try:
            after.play(WHITE, a)
        except ValueError:
            continue                      # 這一點對白而言是禁著點，白下不了
        attacker_has_a_move = True
        # 防守方回應：可以下在眼位空間裡的任何空點
        saved = False
        for d in region:
            if after.grid[d] != 0:
                continue
            t = after.copy()
            try:
                t.play(BLACK, d)
            except ValueError:
                continue
            if pass_alive(t):
                saved = True
                break
        if not saved:
            worst = format_coord(a, N)
            return False, worst
    if not attacker_has_a_move:
        # 進攻方在眼位空間裡一手都下不了（每一點都是禁著點）——
        # 那麼安不安全，就看這個盤面本身是不是已經無條件活。
        # 一點眼就是這種情況：白下不進去，但這塊棋只有一個眼，仍然不活。
        return pass_alive(board), None
    return True, None                     # 每一手進攻都擋得住


SHAPES = [
    ("一點眼",   [(0, 0)]),
    ("直二",     [(0, 0), (0, 1)]),
    ("直三",     [(0, 0), (0, 1), (0, 2)]),
    ("曲三",     [(0, 0), (0, 1), (1, 1)]),
    ("直四",     [(0, 0), (0, 1), (0, 2), (0, 3)]),
    ("曲四",     [(0, 0), (0, 1), (0, 2), (1, 2)]),
    ("方四",     [(0, 0), (0, 1), (1, 0), (1, 1)]),
    ("丁四",     [(0, 0), (0, 1), (0, 2), (1, 1)]),
    ("直五",     [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)]),
    ("刀把五",   [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2)]),
    ("花五",     [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)]),
    ("板六",     [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]),
]


def main():
    print("=" * 78)
    print("死活口訣表，用 Benson 重新算一遍")
    print("=" * 78)
    print("  眼位空間擺在中央（自動砌一圈實心圍牆），三個問題：")
    print("    Q1 現在就是 Benson 活嗎（虛手也活）")
    print("    Q2 防守方先下一手，能達到 Benson 活嗎")
    print("    Q3 進攻方先下一手、防守方再一手，守得住嗎  <- 這一欄就是那張口訣表")
    print()
    hdr = f"{'形狀':<8}{'點數':>4}{'vital':>7}{'Q1':>5}{'Q2 的著點':>18}{'Q3':>6}  傳統說法"
    print(hdr)
    print("-" * 78)

    said = {
        "一點眼": "一個眼不活", "直二": "二目不活", "直三": "直三死", "曲三": "曲三死",
        "直四": "直四活", "曲四": "曲四活", "方四": "方四死", "丁四": "丁四死",
        "直五": "直五活", "刀把五": "刀把五死", "花五": "花五死", "板六": "板六活",
    }
    results = {}
    for label, shape in SHAPES:
        b, region = build(shape, origin=(3, 3))       # 擺在中央，四面都有空間砌牆
        v = n_vital(b, region)
        q1 = pass_alive(b)
        q2 = q2_defender_first(b, region)
        q3, killer = q3_attacker_first(b, region)
        results[label] = (v, q1, bool(q2), q3)
        q2s = ("、".join(q2) if q2 else "無") if not q1 else "（已經活了）"
        print(f"{label:<8}{len(shape):>4}{v:>7}{'活' if q1 else '否':>5}"
              f"{q2s:>18}{'守得住' if q3 else '死':>6}  {said[label]}")

    print()
    print("  五點以內，Q3 那一欄和最右邊那一欄逐條吻合 —— 那張背了幾十年的表，")
    print("  是「兩個 vital 區域」這個條件在各種形狀上的展開。")
    print()
    print("  唯一對不上的是【板六】。那不是 Benson 錯了，是這個模型只看兩手：")
    print("  板六要往下看四手以上（而且傳統的板六是貼著邊的，這裡擺在中央）。")
    print("  這正是第 4 章要處理的事 —— 死活的一般情況需要一棵 AND-OR 搜尋樹，")
    print("  而不是固定深度的窮舉。")
    print()
    print("  三個層次的差別也很清楚：")
    print("    直四  Q1 否、Q2 可、Q3 守得住   -> 活，但欠一手")
    print("    直三  Q1 否、Q2 可、Q3 死       -> 只有搶到先手才活，被點就死")
    print("    方四  Q1 否、Q2 不可、Q3 死     -> 連先手都救不了（一手切不開 2x2）")

    # 那張口訣表（五點以內）
    assert results["直四"][3] is True and results["曲四"][3] is True
    assert results["直五"][3] is True
    assert results["刀把五"][3] is False and results["花五"][3] is False
    assert results["直三"][3] is False and results["曲三"][3] is False
    assert results["方四"][3] is False and results["丁四"][3] is False
    # 方四連「防守方先下一手」都救不了
    assert results["方四"][2] is False
    # 直三可以靠先手做活，方四不行 —— 兩者都「死」，但死得不一樣
    assert results["直三"][2] is True
    # 板六：模型深度不足，會誤判成死。明確斷言這個【已知的失效】，免得它被忘記。
    assert results["板六"][3] is False, "板六在 2 手模型下應該被誤判成死"

    print("\n全部斷言通過（含板六那個已知的誤判）。")


if __name__ == "__main__":
    main()
