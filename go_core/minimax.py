"""全局值函數 V(s)：把一個棋盤真的解開。

對應第 10 章 §4.1–§4.4。

Zermelo 定理保證：有限、完全資訊、無隨機、零和的賽局存在唯一的值 V 與
最優策略。圍棋滿足這四個條件（有了劫規則之後就有限了 —— 第 5 章定理 5.3）。
所以「這個盤面到底誰贏」有唯一答案。

**問題從來不是它存不存在，是算不算得出來。** 這個檔案的作用是把那句話變成
具體的數字。

賽局的精確設定（這些選擇會影響答案，所以逐條寫清楚）
----------------------------------------------------
* **記分**：中國規則數子。一方的地 = 自己的子 + 只被自己包圍的空點。
* **終局**：連續兩次虛手。
* **劫**：基本劫規 —— 提掉單子之後，對方不能立刻在該點提回。
* **手數上限 `max_ply`**：超過就當終局，直接數子。

最後那一條是為了讓賽局圖變成**有向無環圖**：手數只增不減，所以置換表
可以安全地把手數放進鍵值裡，不會有「同一個盤面、不同的路、不同的答案」
的問題。代價是我們解的嚴格說來是「限手數的圍棋」。

`solve_converged()` 會把上限一路調高直到答案不再改變 —— 那才是可以引用的
數字。第 10 章 §5.2 會示範這個收斂過程。
"""

import numpy as np

from go_core.board import (BLACK, EMPTY, WHITE, Board, format_coord,
                           neighbors, opposite)

EXACT, LOWER, UPPER = 0, 1, 2


# ---------------------------------------------------------------- 記分

def area_score(board):
    """中國規則數子：回傳 (黑的地, 白的地)。

    空點的歸屬：把空點切成連通區塊，只碰到一種顏色的區塊歸那個顏色，
    兩種都碰到的是單官（不算給任何人）。
    """
    n = board.n
    counts = {BLACK: 0, WHITE: 0}
    for p in board.points():
        v = int(board.grid[p])
        if v != EMPTY:
            counts[v] += 1

    seen = set()
    for p in board.points():
        if board.grid[p] != EMPTY or p in seen:
            continue
        region, frontier, colours = 1, [p], set()
        seen.add(p)
        while frontier:
            q = frontier.pop()
            for r in neighbors(q, n):
                v = int(board.grid[r])
                if v == EMPTY:
                    if r not in seen:
                        seen.add(r)
                        region += 1
                        frontier.append(r)
                else:
                    colours.add(v)
        if len(colours) == 1:
            counts[next(iter(colours))] += region
    return counts[BLACK], counts[WHITE]


def final_value(board, komi=0.0):
    """終局盤面的值，由黑的角度看：黑的地 - 白的地 - 貼目。"""
    b, w = area_score(board)
    return b - w - komi


# ---------------------------------------------------------------- 著手

def legal_moves(board, colour, ko=None):
    """所有合法著手，回傳 [(點, 新盤面, 新的劫點), ...]。不含虛手。"""
    out = []
    for p in board.points():
        if board.grid[p] != EMPTY or p == ko:
            continue
        t = board.copy()
        try:
            captured = t.play(colour, p)
        except ValueError:
            continue                                # 自殺
        # 基本劫規：提掉【剛好一顆】、而且自己這串也剛好一顆一口氣
        new_ko = None
        if len(captured) == 1:
            from go_core.strings import find_string, liberties
            S = find_string(t, p)
            if len(S) == 1 and len(liberties(t, S)) == 1:
                new_ko = next(iter(captured))
        out.append((p, t, new_ko))
    return out


# ---------------------------------------------------------------- 完全解

class Solver:
    """限手數圍棋的完全解：minimax + alpha-beta + 置換表。

    置換表的鍵是 (盤面, 輪到誰, 連續虛手數, 劫點, 手數)。因為手數只增不減，
    這個狀態圖是 DAG —— 置換表因此是**安全的**（不會有路徑相依的問題）。

    alpha-beta 的截斷值另外用 EXACT / LOWER / UPPER 三種旗標記錄，
    這樣存進置換表的界限不會被誤當成精確值。這一步不做的話，
    答案會安靜地變錯（本書寫作時就先踩過一次）。
    """

    def __init__(self, komi=0.0, max_ply=None, use_memo=True,
                 use_alphabeta=True, superko=False):
        self.komi = komi
        self.max_ply = max_ply
        self.use_memo = use_memo
        self.use_alphabeta = use_alphabeta
        self.superko = superko
        self.tt = {}
        self.nodes = 0

    def _order(self, options, n):
        """先試靠中央的點 —— 小盤面上中央通常較好，能讓剪枝早一點發生。"""
        c = (n - 1) / 2
        return sorted(options, key=lambda o: abs(o[0][0] - c) + abs(o[0][1] - c))

    def search(self, board, to_move, alpha=-1e9, beta=1e9,
               passes=0, ko=None, ply=0, path=None):
        """回傳 (值, 最佳著)。值一律由**黑**的角度看。著手 None 代表虛手。

        superko=True 時 `path` 記錄本路徑出現過的所有盤面，並禁止重現。
        那時候 path 也會進置換表的鍵值 —— 慢，但沒有任何折衷。
        """
        self.nodes += 1
        if self.superko and path is None:
            path = frozenset({board.grid.tobytes()})
        if passes >= 2 or (self.max_ply is not None and ply >= self.max_ply):
            return final_value(board, self.komi), None

        key = (board.grid.tobytes(), to_move, passes, ko, ply, path)
        alpha0, beta0 = alpha, beta
        if self.use_memo and key in self.tt:
            val, move, flag = self.tt[key]
            if flag == EXACT:
                return val, move
            if flag == LOWER:
                alpha = max(alpha, val)
            else:
                beta = min(beta, val)
            if alpha >= beta:
                return val, move

        maximising = to_move == BLACK
        best = -1e9 if maximising else 1e9
        best_move = None
        cutoff = False

        for p, child, new_ko in self._order(legal_moves(board, to_move, ko),
                                            board.n):
            sub = None
            if self.superko:
                sig = child.grid.tobytes()
                if sig in path:
                    continue                    # positional superko
                sub = path | {sig}
            v, _ = self.search(child, opposite(to_move), alpha, beta,
                               0, new_ko, ply + 1, sub)
            if maximising:
                if v > best:
                    best, best_move = v, p
                alpha = max(alpha, best)
            else:
                if v < best:
                    best, best_move = v, p
                beta = min(beta, best)
            if self.use_alphabeta and beta <= alpha:
                cutoff = True
                break

        if not cutoff:                              # 虛手
            v, _ = self.search(board, opposite(to_move), alpha, beta,
                               passes + 1, None, ply + 1, path)
            if maximising and v > best:
                best, best_move = v, None
            elif not maximising and v < best:
                best, best_move = v, None

        if self.use_memo:
            if best <= alpha0:
                flag = UPPER
            elif best >= beta0:
                flag = LOWER
            else:
                flag = EXACT
            self.tt[key] = (best, best_move, flag)
        return best, best_move


def solve(board, to_move=BLACK, komi=0.0, max_ply=None, **kw):
    """解一個盤面。回傳 (值, 最佳著)。值由黑的角度看。"""
    if max_ply is None:
        max_ply = board.n * board.n * 2 + 4
    s = Solver(komi=komi, max_ply=max_ply, **kw)
    return s.search(board, to_move)


def solve_converged(board, to_move=BLACK, komi=0.0, start=None, step=4,
                    limit=200, trace=False):
    """把手數上限一路調高，直到答案連續兩次不變。

    回傳 (值, 最佳著, 收斂時的手數上限, 歷程)。**這才是可以引用的數字** ——
    「限手數的答案」只有在不再隨上限改變時，才等於真正的 V。
    """
    empties = sum(1 for p in board.points() if board.grid[p] == EMPTY)
    ply = start if start is not None else max(6, empties + 2)
    history, prev = [], None
    while ply <= limit:
        s = Solver(komi=komi, max_ply=ply)
        v, mv = s.search(board, to_move)
        history.append((ply, v, s.nodes))
        if trace:
            name = format_coord(mv, board.n) if mv else "虛手"
            print(f"    max_ply={ply:>3}  V={v:+.1f}  最佳著={name:<4} "
                  f"節點={s.nodes}")
        if prev is not None and v == prev:
            return v, mv, ply, history
        prev = v
        ply += step
    raise RuntimeError(f"手數上限到 {limit} 仍未收斂")


def fair_komi(n, to_move=BLACK):
    """讓 V(空盤) = 0 的貼目 —— 這就是「貼目」這個數字的定義。"""
    v, _, _, _ = solve_converged(Board(n), to_move, komi=0.0)
    return v


def move_values(board, to_move, komi=0.0, max_ply=None):
    """每一個合法著手（含虛手）的值，由黑的角度看。

    回傳 [(著手, 值), ...]，已依「對 to_move 而言由好到壞」排序。
    """
    if max_ply is None:
        max_ply = board.n * board.n * 2 + 4
    out = []
    for p, child, new_ko in legal_moves(board, to_move):
        s = Solver(komi=komi, max_ply=max_ply)
        v, _ = s.search(child, opposite(to_move), passes=0, ko=new_ko, ply=1)
        out.append((p, v))
    s = Solver(komi=komi, max_ply=max_ply)
    v, _ = s.search(board, opposite(to_move), passes=1, ply=1)
    out.append((None, v))
    out.sort(key=lambda kv: -kv[1] if to_move == BLACK else kv[1])
    return out


def delta_v(board, to_move, komi=0.0, max_ply=None):
    """每一手的失分 delta_V >= 0：和最佳著相比虧了幾目。"""
    vals = move_values(board, to_move, komi, max_ply)
    best = vals[0][1]
    sign = 1 if to_move == BLACK else -1
    return [(p, sign * (best - v)) for p, v in vals]


# ---------------------------------------------------------------- 勝率

def win_rate(v, tau=1.0):
    """把目數擠成勝率：p = sigma(V / tau)。

    tau 是「一目值多少勝率」的尺度。tau 大 = 局面還亂，一目不太決定勝負；
    tau 小 = 官子階段，一目就是全部。
    """
    return 1.0 / (1.0 + np.exp(-np.asarray(v, dtype=float) / tau))


def expected_win_rate(outcomes, probs=None, tau=1.0):
    """一組可能結果的期望勝率 E[sigma(V)]。

    第 10 章 §4.3 用它示範 Jensen 不等式：V > 0 時 sigma 是凹的，
    所以**同樣的期望目數，變異數越小勝率越高**。
    """
    outcomes = np.asarray(outcomes, dtype=float)
    if probs is None:
        probs = np.ones_like(outcomes) / len(outcomes)
    probs = np.asarray(probs, dtype=float)
    return float((probs * win_rate(outcomes, tau)).sum())


def variance_preference(mean, spread, tau=1.0):
    """兩個選擇，同樣的期望目數，一個穩一個亂 —— 哪個勝率高？

    回傳 (穩的勝率, 亂的勝率, 差)。差為正表示「該求穩」。
    這就是第 10 章 §4.3 的全部內容，寫成三行。
    """
    steady = expected_win_rate([mean], tau=tau)
    wild = expected_win_rate([mean - spread, mean + spread], tau=tau)
    return steady, wild, steady - wild
