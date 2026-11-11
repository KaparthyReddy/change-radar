# Architecture

Change Radar is a small pipeline. Each stage is a separate module, and each stage can be tested without the network.

```
sources/sources.toml
|
v
fetch (polite HTTP) --> parse feeds --> Items
|
v
store (SQLite): new / changed / unchanged
|
v
extract (planned): what changed, who it affects, deadline, what to check, quote
|
v
verify: the quote must appear word for word in the item’s text
|
v
digest (planned): Markdown and HTML
```


## Modules and status

| Module | Job | Status |
|---|---|---|
| `config.py` | Load and validate the list of sources | Built |
| `models.py` | `Item` and `Alert` types | Built |
| `verify.py` | Deterministic quote check | Built |
| `fetch/http.py` | HTTPS fetching that identifies itself, obeys robots.txt and limits request rate | Built |
| `fetch/text.py` | HTML to plain text | Built |
| `fetch/feeds.py` | RSS and Atom to `Item` | Built |
| `store.py` | SQLite storage for items and alerts | Built |
| `extract/` | Turn items into alerts: rules or an optional local model, then quote verification | Built |
| `digest/` | Render the digest as Markdown or HTML | Built |
| `cli.py` | Command-line interface | Built |

## Design decisions

- **Standard library only.** The core has no dependencies, so it is easy to install and audit.
- **The model never checks itself.** Quote verification is plain string matching.
- **Fail closed.** If robots.txt cannot be read, or a source's terms are unchecked, the source is not fetched in normal use.
- **Changes are first-class.** The store records whether a fetched item is new, changed or unchanged, so a changed document can be flagged.
- **Feeds first.** Version 0.1 reads feed entries. Fetching the full text behind each link comes after that.

## What verification covers

`verify.py` checks three things: the quote appears word for word in the notice, the alert links to the notice it came from, and any stated deadline appears word for word in the notice.

It does not check the summary fields (what changed, who it affects, what to check). Those are written by rules or a model, and they can say more than the quote supports. For that reason every digest item shows the quote beside the summary, and every item should be read by a person while the project is young.

A model can also fail silently by returning nothing. When a model is used, the rule-based extractor runs as a safety net if the model yields no verified alert.
