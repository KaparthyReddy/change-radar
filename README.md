# change-radar

![CI](https://github.com/KaparthyReddy/change-radar/actions/workflows/ci.yml/badge.svg)

Early warning for the rule changes that can break a fintech startup.

Change Radar turns official notices into short alerts: what changed, who it affects, the deadline, and what to check. Every alert carries an exact quote from the notice and a link to it. An alert whose quote cannot be found word for word in the notice is thrown away.

> **Status: v0.1.0, early.** It works end to end on documents you import yourself. Fetching from official feeds is built but switched off for RBI, because its terms and robots.txt are unresolved (see [source policy](docs/source-policy.md)). Treat the output as a triage aid, not a source of truth.

## Example

A digest built from a fictional notice written for this demo (not a real regulator document):

[examples/sample-digest.md](examples/sample-digest.md)

## Quick start

Needs Python 3.11 or newer.

```bash
git clone https://github.com/KaparthyReddy/change-radar.git
cd change-radar
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

change-radar import examples/demo-notice.txt --url https://example.com/demo --title "Demo notice" --db data/demo.sqlite
change-radar extract --db data/demo.sqlite
change-radar digest --db data/demo.sqlite --format html --out out/digest.html
```

Without a model, extraction uses deterministic rules. To use a local model through [Ollama](https://ollama.com), add `--model`, for example `change-radar extract --model qwen2.5:7b-instruct`. The model server must run on localhost. No API keys are involved.

Commands: `sources`, `fetch`, `import`, `extract`, `digest`. Run `change-radar --help` for options.

## How it works

```
import or fetch -> store -> extract -> verify -> digest
```

- **Import** reads a document you saved yourself, so no network access is needed.
- **Fetch** reads RSS feeds politely: it identifies itself, obeys robots.txt, waits between requests, and skips any source whose terms are not marked as checked.
- **Extract** uses rules, or a local model with the rules as a safety net.
- **Verify** is plain string matching. The model never checks its own output.
- **Digest** renders Markdown or HTML.

The core uses only the Python standard library.

## What verification covers

Checked automatically:

- the quote appears word for word in the notice (whitespace and typography are ignored)
- the alert links to the notice it came from
- a stated deadline appears word for word in the notice

Not checked:

- **The summary fields** (what changed, who it affects, what to check). They are written by rules or a model and can say more than the quote supports. Read the quote next to each summary.
- **Silence.** A model can miss an obvious change and return nothing. In testing, a 3B model did exactly that on a simple notice, which is why rules run as a fallback.

The [accuracy log](docs/accuracy-log.md) records what has been tried and what went wrong.

## Sources and terms

Only official public sources are used, and each one's terms are recorded in `sources/sources.toml`. Sources with unchecked terms are skipped unless you pass `--include-unchecked`, which is for local development only. Do not publish output built from sources you do not have permission to use. See the [source policy](docs/source-policy.md).

## Development

```bash
pip install -e ".[dev]"
ruff check . && mypy && pytest -q
```

## Roadmap

- [ ] A first source with cleared terms
- [ ] More official sources
- [ ] A hand-labelled evaluation set and a published accuracy report
- [ ] Reading the full text behind each feed entry

## Disclaimer

Change Radar reports changes in public documents and links to the original. It is not legal, financial or compliance advice. Always read the source.

## License

MIT
