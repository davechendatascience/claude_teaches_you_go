#!/usr/bin/env python
"""章節文字的自動檢查：結構、徽章、字數、禁用詞、混入的雜字元。

這支腳本檢查 docs/03_writing_brief.md §7 交稿清單裡「機器可以查」的那幾條。
另外加了一項在寫第 5 章時吃過虧的檢查：**混入的非預期字元** ——
那一次正文裡莫名其妙出現了一個俄文詞，肉眼完全看不出來。

用法：
    python scripts/check_prose.py                       # 檢查全部章節
    python scripts/check_prose.py chapters/ch05_ko.md
    python scripts/check_prose.py -v                    # 連通過的項目也列出來
"""

import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

H2_EXPECTED = [
    "0. 我們在哪裡",
    "1. 開場思想實驗與掙得的頓悟",
    "2. 多角度直觀",
    "3. 散落的碎片（問題本身）",
    "4. 對齊（解答）",
    "5. 應用：手算追蹤與非黑盒程式",
    "6. 練習與完整解答",
    "7. 本章頓悟總結",
]

BANNED = ["顯然", "不難看出", "容易證明", "眾所周知", "憑感覺",
          "棋感告訴", "多下就懂", "自然地", "不言而喻"]

BADGE_MIN = {"EUREKA": 1, "RECALL": 6, "INTUITION": 3,
             "BOARD REALITY": 2, "PROVERB": 2}
BADGE_MAX = {"EUREKA": 1}

# 允許出現的文字系統。日文假名是刻意允許的（術語的日文原文）。
ALLOWED_SCRIPTS = ("CJK", "LATIN", "DIGIT", "HIRAGANA", "KATAKANA", "GREEK")


def script_of(ch):
    """粗略判斷一個字元屬於哪個文字系統。"""
    o = ord(ch)
    if ch.isascii():
        return "LATIN" if ch.isalpha() else ("DIGIT" if ch.isdigit() else None)
    if 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF:
        return "CJK"
    if 0x3040 <= o <= 0x309F:
        return "HIRAGANA"
    if 0x30A0 <= o <= 0x30FF:
        return "KATAKANA"
    if 0x0370 <= o <= 0x03FF:
        return "GREEK"
    if 0x0400 <= o <= 0x04FF:
        return "CYRILLIC"
    if 0xAC00 <= o <= 0xD7AF:
        return "HANGUL"
    if 0x0590 <= o <= 0x08FF:
        return "RTL"
    if unicodedata.category(ch) in ("Zs", "Po", "Pd", "Ps", "Pe", "Pi", "Pf",
                                    "Sm", "Sk", "So", "Cf", "Mn", "Nd", "Ll",
                                    "Lu", "Pc"):
        return None                       # 標點、符號、空白 —— 不管
    return None


def check(path, verbose=False):
    text = Path(path).read_text(encoding="utf-8")
    name = Path(path).name
    problems, notes = [], []
    is_chapter = Path(path).parent.name == "chapters"

    if not is_chapter:
        # docs/ 底下的檔案只查「機械性」的問題：雜字元與 tab。
        # 這兩種都是反斜線跳脫被誤解造成的，而且肉眼看不出來。
        stray = {}
        for ch in text:
            s = script_of(ch)
            if s and s not in ALLOWED_SCRIPTS:
                stray.setdefault(s, set()).add(ch)
        for s, chars in stray.items():
            problems.append(f"混入 {s} 字元：{''.join(sorted(chars))}")
        if "\t" in text:
            n = sum(1 for l in text.split("\n") if "\t" in l)
            problems.append(f"{n} 行含有 tab 字元（很可能是 LaTeX 的反斜線被吃掉）")
        notes.append(f"{len(text)} 字元")
        return problems, notes

    # --- 結構 -------------------------------------------------------
    h2 = re.findall(r"^## (.*)$", text, re.M)
    if len(h2) != 8:
        problems.append(f"H2 標題應有 8 個，實際 {len(h2)} 個")
    else:
        for got, want in zip(h2, H2_EXPECTED):
            if not got.startswith(want.split("：")[0]):
                problems.append(f"H2 順序或文字不符：期待「{want}」，得到「{got}」")

    # --- 字數 -------------------------------------------------------
    cjk = len(re.findall(r"[一-鿿]", text))
    lo, hi = (4000, 6000) if "app" in name else (8000, 12000)
    notes.append(f"中文字數 {cjk}")
    if cjk < lo:
        problems.append(f"中文字數 {cjk} 低於下限 {lo}")
    elif cjk > hi * 1.25:
        problems.append(f"中文字數 {cjk} 遠超過上限 {hi}，該拆或該刪")
    elif cjk > hi:
        notes.append(f"（略超過 {hi} 的目標，可接受）")

    # --- 徽章 -------------------------------------------------------
    for badge, lo_n in BADGE_MIN.items():
        got = text.count(f"[!{badge}]")
        notes.append(f"[!{badge}] x {got}")
        if got < lo_n:
            problems.append(f"[!{badge}] 只有 {got} 個，至少要 {lo_n} 個")
        if badge in BADGE_MAX and got > BADGE_MAX[badge]:
            problems.append(f"[!{badge}] 有 {got} 個，最多 {BADGE_MAX[badge]} 個")

    # PROVERB 必須有失效條件
    for m in re.finditer(r"> \[!PROVERB\]\n((?:> .*\n)+)", text):
        if "失效條件" not in m.group(1):
            head = m.group(1).splitlines()[0][:40]
            problems.append(f"PROVERB 缺少「失效條件」：{head}")

    # --- 禁用詞 -----------------------------------------------------
    for w in BANNED:
        if w in text:
            problems.append(f"禁用詞「{w}」出現 {text.count(w)} 次")

    # --- 混入的雜字元 -----------------------------------------------
    stray = {}
    for ch in text:
        s = script_of(ch)
        if s and s not in ALLOWED_SCRIPTS:
            stray.setdefault(s, set()).add(ch)
    for s, chars in stray.items():
        problems.append(f"混入 {s} 字元：{''.join(sorted(chars))}")

    # --- 其他 -------------------------------------------------------
    if "\t" in text:
        problems.append("含有 tab 字元（很可能是反斜線跳脫被誤解）")
    diagrams = len(re.findall(r"<!-- diagram:", text))
    blocks = len(re.findall(r"```python", text))
    notes.append(f"棋圖 {diagrams} 張、python 區塊 {blocks} 個")
    if diagrams == 0:
        problems.append("一張棋圖都沒有")

    return problems, notes


def main(argv):
    verbose = "-v" in argv
    args = [a for a in argv if not a.startswith("-")]
    targets = [Path(a) for a in args] or sorted((ROOT / "chapters").glob("*.md"))
    bad = 0
    for t in targets:
        problems, notes = check(t, verbose)
        if problems:
            bad += 1
            print(f"[FAIL] {t.name}")
            for p in problems:
                print(f"    {p}")
        else:
            print(f"[ ok ] {t.name}")
        if verbose or problems:
            print(f"       {' | '.join(notes)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
