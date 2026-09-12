"""對殺：把氣分類，然後把勝負算出來。

對應第 4 章 §4.2、§4.3、§4.4。

這個檔案有三層：

1. `classify_liberties`  —— 在【真實盤面】上，把兩塊敵對棋串的氣分成三類：
       我方外氣 a（只貼著我）、對方外氣 b（只貼著他）、公氣 c（兩邊都貼）。

2. `race_winner`         —— 一個【抽象模型】：只用 (a, b, c, 誰有眼, 誰先手)
       這五個數就把對殺算完。它是一棵完整的搜尋樹，不是公式。

3. `big_eye_liberties`   —— 大眼氣數，用淨手數的定義算出來。

第 3 層的「淨手數」是本章最重要的一個澄清：口訣表上的「三目三氣、四目五氣」
不是「攻方要下幾手」，而是**攻方手數減掉守方在眼內的手數**。
攻方要 4 手才吃得掉三目大眼，但守方必須在眼裡陪下 1 手，所以淨值是 3。
"""

from functools import lru_cache

from go_core.board import EMPTY
from go_core.strings import liberties


# ---------------------------------------------------------------- 第 1 層

def classify_liberties(board, S1, S2):
    """把兩塊敵對棋串的氣分成三類。

    回傳 dict：
        own    S1 的外氣（只貼著 S1）
        opp    S2 的外氣（只貼著 S2）
        shared 公氣（兩邊都貼）
    """
    L1 = liberties(board, S1)
    L2 = liberties(board, S2)
    shared = L1 & L2
    return {"own": L1 - shared, "opp": L2 - shared, "shared": shared,
            "a": len(L1 - shared), "b": len(L2 - shared), "c": len(shared)}


def eye_points(board, S):
    """屬於 S 自己的單點眼。注意：眼點【本身就是一口氣】。

    所以在餵給 race_winner 之前，外氣數要先把眼點扣掉，否則會重複計算。
    """
    from go_core.board import neighbors
    from go_core.eyes import is_eye_like
    colour = int(board.grid[next(iter(S))])
    return frozenset(
        v for v in liberties(board, S)
        if is_eye_like(board, v, colour) is not None
        and all(q in S for q in neighbors(v, board.n))
    )


def race_preconditions(board, S1, S2):
    """檢查這個盤面符不符合抽象模型的前提。回傳 (符合嗎, 不符的理由清單)。

    抽象模型（race_winner）不是對任何盤面都成立的。它有三個前提，
    而這三個前提不是憑空假設的 —— 它們是被「模型與盤面搜尋不符的例子」
    一個一個逼出來的（見 examples/ch04_capture_races/ex01_race_formula.py）：

    前提一（嚴格封閉，三個互不相通的口袋）
        公氣的鄰點只能是這兩塊棋、或別的公氣；
        我方外氣的鄰點只能是我方的棋、或我方別的外氣（對方同理）。
        若不成立，「填一口公氣」可能讓對手接觸到原本專屬於我的氣，
        而模型假設填公氣只會讓雙方各少一口。

    前提二（眼的狀態已經定下來）
        外氣口袋裡不能有兩點相鄰。若有，那個口袋還能做出一個眼，
        而模型的「有沒有眼」是一個已經固定的旗標。

    前提三（各自是一整塊）
        S1 與 S2 各自是單一的連通分量，而且各自最多一個眼。

    這三個前提在真實對局的大多數對殺裡都成立 —— 因為對殺通常就發生在
    一個封閉的小空間裡。但寫進書上的定理必須把前提寫出來。
    """
    from go_core.board import neighbors
    d = classify_liberties(board, S1, S2)
    own, opp, sh = d["own"], d["opp"], d["shared"]
    reasons = []

    for v in sh:
        if not all(q in S1 or q in S2 or q in sh for q in neighbors(v, board.n)):
            reasons.append(f"公氣 {v} 通往別處，不是封閉的口袋")
            break
    for label, pocket, S in (("我方", own, S1), ("對方", opp, S2)):
        for v in pocket:
            if not all(q in S or q in pocket for q in neighbors(v, board.n)):
                reasons.append(f"{label}外氣 {v} 通往別處，不是封閉的口袋")
                break

    for label, S in (("我方", S1), ("對方", S2)):
        eyes = eye_points(board, S)
        if len(eyes) > 1:
            reasons.append(f"{label}已經有兩個眼，那不是對殺，是活棋")
        pocket = (own if S is S1 else opp) - eyes
        for v in pocket:
            if any(q in pocket for q in neighbors(v, board.n)):
                reasons.append(f"{label}的外氣口袋裡有相鄰的兩點，眼的狀態還沒定")
                break

    return (not reasons), reasons


# ---------------------------------------------------------------- 第 2 層

WIN, SEKI, LOSS = "我勝", "雙活", "他勝"
_ORDER = {WIN: 2, SEKI: 1, LOSS: 0}          # 從「我」的角度，越大越好


@lru_cache(maxsize=None)
def _race(a, b, c, my_eye, opp_eye, my_turn, passes):
    """對殺搜尋的內層。狀態全部從「我」的角度描述。

    提子是在【落子的當下】判定的，不是在節點入口 —— 因為「誰被提」取決於
    誰下了最後那一手（第 2 章 §4.4 的順序）。這個細節如果搞錯，
    雙活會被誤判成一方獲勝。
    """
    if passes >= 2:
        return SEKI                       # 雙方都不敢動 —— 這就是雙活的定義

    my_libs = lambda A, C: A + C + (1 if my_eye else 0)
    his_libs = lambda B, C: B + C + (1 if opp_eye else 0)

    results = []

    if my_turn:
        # (1) 填他的外氣：我的氣不變，他少一口
        if b > 0:
            if his_libs(b - 1, c) == 0:
                return WIN                        # 這一手提掉他
            results.append(_race(a, b - 1, c, my_eye, opp_eye, False, 0))
        # (2) 填公氣：雙方同時少一口
        if c > 0:
            if his_libs(b, c - 1) == 0:
                return WIN                        # 先提到他，所以合法
            if my_libs(a, c - 1) > 0:             # 否則我自己不能歸零（自殺）
                results.append(_race(a, b, c - 1, my_eye, opp_eye, False, 0))
        # (3) 填他的眼：只有在他其他氣都沒了的時候才合法（那一手會提子）
        if opp_eye and b == 0 and c == 0:
            return WIN
        # (4) 虛手
        results.append(_race(a, b, c, my_eye, opp_eye, False, passes + 1))
        return max(results, key=lambda r: _ORDER[r])

    # 換他走。對稱地做一遍，然後取對他最好的（也就是對我最差的）。
    if a > 0:
        if my_libs(a - 1, c) == 0:
            return LOSS
        results.append(_race(a - 1, b, c, my_eye, opp_eye, True, 0))
    if c > 0:
        if my_libs(a, c - 1) == 0:
            return LOSS
        if his_libs(b, c - 1) > 0:
            results.append(_race(a, b, c - 1, my_eye, opp_eye, True, 0))
    if my_eye and a == 0 and c == 0:
        return LOSS
    results.append(_race(a, b, c, my_eye, opp_eye, True, passes + 1))
    return min(results, key=lambda r: _ORDER[r])


def race_winner(a, b, c, my_eye=False, opp_eye=False, my_turn=True):
    """對殺的抽象模型。回傳 "我勝"、"雙活" 或 "他勝"。

    狀態只有五個數：
        a        我的外氣數（只貼著我）
        b        他的外氣數（只貼著他）
        c        公氣數（填一個，雙方的氣同時少一個）
        my_eye   我有沒有眼
        opp_eye  他有沒有眼
      再加上「輪到誰」。

    每一條規則都是第 2 章提子規則的直接後果：
      * 填對方外氣：他的總氣 -1，我的不變。
      * 填公氣：雙方的總氣同時 -1。所以填公氣是一手「兩敗俱傷」的棋 ——
        只有在填完之後我還活著（或者填完就提到他）的時候才合法。
      * 「眼」是一口對手填不了的氣：他只有在我其他氣都沒了的時候才填得下去，
        因為那時候填它會提到我（第 3 章命題 3.4）；在那之前填它是純自殺
        （第 3 章定理 3.5）。
      * 雙方連續虛手 -> 雙活。這就是雙活的定義：誰先動誰吃虧。
    """
    # 退化輸入：有一方的總氣本來就是 0，那它早就被提走了，沒有對殺可言。
    if b + c + (1 if opp_eye else 0) == 0:
        return WIN
    if a + c + (1 if my_eye else 0) == 0:
        return LOSS
    return _race(a, b, c, bool(my_eye), bool(opp_eye), bool(my_turn), 0)


def race_formula(a, b, c, my_eye=False, opp_eye=False, my_turn=True):
    """同樣的答案，但用【公式】算，不搜尋。第 4 章 §4.2、§4.3 的判定式。

    令 d = a - b + tau（tau = 1 表示我先手）：

      無眼對無眼   我勝 <=> d >= max(c, 1)
                   他勝 <=> d <= min(1 - c, 0)
                   雙活 <=> 2 - c <= d <= c - 1      （c >= 2 才非空）

      我有眼他無眼 我勝 <=> b <= a + c + tau         （公氣全歸有眼的一方）
                   永遠不會雙活

      雙方都有眼   我勝 <=> d >= c + 1
                   他勝 <=> d <= -c
                   雙活 <=> 1 - c <= d <= c          （c >= 1 才非空）

    這些公式不是猜的：examples/ch04_capture_races/ex01_race_formula.py
    把它們和上面那棵完整搜尋樹逐格比對過。
    """
    tau = 1 if my_turn else 0
    d = a - b + tau
    if my_eye and opp_eye:
        if d >= c + 1:
            return WIN
        if d <= -c:
            return LOSS
        return SEKI
    if my_eye and not opp_eye:
        return WIN if b <= a + c + tau else LOSS
    if opp_eye and not my_eye:
        return LOSS if a <= b + c + (1 - tau) else WIN
    if d >= max(c, 1):
        return WIN
    if d <= min(1 - c, 0):
        return LOSS
    return SEKI


# ---------------------------------------------------------------- 第 3 層

def big_eye_liberties(n):
    """大眼氣數的閉合解，n 是眼位空間的點數（2 <= n <= 6）。

        f(n) = 2 + (n-1)(n-2)/2

    驗證：f(2)=2, f(3)=3, f(4)=5, f(5)=8, f(6)=12 —— 就是那張口訣表。

    這個數的定義是【淨手數】：攻方的手數，減掉守方在眼內被迫陪下的手數。
    examples/ch04_capture_races/ex02_big_eye.py 用完整搜尋把它算出來對答案。
    """
    if not 2 <= n <= 6:
        raise ValueError("這條閉合解只在 2 <= n <= 6 成立；n >= 7 的眼位空間"
                         "大到可以自己做出兩個眼，不再是大眼（第 3 章 §4.4）")
    return 2 + (n - 1) * (n - 2) // 2


def attacker_moves(n):
    """攻方【實際】要下的手數：g(n) = 1 + n(n-1)/2。

    g(2)=2, g(3)=4, g(4)=7, g(5)=11, g(6)=16。

    這個數字比口訣表大，因為守方會在中途提掉攻方填進去的子，逼攻方重填。
    """
    if not 2 <= n <= 6:
        raise ValueError("只在 2 <= n <= 6 成立")
    return 1 + n * (n - 1) // 2


def defender_moves(n):
    """守方在眼內被迫陪下的手數：n - 2。

    三個數字合起來就是本章最重要的一條恆等式：

        g(n)  -  (n - 2)  =  f(n)
        攻方實際手數 - 守方陪下手數 = 大眼氣數（口訣表上的數字）
    """
    if not 2 <= n <= 6:
        raise ValueError("只在 2 <= n <= 6 成立")
    return n - 2
