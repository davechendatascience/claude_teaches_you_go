"""攻擊與治孤：死活（第 2 層）與溫度（第 3 層）耦合的地方。

對應第 12 章。

前面十章有一個反覆出現的前提：**局部要真的獨立，局部的結論才成立。**
而圍棋裡最不獨立的東西，就是一塊還沒活淨的棋 —— 它同時出現在兩個帳本上：

  * 第 2 層：它的死活是離散的（活或死），不受溫度遞減規律約束。
  * 第 3 層：它的存亡改變周圍每一個局部的溫度。

這個檔案把那個耦合寫成三個可以算的量：

1. `stake`          一塊棋的賭注 s + t（子數 + 它圍住的空點）。
2. `life_swing`     死活的擺盪 = **2 × stake**。死活是雙向的，所以要乘二。
3. `life_distance`  治孤距離：還要幾手才能達到 Benson 無條件活（第 3 章定理 3.10）。

而「大場不如急場」就變成一條可以比大小的不等式（見 `is_urgent`）。
"""

import numpy as np

from go_core.benson import benson_alive
from go_core.board import (BLACK, EMPTY, WHITE, Board, format_coord,
                           neighbors, opposite)
from go_core.strings import find_string, liberties


# ---------------------------------------------------------------- 賭注

def enclosed_empties(board, S):
    """S 這塊棋圍住的空點：空的連通區塊，而且只碰得到 S。

    「只碰得到 S」很重要 —— 碰得到別塊同色棋的空點不算這塊棋的本錢。
    """
    colour = int(board.grid[next(iter(S))])
    n = board.n
    out = set()
    seen = set()
    for p in board.points():
        if board.grid[p] != EMPTY or p in seen:
            continue
        region, frontier, touching = {p}, [p], set()
        seen.add(p)
        while frontier:
            q = frontier.pop()
            for r in neighbors(q, n):
                v = int(board.grid[r])
                if v == EMPTY:
                    if r not in seen:
                        seen.add(r)
                        region.add(r)
                        frontier.append(r)
                else:
                    touching.add((v, r))
        colours = {v for v, _ in touching}
        if colours == {colour} and all(r in S for _, r in touching):
            out |= region
    return frozenset(out)


def stake(board, S):
    """一塊棋的賭注 s + t：自己的子數，加上它圍住的空點數。

    這是「這塊棋活著值多少」—— 但**不是**它死活問題的價值。
    死活的價值是這個數的兩倍，見 `life_swing`。
    """
    return len(S) + len(enclosed_empties(board, S))


def life_swing(board, S):
    """死活的擺盪：活與死之間差幾目（中國規則數子）。

    定理 12.1：擺盪 = 2 x stake。

    理由是一句話：**死活是雙向的。** 活了，那 s + t 點是你的；
    死了，同樣那 s + t 點變成對方的。差額是兩倍，不是一倍。

    這個函式不套公式 —— 它真的把兩種結局各數一次子再相減。
    """
    from go_core.minimax import area_score

    colour = int(board.grid[next(iter(S))])
    foe = opposite(colour)
    region = enclosed_empties(board, S)

    alive = board.copy()                       # 活：這塊棋和它的地都算自己的
    dead = board.copy()                        # 死：整片變成對方的
    for p in S | region:
        dead.grid[p] = foe

    ab, aw = area_score(alive)
    db, dw = area_score(dead)
    mine = (ab - aw) if colour == BLACK else (aw - ab)
    theirs = (db - dw) if colour == BLACK else (dw - db)
    return mine - theirs


# ---------------------------------------------------------------- 治孤距離

def _candidate_moves(board, S, radius=0):
    """治孤只會下在自己這塊棋附近。

    預設（radius = 0）只看**這塊棋的氣加上它圍住的空點** —— 對「被包圍、
    只能在裡面做眼」的局面，那正是全部有意義的著點，而且集合很小。

    radius > 0 時再往外擴，用在需要**逃跑**（而不是做眼）的局面。
    分枝因子直接決定搜尋成本，所以這個函式的預設值很重要。
    """
    near = set(liberties(board, S)) | set(enclosed_empties(board, S))
    if radius:
        n = board.n
        for s in S:
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    if abs(dr) + abs(dc) > radius:
                        continue
                    p = (s[0] + dr, s[1] + dc)
                    if 0 <= p[0] < n and 0 <= p[1] < n and board.grid[p] == EMPTY:
                        near.add(p)
    return sorted(near)


def is_alive(board, S, colour):
    """S 所在的那塊棋，現在是不是 Benson 無條件活？"""
    pt = next(iter(S))
    if board.grid[pt] != colour:
        return False
    alive = benson_alive(board, colour, trace=False)
    return any(pt in chain for chain in alive)


def life_distance(board, S, colour, max_moves=4, radius=0):
    """治孤距離（對手不抵抗）：最少幾手能讓這塊棋 Benson 活？

    對手一直虛手，所以這是一個**下界** —— 實戰上只會更多。
    回傳 (手數, 著手序列)，達不到就回傳 (None, [])。

    這個下界仍然有用：它是「這塊棋離安全有多遠」最便宜的度量，
    而第 12 章 §4.4 會拿它和實際的攻防比較。
    """
    pt = next(iter(S))
    if is_alive(board, S, colour):
        return 0, []

    def go(b, depth, path):
        if depth == 0:
            return None
        for p in _candidate_moves(b, find_string(b, pt) if b.grid[pt] == colour
                                  else S, radius):
            t = b.copy()
            try:
                t.play(colour, p)
            except ValueError:
                continue
            if t.grid[pt] != colour:
                continue
            if is_alive(t, find_string(t, pt), colour):
                return path + [p]
            sub = go(t, depth - 1, path + [p])
            if sub is not None:
                return sub
        return None

    for k in range(1, max_moves + 1):
        found = go(board.copy(), k, [])
        if found is not None:
            return len(found), found
    return None, []


def life_distance_contested(board, S, colour, max_moves=3, radius=0):
    """治孤距離（對手全力抵抗）：AND-OR 搜尋。

    守方是 OR 節點（有一條路活就行），攻方是 AND 節點（每一種抵抗都要擋住）。
    回傳能在 max_moves 手內活成的最小手數，活不了回傳 None。

    這比 `life_distance` 貴得多，所以只用在小局部上。
    """
    pt = next(iter(S))
    foe = opposite(colour)

    def defend(b, budget):
        if b.grid[pt] != colour:
            return None
        if is_alive(b, find_string(b, pt), colour):
            return 0
        if budget == 0:
            return None
        best = None
        for p in _candidate_moves(b, find_string(b, pt), radius):
            t = b.copy()
            try:
                t.play(colour, p)
            except ValueError:
                continue
            if t.grid[pt] != colour:
                continue
            got = attack(t, budget - 1)
            if got is not None and (best is None or got + 1 < best):
                best = got + 1
        return best

    def attack(b, budget):
        """攻方走。回傳守方之後還要幾手（取最大 = 最頑強的抵抗）。"""
        if b.grid[pt] != colour:
            return None
        if is_alive(b, find_string(b, pt), colour):
            return 0
        worst = defend(b, budget)               # 攻方也可以虛手
        if worst is None:
            return None
        for p in _candidate_moves(b, find_string(b, pt), radius):
            t = b.copy()
            try:
                t.play(foe, p)
            except ValueError:
                continue
            got = defend(t, budget)
            if got is None:
                return None                     # 攻方有一手能殺，守方就活不了
            worst = max(worst, got)
        return worst

    return defend(board.copy(), max_moves)


def vital_points(board, S, colour):
    """所有「下一手就能讓這塊棋 Benson 活」的點。

    做活點越多，攻方越難殺 —— 因為**一手只能佔一個**（第 3 章的鴿籠原理，
    這是它在本書第五次出現）。
    """
    out = []
    for p in _candidate_moves(board, S, radius=0):
        t = board.copy()
        try:
            t.play(colour, p)
        except ValueError:
            continue
        if t.grid[p] != colour:
            continue
        if is_alive(t, find_string(t, p), colour):
            out.append(p)
    return sorted(out)


def can_kill(board, S, colour, max_moves=3, radius=0):
    """**攻方先走**，殺得掉嗎？

    這是死活題的標準問法，和 `life_distance_contested`（守方先走）互補。
    回傳 True 表示攻方先手能殺。
    """
    foe = opposite(colour)
    pt = next(iter(S))

    def killed(b):
        return b.grid[pt] != colour

    def attacker(b, budget):
        """攻方走。能不能殺？"""
        if killed(b):
            return True
        if is_alive(b, find_string(b, pt), colour):
            return False
        if budget == 0:
            return False
        for p in _candidate_moves(b, find_string(b, pt), radius):
            t = b.copy()
            try:
                t.play(foe, p)
            except ValueError:
                continue
            if defender(t, budget - 1):
                return True
        return False

    def defender(b, budget):
        """守方走。攻方還殺得掉嗎？（守方每一種應法都殺得掉才算殺得掉）"""
        if killed(b):
            return True
        if is_alive(b, find_string(b, pt), colour):
            return False
        moves = _candidate_moves(b, find_string(b, pt), radius)
        if not moves:
            return True
        for p in moves:
            t = b.copy()
            try:
                t.play(colour, p)
            except ValueError:
                continue
            if t.grid[pt] != colour:
                continue
            if not attacker(t, budget):
                return False               # 守方有一手活得了
        return True

    return attacker(board.copy(), max_moves)


# ------------------------------------------------- 急場 vs 大場

def urgency(board, S):
    """一塊未定的棋，把它所在的局部變得多熱？

    形式化：如果我先下就活（我得 stake），對手先下就死（對方得 stake），
    那個局部就是一個開關
        G = { +stake | -stake }
    依第 7 章命題 7.3，它的溫度是 stake、均值是 0。

    **未定塊的溫度 = 它的賭注。** 這就是「急場」的溫度。
    """
    return stake(board, S)


def as_switch(board, S):
    """把未定的一塊棋寫成第 6 章的賽局值 { +stake | -stake }。"""
    from go_core.cgt import switch

    k = stake(board, S)
    return switch(k, -k)


def is_urgent(board, S, global_temperature):
    """「大場不如急場」的判定式。

    急場 <=> stake > T'（除了這塊棋以外的全局溫度）

    這不是新原則 —— 它就是第 7 章的溫度排序（策略 7.9）：先下最熱的。
    未定塊的溫度是 stake，所以只要 stake 比最大的大場還熱，它就該先下。

    回傳 (是不是急場, stake, 差額)。
    """
    k = stake(board, S)
    return k > global_temperature, k, k - global_temperature


def should_abandon(board, S, global_temperature, moves_needed=None,
                   max_moves=4):
    """棄子的判定式（啟發式，不是定理）。

    救活要花 d 手，而那 d 手本來可以拿去下別處值 T' 的地方。
    所以粗略地說：

        值得救  <=>  2 x stake  >  d x T'

    左邊是死活的擺盪（定理 12.1），右邊是機會成本。

    **這是啟發式**：它假設對手不會因為你救棋而額外獲利，也忽略了
    救棋過程本身可能製造的厚勢（第 9 章那筆算不清的帳）。
    回傳 (該不該棄, 擺盪, 機會成本, 需要幾手)。
    """
    colour = int(board.grid[next(iter(S))])
    if moves_needed is None:
        moves_needed, _ = life_distance(board, S, colour, max_moves=max_moves)
    swing = life_swing(board, S)
    if moves_needed is None:                    # 救不活
        return True, swing, float("inf"), None
    cost = moves_needed * global_temperature
    return swing <= cost, swing, cost, moves_needed


# ---------------------------------------------------------------- 報告

def group_report(board, S, global_temperature=None):
    """把一塊棋的攻防狀態整理成一份表。"""
    colour = int(board.grid[next(iter(S))])
    d, path = life_distance(board, S, colour)
    out = {
        "colour": colour,
        "stones": len(S),
        "territory": len(enclosed_empties(board, S)),
        "stake": stake(board, S),
        "swing": life_swing(board, S),
        "liberties": len(liberties(board, S)),
        "alive": is_alive(board, S, colour),
        "life_distance": d,
        "life_path": [format_coord(p, board.n) for p in path],
    }
    if global_temperature is not None:
        urgent, k, margin = is_urgent(board, S, global_temperature)
        out["urgent"] = urgent
        out["margin"] = margin
    return out
