# OpenCode Mirror

Your working style, conversation fingerprint and daily rhythm, drawn from your local OpenCode archive.

## Run

Download and unzip [OpenCode Mirror](handbook/opencode-mirror.zip), then run:

```sh
python3 mirror.py --db "/path/to/opencode.db"
```

Python 3.10+. No dependencies to install. Opens [127.0.0.1:8787](http://127.0.0.1:8787/). Without `--db`, Mirror tries the usual OpenCode data directory or lets you enter a path.

## The report

- A working persona and communication fingerprint, with scoring rules and message counts.
- A weekday/hour activity mosaic in your local timezone, with exact counts available.
- A 1200 × 1200 PNG share card and an offline HTML export.

The persona is a transparent heuristic, not a validated personality test. Fewer than 20 filtered user messages produces an early sketch. Activity measures interaction, not hours worked.

Root user text excludes synthetic/ignored parts, reminders and identifiable history copies. Real repeat requests remain. Pasted material can influence the result.

## Timezone and export

The browser supplies its local timezone. Headless exports use the computer’s zone, falling back to UTC if no installed named zone is detectable. Daylight saving follows each message’s date; exported snapshots retain their original zone.

```sh
python3 mirror.py --db "/path/to/opencode.db" --timezone America/Denver
python3 mirror.py --db "/path/to/opencode.db" --export mirror.html
```

Other options: `--port 8788`, `--no-open`, `--version`.

## Local by design

SQLite is opened read-only. Nothing is uploaded. Exports exclude prompts, tool inputs and outputs, full paths, session IDs and credentials. Shared HTML replaces project names with aliases; dates, aggregate counts and model/tool names remain.

Supported archives contain `session`, `message` and `part` tables with JSON message/part data. Empty archives and missing optional columns are supported. Aggregate resource, project and tool fields remain in the engine for compatibility.

Source: `design-system/tools/opencode-mirror/`. The handbook build produces the portable download, including source, tests, fonts and license notices.
