"""蒙地卡羅樹搜尋：不展開全部，只展開有希望的。

對應第 10 章 §4.4。

第 10 章 §4.2 的完全解在 3 路盤上跑得動，4 路盤已經吃力，5 路盤在純 Python
裡沒有希望 —— 而 19 路盤和「沒有希望」之間還隔著天文數字。

MCTS 換一個問法。它不問「這棵樹長什麼樣」，只問：

    我有一筆固定的預算，該把它花在哪些分支上？

每一次模擬走四步：**選擇 -> 擴展 -> 模擬 -> 回傳**。選擇那一步用的公式是
這一整章最該記住的一行：

    UCT:   a* = argmax [ Q(a) + c * sqrt( ln N / n(a) ) ]
    PUCT:  a* = argmax [ Q(a) + c * P(a) * sqrt(N) / (1 + n(a)) ]

左邊那項是**已知的好**，右邊那項是**還沒看夠的可能**。AlphaGo 系列用的是
PUCT，多出來的 P(a) 是策略網路給的先驗 —— 也就是「人類會先看哪幾手」。

這個檔案沒有神經網路。先驗可以自己傳進來（`prior=` 參數），不傳就退化成
均勻分佈，也就是純 UCT。第 10 章用它示範一件事：**同樣的模擬次數，
有先驗和沒先驗的差距有多大。**
"""

import math
import random

from go_core.board import BLACK, EMPTY, WHITE, Board, format_coord, opposite
from go_core.eyes import is_eye_like
from go_core.minimax import final_value, legal_moves


class Node:
    """一個節點。`moves` 是 [(著手, 子盤面, 新劫點), ...]，None 代表虛手。"""

    __slots__ = ("board", "to_move", "ko", "passes", "moves", "children",
                 "n", "w", "prior")

    def __init__(self, board, to_move, ko=None, passes=0):
        self.board = board
        self.to_move = to_move
        self.ko = ko
        self.passes = passes
        self.moves = None
        self.children = {}
        self.n = 0
        self.w = 0.0            # 累積的值，一律由**黑**的角度看
        self.prior = None

    def is_terminal(self):
        return self.passes >= 2

    def expand(self, prior_fn=None):
        """列出著手（含虛手），並算好先驗。"""
        if self.moves is not None:
            return
        opts = legal_moves(self.board, self.to_move, self.ko)
        opts.append((None, self.board, None))          # 虛手
        self.moves = opts
        if prior_fn is None:
            self.prior = [1.0 / len(opts)] * len(opts)
        else:
            raw = [max(1e-9, prior_fn(self.board, self.to_move, p))
                   for p, _, _ in opts]
            total = sum(raw)
            self.prior = [x / total for x in raw]


def rollout(board, to_move, ko, passes, rng, max_moves=None, komi=0.0):
    """隨機把棋下完，回傳終局的值（黑的角度）。

    和第 9 章的 `influence.playout` 一樣，關鍵是**不填自己的眼** ——
    不然雙方會把自己的活棋填死，模擬出來的結果毫無意義。
    """
    b = board.copy()
    n = b.n
    max_moves = max_moves or n * n * 3
    colour = to_move
    for _ in range(max_moves):
        if passes >= 2:
            break
        cands = [p for p, _, _ in legal_moves(b, colour, ko)
                 if not is_eye_like(b, p, colour)]
        if not cands:
            passes += 1
            ko = None
        else:
            p = rng.choice(cands)
            captured = b.play(colour, p)
            ko = None
            if len(captured) == 1:
                from go_core.strings import find_string, liberties
                S = find_string(b, p)
                if len(S) == 1 and len(liberties(b, S)) == 1:
                    ko = next(iter(captured))
            passes = 0
        colour = opposite(colour)
    return final_value(b, komi)


def uct_score(child_n, child_w, parent_n, prior, c, to_move, puct):
    """選擇公式。回傳給 to_move 看的分數（越大越想走）。"""
    if child_n == 0:
        q = 0.0
    else:
        q = child_w / child_n
        if to_move == WHITE:
            q = -q                       # 值一律由黑的角度存，白要反過來看
    if puct:
        u = c * prior * math.sqrt(parent_n) / (1 + child_n)
    else:
        if child_n == 0:
            return float("inf")
        u = c * math.sqrt(math.log(max(parent_n, 1)) / child_n)
    return q + u


def search(board, to_move, simulations=400, c=1.4, rng=None, komi=0.0,
           prior_fn=None, puct=False, scale=None):
    """跑 `simulations` 次模擬，回傳 (根節點, 各著手的統計)。

    統計是 [(著手, 訪問次數, 平均值), ...]，依訪問次數排序 ——
    **AlphaGo 選的是訪問最多的那一手，不是平均值最高的那一手**，
    因為訪問次數是「被反覆驗證過」的意思，比較不會被少數幾次幸運的模擬騙。
    """
    rng = rng or random.Random(0)
    scale = scale or (board.n * board.n)          # 把目數壓到大約 [-1, 1]
    root = Node(board.copy(), to_move)

    for _ in range(simulations):
        node = root
        path = [node]

        # 1. 選擇
        while node.moves is not None and not node.is_terminal():
            node.expand(prior_fn)
            best, best_key = None, None
            for i, (p, child_board, new_ko) in enumerate(node.moves):
                ch = node.children.get(i)
                s = uct_score(ch.n if ch else 0, ch.w if ch else 0.0,
                              max(node.n, 1), node.prior[i], c,
                              node.to_move, puct)
                if best is None or s > best:
                    best, best_key = s, i
            i = best_key
            p, child_board, new_ko = node.moves[i]
            if i not in node.children:
                node.children[i] = Node(
                    child_board.copy(), opposite(node.to_move), new_ko,
                    node.passes + 1 if p is None else 0)
            node = node.children[i]
            path.append(node)

        # 2. 擴展
        if not node.is_terminal():
            node.expand(prior_fn)

        # 3. 模擬
        if node.is_terminal():
            v = final_value(node.board, komi)
        else:
            v = rollout(node.board, node.to_move, node.ko, node.passes,
                        rng, komi=komi)
        v = max(-1.0, min(1.0, v / scale))

        # 4. 回傳
        for nd in path:
            nd.n += 1
            nd.w += v

    root.expand(prior_fn)
    stats = []
    for i, (p, _, _) in enumerate(root.moves):
        ch = root.children.get(i)
        if ch is None or ch.n == 0:
            continue
        stats.append((p, ch.n, ch.w / ch.n))
    stats.sort(key=lambda t: -t[1])
    return root, stats


def best_move(board, to_move, simulations=400, **kw):
    """訪問次數最多的那一手。"""
    _, stats = search(board, to_move, simulations, **kw)
    return stats[0][0] if stats else None


def describe(stats, n, top=6):
    lines = [f"  {'著手':<6}{'訪問':>8}{'平均值':>10}"]
    for p, visits, q in stats[:top]:
        name = format_coord(p, n) if p else "虛手"
        lines.append(f"  {name:<6}{visits:>8}{q:>10.3f}")
    return "\n".join(lines)
