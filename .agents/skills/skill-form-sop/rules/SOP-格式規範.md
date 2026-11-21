# Rule 1 - Skill 必須包含 SOP section

- Level: `MUST`
- 每份 Skill 的 SKILL.md 必須包含 `# SOP` section。
- 流程內容都寫在 `# SOP` 底下，以 Phase 與 Step 組成。

## Good Example

- 有 `# SOP` section，底下以 Phase 分段。

```md
# SOP

## Phase 1 -- 載入需求

1. READ 讀取需求文件，確認開發範圍。
```

## Bad Example

- 沒有 `# SOP` section，流程以段落散寫。

```md
# 流程

先讀取需求文件，再開始開發。
```

# Rule 2 - Phase 標題格式

- Level: `MUST`
- 每個 Phase 標題必須寫成 `## Phase N -- <階段標題>`。
- `N` 從 1 開始，依序遞增，不跳號、不重複。

## Good Example

- 編號從 1 連續遞增，格式固定。

```md
## Phase 1 -- 載入需求

## Phase 2 -- 提案類別圖
```

## Bad Example

- 缺少 `Phase N --` 前綴、編號跳號，且使用不同分隔符號。

```md
## 載入需求

## Phase 3 - 提案類別圖
```

# Rule 3 - Phase 標題概括該 Phase 的內容

- Level: `SHOULD`
- Phase 標題應以「動作 + 對象」概括該 phase 底下所有 Step 實際在做的事。
- Phase 標題的範圍要與底下 Step 相符，不多於、不少於 Step 的實際內容。
- Phase 標題不使用「準備」「其他」「處理」等抽象詞。

## Good Example

- 標題直接概括 Step 內容：該 phase 只有讀取檔案，所以叫「讀取目標」。

```md
## Phase 1 -- 讀取目標

1. READ 讀取目標 skill 的 SKILL.md，確認要修改的 SOP 範圍。

## Phase 2 -- 撰寫並通過檢查

1. WRITE 修改目標 skill 的 SOP section。
2. READ 回頭檢查結果是否符合規範；若不符合，立即修正。
```

## Bad Example

- 標題是抽象詞，看不出底下做了什麼；第二個標題只概括了 Step 的一部分，漏掉檢查。

```md
## Phase 1 -- 準備

1. READ 讀取目標 skill 的 SKILL.md，確認要修改的 SOP 範圍。

## Phase 2 -- 撰寫

1. WRITE 修改目標 skill 的 SOP section。
2. READ 回頭檢查結果是否符合規範；若不符合，立即修正。
```

# Rule 4 - Step 格式

- Level: `MUST`
- 每個 Step 必須寫成 `N. <動詞> <描述此步驟所需進行的行為>`。
- `N` 在每個 Phase 內從 1 開始，依序遞增。

## Good Example

- Step 以編號開頭，後接動詞與行為描述。

```md
1. READ 讀取需求文件，確認開發範圍。
2. THINK 拆解需求，列出需要的類別。
```

## Bad Example

- 缺少動詞，且編號跳號。

```md
1. 需求文件要看過。
3. 列出需要的類別。
```

# Rule 5 - Step 動詞只能使用固定集合

- Level: `MUST`
- Step 動詞只能是 `READ`、`WRITE`、`THINK`、`DELEGATE`、`ASK` 其中之一。
- `READ` 用於讀取檔案、文件、上下文。
- `WRITE` 用於寫入或修改檔案、產出內容。
- `THINK` 用於分析、拆解、判斷、收斂。
- `DELEGATE` 用於委派給 script、其他 skill 或 agent。
- `ASK` 用於向使用者提問或請求確認，取得回覆後才進入下一步。

## Good Example

- 動詞皆在集合內，語意與行為相符。

```md
1. READ 讀取 `package.json`，確認專案使用的測試框架。
2. ASK 詢問使用者是否同意此方案，取得回覆後才繼續。
```

## Bad Example

- 使用集合外的動詞，且用 `READ` 描述寫入行為。

```md
1. CHECK 檢查專案使用的測試框架。
2. READ 把結果寫入 `report.md`。
```

# Rule 6 - Phase 必須有順序並建立在前一 Phase 的產出之上

- Level: `MUST`
- 後一個 Phase 必須使用前一個 Phase 的產出。
- 不可把互不相依、順序可任意對調的內容硬分成多個 Phase。

## Good Example

- Phase 2 使用 Phase 1 讀到的需求，Phase 3 使用 Phase 2 確認的類別圖。

```md
## Phase 1 -- 需求已釐清

1. READ 讀取需求文件。

## Phase 2 -- 類別圖已獲確認

1. WRITE 依 Phase 1 釐清的需求輸出類別圖。

## Phase 3 -- 程式已依類別圖完成

1. WRITE 依 Phase 2 確認的類別圖逐一實作類別。
```

## Bad Example

- 兩個 Phase 互不相依，順序對調也不影響結果。

```md
## Phase 1 -- 整理 README

1. WRITE 更新 README。

## Phase 2 -- 整理 CHANGELOG

1. WRITE 更新 CHANGELOG。
```

# Rule 7 - Step 必須可執行

- Level: `MUST`
- 每個 Step 必須是 AI 能直接執行並驗證完成與否的具體動作。
- 不可使用空泛指示，例如「注意品質」「確保正確」。

## Good Example

- 動作與完成條件都明確。

```md
1. READ 回頭對照類別圖，確認每個類別皆已實作；有落差立即補正。
```

## Bad Example

- 空泛指示，無法判斷是否完成。

```md
1. THINK 注意程式品質。
```

# Rule 8 - Step 寫清處理對象、動作與目的

- Level: `SHOULD`
- 每個 Step 應寫出處理對象、動作與目的。
- 單純到不需說明目的的 Step 可省略目的。

## Good Example

- 對象是 `package.json`，動作是讀取，目的是確認測試框架。

```md
1. READ 讀取 `package.json`，確認專案使用的測試框架。
```

## Bad Example

- 沒有處理對象，也沒有目的。

```md
1. READ 讀取資料。
```

# Rule 9 - 委派必須用 DELEGATE 標明對象與交付內容

- Level: `MUST`
- 需要委派時，必須使用 `DELEGATE` 動詞。
- `DELEGATE` Step 必須寫明委派對象與交付內容。

## Good Example

- 寫明委派對象為 `reviewer` agent，交付內容為變更檔案清單。

```md
1. DELEGATE 委派 `reviewer` agent 審查變更，交付內容為變更檔案清單，取回審查結論。
```

## Bad Example

- 用 `THINK` 描述委派，且沒有對象與交付內容。

```md
1. THINK 請別人幫忙看一下。
```
