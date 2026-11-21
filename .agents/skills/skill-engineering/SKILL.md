---
name: skill-engineering
description: 當使用者要建立新 skill(例如「幫我寫一個 skill」「做一個 xxx 的 skill」),或對某個 skill 的結果不滿意、要優化或改寫它(例如「這個 skill 輸出不對」「幫我改寫 plan-with-class-diagram」)時使用,目標是 skill-form-*、skill-derive-* 本身時也走這裡。優化先做根因診斷並取得確認,再提出藍圖,確認後依序委派 skill-form-sop 與 skill-derive-rule、skill-derive-template、skill-derive-script 施工。只改單一 step 請改用 skill-derive-*,只改單一部位的內容請改用 skill-form-*。
compatibility: 需要 uv 與 Python 3.11 以上,各腳本的第三方套件宣告在 scripts/*.py 開頭的 PEP 723 區塊
---

# SOP

## Phase 1 -- 載入問題與素材

1. READ 讀取 `rules/編排-規範.md`，將其視為唯一編排規範來源。
2. READ 讀取 `rules/腳本執行-格式規範.md`，將其視為唯一腳本執行規範來源。
3. DELEGATE 依腳本執行規範執行 `scripts/audit_skill.py`，傳入 skills 根目錄與依編排規範決定的施工紀錄根目錄，取回現有 skill 的名稱、description、結構摘要、呼叫關係與過去的施工紀錄，供新建時查職責重疊、優化時把呼叫鏈對應到目錄。
4. ASK 依編排規範詢問使用者要新建還是優化既有 skill，並補齊該模式缺的資訊，取得回覆後才繼續；新建時略過 Phase 2。

## Phase 2 -- 完成根因診斷並取得確認（優化）

1. READ 讀取 `rules/根因分析-規範.md`，將其視為唯一根因分析規範來源。
2. THINK 依根因分析規範判定問題型態，決定要取得的證據與對話紀錄份數。
3. DELEGATE 有問題對話紀錄時，依腳本執行規範對每份對話紀錄執行 `scripts/trace_session.py`，傳入問題發生的對話紀錄（不確定是哪一份時，先列出近期對話請使用者指認），取回 skill 呼叫鏈、各 skill 載入過的檔案時間線、使用者的訊息、AI 先前的回覆與寫入的檔案，作為診斷的事實依據。
4. DELEGATE 依腳本執行規範再次執行 audit_skill 腳本，傳入 skills 根目錄與呼叫鏈上的 skill，取回 step 盤點、呼叫關係、複雜度與違規清單；以只回報的方式執行，違規清單只作診斷的事實，不在此階段修正。
5. READ 依根因分析規範，沿呼叫鏈走查各 skill 的 SOP 與過去的施工紀錄。
6. THINK 依根因分析規範，對照預期與現況，分析落差與根因。
7. READ 讀取 `templates/diagnosis.md`（骨架）與 `templates/diagnosis.example.md`（範例），兩個檔案都必須讀取，將其視為唯一診斷單樣板來源。
8. WRITE 依根因分析規範與診斷單樣板，複製骨架並參照範例填寫，在對話中輸出診斷單。
9. ASK 依根因分析規範詢問使用者是否同意診斷單；不同意就依根因分析規範回到本 phase 對應的步驟，取得明確同意才進入下一 phase；診斷結論是不施工時，依根因分析規範請使用者補證據、調整預期或結案，不進入下一 phase。

## Phase 3 -- 完成藍圖並取得確認

1. READ 讀取 `rules/選型-規範.md`，將其視為唯一選型規範來源。
2. THINK 依選型規範，決定目標 skill 的主幹；優化時另決定處置範圍，以及範圍內每個既有元素的處置。
3. READ 讀取 `templates/blueprint.md`（骨架）與 `templates/blueprint.example.md`（範例），兩個檔案都必須讀取，將其視為唯一藍圖樣板來源。
4. WRITE 依選型規範與藍圖樣板，複製骨架並參照範例填寫，在對話中輸出藍圖。
5. ASK 依選型規範詢問使用者是否同意藍圖；不同意就依選型規範回到對應的步驟，取得明確同意才進入下一 phase。

## Phase 4 -- 完成施工紀錄與 SOP 主幹

1. WRITE 依編排規範建立施工紀錄資料夾，存入藍圖；優化時另存入診斷單與還原點。
2. WRITE 新建時依編排規範建立目標 skill 的 SKILL.md 外殼。
3. DELEGATE 依編排規範委派 /skill-form-sop 依藍圖撰寫或重寫目標 skill 的 SOP，交付內容依編排規範。
4. READ 核對完成後的 SOP 與藍圖一致；有落差退回 /skill-form-sop 補正。

## Phase 5 -- 完成藍圖各列的施工

1. DELEGATE 依編排規範，按藍圖逐列委派 /skill-derive-script、/skill-derive-rule、/skill-derive-template 展開部位（改寫既有部位，或在既有部位檔內新增或刪除單條，則委派對應的 /skill-form-script、/skill-form-rule、/skill-form-template），交付內容為該列的交付單；取回、核對並更新該列狀態後才進入下一列。
2. WRITE 依編排規範刪除藍圖列為刪除的整份部位檔，並改寫藍圖列出的 frontmatter。

## Phase 6 -- 完成驗收並回報

1. DELEGATE 依腳本執行規範再次執行 audit_skill 腳本，傳入 skills 根目錄、藍圖處置列涉及的 skill 與施工紀錄資料夾，取回違規清單、藍圖追溯結果與複雜度前後對照；新增的違規清單為空才算完成。
2. READ 讀取 `rules/驗收-規範.md`，將其視為唯一驗收規範來源。
3. DELEGATE 依驗收規範委派全新的唯讀 agent 走查改完的 skill，交付內容依驗收規範，取回逐步走查結果；有落差時依驗收規範處理。
4. READ 依驗收規範的完成條件核對語意項；有落差立即補正。
5. WRITE 依驗收規範輸出完工報告，在對話中回報並存入施工紀錄資料夾。
