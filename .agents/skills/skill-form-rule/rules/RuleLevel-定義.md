# Rule 1 - `MUST` 只用於不可違反的硬性規則

- Level: `MUST`
- `MUST` 表示硬性規則，預設不可違反。
- 若規則不符合`MUST`，應視為錯誤、缺漏、或違規，而不是單純可改進項目。
- 適合用於必要欄位、固定結構、禁止事項或會影響格式正確性的要求。
- 不可把純偏好、可替代寫法或風格建議包成`MUST`。

## Good Example

- 這個例子是好的，因為它把缺少必要欄位視為明確錯誤，符合`MUST`的語意。

````md
# Rule 3 - 美條規則都必須宣告 Level

- Level: `MUST`
- 每條規則都必須包含 `- Level: \`<value>\`` 欄位。
```

## Bad Example

- 缺少 `Level` 欄位，屬於格是錯誤。

```md
# Rule 4 - Example 區塊不可省略

- 每條規則都必須包含 `## Good Example` 與 `## Bad Example`
```
````

## Bad Example

- 這個例子是壞的，因為它把純建議性事項標成 `MUST` ，讓規則強度過高。 

````md
# Rule 8 - 檔名可以更短

- Level: `MUST`
- 檔名最好控制在 12 個字內
````


# Rule 2 - `SHOULD` 用於預設應遵守但容許具理由偏離的規則

- Level: `MUST`
- `SHOULD` 表示強烈建議，預設應遵守。
- 適合用於提升可讀性、一致性、維護性或協作效率的規則。
- 不應把缺少就會造成明確錯誤的要求標成`SHOULD`。

## Good Example

- 這個例子是好，因為它描述的是提升可讀性的偏好，允許在特殊情況下調整。

````md
# Rule 5 - 檔名應清楚表達主題

- Level: `SHOULD`
- 檔名應讓讀者一眼辨識這份 RuleFile 的主題。

## Bad Example
- 檔名過度抽象，降低可讀性，但不一定造成格是錯誤。

```md
foo.md
```
````

## Bad Example

- 這個例子是壞的，因為它把會造成格式缺漏的要求降成`SHOULD`。

````md
# Rule 9 - 每條規則都必須附 Bad Example

- Level: `SHOULD`
- 每條規則都必須包含 `## Bad Example`
````

# Rule 3 - `MAY` 用於可選寫法、替代方案或延伸彈性

- Level: `MUST`
- `MAY` 表示可選項目，做或不做都合規。
- 適合用於替代寫法、額外補充或延伸彈性，不影響格式正確性與一致性。
- 不應把缺少就會造成錯誤、或團隊預期一致遵守的要求標成`MAY`。

## Good Example

- 這個例子是好的，因為補充說明是否撰寫都不影響規則本身的正確性，屬於可選項目。

````md
# Rule 6 - Example 可以附補充說明

- Level: `MAY`
- `Good Example` 與 `Bad Example` 可以在示範本體前附 1..* 條判讀重點。
````

## Bad Example

- 這個例子是壞的，因為它把必要欄位標成 `MAY`，讓硬性要求變成可有可無。

````md
# Rule 7 - 規則可以宣告 Level

- Level: `MAY`
- 每條規則可以包含 `- Level: \`<value>\`` 欄位。
````
