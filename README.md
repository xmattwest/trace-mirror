# Warm Precision

A design handbook for research, documents, diagrams and software.

**[Read the handbook →](https://xmattwest.github.io/trace-mirror/)**

Principles, a Dawn State visual profile, medium-specific guidance and working examples. Includes [OpenCode Mirror](https://xmattwest.github.io/trace-mirror/handbook/opencode-mirror.html), a local view of your conversational style and daily rhythm.

## Local use

Python 3.10+.

```sh
python3 design-system/scripts/build.py --embed-fonts
python3 -m http.server 8080 --directory handbook
```

Open [localhost:8080](http://localhost:8080). Edit the Markdown, profile tokens and assets under `design-system/`, then rebuild.

```sh
python3 design-system/scripts/build.py --check
python3 design-system/scripts/test_build.py
```
