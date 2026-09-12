"""眼：真眼與假眼的判定。

對應第 3 章 §4.4、§4.5。

這個檔案只實作兩條定義：

    眼位（eye-like point）：一個空點，它的【所有鄰點】都是同一色的子。
    真眼：眼位，而且對方控制的【對角點】夠少 ——

        真眼  <=>  d_opp(v) + 1[v 在邊緣] <= 1

    這條不等式就是「中央三、邊上二、角上一」那句口訣。
    中央：v 有 4 個對角點，指示函數是 0，所以最多容許對方佔 1 個（己方要佔 3 個）。
    邊或角：指示函數是 1，所以對方一個都不能佔。

【重要的誠實聲明】上面的判定是**局部的**：它假設那些對角上的己方子本身是安全的。
真正可靠、而且可判定的活棋定義是 Benson 無條件活（go_core/benson.py，第 3 章 §4.6）。
本檔案的判定是給人用的快速規則，不是定理。
"""

from go_core.board import EMPTY, neighbors, diagonals, degree


def is_eye_like(board, pt, color=None):
    """pt 是不是一個「眼位」：空點，且所有鄰點都是同一色。

    回傳那個顏色；若不是眼位則回傳 None。
    """
    p = board._pt(pt)
    if board.grid[p] != EMPTY:
        return None
    nbrs = neighbors(p, board.n)
    colours = {int(board.grid[q]) for q in nbrs}
    if len(colours) != 1 or EMPTY in colours:
        return None
    c = colours.pop()
    if color is not None and c != color:
        return None
    return c


def diagonal_census(board, pt, color):
    """回傳 (己方佔的對角數, 對方佔的對角數, 空的對角數, 對角總數)。"""
    p = board._pt(pt)
    diag = diagonals(p, board.n)
    mine = sum(1 for q in diag if board.grid[q] == color)
    opp = sum(1 for q in diag if board.grid[q] not in (EMPTY, color))
    empty = len(diag) - mine - opp
    return mine, opp, empty, len(diag)


def is_true_eye(board, pt, color=None):
    """真眼判定：d_opp(v) + 1[v 在邊緣] <= 1。

    空的對角點算「還沒被對方佔」，所以這裡用的是樂觀判定 ——
    它回答的是「現在這一刻，這個眼是真的嗎」。
    """
    c = is_eye_like(board, pt, color)
    if c is None:
        return False
    p = board._pt(pt)
    _, opp, _, _ = diagonal_census(board, p, c)
    on_edge = 1 if degree(p, board.n) < 4 else 0
    return opp + on_edge <= 1


def is_false_eye(board, pt, color=None):
    """假眼：是眼位，但不是真眼。"""
    return is_eye_like(board, pt, color) is not None and not is_true_eye(board, pt, color)


def eye_report(board, pt):
    """給書上用的逐項報告，方便讀者對照那條不等式。"""
    p = board._pt(pt)
    c = is_eye_like(board, p)
    if c is None:
        return {"眼位": False}
    mine, opp, empty, total = diagonal_census(board, p, c)
    on_edge = 1 if degree(p, board.n) < 4 else 0
    return {
        "眼位": True,
        "顏色": "黑" if c == 1 else "白",
        "對角總數": total,
        "己方": mine,
        "對方": opp,
        "空": empty,
        "在邊緣": bool(on_edge),
        "判定式": (f"d_opp + 1[邊緣] = {opp} + {on_edge} = {opp + on_edge}"
                   f"  {'<=' if opp + on_edge <= 1 else '>'} 1"),
        "真眼": opp + on_edge <= 1,
    }


def true_eyes_of(board, S):
    """棋串 S 目前擁有的真眼（以點的集合回傳）。"""
    from go_core.strings import liberties
    colour = int(board.grid[next(iter(S))])
    out = set()
    for v in liberties(board, S):
        if is_eye_like(board, v, colour) is None:
            continue
        # 這個眼位的鄰點必須全部屬於 S 本身，才算是 S 的眼
        if not all(q in S for q in neighbors(v, board.n)):
            continue
        if is_true_eye(board, v, colour):
            out.add(v)
    return frozenset(out)
