# Accuracy log

A running record of what Change Radar got right and wrong, so claims about it can be checked. Add a row every time you test it. Include the failures.

How to read it: "quote verified" means the automatic check passed. "Summary supported" is a human judgement that the summary fields say no more than the quote supports.

| Date | Notice | Method | Result | Notes |
|---|---|---|---|---|
| 2026-11-09 | Fictional demo notice | Rules | Accepted. Quote verified. | Triage only: "what changed" is the notice title. |
| 2026-11-09 | Fictional demo notice | qwen2.5:7b-instruct | Accepted. Quote verified. Summary not fully supported. | The quote was the "must delete" sentence, but the summary said the deadline was extended. The check passed because it only covered the quote. This led to the deadline check and to showing the quote beside every summary. |
| 2026-11-09 | Fictional demo notice | llama3.2:3b | Returned nothing. | Silent miss on an obvious change. Not recommended. Led to the rules fallback. |
| 2026-11-11 | Fictional demo notice | qwen2.5:7b-instruct, through the CLI | Accepted. Quote verified. Summary supported. | The quote was a fragment of the extension sentence and supported the summary and the deadline. |

## Still to do

- Test on real notices, once their use is permitted.
- Build a hand-labelled set of notices and report how often each method finds the change, misses it, or overstates it.
