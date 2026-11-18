# WPC pre-submission correction pass, change log (2026-11-18)

Format: file, location, old -> new, reason. M = main.tex, S = supplementary.tex (Online Resource 1), B = refs.bib.

## Phase 0 (read-only, results reported to the author)
V1 text 4.2/3.9/4.99 is the paired hex lead; Table S8 caption said 1,620 runs but its cells are the pooled 2,130. V2 13 of 165, 56.4-66.8%. V3 accept-all 67.08% (19) and 61.94% (37). V4 12 seeds, 7 ties. V5 gap at 19 gNBs is at most 3.12 pooled / 3.76 per layout, so "5.3" is unsupported. V6 QMIX -0.288 reward, Holm p 1.0. V8 nine failed checks listed in the reply. V10 58 of 58 DOIs resolve (302).

## Phase 1 (main)
- M abstract: replaced by the supplied 249-word text. Reason: 1.1. The "3.9 to 5.0" stays (Phase 0 V1 confirms 4.99).
- M Sec 3: "exposes to xApps, the external control applications of O-RAN" -> "exposes to external controllers through its E2 agent", with \cite{cheng2024oranslice} after OAI. 1.2.
- M Sec 3: control-step sentence now names the 10 ms to 1 s near-real-time RIC loop. 1.3.
- M Sec 3: "which saturates in Env B at nineteen gNBs" -> "which falls to a floor ... where it no longer separates the policies". 1.4.
- M Sec 5: "same 60 seeds" -> "same 60 seeds plus 15 more, 75 in all"; "Every campaign" -> "Unless stated otherwise, every campaign". 1.5. (The phrase "same 60 seeds" is kept inside the new wording, as the instruction's own text contains it.)
- M Sec 5: "Block precision $\pi = b/b$" -> "Block precision, $b_{mMTC}/b$,". No other use of pi for precision exists. 1.6.
- M Sec 5 safeguards: validation-screen sentence moved to the end of the paragraph. 1.7.
- M Sec 5: "above 99.98%" -> "at 99.97% or more". 1.8.
- M Sec 5 end: AI-assistant sentence added, pointing to Sec 6.6. 1.9.
- M Sec 6: mMTC admission 60.9% vs 5.5% -> 60.7% vs 7.6% (pooled, same as Sec 6.1). 1.10.
- M Sec 6.1: p = 0.007 -> 0.0066 (verifier to confirm in Phase 3). 1.11.
- M Table 3 header W/T/L (n = 60) -> (n = 75). The Env B table keeps n = 60, which is correct. 1.12.
- M Sec 6.2: "each layout-independent baseline was run once per seed" merged into the 37-gNB paragraph. 1.13.
- M Sec 6.2: "no other learner" -> "none of DQN-SA, DQN-I, and MAPPO"; QMIX sentence added. 1.14.
- M Sec 6.4: static-rule-over-tuned-rule sentence added (source: S7, 8.05 to 10.63; 1.8 to 2.0). 1.15.
- M Sec 6.7 heading -> "Live Testbed Check". 1.16.
- M Sec 6.6 and S1: "except the one reused rerun disclosed in Section 5" / "except the reused rerun that Section S4 discloses". 1.17.
- M Sec 7: rules paragraph rewritten as supplied, but "as Fig. 10b shows" replaced by "(Section S7 of Online Resource 1)". Reason: Fig. 10 is the capability figure and Fig. 11b compares AXIOM with the tuned rule only, so neither shows static over tuned; the source is OR1 S7. 1.18.
- M Sec 7: MLP-encoder exception added after "No learned baseline earns significantly more reward". V6 shows QMIX is not significantly ahead, so QMIX is not added. 1.19.
- M Sec 7: "Among the learned controllers of Fig. 10". 1.20.
- M Sec 8: "every learned baseline stays below 84%" -> "DQN-SA, DQN-I, and MAPPO stay below 84%". 1.21.
- Fig. 8 tick label "Tuned neighbour rule": left for Phase 4. 1.22.
- M Table 5: no change. The AXIOM row already has "--" in both W/T/L cells. 1.23.
- M Declarations, AI item: now "Claude Code (Anthropic), running Claude Opus models in Visual Studio Code". AUTHOR TO CONFIRM IDE and whether the AI drafted manuscript prose; if so, state it explicitly. This replaces the wording the author gave on 2026-11-18. 1.24.
- B ORANSlice: NOT changed. Crossref for 10.1145/3636534.3701544 gives the title "ORANSlice: An Open Source 5G Network Slicing Platform for O-RAN", the container "Proceedings of the 30th Annual International Conference on Mobile Computing and Networking" and the author order already in refs.bib. The supplied workshop title, booktitle and author order do not match the DOI record. AUTHOR TO DECIDE.
- B page ranges in number fields {3-4} -> {3--4} (2 entries). 1.25.
- B Patterson et al.: url https://jmlr.org/papers/v25/23-0183.html added; the page title is "Empirical Design in Reinforcement Learning". 1.25.
- B OACR2: title is "{OACR$^{2}$}: Online ..." which renders with no space before the colon. No change. 1.25.

## Phase 1E (Online Resource 1)
- S S6: garbled ".7% and 92.0%" removed. E1.
- S S4: live-testbed sentence now reports the PRB grants below the five-PRB floor found before the root fix. E2.
- S Table S2 caption: sentence on the 15 newest seeds (Table S4) and 75 seeds added. E3.
- S S5: "pooled over these 40 seeds, the 30 primary and 10 replication seeds and not the 75-seed sample of the main paper". E4.
- S S7: "In Env B," added before "past the tuning load at nineteen gNBs". E5.
- S Table S12 p values: 8.8e-05 and 1e-05 -> <0.0001; 0.00016 -> 0.0002. E6.
- S S8: duplicate definition of normalised backlog removed. E7.
- S S4 Eqs (1) and (2): attention logits renamed e (epsilon kept for DP); N_i includes i; the second equation reads h_j^(1) and is stated to be the final layer. Self-loops are on by default (framework topology.py). E8.
- S Table S17: Fig1 to Fig11; "m97" -> m104_run.py, plus m109_run.py; seed list extended. m97 is an analysis script, not a runner. E9.

## Phase 2 (author approved the recommendations)
- S Table S8 caption: "1,620 stored runs" -> "2,130", with a note that the 37-gNB AXIOM cell pools three layouts (165 runs) against hex-only baselines (75 runs). P1.
- S S6 text: the 37-gNB lead of 4.99 is stated as the paired hex value. The abstract, Sec 6.2 and Sec 8 keep "3.9 to 5.0". P1.
- S S6: "AXIOM's nine collapsed runs keep 57% to 65%" -> "13 collapsed runs of 165 keep 56% to 67%", the same as the main paper. P2 (the stale sentence was found in the rendered PDF).
- P3: no change. Accept-all is 67.08% and 61.94% on the 30 hex seeds, and no tuned baseline is above it.
- S S7: "within 5.3 points ... 105% to 120%" -> "within 3.1 points at 105% (all layouts pooled), 2.1 at 110%, and 0.2 at 120% (hex layout)". P4.
- M Sec 6.2: "within 5.8 at thirty-seven" -> "within 5.8 at thirty-seven, or 5.2 on the hex layout alone". P4.
- M Fig. 11 caption: sentence on which layout each cell uses. P4.
- S S5: new paragraph with the shared-head (9 of 15, 65.9% vs 96.8%, Holm p 0.0004), joint-target (Holm p >= 0.26) and sensitivity (gaps -0.07, -0.13, -0.12) numbers; federation pooled over 30 seeds (+0.491, CI [-0.08, 1.09], p = 0.14) and DP-SGD drops (1.02, 1.07, 0.77, 1.25; Holm p 0.63) after the zCDP paragraph; S3: 14 and 48 loss readings, all 0.000%. P5.
- S S2: new Table S-failed with the nine failed fresh-seed checks (criterion, value, threshold), cited from S2. P6.
- P7: none of the 58 DOIs fails, so nothing was edited.

## Phase 3 verifier updates (strings changed only where the new value is proven)
- m66_verify.py: p of the static rule over AXIOM now 0.0066 (printed to 4 decimals); the "within 5.3" check now tests 3.1 / 2.1 / 0.2 and 5.2 from the same paired cells as Fig. 11a; quoted abstract, Sec 6, Sec 7 and Sec 5 sentences updated to the new wording; S12 p-value format; new check for the 13 collapsed runs and the 56-67% range (770 checks now; main.tex quotes 770).
- m82_audit.py: Table S12 p parser accepts "<0.0001" and 4-decimal values (round-to-printed-digits instead of 6% relative tolerance); quoted strings for seeds, abstract and Table S17 updated.

## Table 1 and Section 2 corrections (verified against full text, as the author instructed)
- M Table 1 body: all five prior-work rows reset to the supplied cells (Sulaiman: multi-agent ✓^a, max cells 9^b, size-invariant ✗, transfer ✗; Ahmadi: ✓^a, graph ✓^c, 52^b, size-invariant ✓^d, transfer ✓, rules ✓; Zangooei unchanged in content; Mohajer: federated ✗, n.r. for cells, size-invariant and transfer, rules ✗; Bouroudi: multi-agent ◐^f, graph ✓^g, transfer ✗, rules ✓). Footnote-f markers removed from the three name cells. Existing macros only (\gyes, \gpart, \gno, \gnr). Reason: verified against full text.
- M Table 1 AXIOM row: footnote letters c, d -> h, i. Reason: letters now follow first appearance.
- M Table 1 legend and footnotes: replaced by the supplied a to i block; the "Full text not available to us" note deleted. No stale marker remains (a to i all appear in the body and in the legend; checked on the rendered page, docs/table1_page5.png).
- M Sec 2: Ahmadi sentence (3.1), "Two more core studies ..." (3.2) and "Beyond comparisons with greedy admission ..." (3.3) replaced as supplied.
- M Sec 2: closing paragraph before "Robustness studies" (3.4) replaced by the supplied text. The first search for the end of the old passage matched an earlier "independent seeds." and left the old last sentence behind, which duplicated the Table 1 sentence; that leftover was removed.
- M Sec 1, contribution 1: sentence on size transfer precedent [1] added (Phase 4).
- M layout: the longer legend and Section 2 text pushed the paper to 28 pages and left a 44% gap on page 22, because the class's widow and club penalties forced the Conclusion heading to the next page. Set \widowpenalty=100 and \clubpenalty=100 after \setcounter{totalnumber}{5}. Back to 27 pages with the earlier float spacing, no gap above 6%.
- m66_verify.py: Table 1 AXIOM-row check now quotes footnote letters h and i. Verifier 770/770 (full uncached run flagged only this string; the cached rerun passes). Submission package rebuilt.

## 2026-11-18 author action list (15 items)
- 1 Sizes: Section 3 now says 1 gNB is the live rig and earlier studies, 3 the smallest fully connected cluster, and 7, 19, 37 the hex clusters with one, two, three rings around a centre gNB. No recorded reason for stopping at 37 was found in the preregistrations, so none is stated.
- 2 Abstract, Introduction and Section 7: "cannot follow the load" now "cannot adapt to dynamic load".
- 3 Abstract sentence replaced by the "self-learning capability ... manually tuned rules" framing; Section 7 opening and the Conclusion's closing sentence rewritten as a trade-off (small share of reward under known conditions against scalability and tuning-free adaptation).
- 4 Abstract and Conclusion: per-gNB lead stated as about 4% to 5% more compliance (Table S8 per-gNB means: 98.4 to 99.3 against 93.9 to 95.1), and the 37-gNB lead as 63% more cluster-level compliance (94.2 against 57.9). Fresh-seed 36.5-point clause dropped.
- 5 Abstract: "though not at 19" removed. Conclusion: "not a replacement" and "still earns the most" sentences removed.
- 6 Fig. 1 float moved to the bottom of page 2 (float placed before the second Introduction paragraph, option b).
- 7 Introduction: "AXIOM targets this setting." merged into the next sentence; "Fig. 1 shows the system context." merged into the preceding sentence.
- 8 "5 s" now "5 seconds" / "5-second"; "10 ms to 1 s" now "10 milliseconds to 1 second".
- 9 Fig. 1 PRB bar: mMTC segment lightened to 45% tint and white separators added, in the figure and its legend swatch.
- 10 Contributions 1 to 4 shortened (see word counts in the commit).
- 11 Env A and Env B defined as Environment A (Env A) and Environment B (Env B) at first use.
- 12 Table 1 legend cut from 123 to 97 words.
- 13 Experimental Setup first paragraph cut by about 30%; seed ranges removed, per-layout counts kept.
- 14 Fig. 4: step badges moved clear of arrowheads and diamond leaders.
- 15 Declarations: "Opus agents running in Visual Studio Code were used ...".
- Verifier count now 767 (three fresh-seed and per-point abstract/conclusion claims replaced by one per-cent check); main.tex quotes 767. Abstract 248 words after trimming the protocol sentence.
