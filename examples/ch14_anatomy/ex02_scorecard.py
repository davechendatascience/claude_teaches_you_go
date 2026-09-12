#!/usr/bin/env python
"""第 14 章配套範例 2：五層的成績單、基準線、衝突與帳單。

對應章節：第 14 章 §4.3、§4.4、§4.5、§5.3、練習 14.2。

這支腳本把 3 路盤上 1,742 個「可達且已解」的局面全部跑一遍，回答四個問題：

  1. 每一層開口多少次？開口的時候命中率多少？          （成績單）
  2. 在【同一批局面】裡亂猜的命中率是多少？            （基準線 —— 最重要的一欄）
  3. 兩層提名不同的時候，誰對？                        （衝突）
  4. 四層一起落空的局面有多少？它們長什麼樣子？        （帳單）

第 2 題是本章寫作時修正自己的地方：死活層 100% 的命中率看起來很漂亮，
但它開口的那些局面【亂猜也有 80%】。報告命中率而不報告基準線，
就是在誤導自己。

跑法（在專案根目錄，約需 30 秒）：
    python examples/ch14_anatomy/ex02_scorecard.py
"""

import statistics
import sys
import time
from collections import Counter
from pathlib import Path

sys.setrecursionlimit(200000)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from go_core import format_coord                                      # noqa: E402
from go_core.anatomy import (LAYER_NAMES, layer1_candidates,          # noqa: E402
                             layer2_candidates, layer3_candidates,
                             layer4_candidates)
from go_core.minimax import legal_moves                               # noqa: E402
from go_core.tewari import (_board_from_key, reachable_states,        # noqa: E402
                            solve_all)

N = 3
LAYERS = {1: layer1_candidates, 2: layer2_candidates,
          3: layer3_candidates, 4: layer4_candidates}


def bar(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


print(f"  解 {N} 路盤上所有可達的局面 ...", flush=True)
_t = time.time()
TABLE, _ = solve_all(reachable_states(N, 4), n=N)
NOM, LEGAL, BEST = {}, {}, {}
for key in TABLE:
    b, c, ko = _board_from_key(key, N)
    LEGAL[key] = len(legal_moves(b, c, ko))
    BEST[key] = len(TABLE[key][0])
    for k, fn in LAYERS.items():
        NOM.setdefault(k, {})[key] = fn(b, c, ko)[0]
print(f"  完成：{len(TABLE)} 個局面（{time.time() - _t:.0f} 秒）")


# --------------------------------------------------------------- 1 + 2

def scorecard():
    bar("1+2. 成績單 —— 以及它旁邊那一欄基準線")
    print(f"  {'層':<8}{'開口':>8}{'開口率':>9}{'命中率':>9}"
          f"{'亂猜基準':>10}{'贏基準':>9}{'選擇性':>9}")
    print("  " + "-" * 62)
    rows = {}
    for k in sorted(LAYERS):
        spoke = hit = nom = leg = 0
        base = []
        for key, (best, _v) in TABLE.items():
            s = NOM[k][key]
            nom += len(s)
            leg += LEGAL[key]
            if s:
                spoke += 1
                hit += bool(s & best)
                base.append(BEST[key] / LEGAL[key])
        rate, rand = hit / spoke, statistics.mean(base)
        rows[k] = (spoke, rate, rand)
        print(f"  {LAYER_NAMES[k]:<8}{spoke:>8}{spoke / len(TABLE):>9.1%}"
              f"{rate:>9.1%}{rand:>10.1%}{rate - rand:>+9.1%}"
              f"{1 - nom / leg:>9.1%}")
    print("\n  * 命中率只算「那一層有開口」的局面。")
    print("  * 亂猜基準 = 在【同一批】局面裡隨機挑一個合法點的期望命中率。")

    assert rows[2][1] == 1.0                      # 死活：開口就沒錯過
    assert 0.75 < rows[2][2] < 0.85               # 但基準線就有 80%
    assert rows[4][1] - rows[4][2] > 0.35         # 場贏基準線 40 個百分點以上
    print("\n  看那一欄「贏基準」：死活的 100% 只贏基準線 20 個百分點，")
    print("  而場的 86.5% 贏了 41 個百分點。命中率高的那個反而贏得少。")
    print("\n  但這兩個數字【不能直接比】—— 它們算在不同的局面集合上")
    print("  （死活只有 364 個，場有 1742 個）。要公平比較，得把兩層")
    print("  放進同一批局面裡看 —— 那正是下一節做的事。")
    return rows


def baseline_detail():
    bar("2b. 為什麼死活層的 100% 沒有看起來那麼強")
    keys = [k for k in TABLE if NOM[2][k]]
    lg = [LEGAL[k] for k in keys]
    bt = [BEST[k] for k in keys]
    print(f"  死活層開口的局面：{len(keys)} 個")
    print(f"    平均合法點  = {statistics.mean(lg):.1f}")
    print(f"    平均最佳著  = {statistics.mean(bt):.1f}")
    print(f"    -> 亂猜的期望命中率 = "
          f"{statistics.mean(b / l for b, l in zip(bt, lg)):.1%}")

    h = {k: sum(bool(NOM[k][key] & TABLE[key][0]) for key in keys)
         for k in LAYERS}
    print(f"\n  在【同一批】{len(keys)} 個局面裡，各層的命中率：")
    for k in sorted(LAYERS):
        print(f"    {LAYER_NAMES[k]:<6}{h[k] / len(keys):>8.1%}"
              f"   （{h[k]} / {len(keys)}）")
    assert h[2] == len(keys)
    assert h[4] / len(keys) > 0.95
    print(f"\n  死活 100%、場 {h[4] / len(keys):.1%} —— 相差 {h[2] - h[4]} 個局面。")
    print("  這就是「死活 > 場」這條優先序的【全部】證據量。")
    print("  方向沒有例外，但效果量只有個位數。兩件事都要說。")


# --------------------------------------------------------------- 3

def conflicts():
    bar("3. 衝突：兩層提名不同的時候，誰對？")
    print(f"  {'A vs B':<18}{'都開口':>8}{'不同':>7}"
          f"{'只有A對':>9}{'只有B對':>9}{'都對':>7}{'都錯':>7}")
    print("  " + "-" * 65)
    wins = Counter()
    for a, bl in [(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)]:
        both = diff = ao = bo = ok = no = 0
        for key, (best, _v) in TABLE.items():
            sa, sb = NOM[a][key], NOM[bl][key]
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
                wins[a] += 1
            elif hb:
                bo += 1
                wins[bl] += 1
            else:
                no += 1
        print(f"  {LAYER_NAMES[a] + ' vs ' + LAYER_NAMES[bl]:<18}"
              f"{both:>8}{diff:>7}{ao:>9}{bo:>9}{ok:>7}{no:>7}")

    print("\n  死活與溫度在 3 路盤上永遠提名相同（盤太小，同時只有一塊未定的棋）。")
    print("  而它們在所有衝突裡【一次都沒輸過】。")
    print("\n  嚴格的優先序：死活 = 溫度  >  場  >  連通性")
    print("\n  衝突比命中率是更好的證據 —— 因為【分歧本身】就排除了")
    print("  「這個局面隨便下都對」的那些局面，基準線的問題自動消失。")
    print(f"\n  各層在所有衝突裡的總勝場："
          f"{ {LAYER_NAMES[k]: wins[k] for k in sorted(LAYERS)} }")
    return wins


# --------------------------------------------------------------- 4

def the_bill():
    bar("4. 帳單：四層一起落空的局面")
    union_hit, n_right, misses = 0, Counter(), []
    for key, (best, _v) in TABLE.items():
        u = set()
        r = 0
        for k in LAYERS:
            s = NOM[k][key]
            u |= s
            r += bool(s & best)
        n_right[r] += 1
        if u & best:
            union_hit += 1
        else:
            misses.append(key)
    total = len(TABLE)
    print(f"  至少有一層命中：{union_hit} / {total} = {union_hit / total:.1%}")
    print(f"  四層全部落空：  {len(misses)} / {total} = "
          f"{len(misses) / total:.1%}")
    print(f"\n  {'同時說對的層數':<16}{'局面數':>8}{'佔比':>8}")
    for n in sorted(n_right):
        print(f"  {n:<16}{n_right[n]:>8}{n_right[n] / total:>8.1%}")

    # 那 9% 有一個共同的形狀嗎？
    def n_stones(bd):
        return sum(1 for p in bd.points() if bd.grid[p] != 0)

    cap = 0
    for key in misses:
        b, c, ko = _board_from_key(key, N)
        u = set()
        for k in LAYERS:
            u |= NOM[k][key]
        for p, child, _ in legal_moves(b, c, ko):
            if p in u and n_stones(child) <= n_stones(b):
                cap += 1        # 下了一子而總子數沒增加 -> 這一手提了子
                break
    print(f"\n  那 {len(misses)} 個落空的局面裡，有 {cap} 個"
          f"（{cap / len(misses):.0%}）的錯誤提名裡包含【提子】。")
    print("  四層一起說「去提子」，而正解是不提 —— 這是本書 9% 破口最典型的形狀。")
    print("  提子是最看得見的收穫，也是最容易被高估的收穫。")
    assert len(misses) / total < 0.12
    return misses


def main():
    scorecard()
    baseline_detail()
    conflicts()
    the_bill()
    print()
    print("=" * 70)
    print("  報告一個命中率而不報告基準線，就是在誤導自己。")
    print("  這一章唯一真正站得住的證據，是【衝突】那張表。")
    print("=" * 70)


if __name__ == "__main__":
    main()
