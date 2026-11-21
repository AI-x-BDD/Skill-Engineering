# 藍圖 - release-notes、collect-changes

## 預期

- E1：發版說明的最前面列出本版所有破壞性變更
- E2：發版說明的每一項變更都標註對應的 PR 編號

範例情境：輸入「幫我整理 v2.3 的發版說明」，輸出最前面是「破壞性變更」段落，之後依 feat、fix、chore 分段，每項變更結尾附 PR 編號

## 處置範圍

- 範圍：走查範圍
- 擴大理由：無
- 僅走查：無
- 受影響的 skill：無（兩個 skill 都在處置範圍內，沒有其他 skill 委派它們）

## 主幹

### collect-changes

- Phase 1：讀取版本範圍內的 commit
  1. READ 讀取腳本執行規範（部位：`rules/腳本執行-格式規範.md`）
  2. THINK 確認版本範圍的起訖 tag（部位：無）
  3. DELEGATE 執行腳本取得範圍內每個 commit 的標題與註腳（部位：`scripts/list_commits.py`）
- Phase 2：完成變更清單
  1. WRITE 依類型分組輸出變更清單，標出破壞性變更（部位：新增 `rules/破壞性變更-規範.md`）

### release-notes

- Phase 1：讀取變更清單（不變）
- Phase 2：完成發版說明
  1. READ 讀取格式規範（部位：`rules/格式規範.md`）
  2. THINK 依格式規範決定每項變更的寫法（部位：無）
  3. WRITE 輸出發版說明（部位：無）

## 處置

| # | 位置 | 內容 | 處置 | 依據 | 確度 | 狀態 |
|---|---|---|---|---|---|---|
| 1 | collect-changes/SKILL.md#Phase 1 | 取得 commit 的 step 改為取得標題與註腳；確認起訖 tag 的 step 內容不變 | 改寫 | RC1、N3 | 高 | 待辦 |
| 2 | collect-changes/rules/腳本執行-格式規範.md | 內容不變，由 Phase 1 第 1 個 step 載入 | 保留 | N4 | 高 | 無需施工 |
| 3 | collect-changes/scripts/list_commits.py | 輸出加入每個 commit 的註腳 | 改寫 | RC1 | 高 | 待辦 |
| 4 | collect-changes/SKILL.md#Phase 2 | 分組輸出的 step 加上標出破壞性變更；依類型分組的內容不變 | 改寫 | RC1、N1 | 高 | 待辦 |
| 5 | collect-changes/rules/破壞性變更-規範.md | 定義哪些 commit 算破壞性變更與標記方式 | 新增 | RC1 | 中 | 待辦 |
| 6 | release-notes/SKILL.md#Phase 1 | 讀取變更清單與決定段落順序，內容不變 | 保留 | N1 | 高 | 無需施工 |
| 7 | release-notes/SKILL.md#Phase 2 | 輸出前加入讀取格式規範的 step，並改為依格式規範決定每項變更的寫法；輸出的 step 內容不變 | 改寫 | RC2、N2 | 中 | 待辦 |
| 8 | release-notes/rules/舊版格式.md | 已被格式規範取代，沒有任何 step 載入 | 刪除 | 無舉證 | 高 | 待辦 |
| 9 | release-notes/rules/格式規範.md | 內容不變，由 Phase 2 新增的讀取 step 載入 | 保留 | E2 | 高 | 無需施工 |

## 複雜度

| 項目 | 前 | 後 |
|---|---|---|
| Phase 數 | 4 | 4 |
| step 數 | 8 | 10（+2：RC1、RC2 各加一個載入規範的 step） |
| 規則數 | 8 | 9（+1：RC1 新增破壞性變更規範 2 條，扣掉刪除的舊版格式 1 條） |
| 樣板數 | 0 | 0 |
| 腳本數 | 1 | 1 |
| 總行數 | 323 | 348（+25：RC1、RC2 新增的 step 與規則） |

## 交付單

### 3 collect-changes/scripts/list_commits.py

- 目標 skill：`.claude/skills/collect-changes`
- 委派對象：/skill-form-script
- step 原文：DELEGATE 執行腳本取得範圍內每個 commit 的標題與註腳
- 交付內容：現行檔案的路徑為 `scripts/list_commits.py`；要改的地方與原因：輸出加入每個 commit 的註腳，因為 RC1 的變更清單沒有註腳可以判定破壞性變更；不可改變的部分：既有的標題輸出格式；驗收案例：正例 v2.2..v2.3 退出碼 0 且輸出含 `BREAKING CHANGE` 註腳，反例不存在的 tag 退出碼為 2

### 5 collect-changes/rules/破壞性變更-規範.md

- 目標 skill：`.claude/skills/collect-changes`
- 委派對象：/skill-derive-rule
- step 原文：WRITE 依類型分組輸出變更清單，標出破壞性變更
- 交付內容：規範名稱與 RuleFile 檔名：破壞性變更，`rules/破壞性變更-規範.md`；要把關的事：判定哪些 commit 算破壞性變更；約束該 step 的既有 RuleFile：無；要搬移的既有規則：無；新增規則需求：型別後的 `!` 標記與 `BREAKING CHANGE` 註腳都算破壞性變更，判定結果標在變更清單
