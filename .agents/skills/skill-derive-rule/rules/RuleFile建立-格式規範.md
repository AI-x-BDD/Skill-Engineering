# Rule 1 - step 級 RuleFile 命名

- Level: `MUST`
- 檔名以該 step 把關的主題命名
- 檔名不可包含 Phase 或 step 編號

## Good Example

```text
rules/實作-格式規範.md
```

## Bad Example

- 用編號命名，SOP 插入新 step 後編號改變，檔名就對不上

```text
rules/phase3-step2-格式規範.md
```

# Rule 2 - 既有規則搬移

- Level: `MUST`
- 全域 RuleFile 中屬於被展開 step 主題的規則，必須搬到新的 step 級 RuleFile
- 搬移後從全域 RuleFile 刪除該規則，剩餘規則重新編號

## Good Example

- 展開「排出開發順序」這一步時，Before 的全域 RuleFile 有開發順序規則

```md
# Rule 1 - 類別圖語法
# Rule 2 - 類別圖內容範圍
# Rule 3 - 開發順序
# Rule 4 - 實作與類別圖一致
```

- After 的全域 RuleFile 移除開發順序，剩餘規則重新編號

```md
# Rule 1 - 類別圖語法
# Rule 2 - 類別圖內容範圍
# Rule 3 - 實作與類別圖一致
```

- After 的 `開發順序-格式規範.md` 收下搬來的規則，再接上新增規則

```md
# Rule 1 - 開發順序
# Rule 2 - 有循環相依時先拆出介面
```

## Bad Example

- 新規則寫進 step 級 RuleFile，舊規則卻仍留在全域 RuleFile，同一主題分散兩處

```md
# Rule 1 - 類別圖語法
# Rule 2 - 類別圖內容範圍
# Rule 3 - 開發順序
# Rule 4 - 實作與類別圖一致
```

# Rule 3 - 委派的交付清單必須完整

- Level: `MUST`
- 委派 /skill-form-rule 時，交付內容必須包含：目標 skill、依本規範決定的 RuleFile 檔名、要搬移的既有規則、新增規則需求、搬移後要從全域 RuleFile 刪除該規則並重新編號
- 要搬移的既有規則必須逐條寫出原文，不可只寫主題名
- 缺任一項不得委派

## Good Example

- 五項都齊全，搬移規則附上原文

```md
- 目標 skill：skill-api-doc
- RuleFile 檔名：`rules/錯誤碼-格式規範.md`
- 要搬移的既有規則：`文件-格式規範.md` 的 Rule 3「錯誤碼要列出 HTTP 狀態與重試建議」（附原文）
- 新增規則需求：4xx 與 5xx 分開寫；5xx 標明可否重試
- 搬移後從 `文件-格式規範.md` 刪除 Rule 3，剩餘規則重新編號
```

## Bad Example

- 只寫主題名，沒有原文；也沒有說明搬移後要刪除與重新編號

```md
- 目標 skill：skill-api-doc
- RuleFile 檔名：`rules/錯誤碼-格式規範.md`
- 要搬移的既有規則：錯誤碼相關規則
- 新增規則需求：4xx 與 5xx 分開寫
```

# Rule 4 - 委派取回後必須核對

- Level: `MUST`
- 取回後必須核對新 step 級 RuleFile 已收齊所有搬移的規則
- 取回後必須核對全域 RuleFile 已刪除這些規則，且剩餘規則編號連續
- 有落差時退回補正，不進入下一步

## Good Example

- 新檔收齊搬移規則，全域檔已刪除且編號連續

```md
rules/錯誤碼-格式規範.md    → Rule 1 搬來的規則、Rule 2、Rule 3 新增規則
rules/文件-格式規範.md      → Rule 1、Rule 2（原 Rule 3 已刪除）
```

## Bad Example

- 全域檔刪除後編號跳號，卻直接進入下一步

```md
rules/文件-格式規範.md      → Rule 1、Rule 2、Rule 4
```
