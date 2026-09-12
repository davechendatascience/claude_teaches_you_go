#!/usr/bin/env python
"""把章節裡的棋圖與圖表，從 positions/*.sgf 與 figures/*.txt 重新產生一次。

`check_diagrams.py` 與 `check_figures.py` 只會**告訴你**不一致；這一支負責
**改回來**。典型用法是改完 `make_positions_chNN.py` 之後：

    python scripts/make_positions_ch04.py     # 重新產生 SGF
    python scripts/sync_diagrams.py chapters/ch04_capture_races.md
    python scripts/check_diagrams.py chapters/ch04_capture_races.md

棋圖連同下面那一行斜體說明一起換掉（說明存在 SGF 的 C[] 裡）。
如果某張圖底下的說明是章節自己寫的、不在 SGF 裡，就只換棋圖本身。

用法：
    python scripts/sync_diagrams.py                  # 全部章節
    python scripts/sync_diagrams.py chapters/ch04_capture_races.md
    python scripts/sync_diagrams.py --dry-run        # 只印出會改什麼
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from go_core.render import render_ascii   # noqa: E402
from go_core.sgf import load_sgf          # noqa: E402

DIAGRAM = re.compile(
    r"(<!--\s*diagram:\s*([A-Za-z0-9_]+)\s*-->\s*\n```text\n)(.*?)(\n```\n)(\*.*?\*\n)?",
    re.S,
)
FIGURE = re.compile(
    r"(<!--\s*figure:\s*([A-Za-z0-9_]+)\s*-->\s*\n```text\n)(.*?)(\n```)",
    re.S,
)


def sync(path, dry_run=False):
    text = path.read_text(encoding="utf-8")
    changed = []

    def do_diagram(m):
        head, name, body, tail, caption = m.groups()
        sgf = ROOT / "positions" / f"{name}.sgf"
        if not sgf.exists():
            return m.group(0)
        board, numbers, labels, marks, comment = load_sgf(str(sgf))
        art = render_ascii(board, numbers=numbers, labels=labels, marks=marks)
        new_caption = f"*{comment}*\n" if comment else caption
        if body != art or (caption or "") != (new_caption or ""):
            changed.append(name)
        return head + art + tail + (new_caption or "")

    def do_figure(m):
        head, name, body, tail = m.groups()
        txt = ROOT / "figures" / f"{name}.txt"
        if not txt.exists():
            return m.group(0)
        art = txt.read_text(encoding="utf-8").rstrip("\n")
        if body != art:
            changed.append(name)
        return head + art + tail

    out = DIAGRAM.sub(do_diagram, text)
    out = FIGURE.sub(do_figure, out)

    if changed and not dry_run:
        path.write_text(out, encoding="utf-8", newline="\n")
    return changed


def main(argv):
    dry = "--dry-run" in argv
    args = [a for a in argv if not a.startswith("-")]
    targets = [Path(a) for a in args] or sorted((ROOT / "chapters").glob("*.md"))
    total = 0
    for t in targets:
        changed = sync(t, dry)
        total += len(changed)
        verb = "會改" if dry else "已更新"
        if changed:
            print(f"[{verb}] {t.name}：{'、'.join(changed)}")
        else:
            print(f"[ ok ] {t.name}")
    print(f"\n{'會更新' if dry else '共更新'} {total} 張。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
