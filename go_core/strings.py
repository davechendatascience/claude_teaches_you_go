"""棋串與氣：第 2 章 §4.2 與 §4.3 的兩個集合。

整個檔案就在實作兩條定義：

    棋串   S  = 同色棋子在圖 G 上的連通分量
    氣     L(S) = N(S) \\ Occupied，其中 N(S) = ∪_{s∈S} N(s)

請注意 liberties() 回傳的是 **集合**，不是數字。這是全書第 1 層的核心：
氣是一個集合，所以合併棋串時要用容斥原理，不能相加。
"""

from go_core.board import EMPTY, neighbors


def find_string(board, key):
    """回傳包含 key 這一點的棋串（同色連通分量），型別是 frozenset。

    做法是最單純的洪水填充（flood fill）：從 key 出發，一直往同色的鄰點走，
    走過的點記下來，走不動為止。這就是「連通分量」的定義照抄一遍。
    """
    pt = board._pt(key)
    color = board.grid[pt]
    if color == EMPTY:
        raise ValueError("find_string() 的起點必須有子")

    seen = {pt}
    frontier = [pt]
    while frontier:
        p = frontier.pop()
        for q in neighbors(p, board.n):
            if q not in seen and board.grid[q] == color:
                seen.add(q)
                frontier.append(q)
    return frozenset(seen)


def neighbor_set(S, n):
    """N(S) = ∪_{s∈S} N(s)，再扣掉 S 自己。

    這是「這塊棋緊貼著的所有點」，不管那些點上有沒有子。
    注意它是一個**並集** —— 兩顆子如果靠得近，會貢獻到同一個鄰點，
    而並集只會算一次。容斥原理就是從這裡冒出來的。
    """
    out = set()
    for s in S:
        out |= set(neighbors(s, n))
    return frozenset(out - set(S))


def liberties(board, S):
    """L(S) = N(S) \\ Occupied：這塊棋的氣，一個**集合**。"""
    return frozenset(p for p in neighbor_set(S, board.n) if board.grid[p] == EMPTY)


def liberty_count(board, key):
    """key 那一點所屬棋串的氣數 |L(S)|。這是大部分人講「幾口氣」時的意思。"""
    return len(liberties(board, find_string(board, key)))


def all_strings(board, color=None):
    """盤上所有棋串。color=None 表示黑白都要。回傳一個 frozenset 的 list。"""
    seen = set()
    out = []
    for p in board.points():
        v = int(board.grid[p])
        if v == EMPTY or p in seen:
            continue
        if color is not None and v != color:
            continue
        S = find_string(board, p)
        seen |= S
        out.append(S)
    return out


def shared_liberties(board, S1, S2):
    """兩塊棋共用的氣 L(S1) ∩ L(S2)。

    第 2 章 §4.3 的容斥項，也是第 4 章「公氣」的前身 ——
    同一個集合，在死活的脈絡下換了一個名字。
    """
    return liberties(board, S1) & liberties(board, S2)


def merged_liberty_count(board, S1, S2, connector):
    """在 connector 這一點落子、把 S1 與 S2 接起來以後，新棋串有幾口氣。

    第 2 章 §4.3 的容斥定理：接點 p 本來是雙方共同的氣，接上去以後
    它變成了子，所以要扣掉；而 p 自己帶來的新氣要加進來。

        |L(S1 ∪ S2 ∪ {p})| = |L(S1) ∪ L(S2) ∪ E(p)| - 1

    其中 E(p) 是 p 的空鄰點。右邊那個並集，用兩兩容斥展開就是
    |L1| + |L2| - |L1 ∩ L2| + （p 帶來的、原本不在裡面的新氣）。
    """
    p = board._pt(connector)
    a = liberties(board, S1)
    b = liberties(board, S2)
    e = {q for q in neighbors(p, board.n) if board.grid[q] == EMPTY}
    return len(a | b | e) - 1


def liberty_decomposition(board, S):
    """把 |L(S)| 拆成三項，這是第 2 章 §4.3 的主定理。

        |L(S)| = Σ_{s∈S} deg(s)  -  2·e(S)  -  Σ_{v 空} (mult(v) - 1)  -  (外子遮掉的)

    三項的意思：
      * Σ deg(s)      每顆子單獨看有幾個鄰點（角 2、邊 3、中央 4）
      * 2·e(S)        S 內部每一對相鄰的子，互相佔掉對方一個鄰點，所以扣兩次
      * Σ(mult-1)     一個空點若同時貼著 S 裡的 k 顆子，被重複數了 k-1 次
      * 外子遮掉的     鄰點上站著別人的子（或別的己方棋串），那不是氣

    第三項就是「愚形」的精確定義：**有空點被自己的兩顆子同時貼著，
    表示那兩顆子在做重複的工作。** 直三的第三項是 0，空三角是 1，
    所以空三角少一口氣。

    回傳一個 dict，方便在書上逐項對照。
    """
    n = board.n
    deg_sum = sum(len(neighbors(s, n)) for s in S)

    internal_pairs = 0
    for s in S:
        for q in neighbors(s, n):
            if q in S:
                internal_pairs += 1
    internal_pairs //= 2                      # 每一對被數了兩次

    mult = {}
    blocked = 0
    for s in S:
        for q in neighbors(s, n):
            if q in S:
                continue
            if board.grid[q] == EMPTY:
                mult[q] = mult.get(q, 0) + 1
            else:
                blocked += 1                   # 鄰點上是別人的子

    duplicated = sum(k - 1 for k in mult.values())
    total = deg_sum - 2 * internal_pairs - duplicated - blocked

    return {
        "deg_sum": deg_sum,
        "internal_pairs": internal_pairs,
        "duplicated": duplicated,
        "blocked": blocked,
        "liberties": total,
        "shared_empty_points": sorted(q for q, k in mult.items() if k >= 2),
    }
