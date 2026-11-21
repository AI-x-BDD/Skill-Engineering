# 診斷單 - release-notes（呼叫鏈：collect-changes → release-notes）

## 問題型態

重複性問題

## 預期

- E1：發版說明的最前面列出本版所有破壞性變更
- E2：發版說明的每一項變更都標註對應的 PR 編號

## 現況

使用者先後要求整理 v2.2 與 v2.3 的發版說明，兩次產出的說明都沒有破壞性變更的段落，也都只有一半的變更標了 PR 編號；使用者在 v2.3 那次的第 4 則訊息更正：「怎麼沒有 breaking changes？PR 編號也漏了」

## 案例

- 對話紀錄：`~/.claude/projects/D--work-shop/3f2a9c1e-7b4d-4e0a-9a52-1c6d8e2f7a10.jsonl`；當時的輸入：幫我整理 v2.3 的發版說明
- 對話紀錄：`~/.claude/projects/D--work-shop/8b1d44f0-52c7-4d3e-8f0a-6a9b3c2d1e55.jsonl`；當時的輸入：整理 v2.2 的發版說明

## 呼叫鏈

1. collect-changes：收到版本範圍 v2.2..v2.3，產出依類型分組的變更清單
2. release-notes：收到變更清單，產出發版說明

## 落差與根因

### 落差 1：發版說明沒有破壞性變更的段落

- 對應預期：E1
- 偏離點：collect-changes 產出的變更清單沒有破壞性變更的欄位
- 根因：RC1，`collect-changes/SKILL.md` 的 SOP 沒有任何 step 讀取 commit 的 `BREAKING CHANGE` 註腳，缺了這一步
- 診斷階梯：指示（缺）
- 證據：SOP 全文沒有讀取註腳的 step；兩份 trace 的時間線中 collect-changes 都沒有讀取任何含註腳的檔案；兩份 trace 列出的寫入檔案（發版說明）開頭都沒有破壞性變更的段落
- 反事實：若 SOP 有 step 讀取註腳，變更清單就會帶破壞性變更的欄位，release-notes 就有內容可以排在最前面
- 排除的可能：release-notes 看到欄位卻忽略（排除：清單裡沒有該欄位）；兩個 skill 沒被觸發（排除：trace 中兩個 Skill 呼叫都在）
- 證據等級：已證實

### 落差 2：只有一半的變更標了 PR 編號

- 對應預期：E2
- 偏離點：release-notes 產出的發版說明
- 根因：RC2，`release-notes/SKILL.md` 的輸出 step 之前沒有載入 `rules/格式規範.md`，規範第 2 條要求每項標 PR 編號，但執行時沒有被讀到
- 診斷階梯：到位（漏載）
- 證據：兩份 trace 的時間線中都沒有 `rules/格式規範.md` 的 Read；SOP 全文沒有指向該檔的 READ step；兩份 trace 列出的寫入檔案（發版說明）都只有一半的變更標了 PR 編號
- 反事實：若輸出前有 READ 該規範，AI 會看到「每項標 PR 編號」的要求，這次的輸出應該會不同
- 排除的可能：規範寫得不清楚（排除：第 2 條明寫每項都要標）；AI 沒有遵循已載入的規範（排除：該規範根本沒被載入）
- 證據等級：高度可能

## 走查範圍

- collect-changes：Phase 1 與 Phase 2 全部 4 個 step，載入 `rules/腳本執行-格式規範.md` 與 `scripts/list_commits.py`
- release-notes：Phase 1 與 Phase 2 全部 4 個 step，沒有載入任何規範或樣板
- 結構稽核：collect-changes 沒有違規；release-notes 有 2 則 SOP-PART-ORPHAN（`rules/舊版格式.md`、`rules/格式規範.md`，走查範圍內）

## 不可退化清單

- N1：變更依 feat、fix、chore 分組，目前的分組是正確的
- N2：發版說明使用繁體中文，語氣維持現況
- N3：版本範圍由使用者指定的起訖 tag 決定，目前的取得方式是正確的
- N4：腳本以退出碼 2 結束時，skill 停下並回報原因，不用猜測補上內容

## 尚缺證據

- RC2 的反事實需要重跑確認，改完後以同一個輸入在新對話重跑一次
- 兩份紀錄都沒有保留 collect-changes 輸出的原文，需要時請在新對話重跑並保留紀錄
