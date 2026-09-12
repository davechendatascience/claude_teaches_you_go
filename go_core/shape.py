"""形：效率的局部度量，以及手筋的充要條件。

對應第 8 章。

第 2 章 §4.3 已經給了核心工具 —— 三項分解定理：

    |L(S)| = Σ deg(s)  -  2·e(S)  -  Σ(mult(v)-1)  -  b(S)
             原始配額     內部相鄰    重複的氣        被外子遮掉

這個檔案做兩件事：

1. **把形變成一個可以排序的數。** 效率 η(S) = |L(S)| / |S|，以及更有用的
   「邊際氣」—— 多下這一顆子，多了幾口氣。
2. **把手筋變成充要條件。** 雙打、倒撲、接不歸 —— 每一個都是一個可以
   在盤面上檢查的述詞，不是一張要背的圖。
"""

from itertools import combinations

from go_core.board import BLACK, EMPTY, WHITE, Board, neighbors, opposite
from go_core.strings import (all_strings, find_string, liberties,
                             liberty_decomposition)


# ---------------------------------------------------------------- 效率

def efficiency(board, S):
    """氣效率 η(S) = |L(S)| / |S|：平均每顆子帶來幾口氣。"""
    return len(liberties(board, S)) / len(S)


def marginal_liberty(board, S, p):
    """在 p 多下一顆同色子，這塊棋的氣會變幾口（可能是負的）。

    這比 η 有用得多：下棋是一手一手下的，你關心的永遠是**這一手**帶來什麼。
    """
    colour = int(board.grid[next(iter(S))])
    before = len(liberties(board, S))
    t = board.copy()
    t.grid[board._pt(p)] = colour
    after = len(liberties(t, find_string(t, p)))
    return after - before


def marginal_decomposition(board, S, p):
    """把「多下這一顆」拆開成四項，回傳一份可以逐項對照的報告。

    第 2 章的三項分解直接給出一個【精確】的邊際公式：

        dL = deg(p) - k - 1 - d_plus

      deg(p)   p 這一點的原始配額（中央 4、邊 3、角 2）
      k        p 貼著 S 幾顆子
      d_plus   p 這一手【新製造】的重複氣（>= 0）

    推導：加上 p 之後 Sdeg 多了 deg(p)、內部相鄰多了 k 對（-2k），
    而 p 本身原本就是一個 mult = k 的重複氣，那 (k-1) 的懲罰會消失（+k-1）。
    合起來 deg(p) - 2k + (k-1) - d_plus = deg(p) - k - 1 - d_plus。

    兩個推論（都在 tests/test_ch08_shape.py 裡驗過）：
      * d_plus >= 0 恆成立 —— 多一顆子只會讓更多空點被重複貼到。
      * 所以 dL <= deg(p) - k - 1。中央、只貼一處、不製造愚形時上界是 +2，
        而這是【任何一手棋能多的氣的絕對上限】。
    """
    from go_core.board import degree

    pt = board._pt(p)
    k = sum(1 for q in neighbors(pt, board.n) if q in S)
    before = liberty_decomposition(board, S)
    t = board.copy()
    t.grid[pt] = int(board.grid[next(iter(S))])
    after = liberty_decomposition(t, find_string(t, pt))
    d_plus = (after["duplicated"] - before["duplicated"]) + (k - 1)
    delta = after["liberties"] - before["liberties"]
    return {
        "delta": delta,
        "deg": degree(pt, board.n),
        "contacts": k,
        "new_duplicated": d_plus,
        "predicted": degree(pt, board.n) - k - 1 - d_plus,
        "before": before["liberties"],
        "after": after["liberties"],
    }


def shape_report(board, S):
    """把三項分解 + 效率整理成一份報告，方便在書上逐項對照。"""
    d = liberty_decomposition(board, S)
    d["size"] = len(S)
    d["efficiency"] = d["liberties"] / len(S)
    d["stupid"] = d["duplicated"] > 0        # 推論 2.6：第三項不為零就是愚形
    return d


def enumerate_shapes(size, span=5):
    """列舉所有大小為 size 的連通形狀（以相對座標表示，已去除平移重複）。

    回傳一個 set，每個元素是 frozenset of (dr, dc)，已正規化到左上角。
    """
    cells = [(r, c) for r in range(span) for c in range(span)]
    out = set()
    for combo in combinations(cells, size):
        pts = set(combo)
        # 連通嗎？
        seen = {next(iter(pts))}
        frontier = list(seen)
        while frontier:
            p = frontier.pop()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (p[0] + dr, p[1] + dc)
                if q in pts and q not in seen:
                    seen.add(q)
                    frontier.append(q)
        if len(seen) != size:
            continue
        r0 = min(p[0] for p in pts)
        c0 = min(p[1] for p in pts)
        out.add(frozenset((p[0] - r0, p[1] - c0) for p in pts))
    return out


def shape_on_board(shape, n=9, origin=(3, 3), colour=BLACK):
    """把一個相對座標的形狀擺到盤面中央。回傳 (board, 棋串)。"""
    b = Board(n)
    r0, c0 = origin
    pts = [(r0 + dr, c0 + dc) for dr, dc in shape]
    for p in pts:
        b.grid[p] = colour
    return b, find_string(b, pts[0])


def canonical_shape(shape):
    """把形狀正規化：八種對稱（旋轉 + 翻轉）裡字典序最小的那個。"""
    best = None
    pts = list(shape)
    for flip in (False, True):
        cur = [(c, r) if flip else (r, c) for r, c in pts]
        for _ in range(4):
            cur = [(c, -r) for r, c in cur]           # 旋轉 90 度
            r0 = min(p[0] for p in cur)
            c0 = min(p[1] for p in cur)
            norm = tuple(sorted((p[0] - r0, p[1] - c0) for p in cur))
            if best is None or norm < best:
                best = norm
    return best


# ---------------------------------------------------------------- 手筋

def atari_strings(board, colour):
    """colour 這一方目前只剩一口氣的棋串。"""
    return [S for S in all_strings(board, colour) if len(liberties(board, S)) == 1]


def double_atari_points(board, colour):
    """雙打：一手同時讓對方【兩個以上】的棋串只剩一口氣。

    回傳 [(落點, 被叫吃的棋串數), ...]，只列出數量 >= 2 的。

    形式化：存在合法著點 p，使得落子後 |{S : S 是對方棋串, |L(S)| = 1}| 增加到 >= 2，
    而且那些棋串都貼著 p。
    """
    foe = opposite(colour)
    out = []
    for p in board.points():
        if board.grid[p] != EMPTY:
            continue
        t = board.copy()
        try:
            t.play(colour, p)
        except ValueError:
            continue
        hit = set()
        for q in neighbors(p, board.n):
            if t.grid[q] == foe:
                S = find_string(t, q)
                if len(liberties(t, S)) == 1:
                    hit.add(S)
        if len(hit) >= 2:
            out.append((p, len(hit)))
    return sorted(out)


def snapback_points(board, colour):
    """倒撲：故意送一子讓對方提，提完之後對方那塊反而沒氣。

    形式化（三個條件同時成立）：
      1. colour 下在 p 之後，自己那一串只剩一口氣（自己送吃）。
      2. 對方提掉它。
      3. 提完之後，colour 有一手能提掉對方【更多】的子。

    回傳 [(落點, 送掉幾子, 提回幾子), ...]，只列出提回 > 送掉 的。
    """
    foe = opposite(colour)
    out = []
    for p in board.points():
        if board.grid[p] != EMPTY:
            continue
        t = board.copy()
        try:
            t.play(colour, p)
        except ValueError:
            continue
        S = find_string(t, p)
        L = liberties(t, S)
        if len(L) != 1:
            continue                       # 沒有送吃，不是倒撲
        sacrifice = len(S)
        q = next(iter(L))
        t2 = t.copy()
        try:
            taken = t2.play(foe, q)
        except ValueError:
            continue
        if not taken:
            continue                       # 對方那一手沒提到東西
        # 提完之後，colour 能不能提回更多？
        best = 0
        for r in t2.points():
            if t2.grid[r] != EMPTY:
                continue
            t3 = t2.copy()
            try:
                got = t3.play(colour, r)
            except ValueError:
                continue
            best = max(best, len(got))
        if best > sacrifice:
            out.append((p, sacrifice, best))
    return sorted(out)


def connection_points(board, S):
    """S 這塊棋要和同色的別塊連起來，有哪些接點。

    「接不歸」的形式化基礎：若有兩個以上的接點，而對手能同時威脅它們，
    那麼一手只能接一個 —— 又是鴿籠原理（第 3 章 §4.3）。
    """
    colour = int(board.grid[next(iter(S))])
    out = []
    for p in liberties(board, S):
        others = set()
        for q in neighbors(p, board.n):
            if board.grid[q] == colour:
                T = find_string(board, q)
                if T != S:
                    others.add(T)
        if others:
            out.append((p, len(others)))
    return sorted(out)
