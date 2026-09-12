"""從【真實盤面】算出組合賽局值。

對應第 6 章 §4.4 起、第 7 章。

第 6 章教的 CGT 是抽象的：G = {G^L | G^R}。這個檔案把它接回棋盤 ——
給一個局部區域，程式把整棵賽局樹列舉出來，算出那個局部到底值幾目。

【模型的四條約定】（第 6 章 §4.4 會逐條說明，這裡先列出來）

  1. **區域是固定的**：只考慮 region 裡的落子，外面的子當作不動的牆。
  2. **牆是活的**：假設圍住這個區域的棋不會死（死活是第 3、4 章的事）。
  3. **定型（settled）**：region 裡每一塊相連的空點，它周圍的子全是同一色。
     此時雙方再下都只是自填，局部結束。
  4. **記分用日本規則（數目）**：空點算給圍住它的一方，被提的子算對方的目。
     所以「在自己的空裡補一手」會扣自己一目 —— 這正是為什麼有些局部的值
     是【數】：下了會虧，所以雙方都不想動。

【不處理】劫。第 5 章 §4.6 說明了為什麼：劫材是跨局部的。
本模組遇到會產生重複盤面的著手時，直接把那一手排除。
"""

from fractions import Fraction

from go_core.board import BLACK, EMPTY, WHITE, format_coord, neighbors
from go_core.cgt import Game, number


def _components(board, region):
    """region 裡的空點，依相鄰關係分成若干連通塊。"""
    todo = {p for p in region if board.grid[p] == EMPTY}
    out = []
    while todo:
        seed = todo.pop()
        comp = {seed}
        frontier = [seed]
        while frontier:
            p = frontier.pop()
            for q in neighbors(p, board.n):
                if q in todo:
                    todo.discard(q)
                    comp.add(q)
                    frontier.append(q)
        out.append(frozenset(comp))
    return out


def territory(board, region):
    """回傳 (黑的目, 白的目, 是否已定型)。

    一塊相連的空點屬於某一方，若它周圍的子【全部】是那一方的。
    只要還有一塊空點的邊界是黑白混雜的，這個局部就還沒定型。
    """
    black = white = 0
    settled = True
    for comp in _components(board, region):
        border = {int(board.grid[q])
                  for p in comp for q in neighbors(p, board.n)
                  if q not in comp}
        border.discard(EMPTY)
        if border == {BLACK}:
            black += len(comp)
        elif border == {WHITE}:
            white += len(comp)
        else:
            settled = False              # 邊界混雜（或完全沒有邊界）
    return black, white, settled


def region_value(board, region, prisoners=0, _memo=None, _depth=0, max_depth=14):
    """算出這個局部的組合賽局值。

    prisoners 是到目前為止的淨提子數（黑提到的算正）。
    回傳一個 go_core.cgt.Game。
    """
    region = frozenset(board._pt(p) for p in region)
    if _memo is None:
        _memo = {}
    key = (board.grid.tobytes(), prisoners)
    if key in _memo:
        return _memo[key]
    if _depth > max_depth:
        b, w, _ = territory(board, region)
        return number(b - w + prisoners)

    b, w, settled = territory(board, region)
    if settled:
        out = number(b - w + prisoners)
        _memo[key] = out
        return out

    options = {BLACK: [], WHITE: []}
    for colour in (BLACK, WHITE):
        for p in sorted(region):
            if board.grid[p] != EMPTY:
                continue
            t = board.copy()
            try:
                captured = t.play(colour, p)
            except ValueError:
                continue
            gain = len(captured) * (1 if colour == BLACK else -1)
            options[colour].append(
                region_value(t, region, prisoners + gain, _memo, _depth + 1, max_depth)
            )

    if not options[BLACK] and not options[WHITE]:
        out = number(b - w + prisoners)
    else:
        out = Game(options[BLACK], options[WHITE])
    _memo[key] = out
    return out


# ------------------------------------------------------------ 走廊

def corridor(n, board_size=9, depth=1):
    """造一條【走廊】：黑的地，寬 1、長 n，右邊開一個口讓白進來。

    這是組合賽局論在圍棋裡最經典的一族例子（Berlekamp & Wolfe）。
    回傳 (board, region)。

    走廊長這樣（n = 3）：

            A B C D
          2 X X X O      <- 上面是黑牆，右邊 D 是白子
          1 . . . O      <- A1 B1 C1 就是走廊，白可以從 C1 這一頭擠進來
    """
    from go_core.board import Board
    b = Board(board_size)
    cols = "ABCDEFGHJ"
    region = []
    for i in range(n):
        b.place(BLACK, f"{cols[i]}{depth + 1}")       # 上面的黑牆
        region.append(b._pt(f"{cols[i]}{depth}"))
    b.place(WHITE, f"{cols[n]}{depth}")               # 右邊的白子（開口）
    b.place(WHITE, f"{cols[n]}{depth + 1}")
    return b, frozenset(region)


def describe(board, region):
    """把區域裡的點列出來，方便在書上對照。"""
    return sorted(format_coord(p, board.n) for p in region)
