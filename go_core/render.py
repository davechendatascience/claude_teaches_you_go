"""把盤面畫成書上的 ASCII 棋圖。

字元約定見 docs/03_writing_brief.md §4.2：

    X    黑子
    O    白子
    .    空點
    +    空的星位
    1-9  著手順序（一張圖最多 9 手，超過就分圖）
    a-h  正文要指涉的參考點
    #    被標記的棋子

正文中不准手打棋圖 —— 每一張都必須經過這個函式。
"""

from go_core.board import EMPTY, BLACK, WHITE, STAR_POINTS, col_letters, parse_coord

_STONE = {EMPTY: ".", BLACK: "X", WHITE: "O"}


def render_ascii(board, numbers=None, labels=None, marks=None, show_stars=True):
    """回傳一張 ASCII 棋圖（不含前後的 code fence）。

    numbers : {pt: int}   著手順序，1..9
    labels  : {pt: str}   單一字元的參考標記，通常是 'a'..'h'
    marks   : iterable    要標成 '#' 的棋子
    """
    n = board.n
    numbers = {board._pt(k): v for k, v in (numbers or {}).items()}
    labels = {board._pt(k): v for k, v in (labels or {}).items()}
    marks = {board._pt(k) for k in (marks or ())}
    stars = set()
    if show_stars:
        stars = {parse_coord(s, n) for s in STAR_POINTS.get(n, [])}

    letters = " ".join(col_letters(n))
    head = "     " + letters
    lines = [head]
    for r in range(n):
        num = n - r
        cells = []
        for c in range(n):
            pt = (r, c)
            v = int(board.grid[pt])
            if pt in numbers and v != EMPTY:
                # 已經被提掉的子不標號 —— 靜態棋圖上，空點的編號沒有意義
                d = numbers[pt]
                if not 1 <= d <= 9:
                    raise ValueError("一張棋圖最多只能標 9 手，超過請分圖（見寫作規範 §4.2）")
                cells.append(str(d))
            elif pt in labels:
                ch = labels[pt]
                if len(ch) != 1:
                    raise ValueError(f"標記 {ch!r} 必須是單一字元")
                cells.append(ch)
            elif pt in marks:
                cells.append("#")
            elif v == EMPTY and pt in stars:
                cells.append("+")
            else:
                cells.append(_STONE[v])
        lines.append(f"  {num:2d} " + " ".join(cells) + f" {num}")
    lines.append(head)
    return "\n".join(lines)


def render_block(board, caption, **kwargs):
    """連同 ```text 圍欄與底下的「請看什麼」說明行一起回傳。

    寫作規範 §4.3：每張棋圖正下方必須有一行斜體說明。棋圖不會自己說話。
    """
    body = render_ascii(board, **kwargs)
    return f"```text\n{body}\n```\n*{caption}*"
