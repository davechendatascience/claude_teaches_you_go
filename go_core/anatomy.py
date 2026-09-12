"""逐手解剖：把一局棋的每一手丟給五層骨架，看誰說得出話。

對應第 14 章。

前面十二章各自造了一把尺。這個檔案做的事只有一件：**把它們同時架在一局棋上**，
然後問每一手 ——

    這一手，哪一層解釋得了？

每一層都用**那一章自己建立的判準**，不另外發明：

    第 1 層 連通性   marginal_liberty 最大（第 8 章命題 8.2）
    第 2 層 死活     這一點是某塊棋的做活點／要害（第 12 章定義 12.5）
    第 3 層 溫度     賭注最大的未定塊裡的要點（第 12 章命題 12.3）
    第 4 層 場       影響力總和最大（第 9 章定義 9.1）
    第 5 層 值函數   Delta_V = 0，也就是最佳著（第 10 章定義 10.3）

「解釋得了」的意思很窄：**那一層自己的判準會選這一手。** 不是「事後說得通」，
是「事前就會挑它」。這個定義刻意嚴格 —— 寬鬆的定義會讓五層看起來什麼都解釋，
那就沒有資訊了。

第 5 層只在 3 路盤上算得動（第 10 章：4 路盤就解不完）。所以 9 路盤的解剖
天生缺一層 —— **那個缺口本身就是第 14 章要交代的帳。**
"""

from go_core.board import BLACK, EMPTY, WHITE, Board, format_coord, opposite
from go_core.strings import all_strings, find_string, liberties

LAYER_NAMES = {
    1: "連通性",
    2: "死活",
    3: "溫度",
    4: "場",
    5: "值函數",
}


# ---------------------------------------------------------------- 各層的判準

def layer1_candidates(board, colour, ko=None):
    """第 1 層：邊際氣最大的點（第 8 章命題 8.2）。"""
    from go_core.minimax import legal_moves
    from go_core.shape import marginal_decomposition

    best, out = None, []
    for p, child, _ in legal_moves(board, colour, ko):
        # 這一手接上的自己人（可能不只一塊），取合併後的氣變化
        before = 0
        seen = set()
        for q in board.points():
            if board.grid[q] == colour and q not in seen:
                S = find_string(board, q)
                seen |= S
        S_new = find_string(child, p)
        touching = {q for q in S_new if board.grid[q] == colour}
        if touching:
            olds = set()
            seen2 = set()
            for q in touching:
                if q in seen2:
                    continue
                T = find_string(board, q)
                seen2 |= T
                olds |= liberties(board, T)
            before = len(olds)
        delta = len(liberties(child, S_new)) - before
        if best is None or delta > best:
            best, out = delta, [p]
        elif delta == best:
            out.append(p)
    return set(out), best


def layer2_candidates(board, colour, ko=None):
    """第 2 層：做活點或要害 —— 讓自己活、或讓對手不能活的點。"""
    from go_core.attack import vital_points
    from go_core.minimax import legal_moves

    foe = opposite(colour)
    out = set()
    for S in all_strings(board, colour):          # 自己的做活點
        out |= set(vital_points(board, S, colour))
    for S in all_strings(board, foe):             # 對手的做活點（佔住就是要害）
        out |= set(vital_points(board, S, foe))
    legal = {p for p, _, _ in legal_moves(board, colour, ko)}
    return out & legal, len(out & legal)


def layer3_candidates(board, colour, ko=None):
    """第 3 層：溫度最高的地方 —— 賭注最大的未定塊裡的要點。

    第 12 章命題 12.3：未定塊的溫度 = 它的賭注 s + t。
    所以「最熱的局部」就是賭注最大的那塊未定棋，而它的要點就是做活點。
    """
    from go_core.attack import is_alive, stake, vital_points
    from go_core.minimax import legal_moves

    legal = {p for p, _, _ in legal_moves(board, colour, ko)}
    best_k, out = -1, set()
    for c in (colour, opposite(colour)):
        for S in all_strings(board, c):
            if is_alive(board, S, c):
                continue                          # 已經活淨，溫度 0
            vp = set(vital_points(board, S, c)) & legal
            if not vp:
                continue
            k = stake(board, S)
            if k > best_k:
                best_k, out = k, vp
            elif k == best_k:
                out |= vp
    return out, best_k


def layer4_candidates(board, colour, ko=None, lam=0.8):
    """第 4 層：讓自己的影響力總和最大的點（第 9 章定義 9.1）。"""
    from go_core.influence import zobrist_field
    from go_core.minimax import legal_moves

    sign = 1 if colour == BLACK else -1
    best, out = None, []
    for p, child, _ in legal_moves(board, colour, ko):
        score = sign * float(zobrist_field(child, lam).sum())
        if best is None or score > best + 1e-12:
            best, out = score, [p]
        elif abs(score - best) <= 1e-12:
            out.append(p)
    return set(out), best


def layer5_candidates(board, colour, ko=None, max_ply=15):
    """第 5 層：Delta_V = 0 的著手，也就是最佳著（只有 3 路盤算得動）。"""
    from go_core.tewari import best_moves

    best, vals = best_moves(board, colour, ko, n=board.n, max_ply=max_ply)
    return {p for p in best if p is not None}, vals


# ---------------------------------------------------------------- 解剖

def explain_move(board, colour, move, ko=None, with_v=False, max_ply=15):
    """這一手，哪幾層解釋得了？

    回傳 {層號: (選中了嗎, 那一層提名幾個點, 合法點共幾個, 附註)}。

    **「提名幾個點」和「選中了嗎」一樣重要。** 一層如果把九個合法點提名了八個，
    它當然會「命中」，但那不叫解釋。第 14 章把這個比例叫做**選擇性**：

        選擇性 = 1 - (提名數 / 合法點數)

    選擇性接近 0 的一層，命中率再高也沒有資訊。
    """
    from go_core.minimax import legal_moves

    n_legal = len(legal_moves(board, colour, ko))
    out = {}

    cands, info = layer1_candidates(board, colour, ko)
    out[1] = (move in cands, len(cands), n_legal, f"邊際氣最大 = {info:+d}")

    cands, n = layer2_candidates(board, colour, ko)
    out[2] = (move in cands, len(cands), n_legal, f"做活點／要害 {n} 個")

    cands, k = layer3_candidates(board, colour, ko)
    out[3] = (move in cands, len(cands), n_legal,
              f"最熱的未定塊賭注 = {k}" if k >= 0 else "沒有未定塊")

    cands, _ = layer4_candidates(board, colour, ko)
    out[4] = (move in cands, len(cands), n_legal, "影響力總和最大")

    if with_v:
        cands, vals = layer5_candidates(board, colour, ko, max_ply)
        sign = 1 if colour == BLACK else -1
        best_val = max(vals.values()) if colour == BLACK else min(vals.values())
        loss = sign * (best_val - vals.get(move, best_val))
        out[5] = (move in cands, len(cands), n_legal, f"Delta_V = {loss:+.0f}")
    return out


def explain_game(moves, n=9, with_v=False, max_ply=15, progress=False):
    """把一整局棋逐手解剖。

    `moves` 是 [(顏色, 座標字串), ...]。回傳每一手一列的報告。
    """
    from go_core.minimax import legal_moves

    board = Board(n)
    ko = None
    rows = []
    for i, (colour, coord) in enumerate(moves, 1):
        if coord is None:                          # 虛手：不解剖，但要換手
            rows.append({"no": i, "colour": colour, "coord": "虛手",
                         "verdicts": {}, "layers": [], "pass": True})
            ko = None
            continue
        pt = board._pt(coord)
        verdicts = explain_move(board, colour, pt, ko, with_v, max_ply)
        rows.append({
            "no": i,
            "colour": colour,
            "coord": coord,
            "verdicts": verdicts,
            "layers": sorted(k for k, v in verdicts.items() if v[0]),
            "pass": False,
        })
        if progress:
            print(f"    第 {i} 手 {coord} -> 層 {rows[-1]['layers']}", flush=True)
        # 走這一手
        new_ko = None
        for p, child, nk in legal_moves(board, colour, ko):
            if p == pt:
                board, new_ko = child, nk
                break
        else:
            raise ValueError(f"第 {i} 手 {coord} 不合法")
        ko = new_ko
    return rows


def coverage(rows):
    """帳單：每一層解釋了幾手、提名了多寬、幾手一層都解釋不了？"""
    real = [r for r in rows if not r.get("pass")]
    layers = sorted(real[0]["verdicts"]) if real else sorted(LAYER_NAMES)
    per_layer = {k: 0 for k in layers}
    nominated = {k: 0 for k in layers}
    legal_total = {k: 0 for k in layers}
    unexplained = 0
    rows = [r for r in rows if not r.get("pass")]
    for r in rows:
        for k in layers:
            hit, n_cand, n_legal, _ = r["verdicts"][k]
            per_layer[k] += hit
            nominated[k] += n_cand
            legal_total[k] += n_legal
        if not r["layers"]:
            unexplained += 1
    total = len(rows)
    return {
        "total": total,
        "per_layer": per_layer,
        "hit_rate": {k: per_layer[k] / total for k in layers},
        "selectivity": {k: 1 - nominated[k] / max(1, legal_total[k])
                        for k in layers},
        "unexplained": unexplained,
        "explained": total - unexplained,
    }


def render_table(rows, n=9, with_v=False):
    """把解剖表印成書上的樣子。"""
    head = f"  {'手':>3} {'':>2}{'點':>5}   " + "".join(
        f"{LAYER_NAMES[k]:>6}" for k in sorted(LAYER_NAMES)
        if with_v or k != 5)
    out = [head, "  " + "-" * (len(head) - 2)]
    for r in rows:
        mark = "黑" if r["colour"] == BLACK else "白"
        if r.get("pass"):
            out.append(f"  {r['no']:>3} {mark:>2}{'虛手':>5}")
            continue
        cells = ""
        for k in sorted(LAYER_NAMES):
            if not with_v and k == 5:
                continue
            cells += f"{('O' if r['verdicts'][k][0] else '.'):>6}"
        out.append(f"  {r['no']:>3} {mark:>2}{r['coord']:>5}   {cells}")
    return "\n".join(out)


# ---------------------------------------------------------------- 照書下棋

def book_player(board, colour, ko=None, rng=None, lam=0.8):
    """一個**完全照本書的層級順序**下棋的程式。沒有搜尋，只有優先序。

        1. 能提子就提（第 2 章：沒氣就被提）
        2. 自己被叫吃就逃／接，只要逃得出兩口氣以上（第 2 章）
        3. 佔要害 —— 賭注最大的未定塊的做活點（第 12 章命題 12.3）
        4. 其餘：影響力總和最大（第 9 章定義 9.1）

    每一步都排除「填自己的眼」和「自殺」。

    它不強 —— 但它下出來的每一手都**有一個層可以指名負責**，
    這正是第 14 章要拿來解剖的東西。
    """
    import random

    from go_core.attack import is_alive, stake, vital_points
    from go_core.eyes import is_eye_like
    from go_core.influence import zobrist_field
    from go_core.minimax import legal_moves

    rng = rng or random.Random(0)
    foe = opposite(colour)
    opts = [(p, ch) for p, ch, _ in legal_moves(board, colour, ko)
            if not is_eye_like(board, p, colour)]
    if not opts:
        return None, None

    # 1. 提子 —— 提最多的
    caps = []
    for p, ch in opts:
        taken = sum(1 for q in board.points()
                    if board.grid[q] == foe and ch.grid[q] == EMPTY)
        if taken:
            caps.append((taken, p))
    if caps:
        caps.sort(reverse=True)
        return caps[0][1], 2

    # 2. 自己被叫吃 -> 逃或接
    in_atari = [S for S in all_strings(board, colour)
                if len(liberties(board, S)) == 1]
    if in_atari:
        best = None
        for p, ch in opts:
            if not any(p in liberties(board, S) for S in in_atari):
                continue
            libs = len(liberties(ch, find_string(ch, p)))
            if libs >= 2 and (best is None or libs > best[0]):
                best = (libs, p)
        if best:
            return best[1], 1

    # 3. 要害：賭注最大的未定塊的做活點
    legal = {p for p, _ in opts}
    best_k, pick = -1, None
    for c in (colour, foe):
        for S in all_strings(board, c):
            if is_alive(board, S, c):
                continue
            vp = set(vital_points(board, S, c)) & legal
            if not vp:
                continue
            k = stake(board, S)
            if k > best_k:
                best_k, pick = k, sorted(vp)[0]
    if pick is not None:
        return pick, 3

    # 4. 場
    sign = 1 if colour == BLACK else -1
    best, out = None, []
    for p, ch in opts:
        score = sign * float(zobrist_field(ch, lam).sum())
        if best is None or score > best + 1e-12:
            best, out = score, [p]
        elif abs(score - best) <= 1e-12:
            out.append(p)
    return (rng.choice(sorted(out)) if out else None), 4


def play_book_game(n=9, max_moves=120, rng=None, fill_dame=True):
    """讓兩個 book_player 對下一局，回傳 (著手序列, 每手是哪一層決定的, 終局盤面)。"""
    import random

    from go_core.minimax import legal_moves
    from go_core.score import ScoredGame, dame

    rng = rng or random.Random(0)
    g = ScoredGame(n)
    colour, ko, passes = BLACK, None, 0
    moves, reasons = [], []
    for _ in range(max_moves):
        mv, layer = book_player(g.board, colour, ko, rng)
        if mv is None:
            moves.append((colour, None))
            reasons.append(None)
            passes += 1
            ko = None
            if passes >= 2:
                break
        else:
            name = format_coord(mv, n)
            for p, ch, nk in legal_moves(g.board, colour, ko):
                if p == mv:
                    g.play(colour, name)
                    ko = nk
                    break
            moves.append((colour, name))
            reasons.append(layer)
            passes = 0
        colour = opposite(colour)

    if fill_dame:
        while True:
            d = sorted(dame(g.board))
            if not d:
                break
            name = format_coord(d[0], n)
            try:
                g.play(colour, name)
            except ValueError:
                break
            moves.append((colour, name))
            reasons.append(0)             # 0 = 收單官，不屬於任何一層
            colour = opposite(colour)
    return moves, reasons, g
