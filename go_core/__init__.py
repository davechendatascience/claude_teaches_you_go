"""go_core —— 《Claude 教你圍棋》的計算核心。

設計原則（見 docs/03_writing_brief.md §5）：
  1. 純 Python + NumPy。不使用 SciPy、SymPy，也不使用任何現成的圍棋函式庫。
  2. 每一個函式都短到可以整段印在書上，而且書上出現的每一條公式，
     都能在這裡找到一段直接對應的程式碼。
  3. 沒有黑盒。書上說「這塊棋有 7 口氣」，讀者必須能自己跑出 7。
"""

from go_core.board import (
    EMPTY, BLACK, WHITE,
    Board, neighbors, degree, parse_coord, format_coord, opposite,
)
from go_core.strings import (
    find_string, neighbor_set, liberties, liberty_count, all_strings,
)

__all__ = [
    "EMPTY", "BLACK", "WHITE",
    "Board", "neighbors", "degree", "parse_coord", "format_coord", "opposite",
    "find_string", "neighbor_set", "liberties", "liberty_count", "all_strings",
]
