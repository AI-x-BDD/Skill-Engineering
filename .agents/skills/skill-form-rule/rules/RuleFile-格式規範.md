# Rule 1 - 每條規則都使用固定區塊與欄位順序

- Level: `MUST`
- 每條規則必須以 `# Rule N - <Rule name>` 開頭。
- 規則描述使用條列，聚焦單一規則，不混入其他主題。
- 每條規則都必須依序包含 `## Good Example` 與 `## Bad Example`。
- `Good Example` / `Bad Example` 內可以先用 1..* 個條列補充判讀重點，再放示範本體。
- `N` 從 1 開始，依序遞增，不跳號、不重複。
- 標題下方必須緊接 ``- Level: `<value>` `` 欄位。
- `Level` 僅可使用 `MUST`、`SHOULD`、`MAY`，其語意以 `RuleLevel-定義.md` 為準。
- `Level` 之後才寫規則描述條列，接著依序包含 `## Good Example` 與 `## Bad Example`。

## Good Example

- 這個例子是好的，因為它把標題、`Level`、規則描述與 Example 區塊排成固定順序，結構容易被人與 agent 穩定判讀。

````md
# Rule 1 - 類別命名

- Level: `MUST`
- 類別名稱使用 PascalCase

## Good Example

- 每個單字首字母大寫

```java
class OrderItem {}
```

## Bad Example

- 首字母小寫

```java
class orderItem {}
```
````

## Bad Example

- 這個例子是壞的，因為標題缺少 `Rule N -` 前綴且層級錯誤、缺少 `Level` 欄位、規則描述用段落混入兩個主題，也缺少 `## Bad Example`。

````md
## 類別命名

類別名稱使用 PascalCase，類別之間的關係只能用繼承與組合。

## Good Example

- 每個單字首字母大寫

```java
class OrderItem {}
```
````

# Rule 2 - Example 的示範本體必須包在 fenced code block

- Level: `MUST`
- `Good Example` 與 `Bad Example` 中，實際示範內容必須使用 fenced code block 包裹。
- code block 外只放簡短說明，不放示範本體。
- 若示範內容本身是 Markdown，code fence language 建議使用 `md`。
- 若需要在示範中展示巢狀 code block，外層應改用更長的 fence，例如 ````md。

## Good Example

- 這個例子是好的，因為說明留在 code block 外，示範本體包在 fence 內；示範內容含有 code block，所以外層改用四個反引號。

````md
## Good Example

- 每個單字首字母大寫

```java
class OrderItem {}
```
````

## Bad Example

- 這個例子是壞的，因為示範本體直接寫在 code block 外，沒有 fence 包裹。

````md
## Good Example

- 每個單字首字母大寫

class OrderItem {}
````

# Rule 3 - `Level` 欄位只填值，不在各 RuleFile 重複定義語意

- Level: `MUST`
- 每個 Rule 只需宣告自身 `Level` 值，不在當前 RuleFile 內重複解釋 `MUST`、`SHOULD`、`MAY` 的共用語意。
- `Level` 的語意集中由 `RuleLevel-定義.md` 負責。
- 若該 Rule 有額外限制或例外，寫在規則描述條列中，不覆寫共用 `Level` 定義。

## Good Example

- 這個例子是好的，因為 `Level` 只填值，語意交給 `RuleLevel-定義.md`；額外的例外寫在規則描述條列中，沒有改動 `MUST` 的定義。

````md
# Rule 1 - 類別命名

- Level: `MUST`
- 類別名稱使用 PascalCase
- 測試類別以 `Test` 結尾，不受第一條以外的命名限制
````

## Bad Example

- 這個例子是壞的，因為在 `Level` 欄位重述 `MUST` 的語意，並在說明中重新定義 `MUST` 可以被偏離，與 `RuleLevel-定義.md` 衝突，日後可能不一致。

````md
# Rule 1 - 類別命名

- Level: `MUST`，表示硬性規則，不可違反
- 本檔的 `MUST` 在有理由時可以偏離
- 類別名稱使用 PascalCase
````
