"""Benson 無條件活：一個真正可判定的「活」。

對應第 3 章 §4.6。

「兩眼活」是一條好規則，但它不是定義 —— 眼可能是假的、可能還沒做出來、
可能要靠應手才成立。Benson（1976）給了一個更強、而且**電腦可以在多項式時間內
判定**的概念：

    無條件活（unconditionally alive）：就算我從現在起【永遠不應】，
    對手也吃不掉這塊棋。

演算法是一個「一直刪到刪不動為止」的迭代，也就是求一個單調算子的**最大不動點**：

    X = 我方所有棋串
    R = 所有「被我方圍住的區域」
    重複：
        1. 從 R 刪掉那些「有鄰接棋串已經不在 X 裡」的區域
        2. 從 X 刪掉那些「在 R 裡的 vital 區域少於 2 個」的棋串
    直到 X 與 R 都不再變小。

其中「區域 R 對棋串 X 而言是 vital 的」，意思是 **R 裡的每一個空點都是 X 的氣**。

剩下的 X 就是無條件活的。兩個 vital 區域，正是「兩個眼」這件事的正確推廣 ——
它允許眼比一個點大，也自動排除了假眼。
"""

from go_core.board import EMPTY, neighbors
from go_core.strings import find_string, liberties, all_strings


def enclosed_regions(board, color):
    """所有「被 color 圍住的區域」。

    區域的定義：由【非 color】的點（空點或對方的子）構成的連通分量，
    而且它的所有外鄰點都是 color 的子。

    回傳一個 list，每個元素是該區域的點集合（frozenset）。
    """
    n = board.n
    seen = set()
    out = []
    for p in board.points():
        if p in seen or board.grid[p] == color:
            continue
        # 洪水填充出這個非 color 的連通分量
        comp = {p}
        frontier = [p]
        while frontier:
            q = frontier.pop()
            for r in neighbors(q, n):
                if r not in comp and board.grid[r] != color:
                    comp.add(r)
                    frontier.append(r)
        seen |= comp
        # 它的外鄰點是否全都是 color？
        border = {r for q in comp for r in neighbors(q, n) if r not in comp}
        if border and all(board.grid[r] == color for r in border):
            out.append(frozenset(comp))
    return out


def is_vital(board, region, chain):
    """區域 region 對棋串 chain 而言是 vital 的嗎？

    定義：region 裡的【每一個空點】都是 chain 的氣。
    （region 裡的對方死子不算 —— 它們遲早會被提掉，提掉之後才變成空點。）
    """
    libs = liberties(board, chain)
    empties = {p for p in region if board.grid[p] == EMPTY}
    if not empties:
        return False
    return empties <= libs


def benson_alive(board, color, trace=False):
    """回傳 color 這一方所有無條件活的棋串（frozenset 的 set）。

    trace=True 時，同時回傳每一輪迭代的紀錄，方便書上逐步展示。
    """
    n = board.n
    X = set(all_strings(board, color))
    R = set(enclosed_regions(board, color))
    log = []

    round_no = 0
    while True:
        round_no += 1
        before = (len(X), len(R))

        # 步驟 1：區域的所有鄰接棋串都必須還在 X 裡
        R2 = set()
        for r in R:
            nbr_chains = set()
            ok = True
            for p in r:
                for q in neighbors(p, n):
                    if board.grid[q] == color:
                        ch = find_string(board, q)
                        nbr_chains.add(ch)
            for ch in nbr_chains:
                if ch not in X:
                    ok = False
                    break
            if ok:
                R2.add(r)
        R = R2

        # 步驟 2：棋串至少要有兩個 vital 區域
        X2 = set()
        for ch in X:
            vitals = [r for r in R if is_vital(board, r, ch)]
            if len(vitals) >= 2:
                X2.add(ch)
        X = X2

        after = (len(X), len(R))
        log.append({"round": round_no, "chains": after[0], "regions": after[1]})
        if after == before:
            break

    return (X, log) if trace else X


def benson_status(board):
    """全盤報告：每一塊棋是不是無條件活。回傳 {frozenset: (顏色, 是否無條件活)}。"""
    from go_core.board import BLACK, WHITE
    out = {}
    for colour in (BLACK, WHITE):
        alive = benson_alive(board, colour)
        for ch in all_strings(board, colour):
            out[ch] = (colour, ch in alive)
    return out
