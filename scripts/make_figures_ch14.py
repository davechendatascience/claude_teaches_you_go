#!/usr/bin/env python
"""產生第 14 章用到的 figures/*.txt。（跑完約需一分鐘）

四張表，全部算出來：
  * ch14_anatomy3   3 路盤最優對局的逐手解剖（V 已知）
  * ch14_scorecard  五層在 1,742 個已解局面上的成績單
  * ch14_conflicts  兩層衝突時誰對
  * ch14_checklist  自我覆盤清單（唯一一張不是算出來的 —— 它是本書的摘要）
"""

import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.setrecursionlimit(200000)
sys.path.insert(0, str(ROOT))

from go_core.anatomy import (LAYER_NAMES, coverage, explain_game,      # noqa: E402
                             layer1_candidates, layer2_candidates,
                             layer3_candidates, layer4_candidates,
                             render_table)
from go_core.board import BLACK, Board, format_coord, opposite         # noqa: E402
from go_core.minimax import Solver, legal_moves                        # noqa: E402
from go_core.tewari import _board_from_key, reachable_states, solve_all  # noqa: E402

OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)

N, MAX_PLY = 3, 15
LAYER_FN = {1: layer1_candidates, 2: layer2_candidates,
            3: layer3_candidates, 4: layer4_candidates}


def optimal_3x3_game():
    s = Solver(komi=0.0, max_ply=MAX_PLY)
    b, colour, ko, passes, ply, mv = Board(N), BLACK, None, 0, 0, []
    while ply < MAX_PLY and passes < 2:
        _, m = s.search(b, colour, passes=passes, ko=ko, ply=ply)
        if m is None:
            mv.append((colour, None))
            passes += 1
            ko = None
        else:
            mv.append((colour, format_coord(m, N)))
            for p, ch, nk in legal_moves(b, colour, ko):
                if p == m:
                    b, ko = ch, nk
                    break
            passes = 0
        colour = opposite(colour)
        ply += 1
    return mv


GAME = optimal_3x3_game()
ROWS = explain_game(GAME, n=N, with_v=True, max_ply=MAX_PLY)
COV = coverage(ROWS)

print("  解 1,742 個局面 ...", flush=True)
_t = time.time()
STATES = reachable_states(N, 4)
TABLE, _ = solve_all(STATES, n=N)
NOMS = {k: {} for k in LAYER_FN}
for key in TABLE:
    b, c, ko = _board_from_key(key, N)
    for k, fn in LAYER_FN.items():
        NOMS[k][key] = fn(b, c, ko)[0]
print(f"  完成（{time.time() - _t:.0f}s）", flush=True)


def anatomy3():
    out = [render_table(ROWS, n=N, with_v=True), ""]
    out.append(f"  O = 那一層自己的判準會挑這一手；. = 不會。")
    out.append(f"  這是【最優對局】，所以第 5 層（值函數）整欄都是 O。")
    out.append("")
    out.append(f"  {'層':<8}{'命中率':>9}{'選擇性':>9}")
    for k in sorted(COV["hit_rate"]):
        out.append(f"  {LAYER_NAMES[k]:<8}{COV['hit_rate'][k]:>9.0%}"
                   f"{COV['selectivity'][k]:>9.0%}")
    out.append("")
    out.append(f"  一層都解釋不了的手：{COV['unexplained']} / {COV['total']}")
    return "\n".join(out)


def scorecard():
    out = [f"  {'層':<8}{'開口的局面':>12}{'命中率*':>9}{'亂猜基準**':>12}"
           f"{'選擇性':>9}",
           "  " + "-" * 52]
    for k in sorted(LAYER_FN):
        spoke = hit = nom = leg = 0
        base = []
        for key, (best, _v) in TABLE.items():
            b, c, ko = _board_from_key(key, N)
            s = NOMS[k][key]
            nom += len(s)
            n_legal = len(legal_moves(b, c, ko))
            leg += n_legal
            if s:
                spoke += 1
                hit += bool(s & best)
                base.append(len(best) / n_legal)
        rand = sum(base) / len(base)
        out.append(f"  {LAYER_NAMES[k]:<8}{spoke:>12}{hit / spoke:>9.1%}"
                   f"{rand:>12.1%}{1 - nom / leg:>9.1%}")
    out.append("")
    out.append("  *  命中率只算「那一層有開口」的局面。")
    out.append("  ** 在【同一批】局面裡隨機挑一個合法點的期望命中率。")
    out.append("")
    out.append("  死活與溫度只在五分之一的局面開口，而且一開口就從沒錯過 ——")
    out.append("  但要看基準線：它們開口的那些局面，平均 5.4 個合法點裡")
    out.append("  就有 4.3 個是最佳著，所以亂猜也有 80%。")
    out.append("  真正的證據不在這張表，在下一張（衝突）。")
    return chr(10).join(out)


def conflicts():
    out = [f"  {'A vs B':<18}{'都開口':>8}{'提名不同':>10}"
           f"{'只有A對':>9}{'只有B對':>9}{'都對':>7}{'都錯':>7}",
           "  " + "-" * 68]
    for a, bl in [(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)]:
        both = diff = ao = bo = ok = no = 0
        for key, (best, _v) in TABLE.items():
            sa, sb = NOMS[a][key], NOMS[bl][key]
            if not sa or not sb:
                continue
            both += 1
            if sa == sb:
                continue
            diff += 1
            ha, hb = bool(sa & best), bool(sb & best)
            if ha and hb:
                ok += 1
            elif ha:
                ao += 1
            elif hb:
                bo += 1
            else:
                no += 1
        label = f"{LAYER_NAMES[a]} vs {LAYER_NAMES[bl]}"
        out.append(f"  {label:<18}{both:>8}{diff:>10}{ao:>9}{bo:>9}{ok:>7}{no:>7}")
    out.append("")
    out.append("  死活與溫度在 3 路盤上永遠提名相同（盤面太小，同時只有一塊未定的棋）。")
    out.append("  而它們【從來沒有輸過】任何一次衝突 —— 連通性 0 勝，場 0 勝。")
    out.append("")
    out.append("  嚴格的優先序：死活 = 溫度  >  場  >  連通性")
    return "\n".join(out)


def bill():
    union_hit = 0
    n_right = Counter()
    for key, (best, _v) in TABLE.items():
        u = set()
        r = 0
        for k in LAYER_FN:
            s = NOMS[k][key]
            u |= s
            r += bool(s & best)
        union_hit += bool(u & best)
        n_right[r] += 1
    total = len(TABLE)
    out = [f"  至少有一層提名到最佳著：{union_hit} / {total} = {union_hit/total:.1%}",
           f"  四層【全部】落空：      {total-union_hit} / {total} = "
           f"{(total-union_hit)/total:.1%}", "",
           f"  {'同時說對的層數':<16}{'局面數':>8}{'佔比':>8}"]
    for n in sorted(n_right):
        out.append(f"  {n:<16}{n_right[n]:>8}{n_right[n]/total:>8.1%}")
    return "\n".join(out)


CHECKLIST = """
  自我覆盤清單                                            （可列印，一頁）
  ======================================================================

  對【每一手】問：

    1. 這手棋在哪一層？
       連通性 / 死活 / 溫度 / 場 / 值函數
       -> 答不出來的手，多半沒有理由，只有印象。

    2. 它的溫度是多少？當時的全局溫度是多少？
       未定塊的溫度 = 賭注 s + t（第 12 章命題 12.3）
       大場的溫度  = 出入 / 2（第 7 章定理 7.6）
       -> 記得把薄棋的價碼【乘二】再比（第 12 章）。

    3. 有沒有更高溫度的局部被忽略？
       -> 這是「大場不如急場」的操作版本。

    4. 我方哪些棋塊【不是】Benson 活？
       -> 那些就是你的賭注。列出來，加總。

    5. 這一手有沒有把一塊棋切成兩塊？
       -> 做活點從 e-2 掉到 e-4（第 12 章 §4.6）。

  對【整局】問：

    6. Delta_V 損失最大的三手在哪裡？它們屬於同一類錯誤嗎？
       -> 看分佈，不要看單點（第 10 章 §3）。

    7. 我輸的那幾目，是【手數差】還是【判斷差】？
       -> C - J = b - w（第 13 章定理 13.2）。

    8. 有沒有一手，四層都說不出理由？
       -> 那是你真正該想的地方 —— 也可能是本書欠你的帳（§4.5）。

  ======================================================================
"""


FIGURES = {
    "ch14_anatomy3": anatomy3,
    "ch14_scorecard": scorecard,
    "ch14_conflicts": conflicts,
    "ch14_bill": bill,
    "ch14_checklist": lambda: CHECKLIST.strip("\n"),
}


def main():
    for name, fn in FIGURES.items():
        (OUT / f"{name}.txt").write_text(fn().rstrip("\n") + "\n",
                                         encoding="utf-8", newline="\n")
        print(f"  寫出 {name}.txt")


if __name__ == "__main__":
    main()
