#!/usr/bin/env python
"""產生第 11 章用到的 figures/*.txt。（跑完約需半分鐘）

兩張表，都是算出來的：
  * ch11_ledger      同樣四顆子的四種順序，每一手的失分與總帳
  * ch11_dictionary  一本【完美擬合】的定石辭典：看得越多，要記的越多
"""

import itertools
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.setrecursionlimit(100000)
sys.path.insert(0, str(ROOT))

from go_core.board import BLACK, WHITE, Board, opposite                # noqa: E402
from go_core.minimax import Solver                                     # noqa: E402
from go_core.tewari import (_board_from_key, reachable_states,          # noqa: E402
                            solve_all)

OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)

N = 3
SOLVER = Solver(komi=0.0, max_ply=15)
BLACK_STONES = ["B2", "A1"]
WHITE_STONES = ["B3", "C2"]


def _v(board, colour, ko=None):
    return SOLVER.search(board, colour, ko=ko)[0]


def _walk(seq):
    b, ko, steps = Board(N), None, []
    for colour, coord in seq:
        before = _v(b, colour, ko)
        t = b.copy()
        taken = t.play(colour, coord)
        assert not taken, "手割的前提是無提子"
        after = _v(t, opposite(colour))
        loss = (before - after) if colour == BLACK else (after - before)
        steps.append((colour, coord, loss))
        b, ko = t, None
    return steps, b


def ledger():
    rows, finals, diffs = [], set(), set()
    for bo in itertools.permutations(BLACK_STONES):
        for wo in itertools.permutations(WHITE_STONES):
            seq = [(BLACK, bo[0]), (WHITE, wo[0]),
                   (BLACK, bo[1]), (WHITE, wo[1])]
            steps, final = _walk(seq)
            lb = sum(l for c, _, l in steps if c == BLACK)
            lw = sum(l for c, _, l in steps if c == WHITE)
            rows.append((seq, steps, lb, lw))
            finals.add(final.grid.tobytes())
            diffs.add(lb - lw)
    assert len(finals) == 1 and len(diffs) == 1

    out = [f"  {'順序':<24}{'每一手的失分':<26}{'黑':>5}{'白':>5}{'黑-白':>7}"]
    out.append("  " + "-" * 65)
    for seq, steps, lb, lw in rows:
        order = " ".join(f"{'黑' if c == BLACK else '白'}{p}" for c, p in seq)
        detail = " ".join(f"{p}{l:+.0f}" for _, p, l in steps)
        out.append(f"  {order:<24}{detail:<26}{lb:>5.0f}{lw:>5.0f}{lb - lw:>+7.0f}")
    out.append("")
    out.append(f"  四種順序的終局盤面：{len(finals)} 種")
    out.append(f"  四種順序的（黑失分 - 白失分）：{sorted(diffs)[0]:+.0f}，四種完全相同")
    return "\n".join(out)


WINDOWS = [
    ("下面一列 (3 點)", [(2, 0), (2, 1), (2, 2)]),
    ("左下角 (4 點)", [(1, 0), (1, 1), (2, 0), (2, 1)]),
    ("下面兩列 (6 點)", [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)]),
    ("整個棋盤 (9 點)", [(r, c) for r in range(3) for c in range(3)]),
]


def dictionary():
    states = reachable_states(N, 4)
    table, _ = solve_all(states, n=N, solver=SOLVER)
    out = [f"  {'記憶者看得到':<20}{'要記幾條':>10}{'命中率':>10}"]
    out.append("  " + "-" * 40)
    for name, win in WINDOWS:
        winset = set(win)
        groups = defaultdict(list)
        for key, (best, _vals) in table.items():
            board, colour, _ko = _board_from_key(key, N)
            gk = (tuple(int(board.grid[p]) for p in win), colour)
            groups[gk].append((key, best))
        hits = total = 0
        for members in groups.values():
            counter = Counter()
            for _key, best in members:
                inside = [p for p in best if p in winset]
                if inside:
                    for p in inside:
                        counter[p] += 1
                else:
                    counter[None] += 1
            memorised = counter.most_common(1)[0][0]
            for _key, best in members:
                total += 1
                inside = {p for p in best if p in winset}
                hits += (not inside) if memorised is None else (memorised in best)
        out.append(f"  {name:<20}{len(groups):>10}{hits / total:>10.1%}")
    out.append("")
    out.append("  （辭典直接用同一批資料擬合 —— 這是對背譜最寬容的設定）")
    return "\n".join(out)


FIGURES = {
    "ch11_ledger": ledger,
    "ch11_dictionary": dictionary,
}


def main():
    for name, fn in FIGURES.items():
        (OUT / f"{name}.txt").write_text(fn().rstrip("\n") + "\n",
                                         encoding="utf-8", newline="\n")
        print(f"  寫出 {name}.txt")


if __name__ == "__main__":
    main()
