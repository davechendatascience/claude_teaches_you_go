"""三種計分法，以及它們之間那條精確的等式。

對應第 13 章。

圍棋有兩套主流計分法，結果「幾乎總是一樣」——而這一章要把「幾乎」變成一個式子。

    中國規則（數子）  score = 自己的子 + 自己圍住的空點
    日本規則（數目）  score = 自己圍住的空點 + 提到的對方子

看起來完全不同。但把兩邊的差寫開，會發現它只等於一個東西：**雙方手數的差**。

    C - J = b - w        （定理 13.2）

其中 b、w 是黑白各自【下過幾顆子】（含後來被提掉的）。
證明是四行代數，見 `equivalence_gap` 的說明。

真正的例外只有一個，而且它是**規則層面**的，不是算術層面的：
日本規則規定**雙活裡的眼不算目**。那一條不在上面的推導裡，
所以要另外處理（見 `japanese_score` 的 `count_seki_eyes` 參數）。
"""

import numpy as np

from go_core.board import BLACK, EMPTY, WHITE, Board, neighbors, opposite


# ---------------------------------------------------------------- 區塊

def empty_regions(board):
    """把空點切成連通區塊。回傳 [(區塊, 碰得到的顏色集合), ...]。"""
    seen = set()
    out = []
    for p in board.points():
        if board.grid[p] != EMPTY or p in seen:
            continue
        region, frontier, colours = {p}, [p], set()
        seen.add(p)
        while frontier:
            q = frontier.pop()
            for r in neighbors(q, board.n):
                v = int(board.grid[r])
                if v == EMPTY:
                    if r not in seen:
                        seen.add(r)
                        region.add(r)
                        frontier.append(r)
                else:
                    colours.add(v)
        out.append((frozenset(region), frozenset(colours)))
    return out


def territory(board):
    """只碰得到一種顏色的空區塊，就是那個顏色的地。回傳 (黑的目, 白的目)。

    碰得到兩種顏色的區塊是**單官**（dame），不算給任何人 ——
    兩套規則在這一點上是一致的。
    """
    counts = {BLACK: 0, WHITE: 0}
    for region, colours in empty_regions(board):
        if len(colours) == 1:
            counts[next(iter(colours))] += len(region)
    return counts[BLACK], counts[WHITE]


def stones(board):
    """盤上各有幾顆子。回傳 (黑, 白)。"""
    return int((board.grid == BLACK).sum()), int((board.grid == WHITE).sum())


def dame(board):
    """單官：碰得到兩種顏色的空點。"""
    out = set()
    for region, colours in empty_regions(board):
        if len(colours) > 1:
            out |= region
    return frozenset(out)


# ---------------------------------------------------------------- 三種計分

def chinese_score(board, komi=0.0):
    """數子（中國規則 / area scoring）：子 + 地。回傳黑的領先目數。"""
    sb, sw = stones(board)
    tb, tw = territory(board)
    return (sb + tb) - (sw + tw) - komi


def japanese_score(board, prisoners_black=0, prisoners_white=0, komi=0.0,
                   seki_eyes=0):
    """數目（日本規則 / territory scoring）：地 + 提子。回傳黑的領先目數。

    `prisoners_black` 是**黑提到的白子**（黑的收穫），反之亦然。

    `seki_eyes` 是「雙活裡的眼」的黑減白差額 —— 日本規則規定那些點不算目，
    而 `territory()` 會把它們算進去，所以要在這裡扣掉。
    預設 0，表示盤面上沒有雙活（大多數對局如此）。
    """
    tb, tw = territory(board)
    return (tb + prisoners_black) - (tw + prisoners_white) - seki_eyes - komi


def tromp_taylor_score(board, komi=0.0):
    """Tromp-Taylor：和數子完全一樣，只是它連死子都不判 —— 盤面就是全部。

    本書的 `chinese_score` 已經是這個意思（不做死子判定），
    所以兩者在**已經下完的盤面**上恆等。留這個名字是為了對照。
    """
    return chinese_score(board, komi)


# ------------------------------------------------- 等價定理

def equivalence_gap(board, moves_black, moves_white,
                    prisoners_black=0, prisoners_white=0):
    """定理 13.2：C - J = b - w。回傳 (C, J, C-J, b-w, 相符嗎)。

    推導（四行）：令盤上黑子 S_B、白子 S_W，黑地 T_B、白地 T_W，
    黑提到的白子 P_B、白提到的黑子 P_W。

        C = (S_B + T_B) - (S_W + T_W)
        J = (T_B + P_B) - (T_W + P_W)
        C - J = S_B - S_W - P_B + P_W

    而「下過的子」= 盤上的 + 被對方提掉的：

        b = S_B + P_W,   w = S_W + P_B

    代進去：C - J = (b - P_W) - (w - P_B) - P_B + P_W = b - w。   □
    """
    c = chinese_score(board)
    j = japanese_score(board, prisoners_black, prisoners_white)
    return c, j, c - j, moves_black - moves_white, (c - j) == (moves_black
                                                              - moves_white)


# ------------------------------------------------- 終局

def is_finished(board, colour_to_move=None):
    """終局的操作型定義：**沒有單官了，而且雙方都沒有還能賺的著手**。

    本書 §4.1 給的定義是「所有局部的溫度 <= 0」。在程式裡最便宜的近似是：
    盤面上沒有單官（碰得到兩色的空點），因為單官正是溫度 0 的地方。

    回傳 (是否終局, 還剩幾個單官)。
    """
    d = dame(board)
    return len(d) == 0, len(d)


def score_report(board, moves_black=0, moves_white=0,
                 prisoners_black=0, prisoners_white=0, komi=0.0,
                 seki_eyes=0):
    """把一個盤面的三種計分並排。"""
    sb, sw = stones(board)
    tb, tw = territory(board)
    c = chinese_score(board, komi)
    j = japanese_score(board, prisoners_black, prisoners_white, komi, seki_eyes)
    return {
        "stones": (sb, sw),
        "territory": (tb, tw),
        "prisoners": (prisoners_black, prisoners_white),
        "moves": (moves_black, moves_white),
        "dame": len(dame(board)),
        "chinese": c,
        "japanese": j,
        "gap": c - j,
        "move_diff": moves_black - moves_white,
    }


# ------------------------------------------------- 對局紀錄

class ScoredGame:
    """一邊下一邊記帳：誰下了幾顆子、誰提了幾顆子。

    這是驗證定理 13.2 唯一需要的東西 —— 兩套計分法的差，
    全部藏在這兩本流水帳裡。
    """

    def __init__(self, n=9):
        self.board = Board(n)
        self.moves = {BLACK: 0, WHITE: 0}
        self.prisoners = {BLACK: 0, WHITE: 0}   # prisoners[c] = c 提到的對方子
        self.passes = 0

    def play(self, colour, coord):
        taken = self.board.play(colour, coord)
        self.moves[colour] += 1
        self.prisoners[colour] += len(taken)
        self.passes = 0
        return taken

    def pass_move(self):
        self.passes += 1

    def report(self, komi=0.0, seki_eyes=0):
        return score_report(self.board, self.moves[BLACK], self.moves[WHITE],
                            self.prisoners[BLACK], self.prisoners[WHITE],
                            komi, seki_eyes)

    def check_equivalence(self):
        return equivalence_gap(self.board, self.moves[BLACK], self.moves[WHITE],
                               self.prisoners[BLACK], self.prisoners[WHITE])


def random_finished_game(n=9, rng=None, max_moves=None, fill_dame=True):
    """隨機把棋下完（不填自己的眼），回傳 ScoredGame。

    `fill_dame=True` 時最後會把單官全部填掉 —— 那是「終局」的操作型定義
    （§4.1），也是兩套規則能對得起來的前提。
    """
    import random

    from go_core.eyes import is_eye_like

    rng = rng or random.Random(0)
    g = ScoredGame(n)
    max_moves = max_moves or n * n * 3
    colour = BLACK
    for _ in range(max_moves):
        cands = [p for p in g.board.points()
                 if g.board.grid[p] == EMPTY and not is_eye_like(g.board, p, colour)]
        rng.shuffle(cands)
        played = False
        for p in cands:
            try:
                g.play(colour, p)
                played = True
                break
            except ValueError:
                continue
        if not played:
            g.pass_move()
            if g.passes >= 2:
                break
        colour = opposite(colour)

    if fill_dame:
        while True:
            d = sorted(dame(g.board))
            if not d:
                break
            moved = False
            for p in d:
                try:
                    g.play(colour, p)
                    moved = True
                    break
                except ValueError:
                    continue
            colour = opposite(colour)
            if not moved:
                break
    return g


# ------------------------------------------------- 日本規則下的完全解

def solve_japanese(board, to_move=BLACK, komi=0.0, max_ply=None):
    """用**日本規則**（數目）把小盤面解開，回傳 (值, 最佳著)。

    關鍵的簡化來自定理 13.2 本身：

        J = C - (b - w)

    終局的 C 只看盤面，而 (b - w) 只要沿路加減就好（黑落子 +1、白落子 -1，
    虛手不算）。所以狀態只要多帶一個整數，不必記提子數。

    這讓「日本規則的公平貼目」在 3 路盤上算得出來 ——
    而第 10 章已經算過中國規則的答案是 9。兩者一比，
    貼目那一目的差就有了一個可以引用的數字。
    """
    from go_core.minimax import EXACT, LOWER, UPPER, legal_moves

    if max_ply is None:
        max_ply = board.n * board.n * 2 + 4
    tt = {}
    stats = {"nodes": 0}

    def search(b, colour, alpha, beta, passes, ko, ply, diff):
        stats["nodes"] += 1
        if passes >= 2 or ply >= max_ply:
            return chinese_score(b) - diff - komi, None

        key = (b.grid.tobytes(), colour, passes, ko, ply, diff)
        alpha0, beta0 = alpha, beta
        if key in tt:
            val, mv, flag = tt[key]
            if flag == EXACT:
                return val, mv
            if flag == LOWER:
                alpha = max(alpha, val)
            else:
                beta = min(beta, val)
            if alpha >= beta:
                return val, mv

        maximising = colour == BLACK
        best = -1e9 if maximising else 1e9
        best_move = None
        cutoff = False
        step = 1 if colour == BLACK else -1

        c = (b.n - 1) / 2
        opts = sorted(legal_moves(b, colour, ko),
                      key=lambda o: abs(o[0][0] - c) + abs(o[0][1] - c))
        for p, child, new_ko in opts:
            v, _ = search(child, opposite(colour), alpha, beta, 0, new_ko,
                          ply + 1, diff + step)
            if maximising:
                if v > best:
                    best, best_move = v, p
                alpha = max(alpha, best)
            else:
                if v < best:
                    best, best_move = v, p
                beta = min(beta, best)
            if beta <= alpha:
                cutoff = True
                break

        if not cutoff:                                  # 虛手：不放子，diff 不變
            v, _ = search(b, opposite(colour), alpha, beta, passes + 1, None,
                          ply + 1, diff)
            if maximising and v > best:
                best, best_move = v, None
            elif not maximising and v < best:
                best, best_move = v, None

        flag = UPPER if best <= alpha0 else (LOWER if best >= beta0 else EXACT)
        tt[key] = (best, best_move, flag)
        return best, best_move

    val, mv = search(board.copy(), to_move, -1e9, 1e9, 0, None, 0, 0)
    return val, mv, stats["nodes"]
