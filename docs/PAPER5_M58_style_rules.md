# M58 Group S1 — the author's actual style, extracted from Paper #3 and Paper #4

## Status: NO RIG, analysis only. No edits made to `main.tex` in this gate. Sources: `/home/kmanojp/Desktop/CACS26/DQSACLOOR.pdf` (Paper #4, CACS26 — LaTeX source also available in-repo at `Papers_4-5/Paper_4/main.tex`, used as the primary, exact-punctuation ground truth) and `/home/kmanojp/Desktop/IA_CROTUCDNS5GN_corrected.pdf` (Paper #3, IEEE Access — no LaTeX source available on this machine, so quotes are from `pdftotext -layout` extraction; flagged per-quote where a line-wrap hyphen may be an artifact rather than the author's own hyphenation).

## Method

For Paper #4, grepped the actual `.tex` source directly rather than reading the rendered PDF, since that gives exact, unambiguous punctuation (a rendered PDF cannot be trusted to distinguish a semicolon from a period, or an en-dash range from an em-dash, at normal reading resolution — this was confirmed the hard way below). For Paper #3, extracted text via `pdftotext -layout` and cross-checked every semicolon/dash hit by hand against its surrounding context (table cell vs. running prose) rather than trusting a raw count.

## THE PUNCTUATION VERDICT (answering S1's direct question)

**No em-dashes. Effectively no semicolons in prose either.** Both findings are stronger and more absolute than a typical style analysis would expect, and both are backed by an exhaustive check, not a sample.

### Em-dashes: zero, in either paper

- Paper #4's `.tex` source contains 31 instances of `--` and one instance of `---`. Checked every one: **all 31 `--` are numeric ranges** (`33--36`, `67.9--68.3\,$\mu$s`, `24--25 point`, `0--100 scale`, `5--8 points`) or TikZ `\draw` arrow syntax (`(probe) -- (sim)`) — never a prose interruption. The single `---` is the IEEE template's mandatory `\textit{Index Terms}---5G, ...` keyword-list boilerplate, not an authorial prose choice.
- Paper #3's extracted text contains 4 instances of a real em-dash character (`—`). Checked every one: **all 4 are the IEEEtran bibliography's "ditto" mark** (`[9] ——, "SLA-aware DRL for..."`, meaning "same author as the previous reference"), a citation-list convention, not prose.
- **Conclusion: the author never uses an em-dash to set off a parenthetical or an appositive in running prose, in either paper.** Where such an aside is needed, both papers use a comma instead (see the "trailing appositive" rule below).

### Semicolons: zero in flowing prose; used only inside structured lists and table cells

- Paper #4's `.tex` source: of 51 raw semicolon hits, every single one outside the author/ORCID block is inside TikZ node/draw code, a source comment, or a math-mode `\;` spacing command. The two hits inside the author block are the ORCID list (`W.~L.~Pang, 0000-0001-8407-5648;`), a structured metadata list, not a sentence. **A line-by-line scan of the entire body (Introduction through Conclusion, lines 290–630) found zero semicolons in prose.**
- Paper #3: 139 raw semicolon hits. Traced every one that appears outside a wide-column table row (a simple heuristic — genuine prose lines don't have 3+ runs of double-spacing from column alignment) and found exactly three contexts: (a) the PRISMA formal inclusion-criteria list, `(I1) ...; (I2) ...; (I3) ...; (I4) ...` — a numbered-criteria list, not narrative prose; (b) the author-biography paragraph's career/award timeline (`in 2019; and the Champion for...`); (c) dense evidence-table cells packing several statistics into one column (`98% acc.; 97.6% P; 97.1% R; 98.0% F1`). **Zero semicolons join two independent clauses in ordinary argumentative or descriptive prose, anywhere in either paper.**
- **Conclusion: semicolons are reserved for compact item-separation inside a structured list or a table cell. They are never used as a stylistic alternative to "and" or a full stop within a sentence.** Paper 5's current draft uses semicolons in flowing prose extensively (dozens of times) — this is a real, checkable mismatch with the author's own practice, to be corrected in S2.

### Colons: used, for exactly two purposes

- To introduce a list, including a single-sentence contribution/gap list: *"This paper makes the following contributions:"* (Paper #4, followed by a numbered list).
- To introduce a concrete elaboration or evidentiary example of a claim just made: *"Crucially, the framework is not a purely conceptual proposal, but rests on an incremental validation pathway: our prior single-gNB SAC study raised URLLC SLA satisfaction to approximately 99.5%..."* (Paper #3 Conclusion). This is a genuine "claim: evidence" colon, distinct from a list-introducer, and worth preserving as a pattern (Paper 5 already does this in places and should keep it).
- Colons are **not** used to bolt an afterthought onto an already-complete sentence (the AI-tell pattern "X happened: a real problem." with the colon doing no structural work). Every colon found introduces either an explicit list or a specific, concrete elaboration.

## Rule 1 — sentence length: not uniformly short; long sentences are built by comma-chaining, never by semicolon-splicing

The author's sentences vary widely, from very short (**"Both were validated only in simulation."** — 6 words, Paper #4 Intro) to quite long (**"Following a PRISMA-based protocol, we screened 6,286 records to 67 core studies from 2024–2026 and normalised each through a common evidence tuple, enabling a consistent, role-oriented comparison across admission control, resource allocation and offloading, orchestration, graph learning, and FL."** — 47 words, Paper #3 Conclusion). The long sentences are never semicolon-spliced two-independent-clause constructions; they are built from **one main clause plus a chain of comma-separated modifying phrases and a trailing participial clause** (`enabling...`, `raising whether...`, `confirming...`). A representative medium example: **"After finalising QoE calibration, a fully powered live evaluation across 128 episodes per arm demonstrated the QoE-aware DQN sustaining 100.0% eMBB/URLLC/mMTC SLA compliance on every episode, a statistically significant improvement over the static baseline's 93.9% slice-wide compliance."** (Paper #4 Abstract, 39 words, zero semicolons, one comma-set-off trailing appositive at the end).

**Rule for S2**: do not mechanically shorten every long sentence. Instead, wherever a long sentence currently uses a semicolon or an em-dash to join clauses, rebuild it as one of the author's own patterns: comma + coordinating conjunction (and/but/so), or a trailing participial/appositive phrase set off by a comma.

## Rule 2 — the trailing appositive: the author's actual "em-dash replacement"

Both papers close a high proportion of sentences with a short, comma-set-off noun phrase that glosses the significance of what was just said, functioning exactly where a lesser writer would reach for an em-dash:

- **"Both reach an identical 126/128, a genuine null result."** (Paper #4)
- **"The static baseline trails both at 120/128, its ceiling staying flat rather than rising toward the calibrated maximum."** (Paper #4)
- **"p90/p99 reach 84.6–85.1/108.9–115.0 μs across both reward modes, a small fraction of the 5-second control interval."** (Paper #4)

**Rule for S2**: whenever Paper 5's draft uses `—` (or `--` typed as a prose dash) to introduce a gloss, verdict, or aside, replace it with a comma and this trailing-appositive construction rather than a semicolon or a parenthesis.

## Rule 3 — section openings: "This [section/paper/review] [verb]s..." stating scope directly, third person

Every section opening sampled follows the same shape: a short sentence naming what the section itself does, no throat-clearing.

- **"This section reviews ten QoE-focused works from the verified pool of [3]."** (Paper #4, Related Work)
- **"This section describes the testbed and admission-control problem formulation, summarised by Fig. 1, with no new algorithmic framework proposed at this stage."** (Paper #4, Methodology)
- **"This review has shown that user-centric 5G NS can be advanced by pairing role-specific ML methods with optimisation-oriented formulations."** (Paper #3, Conclusion)

**Rule for S2**: open each major section/subsection with a plain "This [noun] [verb]s..." sentence stating its own content or finding, not a scene-setting or motivational lead-in.

## Rule 4 — voice: "we" for actions the authors took, third-person passive/nominal for what a metric or method does

Consistently: **"We evaluate a Deep Q-Network (DQN)-based approach..."**, **"We deploy a DRL-based SAC policy..."**, **"we screened 6,286 records..."**, **"we distilled recurring objective and constraint classes..."** for anything the authors did. But results/mechanisms are described impersonally: **"The SLA-only reward and the static-at-cap policy converge to a statistically indistinguishable compliance rate..."**, **"The comparative analysis confirms that DRL, MARL, GNN-assisted control, and FL are individually effective..."**. No passive-voice hedging like "it was found that" — the metric or method itself is the grammatical subject.

## Rule 5 — results introduced by naming the figure/table as the sentence's grammatical subject

- **"Table 1 summarises SLA compliance for all four arms across 128 live episodes each..."** (Paper #4)
- **"Fig. 3 plots DQN-QoE against DQN-SLA on the one seed where DQN-SLA collapses."** (Paper #4)
- **"Fig. 4 shows this episode-by-episode..."**, **"Fig. 5 shows two bars per arm."** (Paper #4)

Paper 5's own current style already mostly matches this (`Table~\ref{tab:m2-results} and Fig.~\ref{fig:m2-results} report the final, post-fix 30-seed campaign`) — confirmed compatible, no change needed to this pattern specifically.

## Rule 6 — hedging register: short, blunt negation, never elaborate hedging phrases

Limits and uncertainty are stated as direct negation, using **"but"** as the primary contrast word (not "however" mid-sentence, not "nonetheless") and **"However,"** only as a sentence-opener:

- **"However, static SAC cannot adapt as user demands shift, particularly in dynamic 5G environments."** (Paper #4)
- **"This traces in part to the simulator's backlog-capacity parameter, which was never validated against real SLA-margin magnitude."** (Paper #4)
- **"...but only DQN-QoE's gap is significant."**, **"...survives correction, but the SLA-only reward's does not."** (Paper #4 — note the terse elliptical "does not" standing in for "does not survive correction", a recurring economy)
- **"...single-agent, single-gNB deployment leaves open whether the E2 interface's per-slice ceiling primitive still suffices..."** (Paper #4, Conclusion/Future Work — "leaves open whether" as the limitation-framing verb phrase)

Zero instances anywhere in either paper of "it is worth noting", "notably" (as a sentence-opener), "underscores", "delve", or similar. "Furthermore" and "Overall" each appear exactly **once** across Paper #3's 20 pages (never as a repeated paragraph-opening tic) — rare enough to treat as effectively unused, not as license to sprinkle them through Paper 5.

## Rule 7 — multi-item limitations/contributions are enumerated as separate ordinal sentences, not packed into one clause-chain

Paper #3's Future Work section is the clearest evidence: **"Five validation directions should precede any deployment-level claims. First, inferred MOS should be calibrated against objective MOS and ACR-style labels to confirm alignment with user-perceived QoE. Second, topology scalability should [...]. Third, differential privacy trades inference accuracy for protection in proportion to the privacy budget, whose per-slice calibration is deployment-specific. Fourth, the O-RAN Near-RT and Non-RT RIC layers impose strict latency budgets [...]. Finally, real-time QoE inference depends on feature-pipeline latency and model footprint..."** Each limitation/direction is its own complete sentence, opened by an ordinal transition word (First/Second/Third/Fourth/Finally). Paper #4's numbered contribution list uses the same device via an explicit `\begin{enumerate}` after a colon.

**Rule for S2, direct implication for Paper 5's own Conclusion**: the "four limits" paragraph (already compressed once in M57 to three dense, semicolon-joined sentences) should be re-cast as one lead sentence plus four short ordinal sentences (First/Second/Third/Fourth), matching this exact, well-evidenced authorial convention, rather than staying comma/semicolon-packed.

## Rule 8 — vocabulary level and recurring terms of art

Precise, technical, unhedged nouns rather than adjectives doing the work: "a genuine null result", "a real, delayed consequence" (Paper #4, of an admission decision), "an incremental validation pathway" (Paper #3). Recurring citation-introduction phrasings in Related Work: **"The authors in [X] used/showed/reported..."**, **"Another study [X]..."**, **"Closest to the present setting, ... none deploying..."** (a "closest prior art" framing sentence at the end of a Related Work paragraph, stating precisely what the closest work still doesn't do — Paper 5 already has a close cousin of this pattern in its own Related Work). "Namely" is the author's standard list-introduction word (**"...three core service categories, namely..."**, **"...five recurring gaps, namely QoE inference, topology awareness..."**) — Paper 5 should prefer "namely" over "specifically" or "i.e." for the same function.

## What this means for Group S2 (not executed in this gate)

1. **Remove every em-dash in `main.tex`** (both literal `--`/`---` typed as prose punctuation and the earlier milestones' occasional use of `--` as a parenthetical dash — number ranges like `900--909` are NOT em-dashes and must stay). Replace each with a comma + trailing appositive/participial clause, a full stop, or a comma + coordinating conjunction, chosen per the specific sentence.
2. **Remove essentially all prose semicolons.** Paper 5's current manuscript uses many; the target rate, backed by an exhaustive count of both reference papers, is zero in flowing prose. Replace with a full stop or comma + and/but/so. Keep a semicolon only if introducing a genuine structured list of 3+ short parallel items (matching the PRISMA-criteria/ORCID-list precedent) — expected to be rare to nonexistent in Paper 5's own prose.
3. Recast the Conclusion's four-limits paragraph into a lead sentence + First/Second/Third/Fourth ordinal sentences (Rule 7).
4. Leave colons where they introduce a list or a concrete "claim: evidence" elaboration; don't add or remove colons elsewhere.
5. Leave the existing "Table/Fig. X [verb]s..." results-introduction pattern and the "This [section] [verb]s..." section-opening pattern alone where already present — both already match.
6. Do not introduce "moreover/furthermore/notably/it is worth noting" — they are absent (or used at most once, coincidentally) from the author's own practice.
7. Every rephrasing must preserve the exact meaning, number, and caveat of the sentence being touched — this gate changes voice, not content.

## STOP

Reported per the milestone's own gate. No edits made to `main.tex`. Awaiting approval of these rules before Group S2 begins.
