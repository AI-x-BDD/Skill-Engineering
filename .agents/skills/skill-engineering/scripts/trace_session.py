# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""從 Claude Code 的對話紀錄（.jsonl）整理 skill 呼叫鏈、載入過的檔案與使用者的訊息。

用法：
    uv run trace_session.py list [--projects-dir <資料夾>] [--all-projects] [--limit N]
    uv run trace_session.py trace <對話紀錄路徑或 session id> [--projects-dir <資料夾>] [--max-chars N] [--ai-chars N]

list   列出近期的對話（id、標題、時間、第一則訊息、用過的 skill），供指認問題發生的是哪一份
trace  整理單一對話：使用者的訊息與每則訊息之前的 AI 回覆（使用者通常是針對它更正）、對話最後一則 AI 回覆、
       skill 呼叫鏈、各 skill 自己的檔案何時被載入、其他載入的檔案、AI 寫入的檔案（含寫入內容的開頭，使用者事後改掉的內容也查得到）與 agent 呼叫

--projects-dir 預設為目前工作目錄對應的 ~/.claude/projects/<專案>。對話紀錄是 Claude Code 的
內部格式，無法辨識時請使用者直接貼出對話內容。輸出較大時加 --output <檔案> 寫成完整 JSON，
stdout 只留摘要；已存在的檔案要加 --force 才會覆寫，--dry-run 只列出會寫入的檔案。

退出碼：
    0  成功
    2  無法執行（找不到對話、格式無法辨識等，原因寫在 stderr）
"""
import argparse
import json
import re
import sys
from pathlib import Path

SKILL_PATH_RE = re.compile(r"(?:^|/)skills/([^/]+)/(.+)$")
BASE_DIR_RE = re.compile(r"^Base directory for this skill:\s*(.+?)\s*$", re.M)
COMMAND_NAME_RE = re.compile(r"<command-name>\s*/?([^<\s]+)\s*</command-name>")
COMMAND_ARGS_RE = re.compile(r"<command-args>(.*?)</command-args>", re.S)
COMPACT_PREFIX = "This session is being continued from a previous conversation"
AGENT_TOOLS = ("Agent", "Task")
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


class CannotRun(Exception):
    """無法執行的情況，訊息寫到 stderr 並以退出碼 2 結束。"""


# ---------------------------------------------------------------- 基本工具

def norm(path: str) -> str:
    return path.replace("\\", "/")


def short_time(ts):
    return ts[:19] + "Z" if isinstance(ts, str) and len(ts) >= 19 else ts


def trim(text, limit):
    text = text.strip()
    if not limit or len(text) <= limit:
        return text
    return text[:limit] + f"…(+{len(text) - limit} 字)"


def squeeze(items, head, tail, marker):
    if len(items) <= head + tail:
        return items
    return items[:head] + [marker(len(items) - head - tail)] + items[-tail:]


def default_projects_dir() -> Path:
    encoded = re.sub(r"[^A-Za-z0-9]", "-", str(Path.cwd()))
    return Path.home() / ".claude" / "projects" / encoded


def read_events(path: Path):
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as e:
        raise CannotRun(f"讀不了 {path.as_posix()}（{type(e).__name__}）。請確認它是 UTF-8 的 .jsonl 對話紀錄。")
    events, bad = [], 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if isinstance(obj, dict):
            events.append(obj)
        else:
            bad += 1
    return events, bad


# ---------------------------------------------------------------- 解析對話

def parse_session(path: Path):
    events, bad = read_events(path)
    if not any(e.get("type") in ("user", "assistant") for e in events):
        raise CannotRun(
            f"{path.as_posix()} 不像 Claude Code 的對話紀錄：可解析 {len(events)} 行、無法解析 {bad} 行，"
            "找不到 user 或 assistant 行。請請使用者直接貼出對話內容。")
    results = {}
    for ev in events:
        content = (ev.get("message") or {}).get("content") if ev.get("type") == "user" else None
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    results[b.get("tool_use_id")] = not b.get("is_error", False)

    s = {"id": path.stem, "file": path.as_posix(), "size_kb": path.stat().st_size // 1024, "title": None,
         "cwd": None, "version": None, "started": None, "ended": None, "bad_lines": bad, "compactions": 0,
         "messages": [], "calls": [], "loads": [], "writes": [], "agents": [], "mentions": [], "timeline": []}
    state = {"seq": 0, "active": None, "command": None, "ai_text": None}
    by_id = {}

    def add_event(ts, text):
        state["seq"] += 1
        s["timeline"].append(f"#{state['seq']} {short_time(ts)} {text}")
        return state["seq"]

    def owner_of(file_path):
        low = file_path.casefold()
        for call in reversed(s["calls"]):
            d = call["dir"]
            if d and low.startswith(d.casefold().rstrip("/") + "/"):
                return call["skill"], file_path[len(d.rstrip("/")) + 1:]
        m = SKILL_PATH_RE.search(file_path)
        return (m.group(1), m.group(2)) if m else (None, None)

    def new_call(name, via, ts, args, tool_use_id):
        call = {"seq": add_event(ts, f"呼叫 skill {name}（{via}）"), "skill": name, "via": via, "time": short_time(ts),
                "after_message": len(s["messages"]), "args": args or None, "dir": None}
        s["calls"].append(call)
        by_id[tool_use_id] = call
        state["active"] = name
        return call

    def add_load(file_path, ts, how, tool_use_id):
        file_path = norm(file_path)
        owner, rel = owner_of(file_path)
        ok = results.get(tool_use_id) if tool_use_id else True
        tag = f" [{owner}]" if owner else ""
        fail = " 失敗" if ok is False else ""
        seq = add_event(ts, f"{'讀取' if how == 'read' else '附件'} {file_path}{tag}{fail}")
        s["loads"].append({"seq": seq, "path": file_path, "rel": rel, "skill": owner, "how": how,
                           "during": state["active"], "ok": ok})

    def add_write(file_path, ts, tool, preview):
        file_path = norm(file_path)
        owner, _ = owner_of(file_path)
        seq = add_event(ts, f"寫入 {file_path}" + (f" [{owner}]" if owner else ""))
        s["writes"].append({"seq": seq, "path": file_path, "tool": tool, "preview": preview})

    def add_message(text, ts, kind):
        if text.startswith(COMPACT_PREFIX):
            s["compactions"] += 1
            add_event(ts, "對話被壓縮並續接（以下的使用者訊息不含這段摘要）")
            return
        if "<local-command-stdout>" in text or "<local-command-caveat>" in text:
            return
        cm = COMMAND_NAME_RE.search(text)
        if cm:
            am = COMMAND_ARGS_RE.search(text)
            args = am.group(1).strip() if am else ""
            state["command"] = {"name": cm.group(1), "args": args}
            kind, text = "command", f"/{cm.group(1)} {args}".strip()
        else:
            state["command"] = None
        if text.startswith("[Request interrupted"):
            kind = "interrupt"
        idx = len(s["messages"]) + 1
        s["messages"].append({"index": idx, "time": short_time(ts), "kind": kind, "text": text.strip(),
                              "during": state["active"], "ai_before": state["ai_text"]})
        state["ai_text"] = None
        add_event(ts, f"使用者[{idx}] {trim(text, 50)}")

    def on_user(ev, ts):
        content = (ev.get("message") or {}).get("content")
        if ev.get("isMeta"):
            texts = [content] if isinstance(content, str) else [
                b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text"]
            m = BASE_DIR_RE.search("\n".join(texts))
            if m:
                call = by_id.get(ev.get("sourceToolUseID"))
                if call is None and state["command"]:
                    call = new_call(state["command"]["name"], "command", ts, state["command"]["args"], None)
                    state["command"] = None
                if call is not None:
                    call["dir"] = norm(m.group(1))
            return
        if isinstance(content, str):
            add_message(content, ts, "prompt")
        elif isinstance(content, list):
            texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
            has_result = any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content)
            text = "\n".join(texts)
            if texts and not has_result and not text.lstrip().startswith("<system-reminder>"):
                add_message(text, ts, "prompt")

    def on_assistant(ev, ts):
        content = (ev.get("message") or {}).get("content")
        for b in content if isinstance(content, list) else []:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text" and (b.get("text") or "").strip():
                state["ai_text"] = b["text"]
                continue
            if b.get("type") != "tool_use":
                continue
            name, inp = b.get("name"), b.get("input") or {}
            if name == "Skill":
                args = inp.get("args")
                new_call(inp.get("skill") or "?", "tool", ts, args if isinstance(args, str) else None, b.get("id"))
            elif name == "Read" and inp.get("file_path"):
                add_load(inp["file_path"], ts, "read", b.get("id"))
            elif name in WRITE_TOOLS and (inp.get("file_path") or inp.get("notebook_path")):
                edits = inp.get("edits") if isinstance(inp.get("edits"), list) else []
                body = inp.get("content") or inp.get("new_string") or inp.get("new_source") or "\n".join(
                    str(e.get("new_string", "")) for e in edits if isinstance(e, dict))
                add_write(inp.get("file_path") or inp.get("notebook_path"), ts, name, body if isinstance(body, str) else "")
            elif name in AGENT_TOOLS:
                agent = {"seq": 0, "time": short_time(ts), "subagent_type": inp.get("subagent_type"),
                         "description": inp.get("description")}
                agent["seq"] = add_event(ts, f"委派 agent {agent['subagent_type'] or '?'}：{trim(str(agent['description'] or ''), 50)}")
                s["agents"].append(agent)

    def on_attachment(ev, ts):
        a = ev.get("attachment") or {}
        kind = a.get("type")
        if kind == "file" and a.get("filename"):
            add_load(a["filename"], ts, "attachment", None)
        elif kind == "queued_command" and a.get("prompt") and (a.get("origin") or {}).get("kind", "human") == "human":
            add_message(a["prompt"], ts, "queued")
        elif kind == "skill_mention" and a.get("skillName"):
            s["mentions"].append(a["skillName"])
            add_event(ts, f"使用者提到 skill {a['skillName']}")

    for ev in events:
        ts = ev.get("timestamp")
        if ts:
            s["started"] = s["started"] or ts
            s["ended"] = ts
        s["cwd"] = s["cwd"] or ev.get("cwd")
        s["version"] = s["version"] or ev.get("version")
        kind = ev.get("type")
        if kind == "custom-title":
            s["title"] = ev.get("customTitle") or s["title"]
        elif kind == "user":
            on_user(ev, ts)
        elif kind == "assistant":
            on_assistant(ev, ts)
        elif kind == "attachment":
            on_attachment(ev, ts)
    s["last_ai"] = state["ai_text"]
    return s


def build_trace(s, max_chars, ai_chars, full):
    skills = {}
    for c in s["calls"]:
        info = skills.setdefault(c["skill"], {"in_chain": True, "calls": [], "dir": None, "files_loaded": []})
        info["calls"].append(c["seq"])
        info["dir"] = info["dir"] or c["dir"]
    other = []
    for l in s["loads"]:
        if l["skill"]:
            info = skills.setdefault(l["skill"], {"in_chain": False, "calls": [], "dir": None, "files_loaded": []})
            entry = {"path": l["rel"], "seq": l["seq"], "during": l["during"]}
            if l["ok"] is False:
                entry["ok"] = False
            info["files_loaded"].append(entry)
        else:
            other.append({"path": l["path"], "seq": l["seq"]})
    messages = []
    for m in s["messages"]:
        item = {**m, "text": trim(m["text"], 0 if full else max_chars)}
        if item["ai_before"]:
            item["ai_before"] = trim(item["ai_before"], 0 if full else ai_chars)
        else:
            del item["ai_before"]
        messages.append(item)
    written = {}
    for w in s["writes"]:
        entry = written.setdefault(w["path"], {"path": w["path"], "count": 0, "first_seq": w["seq"], "tool": w["tool"],
                                               "preview": trim(w["preview"], 0 if full else 120)})
        entry["count"] += 1
    written = list(written.values())
    chain = []
    for c in s["calls"]:
        item = {k: v for k, v in c.items() if k != "dir"}
        if item["args"]:
            item["args"] = trim(item["args"], 0 if full else 100)
        chain.append(item)
    timeline = s["timeline"]
    if not full:
        messages = squeeze(messages, 6, 24, lambda k: {"…": f"省略 {k} 則；加 --output 取得完整內容"})
        timeline = squeeze(timeline, 40, 30, lambda k: f"…（省略 {k} 筆；加 --output 取得完整內容）")
    result = {
        "session": {k: s[k] for k in ("id", "title", "cwd", "version", "started", "ended", "file", "size_kb")},
        "counts": {"human_messages": sum(m["kind"] != "interrupt" for m in s["messages"]),
                   "interrupts": sum(m["kind"] == "interrupt" for m in s["messages"]),
                   "skill_calls": len(s["calls"]), "files_loaded": len(s["loads"]), "files_written": len(written),
                   "agent_calls": len(s["agents"]), "compactions": s["compactions"], "unparsed_lines": s["bad_lines"]},
        "user_messages": messages,
        "call_chain": chain,
        "skills": skills,
        "other_files": {"count": len(other), "first": other if full else other[:30]},
        "written_files": {"count": len(written), "first": written if full else written[:25]},
        "agent_calls": s["agents"],
        "mentioned_skills": s["mentions"],
        "timeline": timeline,
    }
    if s["last_ai"]:
        result["last_ai_reply"] = trim(s["last_ai"], 0 if full else 300)
    return result


# ---------------------------------------------------------------- 指令

def emit(result, args, summary):
    if not args.output:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return
    out = Path(args.output)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "would_write": out.as_posix(), **summary}, ensure_ascii=False))
        return
    if out.exists() and not args.force:
        raise CannotRun(f"輸出檔 {out.as_posix()} 已存在。要覆寫請加 --force，或換一個檔名。")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({"output": out.as_posix(), **summary}, ensure_ascii=False))


def session_files(args):
    if args.all_projects:
        root = Path(args.projects_dir) if args.projects_dir else Path.home() / ".claude" / "projects"
        files = list(root.glob("*/*.jsonl"))
    else:
        base = Path(args.projects_dir) if args.projects_dir else default_projects_dir()
        if not base.is_dir():
            raise CannotRun(f"找不到對話紀錄資料夾：{base.as_posix()}。可用 --projects-dir 指定，或加 --all-projects 掃描所有專案。")
        files = list(base.glob("*.jsonl"))
    if not files:
        raise CannotRun("找不到任何 .jsonl 對話紀錄。可用 --projects-dir 指定資料夾，或加 --all-projects。")
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def cmd_list(args):
    items = []
    for path in session_files(args)[:args.limit]:
        try:
            s = parse_session(path)
        except CannotRun as e:
            print(f"[略過] {path.name}：{e}", file=sys.stderr)
            continue
        names = list(dict.fromkeys(c["skill"] for c in s["calls"]))
        first = s["messages"][0]["text"] if s["messages"] else ""
        items.append({"id": s["id"], "project": path.parent.name, "title": s["title"], "started": short_time(s["started"]),
                      "ended": short_time(s["ended"]), "size_kb": s["size_kb"], "human_messages": len(s["messages"]),
                      "first_message": trim(first, 100), "skills": names, "file": s["file"]})
    emit({"sessions": items}, args, {"sessions": len(items)})
    return 0


def resolve_session(arg, args):
    p = Path(arg)
    if p.is_file():
        return p
    base = Path(args.projects_dir) if args.projects_dir else default_projects_dir()
    pools = [base.glob("*.jsonl")] if base.is_dir() else []
    pools.append((Path.home() / ".claude" / "projects").glob("*/*.jsonl"))
    for pool in pools:
        hits = sorted(f for f in pool if f.stem.startswith(arg))
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise CannotRun(f"「{arg}」對應到 {len(hits)} 份對話，請多給幾個字元：{', '.join(h.stem for h in hits[:8])}")
    raise CannotRun(f"找不到對話「{arg}」。先執行 list 看有哪些對話，再傳入完整路徑或 id 的開頭。")


def cmd_trace(args):
    path = resolve_session(args.session, args)
    s = parse_session(path)
    result = build_trace(s, args.max_chars, args.ai_chars, full=bool(args.output))
    emit(result, args, {"session": s["id"], "human_messages": len(s["messages"]), "skill_calls": len(s["calls"]),
                        "files_loaded": len(s["loads"])})
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    fmt = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=fmt)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--projects-dir", help="對話紀錄所在的資料夾，預設為目前工作目錄對應的專案")
        p.add_argument("--output", help="把完整結果寫成 JSON 檔，stdout 只留摘要")
        p.add_argument("--force", action="store_true", help="覆寫已存在的輸出檔")
        p.add_argument("--dry-run", action="store_true", help="只列出會寫入的檔案，不實際寫入")

    p_list = sub.add_parser("list", help="列出近期的對話", formatter_class=fmt)
    p_list.add_argument("--all-projects", action="store_true", help="掃描所有專案，不只目前的專案")
    p_list.add_argument("--limit", type=int, default=15, help="最多列出幾份，預設 15")
    common(p_list)
    p_trace = sub.add_parser("trace", help="整理單一對話", formatter_class=fmt)
    p_trace.add_argument("session", help="對話紀錄的路徑，或 session id 的開頭")
    p_trace.add_argument("--max-chars", type=int, default=200, help="每則使用者訊息最多顯示幾字，預設 200")
    p_trace.add_argument("--ai-chars", type=int, default=150, help="每則使用者訊息之前的 AI 回覆最多顯示幾字，預設 150")
    common(p_trace)
    args = parser.parse_args()
    return cmd_list(args) if args.command == "list" else cmd_trace(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CannotRun as e:
        print(f"[無法執行] {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"[無法執行] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
