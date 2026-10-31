# OpenCode Mirror

Your working style, conversation fingerprint and daily rhythm, drawn from your local OpenCode archive.

**[Handbook & download →](https://xmattwest.github.io/trace-mirror/)**

## Run

Python 3.10+. No dependencies to install.

```sh
python3 mirror.py --db "/path/to/opencode.db"
```

Opens [127.0.0.1:8787](http://127.0.0.1:8787/). Without `--db`, Mirror tries OpenCode’s usual data directory or lets you enter a path.

Save a PNG share card or an offline HTML report. For a headless export, add `--export mirror.html`. Other options: `--timezone America/Denver`, `--port 8788`, `--no-open`.

The database stays read-only. Nothing is uploaded. The persona is a transparent heuristic, not a validated personality test.

## Development

```sh
python3 -m unittest discover -s tests -v
python3 build.py
```
