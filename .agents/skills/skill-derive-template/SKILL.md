---
name: skill-derive-template
description: 當使用者指定某個 skill SOP 中的某一個 step,認為這一步要約束的是 AI 產出檔案的「格式」(而非條列式規則)時使用。為該 step 展開一組按需載入的樣板(骨架與範例),並把它接回 SOP,讓 skill 可以「流程先有、樣板慢慢展開」。條列式規則請改用 skill-derive-rule。
---

# SOP

## Phase 1 -- 載入展開目標

1. READ 讀取 `rules/樣板展開-格式規範.md`，將其視為唯一樣板展開規範來源。
2. READ 依樣板展開規範，讀取目標 skill 的 SKILL.md，定位使用者指定的 step，並列出 `rules/` 與 `templates/` 底下的檔名。
3. ASK 若使用者沒有說明這一步要產出的檔案格式（副檔名、有無現成範本、填位符號偏好），詢問使用者，取得回覆後才繼續。

## Phase 2 -- 完成骨架與範例

1. READ 讀取 `rules/樣板建立-格式規範.md`，將其視為唯一樣板建立規範來源。
2. DELEGATE 依樣板建立規範委派 /skill-form-template，為該 step 建立骨架與範例。
3. READ 依樣板建立規範核對委派結果；有落差時退回補正。

## Phase 3 -- 完成樣板接回 SOP

1. WRITE 依樣板展開規範修改目標 skill 的 SOP，把被展開的 step 接上新樣板。
2. READ 讀取修改後的 SOP，對照樣板展開規範找出不符合處。
3. WRITE 修正不符合處。
