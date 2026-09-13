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
    #  名稱              框線色     底色      標題
    "EUREKA":        ("B45309", "FFFBEB", "掙得的頓悟"),
    "RECALL":        ("0369A1", "F0F9FF", "回頭掛勾"),
    "INTUITION":     ("6D28D9", "F5F3FF", "一個角度"),
    "BOARD REALITY": ("B91C1C", "FEF2F2", "棋盤現實檢查"),
    "PROVERB":       ("15803D", "F0FDF4", "古諺與它的公式"),
    "WARNING":       ("C2410C", "FFF7ED", "注意"),
    "IMPORTANT":     ("334155", "F1F5F9", "重要"),
}
SOLUTION = ("57534E", "FAFAF9", "解答")


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
\usepackage{amsmath,amssymb}
\usepackage{fancyhdr}
\usepackage{longtable,booktabs,array}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{needspace}
% framed 提供可【跨頁】的框。這裡刻意不用 tcolorbox ——
% 它的 breakable 需要 pdfcol、skins 需要 tikzfill，
% 兩者在精簡安裝的 TeX 上常常沒有，而這本書的方塊不需要那些。
\usepackage{framed}

% --- 字型 -----------------------------------------------------------
% 三件事必須同時成立，中文書才排得出來：
%
% 1. **會斷行。** 沒有 xeCJK 也行：\XeTeXlinebreaklocale 是 XeTeX 自己
%    的原語，有了它中文才會在字與字之間斷行。
% 2. **有真正的粗體。** Windows 內建的 Noto Serif TC 是【可變字型】，
%    XeTeX 只取得到單一實例（實測拿到 ExtraLight），於是整本書偏細、
%    而且 \textbf 完全沒有作用。微軟正黑體有獨立的 Regular 與 Bold 兩個
%    字面，所以這裡優先用它。
% 3. **等寬是雙寬的。** 棋圖與圖表都是用「一個中文字 = 兩個半形字」
%    排出來的，等寬字型必須讓漢字剛好等於兩個半形字（MS Gothic 是）。
%    換成一般等寬字型，每一張棋圖都會歪掉。
%
% 下面依序試，有什麼用什麼 —— 換一台機器也跑得動。
\IfFontExistsTF{Noto Serif CJK TC}{\setmainfont{Noto Serif CJK TC}}{%
  \IfFontExistsTF{Source Han Serif TC}{\setmainfont{Source Han Serif TC}}{%
    \IfFontExistsTF{Microsoft JhengHei}{\setmainfont{Microsoft JhengHei}}{%
      \IfFontExistsTF{PMingLiU}{\setmainfont{PMingLiU}}{}}}}
\IfFontExistsTF{Microsoft JhengHei UI}{\setsansfont{Microsoft JhengHei UI}}{%
  \IfFontExistsTF{Microsoft JhengHei}{\setsansfont{Microsoft JhengHei}}{}}
% 等寬字型的順序：先要【零缺字】，再要【雙寬】。
% MS Gothic 是日文字型，缺「值、啟、夠、稅、說」這些繁體字 ——
% 校對時在 PDF 上看到「四層都口不出理由」才發現。所以它排最後。
\IfFontExistsTF{Sarasa Mono TC}{\setmonofont{Sarasa Mono TC}[Scale=0.92]}{%
  \IfFontExistsTF{MingLiU}{\setmonofont{MingLiU}[Scale=0.98]}{%
    \IfFontExistsTF{Noto Sans Mono CJK TC}{\setmonofont{Noto Sans Mono CJK TC}[Scale=0.90]}{%
      \IfFontExistsTF{NSimSun}{\setmonofont{NSimSun}[Scale=0.94]}{%
        \IfFontExistsTF{MS Gothic}{\setmonofont{MS Gothic}[Scale=0.88]}{}}}}}
\XeTeXlinebreaklocale "zh"
\XeTeXlinebreakskip = 0pt plus 1pt

% pandoc 會載入 unicode-math，而它預設要 latinmodern-math ——
% 不是每台機器都有。Cambria Math 是 Windows 內建的正牌 OpenType
% 數學字型，拿來排這本書的公式綽綽有餘。
\makeatletter
\@ifpackageloaded{unicode-math}{%
  \IfFontExistsTF{Cambria Math}{\setmathfont{Cambria Math}}{}%
}{}
\makeatother

% --- 誠實標記 -------------------------------------------------------
\newcommand{\honestG}{\textcolor[HTML]{15803D}{$\bullet$}}
\newcommand{\honestY}{\textcolor[HTML]{A16207}{$\bullet$}}
\newcommand{\honestR}{\textcolor[HTML]{B91C1C}{$\bullet$}}
\newcommand{\checkmarkbox}{\textcolor[HTML]{15803D}{$\checkmark$}}
\newcommand{\xmarkbox}{\textcolor[HTML]{B91C1C}{$\times$}}

% --- 徽章方塊：一條粗的彩色左框線 + 淡底色 + 一行標題 ----------------
%
% 這裡刻意用【一對巨集】而不是 LaTeX 環境。理由是 pandoc：
% 它看到 \begin{X} 會一路吃到 \end{X}，把中間的東西整段當成 raw LaTeX ——
% 於是方塊裡的 markdown（粗體、清單、公式、程式碼）通通不會被解析。
% 換成 \badgeopen / \badgeclose 兩個獨立的巨集，pandoc 就只把那兩行
% 當成 raw，中間照常當 markdown 處理。
\definecolor{shadecolor}{HTML}{FFFFFF}
\newcommand{\badgeopen}[3]{%   #1 框線色  #2 底色  #3 標題
  \par\smallskip
  \definecolor{shadecolor}{HTML}{#2}%
  \def\FrameCommand{{\color[HTML]{#1}\vrule width 2.6pt}\colorbox{shadecolor}}%
  \MakeFramed{\advance\hsize-\width \FrameRestore}%
  \noindent{\sffamily\bfseries\small\color[HTML]{#1}#3}\par
  \vspace{-0.3\baselineskip}%
}
\newcommand{\badgeclose}{\endMakeFramed\par\smallskip}

% 棋圖與圖表：盡量不要斷頁，並壓縮行距讓一張圖看起來是一塊。
% 圖說也包在同一組裡 —— 中文字型沒有斜體，所以 markdown 的 *斜體*
% 在紙上等於沒有作用；改成「小一級 + 灰一點 + 縮排」。
\newcommand{\gobanopen}{\par\needspace{8\baselineskip}\begingroup
  \setlength{\parskip}{0pt}\linespread{0.95}\selectfont}
\newcommand{\gobancap}{\par\vspace{0.3em}\small\color[HTML]{44403C}%
  \leftskip=1.6em \rightskip=1.6em}
\newcommand{\gobanclose}{\endgroup\par\smallskip}

% --- 標題：這台機器沒有 titlesec，所以直接改 \@startsection ----------
\makeatletter
\renewcommand\section{\@startsection{section}{1}{0pt}%
  {-3.2ex \@plus -1ex \@minus -.2ex}{1.6ex \@plus.2ex}%
  {\normalfont\Large\sffamily\bfseries\color[HTML]{0F172A}}}
\renewcommand\subsection{\@startsection{subsection}{2}{0pt}%
  {-2.6ex \@plus -1ex \@minus -.2ex}{1.1ex \@plus.2ex}%
  {\normalfont\large\sffamily\bfseries\color[HTML]{1E293B}}}
\renewcommand\subsubsection{\@startsection{subsubsection}{3}{0pt}%
  {-2.2ex \@plus -1ex \@minus -.2ex}{0.9ex \@plus.2ex}%
  {\normalfont\normalsize\sffamily\bfseries\color[HTML]{334155}}}
\makeatother

% 引用區塊（定義、定理都用它）：一條可跨頁的淡左框線
\renewenvironment{quote}
  {\par\smallskip
   \def\FrameCommand{{\color[HTML]{CBD5E1}\vrule width 2pt}\hspace{0.9em}}%
   \MakeFramed{\advance\hsize-\width \FrameRestore}}
  {\endMakeFramed\par\smallskip}

% --- 版面 -----------------------------------------------------------
\linespread{1.25}
\setlength{\parskip}{0.5em}
\setlength{\parindent}{0pt}
\setlength{\emergencystretch}{3em}
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
    """> [!EUREKA] 區塊 -> \\badgeopen ... \\badgeclose"""
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        m = re.match(r"^>\s*\[!([A-Z ]+)\]\s*$", lines[i])
        if not m or m.group(1) not in BADGES:
            out.append(lines[i])
            i += 1
            continue
        fg, bg, title = BADGES[m.group(1)]
        i += 1
        body = []
        while i < len(lines) and lines[i].startswith(">"):
            body.append(re.sub(r"^>\s?", "", lines[i]))
            i += 1
        # 方塊的第一行常常是「**角度一：手感／實戰透鏡**」這種整行粗體的
        # 小標。把它併進標題列，免得標題和內文第一行講同一件事。
        while body and not body[0].strip():
            body.pop(0)
        if body:
            m2 = re.fullmatch(r"\*\*(.+?)\*\*", body[0].strip())
            if m2:
                title = f"{title}　·　{m2.group(1)}"
                body.pop(0)
        out += ["", rf"\badgeopen{{{fg}}}{{{bg}}}{{{title}}}", ""]
        out += body
        out += ["", r"\badgeclose", ""]
    return "\n".join(out)


def convert_details(text):
    """<details><summary>解答</summary> ... </details> -> 解答方塊

    紙上沒有「摺疊」，但解答還是要讀得到 —— 換成一個有底色的方塊。
    """
    fg, bg, title = SOLUTION
    opener = f"\n\\badgeopen{{{fg}}}{{{bg}}}{{{title}}}\n\n"
    text = re.sub(r"<details>\s*\n<summary>.*?</summary>\s*\n",
                  opener.replace("\\", "\\\\"), text, flags=re.S)
    return text.replace("</details>", "\n\\badgeclose\n")


def fix_code_blocks(text, mermaid_dir=None):
    """處理三種 ``` 區塊。

    * mermaid：有 mmdc 就畫，沒有就印一行說明。
    * text（棋圖與圖表）：換掉製表符號，並把【緊接在後面的圖說】
      一起包進同一組 —— 中文沒有斜體，所以圖說要另外給樣式。
    * python：原樣保留（pandoc 會排成 verbatim）。
    """
    pat = re.compile(r"```(\w*)\n(.*?)\n```(\n\*(?!\*)(.+?)\*\n)?", re.S)

    def one(m):
        lang, body, _, caption = m.groups()
        if lang == "mermaid":
            img = render_mermaid(body, mermaid_dir)
            if img:
                block = (r"\begin{center}\includegraphics[width=0.92\linewidth,"
                         rf"height=0.34\textheight,keepaspectratio]{{{img}}}"
                         r"\end{center}")
            else:
                block = ("\\begin{center}\\small\\itshape\n"
                         "（此處原為一張 Mermaid 概念流程圖；紙本版省略，"
                         "同一節的 ASCII 概念圖講的是同一件事。）\n"
                         "\\end{center}")
            return "\n" + block + "\n"
        if lang == "text":
            for a, b in BOX_DRAWING.items():
                body = body.replace(a, b)
            out = "\n\\gobanopen\n\n```text\n" + body + "\n```\n"
            if caption:
                out += "\n\\gobancap\n\n" + caption.strip() + "\n"
            out += "\n\\gobanclose\n"
            return out
        return m.group(0)

    return pat.sub(one, text)


def fix_quote_lists(text):
    """引用區塊裡，清單前面要有一行空的「>」，pandoc 才認得出那是清單。

    GitHub 很寬鬆，少那一行照樣畫成清單；CommonMark 不是。
    書裡的定義方塊（> **定義 2.1** ... > * 項目）就踩到這件事 ——
    在 PDF 裡會變成一串literal 的星號。
    """
    lines = text.split("\n")
    out = []
    for i, line in enumerate(lines):
        is_item = re.match(r"^>\s*([*+-]|\d+\.)\s", line)
        if is_item and out:
            prev = out[-1]
            prev_is_item = re.match(r"^>\s*([*+-]|\d+\.)\s", prev)
            prev_blank = prev.strip() in ("", ">")
            prev_is_quote = prev.startswith(">")
            if prev_is_quote and not prev_is_item and not prev_blank:
                out.append(">")
        out.append(line)
    return "\n".join(out)


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
    text = fix_quote_lists(text)
    text = convert_details(text)
    text = convert_badges(text)
    text = replace_glyphs(text)
    # 章末的 --- 分隔線在書裡是多餘的（每章本來就換頁）
    text = re.sub(r"\n---\n", "\n\n", text)
    return text


# ------------------------------------------------------------------ 主流程
def have_sty(name):
    """這個 TeX 安裝有沒有這個套件？"""
    if not shutil.which("kpsewhich"):
        return False
    try:
        r = subprocess.run(["kpsewhich", name], capture_output=True,
                           text=True, timeout=60)
        return bool(r.stdout.strip())
    except Exception:
        return False


# 等寬字型必須滿足兩件事，而兩件都會安靜地壞掉：
#   1. 雙寬（漢字 = 兩個半形字），否則每一張棋圖與圖表都歪掉。
#   2. 蓋得住書裡用到的每一個字。MS Gothic 是日文字型，缺「說」「值」
#      這幾個繁體字 —— 校對時在 PDF 上看到「四層都口不出理由」才發現。
MONO_CANDIDATES = [
    ("Sarasa Mono TC", None),
    ("MingLiU", r"C:\Windows\Fonts\mingliu.ttc"),
    ("Noto Sans Mono CJK TC", None),
    ("NSimSun", r"C:\Windows\Fonts\simsun.ttc"),
    ("MS Gothic", r"C:\Windows\Fonts\msgothic.ttc"),
]


def mono_chars():
    """書裡所有會用等寬字型排的中日文字元（棋圖、圖表）。"""
    out = set()
    for f in sorted((ROOT / "figures").glob("*.txt")):
        out |= {c for c in f.read_text(encoding="utf-8")
                if 0x3000 <= ord(c) <= 0x9FFF}
    for f in sorted((ROOT / "chapters").glob("*.md")):
        t = f.read_text(encoding="utf-8")
        for m in re.finditer(r"```text\n(.*?)\n```", t, re.S):
            out |= {c for c in m.group(1) if 0x3000 <= ord(c) <= 0x9FFF}
    return out


def check_mono_font():
    """報告第一個【裝得到】的候選字型缺不缺字。缺就警告，不擋建置。"""
    try:
        from fontTools.ttLib import TTCollection, TTFont
    except ImportError:
        return
    need = mono_chars()
    for name, path in MONO_CANDIDATES:
        if not path or not os.path.exists(path):
            continue
        cov = set()
        try:
            fonts = TTCollection(path, lazy=True).fonts
        except Exception:
            try:
                fonts = [TTFont(path, lazy=True)]
            except Exception:
                continue
        for ft in fonts:
            try:
                cov |= set(ft.getBestCmap())
            except Exception:
                pass
        missing = sorted(c for c in need if ord(c) not in cov)
        if missing:
            print(f"  [!] 等寬字型 {name} 缺 {len(missing)} 字："
                  f"{''.join(missing[:20])} —— 棋圖裡那些字會變成豆腐")
        else:
            print(f"  等寬字型 {name}：{len(need)} 個中文字全部蓋得住")
        return


def collect(chapters):
    files = sorted((ROOT / "chapters").glob("ch*.md"))
    if chapters:
        want = {f"{int(c):02d}" for c in chapters}
        files = [f for f in files if f.name[2:4] in want]
    files += sorted((ROOT / "chapters").glob("app*.md"))
    return files


# pandoc 的預設 LaTeX 範本會載入幾個「有更好，沒有也活得下去」的套件，
# 而其中有些（bookmark）沒有 \IfFileExists 防護 —— 精簡安裝的 TeX 上
# 直接就是硬錯誤。與其要求讀者去補裝套件（有些機器根本連不了網），
# 不如就地放一個空殼，把那一行變成沒有作用。
#
# 這裡放的每一個空殼都只影響「錦上添花」的功能：
#   footnote  —— 讓 longtable 的表頭能放註腳。本書一個註腳都沒有。
#   bookmark  —— 比 hyperref 更好的 PDF 書籤。hyperref 自己也會做書籤。
STUBS = {
    "footnote.sty": r"""\ProvidesPackage{footnote}[2024/01/01 空殼]
\providecommand{\makesavenoteenv}[2][]{}
\providecommand{\savenotes}{}
\providecommand{\spewnotes}{}
""",
    "bookmark.sty": r"""\ProvidesPackage{bookmark}[2024/01/01 空殼]
\RequirePackage{hyperref}
\providecommand{\bookmarksetup}[1]{}
\providecommand{\bookmark}[2][]{}
\providecommand{\bookmarkdefinestyle}[2]{}
\providecommand{\bookmarkget}[1]{}
""",
}


def install_stubs(tmp, env):
    """把這台機器缺、但只是錦上添花的套件，用空殼補上。"""
    missing = [n for n in STUBS if not have_sty(n)]
    if not missing:
        return
    for name in missing:
        (tmp / name).write_text(STUBS[name], encoding="utf-8", newline="\n")
    env["TEXINPUTS"] = str(tmp) + os.pathsep + env.get("TEXINPUTS", "")
    print(f"  （這台機器沒有 {'、'.join(missing)}，改用內建空殼）")


def build(chapters=None, keep_tex=False, html=False):
    if not shutil.which("pandoc"):
        sys.exit("找不到 pandoc。請先安裝：https://pandoc.org/installing.html")

    BUILD.mkdir(exist_ok=True)
    files = collect(chapters)
    if not files:
        sys.exit("chapters/ 底下沒有東西可以排。")
    check_mono_font()

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

        env = dict(os.environ)
        env.setdefault("MIKTEX_ALLOW_UNRESTRICTED_SUPER_USER", "t")
        install_stubs(tmp, env)

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
            # MiKTeX 預設會在遇到缺少的套件時上網抓。抓不到的時候，
            # 連 pandoc 範本裡有 \IfFileExists 防護的套件也會變成硬錯誤 ——
            # 關掉 installer，缺的套件才會乾淨地「不存在」。
            "--pdf-engine-opt=--disable-installer",
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
                           encoding="utf-8", errors="replace", env=env)
        if keep_tex or r.returncode:
            tex = BUILD / "claude_teaches_go.tex"
            subprocess.run(cmd[:-2] + ["-s", "-o", str(tex)],
                           capture_output=True, env=env)
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
                           check=True, env=env)
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
