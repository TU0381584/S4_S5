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

## Phase 1, removals and moves: STOPPED at the pre-edit claim check (no edits made)

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

Gate 1 is waiting on the author's choice for the two orphaned groups.
