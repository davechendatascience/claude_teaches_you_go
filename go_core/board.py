"""棋盤：交叉點、鄰點、落子、提子、合法性。

對應第 2 章 §4.1、§4.4。

座標約定（與 docs/03_writing_brief.md §4.2 一致）：
  * 對外的人類座標是 "D4" 這種字串：字母是「列」（A..T，跳過 I），數字是「行」（由下往上 1 起算）。
  * 對內一律用 (r, c) 這個 tuple，r 是由上往下數的列索引（0 在最上面），c 是由左往右數的行索引。
  * 兩者的換算：r = n - 數字，c = 字母的索引。9 路盤上 "D4" -> (5, 3)。
"""

import numpy as np

EMPTY, BLACK, WHITE = 0, 1, 2

# 圍棋座標傳統上跳過字母 I，以免與數字 1 混淆。
_COLS = "ABCDEFGHJKLMNOPQRST"

# 各種盤面大小的星位（hoshi）。key 是盤面大小。
STAR_POINTS = {
    7:  ["C3", "E3", "C5", "E5", "D4"],
    9:  ["C3", "G3", "C7", "G7", "E5"],
    13: ["D4", "K4", "D10", "K10", "G7"],
    19: ["D4", "K4", "Q4", "D10", "K10", "Q10", "D16", "K16", "Q16"],
}


def opposite(color):
    """回傳對方的顏色。"""
    if color == BLACK:
        return WHITE
    if color == WHITE:
        return BLACK
    raise ValueError("opposite() 只接受 BLACK 或 WHITE")


def col_letters(n):
    """回傳 n 路盤用到的列字母，例如 n=9 時是 'ABCDEFGHJ'。"""
    return _COLS[:n]


def parse_coord(s, n):
    """把 "D4" 這樣的人類座標，轉成內部的 (r, c)。"""
    s = s.strip().upper()
    letter, number = s[0], int(s[1:])
    if letter not in _COLS[:n]:
        raise ValueError(f"{s!r}：列字母超出 {n} 路盤的範圍（合法字母：{_COLS[:n]}）")
    if not 1 <= number <= n:
        raise ValueError(f"{s!r}：行數字超出 {n} 路盤的範圍（1..{n}）")
    return (n - number, _COLS.index(letter))


def format_coord(pt, n):
    """把內部的 (r, c) 轉回 "D4" 這樣的人類座標。"""
    r, c = pt
    return f"{_COLS[c]}{n - r}"


def neighbors(pt, n):
    """回傳 pt 的四個鄰點裡，還在盤內的那些。

    這就是第 2 章 §4.1 裡的 N(v)。角上只有 2 個，邊上 3 個，中央 4 個 ——
    「金角銀邊」的第一個線索就藏在這個函式的回傳長度裡。
    """
    r, c = pt
    out = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < n and 0 <= cc < n:
            out.append((rr, cc))
    return out


def diagonals(pt, n):
    """回傳 pt 的四個對角點裡，還在盤內的那些。第 3 章判定真假眼時要用。"""
    r, c = pt
    out = []
    for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < n and 0 <= cc < n:
            out.append((rr, cc))
    return out


def degree(pt, n):
    """pt 的度數 deg(v)：角 2、邊 3、中央 4。"""
    return len(neighbors(pt, n))


def is_edge(pt, n):
    """pt 是否在盤的最外圈（含四個角）。"""
    return degree(pt, n) < 4


class Board:
    """一個棋盤。

    grid 是 (n, n) 的 int8 陣列，值為 EMPTY / BLACK / WHITE。
    索引可以用內部 tuple，也可以直接用字串："D4"。
    """

    def __init__(self, n=9, grid=None):
        self.n = n
        if grid is None:
            self.grid = np.zeros((n, n), dtype=np.int8)
        else:
            self.grid = np.asarray(grid, dtype=np.int8).copy()
            if self.grid.shape != (n, n):
                raise ValueError(f"grid 的形狀 {self.grid.shape} 與 n={n} 不符")

    # ---- 基本存取 ----------------------------------------------------

    def _pt(self, key):
        """把 "D4" 或 (r, c) 統一轉成 (r, c)。"""
        if isinstance(key, str):
            return parse_coord(key, self.n)
        r, c = key
        if not (0 <= r < self.n and 0 <= c < self.n):
            raise ValueError(f"{key} 不在 {self.n} 路盤內")
        return (int(r), int(c))

    # 給書上的程式碼用的公開名稱（內部仍用 _pt，兩者是同一件事）。
    pt = _pt

    def __getitem__(self, key):
        r, c = self._pt(key)
        return int(self.grid[r, c])

    def __setitem__(self, key, value):
        r, c = self._pt(key)
        self.grid[r, c] = value

    def copy(self):
        return Board(self.n, self.grid)

    def is_empty(self, key):
        return self[key] == EMPTY

    def points(self):
        """走訪盤上所有交叉點，由上而下、由左而右。"""
        for r in range(self.n):
            for c in range(self.n):
                yield (r, c)

    def empties(self):
        return [p for p in self.points() if self.grid[p] == EMPTY]

    def stones(self, color=None):
        if color is None:
            return [p for p in self.points() if self.grid[p] != EMPTY]
        return [p for p in self.points() if self.grid[p] == color]

    # ---- 落子與提子 --------------------------------------------------

    def place(self, color, key):
        """直接把一顆子放上去，不檢查合法性、不提子。

        擺設題目盤面時用這個（相當於 SGF 的 AB / AW）。
        真正「下一手棋」請用 play()。
        """
        self[key] = color
        return self

    def place_many(self, color, keys):
        for k in keys:
            self.place(color, k)
        return self

    def play(self, color, key, allow_suicide=False):
        """下一手棋：放子、提掉沒氣的對方棋串、再檢查自殺。

        這就是第 2 章 §4.4 的兩條規則，逐字翻譯成程式：
            提子：  |L(S)| = 0  =>  移除 S
            禁著點：落子後自己的棋串 |L| = 0 且沒提到子  =>  非法

        回傳被提掉的點所成的 frozenset（沒提到就是空集合）。
        """
        from go_core.strings import find_string, liberties  # 避免循環匯入

        pt = self._pt(key)
        if self.grid[pt] != EMPTY:
            raise ValueError(f"{format_coord(pt, self.n)} 已經有子了")

        self.grid[pt] = color

        # 第一步：先看對方有沒有棋串因此沒氣。順序很重要 ——
        # 必須先提對方，才輪到檢查自己是不是自殺。
        captured = set()
        enemy = opposite(color)
        for q in neighbors(pt, self.n):
            if self.grid[q] == enemy:
                S = find_string(self, q)
                if len(liberties(self, S)) == 0:
                    captured |= S
        for q in captured:
            self.grid[q] = EMPTY

        # 第二步：提完之後，自己這串還有氣嗎？
        mine = find_string(self, pt)
        if len(liberties(self, mine)) == 0 and not allow_suicide:
            self.grid[pt] = EMPTY          # 復原，這一手不合法
            for q in captured:
                self.grid[q] = enemy
            raise ValueError(
                f"{format_coord(pt, self.n)} 是禁著點（自殺）：落子後這串沒有氣，而且沒有提到對方的子"
            )

        return frozenset(captured)

    def is_legal(self, color, key):
        """這一手合法嗎？（只看提子與自殺兩條規則，不含劫 —— 劫在第 5 章。）"""
        try:
            self.copy().play(color, key)
            return True
        except ValueError:
            return False

    # ---- 顯示 --------------------------------------------------------

    def to_ascii(self, **kwargs):
        """畫成書上的 ASCII 棋圖。參數說明見 go_core.render.render_ascii。"""
        from go_core.render import render_ascii
        return render_ascii(self, **kwargs)

    def __str__(self):
        chars = {EMPTY: ".", BLACK: "X", WHITE: "O"}
        stars = {parse_coord(s, self.n) for s in STAR_POINTS.get(self.n, [])}
        letters = col_letters(self.n)
        head = "     " + " ".join(letters)
        rows = [head]
        for r in range(self.n):
            num = self.n - r
            cells = []
            for c in range(self.n):
                v = int(self.grid[r, c])
                if v == EMPTY and (r, c) in stars:
                    cells.append("+")
                else:
                    cells.append(chars[v])
            rows.append(f"  {num:2d} " + " ".join(cells) + f" {num:d}")
        rows.append(head)
        return "\n".join(rows)

    __repr__ = __str__
