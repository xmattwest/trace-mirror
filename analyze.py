"""OpenCode Mirror: local, read-only, deterministic working-habit analysis."""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VERSION = "0.3.3"
REMINDERS = re.compile(r"<system-reminder\b[^>]*>.*?(?:</system-reminder>|$)", re.S | re.I)
CONTINUE = re.compile(r"^(go|continue|proceed|yes|yep|ok|okay|do it|keep going|let'?s go)[.!\s]*$", re.I)
SIGNALS = {
    "question": ("Question-led", "Questions or question-opening language", re.compile(r"\?|^(?:what|why|how|where|when|which|can|could|should|is|are|do|does)\b", re.I)),
    "direction": ("Action-oriented", "Action verbs or explicit action requests", re.compile(r"\b(?:build|implement|create|fix|add|remove|update|run|make|write|start|ship|deploy|commit|push|please|i want|let'?s)\b", re.I)),
    "review": ("Review-minded", "Review, verification or revision language", re.compile(r"\b(?:review|verify|check|test|critique|correct|wrong|revise|revision|improve|refine|polish|feedback)\b", re.I)),
    "continuity": ("Continuity-minded", "Context, handoff or bounded-phase language", re.compile(r"\b(?:handoff|hand-off|resume|next session|fresh context|starting prompt|checkpoint|phase|gate|acceptance|criteria|current state)\b", re.I)),
}
COMPONENTS = ("input", "cache_read", "cache_write", "output", "reasoning")


class ArchiveError(ValueError):
    pass


def number(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return None
    try:
        return value if math.isfinite(value) and value >= 0 else None
    except OverflowError:
        return None


def exit_code(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def obj(value):
    return value if isinstance(value, dict) else {}


def parse(value):
    try:
        return obj(json.loads(value))
    except (ValueError, TypeError):
        return {}


def percentile(values, p):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower), 3)


def clean_text(text):
    return re.sub(r"\s+", " ", REMINDERS.sub("", text)).strip()


def local_time(milliseconds, zone):
    value = number(milliseconds)
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value / 1000, zone)
    except (ValueError, OSError, OverflowError):
        return None


def project_name(directory):
    if not directory:
        return "Unassigned"
    # Windows paths are interpreted consistently even on a Unix host.
    parts = re.split(r"[/\\]+", str(directory).rstrip("/\\"))
    if len(parts) <= 1:
        return "Unassigned"
    return parts[-1] or "Unassigned"


def connect_archive(path):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ArchiveError("That database was not found. Enter the path to your opencode.db.")
    try:
        connection = sqlite3.connect("file:" + quote(str(path)) + "?mode=ro", uri=True)
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required = {"session", "message", "part"}
        if not required <= tables:
            raise ArchiveError("This archive needs the OpenCode session, message and part tables. Its schema is not supported yet.")
        columns = {table: {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')} for table in required}
        for table, names in {"session": {"id"}, "message": {"id", "session_id", "data"}, "part": {"id", "message_id", "data"}}.items():
            if not names <= columns[table]:
                raise ArchiveError(f"The {table} table has an unsupported structure.")
        # Additional application tables, including credentials, are never queried.
        return connection, columns
    except (sqlite3.Error, ArchiveError) as exc:
        if "connection" in locals():
            connection.close()
        if isinstance(exc, ArchiveError):
            raise
        raise ArchiveError("This file could not be read as an OpenCode SQLite database.") from exc


def assess(signals, count, median_length, delegation_roots):
    rates = {name: round(value / count * 100, 1) if count else 0 for name, value in signals.items()}
    scores = {
        "The Investigator": rates.get("question", 0) + rates.get("review", 0) * .4,
        "The Builder": rates.get("direction", 0) + rates.get("continuation", 0) * .25,
        "The Systems Thinker": rates.get("continuity", 0) * 1.5 + rates.get("detail", 0) * .5 + rates.get("review", 0) * .4,
        "The Orchestrator": delegation_roots * 1.5 + rates.get("continuity", 0) * .4,
        "The Editor": rates.get("review", 0) * 1.4 + rates.get("detail", 0) * .25,
    }
    persona = max(scores, key=scores.get) if count >= 20 else "An Early Sketch"
    descriptions = {
        "The Investigator": "You lead with questions, then use the conversation to sharpen what you know.",
        "The Builder": "You turn conversation into motion. Your strongest signal is asking for concrete action.",
        "The Systems Thinker": "You give work a structure: specifications, checkpoints, review, and a way to pick it up again.",
        "The Orchestrator": "You spread work across agents and bring the pieces back together.",
        "The Editor": "You keep returning to the quality of the result: checking, refining, and asking for another pass.",
        "An Early Sketch": "A few more conversations will give this mirror a clearer outline. Explore the measured activity below.",
    }
    if not count:
        communication = "Still taking shape"
    elif rates.get("detail", 0) >= 25 or median_length >= 700:
        communication = "Detailed specifier"
    elif rates.get("question", 0) > rates.get("direction", 0):
        communication = "Question-led explorer"
    elif median_length < 200:
        communication = "Concise driver"
    else:
        communication = "Context-rich collaborator"
    evidence = sorted(((name, value) for name, value in rates.items()), key=lambda row: -row[1])[:3]
    ordered_personas = sorted(scores, key=scores.get, reverse=True)
    secondary = ordered_personas[1] if count >= 20 and scores[ordered_personas[1]] >= scores[ordered_personas[0]] * .5 else None
    return {"persona": persona, "description": descriptions[persona], "communication": communication,
            "secondary": secondary,
            "rates": rates, "evidence": [{"signal": name, "rate": value, "count": signals[name]} for name, value in evidence],
            "sample": "early" if count < 20 else "established",
            "method": "Deterministic working-style lens, not a validated personality test or comparison with other people. Keyword categories overlap; detailed means at least 1,000 characters. Communication uses median length and detail share, so one long paste does not determine the style. Pasted material can contribute to language signals.",
            "persona_rules": "Investigator: questions + 0.4×review; Builder: direction + 0.25×continuation; Systems Thinker: 1.5×continuity + 0.5×detail + 0.4×review; Orchestrator: 1.5×root delegation share + 0.4×continuity; Editor: 1.4×review + 0.25×detail. Highest score selects the lens; fewer than 20 filtered messages yields Early Sketch."}


def local_timezone():
    """Find the host's IANA zone without reducing it to a fixed UTC offset."""
    candidates = [os.environ.get("TZ", "").lstrip(":")]
    try:
        target = str(Path("/etc/localtime").resolve())
        if "/zoneinfo/" in target:
            candidates.append(target.split("/zoneinfo/", 1)[1])
    except OSError:
        pass
    try:
        candidates.append(Path("/etc/timezone").read_text(encoding="utf-8").strip())
    except OSError:
        pass
    for candidate in candidates:
        if not candidate:
            continue
        try:
            ZoneInfo(candidate)
            return candidate
        except (ZoneInfoNotFoundError, ValueError):
            continue
    # Browser detection supplies the local zone on systems without a named zone file.
    return "UTC"


def analyze(path, timezone_name=None):
    timezone_name = timezone_name or local_timezone()
    try:
        zone = timezone.utc if timezone_name == "UTC" else ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ArchiveError("Choose an installed IANA timezone, for example America/Denver or UTC.") from exc
    connection, columns = connect_archive(path)
    try:
        return extract(connection, columns, zone)
    except sqlite3.Error as exc:
        raise ArchiveError("The archive could not be read completely. Check that this is an OpenCode database.") from exc
    finally:
        connection.close()


def extract(connection, columns, zone):
    def select(table, fields):
        expressions = [f'"{field}"' if field in columns[table] else f'NULL AS "{field}"' for field in fields]
        return connection.execute('SELECT ' + ', '.join(expressions) + f' FROM "{table}"')

    sessions = {}
    for sid, parent, directory, created in select("session", ("id", "parent_id", "directory", "time_created")):
        sessions[sid] = {"parent": parent, "project": project_name(directory), "created": number(created) or 0}
    roots = {sid for sid, session in sessions.items() if not session["parent"]}

    def root_of(sid):
        visited = set()
        while sid in sessions and sessions[sid]["parent"]:
            if sid in visited:
                return None
            visited.add(sid)
            sid = sessions[sid]["parent"]
        return sid if sid in sessions else None

    root_map = {sid: root_of(sid) for sid in sessions}
    messages = {}
    malformed = 0
    for mid, sid, stored, data in select("message", ("id", "session_id", "time_created", "data")):
        info = parse(data)
        if not info or sid not in sessions:
            malformed += 1
            continue
        stamp = number(obj(info.get("time")).get("created"))
        messages[mid] = {"session": sid, "created": stamp if stamp is not None else number(stored),
                         "original": stamp, "info": info}
    user_text = defaultdict(list)
    tools = []
    part_counts = Counter()
    compactions = 0
    for pid, mid, stored, data in select("part", ("id", "message_id", "time_created", "data")):
        part = parse(data)
        if not part:
            malformed += 1
            continue
        kind = part.get("type", "unknown")
        part_counts[kind] += 1
        message = messages.get(mid)
        if not message:
            continue
        if kind == "text" and message["session"] in roots and message["info"].get("role") == "user":
            if not part.get("synthetic") and not part.get("ignored") and isinstance(part.get("text"), str):
                text = clean_text(part["text"])
                if text:
                    user_text[mid].append(text)
        if kind == "compaction":
            compactions += 1
        if kind == "tool":
            state = obj(part.get("state"))
            input_data = obj(state.get("input"))
            digest = hashlib.sha256(json.dumps(input_data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            metadata = obj(state.get("metadata"))
            tool = str(part.get("tool", "unknown"))
            times = obj(state.get("time"))
            start, end = number(times.get("start")), number(times.get("end"))
            duration = (end - start) / 1000 if start is not None and end is not None and end >= start else None
            tool_path = input_data.get("filePath") or input_data.get("path")
            if not isinstance(tool_path, str):
                tool_path = None
            tools.append({"id": pid, "call": part.get("callID"), "message": mid, "session": message["session"],
                          "user": message["info"].get("parentID"), "original": message["original"],
                          "created": start if start is not None else message["created"] or number(stored) or 0,
                          "tool": tool, "digest": digest, "status": state.get("status", "unknown"),
                          "failure": state.get("status") == "error" or (tool == "bash" and exit_code(metadata.get("exit")) not in (None, 0)),
                           "nonzero": tool == "bash" and exit_code(metadata.get("exit")) not in (None, 0),
                           "duration": duration, "truncated": bool(metadata.get("truncated")), "path": tool_path})

    # Sorting ensures copied receipts are assigned to the earliest owning session.
    order = lambda mid: (sessions[messages[mid]["session"]]["created"], messages[mid]["created"] or 0, str(mid))
    human_seen, human, copied_human = set(), [], 0
    for mid in sorted(user_text, key=order):
        text = " ".join(user_text[mid])
        message = messages[mid]
        signature = (message["original"], text)
        if message["original"] is not None and signature in human_seen:
            copied_human += 1
            continue
        human_seen.add(signature)
        human.append({"id": mid, "text": text,
                      "session": message["session"], "created": message["created"]})
    human.sort(key=lambda row: row["created"] or 0)
    signals = Counter({name: 0 for name in (*SIGNALS, "detail", "continuation")})
    nudges, lengths, daily, hours, weekdays = Counter(), [], Counter(), [0] * 24, [0] * 7
    heatmap = [[0] * 24 for _ in range(7)]
    monthly = defaultdict(lambda: {"messages": 0, "tokens": 0, "cost": 0.0})
    projects = defaultdict(lambda: {"messages": 0, "tokens": 0, "cost": 0.0, "sessions": set(), "monthly": defaultdict(lambda: {"messages": 0, "tokens": 0, "cost": 0.0})})
    for item in human:
        text = item["text"]
        lengths.append(len(text))
        for name, (_, _, pattern) in SIGNALS.items():
            signals[name] += bool(pattern.search(text))
        signals["detail"] += len(text) >= 1000
        match = CONTINUE.fullmatch(text)
        signals["continuation"] += bool(match)
        if match:
            nudges[match.group(1).lower()] += 1
        project = projects[sessions[item["session"]]["project"]]
        project["messages"] += 1
        project["sessions"].add(item["session"])
        when = local_time(item["created"], zone)
        if when:
            day, month = when.date().isoformat(), when.strftime("%Y-%m")
            daily[day] += 1
            hours[when.hour] += 1
            weekdays[when.weekday()] += 1
            heatmap[when.weekday()][when.hour] += 1
            monthly[month]["messages"] += 1
            project["monthly"][month]["messages"] += 1

    usage, usage_seen, copied_receipts = Counter({field: 0 for field in COMPONENTS}), set(), 0
    costs, models, receipt_count, zero_price, missing_price, invalid_usage = 0.0, {}, 0, 0, 0, 0
    errors = Counter()
    for mid in sorted(messages, key=order):
        message = messages[mid]
        info = message["info"]
        if info.get("role") != "assistant":
            continue
        tokens, cache = obj(info.get("tokens")), obj(obj(info.get("tokens")).get("cache"))
        raw = {"input": tokens.get("input"), "output": tokens.get("output"), "reasoning": tokens.get("reasoning"), "cache_read": cache.get("read"), "cache_write": cache.get("write")}
        values = {field: number(value) or 0 for field, value in raw.items()}
        invalid_usage += any(value is not None and number(value) is None for value in raw.values())
        cost = number(info.get("cost"))
        completed = number(obj(info.get("time")).get("completed"))
        signature = (info.get("providerID"), info.get("modelID"), message["original"], completed, cost,
                     *(values[field] for field in COMPONENTS), number(tokens.get("total")))
        if message["original"] is not None and completed is not None and signature in usage_seen:
            copied_receipts += 1
            continue
        usage_seen.add(signature)
        receipt_count += 1
        total = sum(values.values())
        usage.update(values)
        costs += cost or 0
        zero_price += cost == 0 and total > 0
        missing_price += cost is None and total > 0
        error_name = obj(info.get("error")).get("name")
        if isinstance(error_name, str):
            errors[error_name] += 1
        project = projects[sessions[message["session"]]["project"]]
        project["tokens"] += total
        project["cost"] += cost or 0
        when = local_time(message["created"], zone)
        if when:
            month = when.strftime("%Y-%m")
            monthly[month]["tokens"] += total
            monthly[month]["cost"] += cost or 0
            project["monthly"][month]["tokens"] += total
            project["monthly"][month]["cost"] += cost or 0
        label = str(info.get("modelID") or "Unspecified model")
        key = (str(info.get("providerID") or "Unspecified provider"), label)
        model = models.setdefault(key, {"provider": key[0], "name": label, "receipts": 0, "tokens": 0, "cost": 0.0})
        model["receipts"] += 1
        model["tokens"] += total
        model["cost"] += cost or 0

    unique_tools, tool_seen, copied_tools = [], set(), 0
    for tool in sorted(tools, key=lambda row: (sessions[row["session"]]["created"], row["created"], str(row["id"]))):
        signature = (tool["call"], tool["original"], tool["tool"], tool["digest"])
        if tool["call"] and tool["original"] is not None and signature in tool_seen:
            copied_tools += 1
            continue
        tool_seen.add(signature)
        unique_tools.append(tool)
    tool_stats, by_session, read_groups, delegated = {}, defaultdict(list), Counter(), set()
    for tool in unique_tools:
        stats = tool_stats.setdefault(tool["tool"], {"name": tool["tool"], "calls": 0, "failures": 0, "tool_errors": 0, "nonzero_exits": 0, "durations": []})
        stats["calls"] += 1
        stats["failures"] += tool["failure"]
        stats["tool_errors"] += tool["status"] == "error"
        stats["nonzero_exits"] += tool["nonzero"]
        if tool["duration"] is not None:
            stats["durations"].append(tool["duration"])
        by_session[tool["session"]].append(tool)
        if tool["tool"] == "read" and tool["path"] and tool["user"]:
            read_groups[(tool["session"], tool["user"], tool["path"])] += 1
        if tool["tool"] == "task" and root_map[tool["session"]]:
            delegated.add(root_map[tool["session"]])
    retry_count = 0
    for calls in by_session.values():
        calls.sort(key=lambda row: row["created"])
        for index, tool in enumerate(calls):
            if not tool["failure"] or not tool["user"]:
                continue
            for later in calls[index + 1:index + 6]:
                if later["created"] - tool["created"] > 30 * 60 * 1000:
                    break
                if later["user"] == tool["user"] and later["tool"] == tool["tool"] and later["digest"] == tool["digest"]:
                    retry_count += 1
                    break
    repeated_reads = sum(max(0, count - 1) for count in read_groups.values())
    for stats in tool_stats.values():
        durations = stats.pop("durations")
        stats.update(timed_calls=len(durations), median_seconds=percentile(durations, .5), p90_seconds=percentile(durations, .9))
    ordered_days = sorted(daily)
    longest, streak, previous = 0, 0, None
    for day in ordered_days:
        current = date.fromisoformat(day)
        streak = streak + 1 if previous is not None and current == previous + timedelta(days=1) else 1
        longest, previous = max(longest, streak), current
    calendar = []
    if ordered_days:
        current, last = date.fromisoformat(ordered_days[0]), date.fromisoformat(ordered_days[-1])
        while current <= last:
            calendar.append({"date": current.isoformat(), "count": daily[current.isoformat()]})
            current += timedelta(days=1)
    mean_length = sum(lengths) / len(lengths) if lengths else 0
    human_roots = {item["session"] for item in human}
    active_roots = len(human_roots)
    delegation_share = len(delegated & human_roots) / active_roots * 100 if active_roots else 0
    assessment = assess(signals, len(human), percentile(lengths, .5) or 0, delegation_share)
    peak_hour = max(range(24), key=lambda hour: hours[hour]) if ordered_days else None
    peak_day = max(range(7), key=lambda day: weekdays[day]) if ordered_days else None
    failures = sum(tool["failure"] for tool in unique_tools)
    candidates = []
    if repeated_reads:
        candidates.append({"id": "rereads", "title": "Give context a smaller front door.", "value": repeated_reads,
                           "unit": "additional reads of the same path within one user turn", "score": repeated_reads / max(1, len(unique_tools)),
                           "body": "A compact state file or a targeted line range may reduce repeated context gathering. Rereads after edits can be intentional.",
                           "experiment": "For your next three sessions, begin with one state file and ask for targeted reads. Compare the repeated-read count."})
    if failures:
        candidates.append({"id": "failures", "title": "Make the first failed attempt more informative.", "value": failures,
                           "unit": "calls with a tool error or recorded nonzero shell exit", "score": failures / max(1, len(unique_tools)) * 3,
                           "body": f"{retry_count:,} failure-shaped calls are followed by an identical input within five calls, 30 minutes, and the same user turn. Expected shell nonzero exits may be legitimate.",
                           "experiment": "Add a cheap preflight and an explicit expected result to one repeated command. Review whether retries change."})
    if signals["continuation"]:
        candidates.append({"id": "continuations", "title": "Bundle the small green lights.", "value": signals["continuation"],
                           "unit": "short continuation messages", "score": signals["continuation"] / max(1, len(human)),
                           "body": "Short approvals can preserve useful boundaries. Within an already authorized phase, a clear finish line may reduce extra turns.",
                           "experiment": "Authorize one bounded phase with its stopping condition up front. Compare continuation turns, without removing deliberate gates."})
    if signals["continuity"]:
        candidates.append({"id": "handoffs", "title": "Make your restart point reusable.", "value": signals["continuity"],
                           "unit": "messages matching continuity or phase language", "score": signals["continuity"] / max(1, len(human)) * .7,
                           "body": "These messages name context, gates, or handoffs. One authoritative restart document may make that structure easier to maintain.",
                           "experiment": "Keep verified state, remaining work, and the next runnable action in one short file for a week."})
    candidates.sort(key=lambda row: -row["score"])
    for candidate in candidates:
        candidate.pop("score")
    if not candidates:
        candidates.append({"id": "baseline", "title": "Give the next phase a visible finish line.", "value": len(human), "unit": "filtered user messages in this snapshot",
                           "body": "There is no strong friction signal in this sample yet. Start with one observable completion check.",
                           "experiment": "Name the deliverable and its acceptance check before your next task. Save the result for your next mirror."})
    months = sorted(monthly)
    # Fill calendar months that have no receipts, preserving real gaps.
    if months:
        year, month = map(int, months[0].split("-"))
        final = months[-1]
        months = []
        while f"{year:04}-{month:02}" <= final:
            months.append(f"{year:04}-{month:02}")
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    project_list = []
    for name, project in projects.items():
        if not project["messages"] and not project["tokens"] and not project["cost"]:
            continue
        project_list.append({"name": name, "messages": project["messages"], "tokens": project["tokens"], "cost": round(project["cost"], 6),
                             "sessions": len(project["sessions"]), "monthly": [{"month": month, **project["monthly"][month]} for month in months]})
    project_list.sort(key=lambda row: (-row["messages"], -row["tokens"], row["name"]))
    top_nudge = nudges.most_common(1)[0] if nudges else None
    total_tokens = sum(usage.values())
    return {
        "schema": "opencode-mirror/1", "version": VERSION, "generated_utc": datetime.now(timezone.utc).isoformat(), "shared": False,
        "timezone": str(zone), "coverage": {"start": ordered_days[0] if ordered_days else None, "end": ordered_days[-1] if ordered_days else None},
        "summary": {"sessions": len(sessions), "root_sessions": len(roots), "child_sessions": len(sessions) - len(roots),
                    "active_root_sessions": active_roots, "messages": len(human), "active_days": len(ordered_days), "longest_streak": longest,
                    "projects": len(project_list), "tool_calls": len(unique_tools), "receipts": receipt_count,
                    "tokens": total_tokens, "recorded_cost": round(costs, 6)},
        "assessment": assessment,
        "communication": {"signals": [{"id": name, "label": label, "description": description, "count": signals[name], "rate": assessment["rates"][name]} for name, (label, description, _) in SIGNALS.items()]
                          + [{"id": "detail", "label": "Specification-rich", "description": "At least 1,000 characters", "count": signals["detail"], "rate": assessment["rates"]["detail"]},
                             {"id": "continuation", "label": "Quick green lights", "description": "Exact short continuation phrases", "count": signals["continuation"], "rate": assessment["rates"]["continuation"]}],
                          "mean_characters": round(mean_length), "median_characters": percentile(lengths, .5),
                          "top_nudge": {"label": top_nudge[0], "count": top_nudge[1]} if top_nudge else None},
        "rhythm": {"hours": hours, "weekdays": weekdays, "heatmap": heatmap, "calendar": calendar, "peak_hour": peak_hour, "peak_weekday": peak_day},
        "months": [{"month": month, **monthly[month]} for month in months], "projects": project_list,
        "resources": {"components": dict(usage), "zero_cost_token_receipts": zero_price, "missing_cost_token_receipts": missing_price,
                      "models": sorted(models.values(), key=lambda row: -row["cost"]), "token_definition": "input + cache read + cache write + output + reasoning; repeated cache processing is included"},
        "execution": {"tools": sorted(tool_stats.values(), key=lambda row: -row["calls"]), "failure_shaped_calls": failures,
                      "identical_after_failure": retry_count, "repeated_reads": repeated_reads,
                      "truncated_calls": sum(tool["truncated"] for tool in unique_tools), "compactions_raw": compactions,
                      "delegated_root_sessions": len(delegated & roots), "assistant_errors": dict(errors)},
        "opportunities": candidates[:3],
        "methods": {"human": "Root user text only; synthetic and ignored parts excluded; system-reminder blocks removed. Identical text at the same original creation timestamp retained once. Pasted templates can remain." + (" Parent links are unavailable in this schema; all sessions are treated as roots." if "parent_id" not in columns["session"] else ""),
                    "resources": "Root and child assistant receipts included once. Identical provider/model/original timestamps/cost/token signatures retained in earliest session. No original timestamp/completion means no receipt deduplication. Recorded cost is an estimate, not an invoice.",
                    "tools": "Call-ID/original-message-time/tool/input signatures deduplicated. Rereads compare exact path strings within a session and user turn; path aliases and edits are not resolved. Failure signals union tool error and nonzero shell exit.",
                    "rhythm": "Filtered user message creation timestamps in the selected timezone. Activity is interaction, not labor hours. Streaks are consecutive calendar days with at least one filtered message.",
                    "projects": "Owning session directory basename; equal basenames combine. Child resources stay with their owning directory. Months follow original receipt creation times.",
                    "privacy": "No prompts, tool inputs/results, full paths, session IDs, credentials or account data in reports. Shared reports replace project names with aliases.",
                    "assessment": "Communication: detailed specifier if at least 25% of messages have 1,000+ characters or the median is at least 700; otherwise question-led if question share exceeds direction share, concise driver if median length is under 200, context-rich collaborator otherwise. A secondary persona appears when the runner-up reaches half the leading heuristic score. Delegation uses active root sessions with filtered human messages as its denominator.",
                    "opportunities": "Ordered by signal rate with exploratory weights: failure-shaped calls ×3, continuity language ×0.7, repeated reads ×1, short continuations ×1. These priorities are hypotheses for small experiments, not estimated time savings.",
                    "copied_human_messages_removed": copied_human, "copied_receipts_removed": copied_receipts, "copied_tools_removed": copied_tools,
                    "malformed_or_unlinked_records_skipped": malformed, "receipts_with_invalid_token_values": invalid_usage}
    }


def share_report(report):
    shared = json.loads(json.dumps(report, allow_nan=False))
    shared["shared"] = True
    for index, project in enumerate(shared["projects"], 1):
        project["name"] = f"Project {index:02}"
    return shared
