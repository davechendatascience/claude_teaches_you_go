#!/usr/bin/env python
"""產生第 12 章用到的 positions/*.sgf。

眼位的「做活點」不是手標的 —— 它們由 go_core.attack.vital_points 算出來，
再寫進 SGF 的標記。

**每一句說明文字裡的死活宣稱，這支腳本都會先驗證過再寫出去**（見 `check`）。
本書寫作時在這裡踩過一次：原本用眼位 5 當「未定」的例子，但眼位 5 的
做活點有 3 個，白先手根本殺不掉 —— 那塊棋早就活了，沒有擺盪可言。
真正未定的是眼位 3。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.setrecursionlimit(100000)
sys.path.insert(0, str(ROOT))

from go_core.attack import (can_kill, enclosed_empties, is_alive,   # noqa: E402
                            life_swing, stake, vital_points)
from go_core.board import BLACK, WHITE, Board, format_coord         # noqa: E402
from go_core.sgf import save_sgf                                    # noqa: E402
from go_core.strings import find_string                             # noqa: E402

OUT = ROOT / "positions"
OUT.mkdir(exist_ok=True)

N = 9


def corridor(eyespace):
    """眼位 A1..A(e) 的一塊黑棋，四周被白包住。回傳 (黑, 白)。"""
    e = eyespace
    black = [f"B{r}" for r in range(1, e + 2)] + [f"A{e + 1}"]
    white = [f"C{r}" for r in range(1, e + 2)] + [f"B{e + 2}", f"A{e + 2}"]
    return black, white


def build(eyespace, extra_black=(), extra_white=()):
    black, white = corridor(eyespace)
    b = Board(N)
    b.place_many(BLACK, black)
    b.place_many(WHITE, list(white) + list(extra_white))
    b.place_many(BLACK, list(extra_black))
    return b, find_string(b, "B1")


def facts(eyespace):
    b, S = build(eyespace)
    return {
        "stake": stake(b, S),
        "stones": len(S),
        "territory": len(enclosed_empties(b, S)),
        "swing": life_swing(b, S),
        "vital": [format_coord(p, N) for p in vital_points(b, S, BLACK)],
        "attacker_kills": can_kill(b, S, BLACK, max_moves=3),
    }


F3, F4, F5 = facts(3), facts(4), facts(5)

# ---- 說明文字裡的宣稱，先驗證 ----
assert F3["vital"] == ["A2"] and F3["attacker_kills"], F3
assert len(F4["vital"]) == 2 and not F4["attacker_kills"], F4
assert len(F5["vital"]) == 3 and not F5["attacker_kills"], F5
assert F3["swing"] == 2 * F3["stake"] == 16, F3

_alive, _Sa = build(3, extra_black=["A2"])
assert is_alive(_alive, find_string(_alive, "B1"), BLACK), "黑下 A2 應該活"
_dead, _Sd = build(3, extra_white=["A2"])
assert not vital_points(_dead, find_string(_dead, "B1"), BLACK), "白下 A2 之後黑無做活點"

_conn = Board(N)
_conn.place_many(BLACK, ["B1", "B2", "B3", "B4", "B5", "A5"])
_conn.place_many(WHITE, ["C1", "C2", "C3", "C4", "C5", "B6", "A6"])
_Sc = find_string(_conn, "B1")
assert len(vital_points(_conn, _Sc, BLACK)) == 2
assert not can_kill(_conn, _Sc, BLACK, max_moves=3), "連著應該殺不掉"

_split = Board(N)
_split.place_many(BLACK, ["B1", "B2", "B3", "A3", "B6", "B7", "B8", "A6"])
_split.place_many(WHITE, ["C1", "C2", "C3", "B4", "A4", "C6", "C7", "C8",
                          "B9", "A9", "B5", "A5"])
for _seed in ["B1", "B6"]:
    _Ss = find_string(_split, _seed)
    assert vital_points(_split, _Ss, BLACK) == [], f"{_seed} 不該有做活點"
    assert can_kill(_split, _Ss, BLACK, max_moves=3), f"{_seed} 應該殺得掉"

B3, W3 = corridor(3)
B4, W4 = corridor(4)
B5, W5 = corridor(5)
B2, W2 = corridor(2)

POSITIONS = {
    # --- §4.1 一塊真正未定的棋（眼位 3：誰先下誰贏）-----------------------
    "ch12_weak": dict(n=N, AB=B3, AW=W3,
        comment=f"一塊還沒定的黑棋。子數 {F3['stones']}、圍住的空點 "
                f"{F3['territory']}，賭注 {F3['stake']}。"
                "黑先下就活、白先下就死 —— 它同時記在兩個帳本上："
                "死活（第 2 層）與溫度（第 3 層）。",
    ),
    "ch12_alive": dict(n=N, AB=B3 + ["A2"], AW=W3,
        comment="黑先，下在唯一的做活點 A2。眼位被切成 A1 與 A3 兩個真眼 —— "
                "Benson 無條件活（第 3 章定理 3.10）。",
    ),
    "ch12_dead": dict(n=N, AB=B3, AW=W3 + ["A2"],
        comment="換白先下同一點。剩下 A1 與 A3 兩個孤立的點，"
                "而它們都不是真眼 —— 黑死。"
                f"同一個點、兩種結局，這就是 {F3['swing']} 目的擺盪。",
    ),

    # --- §4.4 做活點的個數 -------------------------------------------------
    "ch12_three": dict(n=N, AB=B3, AW=W3,
        LB={F3["vital"][0]: "a"},
        comment="眼位長 3（直三）。做活點只有 a 一個 —— 白先手佔住它，黑就死了。"
                "「直三死」不是要背的口訣，是做活點只有 3 - 2 = 1 個。",
    ),
    "ch12_four": dict(n=N, AB=B4, AW=W4,
        LB={c: ch for c, ch in zip(sorted(F4["vital"]), "ab")},
        comment="眼位長 4（直四）。做活點有 a、b 兩個 —— 白一手只佔得住一個，"
                "黑佔另一個就活。「直四活」= 做活點 4 - 2 = 2 個 + 鴿籠原理。",
    ),
    "ch12_five": dict(n=N, AB=B5, AW=W5,
        LB={c: ch for c, ch in zip(sorted(F5["vital"]), "abc")},
        comment="眼位長 5：做活點三個。眼位每長一格，做活點就多一個，"
                "而攻方永遠只有一手 —— 這就是「眼位要寬」的全部內容。",
    ),

    # --- §4.6 連接與分斷 ---------------------------------------------------
    "ch12_connected": dict(n=N,
        AB=["B1", "B2", "B3", "B4", "B5", "A5"],
        AW=["C1", "C2", "C3", "C4", "C5", "B6", "A6"],
        comment="連在一起的一塊，眼位 4（A1-A4）。做活點兩個，白先手也殺不掉。",
    ),
    "ch12_split": dict(n=N,
        AB=["B1", "B2", "B3", "A3", "B6", "B7", "B8", "A6"],
        AW=["C1", "C2", "C3", "B4", "A4", "C6", "C7", "C8",
            "B9", "A9", "B5", "A5"],
        comment="同樣的子數被切成兩塊，各自只剩兩點眼位。"
                "兩塊的做活點都是 0 —— 兩塊【都死】。連接不是防守的一種，"
                "它常常就是防守本身。",
    ),

    # --- §6 練習 -----------------------------------------------------------
    "ch12_ex1": dict(n=N, AB=B2, AW=W2,
        comment="練習 12.1：眼位長 2。算出這塊棋的賭注與死活擺盪，"
                "並回答：它有幾個做活點？為什麼這塊棋不管誰先下都一樣？",
    ),
    "ch12_ex2": dict(n=N, AB=B3, AW=W3,
        comment="練習 12.2：這塊棋的賭注是 8。棋盤別處最大的大場出入 20 目。"
                "該先補這塊棋，還是先佔大場？先用直覺答，再用判定式算。",
    ),
    "ch12_ex3": dict(n=N, AB=B4, AW=W4,
        comment="練習 12.3：直四。白先手殺得掉嗎？"
                "把做活點的個數和鴿籠原理連起來，說明為什麼。",
    ),
}


def main():
    for name, spec in POSITIONS.items():
        save_sgf(str(OUT / f"{name}.sgf"), None, n=spec.get("n", 9),
                 AB=spec.get("AB", ()), AW=spec.get("AW", ()), AE=spec.get("AE", ()),
                 LB=spec.get("LB"), MA=spec.get("MA", ()),
                 moves=spec.get("moves", ()), comment=spec.get("comment"))
    print(f"寫出 {len(POSITIONS)} 個盤面（說明文字裡的死活宣稱都已驗證）")
    for e, f in [(3, F3), (4, F4), (5, F5)]:
        print(f"  眼位 {e}：賭注 {f['stake']}、擺盪 {f['swing']}、"
              f"做活點 {f['vital']}、攻方先手殺得掉 = {f['attacker_kills']}")


if __name__ == "__main__":
    main()
