#!/usr/bin/env python
"""第 10 章配套範例 1：把一個棋盤真的解開。（跑完約需一到兩分鐘）

對應章節：第 10 章 §4.1、§4.2、§4.3。

四件事：

1. **2 路盤沒有值。** 只用基本劫規時，V 隨手數上限以週期 6 震盪，永遠不收斂。
   而 2 路盤狀態圖裡最短的純落子環恰好是 6 手 —— 正是第 5 章說「基本劫規
   擋不住」的那個 6-環。Zermelo 定理的「有限」前提在這裡真的破了。

2. **3 路盤解得開。** V = +9，黑拿走整個棋盤，最佳第一手是天元。
   每一手的失分：天元 0、邊 -5、角 -18 —— 而 -18 也正是虛手的失分。

3. **剪枝值 58 倍。** 同一個答案，alpha-beta 讓節點從 556,948 降到 9,591。

4. **4 路盤已經不行了。** 同一支程式，手數上限才 8 就要跑十幾秒，
   而它需要 20 以上才可能收斂。

跑法（在專案根目錄）：
    python examples/ch10_value/ex01_solve_3x3.py
"""

import sys
import time
from collections import deque
from pathlib import Path

sys.setrecursionlimit(100000)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import BLACK, WHITE, Board, format_coord, opposite      # noqa: E402
from go_core.minimax import (Solver, area_score, legal_moves,         # noqa: E402
                             move_values)

MAX_PLY = 15


# ------------------------------------------------------------ 1. 2 路盤

def shortest_move_cycle(n=2):
    """在狀態圖（含輪次與劫點）裡找最短的【純落子】有向環。"""
    start = (Board(n), BLACK, None)
    sig = lambda b, c, ko: (b.grid.tobytes(), c, ko)
    edges, nodes = {}, {sig(*start)}
    Q = deque([start])
    while Q:
        b, c, ko = Q.popleft()
        k = sig(b, c, ko)
        edges[k] = []
        for p, child, nk in legal_moves(b, c, ko):
            s2 = sig(child, opposite(c), nk)
            edges[k].append((p, s2))
            if s2 not in nodes:
                nodes.add(s2)
                Q.append((child, opposite(c), nk))
        s2 = sig(b, opposite(c), None)              # 虛手
        edges[k].append((None, s2))
        if s2 not in nodes:
            nodes.add(s2)
            Q.append((b, opposite(c), None))

    best = None
    for src in nodes:
        dist, par = {src: 0}, {}
        Q2 = deque([src])
        while Q2:
            u = Q2.popleft()
            for mv, v in edges.get(u, []):
                if mv is None:
                    continue                        # 虛手造成的環是平凡的
                if v == src:
                    if best is None or dist[u] + 1 < best[0]:
                        path, x = [], u
                        while x != src:
                            path.append(par[x])
                            x = par[x][0]
                        best = (dist[u] + 1, src, list(reversed(path)) + [(u, mv)])
                    continue
                if v not in dist:
                    dist[v] = dist[u] + 1
                    par[v] = (u, mv)
                    Q2.append(v)
        if best and best[0] <= 6:
            break
    return len(nodes), best


def two_by_two():
    print("=" * 66)
    print("1. 2 路盤：只有基本劫規時，V 永遠不收斂")
    print("=" * 66)
    vals = []
    for ply in range(4, 27, 2):
        s = Solver(komi=0.0, max_ply=ply)
        v, _ = s.search(Board(2), BLACK)
        vals.append(int(v))
    print("  手數上限 4, 6, 8, ..., 26 時的 V：")
    print("   ", vals)
    assert vals == [-1, 0, 0] * 4
    print("  -> 週期 6，永遠不收斂")

    n_states, (length, _, moves) = shortest_move_cycle(2)
    print(f"\n  2 路盤的狀態圖（含輪次與劫點）共 {n_states} 個狀態")
    print(f"  最短的【純落子】有向環：{length} 手")
    print("  環上的著手：", " ".join(format_coord(mv, 2) for _, mv in moves))
    assert length == 6
    print("\n  震盪的週期 = 環的長度 = 6。")
    print("  第 5 章規則 5.4：基本劫規擋 2-環，擋不住 6-環。")
    print("  於是 Zermelo 的『有限』前提破了 —— 2 路圍棋【沒有值】。")


# ------------------------------------------------------------ 2. 3 路盤

def three_by_three():
    print("\n" + "=" * 66)
    print("2. 3 路盤：解得開")
    print("=" * 66)
    print(f"  {'手數上限':>8}{'V':>6}{'最佳著':>8}{'節點':>10}")
    for ply in [9, 11, 13, 15, 19, 23]:
        s = Solver(komi=0.0, max_ply=ply)
        v, mv = s.search(Board(3), BLACK)
        name = format_coord(mv, 3) if mv else "虛手"
        print(f"  {ply:>8}{v:>+6.0f}{name:>8}{s.nodes:>10}")
    print("  -> 手數上限 13 以後穩定在 +9：黑拿走整個棋盤")

    print("\n  每一手的失分（delta_V）：")
    vals = dict(move_values(Board(3), BLACK, komi=0.0, max_ply=MAX_PLY))
    best = max(vals.values())
    for name, pts in [("天元", [(1, 1)]),
                      ("邊", [(0, 1), (1, 0), (1, 2), (2, 1)]),
                      ("角", [(0, 0), (0, 2), (2, 0), (2, 2)])]:
        losses = {best - vals[p] for p in pts}
        assert len(losses) == 1, (name, losses)
        print(f"    {name:<4} delta_V = {losses.pop():>3.0f}")
    print(f"    虛手   delta_V = {best - vals[None]:>3.0f}")
    assert best == 9
    assert best - vals[(1, 1)] == 0
    assert best - vals[(0, 1)] == 5
    assert best - vals[(0, 0)] == 18 == best - vals[None]
    print("  -> 第一手下角落和直接虛手一樣糟（都是 -18）")
    print(f"\n  公平貼目 = V(空盤) = {best}")

    # 最優對局
    s = Solver(komi=0.0, max_ply=MAX_PLY)
    b, colour, ko, passes, ply, pv = Board(3), BLACK, None, 0, 0, []
    while ply < MAX_PLY and passes < 2:
        _, mv = s.search(b, colour, passes=passes, ko=ko, ply=ply)
        if mv is None:
            pv.append((colour, None))
            passes += 1
            ko = None
        else:
            for p, child, nk in legal_moves(b, colour, ko):
                if p == mv:
                    b, ko = child, nk
                    break
            pv.append((colour, mv))
            passes = 0
        colour = opposite(colour)
        ply += 1
    print(f"\n  最優對局（{len(pv)} 手）：")
    print("   ", " ".join(
        f"{'黑' if c == BLACK else '白'}{format_coord(p, 3) if p else '虛手'}"
        for c, p in pv))
    print()
    print(b)
    nb, nw = area_score(b)
    print(f"  數子：黑 {nb} : 白 {nw}")
    assert (nb, nw) == (9, 0)


# ------------------------------------------------------------ 3. 代價

def search_cost():
    print("\n" + "=" * 66)
    print("3. 剪枝值多少（3 路盤，手數上限 15）")
    print("=" * 66)
    counts = {}
    for ab, label in [(False, "只有置換表"), (True, "置換表 + alpha-beta")]:
        t = time.time()
        s = Solver(komi=0.0, max_ply=15, use_alphabeta=ab)
        v, _ = s.search(Board(3), BLACK)
        counts[ab] = s.nodes
        print(f"  {label:<22} V = {v:+.0f}   節點 = {s.nodes:>8}   "
              f"{time.time() - t:.1f}s")
    assert counts[True] == 9591 and counts[False] == 556948
    print(f"  -> 省下 {counts[False] / counts[True]:.0f} 倍，答案完全一樣")


def why_19_is_hopeless():
    print("\n" + "=" * 66)
    print("4. 4 路盤已經不行了")
    print("=" * 66)
    for ply in [6, 8]:
        t = time.time()
        s = Solver(komi=0.0, max_ply=ply)
        v, mv = s.search(Board(4), BLACK)
        name = format_coord(mv, 4) if mv else "虛手"
        print(f"  4 路 手數上限 {ply:>2}：V = {v:+.0f}  最佳著 {name:<4} "
              f"節點 = {s.nodes:>9}  {time.time() - t:.1f}s")
    print("  （它需要 20 以上才可能收斂 —— 那要跑上好幾天）")

    print("\n  盤面數的上界 3^(n*n)（第 5 章定理 5.3 用過的那個界）：")
    for n in [3, 4, 5, 9, 19]:
        print(f"    {n:>2} 路：3^{n * n:<3} = 10^{n * n * 0.4771:.0f}")
    print("\n  從 3 路到 19 路，中間隔著 165 個數量級。")


def main():
    two_by_two()
    three_by_three()
    search_cost()
    why_19_is_hopeless()
    print("\n" + "=" * 66)
    print("V 存在（Zermelo），而且在 3 路盤上算得出來。")
    print("問題從來不是它存不存在，是算不算得出來。")
    print("=" * 66)


if __name__ == "__main__":
    main()
