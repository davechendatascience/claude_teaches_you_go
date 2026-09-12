"""影響力場：厚薄的可計算模型 —— 以及它可以被證明的失效。

對應第 9 章。

> **這個檔案裡沒有定理，只有模型。**
>
> go_core 的其他檔案（strings、benson、capture_race、cgt、temperature、shape）
> 算出來的每一個數字都有證明撐著。這一個沒有。影響力場是**啟發式**：
> 它可以計算、常常有用、畫出來很漂亮，但它不保證任何事。
>
> 唯一的例外是 `discontinuity_witness()` —— 那個函式證明的是這一層的**極限**，
> 也就是「任何這種形式的場都算不出死活」。負面結果，但它是真的定理。

三個模型：

1. `zobrist_field`  —— 每顆子像一盞燈，亮度隨距離指數衰減，正負相加。
2. `bouzy_field`    —— 膨脹／侵蝕。離散、沒有參數 lambda，比較貼近人類看棋的方式。
3. `moyo`           —— 亮度超過門檻的地方就算你的模樣。

以及三個誠實的量測：

4. `playout_ownership` / `field_accuracy` —— 場預測的歸屬 vs 真的下完之後的歸屬。
5. `marginal_moyo`   —— 多下這一手，模樣大了幾點。「厚勢不圍空」的量化。
6. `discontinuity_witness` —— 場是連續的，真相不是。第 9 章的頓悟。
"""

import numpy as np

from go_core.board import BLACK, EMPTY, WHITE, Board, neighbors, opposite
from go_core.eyes import is_eye_like
from go_core.strings import all_strings, find_string, liberties


# ---------------------------------------------------------------- 1. Zobrist

def distance_map(n):
    """所有點對之間的格子距離（Manhattan）。回傳形狀 (n*n, n*n) 的整數陣列。

    盤面很小（<= 19），一次算好比每次重算快得多。
    """
    idx = np.arange(n * n)
    r, c = idx // n, idx % n
    return np.abs(r[:, None] - r[None, :]) + np.abs(c[:, None] - c[None, :])


_DIST_CACHE = {}


def _dist(n):
    if n not in _DIST_CACHE:
        _DIST_CACHE[n] = distance_map(n)
    return _DIST_CACHE[n]


def zobrist_field(board, lam=0.6):
    """Zobrist 影響力場：

        I(v) = sum_s sigma(s) * lam ** d(s, v)

    sigma = +1（黑）或 -1（白），d 是格子距離，lam 在 (0, 1) 之間。

    每顆子是一盞燈，越遠越暗；黑燈加分、白燈減分，直接疊加。
    回傳形狀 (n, n) 的浮點陣列，正數偏黑、負數偏白。
    """
    if not 0 < lam < 1:
        raise ValueError("lam 必須在 (0, 1) 之間")
    n = board.n
    sigma = np.zeros(n * n)
    flat = board.grid.reshape(-1)
    sigma[flat == BLACK] = 1.0
    sigma[flat == WHITE] = -1.0
    if not sigma.any():
        return np.zeros((n, n))
    weights = lam ** _dist(n)
    return (sigma @ weights).reshape(n, n)


# ---------------------------------------------------------------- 2. Bouzy

def _neighbour_stack(f):
    """把四個方向的鄰居疊成 (4, n, n)，盤外補 0。"""
    n = f.shape[0]
    out = np.zeros((4, n, n))
    out[0, 1:, :] = f[:-1, :]      # 上
    out[1, :-1, :] = f[1:, :]      # 下
    out[2, :, 1:] = f[:, :-1]      # 左
    out[3, :, :-1] = f[:, 1:]      # 右
    return out


def dilate(f):
    """膨脹一次（Bouzy）。

    每一點加上「和自己同號的鄰居」的個數 —— 但只有在沒有反號鄰居的時候。
    直覺：勢力向外滲一格，遇到對方就停。
    """
    nb = _neighbour_stack(f)
    pos = (nb > 0).sum(axis=0)
    neg = (nb < 0).sum(axis=0)
    out = f.copy()
    grow = np.where(f > 0, pos, np.where(f < 0, -neg, pos - neg))
    blocked = np.where(f > 0, neg > 0, np.where(f < 0, pos > 0, False))
    return np.where(blocked, out, out + grow)


def erode(f, count_offboard=False):
    """侵蝕一次（Bouzy）。

    每一點減掉「不同號（含 0）的鄰居」個數，但不會穿過零點變號。
    直覺：把膨脹時滲得太薄的邊緣削掉。

    `count_offboard` 是一個**有後果的選擇**，Bouzy 原文沒有明講：
    盤外的鄰居算不算「不同號」？

      * False（原文的作法）：不算。於是邊角侵蝕得比較少，勢力會黏在邊角上。
      * True：算。於是邊角侵蝕得比較多，勢力集中在中央。

    這個開關會讓同一個盤面的估計差好幾目。第 9 章 §4.2 把兩種都跑一遍，
    拿隨機下完的實際歸屬去比 —— 這是本章少數幾個**可以量測**的問題之一。
    """
    nb = _neighbour_stack(f)
    n = f.shape[0]
    on_board = np.zeros((4, n, n), dtype=bool)
    on_board[0, 1:, :] = True
    on_board[1, :-1, :] = True
    on_board[2, :, 1:] = True
    on_board[3, :, :-1] = True
    if count_offboard:
        on_board[:] = True

    not_pos = ((nb <= 0) & on_board).sum(axis=0)
    not_neg = ((nb >= 0) & on_board).sum(axis=0)
    shrink = np.where(f > 0, not_pos, np.where(f < 0, not_neg, 0))
    out = np.where(f > 0, np.maximum(f - shrink, 0),
                   np.where(f < 0, np.minimum(f + shrink, 0), f))
    return out


def bouzy_field(board, k=5, count_offboard=False):
    """Bouzy 的膨脹／侵蝕場：先膨脹 k 次，再侵蝕 k(k-1) 次。

    和 Zobrist 不同，這裡**沒有 lambda 要調** —— 只有一個整數 k，
    而且輸出是整數。它比較像人類看棋：勢力一格一格擴散，
    薄的地方會被削掉，厚的地方留下來。
    """
    f = np.zeros((board.n, board.n))
    f[board.grid == BLACK] = 1.0
    f[board.grid == WHITE] = -1.0
    for _ in range(k):
        f = dilate(f)
    for _ in range(k * (k - 1)):
        f = erode(f, count_offboard)
    return f


# ---------------------------------------------------------------- 3. 模樣

def moyo(field, theta=0.0, colour=BLACK):
    """勢力圈：亮度超過門檻的空點集合。回傳點的 frozenset。"""
    sign = 1 if colour == BLACK else -1
    n = field.shape[0]
    return frozenset((r, c) for r in range(n) for c in range(n)
                     if sign * field[r, c] > theta)


def moyo_area(board, field, theta=0.0, colour=BLACK):
    """模樣的面積：只數**空點**（已經有子的地方不是「圍到的空」）。"""
    return sum(1 for p in moyo(field, theta, colour) if board.grid[p] == EMPTY)


def field_ownership(field, theta=0.0):
    """把場化成歸屬預測：+1 黑、-1 白、0 不明。"""
    out = np.zeros(field.shape, dtype=int)
    out[field > theta] = BLACK
    out[field < -theta] = WHITE
    return out


# ------------------------------------------------- 4. 和「真的下完」比對

def _has_true_liberty(board, colour, p):
    """在 p 落子之後不會立刻自殺嗎？（快速版，不做完整搜尋）"""
    t = board.copy()
    try:
        t.play(colour, p)
    except ValueError:
        return False
    return True


def playout(board, to_move, rng, max_moves=None, avoid_eyes=True):
    """隨機把棋下完：雙方隨機落子，不填自己的眼，兩方都無處可下就結束。

    這**不是**一個會下棋的程式 —— 它只是一個能把盤面填滿到可以數目的方法。
    第 9 章用它產生「真的下完之後誰擁有這一點」的樣本，
    好拿來檢驗影響力場的預測準不準。
    """
    b = board.copy()
    n = b.n
    max_moves = max_moves or n * n * 3
    passes = 0
    colour = to_move
    for _ in range(max_moves):
        cands = [p for p in b.points() if b.grid[p] == EMPTY]
        if avoid_eyes:
            cands = [p for p in cands if not is_eye_like(b, p, colour)]
        rng.shuffle(cands)
        played = False
        for p in cands:
            if _has_true_liberty(b, colour, p):
                b.play(colour, p)
                played = True
                break
        passes = 0 if played else passes + 1
        if passes >= 2:
            break
        colour = opposite(colour)
    return b


def _empty_regions(board):
    """把空點切成連通區塊。回傳 [(區塊, 周圍有哪些顏色), ...]。"""
    seen = set()
    out = []
    for p in board.points():
        if board.grid[p] != EMPTY or p in seen:
            continue
        region, frontier, colours = {p}, [p], set()
        seen.add(p)
        while frontier:
            q = frontier.pop()
            for r in neighbors(q, board.n):
                v = int(board.grid[r])
                if v == EMPTY:
                    if r not in seen:
                        seen.add(r)
                        region.add(r)
                        frontier.append(r)
                else:
                    colours.add(v)
        out.append((frozenset(region), colours))
    return out


def final_ownership(board):
    """一個下完的盤面上，每一點屬於誰。回傳 (n, n) 的整數陣列。

    規則很簡單：有子的點屬於那顆子；空的區塊如果只被一種顏色包圍，
    就屬於那個顏色，否則是無主（0）。這就是日本規則的數目方式。
    """
    own = np.array(board.grid, dtype=int)
    for region, colours in _empty_regions(board):
        if len(colours) == 1:
            c = next(iter(colours))
            for p in region:
                own[p] = c
    return own


def field_accuracy(board, to_move, field, rng, trials=20, theta=0.0):
    """場的預測 vs 隨機下完的實際歸屬。回傳一份統計。

    對每一個**當下還是空的**點，比對 sign(field) 和下完之後的歸屬。
    無主點與場判為 0 的點都不計分（那些是「場說不知道」，不是錯）。
    """
    pred = field_ownership(field, theta)
    empties = [p for p in board.points() if board.grid[p] == EMPTY]
    hit = miss = skipped = 0
    for _ in range(trials):
        done = playout(board, to_move, rng)
        own = final_ownership(done)
        for p in empties:
            if pred[p] == 0 or own[p] == 0:
                skipped += 1
                continue
            if pred[p] == own[p]:
                hit += 1
            else:
                miss += 1
    total = hit + miss
    return {"hit": hit, "miss": miss, "skipped": skipped,
            "accuracy": hit / total if total else float("nan"),
            "scored": total}


# --------------------------------------------- 5. 厚勢不圍空的量化

def marginal_moyo(board, colour, p, theta=0.0, lam=0.6):
    """多下這一手，模樣的面積多了幾點？

    「厚勢不圍空」的量化版本：在自己已經很厚的地方再下一手，
    這個數字很小（那些點早就在模樣裡了）；在模樣邊界下一手，這個數字大。
    """
    before = moyo_area(board, zobrist_field(board, lam), theta, colour)
    t = board.copy()
    t.grid[t._pt(p)] = colour
    after = moyo_area(t, zobrist_field(t, lam), theta, colour)
    return after - before


def marginal_map(board, colour, theta=0.0, lam=0.6):
    """對每一個空點算 marginal_moyo。回傳 {點: 增量}。"""
    return {p: marginal_moyo(board, colour, p, theta, lam)
            for p in board.points() if board.grid[p] == EMPTY}


# ------------------------------------- 6. 場的極限（這一節有定理）

def field_perturbation(n, distance, lam):
    """在距離 d 之外多放一顆子，對這裡的場最多能改變多少？

    答案就是 lam ** d —— 一顆子的貢獻。這是**上界**，而且它隨 d 指數趨近 0。
    """
    return lam ** distance


def discontinuity_witness(lam=0.6):
    """第 9 章的定理：場是連續的，真相不是。

    用第 8 章的征子當見證：13 路盤上，黑 D10 被白征子（35 手，死）。
    在 N4 多放一顆黑子 —— 距離 15 路 —— 征子就破了，黑活。

    這個函式回傳一份對照：
      * 那一顆子讓 D10 附近的場改變了多少（<= lam ** 15，微乎其微）
      * 那一顆子讓 D10 的死活改變了多少（死 -> 活，完全翻轉）

    結論：**任何形如 I(v) = sum_s sigma(s) f(d(s,v))（f 遞減趨零）的場，
    都不可能算出死活。** 因為場對遠處的擾動是連續的，死活不是。
    """
    from go_core.ladder import ladder_capture

    n = 13
    base = Board(n)
    base.place(BLACK, "D10")
    base.place_many(WHITE, ["D11", "C10", "E11"])

    broken = base.copy()
    broken.place(BLACK, "N4")

    f0 = zobrist_field(base, lam)
    f1 = zobrist_field(broken, lam)
    target = base._pt("D10")
    breaker = base._pt("N4")
    d = abs(target[0] - breaker[0]) + abs(target[1] - breaker[1])

    dead_before, path = ladder_capture(base, "D10", WHITE, max_depth=200)
    dead_after, _ = ladder_capture(broken, "D10", WHITE, max_depth=200)

    return {
        "distance": d,
        "field_before": float(f0[target]),
        "field_after": float(f1[target]),
        "field_change": float(abs(f1[target] - f0[target])),
        "bound": field_perturbation(n, d, lam),
        "captured_before": dead_before,
        "captured_after": dead_after,
        "ladder_length": len(path),
    }


# ---------------------------------------------------------------- 顯示

def render_field(field, board=None, scale=None, unit=None):
    """把場印成一張圖：數字越大越黑。給第 9 章的手算追蹤用。

    用一個字元表示一格：X/O 是棋子，`.` 是幾乎沒有影響，
    1-9 是黑的強度，a-i 是白的強度（a 最弱、i 最強）。

    刻度有兩種指定方式，**書上每一張場圖都必須說明用的是哪一種**：

      * `unit=0.1` —— 一格代表 0.1，也就是印出「十分位」。適合單顆子的圖。
      * `unit=1.0` —— 一格代表 1.0，印出「個位」。適合一整道牆的圖。
      * 都不給 —— 相對刻度，最強的地方是 9。只適合看形狀，不能跨圖比較。
    """
    n = field.shape[0]
    if unit is None:
        scale = scale or (np.abs(field).max() or 1.0)
    rows = []
    for r in range(n):
        cells = []
        for c in range(n):
            if board is not None and board.grid[r, c] != EMPTY:
                cells.append("X" if board.grid[r, c] == BLACK else "O")
                continue
            if unit is not None:
                v = field[r, c]
                mag = min(9, int(abs(v) / unit + 0.5))
                if mag == 0:
                    cells.append(".")
                else:
                    cells.append(str(mag) if v > 0 else chr(ord("a") + mag - 1))
                continue
            v = field[r, c] / scale
            mag = min(9, int(abs(v) * 9 + 0.5))
            if mag == 0:
                cells.append(".")
            else:
                cells.append(str(mag) if v > 0 else chr(ord("a") + mag - 1))
        rows.append(" ".join(cells))
    return "\n".join(rows)
