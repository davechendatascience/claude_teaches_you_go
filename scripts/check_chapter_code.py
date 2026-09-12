#!/usr/bin/env python
"""執行章節裡的每一個 python 程式碼區塊。

寫作規範 §5 要求每個區塊：
  1. 自足（所有名字都在區塊內綁定，import 在最上面）
  2. 印出東西
  3. assert 一個預期值

這支腳本把每個區塊抽出來，在乾淨的命名空間裡跑一遍。任何例外、
沒有 print、或沒有 assert，都算失敗。

用法：
    python scripts/check_chapter_code.py
    python scripts/check_chapter_code.py chapters/ch02_connectivity.md
"""

import io
import re
import sys
import traceback
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BLOCK = re.compile(r"```python\n(.*?)\n```", re.S)


def check_file(path, verbose=False):
    text = Path(path).read_text(encoding="utf-8")
    problems = []
    blocks = BLOCK.findall(text)
    for i, code in enumerate(blocks, 1):
        if "print(" not in code:
            problems.append(f"  區塊 {i}：沒有 print()")
        if "assert " not in code:
            problems.append(f"  區塊 {i}：沒有 assert")
        buf = io.StringIO()
        ns = {"__name__": "__main__"}
        try:
            with redirect_stdout(buf):
                exec(compile(code, f"{Path(path).name}#block{i}", "exec"), ns)
        except Exception:
            problems.append(f"  區塊 {i}：執行失敗\n"
                            + "".join("      " + ln for ln in
                                      traceback.format_exc().splitlines(True)[-6:]))
        if verbose:
            print(f"--- {Path(path).name} 區塊 {i} ---")
            print(buf.getvalue())
    return len(blocks), problems


def main(argv):
    verbose = "-v" in argv
    args = [a for a in argv if not a.startswith("-")]
    targets = [Path(a) for a in args] or sorted((ROOT / "chapters").glob("*.md"))
    bad = 0
    for t in targets:
        if not t.exists():
            print(f"[skip] {t} 不存在")
            continue
        n, problems = check_file(t, verbose)
        if problems:
            bad += 1
            print(f"[FAIL] {t.name}（{n} 個區塊）")
            for p in problems:
                print(p)
        else:
            print(f"[ ok ] {t.name}（{n} 個區塊全部通過）")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
