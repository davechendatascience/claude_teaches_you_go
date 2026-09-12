# 《Claude 教你圍棋》

**圍棋的五層骨架 —— 從一顆棋子的氣，到 AI 眼中的勝率**

用高槓桿頓悟（High-Leverage Eureka）與可計算的公式重寫圍棋教學。
沿用 `robotics/Modern_robotics_rewrite` 的 SME 框架（Simple / Multi-Angle / Expressive）。

## 現況

規劃階段（M0）。架構文件已完成，尚未開始寫章節。

## 從哪裡開始讀

| 文件 | 內容 |
| :--- | :--- |
| [`docs/00_book_outline.md`](docs/00_book_outline.md) | **全書架構** —— 14 章 + 5 附錄，每章的思想實驗、頓悟與公式 |
| [`docs/01_book_prompt.md`](docs/01_book_prompt.md) | SME 教學框架的圍棋版（系統提示） |
| [`docs/02_concept_dependency_graph.md`](docs/02_concept_dependency_graph.md) | 五層骨架與概念依賴 DAG |
| [`docs/03_writing_brief.md`](docs/03_writing_brief.md) | 章節骨架、字數、徽章、棋圖與程式碼規範 |
| [`docs/04_formula_index.md`](docs/04_formula_index.md) | **概念 → 公式** 對照總表（含定理／啟發式／待驗證的誠實標記） |

## 一句話

圍棋的每一條口訣都是一個定理的白話版，而它們全部來自同一組五個概念：
**連通性、不變量、溫度、場、值函數** —— 外加一個例外：**劫**。
