"""死活搜尋：AND-OR 樹。

對應第 4 章 §4.5。

「讀棋」這件事，形式化之後就是在一棵樹上做深度優先搜尋。樹有兩種節點：

    OR  節點（輪到我）：只要【有一個】子節點成功，這個節點就成功。
    AND 節點（輪到對手）：必須【每一個】子節點都成功，這個節點才成功。

這就是為什麼讀棋那麼累：OR 節點你可以挑最好的一手，AND 節點你必須把對手
所有的回應都算一遍。工作量大約是 b^d（b 是分枝因子、d 是深度），而 b 和 d
都不用大，乘起來就超過人的工作記憶。

【範圍】這裡的搜尋只在一個指定的小區域裡進行（candidates），而且沒有處理劫
（那是第 5 章）。它足以解本書用到的死活題，不是一個完整的引擎。
"""

from go_core.board import BLACK, WHITE, EMPTY, opposite, neighbors
from go_core.strings import find_string, liberties


def region_of_interest(board, target, radius=1):
    """target 這塊棋周圍值得考慮的落點：它的氣，加上氣的鄰點。"""
    S = find_string(board, target)
    pts = set(liberties(board, S))
    for _ in range(radius - 1):
        pts |= {q for p in pts for q in neighbors(p, board.n)}
    return frozenset(p for p in pts if board.grid[p] == EMPTY)


def _key(board, to_move, candidates):
    """把盤面壓成一個可雜湊的鍵，只保留候選區域與 target 周邊。"""
    return (board.grid.tobytes(), to_move)


def can_capture(board, target, attacker, candidates=None, max_depth=12,
                _memo=None, _depth=0, _to_move=None):
    """攻方（attacker）先手，能不能提掉 target 這塊棋？

    回傳 (能不能, 第一手下在哪)。第一手是 None 表示不需要下 / 找不到。

    這是一棵 AND-OR 樹：
      * attacker 走的層是 OR   —— 有一手能成功就算成功
      * 防守方走的層是 AND     —— 對手所有的回應都必須擋不住
    """
    defender = opposite(attacker)
    if _to_move is None:
        _to_move = attacker
    if _memo is None:
        _memo = {}
    if candidates is None:
        candidates = region_of_interest(board, target, radius=2)

    # 終止條件：target 已經不在盤上了
    if board.grid[board._pt(target)] != defender:
        return True, None
    if _depth >= max_depth:
        return False, None

    k = (_key(board, _to_move, candidates), _depth)
    if k in _memo:
        return _memo[k]

    moves = [p for p in candidates if board.grid[p] == EMPTY]

    if _to_move == attacker:
        # OR 節點：試每一手，有一手成功就成功
        result = (False, None)
        for m in moves:
            t = board.copy()
            try:
                t.play(attacker, m)
            except ValueError:
                continue
            ok, _ = can_capture(t, target, attacker, candidates, max_depth,
                                _memo, _depth + 1, defender)
            if ok:
                result = (True, m)
                break
        _memo[k] = result
        return result

    # AND 節點：防守方可以下，也可以虛手。任何一種能活下來，攻方就失敗。
    for m in moves + [None]:
        if m is None:
            t = board            # 虛手
        else:
            t = board.copy()
            try:
                t.play(defender, m)
            except ValueError:
                continue
            if t.grid[t._pt(target)] != defender:
                # 自己把自己下沒了（例如提到自己），視為防守失敗的一種
                continue
        ok, _ = can_capture(t, target, attacker, candidates, max_depth,
                            _memo, _depth + 1, attacker)
        if not ok:
            _memo[k] = (False, None)
            return (False, None)
    _memo[k] = (True, None)
    return (True, None)


def net_moves_to_capture(board, target, attacker, candidates, max_depth=30,
                         _memo=None, _depth=0, _to_move=None):
    """【淨手數】：攻方的手數，減掉守方在同一個區域裡被迫陪下的手數。

    這就是「大眼氣數」那張口訣表上的數字（三目三氣、四目五氣、五目八氣、
    六目十二氣）。它不是「攻方要下幾手」—— 攻方要下的手數更多，因為守方
    會在中途提掉攻方的子，逼攻方重填。

    為什麼要減？因為在對殺裡，守方在眼內下的每一手，都是他【沒有】拿去填
    對方氣的一手。所以那些手在帳上是攻方賺到的 tempo，要從成本裡扣掉。

    回傳淨手數；若守方守得住（例如那根本是活形）則回傳 None。
    """
    from go_core.board import opposite
    defender = opposite(attacker)
    if _to_move is None:
        _to_move = attacker
    if _memo is None:
        _memo = {}

    if board.grid[board._pt(target)] != defender:
        return 0
    if _depth >= max_depth:
        return None

    k = (board.grid.tobytes(), _to_move)
    if k in _memo:
        return _memo[k]
    _memo[k] = None                       # 防止無窮遞迴

    moves = [p for p in candidates if board.grid[p] == EMPTY]

    if _to_move == attacker:
        best = None
        for m in moves:
            t = board.copy()
            try:
                t.play(attacker, m)
            except ValueError:
                continue
            sub = net_moves_to_capture(t, target, attacker, candidates, max_depth,
                                       _memo, _depth + 1, defender)
            if sub is None:
                continue
            if best is None or 1 + sub < best:
                best = 1 + sub
        _memo[k] = best
        return best

    worst = 0
    for m in moves + [None]:
        if m is None:
            t = board                      # 守方虛手
        else:
            t = board.copy()
            try:
                t.play(defender, m)
            except ValueError:
                continue
            if t.grid[t._pt(target)] != defender:
                continue
        sub = net_moves_to_capture(t, target, attacker, candidates, max_depth,
                                   _memo, _depth + 1, attacker)
        if sub is None:
            _memo[k] = None                # 守方有辦法活下來
            return None
        # 守方下一手，攻方的淨成本就少一手
        worst = max(worst, sub - (0 if m is None else 1))
    _memo[k] = worst
    return worst


def moves_to_capture(board, target, attacker, candidates=None, max_depth=16,
                     _memo=None, _depth=0, _to_move=None):
    """攻方要幾手才提得掉 target？攻方求最少，守方求最多。

    回傳攻方實際落子的手數；提不掉則回傳 None（在 max_depth 之內）。

    這就是「大眼氣數」的定義：一塊只剩一個大眼的棋，對手要花幾手才吃得掉。
    傳統上這個數字是一張要背的表（三目三氣、四目五氣……）；
    這個函式把它算出來。
    """
    defender = opposite(attacker)
    if _to_move is None:
        _to_move = attacker
    if _memo is None:
        _memo = {}
    if candidates is None:
        candidates = region_of_interest(board, target, radius=2)

    if board.grid[board._pt(target)] != defender:
        return 0
    if _depth >= max_depth:
        return None

    k = (_key(board, _to_move, candidates), _depth)
    if k in _memo:
        return _memo[k]

    moves = [p for p in candidates if board.grid[p] == EMPTY]

    if _to_move == attacker:
        best = None
        for m in moves:
            t = board.copy()
            try:
                t.play(attacker, m)
            except ValueError:
                continue
            sub = moves_to_capture(t, target, attacker, candidates, max_depth,
                                   _memo, _depth + 1, defender)
            if sub is None:
                continue
            cost = 1 + sub          # 攻方這一手也要算
            if best is None or cost < best:
                best = cost
        _memo[k] = best
        return best

    # 防守方：求最多（拖得越久越好）。虛手也是一個選項。
    worst = 0
    for m in moves + [None]:
        if m is None:
            t = board
        else:
            t = board.copy()
            try:
                t.play(defender, m)
            except ValueError:
                continue
            if t.grid[t._pt(target)] != defender:
                continue
        sub = moves_to_capture(t, target, attacker, candidates, max_depth,
                               _memo, _depth + 1, attacker)
        if sub is None:
            _memo[k] = None          # 防守方有辦法永遠不死
            return None
        worst = max(worst, sub)
    _memo[k] = worst
    return worst
