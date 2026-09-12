"""手割：把著手順序打亂，因為盤面不記得你怎麼走到那裡的。

對應第 11 章。

「手割」在傳統教材裡看起來像魔法：把一個定石的著手順序重排，換成另一個
已知的序列，然後說「你看，白多下了一手」。它的理論內容其實只有一句話：

    **不含提子的落子序列，最終盤面只取決於「哪個點放了什麼顏色」的集合，
    與下的順序無關。**

證明是一行：每一手只是把某個點從空變成某色，而這些操作互相交換。
提子是唯一會壞事的東西 —— 它會把別的點變回空，於是順序就有影響了。

這個檔案提供三件事：

1. `play_sequence` / `tewari_equal` —— 給兩個序列，自動驗證是否到達同一盤面，
   並在不同時指出差在哪裡。
2. `reachable_states` / `exact_values` —— 把小盤面上所有到得了的局面列出來，
   並用第 10 章的求解器算出精確的 V。（共用置換表，快二十倍。）
3. `evaluate_policy` —— 拿一條便宜的規則去和精確的 V 比。
   第 11 章 §4.4 用它回答「該記什麼」：**哪一條規則值得背。**
"""

import numpy as np

from go_core.board import (BLACK, EMPTY, WHITE, Board, format_coord,
                           neighbors, opposite)
from go_core.minimax import Solver, legal_moves

MAX_PLY = 15


# ---------------------------------------------------------------- 手割

def play_sequence(moves, n=9, allow_illegal=False):
    """依序落子。moves 是 [(顏色, 座標), ...]。

    回傳 (盤面, 提子紀錄)。提子紀錄是 [(第幾手, 顏色, 座標, 提掉的點), ...]，
    **只要它不是空的，手割就不能直接用。**
    """
    b = Board(n)
    captures = []
    for i, (colour, coord) in enumerate(moves, 1):
        try:
            taken = b.play(colour, coord)
        except ValueError:
            if allow_illegal:
                captures.append((i, colour, coord, None))   # None = 這一手不合法
                continue
            raise
        if taken:
            captures.append((i, colour, coord, frozenset(taken)))
    return b, captures


def stone_set(board):
    """盤面的「棋子集合」表示：{(點, 顏色)}。手割比較的就是這個。"""
    return frozenset((p, int(board.grid[p])) for p in board.points()
                     if board.grid[p] != EMPTY)


def tewari_equal(seq_a, seq_b, n=9, allow_illegal=True):
    """兩個序列會不會到達同一個盤面？

    回傳一份報告：
        same        兩個盤面是否相同
        captures_a  序列 A 有沒有提子（有的話手割不適用）
        captures_b  同上
        only_a      只有 A 有的子
        only_b      只有 B 有的子
        illegal_a / illegal_b   哪幾手在該順序下不合法
    """
    ba, ca = play_sequence(seq_a, n, allow_illegal)
    bb, cb = play_sequence(seq_b, n, allow_illegal)
    sa, sb = stone_set(ba), stone_set(bb)
    return {
        "same": sa == sb,
        "captures_a": [x for x in ca if x[3]],
        "captures_b": [x for x in cb if x[3]],
        "only_a": sorted((format_coord(p, n), c) for p, c in sa - sb),
        "only_b": sorted((format_coord(p, n), c) for p, c in sb - sa),
        "illegal_a": [(i, co) for i, _, co, t in ca if t is None],
        "illegal_b": [(i, co) for i, _, co, t in cb if t is None],
        "board_a": ba,
        "board_b": bb,
    }


def is_capture_free(moves, n=9):
    """這個序列從頭到尾都沒有提子嗎？（手割定理的前提）"""
    _, caps = play_sequence(moves, n)
    return not caps


# ------------------------------------------------- 可達局面與精確值

def _state_key(board, to_move, ko):
    return (board.grid.tobytes(), to_move, ko)


def _board_from_key(key, n):
    grid, to_move, ko = key
    b = Board(n)
    b.grid = np.frombuffer(grid, dtype=b.grid.dtype).reshape(n, n).copy()
    return b, to_move, ko


def reachable_states(n=3, depth=4, to_move=BLACK):
    """BFS：`depth` 手之內到得了的所有 (盤面, 輪到誰, 劫點)。

    回傳 {狀態鍵: 最短距離}。狀態鍵裡有劫點 —— 這一點在第 11 章 §4.1
    會變得很重要：**同一個盤面、同一方走，劫點不同就是不同的局面。**
    """
    from collections import deque

    start = Board(n)
    seen = {_state_key(start, to_move, None): 0}
    queue = deque([(start, to_move, None, 0)])
    while queue:
        b, colour, ko, d = queue.popleft()
        if d >= depth:
            continue
        for _, child, new_ko in legal_moves(b, colour, ko):
            k = _state_key(child, opposite(colour), new_ko)
            if k not in seen:
                seen[k] = d + 1
                queue.append((child, opposite(colour), new_ko, d + 1))
        k = _state_key(b, opposite(colour), None)            # 虛手
        if k not in seen:
            seen[k] = d + 1
            queue.append((b, opposite(colour), None, d + 1))
    return seen


def exact_values(states, n=3, komi=0.0, max_ply=MAX_PLY, solver=None):
    """把每個狀態的 V 算出來。共用一個置換表，快二十倍。

    回傳 ({狀態鍵: V}, solver)。
    """
    solver = solver or Solver(komi=komi, max_ply=max_ply)
    out = {}
    for key in states:
        b, colour, ko = _board_from_key(key, n)
        v, _ = solver.search(b, colour, ko=ko)
        out[key] = v
    return out, solver


def best_moves(board, to_move, ko=None, n=3, komi=0.0, max_ply=MAX_PLY,
               solver=None):
    """這個局面所有**最佳**著手（可能不只一個），以及每一手的值。

    回傳 (最佳著集合, {著手: V})。著手 None 代表虛手。
    """
    solver = solver or Solver(komi=komi, max_ply=max_ply)
    vals = {}
    for p, child, new_ko in legal_moves(board, to_move, ko):
        v, _ = solver.search(child, opposite(to_move), ko=new_ko)
        vals[p] = v
    v, _ = solver.search(board, opposite(to_move), passes=1)
    vals[None] = v
    best = max(vals.values()) if to_move == BLACK else min(vals.values())
    return {p for p, x in vals.items() if x == best}, vals


# ---------------------------------------------------------------- 便宜的規則

def policy_centre(board, to_move, ko=None):
    """靠中央的點優先。第 9 章的影響力場說中央最好 —— 這是它的極簡版。"""
    n = board.n
    c = (n - 1) / 2
    opts = [p for p, _, _ in legal_moves(board, to_move, ko)]
    if not opts:
        return None
    return min(opts, key=lambda p: (abs(p[0] - c) + abs(p[1] - c), p))


def policy_liberties(board, to_move, ko=None):
    """下完之後自己這串氣最多的點。第 2 章的度量。"""
    from go_core.strings import find_string, liberties
    best, best_key = None, None
    for p, child, _ in legal_moves(board, to_move, ko):
        libs = len(liberties(child, find_string(child, p)))
        key = (-libs, p)
        if best_key is None or key < best_key:
            best, best_key = p, key
    return best


def policy_influence(board, to_move, ko=None, lam=0.8):
    """讓自己的影響力總和最大的點。第 9 章的場。"""
    from go_core.influence import zobrist_field
    sign = 1 if to_move == BLACK else -1
    best, best_key = None, None
    for p, child, _ in legal_moves(board, to_move, ko):
        score = sign * float(zobrist_field(child, lam).sum())
        key = (-score, p)
        if best_key is None or key < best_key:
            best, best_key = p, key
    return best


def policy_greedy_score(board, to_move, ko=None):
    """下完之後立刻數子，選數字最好的那一手。最短視的一條規則。"""
    from go_core.minimax import final_value
    sign = 1 if to_move == BLACK else -1
    best, best_key = None, None
    for p, child, _ in legal_moves(board, to_move, ko):
        key = (-sign * final_value(child), p)
        if best_key is None or key < best_key:
            best, best_key = p, key
    return best


def policy_mcts(simulations=200, seed=0):
    """跑 N 次模擬的 MCTS。第 10 章的搜尋，只是預算很小。"""
    import random

    from go_core.mcts import search as mcts_search

    def fn(board, to_move, ko=None):
        _, stats = mcts_search(board, to_move, simulations=simulations,
                               rng=random.Random(seed))
        return stats[0][0] if stats else None
    return fn


# ---------------------------------------------------------------- 評分

def solve_all(states, n=3, komi=0.0, max_ply=MAX_PLY, solver=None,
              progress=None):
    """把每個局面的【所有最佳著】與【每一手的值】算好，之後所有規則共用。

    這一步是整章最貴的計算，但只做一次 —— 七條規則各算一遍是七倍的浪費
    （本書寫作時先犯過這個錯）。回傳 {狀態鍵: (最佳著集合, {著手: V})}。
    """
    solver = solver or Solver(komi=komi, max_ply=max_ply)
    table = {}
    for i, key in enumerate(states):
        board, to_move, ko = _board_from_key(key, n)
        if not legal_moves(board, to_move, ko):
            continue
        table[key] = best_moves(board, to_move, ko, n, komi, max_ply, solver)
        if progress and i % progress == 0:
            print(f"    ... {i}/{len(states)}", flush=True)
    return table, solver


def score_policy(table, policy, n=3):
    """拿一條規則去對照 `solve_all` 算好的答案。"""
    losses, hits = [], 0
    for key, (best, vals) in table.items():
        board, to_move, ko = _board_from_key(key, n)
        chosen = policy(board, to_move, ko)
        if chosen not in vals:
            chosen = None
        sign = 1 if to_move == BLACK else -1
        best_val = max(vals.values()) if to_move == BLACK else min(vals.values())
        losses.append(sign * (best_val - vals[chosen]))
        hits += chosen in best
    total = len(losses)
    return {
        "n_states": total,
        "hit_rate": hits / total if total else float("nan"),
        "mean_loss": float(np.mean(losses)) if losses else float("nan"),
        "max_loss": max(losses) if losses else float("nan"),
        "losses": losses,
    }


def evaluate_policy(states, policy, n=3, komi=0.0, max_ply=MAX_PLY,
                    solver=None, skip_terminal=True):
    """一條規則在一堆局面上有多好？

    回傳：
        n_states   評了幾個局面
        hit_rate   選中【某一個】最佳著的比例
        mean_loss  平均失分（目）
        max_loss   最大失分
        losses     每個局面的失分（給畫分佈用）
    """
    solver = solver or Solver(komi=komi, max_ply=max_ply)
    losses = []
    hits = 0
    for key in states:
        board, to_move, ko = _board_from_key(key, n)
        opts = legal_moves(board, to_move, ko)
        if skip_terminal and not opts:
            continue
        best, vals = best_moves(board, to_move, ko, n, komi, max_ply, solver)
        chosen = policy(board, to_move, ko)
        if chosen not in vals:
            chosen = None                       # 規則給了不合法的點，當作虛手
        sign = 1 if to_move == BLACK else -1
        best_val = max(vals.values()) if to_move == BLACK else min(vals.values())
        loss = sign * (best_val - vals[chosen])
        losses.append(loss)
        hits += chosen in best
    total = len(losses)
    return {
        "n_states": total,
        "hit_rate": hits / total if total else float("nan"),
        "mean_loss": float(np.mean(losses)) if losses else float("nan"),
        "max_loss": max(losses) if losses else float("nan"),
        "losses": losses,
    }
