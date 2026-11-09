# change-radar

![CI](https://github.com/KaparthyReddy/change-radar/actions/workflows/ci.yml/badge.svg)

Early warning for the rule changes that can break a fintech startup.

Change Radar reads official public sources (RBI and NPCI notices to start), works out what changed, who it affects and by when, and produces a short digest. It will not publish any claim it cannot quote word for word from the original.

> **Status: early development.** Nothing here is usable yet. This README describes what is being built and will be updated as each part lands.

## Why

Rules and platform terms change often, and the announcements are spread across many sites. Small teams rarely have anyone whose job is to read them all, so changes get noticed late, or a deadline is planned around and then moves. The RBI's card-on-file tokenisation deadline, which was extended more than once, is a typical example.

## Design rules

1. **No quote, no alert.** Every item must carry an exact quote from the source. A deterministic check confirms the quote appears in the source text. The model is never trusted to do this.
2. **Official public sources only.** Each source's terms are recorded and checked before it is fetched.
3. **Every item links to its source**, so a reader can check it in seconds.
4. **Reports changes, not advice.** This is not legal or compliance advice.
5. **Free to run.** The core uses only the Python standard library. A local model through Ollama is optional. No API keys.

## Planned alert format

Each item will contain:

- What changed, in one sentence
- Who it affects
- Deadline, or "none stated"
- What to check
- Source: the exact quote and a link

## Planned usage (not implemented yet)

```bash
change-radar sources check
change-radar run
change-radar digest --out out/digest.md
```

## Roadmap to v0.1.0

- [ ] Source config with recorded terms
- [ ] Fetch feeds from official sources
- [ ] SQLite store
- [ ] Rule-based extraction, plus optional extraction with a local model
- [ ] Quote verification
- [ ] Digest rendering (Markdown and HTML)
- [ ] Command-line interface

## Development

Needs Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ruff check . && mypy && pytest -q
```

## Disclaimer

Change Radar reports changes in public documents and links to the original. It is not legal, financial or compliance advice. Always read the source.

## License

MIT
