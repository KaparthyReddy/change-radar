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
| `extract/` | Turn items into alerts | Planned |
| `digest/` | Render the digest | Planned |
| `cli.py` | Command-line interface | Planned |

## Design decisions

- **Standard library only.** The core has no dependencies, so it is easy to install and audit.
- **The model never checks itself.** Quote verification is plain string matching.
- **Fail closed.** If robots.txt cannot be read, or a source's terms are unchecked, the source is not fetched in normal use.
- **Changes are first-class.** The store records whether a fetched item is new, changed or unchanged, so a changed document can be flagged.
- **Feeds first.** Version 0.1 reads feed entries. Fetching the full text behind each link comes after that.
