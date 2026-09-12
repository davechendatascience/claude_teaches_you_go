"""一個夠用就好的 SGF 讀寫器。

為什麼不用現成的函式庫：見 docs/03_writing_brief.md §5。書上每一張棋圖都必須
能被讀者自己重現，所以連 SGF 解析都要看得見。

支援的屬性：
    SZ  盤面大小
    AB / AW / AE   擺黑子 / 擺白子 / 清空（設定題目盤面用）
    B / W          實際的著手（會依序編號 1..9，並執行提子）
    LB[xx:a]       參考標記
    MA[xx]         標記棋子（畫成 #）
    C[...]         註解，讀進來但不畫

不支援的：分支、時間、rank 等對本書無用的東西。
"""

import re

from go_core.board import Board, BLACK, WHITE, EMPTY

_PROP = re.compile(r"([A-Z]{1,2})((?:\[(?:\\.|[^\\\]])*\])+)", re.S)
_VALUE = re.compile(r"\[((?:\\.|[^\\\]])*)\]", re.S)


def _sgf_to_pt(s, n):
    """SGF 的 'dd' -> 內部的 (r, c)。空字串或 'tt' 表示虛手。"""
    if s == "" or (s == "tt" and n <= 19):
        return None
    c = ord(s[0]) - ord("a")
    r = ord(s[1]) - ord("a")
    if not (0 <= r < n and 0 <= c < n):
        raise ValueError(f"SGF 座標 {s!r} 超出 {n} 路盤")
    return (r, c)


def pt_to_sgf(pt):
    r, c = pt
    return chr(ord("a") + c) + chr(ord("a") + r)


def _nodes(text):
    """把 SGF 切成一串節點，每個節點是 {屬性: [值, ...]}。"""
    text = text.strip()
    if text.startswith("("):
        text = text[1:]
    if text.endswith(")"):
        text = text[:-1]
    out = []
    for chunk in text.split(";"):
        if not chunk.strip():
            continue
        props = {}
        for name, blob in _PROP.findall(chunk):
            props[name] = [m.replace("\\]", "]") for m in _VALUE.findall(blob)]
        out.append(props)
    return out


def load_sgf(path_or_text):
    """讀一個 SGF，回傳 (board, numbers, labels, marks, comment)。

    numbers 是 {pt: 第幾手}，可以直接餵給 go_core.render.render_ascii。
    """
    text = path_or_text
    if "\n" not in text and text.strip().endswith(".sgf"):
        with open(text, encoding="utf-8") as fh:
            text = fh.read()

    nodes = _nodes(text)
    if not nodes:
        raise ValueError("空的 SGF")

    root = nodes[0]
    n = int(root.get("SZ", ["19"])[0])
    board = Board(n)

    for v in root.get("AB", []):
        pt = _sgf_to_pt(v, n)
        if pt:
            board.grid[pt] = BLACK
    for v in root.get("AW", []):
        pt = _sgf_to_pt(v, n)
        if pt:
            board.grid[pt] = WHITE
    for v in root.get("AE", []):
        pt = _sgf_to_pt(v, n)
        if pt:
            board.grid[pt] = EMPTY

    labels = {}
    marks = set()
    comment_parts = []
    for node in nodes:
        for v in node.get("LB", []):
            coord, _, ch = v.partition(":")
            pt = _sgf_to_pt(coord, n)
            if pt:
                labels[pt] = ch
        for v in node.get("MA", []):
            pt = _sgf_to_pt(v, n)
            if pt:
                marks.add(pt)
        if "C" in node:
            comment_parts.extend(node["C"])

    numbers = {}
    move_no = 0
    for node in nodes[1:]:
        for key, color in (("B", BLACK), ("W", WHITE)):
            if key in node:
                pt = _sgf_to_pt(node[key][0], n)
                if pt is None:
                    continue                      # 虛手
                move_no += 1
                board.play(color, pt)
                numbers[pt] = move_no

    return board, numbers, labels, marks, "\n".join(comment_parts)


def save_sgf(path, board_or_none, n=9, AB=(), AW=(), AE=(), LB=None, MA=(),
             moves=(), comment=None):
    """寫一個最小 SGF。座標一律用人類座標字串（"D4"）。"""
    from go_core.board import parse_coord

    def block(name, coords):
        if not coords:
            return ""
        return name + "".join(f"[{pt_to_sgf(parse_coord(x, n))}]" for x in coords)

    head = f";GM[1]FF[4]CA[UTF-8]SZ[{n}]"
    head += block("AB", AB) + block("AW", AW) + block("AE", AE)
    if LB:
        head += "LB" + "".join(
            f"[{pt_to_sgf(parse_coord(k, n))}:{v}]" for k, v in LB.items()
        )
    head += block("MA", MA)
    if comment:
        head += "C[" + comment.replace("]", "\\]") + "]"

    body = ""
    for color, coord in moves:
        key = "B" if color in (BLACK, "B", "b") else "W"
        body += f";{key}[{pt_to_sgf(parse_coord(coord, n))}]"

    text = "(" + head + body + ")\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return text
