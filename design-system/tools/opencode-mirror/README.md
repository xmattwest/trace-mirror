# OpenCode Mirror

Your working style, conversation fingerprint and daily rhythm, drawn from your local OpenCode archive.

## Run

Python 3.10+. No dependencies to install.

```sh
python3 mirror.py --db "/path/to/opencode.db"
```

Opens [127.0.0.1:8787](http://127.0.0.1:8787/). Without `--db`, Mirror tries OpenCode’s usual data directory or lets you enter a path.

## Save

**Save share card** downloads a 1200 × 1200 PNG. **Export report** downloads an offline HTML page with embedded fonts.

For a headless export:

```sh
python3 mirror.py --db "/path/to/opencode.db" --export mirror.html
```

Exports contain aggregate counts, dates and model/tool names. Project names are replaced with aliases. Prompts, tool inputs and outputs, full paths, session IDs and credentials are excluded.

## Timezone

The app uses your browser’s local timezone; headless exports use the computer’s zone. Daylight saving follows each message’s date. Shared snapshots retain their original zone.

Override with `--timezone America/Denver`. Other options: `--port 8788`, `--no-open`, `--version`.

## Method

The persona is a deterministic reading of language and delegation signals. It is not a validated personality test. The app includes its scoring rules and exact message counts; fewer than 20 filtered messages produces an early sketch.

Only root user text contributes to language and rhythm. Synthetic text, ignored parts, reminders and identifiable history copies are excluded. Real repeat requests remain. Pasted material can influence the result. Activity measures interaction, not hours worked.

The engine retains aggregate resource, project and tool fields for compatibility. Root and child usage is counted once; token totals sum input, cache read/write, output and reasoning.

Mirror reads `session`, `message` and `part` tables in a read-only SQLite transaction. Empty archives and missing optional columns are supported. Nothing is uploaded or written to the database.

## Development

```sh
python3 -m unittest discover -s tests -v
```

In the Warm Precision checkout, source lives in `design-system/tools/opencode-mirror/`. Building the handbook creates a portable `handbook/opencode-mirror.zip` with theme tokens, fonts and their license notices.
