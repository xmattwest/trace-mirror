# Set up OpenCode Mirror

Set up Mirror on this user’s computer, verify it, and leave it ready to use. Mirror reads a local OpenCode archive and shows a working persona, conversation fingerprint and daily rhythm.

## 1. Check Python

Use Python 3.10 or newer. Check `python3 --version`; on Windows, also try `py -3 --version` or `python --version`. Use the interpreter that meets the requirement in the commands below.

If Python is missing, install it using the platform’s usual method. Mirror has no third-party runtime dependencies. No pip install, account, model API or build step is needed.

## 2. Get the tool

If a complete installation is already available, use it. Otherwise download:

https://xmattwest.github.io/trace-mirror/opencode-mirror.zip

Extract it into a writable parent folder, such as Downloads. The zip contains an `opencode-mirror` folder; the installation folder is the one containing `mirror.py`.

Confirm these files exist:

- `mirror.py` and `analyze.py`
- `assets/app.js` and `assets/app.css`
- `assets/index.html`, `assets/theme.css` and `assets/fonts.css`

Use a separate folder if an existing checkout has local edits. Bundled fonts are ready to use; do not refresh them as part of setup.

## 3. Locate the archive

Mirror’s default is:

- `$XDG_DATA_HOME/opencode/opencode.db`, when `XDG_DATA_HOME` is set.
- Otherwise, `.local/share/opencode/opencode.db` under the user’s home directory.

Check those locations first. Use the database in place; Mirror opens it read-only. Keep the database and any exports local.

If neither location contains an archive, ask the user for its path or leave the welcome screen ready for them to enter one. Do not create a replacement database. A new OpenCode user may need to start an OpenCode session first.

## 4. Start Mirror

Use the actual installation path, quoted if it contains spaces:

```sh
python3 "/path/to/opencode-mirror/mirror.py" --no-open
```

If the archive is elsewhere, add its actual path:

```sh
python3 "/path/to/opencode-mirror/mirror.py" --db "/path/to/opencode.db" --no-open
```

Keep the server running using the environment’s supported process mechanism. Large archives can take time to read; wait for the printed local URL before checking the page.

The default port is 8787. If it is occupied, add `--port 0` to let the operating system choose a free port. Read the URL from the launcher output; do not assume it is still 8787 or stop another service to free that port.

Open that `http://127.0.0.1:<port>/` URL in the user’s browser when available. Mirror binds only to this computer. If a working Mirror instance is already serving the intended archive, its URL can be reused.

## 5. Verify and hand off

- Confirm the local page loads. With an archive, the persona, fingerprint and rhythm should appear. Without one, the path-entry screen is the expected result.
- Check `http://127.0.0.1:<port>/api/report`: it returns report JSON, or `null` before an archive is opened. A populated report has schema `opencode-mirror/1`.
- With an archive open, check `http://127.0.0.1:<port>/export` returns an HTML snapshot. No upload or database write is involved.
- Confirm the displayed timezone. The browser supplies its local zone; `--timezone` is an explicit override. If named timezone data is unavailable, report the UTC fallback rather than choosing a region for the user.

Tell the user the installation folder, the working local URL, the exact command to start it again, and how to stop the process. Use Ctrl+C for a foreground server, or identify the specific process you started when running it in the background.

If an archive is still needed, state that clearly. An early sketch from a small archive is valid; the persona is a heuristic, not a validated personality test.
