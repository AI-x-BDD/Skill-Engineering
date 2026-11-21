# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""盤點 skill 並檢查結構，供 skill-engineering 使用。

用法：
    uv run audit_skill.py list <skills 根目錄> [--runs-dir <施工紀錄根目錄>]
    uv run audit_skill.py check <skills 根目錄> [<skill 名稱> ...] [--run <施工紀錄資料夾>] [--report-only]

list   列出每個 skill 的名稱、description、結構摘要、呼叫關係與過去的施工紀錄；
       施工紀錄根目錄不存在時視為沒有任何紀錄
check  檢查 skill 的結構違規並計算複雜度；加 --run 時另核對藍圖追溯與複雜度前後對照，
       此時可省略 skill 名稱，改由藍圖推得，並且 baseline 就有的既有違規另列為 pre_existing，
       不算違規也不影響退出碼（比對時抹掉訊息裡的行號）；診斷單證據等級為推測的根因不要求處置列，
       藍圖引用它才算違規；加 --report-only 時有違規也以退出碼 0 結束，供診斷階段只取事實

輸出較大時加 --output <檔案> 寫成檔案，stdout 只留摘要；已存在的檔案要加 --force 才會覆寫，
--dry-run 只列出會寫入的檔案。

退出碼：
    0  成功，沒有違規
    1  有違規（清單以 JSON 寫在 stdout）
    2  無法執行（原因寫在 stderr）
"""
import argparse
import io
import json
import re
import sys
import tokenize
from pathlib import Path

VERBS = ("READ", "WRITE", "THINK", "DELEGATE", "ASK")
PHASE_RE = re.compile(r"^## Phase (\d+) -- (.+?)\s*$")
STEP_RE = re.compile(r"^(\d+)\.\s+(\S+)")
PART_RE = re.compile(r"`((?:rules|templates|scripts)/[^`\s]+)`")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
RULE_RE = re.compile(r"^# Rule (\d+) - (.+)$")
LEVEL_RE = re.compile(r"^- Level: `(MUST|SHOULD|MAY)`$")
SLASH_RE = re.compile(r"/([A-Za-z0-9][\w.-]*)")
ID_RE = re.compile(r"(?<![A-Za-z0-9])(RC\d+|E\d+|N\d+|無舉證|使用者指定)(?![A-Za-z0-9])")
PLACEHOLDERS = {
    "{{名稱}}": re.compile(r"\{\{[^{}\n]+\}\}"),
    "[[名稱]]": re.compile(r"\[\[[^\[\]\n]+\]\]"),
}
EXEC_RULE = "rules/腳本執行-格式規範.md"
PROJECT_FILES = {
    "pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "__init__.py",
    "uv.lock", "poetry.lock", "Pipfile",
}
BLUEPRINT_HEADER = ["#", "位置", "內容", "處置", "依據", "確度", "狀態"]
ACTIONS = ("保留", "改寫", "刪除", "新增")
CONFIDENCE = ("高", "中", "低")
STATUSES = ("待辦", "已完成", "無需施工")
ITEMS = [
    ("Phase 數", "phases"), ("step 數", "steps"), ("規則數", "rules"),
    ("樣板數", "templates"), ("腳本數", "scripts"), ("總行數", "lines"),
]
MAX_ITEMS = 200


class CannotRun(Exception):
    """無法執行的情況，訊息寫到 stderr 並以退出碼 2 結束。"""


# ---------------------------------------------------------------- 基本工具

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def count_lines(path: Path) -> int:
    try:
        return len(read_text(path).splitlines())
    except UnicodeDecodeError:
        return 0


def scan_fences(lines):
    """標出每一行是 text、open、code 或 close，回傳 (種類清單, 最後是否沒有關閉)。"""
    kinds = []
    fence = None
    for line in lines:
        m = FENCE_RE.match(line)
        if fence is None:
            if m:
                fence = (m.group(1)[0], len(m.group(1)))
                kinds.append("open")
            else:
                kinds.append("text")
        elif m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1] and not m.group(2).strip():
            fence = None
            kinds.append("close")
        else:
            kinds.append("code")
    return kinds, fence is not None


def parse_frontmatter(lines):
    """回傳 (欄位, 本文起始的行索引)；沒有 frontmatter 時回傳 ({}, 0)。"""
    if not lines or lines[0].strip() != "---":
        return {}, 0
    fm = {}
    key = None
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == "---":
            return {k: v.strip().strip("\"'") for k, v in fm.items()}, i + 1
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fm[key] = "" if m.group(2).strip() in (">", "|", ">-", "|-") else m.group(2).strip()
        elif key and line[:1] in (" ", "\t"):
            fm[key] = (fm[key] + " " + line.strip()).strip()
    return {}, 0


def viol(skill, file, line, code, problem, fix):
    return {"skill": skill, "file": file, "line": line, "code": code, "problem": problem, "fix": fix}


def cap(items):
    return items[:MAX_ITEMS]


# ---------------------------------------------------------------- 解析 skill

def own_refs(line):
    """取出這行寫的部位路徑；「目標 skill 的 `路徑`」指的是別的 skill 的檔案，不算在內。"""
    return [r for r in PART_RE.findall(line) if not re.search(r"目標 skill 的\s*`" + re.escape(r) + "`", line)]


def parse_sop(lines, kinds):
    sop = {"found": False, "line": 0, "phases": [], "steps": [], "refs": [], "format": []}
    in_sop = False
    phase = None
    for i, line in enumerate(lines):
        if kinds[i] != "text":
            continue
        no = i + 1
        if not in_sop:
            if line.strip() == "# SOP":
                in_sop = True
                sop["found"] = True
                sop["line"] = no
            continue
        if re.match(r"^# \S", line):
            break
        if line.startswith("## "):
            m = PHASE_RE.match(line)
            if m:
                phase = {"n": int(m.group(1)), "title": m.group(2), "line": no, "steps": []}
                sop["phases"].append(phase)
            else:
                phase = None
                sop["format"].append((no, "SOP-PHASE-FORMAT",
                                      f"Phase 標題不是「## Phase N -- <階段標題>」：{line.strip()[:40]}",
                                      "改寫成「## Phase N -- <階段標題>」"))
            continue
        m = STEP_RE.match(line)
        if m:
            step = {"n": int(m.group(1)), "verb": m.group(2), "text": line, "line": no,
                    "refs": own_refs(line), "phase": phase["n"] if phase else None}
            if phase is None:
                sop["format"].append((no, "SOP-STEP-FORMAT", "step 不在任何 Phase 底下",
                                      "把 step 放進某個「## Phase N -- <階段標題>」之下"))
            else:
                phase["steps"].append(step)
            sop["steps"].append(step)
            sop["refs"].extend((ref, no) for ref in step["refs"])
        else:
            sop["refs"].extend((ref, no) for ref in own_refs(line))
    return sop


def list_parts(skill_dir: Path):
    def files_in(sub, pattern=None):
        d = skill_dir / sub
        if not d.is_dir():
            return []
        found = sorted(d.glob(pattern)) if pattern else sorted(d.iterdir())
        return [p for p in found if p.is_file()]

    scripts_dir = skill_dir / "scripts"
    extras = []
    if scripts_dir.is_dir():
        for p in sorted(scripts_dir.iterdir()):
            if p.name == "__pycache__":
                continue
            if p.is_dir() and (p.name.startswith(".") or (p / "__init__.py").exists()):
                extras.append(p)
            elif p.is_file() and p.name in PROJECT_FILES:
                extras.append(p)
    return {
        "rules": files_in("rules", "*.md"),
        "templates": files_in("templates"),
        "scripts": files_in("scripts", "*.py"),
        "extras": extras,
    }


def load_skill(skill_dir: Path):
    lines = read_text(skill_dir / "SKILL.md").splitlines()
    kinds, unclosed = scan_fences(lines)
    fm, _ = parse_frontmatter(lines)
    return {
        "name": skill_dir.name, "dir": skill_dir, "lines": lines, "fm": fm,
        "sop": parse_sop(lines, kinds), "parts": list_parts(skill_dir), "unclosed": unclosed,
    }


def load_all(root: Path):
    return {d.name: load_skill(d) for d in sorted(root.iterdir()) if d.is_dir() and (d / "SKILL.md").is_file()}


def rel(skill, path: Path):
    return path.relative_to(skill["dir"]).as_posix()


def count_rules(path: Path):
    lines = read_text(path).splitlines()
    kinds, _ = scan_fences(lines)
    return sum(1 for i, line in enumerate(lines) if kinds[i] == "text" and RULE_RE.match(line))


def is_example(path: Path):
    return ".example." in path.name


def complexity(skill):
    parts = skill["parts"]
    total = len(skill["lines"])
    for p in parts["rules"] + parts["templates"] + parts["scripts"]:
        total += count_lines(p)
    sop = skill["sop"]
    return {
        "phases": len(sop["phases"]),
        "steps": sum(len(p["steps"]) for p in sop["phases"]),
        "rule_files": len(parts["rules"]),
        "rules": sum(count_rules(p) for p in parts["rules"]),
        "templates": sum(1 for p in parts["templates"] if not is_example(p)),
        "scripts": len(parts["scripts"]),
        "lines": total,
    }


def relations(skills):
    names = set(skills)
    delegates = {}
    for name, s in skills.items():
        found = set()
        for step in s["sop"]["steps"]:
            found.update(t for t in SLASH_RE.findall(step["text"]) if t in names and t != name)
        delegates[name] = sorted(found)
    called_by = {name: sorted(n for n, d in delegates.items() if name in d) for name in names}
    return delegates, called_by


# ---------------------------------------------------------------- 結構檢查

def check_sop(skill, out, warn):
    name, sop = skill["name"], skill["sop"]
    f = "SKILL.md"
    parts = skill["parts"]
    if not sop["found"]:
        out.append(viol(name, f, 1, "SOP-MISSING", "SKILL.md 沒有 `# SOP` section",
                        "補上 `# SOP` 與 Phase/step（交給 /skill-form-sop）"))
        return
    for no, code, problem, fix in sop["format"]:
        out.append(viol(name, f, no, code, problem, fix))
    for idx, ph in enumerate(sop["phases"], 1):
        if ph["n"] != idx:
            out.append(viol(name, f, ph["line"], "SOP-PHASE-NUMBER",
                            f"Phase 編號是 {ph['n']}，應為 {idx}", "Phase 編號從 1 連續遞增"))
        if not ph["steps"]:
            warn.append(viol(name, f, ph["line"], "SOP-PHASE-EMPTY",
                             f"Phase {ph['n']} 底下沒有 step", "刪除空的 Phase，或補上有產出的 step"))
        for j, st in enumerate(ph["steps"], 1):
            if st["n"] != j:
                out.append(viol(name, f, st["line"], "SOP-STEP-NUMBER",
                                f"Phase {ph['n']} 的 step 編號是 {st['n']}，應為 {j}", "step 編號在每個 Phase 內從 1 連續遞增"))
            if st["verb"] not in VERBS:
                out.append(viol(name, f, st["line"], "SOP-STEP-VERB",
                                f"動詞「{st['verb'][:12]}」不在 READ、WRITE、THINK、DELEGATE、ASK 之內",
                                "改用固定動詞集合，動詞後留一個空格"))

    # 路徑：只在第一次出現時寫出
    seen = {}
    for ref, no in sop["refs"]:
        seen.setdefault(ref, []).append(no)
    for ref, nos in seen.items():
        if len(nos) > 1:
            out.append(viol(name, f, nos[1], "SOP-PATH-REPEAT",
                            f"`{ref}` 在第 {', '.join(map(str, nos))} 行重複出現",
                            "路徑只在第一次載入或委派時寫出，後續 step 改用名稱稱呼"))
    existing = set()
    for p in parts["rules"] + parts["templates"] + parts["scripts"]:
        existing.add(rel(skill, p))
    for ref, nos in seen.items():
        if ref not in existing:
            out.append(viol(name, f, nos[0], "SOP-PATH-DANGLING", f"SOP 引用的 `{ref}` 不存在",
                            "建立該檔，或刪除對它的引用"))
    for path in sorted(existing - set(seen)):
        out.append(viol(name, path, 1, "SOP-PART-ORPHAN", f"`{path}` 沒有任何 step 引用",
                        "在 SOP 補上載入或委派它的 step，或刪除該檔"))

    # READ 規範與樣板的寫法
    for st in sop["steps"]:
        if st["verb"] != "READ":
            continue
        rules = [r for r in st["refs"] if r.startswith("rules/")]
        if rules and seen.get(rules[0], [0])[0] == st["line"] and not re.search(r"將其視為唯一.+來源", st["text"]):
            out.append(viol(name, f, st["line"], "SOP-READ-WORDING",
                            f"載入 `{rules[0]}` 的 step 沒有寫「將其視為唯一 <規範名稱> 規範來源」",
                            "補上「將其視為唯一 <規範名稱> 規範來源」"))
        if re.search(r"視為唯一(?:規範|樣板)來源", st["text"]):
            out.append(viol(name, f, st["line"], "SOP-READ-WORDING", "「唯一…來源」前面沒有寫出規範或樣板的名稱",
                            "寫成「將其視為唯一 <名稱> 規範來源」或「…樣板來源」"))
    template_names = {rel(skill, p) for p in parts["templates"]}
    for t in sorted(template_names):
        if ".example." in t:
            continue
        stem, _, ext = t.rpartition(".")
        partner = f"{stem}.example.{ext}"
        if partner in template_names:
            together = any(t in s["refs"] and partner in s["refs"] for s in sop["steps"])
            if not together and (t in seen or partner in seen):
                out.append(viol(name, f, seen.get(t, seen.get(partner))[0], "SOP-TEMPLATE-PAIR",
                                f"`{t}` 與 `{partner}` 沒有在同一個 READ step 一起載入",
                                "同一個 READ step 寫出骨架與範例兩個路徑，並寫明兩個檔案都必須讀取"))

    # 腳本執行規範必須在第一個腳本 step 之前載入
    first_script = next((i for i, s in enumerate(sop["steps"]) if any(r.startswith("scripts/") for r in s["refs"])), None)
    if first_script is not None:
        exec_idx = next((i for i, s in enumerate(sop["steps"]) if EXEC_RULE in s["refs"]), None)
        if exec_idx is None:
            out.append(viol(name, f, sop["steps"][first_script]["line"], "SOP-EXEC-RULE",
                            "SOP 有腳本 step，但沒有載入腳本執行規範",
                            f"在第一個腳本 step 前插入 READ `{EXEC_RULE}`"))
        elif exec_idx > first_script:
            out.append(viol(name, f, sop["steps"][exec_idx]["line"], "SOP-EXEC-RULE",
                            "腳本執行規範的載入 step 比第一個腳本 step 還晚",
                            "把載入 step 搬到第一個腳本 step 的正前方"))

    # 多份 RuleFile 時不可只寫「依規範」
    if len(parts["rules"]) >= 2:
        for no, line in enumerate(skill["lines"], 1):
            if STEP_RE.match(line) and re.search(r"依規範(?!名稱)", line):
                out.append(viol(name, f, no, "SOP-RULE-UNNAMED", "已有多份 RuleFile，step 只寫「依規範」",
                                "改成「依 <規範名稱> 規範」"))


def check_frontmatter(skill, out, warn):
    name, fm = skill["name"], skill["fm"]
    if not fm:
        out.append(viol(name, "SKILL.md", 1, "FM-MISSING", "SKILL.md 沒有 frontmatter", "補上 name 與 description"))
        return
    if fm.get("name") != name:
        out.append(viol(name, "SKILL.md", 2, "FM-NAME", f"frontmatter 的 name「{fm.get('name')}」與資料夾名稱「{name}」不同",
                        "讓 name 與資料夾同名"))
    if not fm.get("description"):
        out.append(viol(name, "SKILL.md", 2, "FM-DESC", "frontmatter 沒有 description", "補上觸發情境與分界"))
    if skill["parts"]["scripts"]:
        comp = fm.get("compatibility", "")
        if not comp:
            warn.append(viol(name, "SKILL.md", 2, "FM-COMPAT", "有腳本但 frontmatter 沒有 compatibility",
                             "補上需要 uv 與 Python 版本下限；新增腳本的 skill 由 /skill-derive-script 展開時附帶寫入，既有 skill 缺少時列入完工報告的未解決事項（skill-engineering 不手改）"))
        elif len(comp) > 500:
            warn.append(viol(name, "SKILL.md", 2, "FM-COMPAT", "compatibility 超過 500 字元", "精簡到 500 字元以內"))


def check_rule_file(skill, path: Path, out):
    name, f = skill["name"], rel(skill, path)
    lines = read_text(path).splitlines()
    kinds, unclosed = scan_fences(lines)
    if unclosed:
        out.append(viol(name, f, len(lines), "RULE-FENCE", "有 fenced code block 沒有關閉",
                        "補上對應的結尾 fence；示範含巢狀 code block 時外層改用更長的 fence"))
    rules = []
    section = None
    for i, line in enumerate(lines):
        no = i + 1
        if kinds[i] != "text":
            if kinds[i] == "open" and rules and section in ("good", "bad"):
                rules[-1][section + "_fences"] += 1
            continue
        m = RULE_RE.match(line)
        if m:
            rules.append({"n": int(m.group(1)), "line": no, "checked": False, "level_ok": False, "bullets": 0,
                          "order": [], "good_fences": 0, "bad_fences": 0})
            section = "head"
            continue
        if not rules:
            continue
        cur = rules[-1]
        if line.startswith("## Good Example"):
            cur["order"].append("good")
            section = "good"
        elif line.startswith("## Bad Example"):
            cur["order"].append("bad")
            section = "bad"
        elif line.startswith("#"):
            out.append(viol(name, f, no, "RULE-HEADING", f"規則內出現未預期的標題：{line[:30]}",
                            "規則內只能有 `## Good Example` 與 `## Bad Example`"))
        elif not cur["checked"] and line.strip():
            cur["checked"] = True
            cur["level_ok"] = bool(LEVEL_RE.match(line))
        elif section == "head" and line.startswith("- "):
            cur["bullets"] += 1
    for idx, r in enumerate(rules, 1):
        if r["n"] != idx:
            out.append(viol(name, f, r["line"], "RULE-NUMBER", f"Rule 編號是 {r['n']}，應為 {idx}", "Rule 編號從 1 連續遞增"))
        if not r["level_ok"]:
            out.append(viol(name, f, r["line"], "RULE-LEVEL", f"Rule {r['n']} 的標題下一行不是「- Level: `MUST|SHOULD|MAY`」",
                            "標題下方緊接 Level 欄位，值只能是 MUST、SHOULD、MAY"))
        if r["bullets"] < 1:
            out.append(viol(name, f, r["line"], "RULE-BULLETS", f"Rule {r['n']} 在 Level 之後沒有規則描述條列", "補上以「- 」開頭的規則描述"))
        if r["order"] != ["good", "bad"]:
            out.append(viol(name, f, r["line"], "RULE-EXAMPLES", f"Rule {r['n']} 的 Example 區塊不是依序的 Good 與 Bad：{r['order']}",
                            "依序補上 `## Good Example` 與 `## Bad Example`"))
        for kind, key in (("Good", "good_fences"), ("Bad", "bad_fences")):
            if r[key] < 1:
                out.append(viol(name, f, r["line"], "RULE-EXAMPLES", f"Rule {r['n']} 的 {kind} Example 沒有 fenced 示範本體",
                                "示範本體要用 fenced code block 包起來"))


def placeholders_of(text):
    return {label: len(rx.findall(text)) for label, rx in PLACEHOLDERS.items()}


def check_templates(skill, out):
    name = skill["name"]
    groups = {}
    for p in skill["parts"]["templates"]:
        stem, _, rest = p.name.partition(".")
        groups.setdefault(stem, {"skeleton": [], "example": []})["example" if rest.startswith("example.") else "skeleton"].append(p)
    for stem, g in sorted(groups.items()):
        loc = f"templates/{stem}"
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", stem):
            out.append(viol(name, loc, 1, "TPL-NAME", f"樣板名字「{stem}」不是 kebab-case 小寫英文", "改用主題命名的 kebab-case，不含編號"))
        if len(g["skeleton"]) != 1 or len(g["example"]) != 1:
            out.append(viol(name, loc, 1, "TPL-PAIR", f"樣板「{stem}」的骨架有 {len(g['skeleton'])} 個、範例有 {len(g['example'])} 個",
                            "每份樣板要有一個骨架與一個範例：<名字>.<格式> 與 <名字>.example.<格式>"))
            continue
        sk, ex = g["skeleton"][0], g["example"][0]
        if sk.suffix != ex.suffix:
            out.append(viol(name, rel(skill, ex), 1, "TPL-EXT", f"骨架副檔名 {sk.suffix}，範例副檔名 {ex.suffix}", "骨架與範例使用相同且真實的副檔名"))
        try:
            sk_text, ex_text = read_text(sk), read_text(ex)
        except UnicodeDecodeError:
            continue
        used = {k: v for k, v in placeholders_of(sk_text).items() if v}
        if len(used) > 1:
            out.append(viol(name, rel(skill, sk), 1, "TPL-PLACEHOLDER", f"骨架混用了多種填位符號格式：{', '.join(used)}", "整份骨架統一使用一種格式"))
        elif not used:
            out.append(viol(name, rel(skill, sk), 1, "TPL-PLACEHOLDER", "骨架裡找不到任何填位符號（{{名稱}} 或 [[名稱]]）", "在要填寫的位置放上填位符號"))
        for label in used or PLACEHOLDERS:
            for no, line in enumerate(ex_text.splitlines(), 1):
                if PLACEHOLDERS[label].search(line):
                    out.append(viol(name, rel(skill, ex), no, "TPL-RESIDUAL", f"範例殘留填位符號：{line.strip()[:40]}", "把填位符號換成實際內容"))


def mask_strings(text):
    """把字串與註解的內容換成空白（長度與換行不變），找語法的比對才不會誤中說明文字。"""
    skip = {tokenize.STRING, tokenize.COMMENT}
    skip.update(getattr(tokenize, n) for n in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END") if hasattr(tokenize, n))
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    chars = list(text)
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type in skip:
                start = offsets[tok.start[0] - 1] + tok.start[1]
                end = offsets[tok.end[0] - 1] + tok.end[1]
                for i in range(start, end):
                    if chars[i] != "\n":
                        chars[i] = " "
    except (tokenize.TokenError, SyntaxError):
        return text
    return "".join(chars)


def call_args(text, start):
    """回傳 text[start] 這個左括號對應的括號內文字，粗略處理字串與巢狀括號。"""
    depth, i, quote = 0, start, None
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
        i += 1
    return text[start + 1:]


def check_script(skill, path: Path, siblings, out, warn):
    name, f = skill["name"], rel(skill, path)
    try:
        text = read_text(path)
    except UnicodeDecodeError:
        out.append(viol(name, f, 1, "SCRIPT-ENCODING", "腳本不是 UTF-8 文字檔", "改存成 UTF-8"))
        return

    def line_of(index):
        return text.count("\n", 0, index) + 1

    code = mask_strings(text)
    stem = path.stem
    if not re.fullmatch(r"[a-z][a-z0-9_]*", stem) or stem in sys.stdlib_module_names:
        out.append(viol(name, f, 1, "SCRIPT-NAME", f"腳本名字「{stem}」不是 snake_case，或與標準庫模組同名", "以職責命名，使用 snake_case，不與標準庫同名"))
    if text.startswith("#!"):
        out.append(viol(name, f, 1, "SCRIPT-SHEBANG", "腳本有 shebang", "刪除 shebang，腳本由 uv run 啟動"))
    block = re.search(r"^# /// script\s*\n((?:#.*\n)*?)# ///\s*$", text, re.M)
    has_deps = False
    if not block:
        out.append(viol(name, f, 1, "SCRIPT-PEP723", "腳本開頭沒有 PEP 723 `# /// script` 區塊", "補上含 requires-python 與 dependencies 的區塊"))
    else:
        body = "\n".join(ln[2:] if ln.startswith("# ") else ln[1:] for ln in block.group(1).splitlines())
        if not re.search(r"^requires-python\s*=", body, re.M):
            out.append(viol(name, f, line_of(block.start()), "SCRIPT-PEP723", "PEP 723 區塊沒有 requires-python", "補上 requires-python = \">=3.11\""))
        deps = re.search(r"^dependencies\s*=\s*\[(.*?)\]", body, re.M | re.S)
        if not deps:
            out.append(viol(name, f, line_of(block.start()), "SCRIPT-PEP723", "PEP 723 區塊沒有 dependencies", "補上 dependencies，沒有套件時寫 []"))
        else:
            has_deps = bool(deps.group(1).strip())
    if "argparse" not in code or "ArgumentParser(" not in code:
        out.append(viol(name, f, 1, "SCRIPT-ARGPARSE", "腳本沒有使用 argparse", "用 argparse 建立命令列介面並提供 --help"))
    for pattern, label in ((r"os\.system\(", "os.system"), (r"shell\s*=\s*True", "subprocess 的 shell 旗標"), (r"(?<![\w.])input\(", "互動式輸入")):
        for m in re.finditer(pattern, code):
            out.append(viol(name, f, line_of(m.start()), "SCRIPT-SHELL", f"腳本使用了 {label}", "改用 pathlib、shutil 與 subprocess 清單形式；不可等待使用者輸入"))
    for m in re.finditer(r"(?<![\w.])open\(|\.read_text\(|\.write_text\(", code):
        args = call_args(text, m.end() - 1)
        if "encoding" in args:
            continue
        if m.group(0).startswith("open") and re.search(r"""['"][rwax+]*b[rwax+]*['"]""", args):
            continue
        out.append(viol(name, f, line_of(m.start()), "SCRIPT-ENCODING", f"讀寫檔案沒有明確指定 encoding：{m.group(0)}…",
                        "讀外部檔用 encoding=\"utf-8-sig\"，寫出用 encoding=\"utf-8\" 並加 newline=\"\\n\""))
    if not re.search(r"reconfigure\(\s*encoding\s*=", text):  # encoding 的值是字串，用原文比對
        out.append(viol(name, f, 1, "SCRIPT-STDOUT", "腳本沒有把 stdout 與 stderr 重設為 UTF-8", "main() 開頭呼叫 sys.stdout.reconfigure(encoding=\"utf-8\")，stderr 同樣處理"))
    for other in siblings:
        if other != stem and re.search(rf"^\s*(?:from|import)\s+{re.escape(other)}\b", code, re.M):
            out.append(viol(name, f, 1, "SCRIPT-IMPORT", f"腳本 import 了同目錄的 {other}", "腳本之間不互相 import，需要相同邏輯時各自保留一份"))
    if has_deps and "ModuleNotFoundError" not in code:
        out.append(viol(name, f, 1, "SCRIPT-DEPS-HINT", "有第三方套件，但沒有缺套件提示", "用 try/except ModuleNotFoundError 包住 import，提示改用 uv run 並以退出碼 2 結束"))
    writes = re.search(r"\.write_text\(|\.write_bytes\(|\.unlink\(|shutil\.(?:copy|move|rmtree)", code) or any(
        re.search(r"""['"][wax]""", call_args(text, m.end() - 1)) for m in re.finditer(r"(?<![\w.])open\(", code))
    if writes and ("--force" not in text or "--dry-run" not in text):
        warn.append(viol(name, f, 1, "SCRIPT-WRITE-GUARD", "腳本會寫入檔案，但沒有同時提供 --force 與 --dry-run", "預設不覆寫既有檔案，並提供 --force 與 --dry-run"))


def check_skill(skill):
    out, warn = [], []
    name = skill["name"]
    if skill["unclosed"]:
        out.append(viol(name, "SKILL.md", len(skill["lines"]), "SOP-FENCE", "SKILL.md 有 fenced code block 沒有關閉", "補上結尾 fence"))
    check_frontmatter(skill, out, warn)
    check_sop(skill, out, warn)
    for p in skill["parts"]["rules"]:
        check_rule_file(skill, p, out)
    check_templates(skill, out)
    stems = {p.stem for p in skill["parts"]["scripts"]}
    for p in skill["parts"]["scripts"]:
        check_script(skill, p, stems, out, warn)
    for p in skill["parts"]["extras"]:
        out.append(viol(name, rel(skill, p), 1, "SCRIPT-PROJECT-FILE", f"scripts/ 底下有專案檔或環境：{p.name}",
                        "刪除；腳本是獨立單檔，套件只寫在 PEP 723 區塊"))
    return out, warn


# ---------------------------------------------------------------- 施工紀錄與藍圖追溯

def sections_of(lines, kinds):
    heads = [(i, lines[i][3:].strip()) for i in range(len(lines)) if kinds[i] == "text" and lines[i].startswith("## ")]
    spans = {}
    for k, (i, title) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        spans[title] = (i + 1, end)
    return spans


def table_rows(lines, kinds, span):
    rows = []
    for i in range(*span):
        line = lines[i].strip()
        if kinds[i] == "text" and line.startswith("|"):
            rows.append((i + 1, [c.strip() for c in line.strip("|").split("|")]))
    return rows[0] if rows else None, rows[2:]


def parse_blueprint(text):
    lines = text.splitlines()
    kinds, _ = scan_fences(lines)
    spans = sections_of(lines, kinds)
    bp = {"title": "", "expectations": set(), "header": None, "rows": [], "plan": {}, "scope": "", "walk_only": ""}
    for line in lines:
        m = re.match(r"^# 藍圖 - (.+)$", line)
        if m:
            bp["title"] = m.group(1).strip()
            break
    if "預期" in spans:
        for i in range(*spans["預期"]):
            m = re.match(r"^- E(\d+)[：:]", lines[i])
            if kinds[i] == "text" and m:
                bp["expectations"].add(f"E{m.group(1)}")
    if "處置範圍" in spans:
        for i in range(*spans["處置範圍"]):
            m = re.match(r"^- 範圍[：:](.+)$", lines[i])
            if kinds[i] == "text" and m:
                bp["scope"] = m.group(1).strip()
            m = re.match(r"^- 僅走查[：:](.+)$", lines[i])
            if kinds[i] == "text" and m:
                bp["walk_only"] = m.group(1).strip()
    if "處置" in spans:
        head, data = table_rows(lines, kinds, spans["處置"])
        bp["header"] = head[1] if head else None
        for no, cells in data:
            bp["rows"].append({"line": no, "cells": cells})
    if "複雜度" in spans:
        _, data = table_rows(lines, kinds, spans["複雜度"])
        for _, cells in data:
            m = re.match(r"\D{0,3}(\d+)", cells[2]) if len(cells) == 3 else None
            if m:
                bp["plan"][cells[0]] = int(m.group(1))
    return bp


def parse_diagnosis(text):
    lines = text.splitlines()
    kinds, _ = scan_fences(lines)
    spans = sections_of(lines, kinds)
    ids = {"E": set(), "RC": set(), "N": set(), "GUESS": set(), "SCOPE": []}
    for title, key, pattern in (("預期", "E", r"^- E(\d+)[：:]"), ("不可退化清單", "N", r"^- N(\d+)[：:]")):
        if title in spans:
            for i in range(*spans[title]):
                m = re.match(pattern, lines[i])
                if kinds[i] == "text" and m:
                    ids[key].add(f"{key}{m.group(1)}")
    current = None
    for i, line in enumerate(lines):
        m = re.match(r"^- 根因[：:]RC(\d+)", line)
        if kinds[i] == "text" and m:
            current = f"RC{m.group(1)}"
            ids["RC"].add(current)
        m = re.match(r"^- 證據等級[：:](.*)$", line)
        if kinds[i] == "text" and m and current:
            if "推測" in m.group(1):
                ids["GUESS"].add(current)
            current = None
    if "走查範圍" in spans:
        for i in range(*spans["走查範圍"]):
            m = re.match(r"^- ([^：:]+)[：:](.*)$", lines[i])
            if kinds[i] == "text" and m:
                ids["SCOPE"].append((m.group(1).strip(), re.findall(r"`([^`]+)`", m.group(2))))
    return ids


def collect_runs(runs_dir: Path):
    runs = []
    if not runs_dir.is_dir():
        return runs
    for d in sorted(runs_dir.iterdir()):
        bp_file = d / "blueprint.md"
        if not (d.is_dir() and bp_file.is_file()):
            continue
        bp = parse_blueprint(read_text(bp_file))
        skills = {s.strip() for s in re.split(r"[、,，]", bp["title"]) if s.strip()}
        pending = 0
        for r in bp["rows"]:
            if len(r["cells"]) == len(BLUEPRINT_HEADER):
                skills.add(r["cells"][1].split("/")[0])
                pending += r["cells"][6] == "待辦"
        runs.append({"folder": d.name, "path": d.as_posix(), "skills": sorted(skills), "pending_rows": pending})
    return runs


def check_run(run_dir: Path, root: Path, skills, names, out, warn):
    bp_file, dg_file, baseline = run_dir / "blueprint.md", run_dir / "diagnosis.md", run_dir / "baseline"
    bp = parse_blueprint(read_text(bp_file))
    ids = {"E": set(bp["expectations"]), "RC": set(), "N": set(), "GUESS": set()}
    optimize = dg_file.is_file() or baseline.is_dir()
    scope_files = []
    if dg_file.is_file():
        d = parse_diagnosis(read_text(dg_file))
        ids["E"] |= d["E"]
        ids["RC"], ids["N"], ids["GUESS"] = d["RC"], d["N"], d["GUESS"]
        scope_files = d["SCOPE"]
    known = ids["E"] | ids["RC"] | ids["N"]
    f = "blueprint.md"
    if bp["header"] != BLUEPRINT_HEADER:
        out.append(viol("(run)", f, 1, "RUN-TABLE", f"處置表頭不是 {' | '.join(BLUEPRINT_HEADER)}", "依藍圖樣板的表頭修正"))
    covered = set()
    listed = set()
    for r in bp["rows"]:
        cells, no = r["cells"], r["line"]
        if len(cells) != len(BLUEPRINT_HEADER):
            out.append(viol("(run)", f, no, "RUN-TABLE", f"處置列的欄數是 {len(cells)}，應為 {len(BLUEPRINT_HEADER)}", "補齊或刪除多餘的欄位"))
            continue
        n, loc, _, action, basis, conf, status = cells
        for label, value, allowed in (("處置", action, ACTIONS), ("確度", conf, CONFIDENCE), ("狀態", status, STATUSES)):
            if value not in allowed:
                out.append(viol("(run)", f, no, "RUN-VALUE", f"第 {n} 列的{label}「{value}」不在 {'、'.join(allowed)} 之內", f"{label}只能填 {'、'.join(allowed)}"))
        if status == "待辦":
            out.append(viol("(run)", f, no, "RUN-STATUS", f"第 {n} 列還是待辦", "完成施工並核對後改為已完成，或回到閘門 2 調整藍圖"))
        elif action == "保留" and status != "無需施工":
            out.append(viol("(run)", f, no, "RUN-STATUS", f"第 {n} 列處置是保留，狀態應為無需施工", "把狀態改為無需施工"))
        elif action in ("改寫", "刪除", "新增") and status == "無需施工":
            out.append(viol("(run)", f, no, "RUN-STATUS", f"第 {n} 列處置是{action}，狀態不可為無需施工", "完成施工後改為已完成"))
        tokens = ID_RE.findall(basis)
        if not tokens:
            out.append(viol("(run)", f, no, "RUN-EVIDENCE", f"第 {n} 列的依據欄沒有 RC#、E#、N#、「使用者指定」或「無舉證」", "補上依據編號"))
        for t in tokens:
            if t not in ("無舉證", "使用者指定") and t not in known:
                out.append(viol("(run)", f, no, "RUN-EVIDENCE", f"第 {n} 列的依據 {t} 在診斷單與藍圖的預期中找不到", "改成存在的編號"))
            elif t in ids["GUESS"]:
                out.append(viol("(run)", f, no, "RUN-EVIDENCE", f"第 {n} 列的依據 {t} 的證據等級是推測，推測的根因不進藍圖", "補證據讓它升為高度可能，或拿掉這一列"))
        if "無舉證" in tokens and action != "刪除":
            out.append(viol("(run)", f, no, "RUN-EVIDENCE", f"第 {n} 列的依據是無舉證，但處置是{action}", "無舉證只能搭配刪除；要保留或改寫須寫出依據"))
        if "使用者指定" in tokens and action != "保留":
            out.append(viol("(run)", f, no, "RUN-EVIDENCE", f"第 {n} 列的依據是使用者指定，但處置是{action}", "使用者指定只能搭配保留，表示閘門 2 使用者要求保留這個元素"))
        if action in ("改寫", "刪除", "新增"):
            covered.update(t for t in tokens if t.startswith("RC"))
        if action == "新增" and not any(t.startswith("RC" if optimize else "E") for t in tokens):
            out.append(viol("(run)", f, no, "RUN-NEW-NO-RC", f"第 {n} 列是新增，但依據沒有{'根因 RC#' if optimize else '預期 E#'}",
                            "沒有根因的新增是疊床架屋，補上依據或刪除該列"))
        skill_name, _, path = loc.partition("/")
        base = path.split("#")[0]
        whole_file = "#" not in path
        skill_dir = root / skill_name
        if base:
            listed.add((skill_name, base))
        if not skill_dir.is_dir() and action != "刪除":
            out.append(viol("(run)", f, no, "RUN-FILE-MISSING", f"第 {n} 列的 skill「{skill_name}」在 {root.as_posix()} 底下不存在", "確認位置的格式是 <skill 名稱>/<部位路徑>"))
        elif base and base != "SKILL.md":
            exists = (skill_dir / base).exists()
            if action == "刪除" and exists and whole_file:
                out.append(viol("(run)", f, no, "RUN-FILE-STILL-EXISTS", f"第 {n} 列要刪除的 {loc} 還存在", "刪除該檔（先確認 SOP 已不引用）；檔內單條的刪除，位置要寫到該條，用規則標題（<檔案>#<規則標題>）"))
            elif action != "刪除" and not exists:
                out.append(viol("(run)", f, no, "RUN-FILE-MISSING", f"第 {n} 列的 {loc} 不存在", "完成該列的施工，或修正位置"))
            if action == "刪除" and whole_file and baseline.is_dir() and not (baseline / skill_name / base).exists():
                warn.append(viol("(run)", f, no, "RUN-BASELINE", f"第 {n} 列刪除的 {loc} 在 baseline 沒有複本，無法還原", "確認該檔是否為新建後才刪除"))
    # 處置範圍內的每個部位檔都要有處置列（預設刪除、舉證保留，不能漏列）
    def part_paths(skill):
        return [rel(skill, p) for p in skill["parts"]["rules"] + skill["parts"]["templates"] + skill["parts"]["scripts"]]

    def scoped_skill(n):
        old = baseline / n
        return load_skill(old) if (old / "SKILL.md").is_file() else skills.get(n)

    expected = set()
    if "新建" not in bp["scope"]:
        if "整個 skill" in bp["scope"]:
            for n in names:
                if scoped_skill(n):
                    expected.update((n, p) for p in part_paths(scoped_skill(n)))
        else:
            for n, tokens in scope_files:
                if not scoped_skill(n):
                    continue
                paths = part_paths(scoped_skill(n))
                for tok in tokens:
                    hits = [tok] if tok in paths else [p for p in paths if p.endswith("/" + tok)]
                    if len(hits) == 1:
                        expected.add((n, hits[0]))
    walk_only = bp["walk_only"]
    expected = {(n, p) for n, p in expected if not (walk_only and (n in walk_only or p in walk_only))}
    for n, p in sorted(expected - listed):
        out.append(viol("(run)", f, 1, "RUN-SCOPE-UNLISTED", f"處置範圍內的 {n}/{p} 沒有任何處置列", "為它補一列：預設刪除，要保留須寫出依據（E#、N# 或使用者指定）"))
    for rc in sorted(ids["RC"] - ids["GUESS"] - covered):
        out.append(viol("(run)", f, 1, "RUN-RC-UNCOVERED", f"診斷單的根因 {rc} 沒有任何改寫、刪除或新增的處置列依據它", "為它補一列處置，或回到診斷單說明為何不是根因"))

    def total(source):
        acc = {key: 0 for _, key in ITEMS}
        for n in names:
            if source == "after":
                skill = skills.get(n)
            else:
                skill = load_skill(baseline / n) if (baseline / n / "SKILL.md").is_file() else None
            if skill:
                for key, value in complexity(skill).items():
                    if key in acc:
                        acc[key] += value
        return acc

    before, after = total("before"), total("after")
    table = []
    for label, key in ITEMS:
        planned = bp["plan"].get(label)
        table.append({"item": label, "before": before[key], "after": after[key], "planned_after": planned})
        if after[key] > before[key]:
            warn.append(viol("(run)", f, 1, "RUN-GROWTH", f"{label}由 {before[key]} 增加為 {after[key]}", "確認增加的部分都能指到根因（驗收規範的語意完成條件）"))
        if planned is not None and planned != after[key]:
            warn.append(viol("(run)", f, 1, "RUN-PLAN", f"{label}藍圖預估 {planned}，實際 {after[key]}", "更新藍圖的複雜度表，或確認為何與預估不同"))
    return {"folder": run_dir.as_posix(), "mode": "優化" if optimize else "新建", "rows": len(bp["rows"]),
            "skills": names, "complexity": table}


# ---------------------------------------------------------------- 指令

def emit(result, args, summary):
    if not args.output:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return
    out = Path(args.output)
    note = {"output": out.as_posix(), **summary}
    if args.dry_run:
        print(json.dumps({"dry_run": True, "would_write": out.as_posix(), **summary}, ensure_ascii=False))
        return
    if out.exists() and not args.force:
        raise CannotRun(f"輸出檔 {out.as_posix()} 已存在。要覆寫請加 --force，或換一個檔名。")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(note, ensure_ascii=False))


def need_dir(path_text, what):
    p = Path(path_text)
    if not p.is_dir():
        raise CannotRun(f"找不到 {what}：{p.as_posix()}。請確認路徑是否為存在的資料夾。")
    return p


def cmd_list(args):
    root = need_dir(args.skills_root, "skills 根目錄")
    skills = load_all(root)
    if not skills:
        raise CannotRun(f"{root.as_posix()} 底下沒有任何含 SKILL.md 的 skill 資料夾。")
    delegates, called_by = relations(skills)
    runs_dir = Path(args.runs_dir) if args.runs_dir else root.parent / "engineering-runs"
    runs = collect_runs(runs_dir)
    items = []
    for name, s in skills.items():
        c = complexity(s)
        item = {"name": name, "dir": s["dir"].as_posix(), "description": s["fm"].get("description", ""),
                "has_sop": s["sop"]["found"], **c, "delegates_to": delegates[name], "called_by": called_by[name],
                "past_runs": [{"folder": r["folder"], "pending_rows": r["pending_rows"]} for r in runs if name in r["skills"]]}
        if s["fm"].get("name") not in (None, name):
            item["frontmatter_name"] = s["fm"]["name"]
        items.append(item)
    result = {"skills_root": root.as_posix(), "runs_dir": runs_dir.as_posix(), "skills": items,
              "unfinished_runs": [r["path"] for r in runs if r["pending_rows"]]}
    emit(result, args, {"skills": len(items), "unfinished_runs": len(result["unfinished_runs"])})
    return 0


def issue_key(x):
    """施工前後是不是同一則違規：訊息裡的行號會因插入或刪除 step 而位移，比對前先抹掉。"""
    return (x["skill"], x["file"], x["code"], re.sub(r"第 [\d, ]+ 行", "第 N 行", x["problem"]))


def cmd_check(args):
    root = need_dir(args.skills_root, "skills 根目錄")
    skills = load_all(root)
    names = list(args.skills)
    run_dir = None
    if args.run:
        run_dir = need_dir(args.run, "施工紀錄資料夾")
        if not (run_dir / "blueprint.md").is_file():
            raise CannotRun(f"{run_dir.as_posix()} 底下沒有 blueprint.md，不是施工紀錄資料夾。")
        if not names:
            bp = parse_blueprint(read_text(run_dir / "blueprint.md"))
            inferred = {s.strip() for s in re.split(r"[、,，]", bp["title"]) if s.strip()}
            inferred |= {r["cells"][1].split("/")[0] for r in bp["rows"] if len(r["cells"]) == len(BLUEPRINT_HEADER)}
            names = sorted(n for n in inferred if n in skills)
    if not names:
        raise CannotRun("沒有指定要檢查的 skill。請在 skills 根目錄後面寫出 skill 名稱，或加 --run 由藍圖推得。")
    for n in names:
        if n not in skills:
            raise CannotRun(f"找不到 skill「{n}」：{(root / n / 'SKILL.md').as_posix()} 不存在。現有的 skill：{', '.join(sorted(skills))}")
    delegates, called_by = relations(skills)
    violations, warnings, summary, pre_existing = [], [], [], []
    for n in names:
        v, w = check_skill(skills[n])
        if run_dir and (run_dir / "baseline" / n / "SKILL.md").is_file():
            old_v, _ = check_skill(load_skill(run_dir / "baseline" / n))
            old = {issue_key(x) for x in old_v}
            pre_existing += [x for x in v if issue_key(x) in old]
            v = [x for x in v if issue_key(x) not in old]
        violations += v
        warnings += w
        s = skills[n]
        summary.append({"name": n, "complexity": complexity(s), "delegates_to": delegates[n], "called_by": called_by[n],
                        "phases": [{"n": p["n"], "title": p["title"], "steps": len(p["steps"])} for p in s["sop"]["phases"]]})
    result = {"skills": summary}
    if run_dir:
        run_violations, run_warnings = [], []
        result["run"] = check_run(run_dir, root, skills, names, run_violations, run_warnings)
        violations += run_violations
        warnings += run_warnings
    result["violations"] = cap(violations)
    result["warnings"] = cap(warnings)
    if run_dir:
        result["pre_existing"] = cap(pre_existing)
    if len(violations) > MAX_ITEMS or len(warnings) > MAX_ITEMS:
        result["truncated"] = {"violations": len(violations), "warnings": len(warnings), "shown_each": MAX_ITEMS}
    emit(result, args, {"violations": len(violations), "warnings": len(warnings), "pre_existing": len(pre_existing)})
    return 1 if violations and not args.report_only else 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    fmt = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=fmt)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--output", help="把完整結果寫成 JSON 檔，stdout 只留摘要")
        p.add_argument("--force", action="store_true", help="覆寫已存在的輸出檔")
        p.add_argument("--dry-run", action="store_true", help="只列出會寫入的檔案，不實際寫入")

    p_list = sub.add_parser("list", help="盤點所有 skill", formatter_class=fmt)
    p_list.add_argument("skills_root", help="skills 根目錄")
    p_list.add_argument("--runs-dir", help="施工紀錄根目錄，預設為 skills 根目錄上一層的 engineering-runs；不存在時視為沒有紀錄")
    common(p_list)
    p_check = sub.add_parser("check", help="檢查 skill 的結構違規與複雜度", formatter_class=fmt)
    p_check.add_argument("skills_root", help="skills 根目錄")
    p_check.add_argument("skills", nargs="*", help="要檢查的 skill 名稱")
    p_check.add_argument("--run", help="施工紀錄資料夾，加上時另核對藍圖追溯與複雜度前後對照，並把施工前就有的既有違規另列為 pre_existing")
    p_check.add_argument("--report-only", action="store_true", help="只回報，不以退出碼判定：有違規也以退出碼 0 結束（診斷階段用）")
    common(p_check)
    args = parser.parse_args()
    return cmd_list(args) if args.command == "list" else cmd_check(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CannotRun as e:
        print(f"[無法執行] {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"[無法執行] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
