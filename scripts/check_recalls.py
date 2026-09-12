#!/usr/bin/env python
"""驗證全書的交叉引用：每一個「第 N 章 §x.y」與「定理 N.M」都真的存在。

寫作規範 §3 說：「**絕不 RECALL 從未教過的東西。**」這支腳本把那句話
變成可執行的檢查。它做四件事：

  1. 掃描每一章，建立【索引】：有哪些節（## 4.、### 4.3）、
     宣告了哪些具名結果（定理 2.11、命題 12.3、定義 14.1 ...）。
  2. 掃描每一處【跨章引用】「第 N 章 §x.y」，確認那一章與那一節都存在。
  3. 掃描每一處【同章引用】「§x.y」，確認本章真的有那一節。
  4. 掃描每一處【具名結果引用】「定理 9.5」，確認它被宣告過，
     而且編號的章號和它所在的章對得上。

第 4 項抓過一個真實的錯誤類型：把「第 12 章命題 12.3」寫成「命題 12.2」。
那種錯讀者查不到，只會以為自己找錯地方。

用法：
    python scripts/check_recalls.py            # 全書
    python scripts/check_recalls.py -v         # 連索引一起印出來
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 具名結果的種類。順序不重要，但要涵蓋全書用過的每一種。
KINDS = ["定理", "命題", "定義", "推論", "規則", "觀察", "演算法", "引理"]
KIND_RE = "|".join(KINDS)

# 一章的檔名 -> 章號
CH_RE = re.compile(r"^ch(\d+)_")

# 宣告：出現在標題或粗體裡，例如「**定理 2.11（反射版）**」「定義 9.1」
DECL_RE = re.compile(rf"(?:{KIND_RE})\s*(\d+)\.(\d+[a-z]?)")

# 跨章引用：「第 10 章 §4.2」「第 12 章 §4.6」（章與 § 之間可有全形空白或無空白）
XREF_RE = re.compile(r"第\s*(\d+)\s*章[^\S\n]*§\s*(\d+(?:\.\d+)*)")

# 同章引用：「§4.3」，但不能是上面那個跨章引用的一部分
SELFREF_RE = re.compile(r"(?<!章)(?<!章 )§\s*(\d+(?:\.\d+)*)")

# 純粹的章引用：「第 13 章」
CHREF_RE = re.compile(r"第\s*(\d+)\s*章")

MAX_CH = 14


def index_chapter(path):
    """回傳 (章號, 節集合, 宣告的具名結果集合)。"""
    text = path.read_text(encoding="utf-8")
    m = CH_RE.match(path.name)
    ch = int(m.group(1)) if m else None

    sections = set()
    for line in text.splitlines():
        h = re.match(r"^##\s+(\d+)\.\s", line)
        if h:
            sections.add(h.group(1))
            continue
        h = re.match(r"^#{3,4}\s+(\d+(?:\.\d+)+)\s", line)
        if h:
            sections.add(h.group(1))
            # 「§4.5.1」這種三層的，也要讓「§4.5」算數
            parts = h.group(1).split(".")
            for i in range(1, len(parts) + 1):
                sections.add(".".join(parts[:i]))

    # 宣告只認「粗體裡的」或「標題裡的」—— 正文中間提到的算引用不算宣告
    decls = set()
    for m2 in re.finditer(rf"\*\*\s*({KIND_RE})\s*(\d+)\.(\d+[a-z]?)", text):
        # 第 9 章的 RECALL 也會寫 **定理 2.11**，那是【引用】不是宣告。
        # 唯一可靠的判準：宣告的編號章號等於它所在的章。
        if int(m2.group(2)) == ch:
            decls.add((m2.group(1), int(m2.group(2)), m2.group(3)))
    for line in text.splitlines():
        if line.startswith("#"):
            for m2 in DECL_RE.finditer(line):
                for k in KINDS:
                    if k in line:
                        decls.add((k, int(m2.group(1)), m2.group(2)))
    return ch, sections, decls


def build_index(paths, verbose=False):
    sections = {}
    decls = defaultdict(set)          # 章號 -> {(種類, 章, 編號)}
    for p in paths:
        ch, sec, dec = index_chapter(p)
        if ch is None:
            continue
        sections[ch] = sec
        for d in dec:
            decls[ch].add(d)
        if verbose:
            print(f"  第 {ch:>2} 章：{len(sec)} 個節、{len(dec)} 個具名結果")
    return sections, decls


def check(path, sections, decls):
    text = path.read_text(encoding="utf-8")
    ch, _s, _d = index_chapter(path)
    problems = []
    n_xref = n_self = n_named = 0

    # 為了不把跨章引用重複算成同章引用，先把它們挖掉
    stripped = XREF_RE.sub(" ", text)

    for m in XREF_RE.finditer(text):
        n_xref += 1
        tgt, sec = int(m.group(1)), m.group(2)
        if not 1 <= tgt <= MAX_CH:
            problems.append(f"引用了不存在的第 {tgt} 章（§{sec}）")
        elif tgt not in sections:
            problems.append(f"第 {tgt} 章還沒寫，卻被引用（§{sec}）")
        elif sec not in sections[tgt]:
            problems.append(f"第 {tgt} 章沒有 §{sec}")

    for m in SELFREF_RE.finditer(stripped):
        n_self += 1
        sec = m.group(1)
        if ch in sections and sec not in sections[ch]:
            problems.append(f"本章沒有 §{sec}")

    for m in CHREF_RE.finditer(text):
        tgt = int(m.group(1))
        if not 1 <= tgt <= MAX_CH:
            problems.append(f"引用了不存在的第 {tgt} 章")

    # 具名結果：編號的章號要對得上，而且要真的被宣告過
    all_decls = {(k, c, n) for s in decls.values() for (k, c, n) in s}
    for m in re.finditer(rf"({KIND_RE})\s*(\d+)\.(\d+[a-z]?)", text):
        kind, c, n = m.group(1), int(m.group(2)), m.group(3)
        n_named += 1
        if not 1 <= c <= MAX_CH:
            problems.append(f"{kind} {c}.{n} 的章號不存在")
        elif (kind, c, n) not in all_decls:
            problems.append(f"{kind} {c}.{n} 從來沒有被宣告過")

    return problems, (n_xref, n_self, n_named)


def main(argv):
    verbose = "-v" in argv
    args = [a for a in argv if not a.startswith("-")]
    chapters = sorted((ROOT / "chapters").glob("ch*.md"))
    sections, decls = build_index(chapters, verbose)

    targets = [Path(a) for a in args] or chapters
    bad = 0
    for t in targets:
        problems, (nx, ns, nn) = check(t, sections, decls)
        # 同一個問題可能出現很多次，只報一次並附次數
        counted = {}
        for p in problems:
            counted[p] = counted.get(p, 0) + 1
        if counted:
            bad += 1
            print(f"[FAIL] {t.name}")
            for p, c in sorted(counted.items(), key=lambda kv: -kv[1]):
                print(f"    {p}" + (f"（{c} 次）" if c > 1 else ""))
        else:
            print(f"[ ok ] {t.name}"
                  f"（跨章 {nx}、同章 {ns}、具名結果 {nn}）")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
