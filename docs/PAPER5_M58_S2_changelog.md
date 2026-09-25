# M58 Group S2 — apply the author's style, remove AI-tells (line-by-line edit)

## Status: NO RIG, complete. Target: `Papers_4-5/Paper_5/WPC/main.tex` @ `f60efc5` (M58 Group S1). Compiles clean (pdflatex → bibtex → pdflatex ×2, exit 0 every stage, zero undefined references or citations, zero overfull-hbox warnings). **Final page count: 21pp, unchanged** — this was a voice/punctuation pass, not a length pass, and no group in this gate targeted page count. **Every retained number verified unchanged: a full numeric-token diff of the whole file shows zero tokens added or removed, in either direction.**

## What changed: categories and counts

Applied the S1 rules (`docs/PAPER5_M58_style_rules.md`) line by line across the entire manuscript body (Introduction through Declarations). Two mechanical categories account for nearly everything:

| category | before | after | rule |
|---|---|---|---|
| Prose em-dashes (`--`/`---` used as a parenthetical/interruption, not a numeric range) | 12 | 0 (1 left: a source `%` comment, unrendered, matching Paper #4's own comment style) | S1 Rule 2 |
| Prose semicolons (joining independent clauses or list items in flowing text; excludes algorithm pseudocode, `\cite`/`\ref` internals, table rules, and math-mode `\;`) | 62 | 1 (a single dense parenthetical stat tuple, `(fully-connected ...; ring ...; hex ...)`, kept as the one evidenced exception — see below) | S1 Rule verdict |

No other systematic AI-tell phrase was found anywhere in the manuscript (`it is worth noting`, `notably,`, `underscores`, `delve`, `moreover`, `furthermore`, `in conclusion,`, `overall,`, `plays a crucial/vital/pivotal role`, `boasts`, `leverage(d/s)`, `myriad`, `a testament to` — all zero hits, checked after the edit). This confirms the manuscript's earlier drafting (M54–M57) had already avoided that specific class of tell; this gate's actual work was almost entirely the em-dash/semicolon correction.

## How each category was fixed, by pattern (with counts)

- **Em-dash as trailing appositive/gloss** (S1 Rule 2, e.g. "...a genuine null result." in Paper #4) → replaced with a comma: 7 instances (Abstract, Related Work, Evaluation Safeguards ×2, Centralised results, Live Deployment ×2).
- **Em-dash introducing a list or elaboration** (S1 Rule on colons) → replaced with a colon: 2 instances (Evaluation Safeguards' four-failures intro, Live Deployment's "executes correctly end to end: real traffic...").
- **Em-dash joining two independent clauses** → replaced with a full stop (optionally followed by "But"/"So" per S1 Rule 6's blunt-contrast pattern): 3 instances (N=7 scaling, Live Deployment's "no catastrophic failure. But since...", the Algorithm comment).
- **Semicolon joining two independent clauses** → split into two sentences, or joined with a comma + coordinating conjunction (and/but/so) where the two clauses share a clear continuation: 41 instances across Introduction, System Model, GAT-CTDE Method (including the merged collapse-diagnosis paragraph), Evaluation Safeguards, Centralised/Federated/Disruption results, Cluster-Size Scaling (N=19 and N=7), Live Deployment, Conclusion, and the Declarations block.
- **Semicolon-separated 3-item lists of full independent clauses** (the Introduction's "three gaps" list and the Conclusion's "four limits" list) → restructured as **First, ... Second, ... Third, ... [Fourth, ...]**, matching S1 Rule 7's direct evidence from Paper #3's Future Work section (five ordinal-numbered separate sentences). 2 lists restructured this way (3 items and 4 items respectively).
- **Semicolon-separated 3-item lists of noun phrases** (the Introduction's "we close all three" list, the Experimental Setup's "three arms" list) → converted to a plain comma list ending in "and", matching S1 Rule evidence from Paper #3's own long comma-lists (e.g. "DRL, MARL, GNN-assisted control, and FL..."). 2 lists converted this way.
- **Semicolon-separated 3-term definitional list** (the Disruption subsection's dropout/spike/churn definitions) → restructured into three separate sentences, one per term, each opening with the term itself in italics (`\emph{gNB dropout} forces...`, `\emph{Demand spike} is...`, `\emph{Agent churn} substitutes...`), removing both the semicolons and the em-dash that had been attached to the third item.
- **Semicolon inside a dense parenthetical statistical tuple** (`(fully-connected $-$0.175 [...], $p=0.7422$; ring ...; hex ...)`, Cluster-Size Scaling) → **kept**, as the one deliberate exception. S1's own evidence (Paper #3's table cells, e.g. "98% acc.; 97.6% P; 97.1% R; 98.0% F1") shows the author does use semicolons for exactly this purpose: separating compact, comma-internal statistical tuples where a plain comma list would be genuinely ambiguous (is "$p=0.7422$, ring" one item or two?). This is the only semicolon left in the manuscript's prose, and it is a deliberate match to the author's own demonstrated practice, not an oversight.

## What did not change

- No number, percentage, $p$-value, confidence interval, seed count, or citation was touched. Verified two ways: (1) every edit above only altered connective punctuation and, where a semicolon-list was restructured into ordinal sentences, added the words "First,"/"Second,"/"Third,"/"Fourth,"; (2) a full numeric-token diff of the file before and after this gate (see below) shows **zero tokens added, zero tokens removed**, in either direction — the strongest possible confirmation available that this was a pure language pass.
- No finding was softened, generalised, or dropped. Spot-checked after the edit: the four safeguard findings (`tab:safeguards`'s 4 rows), the 44/49 (89.8%) and 21/24 (87.5%) metric-disagreement result, the churn retraction ("opposite of immune", 1 occurrence, matching its pre-edit count), the 35.4% [25.5%,45.8%] scaling result (6 occurrences, same as before the edit), the deployability-vs-contention distinction (6 occurrences), the cross-layer scheduler-floor finding (6 occurrences), and the Conclusion's "Four limits bound every claim in this paper" lead sentence (present, now followed by First/Second/Third/Fourth per Rule 7) are all present, unchanged in substance.
- No section, subsection, table, figure, or label was added, removed, or renumbered in this gate. Structure is exactly as M57 left it.

## Zero-number-changed verification

```
$ git diff --stat Papers_4-5/Paper_5/WPC/main.tex   # confirms only main.tex touched
$ python3 <numeric-token-diff script, same method as M55-M57>
ONLY IN REMOVED count=0
ONLY IN ADDED count=0
```

This is a stronger result than every prior condensation gate's own verification (which always found a handful of tokens to trace and explain, all legitimately accounted for) — here there is nothing to trace at all, because no digit in the manuscript was touched by this gate's edits.

## Compilation verification

```
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
bibtex main                                                  # exit 0
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # exit 0
grep -n "Citation.*undefined\|Reference.*undefined\|LaTeX Warning: There were undefined" <final log>  # no matches
grep -n "Overfull \\hbox" <final log>                        # no matches
```

Compiled and verified incrementally five times during the edit (after the Introduction/Abstract, after the merged collapse-diagnosis paragraph, after the Disruption subsection rewrite, after Cluster-Size Scaling and Live Deployment, and after the Conclusion), and once more at the end as the canonical 4-stage sequence. 21 pages, unchanged from the start of this gate.

## STOP

Reported per the milestone's own gate. Compiles clean; page count unchanged at 21 (not this gate's target); zero numbers changed; every preserved finding confirmed intact. Awaiting go before Group S3 (Springer Nature / WPC formatting compliance check).
