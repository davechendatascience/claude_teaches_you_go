#!/usr/bin/env python
"""產生第 8 章用到的所有 positions/*.sgf。

征子的三張圖（本形、路徑、陰影）不是手畫的 —— 它們由 go_core/ladder.py
算出來之後直接寫進 SGF。陰影尤其是：盤上每一點都放一顆子試一次，
看征子的結果會不會翻轉。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from go_core.board import BLACK, WHITE, Board, format_coord   # noqa: E402
from go_core.ladder import ladder_capture, ladder_shadow      # noqa: E402
from go_core.sgf import save_sgf                              # noqa: E402

OUT = ROOT / "positions"
OUT.mkdir(exist_ok=True)


# ---------------------------------------------------------------- 征子

LN = 13
LADDER_BLACK = ["D10"]
LADDER_WHITE = ["D11", "C10", "E11"]


def ladder_setup():
    b = Board(LN)
    b.place_many(BLACK, LADDER_BLACK)
    b.place_many(WHITE, LADDER_WHITE)
    return b


_lb = ladder_setup()
_ok, _path = ladder_capture(_lb, "D10", WHITE, max_depth=200)
assert _ok, "這個盤面應該是征子成立的"
PATH_PTS = {p for _, p in _path}
_shadow = ladder_shadow(_lb, "D10", WHITE, max_depth=200)

# 路徑圖：把整條征子的著手都擺上去（用 AB/AW，因為手數超過 9 手不能編號）
_path_black = [format_coord(p, LN) for c, p in _path if c == BLACK]
_path_white = [format_coord(p, LN) for c, p in _path if c == WHITE]

# 陰影圖：x = 在征子路徑上，o = 不在路徑上但仍能破征子（真正的引徵）
_shadow_labels = {format_coord(p, LN): ("x" if p in PATH_PTS else "o")
                  for p in _shadow}

# 引徵圖：挑一個【離戰場最遠】而且不在征子路徑上的陰影點。
# 「遠方的一顆子決定近處的勝負」正是征子引徵最反直覺的地方。
_origin = _lb._pt("D10")
_off_path = [p for p in _shadow if p not in PATH_PTS]
_breaker = max(_off_path, key=lambda q: abs(q[0] - _origin[0]) + abs(q[1] - _origin[1]))
BREAKER = format_coord(_breaker, LN)
_dist = abs(_breaker[0] - _origin[0]) + abs(_breaker[1] - _origin[1])


# ------------------------------------------------------------ 形狀

def shape_cluster():
    """把四種 4 子形狀擺在同一個 13 路盤上，彼此隔得夠遠。"""
    C = "ABCDEFGHJKLMN"
    put = lambda dc, dr, base: [f"{C[base[0] + c]}{base[1] + r}" for r, c in dc]
    straight = [(0, 0), (0, 1), (0, 2), (0, 3)]      # 直四
    bent = [(0, 0), (0, 1), (0, 2), (1, 0)]          # 曲四 L
    tee = [(0, 0), (0, 1), (0, 2), (1, 1)]           # 丁四 T
    square = [(0, 0), (0, 1), (1, 0), (1, 1)]        # 方四
    stones = (put(straight, None, (1, 11)) + put(bent, None, (8, 11))
              + put(tee, None, (1, 4)) + put(square, None, (8, 4)))
    # 標記放在形狀【左邊的空點】上，才不會蓋掉棋子
    labels = {f"{C[0]}11": "a", f"{C[7]}11": "b",
              f"{C[0]}4": "c", f"{C[7]}4": "d"}
    return stones, labels


SHAPE_STONES, SHAPE_LABELS = shape_cluster()


POSITIONS = {
    # --- §4.2 形狀比較 ------------------------------------------------
    "ch08_four_shapes": dict(n=13, AB=SHAPE_STONES, LB=SHAPE_LABELS,
        comment="四種 4 子形狀，彼此隔得很遠、互不影響。"
                "a 直四、b 曲四、c 丁四、d 方四。四種都是四顆子，"
                "氣卻分別是 10、9、8、8 —— 而且 d 少的兩口和 b、c 少的來源不同。",
    ),

    # --- §4.3 手筋 -----------------------------------------------------
    "ch08_double_atari": dict(n=9,
        AB=["B3", "D3"], AW=["A3", "B4", "E3", "D4"],
        LB={"C3": "a"},
        comment="雙打：黑 B3 與 D3 各有兩口氣，而它們【共用】C3 這一口。"
                "白下 a，兩塊同時剩一口氣 —— 一手只能救一塊。又是鴿籠原理。",
    ),
    "ch08_snapback": dict(n=9,
        AB=["A2", "B2"], AW=["A3", "B3", "C2", "C1"],
        LB={"A1": "a", "B1": "b"},
        comment="倒撲的本形。黑兩子只剩 a、b 兩口氣，而且【兩口氣是相鄰的】—— "
                "這正是倒撲成立的幾何條件。白下 a 會怎樣？",
    ),
    "ch08_snapback_2": dict(n=9,
        AB=["A2", "B2"], AW=["A3", "B3", "C2", "C1"],
        moves=[("W", "A1")],
        LB={"B1": "b"},
        comment="白 1 送一子。那顆白子的鄰點是 A2（黑）與 b —— 只剩一口氣，"
                "看起來是白白送死。黑當然想提它，而提的方法是下在 b。",
    ),
    "ch08_snapback_3": dict(n=9,
        AB=["A2", "B2", "B1"], AW=["A3", "B3", "C2", "C1"],
        LB={"A1": "a"},
        comment="黑提掉白一子之後。但黑那一手下在 B1 —— 【那本來是自己的氣】。"
                "現在黑三子只剩 a 一口。白再下 a，提黑三子。送一得三。",
    ),
    "ch08_connect": dict(n=9,
        AB=["A1", "A2", "C1", "C2"], AW=["A3", "B3", "C3", "D1", "D2"],
        LB={"B1": "a", "B2": "b"},
        comment="黑左右兩塊有【兩個】接點 a 與 b。這是接不歸的結構："
                "如果白能一手同時威脅兩個接點，黑一手只接得了一個。",
    ),

    # --- §4.4 征子 -----------------------------------------------------
    "ch08_ladder": dict(n=LN, AB=LADDER_BLACK, AW=LADDER_WHITE,
        LB={"D9": "a", "E10": "b"},
        comment="征子的本形。黑 D10 只有 a、b 兩口氣。白該從哪一邊叫吃？"
                "兩邊都試一遍 —— 只有一邊征得到。",
    ),
    "ch08_ladder_path": dict(n=LN,
        AB=LADDER_BLACK + _path_black, AW=LADDER_WHITE + _path_white,
        comment=f"征子跑完的樣子，共 {len(_path)} 手，一路斜到右下角。"
                "這條路徑不是畫的，是 go_core/ladder.py 讀出來的。",
    ),
    "ch08_ladder_shadow": dict(n=LN, AB=LADDER_BLACK, AW=LADDER_WHITE,
        LB=_shadow_labels,
        comment=f"征子陰影，共 {len(_shadow)} 個點。做法是：盤上每一個空點都放一顆"
                "黑子試一次，重跑征子，看結果會不會翻轉。"
                "x 在征子路徑上；o 不在路徑上，卻仍然能破征子 —— 那才是真正的「引徵」。",
    ),
    "ch08_ladder_broken": dict(n=LN,
        AB=LADDER_BLACK + [BREAKER], AW=LADDER_WHITE,
        MA=[BREAKER],
        comment=f"在陰影裡放一顆黑子（標 # 的那顆，{BREAKER}），征子就不成立了。"
                f"它離黑 D10 有 {_dist} 路遠，中間隔著整個棋盤 —— "
                "但白再怎麼叫吃，黑都跑得掉。這就是「征子引徵」。",
    ),

    # --- §6 練習 --------------------------------------------------------
    "ch08_ex1": dict(n=9,
        AB=["C4", "C5", "D5"],
        LB={"D4": "a"},
        comment="練習 8.1：黑三子是空三角。用第 2 章的三項分解算出它有幾口氣，"
                "然後回答：如果黑再下 a 補成方四，氣會變多還是變少？",
    ),
    "ch08_ex2": dict(n=9,
        AB=["C3", "E3"], AW=["B3", "C4", "F3", "E4"],
        comment="練習 8.2：白有沒有雙打？如果有，在哪裡？"
                "如果沒有，白要先下哪一手才能製造出雙打？",
    ),
    "ch08_ex3": dict(n=LN, AB=LADDER_BLACK, AW=LADDER_WHITE,
        LB={"G7": "a", "K7": "b", "M11": "c"},
        comment="練習 8.3：a、b、c 三個點，黑在哪些點放一顆子可以破掉這個征子？"
                "先用眼睛判斷（它們離那條斜線多遠），再用程式核對。",
    ),
}


def main():
    for name, spec in POSITIONS.items():
        save_sgf(str(OUT / f"{name}.sgf"), None, n=spec.get("n", 9),
                 AB=spec.get("AB", ()), AW=spec.get("AW", ()), AE=spec.get("AE", ()),
                 LB=spec.get("LB"), MA=spec.get("MA", ()),
                 moves=spec.get("moves", ()), comment=spec.get("comment"))
    print(f"寫出 {len(POSITIONS)} 個盤面")
    print(f"  征子：{len(_path)} 手，陰影 {len(_shadow)} 點"
          f"（其中 {len(_shadow - PATH_PTS)} 點不在路徑上）")
    print(f"  選來當引徵的點：{BREAKER}")


if __name__ == "__main__":
    main()
