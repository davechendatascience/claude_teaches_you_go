"""劫：狀態圖裡的環，以及打破環的三種規則。

對應第 5 章。

到第 4 章為止，我們一直默默假設一件事：**一盤棋會結束**。
劫是唯一讓這個假設失效的東西。

這個檔案有三層：

1. `GameState`     —— 帶著歷史的盤面。三種 ko 規則就是三種「哪些歷史不准重演」。
2. `find_cycle`    —— 在狀態圖裡找環。用它證明「沒有劫規則，遊戲不會終止」，
                      以及「只有基本劫規時，三劫循環仍然會無限下去」。
3. `ko_fight`      —— 劫爭的抽象模型：只用劫的價值與雙方的劫材清單就算出勝負。
"""

from go_core.board import BLACK, EMPTY, WHITE, Board, format_coord, opposite


# ---------------------------------------------------------------- 第 1 層

class IllegalMove(ValueError):
    """這一手不合法（含被 ko 規則禁止的情形）。"""


class GameState:
    """盤面 + 歷史。

    rule 有三種：
        "none"        完全沒有劫規則 —— 遊戲可能永遠不結束
        "basic"       基本劫規：禁止立刻把盤面還原成【上一手之前】的樣子
        "positional"  positional superko：任何盤面都不准重複出現
        "situational" situational superko：「盤面 + 輪到誰」不准重複
    """

    def __init__(self, board=None, n=9, rule="situational", to_move=BLACK):
        self.board = board.copy() if board is not None else Board(n)
        self.n = self.board.n
        self.rule = rule
        self.to_move = to_move
        # 歷史存的是 (盤面位元組, 輪到誰)
        self.history = [(self.board.grid.tobytes(), to_move)]

    def copy(self):
        s = GameState(self.board, self.n, self.rule, self.to_move)
        s.history = list(self.history)
        return s

    # ---- 合法性 ------------------------------------------------------

    def _would_repeat(self, new_bytes, next_to_move):
        if self.rule == "none":
            return False
        if self.rule == "basic":
            # 只看再上一個盤面（也就是「立刻回提」）
            if len(self.history) >= 2:
                return new_bytes == self.history[-2][0]
            return False
        if self.rule == "positional":
            return any(new_bytes == b for b, _ in self.history)
        if self.rule == "situational":
            return (new_bytes, next_to_move) in self.history
        raise ValueError(f"未知的規則 {self.rule!r}")

    def legal_moves(self, colour=None):
        """回傳所有合法著點（不含虛手）。"""
        colour = self.to_move if colour is None else colour
        out = []
        for p in self.board.points():
            if self.board.grid[p] != EMPTY:
                continue
            t = self.board.copy()
            try:
                t.play(colour, p)
            except ValueError:
                continue
            if self._would_repeat(t.grid.tobytes(), opposite(colour)):
                continue
            out.append(p)
        return out

    def play(self, colour, pt):
        """下一手。回傳被提掉的點集合。違反規則會丟 IllegalMove。"""
        t = self.board.copy()
        try:
            captured = t.play(colour, pt)
        except ValueError as e:
            raise IllegalMove(str(e)) from e
        nxt = opposite(colour)
        if self._would_repeat(t.grid.tobytes(), nxt):
            raise IllegalMove(
                f"{format_coord(self.board._pt(pt), self.n)} 違反 {self.rule} 規則："
                f"這一手會讓盤面回到已經出現過的樣子"
            )
        self.board = t
        self.to_move = nxt
        self.history.append((t.grid.tobytes(), nxt))
        return captured

    def passes(self):
        self.to_move = opposite(self.to_move)
        self.history.append((self.board.grid.tobytes(), self.to_move))

    def key(self):
        return (self.board.grid.tobytes(), self.to_move)

    def __str__(self):
        return str(self.board)


# ---------------------------------------------------------------- 第 2 層

def find_cycle(state, candidates, max_len=20):
    """在候選著點的範圍內找一條會回到起點的著手序列（也就是狀態圖裡的環）。

    回傳 [(顏色, 點), ...]，找不到則回傳 None。

    這是第 5 章 §4.2 的核心工具：**環的存在＝遊戲可能不終止。**
    在 rule="none" 的盤面上，任何一個劫都會被它找到一條長度 2 的環。
    在 rule="basic" 的盤面上，單劫找不到環（基本劫規擋住了），
    但三劫循環仍然找得到 —— 那正是基本劫規不夠用的證據。
    """
    start = state.key()
    candidates = [state.board._pt(p) for p in candidates]

    def walk(st, path):
        if len(path) > max_len:
            return None
        for p in candidates:
            if st.board.grid[p] != EMPTY:
                continue
            nxt = st.copy()
            try:
                nxt.play(st.to_move, p)
            except IllegalMove:
                continue
            step = path + [(st.to_move, p)]
            if nxt.key() == start and len(step) >= 2:
                return step
            found = walk(nxt, step)
            if found is not None:
                return found
        return None

    return walk(state, [])


def max_game_length(n):
    """positional superko 之下，一盤 n 路棋最多能下幾手（一個粗糙但有效的上界）。

    每一手之後盤面都必須是全新的，而盤面總數最多 3^(n*n)
    （每一點是空、黑、白三者之一）。所以遊戲一定會結束。

    這個數字大得毫無實用價值（19 路盤是 3^361）—— 但「有限」和「無限」
    在數學上是天差地別：有限保證了勝負有定義（第 10 章的 Zermelo 定理要用到）。
    """
    return 3 ** (n * n)


# ---------------------------------------------------------------- 第 3 層

WIN, LOSS = "打贏劫", "打輸劫"


def ko_fight(ko_value, my_threats, his_threats, i_hold_the_ko):
    """劫爭的抽象模型。回傳 (誰贏, 過程說明)。

    參數
        ko_value        劫的價值 K：打贏和打輸之間的差距（目）
        my_threats      我的劫材價值清單
        his_threats     他的劫材價值清單
        i_hold_the_ko   現在是不是我剛提了劫（也就是他不能立刻回提）

    模型的邏輯（每一條都在第 5 章 §4.4 推導）：
      * 剛被提的一方不能立刻回提，他必須先找一手【劫材】。
      * 一個劫材「有效」的條件是它的價值 >= K。
        若 t < K，對手會直接不理你、把劫消掉 —— 他賺 K，你只賺 t，你虧。
      * 對手回應劫材之後，找劫材的人才能回提，然後換對手找劫材。
      * 誰先找不到有效劫材，誰就輸掉這個劫。
    """
    mine = sorted((t for t in my_threats if t >= ko_value), reverse=True)
    his = sorted((t for t in his_threats if t >= ko_value), reverse=True)
    log = [f"劫的價值 K = {ko_value}",
           f"我的有效劫材（>= K）：{mine or '無'}",
           f"他的有效劫材（>= K）：{his or '無'}"]

    # 剛被提的一方要先找劫材
    finder_is_me = not i_hold_the_ko
    m, h = list(mine), list(his)
    step = 0
    while True:
        step += 1
        pool = m if finder_is_me else h
        who = "我" if finder_is_me else "他"
        if not pool:
            log.append(f"第 {step} 回合：{who}找不到有效劫材 -> {who}輸掉這個劫")
            return (LOSS if finder_is_me else WIN), log
        t = pool.pop(0)
        log.append(f"第 {step} 回合：{who}下一手價值 {t} 的劫材，對手應了，{who}回提")
        finder_is_me = not finder_is_me


def ko_fight_rule(my_threats, his_threats, ko_value, i_hold_the_ko):
    """同樣的答案，但用【數的】。第 5 章 §4.4 的判定式。

        令 m = 我的有效劫材數、h = 他的有效劫材數（價值 >= K 的才算）：

            我剛提了劫（他要先找劫材）：我贏 <=> m >= h
            他剛提了劫（我要先找劫材）：我贏 <=> m >  h

        寫成一條：**我贏 <=> m - h + [我剛提了劫] >= 1**

    和第 4 章的對殺判定式是同一個形狀 —— 因為它們是同一種東西：
    一場交替消耗資源的競賽，加上一個手番項。
    """
    m = sum(1 for t in my_threats if t >= ko_value)
    h = sum(1 for t in his_threats if t >= ko_value)
    return WIN if m - h + (1 if i_hold_the_ko else 0) >= 1 else LOSS
