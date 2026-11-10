# Source policy

Change Radar reads only official, public sources. This page records the rules and the current status of each source. Nothing here is legal advice.

## Rules for adding a source

1. It must be an official publisher of the rules or notices it covers.
2. Read its terms of use and its robots.txt before the first fetch.
3. Record the page you read in `terms_url`.
4. Set `terms_checked = true` only when you are sure automated reading is allowed. Anything unclear stays `false`.
5. Sources with `terms_checked = false` are skipped unless `--include-unchecked` is used. That flag is for local development only. Do not publish output built from unchecked sources.

## How the fetcher behaves

- It identifies itself with a User-Agent that links to this repository.
- It reads robots.txt for each host and refuses anything disallowed. If robots.txt cannot be read, it does not fetch.
- It waits at least two seconds between requests to the same host.
- It accepts HTTPS only and refuses very large responses.

## Current status

| Source | Terms checked | Notes |
|---|---|---|
| RBI notifications | No | See below |
| RBI press releases | No | See below |

### RBI

The RBI's disclaimer page (https://rbi.org.in/Scripts/Disclaimer.aspx, read in November 2026) does not mention automated reading. It does contain language prohibiting caching and framing of the site's contents, and says that linking to an internal page needs prior permission. It also says the RBI may block access from any address.

Because this project stores text for verification and links to the source page in every item, these sources stay unchecked. Before anything built from them is published or sold, either get written permission from the RBI or take advice from a qualified person. Only then change `terms_checked`.
