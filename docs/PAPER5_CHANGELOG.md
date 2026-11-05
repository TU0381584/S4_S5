# Paper 5 (WPC) changelog

Format: timestamp | step | file(s) | change | reason | verify status

2026-11-05 21:46 | F1 | none | skipped, AI disclosure stays in Online Resource 1 S4 | author decision 2026-11-05 | n/a
2026-11-05 21:46 | F2 | none | skipped, data and code stay available on request | author decision 2026-11-05, no archive exists yet | n/a
2026-11-05 21:46 | F3 | docs/PAPER5_REF_AUDIT.md | new audit of refs [2] [6] [9] [10] [12] [14] [20] [23] [35] against Crossref, bib unchanged | external review request | n/a
2026-11-05 21:46 | F4 | main.tex Sec. 7 | fourth limitation replaced: per-gNB penalty raised compliance 10.7 points at 7 gNBs ring (Holm p=0.007) but per-gNB compliance only 1.9 points at 19 gNBs hex (p=0.65) | old sentence said the penalty changed neither compliance nor standing, contradicted by Table S7 | m66_verify 686/686, m82 63/63
2026-11-05 21:46 | F4 | m66_verify.py | two checks tie the new sentences to m79/pergnb_n7_ring and m76/c_pergnb_n19_hex | keep every quoted number verified | 686/686
2026-11-05 21:46 | F5a | main.tex abstract | added that a tuned rule beats every learner at its tuning conditions; overload sentence moved next to it | balance | 686/686
2026-11-05 21:46 | F5a | m66_verify.py | check that the tuned rule out-earns every learner in Env B at 3, 7 and 19 gNBs on reported and fresh seeds, and the static rule in Env A at 3 gNBs | verify the new clause | 686/686
2026-11-05 21:46 | F5b | none | delay ratio already computed from unrounded values, 7.02 and 43.93, kept as 7 to 44 | verified | 686/686
2026-11-05 21:46 | F5c | main.tex abstract | 250 to 245 words: 37-gNB sentences merged (99.8% URLLC served now only in the conclusion), parameter counts shortened to up to 682,058, final sentence shortened | word target | 686/686
2026-11-05 21:46 | F5c | m66_verify.py | abstract URLLC-served check retired, delay-ratio and parameter anchors updated | text moved | 686/686
2026-11-05 21:46 | F7 | main.tex Sec. 7 third limitation | the per-node variant shares parameters but passes no messages, so the gain at scale comes from parameter sharing and per-slice heads | placed in Sec. 7, since any added line in Sec. 6.3 pushes Fig. 6 off page 15 | 686/686
2026-11-05 21:46 | F8 | main.tex Sec. 7 | fifth limitation: rules re-tuned only offline, online re-tuning not tested | external review | 686/686
2026-11-05 21:46 | F6 F9 | none | proposals only, awaiting author approval | review request | n/a
2026-11-05 21:46 | F10 | main.tex, submission/ | self-count 686, package rebuilt | rebuild | 686/686
2026-11-05 21:55 | F9 | main.tex abstract and Sec. 1, supplementary.tex S1 | AXIOM now expands to Adaptive Cross-cell Integrated Orchestration of Multi-slice admission; the integrity-aware gloss is removed and O-RAN is still defined at first use in Sec. 1 | author chose option 2 | see F10b
2026-11-05 21:55 | F6 | main.tex Table 1 and Sec. 2 | AXIOM row graph encoder "Shared GAT or MLP" (shorter than proposed, so the row keeps two lines and no float moves); related-work sentence now says none pairs per-slice admission with a size-independent shared controller and evaluates it against trivial and tuned rules on independent seeds | author approved after checking the six works | see F10b
2026-11-05 21:55 | F10b | main.tex, supplementary.tex, submission/ | abstract 243 words, main 25 pages and OR1 12 with floats unchanged, package rebuilt | rebuild | m66_verify 686/686
2026-11-05 22:37 | G1 | experiments/plots/paper5_fig_superiority.py, figures/fig10_axiom_superiority.* | Fig. 8b and 8d radar polygons no longer filled; panel e x label "Offered load, %" (the old "Offered load at 19 gNBs, %" lost its % at the right edge; the caption already says 19 gNBs) | author request, glitch | summary JSON byte-identical, CVD views checked
2026-11-05 22:37 | G2 | experiments/plots/paper5_fig_decision.py, figures/fig_decision.* | typographic apostrophe in "gNB’s own URLLC queue" | glitch | summary JSON byte-identical
2026-11-05 22:37 | G3 | main.tex Sec. 1 | 43-word sentence on seeds split in two | style rule, 40 words at most | see G5
2026-11-05 22:37 | G4 | supplementary.tex S4, m82_audit.py | 43-word sensitivity-study sentence split in two; audit anchor updated | style rule | see G5
2026-11-05 22:37 | G5 | both manuscripts, submission/ | full re-check: acronyms, British spelling, captions at most 3 lines, every float cited, no undefined references or overfull boxes, fonts embedded | author request | m66_verify 686/686, CI recompute 22/22
2026-11-05 23:52 | H1 | main.tex Sec. 5.3 | Table 5 (evaluation failures) replaced by Fig. 4, a TikZ protocol diagram: the pipeline from plan to reported result, the three gates, each failure a check caught with its outcome, and dashed arrows to the step each failure changed | author request, new diagram | see H4
2026-11-05 23:52 | H2 | experiments/plots/paper5_fig_regime.py, figures/fig_regime.*, main.tex Sec. 7 | new Fig. 10, where AXIOM beats a rule per cluster size and load, paired Wilcoxon with Holm per panel, cells from existing runs only | author request, new diagram | see H4
2026-11-05 23:52 | H3 | main.tex | complexity table moved before the superiority figure with [!b], so it sits on the page that cites it; main now 26 pages | float placement after the new figures | see H4
2026-11-05 23:52 | H4 | m66_verify.py, paper5_regen_wpc_figures.sh | two checks recompute Fig. 10 from the logs and tie it to the text; regen script draws it; self-count 688 | keep every plotted number verified | m66_verify 688/688
