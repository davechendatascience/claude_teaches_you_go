#!/usr/bin/env python
"""把 chapters/*.md 排成一本 PDF。

    python scripts/build_pdf.py                 # 全書 -> build/claude_teaches_go.pdf
    python scripts/build_pdf.py --chapters 1 2  # 只排第 1、2 章（改版式時用）
    python scripts/build_pdf.py --html          # 另外輸出一個單檔 HTML
    python scripts/build_pdf.py --keep-tex      # 保留中間的 .tex，好對 LaTeX 錯誤

需要 pandoc 與 xelatex（MiKTeX／TeX Live 皆可）。

--------------------------------------------------------------------
為什麼需要一個前處理，不能直接餵給 pandoc？
--------------------------------------------------------------------
這本書用了四樣 pandoc 不認識的東西：

1. **徽章方塊** `> [!EUREKA]`。那是 GitHub 的語法，pandoc 會原樣印出
   「[!EUREKA]」五個字元。這裡把它們換成 tcolorbox 環境。
2. **`<details>` 摺疊解答**。在紙上沒有「摺疊」，但解答還是要能讀，
   所以換成一個有底色的「解答」方塊。
3. **Mermaid 流程圖**。pandoc 不會畫。有 mmdc 就叫它畫成 PDF 插進來，
   沒有就印一行說明 —— 每一章的 §1 都另外有一張 ASCII 概念圖講同一件事。
4. **看不見的寬度問題**。棋圖與圖表是用「中文字剛好等於兩個半形字」
   排出來的，所以等寬字型必須是雙寬的 CJK 字型（MS Gothic）。
   而製表符號（U+2500 那一族）在那種字型裡是全形，會把 ASCII 概念圖
   撐歪 —— 所以概念圖裡的製表符號要換回 ASCII。
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"

# ------------------------------------------------------------------ 徽章
BADGES = {
    "EUREKA": ("eureka", "掙得的頓悟"),
    "RECALL": ("recall", "回頭掛勾"),
    "INTUITION": ("intuition", "一個角度"),
    "BOARD REALITY": ("boardreality", "棋盤現實檢查"),
    "PROVERB": ("proverb", "古諺與它的公式"),
    "WARNING": ("warnbox", "注意"),
    "IMPORTANT": ("importantbox", "重要"),
}

# 製表符號在雙寬 CJK 等寬字型裡是全形，會把 ASCII 概念圖撐歪。
# 棋圖本身不含這些字元，所以這個替換只會動到概念圖。
BOX_DRAWING = {
    "─": "-", "│": "|", "┌": "+", "┐": "+", "└": "+", "┘": "+",
    "├": "+", "┤": "+", "┬": "+", "┴": "+", "┼": "+",
    "►": ">", "◄": "<", "▼": "v", "▲": "^",
}

# XeLaTeX 下容易缺字的符號，換成 LaTeX 畫得出來的東西
GLYPHS = {
    "🟢": r"\honestG{}", "🟡": r"\honestY{}", "🔴": r"\honestR{}",
    "✓": r"\checkmarkbox{}", "✅": r"\checkmarkbox{}",
    "✗": r"\xmarkbox{}", "❌": r"\xmarkbox{}",
    "∎": r"$\blacksquare$", "√": r"$\surd$",
    "①": "(1)", "②": "(2)", "③": "(3)", "④": "(4)",
}

HEADER = r"""
\usepackage{xeCJK}
\usepackage{amsmath,amssymb}
\usepackage[most]{tcolorbox}
\usepackage{fancyhdr}
\usepackage{longtable,booktabs,array}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{needspace}

% --- 字型 -----------------------------------------------------------
% 內文用 Noto Serif TC；等寬一定要用雙寬的 CJK 字型，否則棋圖與圖表
% （它們是用「一個中文字 = 兩個半形字」排出來的）會全部歪掉。
\setCJKmainfont{Noto Serif TC}
\setCJKsansfont{Noto Sans TC}
\setCJKmonofont{MS Gothic}
\setmainfont{Noto Serif TC}
\setmonofont{MS Gothic}[Scale=0.92]
\XeTeXlinebreaklocale "zh"
\XeTeXlinebreakskip = 0pt plus 1pt
\punctstyle{kaiming}

% --- 誠實標記 -------------------------------------------------------
\newcommand{\honestG}{\textcolor[HTML]{16A34A}{$\bullet$}}
\newcommand{\honestY}{\textcolor[HTML]{CA8A04}{$\bullet$}}
\newcommand{\honestR}{\textcolor[HTML]{DC2626}{$\bullet$}}
\newcommand{\checkmarkbox}{\textcolor[HTML]{16A34A}{\checkmark}}
\newcommand{\xmarkbox}{\textcolor[HTML]{DC2626}{$\times$}}

% --- 徽章方塊 -------------------------------------------------------
\tcbset{badgebase/.style={
  breakable, enhanced, boxrule=0pt, leftrule=3pt, arc=1pt,
  left=8pt, right=8pt, top=6pt, bottom=6pt,
  fonttitle=\bfseries\sffamily\small,
  attach boxed title to top left={xshift=6pt, yshift=-3pt},
  boxed title style={boxrule=0pt, arc=1pt, left=4pt, right=4pt},
}}
\newtcolorbox{eureka}{badgebase, colback=[HTML]{FFFBEB},
  colframe=[HTML]{D97706}, coltitle=white,
  colbacktitle=[HTML]{D97706}, title={掙得的頓悟}}
\newtcolorbox{recall}{badgebase, colback=[HTML]{F0F9FF},
  colframe=[HTML]{0284C7}, coltitle=white,
  colbacktitle=[HTML]{0284C7}, title={回頭掛勾}}
\newtcolorbox{intuition}{badgebase, colback=[HTML]{F5F3FF},
  colframe=[HTML]{7C3AED}, coltitle=white,
  colbacktitle=[HTML]{7C3AED}, title={一個角度}}
\newtcolorbox{boardreality}{badgebase, colback=[HTML]{FEF2F2},
  colframe=[HTML]{DC2626}, coltitle=white,
  colbacktitle=[HTML]{DC2626}, title={棋盤現實檢查}}
\newtcolorbox{proverb}{badgebase, colback=[HTML]{F0FDF4},
  colframe=[HTML]{16A34A}, coltitle=white,
  colbacktitle=[HTML]{16A34A}, title={古諺與它的公式}}
\newtcolorbox{warnbox}{badgebase, colback=[HTML]{FFF7ED},
  colframe=[HTML]{EA580C}, coltitle=white,
  colbacktitle=[HTML]{EA580C}, title={注意}}
\newtcolorbox{importantbox}{badgebase, colback=[HTML]{F8FAFC},
  colframe=[HTML]{475569}, coltitle=white,
  colbacktitle=[HTML]{475569}, title={重要}}
\newtcolorbox{solutionbox}{badgebase, colback=[HTML]{FAFAF9},
  colframe=[HTML]{78716C}, coltitle=white,
  colbacktitle=[HTML]{78716C}, title={解答}}

% --- 棋圖：不要斷頁，而且要壓縮行距 ---------------------------------
\newenvironment{gobandiagram}
  {\par\needspace{6\baselineskip}\begingroup
   \setlength{\parskip}{0pt}\linespread{0.92}\selectfont\small}
  {\endgroup\par}

% --- 版面 -----------------------------------------------------------
\linespread{1.22}
\setlength{\parskip}{0.55em}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[LE,RO]{\small\thepage}
\fancyhead[RE]{\small\nouppercase\leftmark}
\fancyhead[LO]{\small\nouppercase\rightmark}
\renewcommand{\headrulewidth}{0.4pt}
"""


# ------------------------------------------------------------------ 前處理
def strip_comments(text):
    return re.sub(r"<!--.*?-->\n?", "", text, flags=re.S)


def convert_badges(text):
    """> [!EUREKA] 區塊 -> \\begin{eureka} ... \\end{eureka}"""
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        m = re.match(r"^>\s*\[!([A-Z ]+)\]\s*$", lines[i])
        if not m or m.group(1) not in BADGES:
            out.append(lines[i])
            i += 1
            continue
        env = BADGES[m.group(1)][0]
        i += 1
        body = []
        while i < len(lines) and lines[i].startswith(">"):
            body.append(re.sub(r"^>\s?", "", lines[i]))
            i += 1
        out += ["", rf"\begin{{{env}}}", ""] + body + ["", rf"\end{{{env}}}", ""]
    return "\n".join(out)


def convert_details(text):
    """<details><summary>解答</summary> ... </details> -> 解答方塊"""
    text = re.sub(
        r"<details>\s*\n<summary>.*?</summary>\s*\n",
        "\n\\\\begin{solutionbox}\n\n", text, flags=re.S)
    return text.replace("</details>", "\n\\end{solutionbox}\n")


def fix_code_blocks(text, mermaid_dir=None):
    """text 區塊：概念圖換掉製表符號；mermaid：能畫就畫，不能就說明。"""
    def one(m):
        lang, body = m.group(1), m.group(2)
        if lang == "mermaid":
            img = render_mermaid(body, mermaid_dir)
            if img:
                return (r"\begin{center}\includegraphics[width=0.92\linewidth,"
                        rf"height=0.34\textheight,keepaspectratio]{{{img}}}"
                        r"\end{center}")
            return ("\\begin{center}\\small\\itshape\n"
                    "（此處原為一張 Mermaid 概念流程圖；紙本版省略，"
                    "同一節的 ASCII 概念圖講的是同一件事。）\n"
                    "\\end{center}")
        if lang == "text":
            for a, b in BOX_DRAWING.items():
                body = body.replace(a, b)
            return ("\\begin{gobandiagram}\n```text\n" + body
                    + "\n```\n\\end{gobandiagram}")
        return m.group(0)

    return re.sub(r"```(\w*)\n(.*?)\n```", one, text, flags=re.S)


def render_mermaid(source, out_dir):
    """有 mmdc 就把 mermaid 畫成 PDF。沒有就回傳 None。"""
    if out_dir is None or not shutil.which("mmdc"):
        return None
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    idx = len(list(out_dir.glob("mermaid_*.pdf")))
    src = out_dir / f"mermaid_{idx}.mmd"
    dst = out_dir / f"mermaid_{idx}.pdf"
    src.write_text(source, encoding="utf-8")
    try:
        subprocess.run(["mmdc", "-i", str(src), "-o", str(dst), "-b", "white"],
                       check=True, capture_output=True, timeout=120)
    except Exception:
        return None
    return dst.as_posix() if dst.exists() else None


def replace_glyphs(text):
    """把 XeLaTeX 容易缺字的符號換成 LaTeX 畫得出來的東西（程式碼區塊除外）。"""
    parts = re.split(r"(```.*?```)", text, flags=re.S)
    for i, part in enumerate(parts):
        if part.startswith("```"):
            continue
        for a, b in GLYPHS.items():
            part = part.replace(a, b)
        parts[i] = part
    return "".join(parts)


def preprocess(text, mermaid_dir=None):
    text = fix_code_blocks(text, mermaid_dir)   # 先做，才看得到 ``` 邊界
    text = strip_comments(text)
    text = convert_details(text)
    text = convert_badges(text)
    text = replace_glyphs(text)
    # 章末的 --- 分隔線在書裡是多餘的（每章本來就換頁）
    text = re.sub(r"\n---\n", "\n\n", text)
    return text


# ------------------------------------------------------------------ 主流程
def collect(chapters):
    files = sorted((ROOT / "chapters").glob("ch*.md"))
    if chapters:
        want = {f"{int(c):02d}" for c in chapters}
        files = [f for f in files if f.name[2:4] in want]
    files += sorted((ROOT / "chapters").glob("app*.md"))
    return files


def build(chapters=None, keep_tex=False, html=False):
    if not shutil.which("pandoc"):
        sys.exit("找不到 pandoc。請先安裝：https://pandoc.org/installing.html")

    BUILD.mkdir(exist_ok=True)
    files = collect(chapters)
    if not files:
        sys.exit("chapters/ 底下沒有東西可以排。")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pieces = []
        for f in files:
            print(f"  前處理 {f.name}")
            pieces.append(preprocess(f.read_text(encoding="utf-8"), tmp))
        body = "\n\n\\clearpage\n\n".join(pieces)

        md = tmp / "book.md"
        md.write_text(body, encoding="utf-8", newline="\n")
        hdr = tmp / "header.tex"
        hdr.write_text(HEADER, encoding="utf-8", newline="\n")

        common = [
            "pandoc", str(md),
            "--from", "markdown+raw_tex+tex_math_dollars+pipe_tables"
                      "+backtick_code_blocks+fenced_code_attributes",
            "--toc", "--toc-depth=2",
            "--metadata", "title=Claude 教你圍棋",
            "--metadata", "subtitle=圍棋的五層骨架 —— 從一顆棋子的氣，到 AI 眼中的勝率",
            "--metadata", "author=Claude",
            "--metadata", "lang=zh-Hant",
        ]

        out = BUILD / "claude_teaches_go.pdf"
        cmd = common + [
            "--pdf-engine=xelatex",
            "--include-in-header", str(hdr),
            "--top-level-division=chapter",
            "-V", "documentclass=book",
            "-V", "classoption=11pt,openany",
            "-V", "geometry:paperwidth=18cm,paperheight=25cm,"
                  "top=2.2cm,bottom=2.2cm,inner=2.4cm,outer=1.8cm",
            "-V", "colorlinks=true", "-V", "linkcolor=[HTML]{0F766E}",
            "-V", "toccolor=black",
            "-o", str(out),
        ]
        print(f"\n  跑 pandoc + xelatex（{len(files)} 章）...")
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if keep_tex or r.returncode:
            tex = BUILD / "claude_teaches_go.tex"
            subprocess.run(cmd[:-2] + ["-s", "-o", str(tex)],
                           capture_output=True)
            print(f"  中間檔：{tex}")
        if r.returncode:
            print(r.stdout[-4000:])
            print(r.stderr[-6000:])
            sys.exit("xelatex 失敗（上面是最後幾行）")
        print(f"  [ok] {out}  （{out.stat().st_size / 1e6:.1f} MB）")

        if html:
            hout = BUILD / "claude_teaches_go.html"
            subprocess.run(common + ["--standalone", "--embed-resources",
                                     "--mathml", "-o", str(hout)],
                           check=True)
            print(f"  [ok] {hout}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="把這本書排成 PDF")
    ap.add_argument("--chapters", nargs="*", help="只排這幾章（章號）")
    ap.add_argument("--keep-tex", action="store_true", help="保留中間的 .tex")
    ap.add_argument("--html", action="store_true", help="另外輸出單檔 HTML")
    a = ap.parse_args()
    return build(a.chapters, a.keep_tex, a.html)


if __name__ == "__main__":
    raise SystemExit(main())
