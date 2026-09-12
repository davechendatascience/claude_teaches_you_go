"""征子：一條斜線，以及它的陰影。

對應第 8 章 §4.4。

征子（ladder／シチョウ）是圍棋裡少數幾個「可以完全算清楚」的東西之一：
攻方一路叫吃、守方一路長，路徑是一條 45 度的階梯，走到盤邊就結束。

這個檔案做兩件事：

1. `ladder_capture`  —— 把征子讀完，回傳能不能吃到，以及走過的路徑。
2. `ladder_shadow`   —— **把「征子引徵」的範圍算出來**：盤上每一點都試一遍，
                        看放一顆守方的子在那裡會不會讓征子失敗。

第二件事值得特別說明。傳統教材會說「征子引徵要在征子的路線上」，然後畫一條
斜線。本書不畫那條線 —— 它是**算出來的**：對每一個空點，放一顆子、重跑一次
征子、看結果有沒有翻轉。翻轉的那些點所成的集合，就是陰影。
"""

from go_core.board import BLACK, EMPTY, WHITE, format_coord, neighbors, opposite
from go_core.strings import find_string, liberties


def ladder_capture(board, target, attacker, max_depth=120):
    """攻方先手，能不能用征子吃掉 target 這塊棋？

    回傳 (能不能, 路徑)。路徑是 [(顏色, 點), ...]，記錄雙方實際走過的每一手。

    讀法是一棵很窄的 AND-OR 樹（第 4 章 §4.5）：
      * 攻方（OR）：目標有 2 口氣時，攻方可以叫吃任一口 —— 兩種都試。
      * 守方（AND）：被叫吃時，守方可以長、也可以反提攻方的子 —— 每一種都要擋住。
    分枝因子只有 2 到 3，所以雖然深度可能上百手，還是算得動。
    """
    defender = opposite(attacker)
    memo = {}

    def go(b, to_move, depth, path):
        if depth > max_depth:
            return False, path            # 讀不完就當作跑掉了（保守）
        key = (b.grid.tobytes(), to_move)
        if key in memo:
            return memo[key]
        memo[key] = (False, path)         # 防遞迴（劫）

        pt = b._pt(target)
        if b.grid[pt] != defender:
            return True, path             # 已經被提掉了

        S = find_string(b, target)
        L = liberties(b, S)
        if len(L) >= 3:
            memo[key] = (False, path)
            return False, path            # 三口氣就跑掉了，不是征子

        if to_move == attacker:
            for p in sorted(L):
                t = b.copy()
                try:
                    t.play(attacker, p)
                except ValueError:
                    continue
                if t.grid[pt] != defender:
                    return True, path + [(attacker, p)]
                ok, sub = go(t, defender, depth + 1, path + [(attacker, p)])
                if ok:
                    memo[key] = (True, sub)
                    return True, sub
            memo[key] = (False, path)
            return False, path

        # 守方：長、或反提攻方的子。任何一種能活下來，征子就失敗。
        cands = set(L)
        for s in S:
            for q in neighbors(s, b.n):
                if b.grid[q] == attacker:
                    T = find_string(b, q)
                    if len(liberties(b, T)) == 1:
                        cands |= liberties(b, T)      # 反提
        longest = path
        for p in sorted(cands):
            if b.grid[p] != EMPTY:
                continue
            t = b.copy()
            try:
                t.play(defender, p)
            except ValueError:
                continue
            if t.grid[pt] != defender:
                continue                   # 自己把自己下沒了
            ok, sub = go(t, attacker, depth + 1, path + [(defender, p)])
            if not ok:
                memo[key] = (False, sub)
                return False, sub
            # 守方這一手擋不住。記下它的續著，好把完整的征子路徑報出來。
            if len(sub) > len(longest):
                longest = sub
        memo[key] = (True, longest)
        return True, longest

    return go(board.copy(), attacker, 0, [])


def ladder_path(board, target, attacker, max_depth=120):
    """只要路徑（不管成不成功）。方便畫圖。"""
    return ladder_capture(board, target, attacker, max_depth)[1]


def ladder_shadow(board, target, attacker, max_depth=120, region=None):
    """**征子陰影**：哪些點放一顆守方的子，會讓征子失敗？

    做法很直接：對每一個空點，放一顆守方的子，重跑一次征子，看結果有沒有翻轉。
    翻轉的那些點所成的集合，就是「征子引徵」的有效範圍。

    這不是一條畫出來的斜線 —— 它是算出來的。回傳一個點的 frozenset。
    """
    defender = opposite(attacker)
    base, _ = ladder_capture(board, target, attacker, max_depth)
    if not base:
        return frozenset()                # 本來就征不到，談不上陰影

    pts = region if region is not None else list(board.points())
    out = set()
    S = find_string(board, target)
    for p in pts:
        p = board._pt(p)
        if board.grid[p] != EMPTY or p in S:
            continue
        t = board.copy()
        t.grid[p] = defender
        try:
            ok, _ = ladder_capture(t, target, attacker, max_depth)
        except RecursionError:
            continue
        if not ok:
            out.add(p)
    return frozenset(out)


def describe_path(path, n):
    return " ".join(f"{'黑' if c == BLACK else '白'}{format_coord(p, n)}"
                    for c, p in path)
