# Rule 1 - 不寫前情提要型 Step

- Level: `MUST`
- 每個 Step 都必須產生動作或產出。
- 只說明背景、目標或「接下來要做什麼」的 Step 不可存在。

## Good Example

- 每個 Step 都有具體動作。

```md
1. READ 讀取目標 skill 的 SKILL.md，確認要修改的 SOP 範圍。
2. WRITE 修改目標 skill 的 SOP section。
```

## Bad Example

- 第 1 步只是背景說明，沒有動作也沒有產出。

```md
1. THINK 本 skill 的目的是協助撰寫 SOP，接下來會先讀取檔案再修改。
2. WRITE 修改目標 skill 的 SOP section。
```

# Rule 2 - Step 不預先重述規則檔內容

- Level: `MUST`
- Step 只指向規則檔，不複述規則檔已定義的內容。
- 規則檔裡已有的格式、命名、數量限制，不在 Step 中再寫一次。

## Good Example

- Step 只指向規範。

```md
1. WRITE 依類別圖規範輸出類別圖。
```

## Bad Example

- Step 重述了規範內容，規範一改，Step 就會與規則檔不一致。

```md
1. WRITE 輸出類別圖，以 `classDiagram` 開頭，類別名稱使用 PascalCase。
```

# Rule 3 - RuleFile 只在真的要讀的那一步點名

- Level: `MUST`
- RuleFile 的完整路徑只在 SOP 中第一次 `READ` 它時寫出。
- 該 `READ` 必須位於第一個需要用到它的 Step 上，不提前到無關的 Phase 開頭。
- 後續 Step 以規範名稱指明依據，不再寫路徑。
- Skill 有多份 RuleFile 時，後續 Step 不可只寫「依規範」。

## Good Example

- 路徑只出現一次，且在排序前才點名；後續以規範名稱稱呼。

```md
## Phase 3 -- 程式已依類別圖完成

1. READ 讀取 `rules/開發順序-格式規範.md`，將其視為唯一開發順序規範來源。
2. THINK 依開發順序規範排出開發順序。
```

## Bad Example

- 路徑在後續 Step 重複出現，且有一步只寫「依規範」。

```md
1. READ 讀取 `rules/開發順序-格式規範.md`。
2. THINK 依 `rules/開發順序-格式規範.md` 排出開發順序。
3. WRITE 依規範逐一實作類別。
```

# Rule 4 - RuleFile 在需要判斷時才讀取

- Level: `SHOULD`
- RuleFile 應在 Step 需要判斷時才讀取，不在流程開頭整批載入。
- 每次執行都必定用到、且第一步就要用的規範，可以在第一步直接讀取。

## Good Example

- 在 THINK 需要判斷格式時才讀取規範。

```md
1. THINK 整理最小可用的 phase 與 step；需要判斷格式時，才讀取 `rules/SOP-格式規範.md`。
```

## Bad Example

- 還沒用到就先把兩份規範全部讀進來。

```md
1. READ 讀取 `rules/SOP-格式規範.md`。
2. READ 讀取 `rules/SOP-載入與精簡-格式規範.md`。
3. READ 讀取目標 skill 的 SKILL.md。
```

# Rule 5 - SOP 優先追求最短可執行路徑

- Level: `SHOULD`
- 能由一個 Step 完成的事，不拆成多個 Step。
- 單純為了分類而存在、沒有獨立產出的 Phase，不單獨成立。

## Good Example

- 讀取目標與撰寫合為最少的步驟。

```md
## Phase 1 -- 讀取目標

1. READ 讀取目標 skill 的 SKILL.md，確認要修改的 SOP 範圍。

## Phase 2 -- SOP 已完成

1. WRITE 修改目標 skill 的 SOP section。
```

## Bad Example

- 為了分類多出沒有產出的 Phase，並把一件事拆成兩步。

```md
## Phase 1 -- 準備

1. READ 開啟目標 skill 的資料夾。
2. READ 讀取目標 skill 的 SKILL.md。

## Phase 2 -- 其他

1. WRITE 修改目標 skill 的 SOP section。
```

# Rule 6 - 只保留真正影響結果的步驟

- Level: `SHOULD`
- 刪除重複的 Step 與無法落地的描述。
- 刪除後不影響產出結果的 Step，不保留。

## Good Example

- 每個 Step 都影響產出。

```md
1. READ 讀取需求文件。
2. WRITE 依需求輸出類別圖。
```

## Bad Example

- 第 3 步與第 2 步重複，沒有新增產出。

```md
1. READ 讀取需求文件。
2. WRITE 依需求輸出類別圖。
3. WRITE 再輸出一次類別圖。
```
