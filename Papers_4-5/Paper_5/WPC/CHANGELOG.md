# Figure and table audit, CHANGELOG

Branch `fig-audit`, tag `pre-audit` (= commit 8adad9ff). One entry per item: old id -> new id, verdict, files touched, checks passed.
Fig. 10 (Option A) is frozen and not touched.

## Phase 0, setup

| Item | Old id -> new id | Verdict | Files touched | Checks |
|---|---|---|---|---|
| 0.1 branch and tag | n/a | done | git: branch fig-audit, tag pre-audit | n/a |
| 0.2 shared style | n/a | done | figures/axiom_style.py (new) | smoke test: 84 mm figure saved as PDF and EPS, LiberationSans embedded as TrueType in both; width, 7 pt, 0.3 pt, overlap and clipping checks raise as intended (a clipped tick label in the test layout was caught) |
| 0.3 reference inventory | n/a | done | refs_before.txt (new): 19 main labels (11 fig, 7 tab, 1 alg) and 19 ESM labels (8 fig, 11 tab) with numbers and pages, and all 64 \ref sites with targets | n/a |
| Gate 0 | n/a | PASS | main.tex, supplementary.tex compiled before any edit | main 29 pp, ESM 9 pp; 0 errors, 0 LaTeX warnings, 0 undefined references, 0 overfull boxes in both |

### Phase 0 notes for the author

- Width rule. The brief allows 84 mm or 174 mm. The measured sn-jnl text block is 130.7 mm (`\textwidth` = 372 pt), and the submission so far keeps figures at or under 119 mm. A 174 mm figure is wider than the text block; scaled to fit, 8 pt text prints at 6.0 pt, under the 7 pt minimum. axiom_style.py implements the brief's widths as written and documents this; it is not used for any figure until the author decides.
- Number check. There is no verify_numbers.py; the paper's independent verifier is experiments/scripts/m66_verify.py (652 checks, 57 of them the M82 audit). It matches many table rows as exact strings, so Phase 2's reformatting (fractions to %, siunitx, new CI columns) changes those strings; each affected check will be rewritten to the new format, not deleted.
- Gate 4 asks that every number in the text be unchanged except ids. Phase 2.1 (fractions to %, 1 dp) and 2.2 (new CI columns) necessarily change printed digits without changing results; those will be listed item by item as format changes.

## Author decision (2026-11-08)

"Proceed with your best judgment without compromising integrity; if in doubt, retain the existing arrangements." Applied as:
orphaned Env B claims kept with their own numbers in the text (checked); radar-only "leads on five/four of six" claims
dropped, their unfavourable facts kept as plain statements; figure widths 84 mm and 119 mm (the existing arrangement)
instead of 174 mm; verifier checks rewritten to new formats or re-pointed to where the value now lives, never deleted.

## Phase 1, removals and moves: pre-edit claim check

Sites that cite an item Phase 1 removes or moves (from refs_before.txt), and where their claims would rest afterwards:

| Site | Cites | Claim | Support after Phase 1 |
|---|---|---|---|
| main:346 | Fig. 3b | federated variant described | Fig. S4a in OR1 (moved panel); cite it there |
| main:423 | Table 3 | "sets out how the four learned policies stand" | no specific claim; recite Fig. 5 and Table 7 (new Table 6) |
| main:490 | Table 3 | AXIOM collapses more often at 37 than at 19 gNBs | Fig. 5b already plots the collapse share by size; recite Fig. 5b |
| main:563 | Fig. 8 | per-gNB compliance maps, Env B 19 gNBs | moved to OR1; cite it there |
| main:574, sentence 1 | Fig. 9a | Env A: AXIOM 4.2 to 4.7 reward per gNB, above 93%, baselines lose compliance with size | Fig. 5c after the move (reward per gNB against N) with Fig. 5a |
| main:574, sentences 2 to 4 | Fig. 9c | Env B: every policy loses compliance as the cluster grows; AXIOM most reward per gNB and compliance at 3 and 19 gNBs; about level with DQN-SA on reward per gNB at 7, where DQN-SA keeps more compliance | ORPHANED in part: 3 gNBs in Table 6 (new 5), 19 gNBs in Table S8; the 7-gNB pooled Env B values exist only in Table 3's last row and Fig. 9c |
| main:574, sentences 5 to 7 | Fig. 9b, 9d | radar: Env A AXIOM leads on five of six measures, MAPPO on collapse resistance; Env B AXIOM leads on four, DQN-SA on both measures at seven gNBs | ORPHANED: only the radar panels support them |
| main:574, last sentence | none (Fig. 11) | Env A at 19 gNBs AXIOM within 5.3 points of the static rule from 105% to 120% load | unaffected |

Values printed only in Table 3, which deleting it removes from the paper (no sentence quotes them): Env A priority-slice compliance at 7 gNBs (AXIOM 97.1%, DQN-SA 76.2%, DQN-I 74.6%, MAPPO 67.7%; Fig. 5a plots them) and Env B priority-slice compliance at 7 gNBs (35.1%, 44.3%, 39.9%, 35.9%). The collapse counts at 19 and 37 gNBs are plotted in Fig. 5b; the 37-gNB counts are also in Table S3.

Resolved by the author's decision above.

### Phase 1 entries

| Item | Old id -> new id | Verdict | Files touched | Checks |
|---|---|---|---|---|
| 1.1 Table 3 (tab:compare) | Table 3 -> deleted | done | main.tex; Design row -> Design column of old Table 7 (now Table 6); Parameters row already in that table per size | the 37-gNB values re-pointed to OR1 Table S3 and the text; 19-gNB values to Fig. 5a/5b summary; Env B 19-gNB rewards to Table S8; Env A 3-gNB rewards to Table 3 (old 4) |
| 1.2 Fig. 9 (fig:quadrant) | Fig. 9 -> deleted | done | main.tex; figures/fig10_axiom_superiority.* removed (git rm); paper5_fig_superiority.py kept as a module (shift_row, LOAD_B used by Figs. 8 and 9), dropped from the regen script | Env A reward per gNB moved to Fig. 5c (paper5_fig_scaling_trend.py), values identical to old 9a (AXIOM 4.23 to 4.71); verifier checks Fig. 5c against the logs; Env B per-size claims now quote 65.1, 35.1, 24.7, 3.36, 3.37, 44.3 (claims recomputed from the logs); radar checks replaced by a check of "MAPPO is the only learned policy that never collapses at thirty-seven gNBs, where AXIOM collapses in 6 of 60 runs" |
| 1.3a Fig. 8 (fig:pergnb) | Fig. 8 -> Fig. S8 (S7 before the new interval figure) | done | main.tex (figure removed, sentence cites Section S7 of Online Resource 1), supplementary.tex (figure after Table S8 with a pointer sentence) | figure file unchanged |
| 1.3b Fig. 3b | Fig. 3b -> Fig. S4a | done | figures/fig1_gat_ctde_fl_architecture.tex split into fig_architecture.tex (main Fig. 3, scale 0.81 as before) and fig_fed_variant.tex (OR1 Fig. S4a); privacy panels relabelled b and c (paper5_fig4_m3_privacy.py); main sentence cites Section S5 of Online Resource 1 | pdflatex standalone builds |
| 1.4 references | n/a | done | main.tex, supplementary.tex | main and ESM refer to each other only by section, so no hard-coded ESM numbers broke; refs_after_phase1.txt: 0 unresolved |
| Gate 1 | n/a | PASS | both compile, 0 warnings, 0 undefined, 0 overfull | verifier 657/658 (the one failure was a check edited for Phase 2 while the run was in flight; it passes in the Gate 2 run) |

## Phase 2, tables

| Item | Old id -> new id | Verdict | Files touched | Checks |
|---|---|---|---|---|
| 2.1 Env A results | Table 4 -> Table 3 | done | main.tex: siunitx, CI in its own column, rule above a midrule, W/T/L header with n = 30, compliance as % to 1 dp under a grouped header, row tint removed; precision kept as a fraction (it is a share of blocks, not a compliance) | rows generated by experiments/scripts/audit_table_rows.py from the logs (percentages from unrounded means, CIs identical to the printed ones); verifier T3 checks rewritten to the new format; CI recompute 19/19 same |
| 2.1 Env B results | Table 6 -> Table 5 | done | as above; W/T/L grouped header with n = 30 | as above, T4 checks rewritten |
| 2.2 transfer | Table 5 -> Table 4 | done | main.tex: 95% CI column beside each learned policy's compliance, from the M92 analysis summary (the source of Table S6) | verifier rows92 check rebuilt with the CIs |
| 2.2 Table S6 | Table S6 | trimmed | supplementary.tex: reward and collapses only; the MLP variant's compliance and CI, which no other place prints, moved into the caption | verifier c6 check rebuilt, caption sentence checked |
| 2.3 related work | Table 1 | done | main.tex: glyphs (checkmark, half disc, cross, n.r.) with a key; columns Max cells, Size-invariant params, Zero-shot size transfer, Rule baselines; "Not described" -> n.r. | new verifier check on the AXIOM row |
| 2.3 author verification needed | Table 1 | open | every new prior-work cell is n.r. (30 cells: Max cells, Size-invariant params, Zero-shot size transfer, Rule baselines for Shao, Sulaiman, Ahmadi, Zangooei, Mohajer, Bouroudi); no prior-work fact was added | author to confirm or fill from the papers |
| 2.4 parameters | Table 2 | done | main.tex: Slices / Simulator / Learning group rows with cmidrules; every pair line unchanged | M82 Table 2 checks pass unchanged |
| 2.4 complexity | Table 7 -> Table 6 | done | Design column added (Phase 1), digits grouped with commas, row tint removed | verifier and M82 complexity rows updated |
| 2.5 rliable table | Table S2 -> Online Resource 2 (ESM_2.csv) | done | experiments/scripts/audit_esm2_csv.py writes ESM_2.csv at full precision from m93_summary.json; OR1 sentence points to Online Resource 2; make_submission.py ships ESM_2.csv | verifier compares every CSV value with the recomputed summary |
| 2.5 reproduction figure | Fig. S8 -> Table S11 (tab:repro) | done | supplementary.tex: two-part table, every item's text verbatim; step 7 now names Fig1 to Fig9 and ESM_2.csv | M82 S9 checks match unchanged |


## Phase 3, figures

Gate 3 for every figure: width by `axiom_style.check` (84 or 119 mm; Fig. 8 frozen at 119 mm), no text under 7 pt (all data figures 8 pt), no line under 0.3 pt, no overlapping or clipped text; caption colour-word scan clean for all 18 captions; token separation (CAM02-UCS) AXIOM/learned 28.1, AXIOM/rules 62.4, learned/rules 35.1, under deuteranomaly 28.1/56.2/29.1, protanomaly 24.0/49.1/26.7, tritanomaly 21.5/59.4/38.1; greyscale dL* 7.2/8.2/1.0, so learned against rules relies on marker fill and shape, which differ in every figure; previews in figures/audit_previews/. EPS is written beside every data figure; CI bands are opaque tints with drawn edges, since EPS has no transparency (a first rasterised attempt rendered opaque and was replaced).

| Item | Old id -> new id | Verdict | Files touched | Values traced to |
|---|---|---|---|---|
| 3.1 Env B, three gNBs | Fig. 7 | done, 84 x 52 mm | paper5_fig_envB.py rewritten: horizontal strips (six labels collided at 84 mm in columns), tuned local and neighbour-aware rules hollow with CIs, dashed line at the tuned local rule's mean, AXIOM column shading and Env badge removed; caption | m64/n3_fully_connected eval logs; means and CIs equal Table 5; new verifier check |
| 3.2 scaling | Fig. 5 | done, 119 x 104 mm | paper5_fig_scaling_trend.py drawing: a, per-run dots, mean, CI, static rule; b, collapsed share with Wilson 95% intervals; c, reward per gNB with CIs; direct labels 93.7% and +35.0 pp from the summary; caption fixed (it still named the parameters panel after Phase 1) | m65_n3_view, m65_scaling, m73, m70/R1 logs; summary schema unchanged; Wilson intervals checked by the verifier |
| 3.3 37-gNB gate map | Fig. 6 | done, 119 x 118 mm | paper5_fig_gnb_map.py: flat-topped three-sector hexes, cividis 0 to 1, shared colour bar, headers "SLA x% · collapsed k/n" (2 x 2, since four across left 27.5 mm for a 37 mm header), Env badge removed; caption reworded (no "coloured"), headers noted as hex-layout values | m73/A_n37_hex logs; summary unchanged in content |
| 3.4 per-gNB map | Fig. 8 -> Fig. S8 | done, 119 x 58 mm | paper5_fig_pergnb_envb.py: same hex template, one value per cell, cividis on the existing 50 to 85% range, centre outlined, Env badge removed; main text "dark purple ... pale yellow" -> "dark ... light" (verifier check updated) | m75/D_envB_n19_hex per_gnb_sla.json |
| 3.5 regime map | Fig. 11 -> Fig. 9 | done, 119 x 62 mm | paper5_fig_regime.py: AXIOM ahead #0072B2 and rule ahead #D55E00 at 35% (pre-blended), rule ahead hatched in vermillion, no significant difference in a light neutral (dL* about 14 from the AXIOM tint), values in every cell, dashed tuning-load box, Env badges removed; caption without "Colour" | fig_regime_summary.json, verdicts recomputed by the verifier |
| 3.6 protocol | Fig. 4 | done | main.tex TikZ: serpentine of ten steps, gates as diamonds, callouts a to g of at most four words with a cross (or a check for the cleared testbed floor), every outcome and back-step in the lettered caption key, no fills | text of the former callouts, unchanged in substance |
| 3.7 environment flow | Fig. 2 | done | main.tex TikZ: three swimlanes (Env A, both, Env B), at most six words per box, no fills; details only the boxes carried (ceiling moves, a reject relieving one request's demand, the 10% drift with the M82-checked phrase, episode start) moved into the preceding paragraph | M82 simulator-constants check passes on the moved phrase |
| 3.7 architecture | Fig. 3 | done | figures/fig_architecture.tex: fills removed, "7,782 parameters at execution, the same at every cluster size" added | m64/complexity.json, m73/complexity_n37.json; new verifier check |
| 3.7 system view | Fig. 1 | done | main.tex TikZ: slices told apart by icon, label, position and border style (solid, dashed, dotted); icons and UEs in neutral ink; core and gNB fills removed | n/a |
| 3.8 forest | Fig. S1 | done | paper5_fig_forest.py: Env band tints and badges removed, divider line instead | unchanged rows |
| 3.8 performance profiles | Fig. S2 | done, 4 x 2 | paper5_fig_rliable.py: Env A down the left, Env B down the right, legend in the last cell; tokens of axiom_style (learned grey by line style, rules vermillion); caption without "Shaded" | m93_summary.json |
| 3.8 IQM and P(improvement) | new Fig. S3 | done | new paper5_fig_rliable_intervals.py; OR1 figure and pointer sentence; regen script | m93_summary.json; verifier compares every plotted value |
| 3.8 federation | Fig. S4 -> Fig. S5 | done, 3 panels | a, the federated-variant diagram (Phase 1); b, c, the privacy panels (relabelled), Env badge untinted | unchanged |
| 3.8 disruption | Fig. S5 -> Fig. S6 | no data change | the panels already carried 95% CIs (bootstrap over seeds, named in the caption); Env badge untinted | unchanged |
| 3.8 decision probe | Fig. S7 -> Fig. S9 | done | paper5_fig_decision.py: one panel, the visit histogram as a marginal on the same queue axis, tuned rule step in vermillion, Env badges removed; caption | m81 probe summary |
| shared env badge | all figures using paper5_common.env_tag | done | env_tag prints plain text in ink, no tinted box | n/a |
| testbed | Fig. S3 -> S4 (TikZ) | done | fill removed | n/a |

## Phase 4, renumbering (from the compiled .aux files; refs_before.txt and refs_after.txt)

Main: Fig. 1-7 unchanged, Fig. 9 deleted, Fig. 10 -> 8, Fig. 11 -> 9; Fig. 8 -> OR1. Table 3 deleted, Table 4 -> 3, 5 -> 4, 6 -> 5, 7 -> 6. Algorithm 1 unchanged.
OR1 figures: S1, S2 unchanged; new S3 (IQM and probability-of-improvement intervals); S3 -> S4 (testbed), S4 -> S5 (federation, now three panels with the former main Fig. 3b), S5 -> S6, S6 -> S7, main Fig. 8 -> S8, S7 -> S9; S8 (reproduction) became Table S11.
OR1 tables: S1 unchanged; S2 -> Online Resource 2 (ESM_2.csv); S3 -> S2, S4 -> S3, S5 -> S4, S6 -> S5, S7 -> S6, S8 -> S7, S9 -> S8, S10 -> S9, S11 -> S10; new S11 (reproduction).
Counts: main 9 figures, 6 tables, 1 algorithm; OR1 9 figures, 11 tables. First-citation order holds in both (one main sentence cited Table 6 before Tables 3 to 5 and was reworded). Neither document hard-codes the other's float numbers (the main paper cites OR1 by section, OR1 names main tables), so no cross-document number changed.
Submission: make_submission.py writes Fig1 to Fig9 as PDF and EPS (the data figures' own EPS; TikZ figures converted with pdftops -eps), ESM_1.pdf (byte-identical to supplementary.pdf) and ESM_2.csv; stale Fig10.pdf and Fig11.pdf removed. Figs. 2 and 4 are inline TikZ at 129.7 mm, so the submission scales them to 119 mm, where their 8 pt text prints at 7.3 pt (at or above the 7 pt minimum, as before the audit).
Numbers: numbers_diff_vs_pre_audit.txt lists every number token that differs from tag pre-audit. All differences are ids, TikZ coordinates and column widths, compliance fractions rewritten as percentages from the unrounded means, Table S2's values moved to ESM_2.csv, the Env B per-size values now quoted in the text, and the MLP transfer value moved to the Table S6 caption. No result changed: every printed value is checked by the verifier against the logs.
Reproducibility: paper5_regen_wpc_figures.sh regenerates all 15 figure files; every one is pixel-identical to the files in the paper (fig14_layouts once differed only because an earlier manual run of mine used a relative MATPLOTLIBRC and fell back to DejaVu; the regen version is the correct Liberation Sans one, and repeat runs match).

## Gate 4

| Check | Result |
|---|---|
| main.tex, supplementary.tex compile | 0 errors, 0 warnings, 0 undefined references, 0 overfull boxes; main 29 pp, OR1 10 pp |
| counts | main 9 figures, 6 tables, 1 algorithm; OR1 9 figures, 11 tables |
| unresolved references | 0 (refs_after.txt) |
| first-citation order | holds in both documents |
| verifier m66_verify.py | 663 of 663 checks pass, the 57 M82 audit checks among them; 635 checks shared with the pre-audit run: 607 compute identical values, 28 differ only by the fraction-to-percent rescaling (x 100 exactly) or by a row string reformatted around the same CI; 17 retired or renamed with their text, 28 new |
| CI recompute | 19 of 19 same |
| figures | all 15 regenerate pixel-identical with paper5_regen_wpc_figures.sh |
| submission | Fig1 to Fig9 in PDF and EPS, ESM_1.pdf byte-identical to the compiled OR1, ESM_2.csv; main.pdf has the same words as the working copy apart from the single-letter callout keys inside Fig. 4 |

## Table 1, prior-work cells (2026-11-09, author: "proceed on your recommendations")

A cell changed from n.r. only where the paper's own text states the fact; sources read in full with pdftotext.

| Work | Cell | Value | Verbatim support | Source |
|---|---|---|---|---|
| Shao et al. | Max cells | 19 | "we consider 19 BSs arranged like beehives as displayed in Fig. 1" (Sec. V-A) | arXiv 2108.05063 |
| Shao et al. | Rule baselines | yes | "DRL-based schemes (DQN and A2C) and hard slicing methods are involved as baselines ... Hard slicing allocates the total bandwidth for each slice uniformly" (Sec. V-A) | arXiv 2108.05063 |
| Shao et al. | Size-invariant params | n.r. kept | A2C: "different agents use the independent networks"; the DQN variant's sharing is not stated, so no single answer | arXiv 2108.05063 |
| Shao et al. | Zero-shot size transfer | n.r. kept | only 19 BSs are evaluated | arXiv 2108.05063 |
| Sulaiman et al. | Rule baselines | yes | "We utilize two heuristic-based and three DRL-based approaches ... (i) Greedy: All SRs are accepted for embedding ... (ii) Node-ranking" (Sec. VI-C) | rboutaba.cs.uwaterloo.ca/Papers/Journals/2023/SulaimanTNSM2022.pdf |
| Sulaiman et al. | Max cells | n.r. kept | the topology is "a 3-tiered topology, having 9 nodes, 3 in each tier" of compute sites; the number of cells or RUs is not stated | same |
| Sulaiman et al. | Zero-shot size transfer | n.r. kept | generalisation is to "variable SRs arrival rate, priority and throughput distributions", not to size | same |
| Zangooei et al. | Max cells | 1 | "we consider a single-cell scenario" (Sec. III) | rboutaba.cs.uwaterloo.ca/Papers/Journals/2023/ZangooeiJSAC2023.pdf |
| Zangooei et al. | Size-invariant params | partly, over slices | "A single policy per slice type is stored in Non-RT RIC" | same |
| Zangooei et al. | Zero-shot size transfer | partly, over slices | "the model is meticulously designed to be able to adapt to variations in the number of slices without necessitating a retraining process" | same |
| Zangooei et al. | Rule baselines | no | "We consider four RL methods as baseline algorithms: a model-based RL scheme named KBRL, two model-free single-agent RL methods, ... and a multi-agent RL approach" (Sec. VI-B) | same |
| Ahmadi et al., Mohajer et al., Bouroudi et al. | all four | n.r. kept | no accessible full text found (Ahmadi's NOMS 2023 relative is a different paper) | n/a |

Footnote e added: "Over the number of slices in a single cell, not over cells."

For the author: Sulaiman et al.'s Greedy baseline "accepts all SRs for embedding", close to an accept-all trivial policy. The Related Work sentences "neither study checks for degenerate policies" (Shao, Sulaiman) and "None of these core studies checks its metric against a trivial policy" come from the systematic review and were not changed; please confirm they still hold under the review's definition.

## Colours restored (2026-11-09, author: "restore the colours for the diagrams and figures as before (colour blind passing)")

The pre-audit colour schemes are back on the post-audit layouts; data, captions, layout checks and marker-shape redundancy are unchanged, and Fig. 8 (former Fig. 10) is untouched.

| Figure | Restored |
|---|---|
| shared tokens (figures/axiom_style.py) | AXIOM #0072B2 circle, MAPPO black diamond, DQN-SA #009E73 square, DQN-I #D55E00 triangle (paper5_common.M2_ARM_STYLE); learned filled, rules hollow; static rule #5b5a52 (paper5_common.RULE_STYLE); tuned rule Okabe-Ito purple #CC79A7 as in the pre-audit rliable figure and neighbour-aware rule sky #56B4E9, chosen over RULE_STYLE's olive and gold because olive against DQN-I's vermillion fell to dE 6.8 under protanopia; ENV_TAG badges; inferno_trim map |
| Fig. 1 | core, gNB and slice fills; slice icons and UEs in colour, with the original red, blue and green replaced by Okabe-Ito vermillion, blue and bluish green (the red/green pair is not CVD-safe); border styles kept as a second cue |
| Fig. 2 | Env A boxes blue, Env B orange, shared grey; lane labels in the Env A and Env B badge colours |
| Fig. 3, Fig. S5a | original node fills (blue, orange, green, violet) |
| Fig. 4 | grey steps, blue gates, red dashed failure callouts and connectors |
| Fig. 5, Fig. 7 | policy colours from the tokens; Env badges; Fig. 7's AXIOM row highlight |
| Fig. 6, Fig. S8 | inferno_trim; Env badges; Fig. 6's AXIOM frame (and the shared 8 pt style, which Fig. 6 had not applied; its canvas grows to 124 mm for the badge) |
| Fig. 9 | blue and orange cells at 85%, white hatching on rule cells, grey #DDDDDD neutral, white values on AXIOM cells, Env badges |
| Figs. S1, S2, S3, S5, S6, S7, S9 | forest Env bands and badges; profile line colours (AXIOM blue, DQN-SA green, DQN-I vermillion, MAPPO black, static grey dashed, tuned purple dashed); interval figure via the tokens; coloured env_tag badges (paper5_common); decision tuned-rule step #555555; testbed fill |

CVD check (CAM02-UCS dE, minimum over deuteranomaly, protanomaly, tritanomaly at full severity): policy tokens at least 11.7 for every pair (AXIOM against DQN-SA under tritanomaly, the original pairing), every pair also differs in marker shape or fill; Fig. 9 cells 26.8 to 50.7; Fig. 1 slice borders 10.0 to 43.9, Fig. 4 borders 46.9. The pastel fills of the diagrams are faint for every reader (dE 1.6 to 10.6) and never the only cue: slices carry icons, labels, positions and border styles, lanes are labelled, gates are diamonds. Fig. 1 rendered under deuteranopia keeps the three slices distinct.

## 2026-11-10, author requests: Fig. 3 width, per-gNB map back in the main text, Fig. 5 trend lines

- Fig. 3 (fig_architecture.tex) widened from about 62 mm to 118 mm at the same 0.81 scale, so its fonts are unchanged. Added on the left: each gNB's three features (PRB-used ratio, congestion level, normalised queue length) stacking into X (Sec. 4.1). Added on the right: the centralised training loop of Algorithm 1 (replay buffer and minibatch, per-request target from the target encoder and heads synced every T_s episodes, mean per-request Huber loss with a gradient step on theta and phi_k), plus the labels "decentralised execution" and "centralised training". The verified annotation of 7,782 parameters is unchanged. One caption sentence added.
- Fig. 5 (paper5_fig_scaling_trend.py): thin colour-matched lines (0.45 pt) join each learned policy's plotted means across 3, 7, 19 and 37 gNBs in panels a, b and c, and the legend shows them. The 93.7% label moved below its point so the AXIOM line no longer crosses it. Summary JSON byte-identical. One caption sentence added.
- The per-gNB Env B map (fig_pergnb_envb, OR1 Fig. S8 since the figure audit) returns to the main text as Fig. 8 with its pre-audit caption. "Section S7 of Online Resource 1 maps" now reads "Fig. 8 maps", and the OR1 sentence and figure are removed. The capability and regime figures become Figs. 9 and 10, and the OR1 figures after it shift by one.
- placeins [section] stranded Algorithm 1 and Fig. 4 behind section barriers once Fig. 3 grew, which left two half-empty pages. Both environments moved earlier in the source with their content unchanged. Main is 29 pages with 10 figures, 6 tables and 1 algorithm; OR1 is 10 pages with 8 figures.
- Checks: verifier 663/663 (with --supp), M82 57/57, CIs 17 same in main and 2 in OR1. Every other figure regenerates byte-identical as PNG; PDF and EPS differ only in CreationDate and were restored. The submission package was rebuilt (Fig1 to Fig10).

## 2026-11-10 (second round), author requests: Figs. 4, 5, 6, 10, tables, colour-blind and greyscale check

- Fig. 5: the static rule is no longer drawn (its numbers stay in the summary JSON, which is byte-identical). The method lines are now dotted at 0.3 pt, the house minimum, and the legend has four entries. Caption: "beside the static rule" removed, "Dotted lines join each policy's means across sizes".
- Fig. 6: the four 37-gNB honeycombs sit in one row, 119 x 66 mm instead of 119 x 124 mm, with three-line headers and the key and colour bar side by side below. Summary JSON byte-identical, caption unchanged.
- Fig. 10: 119 x 50 mm instead of 62 mm. The cells are shorter and the titles and legend set closer, with every cell, title and legend entry kept. Summary JSON byte-identical.
- Fig. 4: rows 0.35 cm and 0.8 cm further apart, and every callout moved at least about 0.25 cm from any node, diamond or arrow (c no longer overlaps Gate 1, e no longer touches Gate 3). Wording unchanged.
- OR1 performance-profile figure (fig_rliable): DQN-SA and DQN-I differ by only 3.6 L* in greyscale, so each curve now also has its own line pattern (AXIOM and MAPPO solid, DQN-SA dotted, DQN-I dash-dot, static rule dashed, tuned rule dash-dot-dot).
- Table 2: re-laid out as a URLLC / eMBB / mMTC grid for the slice parameters, with full-width rows for the simulator and learning settings. Values unchanged; caption drops "Slice values are listed as URLLC, eMBB, mMTC". The exact-text matches for Table 2 in m82_audit.py (3 checks) and m66_verify.py (1 check) now match the new layout; each still compares the same values with the configuration and code, and no check was removed.
- Table 6: column widths only (design 74 pt, parameters 80 pt centred, spacing 4 pt), so no cell runs past two lines. Row text unchanged.
- Table 1: Work 2.45 cm and Problem 3.6 cm, so author names fit one line and the table fills the text width. Table 5: policy column 3.5 cm, one line per row. OR1 Table S1: meaning columns at 0.24 of the text width.
- OR1 Table S11: "Fig1 to Fig9" corrected to "Fig1 to Fig10".
- Main 28 pp (was 29), OR1 10 pp.
- Accessibility audit (new experiments/scripts/audit_figure_accessibility.py): every main and OR1 figure rendered as submitted, with greyscale (CIE L*) and deuteranomaly, protanomaly and tritanomaly previews inspected by eye. Every policy pair differs in marker shape or fill, the minimum colour-vision distance between policy colours is 11.7 (CAM02-UCS), and no main or OR1 caption contains a colour word. The one figure that failed in greyscale (fig_rliable) was fixed as above.
- Triple check (new experiments/scripts/audit_runtime_vs_logs.py): 1,872 runner summaries in 27 campaigns, 5,677 seed records. Each reward and block count the runner wrote while it ran matches the value re-read from the evaluation log (reward to 1e-9, blocks exactly), with no mismatch and no missing log.
- Test-choice check (new experiments/scripts/audit_test_robustness.py): 76 tests in the paper's 9 main Holm families (Table 3 family, Env B H1, learned baselines and tuned rule, 7-, 19- and 37-gNB scaling, 19-gNB load shift, shared-head ablation) were redone with a sign-flip permutation test of the mean paired difference (200,000 draws). All 76 verdicts agree with the Wilcoxon verdicts at Holm-adjusted p < 0.05, including the not-significant DQN-SA comparison at three gNBs.
- Final checks on this state: verifier 663/663 (with --supp), M82 57/57, CIs 17 same in main and 2 in OR1; no LaTeX errors or overfull boxes; submission package rebuilt (Fig1 to Fig10, main 28 pp).
- Single-seed influence (added to audit_test_robustness.py): dropping any one seed from any of the 9 families leaves every significant verdict unchanged. The only verdict changes are two borderline non-significant results in the Table 3 family: AXIOM over DQN-SA and over the MLP encoder become significant when seed 901 or 904 is dropped. These are the nulls under test in M98 A and M99 B.
- Check coverage (new experiments/scripts/audit_check_coverage.py): every result number in the abstract, discussion and conclusion lies inside text that m66_verify.py or m82_audit.py matches. The uncovered numbers are labels and conventions (5G, 95% CI, p < 0.05, "Online Resource 1", grant codes). In Results and OR1 the uncovered numbers are seed counts, settings, figure coordinates and section numbers. Two result-like numbers were checked by hand: "Holm-adjusted p <= 0.0002" for Table 3 (0.00018 and 0.000015) and the 24-configuration MAPPO grid (m70_select_mappo.py asserts 24 rows). The live checkpoint's 18,562 parameters were recounted from checkpoint.pt (13-128-128-2).
- Reproduction (experiments/results/audit_reproduction_20261110.json): four stored runs drawn at random (DQN-I, DQN-SA and MAPPO at 37 gNBs, AXIOM at 7 gNBs hex) were retrained from scratch in fresh processes. Each reproduced its stored reward, blocks and per-slice SLA compliance exactly.
