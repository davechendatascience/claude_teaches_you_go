"""組合賽局論（CGT）：把一個局部變成一個「數」。

對應第 6 章。

整個檔案建立在一條遞迴定義上：

    G = { G^L | G^R }

左邊是黑（Left）能走到的所有局面，右邊是白（Right）能走到的所有局面。
沒有別的東西 —— 沒有棋盤、沒有氣、沒有眼。純粹是「誰能走到哪」。

從這一條定義出發，可以推出：
  * 兩個互不干擾的局部可以【相加】，而且加法可交換、可結合。
  * 有些局部的值是一個【數】（包括 1/2、1/4 這種分數）。
  * 有些局部的值不是數（例如 * ），而那正好對應到圍棋裡的奇偶與單劫。

【約定】本書用 Left = 黑、Right = 白，而值越大對黑越好（以目計）。

【重要】這個檔案不處理劫。第 5 章 §4.6 說明了為什麼：劫材是跨局部的，
分離和的前提（局部互不干擾）在有劫時不成立。
"""

from fractions import Fraction
from functools import lru_cache


# ---------------------------------------------------------------- 賽局

class Game:
    """一個組合賽局 G = {L | R}。

    left、right 是 Game 的 frozenset。空集合表示那一方沒有著手。
    """

    __slots__ = ("left", "right", "_key", "_hash")

    def __init__(self, left=(), right=()):
        self.left = frozenset(left)
        self.right = frozenset(right)
        self._key = (frozenset(g._key for g in self.left),
                     frozenset(g._key for g in self.right))
        self._hash = hash(self._key)

    # ---- 基本結構 ---------------------------------------------------

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        other = _coerce(other)
        return _leq(self, other) and _leq(other, self)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __le__(self, other):
        return _leq(self, _coerce(other))

    def __lt__(self, other):
        other = _coerce(other)
        return _leq(self, other) and not _leq(other, self)

    def __ge__(self, other):
        return _coerce(other).__le__(self)

    def __gt__(self, other):
        return _coerce(other).__lt__(self)

    def __neg__(self):
        """-G = { -G^R | -G^L }：把黑白對調。"""
        return Game([-g for g in self.right], [-g for g in self.left])

    def __add__(self, other):
        """G + H = { G^L + H, G + H^L | G^R + H, G + H^R }。

        白話：在「兩個局部並存」的盤面上，輪到你的時候你可以選一個局部下。
        這條式子就是第 6 章 §4.2 的分離和，也是全書最大的槓桿。
        """
        other = _coerce(other)
        return _add(self, other)

    __radd__ = __add__

    def __sub__(self, other):
        return self + (-_coerce(other))

    # ---- 勝負與值 ---------------------------------------------------

    def outcome(self):
        """回傳這個局部的勝負類別（正常規則：不能走的人輸）。

            "黑勝"   G > 0，不管誰先手黑都贏
            "白勝"   G < 0
            "先手勝" G || 0，誰先走誰贏（fuzzy）
            "後手勝" G = 0，誰先走誰輸
        """
        zero = ZERO
        gt, lt = _leq(zero, self), _leq(self, zero)
        if gt and not lt:
            return "黑勝"
        if lt and not gt:
            return "白勝"
        if gt and lt:
            return "後手勝"
        return "先手勝"

    def canonical(self):
        """化成標準形。兩條化簡規則，兩者都是 CGT 的標準結果：

        1. **消除被支配的選項**：黑的兩個選項如果 A <= B，那 A 永遠不會被選，刪掉。
           白的兩個選項如果 A >= B，同理刪掉。
           （白話：有更好的走法就不會走差的。）

        2. **繞過可逆著手**：如果黑走到 G^L，而白在那裡有一個回應 G^LR 滿足
           G^LR <= G，那黑走 G^L 等於白白讓白把局面拉回來（甚至更糟）。
           這時可以把 G^L 換成 G^LR 的黑選項，直接跳過這一來一回。
           （白話：如果對手有一手能把你打回原形，那你那一手等於沒下。）

        化簡不會改變賽局的值 —— 但會讓值【看得懂】。沒有化簡，一條長度 4 的
        走廊會印出好幾千個字元；化簡之後通常只剩一行。
        """
        return _canonical(self)

    def as_number(self, max_denominator_exp=8, bound=40):
        """如果這個賽局的值是一個數，回傳那個 Fraction；否則回傳 None。

        先用【簡單性規則】（所有選項都是數的時候），失敗再退回窮舉比對。
        """
        n = _simplicity(self)
        if n is not None:
            return n
        for k in range(max_denominator_exp + 1):
            den = 2 ** k
            for p in range(-bound * den, bound * den + 1):
                cand = Fraction(p, den)
                if self == number(cand):
                    return cand
        return None

    def __repr__(self):
        n = _simplicity(self)
        if n is not None:
            return _fmt(n)
        if self == STAR:
            return "*"
        if self == UP:
            return "↑"
        if self == DOWN:
            return "↓"
        L = ", ".join(sorted(repr(g) for g in self.left)) or ""
        R = ", ".join(sorted(repr(g) for g in self.right)) or ""
        return "{" + L + " | " + R + "}"


def _fmt(fr):
    if fr.denominator == 1:
        return str(fr.numerator)
    return f"{fr.numerator}/{fr.denominator}"


def _coerce(x):
    if isinstance(x, Game):
        return x
    return number(x)


# ---------------------------------------------------------------- 比較

_LEQ_CACHE = {}


def _leq(g, h):
    """G <= H 的遞迴定義：

        G <= H  <=>  沒有 G^L 使 H <= G^L，且沒有 H^R 使 H^R <= G

    白話：如果黑走一步就能讓 G 追上 H，那 G 就不會真的比 H 小；
    如果白走一步就能讓 H 掉到 G 以下，那 H 也不會真的比 G 大。
    """
    key = (g._key, h._key)
    cached = _LEQ_CACHE.get(key)
    if cached is not None:
        return cached
    _LEQ_CACHE[key] = True                       # 樂觀假設，防止無窮遞迴
    result = (not any(_leq(h, gl) for gl in g.left)
              and not any(_leq(hr, g) for hr in h.right))
    _LEQ_CACHE[key] = result
    return result


_ADD_CACHE = {}


def _add(g, h):
    key = (g._key, h._key)
    cached = _ADD_CACHE.get(key)
    if cached is not None:
        return cached
    left = [_add(gl, h) for gl in g.left] + [_add(g, hl) for hl in h.left]
    right = [_add(gr, h) for gr in g.right] + [_add(g, hr) for hr in h.right]
    out = Game(left, right)
    _ADD_CACHE[key] = out
    return out


# ------------------------------------------------------------ 標準形

_CANON_CACHE = {}


def _dedupe(games):
    """把值相等的選項合併成一個（用 == 比，不是用結構比）。"""
    out = []
    for g in games:
        if not any(_leq(g, h) and _leq(h, g) for h in out):
            out.append(g)
    return out


def _canonical(g):
    if g._key in _CANON_CACHE:
        return _CANON_CACHE[g._key]

    L = [_canonical(x) for x in g.left]
    R = [_canonical(x) for x in g.right]

    for _ in range(50):                          # 兩條規則交替套用到穩定為止
        cur = Game(L, R)
        before = cur._key

        # 規則 2：繞過可逆著手
        newL = []
        for gl in L:
            bypass = next((glr for glr in gl.right if _leq(glr, cur)), None)
            if bypass is not None:
                newL.extend(bypass.left)
            else:
                newL.append(gl)
        newR = []
        for gr in R:
            bypass = next((grl for grl in gr.left if _leq(cur, grl)), None)
            if bypass is not None:
                newR.extend(bypass.right)
            else:
                newR.append(gr)
        L, R = _dedupe(newL), _dedupe(newR)

        # 規則 1：消除被支配的選項
        L = [a for a in L
             if not any(_leq(a, b) and not _leq(b, a) for b in L)]
        R = [a for a in R
             if not any(_leq(b, a) and not _leq(a, b) for b in R)]
        L, R = _dedupe(L), _dedupe(R)

        if Game(L, R)._key == before:
            break

    out = Game(L, R)
    _CANON_CACHE[g._key] = out
    return out


# ---------------------------------------------------------------- 數

ZERO = Game()                                    # 0 = { | }：誰都不能走，先走的人輸


@lru_cache(maxsize=None)
def number(value):
    """把一個二進位分數（dyadic rational）造成賽局。

        0        = { | }
        n > 0    = { n-1 | }
        n < 0    = { | n+1 }
        p / 2^k  = { (p-1)/2^k | (p+1)/2^k }   （已約分，k >= 1）

    「二進位分數」是分母為 2 的冪次的分數：1、1/2、1/4、3/8……
    圍棋局部的值【只會】是這種數，不會出現 1/3 —— 第 6 章 §4.5 會解釋為什麼。
    """
    fr = Fraction(value)
    if fr == 0:
        return ZERO
    den = fr.denominator
    if den == 1:
        n = fr.numerator
        if n > 0:
            return Game([number(n - 1)], [])
        return Game([], [number(n + 1)])
    if den & (den - 1):
        raise ValueError(f"{fr} 的分母不是 2 的冪次；圍棋局部不會出現這種值")
    p = fr.numerator
    return Game([number(Fraction(p - 1, den))], [number(Fraction(p + 1, den))])


def _all_numbers(games):
    out = []
    for g in games:
        n = _simplicity(g)
        if n is None:
            return None
        out.append(n)
    return out


_SIMP_CACHE = {}


def _simplicity(g):
    """簡單性規則：若所有選項都是數，而且左邊全部 < 右邊全部，
    則 G 等於【嚴格夾在中間、分母最小】的那個二進位分數。

    這條規則就是「半目是怎麼冒出來的」的全部答案。
    """
    if g._key in _SIMP_CACHE:
        return _SIMP_CACHE[g._key]
    _SIMP_CACHE[g._key] = None                   # 防遞迴
    lefts = _all_numbers(g.left)
    rights = _all_numbers(g.right)
    if lefts is None or rights is None:
        return None
    lo = max(lefts) if lefts else None
    hi = min(rights) if rights else None
    if lo is not None and hi is not None and lo >= hi:
        return None                              # 這是一個「熱」的局部，不是數
    val = simplest_between(lo, hi)
    _SIMP_CACHE[g._key] = val
    return val


def simplest_between(lo, hi):
    """嚴格夾在 lo 與 hi 之間、最簡單的二進位分數。

    「最簡單」的順序：先找整數（絕對值最小的），沒有整數才找 1/2，
    再沒有才找 1/4……這正是為什麼圍棋官子會出現 1/2 與 1/4，
    卻永遠不會出現 1/3。
    """
    if lo is None and hi is None:
        return Fraction(0)
    if lo is None:                               # 只有上界
        return Fraction(min(0, _floor(hi) if hi != _floor(hi) else hi - 1))
    if hi is None:                               # 只有下界
        return Fraction(max(0, _ceil(lo) if lo != _ceil(lo) else lo + 1))
    # 有沒有整數夾在中間？取絕對值最小的那個
    n = _floor(lo) + 1
    while n < hi:
        if lo < n < hi:
            best = n
            # 在所有可行整數裡挑絕對值最小的
            cands = [m for m in range(_floor(lo) + 1, _ceil(hi)) if lo < m < hi]
            if cands:
                return Fraction(min(cands, key=lambda m: (abs(m), m)))
        n += 1
    # 沒有整數，逐級加細分母
    k = 1
    while k <= 30:
        den = 2 ** k
        p = _floor(lo * den) + 1
        while Fraction(p, den) <= lo:
            p += 1
        if Fraction(p, den) < hi:
            return Fraction(p, den)
        k += 1
    raise ValueError(f"找不到夾在 {lo} 與 {hi} 之間的二進位分數")


def _floor(x):
    return Fraction(x).numerator // Fraction(x).denominator


def _ceil(x):
    return -((-Fraction(x).numerator) // Fraction(x).denominator)


# ------------------------------------------------------- 幾個有名字的值

STAR = Game([ZERO], [ZERO])                      # * = {0 | 0}：誰先走誰贏
UP = Game([ZERO], [STAR])                        # ↑ = {0 | *}：比任何正數都小，但 > 0
DOWN = -UP                                       # ↓ = {* | 0}


def switch(a, b):
    """開關（switch）{a | b}，其中 a > b。這是「熱」的局部 —— 誰先下誰賺。

    均值 (a+b)/2，溫度 (a-b)/2。溫度要到第 7 章才正式定義，
    但你已經可以看出來：a 與 b 差得越開，這個局部越燙。
    """
    return Game([number(a)], [number(b)])


def game_from_tree(spec):
    """從一棵手寫的賽局樹造出 Game。

    spec 的格式：
        數字（int / Fraction / str）      -> 一個數
        (left_specs, right_specs)         -> {L | R}
        "*"                               -> 星

    例：
        game_from_tree(([1], [0]))            # {1 | 0}
        game_from_tree((["1/2"], [0]))        # {1/2 | 0}
        game_from_tree((([2], [0]), [0]))     # 巢狀

    第 6 章的做法是：**盤面翻譯成樹由人做（而且棋圖上會標清楚每一手），
    樹算出值交給程式。** 這樣讀者可以自己核對每一步。
    """
    if spec == "*":
        return STAR
    if isinstance(spec, (int, float, str, Fraction)):
        return number(Fraction(spec))
    left_specs, right_specs = spec
    return Game([game_from_tree(s) for s in left_specs],
                [game_from_tree(s) for s in right_specs])
