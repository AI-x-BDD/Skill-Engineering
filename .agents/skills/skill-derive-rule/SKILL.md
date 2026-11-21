---
name: skill-derive-rule
description: 當使用者指定某個 skill SOP 中的某一個 step,認為這一步需要更多規則把關時使用。為該 step 展開一份按需載入的 step 級 RuleFile,並把它接回 SOP,讓 skill 可以「流程先有、規則慢慢展開」。
---

# SOP

## Phase 1 -- 載入規則與展開目標

1. READ 讀取 `rules/展開-格式規範.md`，將其視為唯一展開規範來源。
2. READ 讀取目標 skill 的 SKILL.md，定位使用者指定的 step，並列出 `rules/` 底下的 RuleFile 檔名。
3. ASK 若 SOP 沒有標明哪些 RuleFile 約束該 step，詢問使用者該讀哪些；若使用者沒有說明這一步要把關什麼，一併詢問要新增的規則需求，取得回覆後才繼續。
4. READ 讀取目標 SOP 中會約束該 step 的 RuleFile，找出其中屬於該 step 主題的既有規則。

## Phase 2 -- step 級 RuleFile 已建立

1. READ 讀取 `rules/RuleFile建立-格式規範.md`，將其視為唯一 RuleFile 建立規範來源。
2. DELEGATE 依 RuleFile 建立規範委派 /skill-form-rule，建立 step 級 RuleFile 並從全域 RuleFile 搬出既有規則。
3. READ 依 RuleFile 建立規範核對委派結果；有落差時退回補正。

## Phase 3 -- SOP 已接上新 RuleFile

1. WRITE 依展開規範修改目標 skill 的 SOP，把被展開的 step 接上新 RuleFile。
2. READ 讀取修改後的 SOP，對照展開規範找出不符合處。
3. WRITE 修正不符合處。
