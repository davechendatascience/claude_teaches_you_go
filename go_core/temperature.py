"""溫度與均值：一個賽局的兩個數。

對應第 7 章。

第 6 章把每個局部變成一個組合賽局值，但那個值（例如 `{2 | {1 | *}}`）
沒辦法拿來排序 —— 你沒辦法說它「大概值幾目」，也沒辦法說「現在下值不值得」。

這個檔案給每個賽局兩個【數】：

    均值 m(G)   雙方輪流下到底，平均會落在幾目     -> 形勢判斷用這個
    溫度 t(G)   現在在這裡下一手，能賺幾目         -> 收官排序用這個

兩者由【熱圖】（thermograph）同時定義。熱圖的想法是：
給整盤棋加一個「稅」t —— 每下一手都要付 t 目。稅越重，越沒有人想動。
稅重到某個程度時，雙方都不想先下了，這個局部就凝固成一個數。

    那個「剛好凝固」的稅率就是溫度 t(G)，凝固後的值就是均值 m(G)。

【重要的對照】圍棋的傳統術語，其實就是這兩個數：

    見合計算（miai counting）   = 溫度 t(G)
    出入計算（deiri counting）  = 2 x 溫度

所以「這手棋 6 目（見合）」和「這手棋 12 目（出入）」講的是同一手棋。
第 7 章 §4.4 會證明這件事。
"""

from fractions import Fraction

from go_core.cgt import Game, ZERO, number


_CACHE = {}
_MAX_T = Fraction(1000)          # 溫度的搜尋上界；圍棋局部不會超過這個


def _as_number(g):
    """如果 g 是一個數就回傳它，否則 None。用 CGT 的簡單性規則。"""
    from go_core.cgt import _simplicity
    return _simplicity(g)


def analyse(g):
    """回傳 (溫度, 均值)。兩者都是 Fraction。

    數的溫度是 -1（Conway 的慣例：數比任何「熱」的東西都冷）。
    本書為了讀者好懂，把它報成 0 —— 見 `temperature()`。
    """
    if g._key in _CACHE:
        return _CACHE[g._key]
    _CACHE[g._key] = (Fraction(0), Fraction(0))     # 防遞迴

    n = _as_number(g)
    if n is not None:
        out = (Fraction(0), n)
        _CACHE[g._key] = out
        return out

    # 二分搜尋：找出最小的 t 使得左牆不再高於右牆
    lo, hi = Fraction(0), _MAX_T
    for _ in range(60):
        mid = (lo + hi) / 2
        if _left_raw(g, mid) <= _right_raw(g, mid):
            hi = mid
        else:
            lo = mid
    t = hi.limit_denominator(2 ** 20)
    # 校正：確保 t 真的是交會點（二分可能差一點點）
    for cand in (t, t.limit_denominator(2 ** 12), t.limit_denominator(2 ** 8)):
        if _left_raw(g, cand) <= _right_raw(g, cand):
            t = min(t, cand)
    m = _left_raw(g, t)
    out = (t, m)
    _CACHE[g._key] = out
    return out


def temperature(g):
    """t(G)：現在在這個局部下一手，能賺幾目。

    這就是圍棋的【見合計算】。出入計算是它的兩倍。
    """
    return analyse(g)[0]


def mean(g):
    """m(G)：雙方輪流下到底，平均落在幾目。形勢判斷要用的就是這個。"""
    return analyse(g)[1]


def _wall_left(g, t):
    """熱圖的左牆 L_G(t)：稅率 t 之下，黑先手的結果。"""
    tG, mG = analyse(g)
    if t >= tG:
        return mG
    return _left_raw(g, t)


def _wall_right(g, t):
    """熱圖的右牆 R_G(t)：稅率 t 之下，白先手的結果。"""
    tG, mG = analyse(g)
    if t >= tG:
        return mG
    return _right_raw(g, t)


def _left_raw(g, t):
    """黑先手：走到最好的 G^L，然後付 t 目的稅。"""
    n = _as_number(g)
    if n is not None:
        return n
    if not g.left:
        return -_MAX_T
    return max(_wall_right(gl, t) for gl in g.left) - t


def _right_raw(g, t):
    """白先手：走到最好的 G^R，然後付 t 目的稅（對白而言是加）。"""
    n = _as_number(g)
    if n is not None:
        return n
    if not g.right:
        return _MAX_T
    return min(_wall_left(gr, t) for gr in g.right) + t


def thermograph(g, steps=None):
    """回傳熱圖上的一串點 [(t, 左牆, 右牆), ...]，方便畫圖或列表。"""
    tG, mG = analyse(g)
    if steps is None:
        steps = sorted({Fraction(0), tG,
                        *(tG * Fraction(k, 8) for k in range(9))})
    return [(t, _wall_left(g, t), _wall_right(g, t)) for t in steps]


def deiri(g):
    """出入計算的值 = 2 x 溫度。傳統圍棋書上的「這手棋 N 目」多半是這個。"""
    return 2 * temperature(g)


def miai(g):
    """見合計算的值 = 溫度本身。"""
    return temperature(g)


# ------------------------------------------------------------ 收官

def is_settled(g):
    """這個局部收完了嗎？—— 也就是它的值已經是一個【數】。

    這裡有一個容易踩的坑：在 CGT 裡，數【形式上仍然有選項】
    （$n = \\{n-1 \\mid\\}$ 就是它被建構出來的方式）。但在圍棋裡，
    一個已經定型的局部沒有人會去下 —— 下了就是自填（第 6 章 §4.4）。

    所以收官程式必須把「是數」當成終局條件，而不是「沒有著手」。
    忘記這一點，程式會在已經定型的地裡一路往下填，算出荒謬的結果。
    """
    return _as_number(g) is not None


def best_move_value(g, colour, by="thermograph"):
    """在這個局部下一手，該走哪一個選項？

    這裡有兩個判準，而**選錯判準會讓「大的先下」失效** ——
    這是第 7 章 §4.6 花了不少篇幅處理的一件事：

      by="mean"         挑均值最好的選項。**這是錯的。**
                        它會忽略「那一手之後還有沒有後續手段」。
      by="thermograph"  挑熱圖說的那一手：在當前溫度 t 之下，
                        黑挑 R 牆最高的選項、白挑 L 牆最低的。**這才是對的。**

    回傳 (走到的賽局, 那個賽局的均值)；沒有著手則回傳 (None, None)。
    """
    options = g.left if colour == "black" else g.right
    if not options:
        return None, None
    if by == "mean":
        key = mean
        pick = max(options, key=key) if colour == "black" else min(options, key=key)
        return pick, mean(pick)

    t = temperature(g)
    if colour == "black":
        pick = max(options, key=lambda x: (_wall_right(x, t), mean(x)))
    else:
        pick = min(options, key=lambda x: (_wall_left(x, t), mean(x)))
    return pick, mean(pick)


def play_greedy(games, first="black", by="thermograph"):
    """貪婪收官：每一手都挑【溫度最高】的局部下。

    回傳 (最終總分, 著手紀錄)。總分以黑為正。

    這就是「大的先下」。第 7 章 §4.6 會證明它離最優解不遠 ——
    而且會給出「不遠」到底是多遠。
    """
    live = list(games)
    colour = first
    log = []
    total = Fraction(0)
    while True:
        # 只考慮還有著手的局部
        movable = [i for i, g in enumerate(live)
                   if not is_settled(g)
                   and (g.left if colour == "black" else g.right)]
        if not movable:
            break
        i = max(movable, key=lambda j: temperature(live[j]))
        before = live[i]
        nxt, _ = best_move_value(before, colour, by=by)
        log.append((colour, i, temperature(before)))
        live[i] = nxt
        colour = "white" if colour == "black" else "black"
    for g in live:
        total += mean(g)
    return total, log


def play_optimal(games, first="black", _memo=None):
    """完全搜尋：把整個和當成一個賽局，算出雙方最優時的最終總分。

    回傳一個 Fraction（黑為正）。只適用於小規模 —— 這是拿來驗證貪婪法的。
    """
    if _memo is None:
        _memo = {}
    key = (tuple(sorted(g._key for g in games)), first)
    if key in _memo:
        return _memo[key]

    movable = [i for i, g in enumerate(games)
               if not is_settled(g)
               and (g.left if first == "black" else g.right)]
    if not movable:
        out = sum((mean(g) for g in games), Fraction(0))
        _memo[key] = out
        return out

    other = "white" if first == "black" else "black"
    results = []
    for i in movable:
        options = games[i].left if first == "black" else games[i].right
        for opt in options:
            nxt = list(games)
            nxt[i] = opt
            results.append(play_optimal(nxt, other, _memo))
    # 也允許「這裡不下了」—— 收官結束
    results.append(sum((mean(g) for g in games), Fraction(0)))
    out = max(results) if first == "black" else min(results)
    _memo[key] = out
    return out
