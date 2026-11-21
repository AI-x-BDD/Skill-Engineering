---
name: skill-derive-script
description: 當使用者指定某個 skill SOP 中的某一個 step,認為這一步可以交給腳本自動化執行時使用。為該 step 展開一支 Python 腳本,並把它接回 SOP,讓 skill 可以「流程先有、腳本慢慢展開」。條列式規則請改用 skill-derive-rule,產出檔案的格式請改用 skill-derive-template。
---

# SOP

## Phase 1 -- 載入展開目標

1. READ 讀取 `rules/腳本展開-格式規範.md`，將其視為唯一腳本展開規範來源。
2. READ 依腳本展開規範，讀取目標 skill 的 SKILL.md，定位使用者指定的 step，並列出 `rules/`、`templates/`、`scripts/` 底下的檔名。
3. ASK 若使用者沒有說明這一步要自動化什麼（輸入、輸出、哪些交給腳本、哪些仍由 AI 判斷、是否需要第三方套件、有沒有現成的驗收案例），詢問使用者，取得回覆後才繼續。

## Phase 2 -- 完成腳本與驗收

1. READ 讀取 `rules/腳本建立-格式規範.md`，將其視為唯一腳本建立規範來源。
2. DELEGATE 依腳本建立規範委派 /skill-form-script，為該 step 建立腳本。
3. READ 依腳本建立規範核對委派結果；有落差時退回補正。
4. READ 讀取目標 skill 的 `rules/腳本執行-格式規範.md`，將其視為唯一腳本執行規範來源。
5. DELEGATE 依腳本執行規範與腳本建立規範，執行新腳本的驗收案例，取回退出碼與輸出；有落差時退回補正。

## Phase 3 -- 完成腳本接回 SOP

1. WRITE 依腳本展開規範修改目標 skill 的 SOP 與 SKILL.md frontmatter，把被展開的 step 接上新腳本。
2. READ 讀取修改後的 SKILL.md，對照腳本展開規範找出不符合處。
3. WRITE 修正不符合處。
